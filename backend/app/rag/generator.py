import ast
import json
import logging
import os
import random
import time
from typing import Any, Dict, List, Optional, Tuple
from app.core.config import settings
from app.schemas.rag import SourceCitation

logger = logging.getLogger("edunex.rag.generator")


def _is_transient_error(error: Exception) -> bool:
    """
    Identifies whether an error is transient (temporary 429 rate limit, 503 unavailable, network timeout)
    versus permanent (400 invalid argument/bad key, 401 unauthorized, 403 forbidden, 404 not found).
    """
    err_str = str(error).lower()

    # Quota exhaustion must not be retried (daily quota exceeded)
    if "resource_exhausted" in err_str or "quota" in err_str or "free_tier" in err_str:
        return False

    # Permanent errors - NEVER retry
    permanent_indicators = [
        "400",
        "invalid_argument",
        "api_key_invalid",
        "api key not valid",
        "apikey invalid",
        "401",
        "unauthorized",
        "403",
        "permission_denied",
        "404",
        "not_found",
        "model not found",
    ]
    if any(ind in err_str for ind in permanent_indicators):
        return False

    # Transient errors - retry with bounded backoff + jitter
    transient_indicators = [
        "503",
        "unavailable",
        "504",
        "deadline",
        "timeout",
        "timed out",
        "connection reset",
        "connection error",
        "connect error",
    ]
    if any(ind in err_str for ind in transient_indicators):
        return True

    return False


