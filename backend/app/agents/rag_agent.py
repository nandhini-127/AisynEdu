import logging
import time
from typing import Dict, List
from uuid import UUID

from app.agents.llm_client import LLMClient
from app.agents.prompts.rag_prompts import RAG_SYSTEM_PROMPT, build_rag_prompt
from app.agents.state import AgentState, SourceCitationDict
from app.guardrails.service import GuardrailsService
from app.rag.embeddings import SentenceTransformerEmbeddings
from app.rag.vectorstore import ChromaVectorStore

logger = logging.getLogger("edunex.agents.rag")


class RAGAgent:
    """
    RAG Agent retrieving knowledge from student documents, citing pages,
    and explicitly differentiating between document-grounded and general knowledge.
    """

    @classmethod
    async def execute(cls, state: AgentState) -> Dict:
        start_time = time.perf_counter()
        query = state.get("input_query", "")
        user_id_str = state.get("user_id")
        doc_ids_raw = state.get("document_ids", [])
        provider = state.get("llm_provider", "gemini")
        model = state.get("model_name")

        # Parse document IDs
        doc_uuids: List[UUID] = []
        for did in doc_ids_raw:
            try:
                doc_uuids.append(UUID(str(did)))
            except ValueError:
                pass

        user_uuid = UUID(user_id_str) if user_id_str else None

        retrieved_chunks = []
        citations: List[SourceCitationDict] = []
        is_grounded = False
        context_body = ""

        subject = state.get("subject", "")
        clean_subject = subject if subject and subject not in ["General Education", "General Studies"] else None

        # Retrieve chunks from ChromaDB if user ID is available
        if user_uuid:
            try:
                embedder = SentenceTransformerEmbeddings.get_instance()
                query_vec = embedder.embed_query(query)
                vector_store = state.get("vector_store") or ChromaVectorStore()

                retrieved_chunks = vector_store.query_similar_chunks(
                    query_embedding=query_vec,
                    user_id=user_uuid,
                    doc_ids=doc_uuids if doc_uuids else None,
                    subject=clean_subject,
                    top_k=4,
                    similarity_threshold=0.45,
                )
            except Exception as e:
                logger.warning("Vector retrieval encountered an issue: %s", str(e))

        if retrieved_chunks:
            is_grounded = True
            for chunk in retrieved_chunks:
                fname = chunk.get("filename", "Study Material")
                page = chunk.get("page", 1)
                score = chunk.get("score", 0.0)
                text = chunk.get("text", "")
                citations.append(
                    SourceCitationDict(
                        document_id=str(chunk.get("doc_id", "")),
                        document_name=fname,
                        page=int(page),
                        chunk_index=int(chunk.get("chunk_index", 0)),
                        score=float(score),
                        text_snippet=text[:180] + ("..." if len(text) > 180 else ""),
                    )
                )

            # Apply Guardrails: treat documents as untrusted reference data & neutralize injections
            context_body = GuardrailsService.sanitize_and_sandbox_documents(retrieved_chunks)

        # Build prompt
        prompt = build_rag_prompt(
            query=query,
            context_body=context_body,
            history_context="",
        )

        client = LLMClient(provider=provider, model_name=model)
        raw_response = await client.generate_response(
            prompt=prompt,
            system_prompt=RAG_SYSTEM_PROMPT,
            temperature=0.2,
        )

        # Append clear study material reference header
        if is_grounded:
            final_response = f"**[Referenced from Your Study Materials]**\n\n{raw_response}"
        else:
            final_response = (
                f"**[General Knowledge / Academic Concept]**\n\n"
                f"*Note: None of your uploaded study materials contained direct sections for this topic, so here is a comprehensive educational breakdown:*\n\n"
                f"{raw_response}"
            )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        logger.info(
            "RAGAgent finished (grounded=%s, chunks=%d, citations=%d, latency=%dms)",
            is_grounded,
            len(retrieved_chunks),
            len(citations),
            latency_ms,
        )

        return {
            "response_text": final_response,
            "retrieved_chunks": retrieved_chunks,
            "context_text": context_body,
            "citations": citations,
            "is_document_grounded": is_grounded,
            "latency_ms": latency_ms,
            "is_fallback": getattr(client, "last_is_fallback", False),
            "fallback_reason": getattr(client, "last_fallback_reason", None),
            "llm_provider": getattr(client, "last_provider_used", provider),
        }
