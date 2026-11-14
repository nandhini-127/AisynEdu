import logging
from typing import List, Optional
from uuid import UUID

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Message, Session

logger = logging.getLogger("edunex.memory.manager")


class ConversationMemoryManager:
    """
    Manages session-bounded conversation history stored in PostgreSQL.
    Provides windowed context retrieval and conversation clearing for students.
    """

    DEFAULT_CONTEXT_WINDOW = 10  # Max previous messages loaded into prompt context

    @classmethod
    async def get_session_history(
        cls,
        db: AsyncSession,
        session_id: UUID,
        limit: int = DEFAULT_CONTEXT_WINDOW,
    ) -> List[Message]:
        """
        Retrieves the most recent messages for a study session, ordered chronologically.
        Enforces a bounded context window to prevent prompt bloat.
        """
        # Fetch the most recent `limit` messages
        query = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(query)
        recent_messages = list(result.scalars().all())

        # Reverse to chronological order (oldest to newest)
        recent_messages.reverse()
        return recent_messages

    @classmethod
    async def get_langchain_messages(
        cls,
        db: AsyncSession,
        session_id: UUID,
        limit: int = DEFAULT_CONTEXT_WINDOW,
    ) -> List[BaseMessage]:
        """
        Converts stored database messages into LangChain HumanMessage and AIMessage objects.
        """
        db_messages = await cls.get_session_history(db, session_id, limit=limit)
        lc_messages: List[BaseMessage] = []

        for msg in db_messages:
            if msg.role == "user":
                lc_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                lc_messages.append(AIMessage(content=msg.content))

        return lc_messages

    @classmethod
    async def format_history_as_text(
        cls,
        db: AsyncSession,
        session_id: UUID,
        limit: int = DEFAULT_CONTEXT_WINDOW,
    ) -> str:
        """
        Formats recent conversation history as readable dialogue string for prompt injection.
        """
        db_messages = await cls.get_session_history(db, session_id, limit=limit)
        if not db_messages:
            return ""

        lines = []
        for msg in db_messages:
            speaker = "Student" if msg.role == "user" else "Tutor"
            lines.append(f"{speaker}: {msg.content}")

        return "\n".join(lines)

    @classmethod
    async def save_message(
        cls,
        db: AsyncSession,
        session_id: UUID,
        user_id: UUID,
        role: str,
        content: str,
        intent: str = "qa",
        sources: Optional[list] = None,
        latency_ms: int = 0,
        token_count: int = 0,
        llm_provider: Optional[str] = None,
    ) -> Message:
        """
        Persists a student or assistant message to the database.
        """
        msg = Message(
            session_id=session_id,
            user_id=user_id,
            role=role,
            content=content,
            intent=intent,
            sources=sources or [],
            latency_ms=latency_ms,
            token_count=token_count,
            llm_provider=llm_provider,
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return msg

    @classmethod
    async def clear_session_history(
        cls,
        db: AsyncSession,
        session_id: UUID,
        user_id: UUID,
    ) -> int:
        """
        Permanently clears all message history for a student's session.
        Enforces user ownership check.
        """
        stmt = delete(Message).where(
            Message.session_id == session_id,
            Message.user_id == user_id,
        )
        result = await db.execute(stmt)
        await db.commit()
        deleted_count = result.rowcount or 0
        logger.info("Cleared %d messages for session %s (user %s)", deleted_count, str(session_id), str(user_id))
        return deleted_count