def extract_text_from_gemini_response(content: Any) -> str:
    """
    Safely extracts clean user-facing generated text from diverse response formats:
    - Pure string responses
    - Structured content block lists: [{'type': 'text', 'text': '...', 'extras': {...}}]
    - Stringified representations of content blocks
    - Objects with .text or .content attributes (e.g. LangChain AIMessage, Google GenAI response)

    Guarantees:
    - Strips internal metadata, extras, and signatures.
    - Preserves Markdown formatting, indentation, and structure.
    - Handles empty responses and missing text gracefully.
    """
    if content is None:
        return ""

    if isinstance(content, str):
        clean = content.strip()
        # Detect and parse stringified content block representations
        if (clean.startswith("[") and clean.endswith("]")) or (clean.startswith("{") and clean.endswith("}")):
            if ("'text':" in clean or '"text":' in clean):
                try:
                    parsed = ast.literal_eval(clean)
                    return extract_text_from_gemini_response(parsed)
                except Exception:
                    try:
                        parsed = json.loads(clean)
                        return extract_text_from_gemini_response(parsed)
                    except Exception:
                        pass
        return clean

    if isinstance(content, list):
        parts = []
        for item in content:
            extracted = extract_text_from_gemini_response(item)
            if extracted:
                parts.append(extracted)
        return "\n\n".join(parts).strip()

    if isinstance(content, dict):
        # Extract text field, ignoring extras, type, signature, and internal metadata
        if "text" in content and isinstance(content["text"], str):
            return content["text"].strip()
        if "content" in content:
            return extract_text_from_gemini_response(content["content"])
        return ""

    if hasattr(content, "text") and getattr(content, "text") is not None:
        return extract_text_from_gemini_response(getattr(content, "text"))

    if hasattr(content, "content") and getattr(content, "content") is not None:
        return extract_text_from_gemini_response(getattr(content, "content"))

    return str(content).strip()


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
        self.api_key = (
            api_key
            or settings.GOOGLE_API_KEY
            or getattr(settings, "GEMINI_API_KEY", "")
            or os.environ.get("GOOGLE_API_KEY", "")
            or os.environ.get("GEMINI_API_KEY", "")
            or ""
        ).strip().strip("'\"")
        self.model_name = (model_name or settings.GEMINI_MODEL or "gemini-3.5-flash-lite").strip().strip("'\"")

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

    def _is_offline_mode(self) -> bool:
        """
        Determines whether the generator should immediately use deterministic offline synthesis.
        Fast-paths when API key is missing, in testing environments, or configured with dummy test keys.
        """
        if not self.api_key or not self.api_key.strip():
            return True
        if settings.ENVIRONMENT == "testing" or os.environ.get("ENVIRONMENT") == "testing":
            return True
        k = self.api_key.lower()
        if k.startswith("test") or "dummy" in k or "your_gemini_api_key_here" in k:
            return True
        return False

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

        # Fast path for offline / test environments
        if self._is_offline_mode():
            logger.info("RAGGenerator fast-pathing offline grounded synthesis (offline/test mode or mock key).")
            answer = self._generate_offline_synthesis(query, chunks)
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            return answer, citations, latency_ms, "offline-grounded-engine"

        # Production Gemini LLM call with bounded retries and timeouts
        try:
            raw_answer, provider_label = self._call_gemini_with_retry(query, chunks)
            answer = extract_text_from_gemini_response(raw_answer)
            if answer:
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                return answer, citations, latency_ms, provider_label
            else:
                logger.warning("Gemini returned empty text response. Falling back to grounded synthesis.")
        except Exception as e:
            logger.warning("Gemini generation failed: %s. Falling back to grounded synthesis.", str(e))

        # Deterministic offline fallback grounded synthesis
        fallback_start = time.perf_counter()
        answer = self._generate_offline_synthesis(query, chunks)
        fallback_ms = int((time.perf_counter() - fallback_start) * 1000)
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(
            "[RAG-GEN-TIMING] Fallback offline synthesis completed in %d ms (total pipeline wait=%d ms)",
            fallback_ms,
            latency_ms,
        )
        return answer, citations, latency_ms, "offline-grounded-engine"

    def _call_gemini_single_attempt(self, user_prompt: str) -> Tuple[str, str]:
        """
        Executes a single generation call against Google Gemini.
        Prefers the official google.genai SDK; falls back to LangChain ONLY if google.genai is not installed.
        Enforces a 25-second per-request network timeout.
        """
        # Candidate models strictly starting with configured primary model, with verified fallback
        primary_model = (self.model_name or settings.GEMINI_MODEL or "gemini-3.5-flash-lite").strip()
        fallback_model = getattr(settings, "GEMINI_FALLBACK_MODEL", "gemini-3.8-flash").strip()
        candidate_models = [primary_model]
        if fallback_model and fallback_model not in candidate_models:
            candidate_models.append(fallback_model)

        # Primary: google.genai SDK
        try:
            from google import genai
            client = genai.Client(
                api_key=self.api_key,
                http_options={"timeout": 20000},  # 20s bounded request timeout
            )
            idx = 0
            while idx < len(candidate_models):
                candidate = candidate_models[idx]
                idx += 1
                try:
                    response = client.models.generate_content(
                        model=candidate,
                        contents=[user_prompt],
                        config={"system_instruction": GROUNDED_SYSTEM_PROMPT, "temperature": 0.2},
                    )
                    raw = getattr(response, "text", response)
                    extracted = extract_text_from_gemini_response(raw)
                    return extracted, f"gemini ({candidate})"
                except Exception as ex:
                    err_str = str(ex).lower()
                    if (
                        "404" in err_str
                        or "not_found" in err_str
                        or "not available" in err_str
                        or "is not found" in err_str
                        or "503" in err_str
                        or "unavailable" in err_str
                        or "504" in err_str
                        or "deadline" in err_str
                        or "timeout" in err_str
                    ):
                        logger.warning(
                            "RAGGenerator: model candidate '%s' error (%s). Failing over...",
                            candidate,
                            str(ex),
                        )
                        if idx < len(candidate_models):
                            continue
                        try:
                            for m in client.models.list():
                                m_name = getattr(m, "name", "").replace("models/", "")
                                if "gemini" in m_name and m_name not in candidate_models:
                                    candidate_models.append(m_name)
                                    break
                        except Exception:
                            pass
                        continue
                    raise ex
        except ImportError:
            logger.info("google-genai SDK not available; falling back to langchain-google-genai.")
        except Exception as e:
            # Re-raise API and network errors so retry logic handles them without duplicate provider calls
            raise e

        # Secondary: langchain_google_genai (used only when google.genai cannot be imported)
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import SystemMessage, HumanMessage

        llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=self.api_key,
            temperature=0.2,
            timeout=25.0,
            max_retries=1,  # Strictly bounded to at most 1 internal retry
        )
        messages = [
            SystemMessage(content=GROUNDED_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        res = llm.invoke(messages)
        extracted = extract_text_from_gemini_response(getattr(res, "content", res))
        return extracted, f"gemini ({self.model_name})"

    def _call_gemini_with_retry(self, query: str, chunks: List[Dict[str, Any]]) -> Tuple[str, str]:
        """
        Calls Gemini with bounded retries (max 1 retry / 2 total attempts) and exponential backoff
        plus jitter for transient 429/503/timeout errors.
        Permanent errors (400, 401, 403, 404) immediately abort without retry.
        """
        user_prompt = self.build_context_prompt(query, chunks)
        max_attempts = 2  # 1 initial call + 1 retry

        for attempt in range(max_attempts):
            attempt_num = attempt + 1
            call_start = time.perf_counter()
            try:
                logger.info(
                    "[RAG-GEN-TIMING] Gemini generation attempt %d/%d starting (model=%s, timeout=25s)",
                    attempt_num,
                    max_attempts,
                    self.model_name,
                )
                answer, provider_label = self._call_gemini_single_attempt(user_prompt)
                call_duration_ms = int((time.perf_counter() - call_start) * 1000)
                logger.info(
                    "[RAG-GEN-TIMING] Gemini generation attempt %d succeeded in %d ms (provider=%s)",
                    attempt_num,
                    call_duration_ms,
                    provider_label,
                )
                return answer, provider_label
            except Exception as exc:
                call_duration_ms = int((time.perf_counter() - call_start) * 1000)
                is_transient = _is_transient_error(exc)
                err_summary = str(exc).strip().replace("\n", " ")[:150]

                if is_transient and attempt < max_attempts - 1:
                    delay = 1.5 * (2 ** attempt) + random.uniform(0.2, 0.6)
                    logger.warning(
                        "[RAG-GEN-TIMING] Gemini attempt %d/%d encountered transient error after %d ms: %s. Retrying in %.2fs with jitter...",
                        attempt_num,
                        max_attempts,
                        call_duration_ms,
                        err_summary,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    if not is_transient:
                        logger.error(
                            "[RAG-GEN-TIMING] Gemini attempt %d failed after %d ms with permanent error: %s. Non-retryable, aborting LLM calls.",
                            attempt_num,
                            call_duration_ms,
                            err_summary,
                        )
                    else:
                        logger.error(
                            "[RAG-GEN-TIMING] Gemini attempt %d failed after %d ms. Exhausted all %d attempts. Error: %s",
                            attempt_num,
                            call_duration_ms,
                            max_attempts,
                            err_summary,
                        )
                    raise

    def _call_gemini(self, query: str, chunks: List[Dict[str, Any]]) -> str:
        """Backward-compatible entry point for _call_gemini."""
        answer, _ = self._call_gemini_with_retry(query, chunks)
        return answer

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

