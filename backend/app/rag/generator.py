import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from app.core.config import settings
from app.schemas.rag import SourceCitation

logger = logging.getLogger("edunex.rag.generator")

GROUNDED_SYSTEM_PROMPT = """You are EduNex AI, a production educational AI tutor and knowledge assistant.
Your mission is to provide accurate, pedagogical, and strictly grounded answers to student questions based ONLY on the provided context chunks.

STRICT INSTRUCTIONS:
1. Grounded Answers: Use ONLY the facts and context provided in the 'CONTEXT CHUNKS' section below.
2. Missing Information: If the provided context does not contain sufficient information to answer the question, state clearly and concisely:
   "The provided document(s) do not contain information to answer this question."
   Do NOT attempt to guess, assume, or answer from general knowledge when context is missing.
3. Citations: Every factual assertion MUST cite its source document and page number in brackets, for example: [Document: <filename>, Page: <page_number>].
4. No Fabrication: Never fabricate or invent document names, page numbers, or citations.
5. Pedagogical Clarity: Structure your explanation clearly with concise paragraphs and bullet points where helpful for student learning.
"""


class RAGGenerator:
    """
    RAG generation engine. Formats context, executes grounded generation with Gemini LLM,
    and falls back cleanly to offline synthesis when API keys are not configured.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or settings.GOOGLE_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL

    def build_context_prompt(self, query: str, chunks: List[Dict[str, Any]]) -> str:
        """
        Builds the prompt string combining context chunks and the user's question.
        """
        if not chunks:
            return f"QUESTION: {query}\n\nCONTEXT CHUNKS: None provided."

        formatted_chunks = []
        for i, chunk in enumerate(chunks, 1):
            filename = chunk.get("filename", "Unknown Document")
            page = chunk.get("page", 1)
            text = chunk.get("text", "").strip()
            score = chunk.get("score", 0.0)
            formatted_chunks.append(
                f"--- CHUNK {i} [Source: {filename} | Page: {page} | Score: {score:.3f}] ---\n{text}"
            )

        context_body = "\n\n".join(formatted_chunks)

        return (
            f"QUESTION: {query}\n\n"
            f"CONTEXT CHUNKS:\n"
            f"{context_body}\n\n"
            f"Please answer the question based strictly on the context chunks above, including citations for all claims."
        )

    def generate_answer(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
    ) -> Tuple[str, List[SourceCitation], int, str]:
        """
        Generates an answer from retrieved chunks.
        Returns:
            (answer_text, citations, latency_ms, llm_provider)
        """
        start_time = time.perf_counter()

        # Format citations from retrieved chunks
        citations: List[SourceCitation] = []
        for chunk in chunks:
            citations.append(
                SourceCitation(
                    document_id=str(chunk.get("doc_id", "")),
                    document_name=str(chunk.get("filename", "")),
                    page=int(chunk.get("page", 1)),
                    chunk_index=int(chunk.get("chunk_index", 0)),
                    score=float(chunk.get("score", 0.0)),
                    text_snippet=chunk.get("text", "")[:200] + ("..." if len(chunk.get("text", "")) > 200 else ""),
                )
            )

        # If no chunks were retrieved (below threshold or no documents)
        if not chunks:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            return (
                "The provided document(s) do not contain information to answer this question.",
                [],
                latency_ms,
                "none",
            )

        # If Gemini API key is configured, call Gemini
        if self.api_key and self.api_key.strip():
            try:
                answer = self._call_gemini(query, chunks)
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                return answer, citations, latency_ms, f"gemini ({self.model_name})"
            except Exception as e:
                logger.warning("Gemini generation failed: %s. Falling back to grounded synthesis.", str(e))

        # Deterministic offline fallback grounded synthesis
        answer = self._generate_offline_synthesis(query, chunks)
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        return answer, citations, latency_ms, "offline-grounded-engine"

    def _call_gemini(self, query: str, chunks: List[Dict[str, Any]]) -> str:
        """Call Gemini via google-genai or langchain-google-genai."""
        user_prompt = self.build_context_prompt(query, chunks)

        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=[user_prompt],
                config={"system_instruction": GROUNDED_SYSTEM_PROMPT, "temperature": 0.2},
            )
            return response.text.strip()
        except Exception:
            # Fallback to langchain_google_genai
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain_core.messages import SystemMessage, HumanMessage

            llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=self.api_key,
                temperature=0.2,
            )
            messages = [
                SystemMessage(content=GROUNDED_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]
            res = llm.invoke(messages)
            return str(res.content).strip()

    def _generate_offline_synthesis(self, query: str, chunks: List[Dict[str, Any]]) -> str:
        """
        Extractive grounded synthesis used when Gemini API key is unavailable or in offline test environments.
        Synthesizes the answer strictly from the relevant chunks and explicitly attaches citations.
        """
        # Group excerpts with their citations
        excerpts = []
        for chunk in chunks:
            filename = chunk.get("filename", "Document")
            page = chunk.get("page", 1)
            text = chunk.get("text", "").strip()
            citation = f"[Document: {filename}, Page: {page}]"
            excerpts.append(f"{text} {citation}")

        body = "\n\n".join(excerpts)
        return (
            f"Based on your study materials:\n\n"
            f"{body}"
        )

