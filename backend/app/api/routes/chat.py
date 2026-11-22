import asyncio
import json
import logging
import re
from typing import AsyncGenerator, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.llm_client import ProviderUnavailableError
from app.agents.orchestrator import EduNexAssistant
from app.analytics.service import AnalyticsService
from app.api.dependencies import get_current_user, verify_resource_ownership
from app.core.database import AsyncSessionLocal, get_db
from app.guardrails.service import GuardrailsService
from app.memory.manager import ConversationMemoryManager
from app.models.entities import User
from app.schemas.base import (
    ApiResponse,
    ExportPDFRequest,
    MessageCreate,
    MessageRead,
    SessionCreate,
    SessionRead,
)
from app.services.chat_service import ChatService
from app.services.pdf_service import PDFService

logger = logging.getLogger("edunex.api.chat")

router = APIRouter(prefix="/chat", tags=["Chat & Learning Assistant"])


@router.post("/sessions", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new subject study session."""
    session = await ChatService.create_session(db, current_user.id, data)
    return ApiResponse(
        success=True,
        message="Session created",
        data=SessionRead.model_validate(session),
    )


@router.get("/sessions", response_model=ApiResponse)
async def get_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves all sessions belonging exclusively to the authenticated student."""
    sessions = await ChatService.list_user_sessions(db, current_user.id)
    return ApiResponse(
        success=True,
        data=[SessionRead.model_validate(s) for s in sessions],
    )


@router.get("/sessions/{session_id}/messages", response_model=ApiResponse)
async def get_session_messages(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetches chat history for a session with strict ownership verification.
    """
    session = await ChatService.get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    verify_resource_ownership(session.user_id, current_user, "study session")

    messages = await ChatService.get_session_messages(db, session_id)
    return ApiResponse(
        success=True,
        data=[MessageRead.model_validate(m) for m in messages],
    )


@router.delete("/sessions/{session_id}/messages", response_model=ApiResponse)
async def clear_session_messages(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Clears all chat message history for the specified session.
    Allows students to reset context while preserving session metadata.
    """
    session = await ChatService.get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    verify_resource_ownership(session.user_id, current_user, "study session")

    deleted_count = await ConversationMemoryManager.clear_session_history(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
    )

    return ApiResponse(
        success=True,
        message=f"Successfully cleared {deleted_count} message(s) from study session.",
        data={"cleared_count": deleted_count},
    )


@router.post("/message", response_model=ApiResponse)
async def send_message(
    msg_in: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submits a student question into an existing session, enforces safety guardrails,
    invokes the LangGraph orchestrator, records telemetry, and returns grounded response.
    """
    session = await ChatService.get_session_by_id(db, msg_in.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Enforce data isolation
    verify_resource_ownership(session.user_id, current_user, "study session")

    # 1. Safety Guardrail: Input Validation & Prompt Injection Detection
    val_res = GuardrailsService.validate_user_query(msg_in.content)
    if not val_res.is_safe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Safety Policy Violation: {val_res.reason}",
        )

    clean_content = val_res.sanitized_text

    # 2. Record student message in DB
    user_msg = await ConversationMemoryManager.save_message(
        db=db,
        session_id=msg_in.session_id,
        user_id=current_user.id,
        role="user",
        content=clean_content,
        intent=msg_in.intent,
    )

    # 3. Retrieve bounded conversation history (context window)
    previous_lc_messages = await ConversationMemoryManager.get_langchain_messages(
        db=db,
        session_id=msg_in.session_id,
        limit=10,
    )

    # Combine session document_ids with any message-level overrides
    combined_doc_ids = list(set([str(d) for d in session.document_ids] + [str(d) for d in msg_in.document_ids]))
    chosen_provider = msg_in.llm_override or current_user.preferred_llm or "gemini"

    # 4. Invoke LangGraph Orchestrator
    try:
        agent_result = await EduNexAssistant.process_student_query(
            user_id=str(current_user.id),
            session_id=str(msg_in.session_id),
            subject=session.subject,
            query=clean_content,
            requested_intent=msg_in.intent,
            difficulty=msg_in.difficulty,
            document_ids=combined_doc_ids,
            llm_provider=chosen_provider,
            previous_messages=previous_lc_messages,
            question_count=msg_in.question_count,
        )
    except ProviderUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Requested LLM provider '{chosen_provider}' is unavailable: {str(e)}",
        )
    except Exception as e:
        safe_msg = GuardrailsService.get_safe_error(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=safe_msg,
        )

    # 5. Safety Guardrail: Output Validation & Hallucination Mitigation
    raw_response = agent_result.get("response_text", "No response generated.")
    citations = agent_result.get("citations", [])
    resolved_intent = agent_result.get("resolved_intent", msg_in.intent)
    latency_ms = agent_result.get("latency_ms", 0)
    is_grounded = agent_result.get("is_document_grounded", False)

    sanitized_response, is_output_safe, safety_meta = GuardrailsService.validate_assistant_output(
        output_text=raw_response,
        is_document_grounded=is_grounded,
        retrieved_context=agent_result.get("retrieved_context", ""),
    )

    # 6. Save Assistant message in DB
    assistant_msg = await ConversationMemoryManager.save_message(
        db=db,
        session_id=msg_in.session_id,
        user_id=current_user.id,
        role="assistant",
        content=sanitized_response,
        intent=resolved_intent,
        sources=citations,
        latency_ms=latency_ms,
        llm_provider=chosen_provider,
    )

    # 7. Telemetry & Analytics Tracking
    try:
        await AnalyticsService.record_event(
            db=db,
            user_id=current_user.id,
            event_type="question_asked",
            subject=session.subject,
            llm_provider=chosen_provider,
            tokens_used=len(sanitized_response.split()),
            latency_ms=latency_ms,
            retrieval_hit=len(citations) > 0,
            retrieval_chunk_count=len(citations),
            extra_data={"intent": resolved_intent, "grounding": safety_meta},
        )
    except Exception as analytics_err:
        logger.warning("Non-blocking analytics failure (chat message): %s", str(analytics_err))

    # Prepare response payload
    user_read = MessageRead(
        id=user_msg.id,
        session_id=user_msg.session_id,
        role=user_msg.role,
        content=user_msg.content,
        sources=user_msg.sources or [],
        intent=user_msg.intent,
        token_count=user_msg.token_count or 0,
        latency_ms=user_msg.latency_ms or 0,
        llm_provider=user_msg.llm_provider,
        created_at=user_msg.created_at,
    )

    assistant_read = MessageRead(
        id=assistant_msg.id,
        session_id=assistant_msg.session_id,
        role=assistant_msg.role,
        content=assistant_msg.content,
        sources=assistant_msg.sources or [],
        intent=assistant_msg.intent,
        token_count=assistant_msg.token_count or 0,
        latency_ms=assistant_msg.latency_ms or 0,
        llm_provider=agent_result.get("llm_provider") or assistant_msg.llm_provider,
        created_at=assistant_msg.created_at,
        quiz_data=agent_result.get("quiz_data"),
        summary_data=agent_result.get("summary_data"),
        recommendations=agent_result.get("learning_recommendations"),
        is_fallback=agent_result.get("is_fallback", False),
        fallback_reason=agent_result.get("fallback_reason"),
    )

    return ApiResponse(
        success=True,
        message=f"Query processed via {resolved_intent.upper()} capability.",
        data={
            "user_message": user_read,
            "assistant_message": assistant_read,
            "resolved_intent": resolved_intent,
            "router_reasoning": agent_result.get("router_reasoning", ""),
            "is_document_grounded": is_grounded,
            "safety_metadata": safety_meta,
            "is_fallback": agent_result.get("is_fallback", False),
            "fallback_reason": agent_result.get("fallback_reason"),
        },
    )


@router.post("/stream")
async def stream_message(
    msg_in: MessageCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Server-Sent Events (SSE) streaming endpoint for real-time progressive response tokens.
    Handles client disconnects, timeouts, guardrails, and message history persistence.
    """
    session = await ChatService.get_session_by_id(db, msg_in.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    verify_resource_ownership(session.user_id, current_user, "study session")

    # Safety Guardrail Check
    val_res = GuardrailsService.validate_user_query(msg_in.content)
    if not val_res.is_safe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Safety Policy Violation: {val_res.reason}",
        )

    clean_content = val_res.sanitized_text

    # Record student message in DB
    user_msg = await ConversationMemoryManager.save_message(
        db=db,
        session_id=msg_in.session_id,
        user_id=current_user.id,
        role="user",
        content=clean_content,
        intent=msg_in.intent,
    )

    combined_doc_ids = list(set([str(d) for d in session.document_ids] + [str(d) for d in msg_in.document_ids]))
    chosen_provider = msg_in.llm_override or current_user.preferred_llm or "gemini"

    previous_lc_messages = await ConversationMemoryManager.get_langchain_messages(
        db=db,
        session_id=msg_in.session_id,
        limit=10,
    )

    async def sse_generator() -> AsyncGenerator[str, None]:
        # 1. Start event
        yield f"event: start\ndata: {json.dumps({'session_id': str(msg_in.session_id), 'user_message_id': str(user_msg.id)})}\n\n"

        # Check client disconnect
        if await request.is_disconnected():
            return

        try:
            # 2. Invoke LangGraph orchestrator
            agent_result = await EduNexAssistant.process_student_query(
                user_id=str(current_user.id),
                session_id=str(msg_in.session_id),
                subject=session.subject,
                query=clean_content,
                requested_intent=msg_in.intent,
                difficulty=msg_in.difficulty,
                document_ids=combined_doc_ids,
                llm_provider=chosen_provider,
                previous_messages=previous_lc_messages,
                question_count=msg_in.question_count,
            )

            resolved_intent = agent_result.get("resolved_intent", msg_in.intent)
            citations = agent_result.get("citations", [])
            raw_text = agent_result.get("response_text", "")
            latency_ms = agent_result.get("latency_ms", 0)
            is_grounded = agent_result.get("is_document_grounded", False)

            # 3. Intent & citations event
            yield f"event: intent\ndata: {json.dumps({'intent': resolved_intent, 'is_grounded': is_grounded})}\n\n"
            if citations:
                yield f"event: citations\ndata: {json.dumps(citations)}\n\n"

            # 4. Stream tokens progressively
            sanitized_text, _, safety_meta = GuardrailsService.validate_assistant_output(
                raw_text, is_document_grounded=is_grounded, retrieved_context=agent_result.get("retrieved_context", "")
            )

            words = sanitized_text.split(" ")
            for i, word in enumerate(words):
                if await request.is_disconnected():
                    break
                chunk = word + (" " if i < len(words) - 1 else "")
                yield f"event: token\ndata: {json.dumps({'chunk': chunk})}\n\n"
                await asyncio.sleep(0.015)  # Progressive token emission pace

            # 5. Persist complete response in chat history using an independent session
            assistant_msg_id = ""
            try:
                async with AsyncSessionLocal() as session_db:
                    assistant_msg = await ConversationMemoryManager.save_message(
                        db=session_db,
                        session_id=msg_in.session_id,
                        user_id=current_user.id,
                        role="assistant",
                        content=sanitized_text,
                        intent=resolved_intent,
                        sources=citations,
                        latency_ms=latency_ms,
                        llm_provider=chosen_provider,
                    )
                    assistant_msg_id = str(assistant_msg.id)

                    # 6. Record analytics event
                    try:
                        await AnalyticsService.record_event(
                            db=session_db,
                            user_id=current_user.id,
                            event_type="question_asked_stream",
                            subject=session.subject,
                            llm_provider=chosen_provider,
                            tokens_used=len(words),
                            latency_ms=latency_ms,
                            retrieval_hit=len(citations) > 0,
                            retrieval_chunk_count=len(citations),
                            extra_data={"intent": resolved_intent, "grounding": safety_meta},
                        )
                    except Exception as analytics_err:
                        logger.warning("Non-blocking analytics failure in stream: %s", str(analytics_err))
            except Exception as persist_err:
                logger.error("Failed to persist assistant message in stream: %s", str(persist_err), exc_info=True)

            # 7. Done event
            yield f"event: done\ndata: {json.dumps({'message_id': assistant_msg_id, 'tokens': len(words), 'latency_ms': latency_ms})}\n\n"

        except Exception as e:
            logger.error("Error in chat streaming: %s", str(e), exc_info=True)
            safe_err = GuardrailsService.get_safe_error(e)
            yield f"event: error\ndata: {json.dumps({'error': safe_err})}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/export-pdf")
async def export_notes_pdf(
    payload: ExportPDFRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Exports synthesized study notes as a professional, multi-page PDF document.
    Preserves headings, bullet points, numbered lists, tables, callouts, and code blocks.
    Returns binary PDF stream with Content-Disposition attachment header.
    """
    if not payload.content or not payload.content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot generate PDF from empty notes content.",
        )

    try:
        pdf_bytes = PDFService.generate_notes_pdf(
            title=payload.title,
            subject=payload.subject or "General Studies",
            content=payload.content,
        )

        safe_title = re.sub(r"[^\w\s-]", "", payload.title).strip()
        safe_title = re.sub(r"[-\s]+", "_", safe_title) or "study_notes"
        filename = f"{safe_title}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "application/pdf",
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )
    except Exception as e:
        logger.error("Failed to generate notes PDF: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF generation failed: {str(e)}",
        )

