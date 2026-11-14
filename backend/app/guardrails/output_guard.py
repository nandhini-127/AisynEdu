import re
from typing import Any, Dict, List, Optional, Tuple


class OutputGuard:
    """
    Validates model generated outputs before returning to the student.
    Enforces:
    1. System prompt leakage protection.
    2. API key and secret leakage protection.
    3. Source grounding check: flags ungrounded hallucinations when document RAG was requested.
    4. Safe, non-revealing error messages.
    """

    # Signatures of system prompt / developer prompt leakage
    SYSTEM_LEAKAGE_PATTERNS = [
        re.compile(r"You\s+are\s+EduNex\s+AI(?:,\s+an\s+expert)?", re.IGNORECASE),
        re.compile(r"CRITICAL\s+SECURITY\s+DIRECTIVE:", re.IGNORECASE),
        re.compile(r"DIAGRAM_SYSTEM_PROMPT", re.IGNORECASE),
        re.compile(r"MATH_SYSTEM_PROMPT", re.IGNORECASE),
        re.compile(r"System\s+instructions:\s*You\s+must", re.IGNORECASE),
    ]

    # Secret leakage patterns (OpenAI, Gemini, JWT, AWS)
    SECRET_PATTERNS = [
        re.compile(r"AIzaSy[A-Za-z0-9_-]{33}"),
        re.compile(r"sk-[A-Za-z0-9]{32,}"),
        re.compile(r"ey[A-Za-z0-9-_]+\.ey[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+"),  # JWT token
    ]

    @classmethod
    def validate_output(
        cls,
        output_text: str,
        is_document_grounded: bool = False,
        retrieved_context: Optional[str] = None,
    ) -> Tuple[str, bool, Dict[str, Any]]:
        """
        Validates generated output.
        Returns:
            (sanitized_text, is_safe, safety_metadata)
        """
        if not output_text:
            return "No content was generated. Please try asking in a different way.", True, {"status": "empty"}

        safety_metadata: Dict[str, Any] = {
            "system_leakage_detected": False,
            "secret_leakage_detected": False,
            "grounding_score": 1.0,
            "is_grounded": True,
        }

        # 1. Check for API key / secret leakage
        sanitized = output_text
        for pattern in cls.SECRET_PATTERNS:
            if pattern.search(sanitized):
                sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
                safety_metadata["secret_leakage_detected"] = True

        # 2. Check for System Prompt leakage
        for pattern in cls.SYSTEM_LEAKAGE_PATTERNS:
            if pattern.search(sanitized):
                safety_metadata["system_leakage_detected"] = True
                # Redact system prompt echoes
                sanitized = pattern.sub("[SYSTEM_INSTRUCTION_REDACTED]", sanitized)

        # 3. Source Grounding Check for RAG Answers
        if is_document_grounded and retrieved_context:
            grounding_score, is_grounded = cls._evaluate_grounding(sanitized, retrieved_context)
            safety_metadata["grounding_score"] = grounding_score
            safety_metadata["is_grounded"] = is_grounded

            if not is_grounded:
                # Append standard grounding disclaimer if the answer claims something not in the doc
                if "not found in the uploaded documents" not in sanitized.lower() and "does not mention" not in sanitized.lower():
                    sanitized += (
                        "\n\n*Note: Part of this explanation was supplemented with general academic knowledge, "
                        "as it was not explicitly stated in your uploaded study material.*"
                    )

        return sanitized, True, safety_metadata

    @classmethod
    def _evaluate_grounding(cls, answer: str, context: str) -> Tuple[float, bool]:
        """
        Heuristic lexical overlap grounding score between answer key concepts and retrieved context.
        """
        if not context or not answer:
            return 0.5, True

        # Extract words > 4 chars from answer
        words_answer = set(w.lower() for w in re.findall(r"\b[A-Za-z]{4,}\b", answer))
        words_context = set(w.lower() for w in re.findall(r"\b[A-Za-z]{4,}\b", context))

        if not words_answer:
            return 1.0, True

        common_words = words_answer.intersection(words_context)
        overlap_ratio = len(common_words) / len(words_answer)

        # If lexical overlap is very low (< 15%), it may be answering from external knowledge
        is_grounded = overlap_ratio >= 0.15
        return round(overlap_ratio, 2), is_grounded

    @classmethod
    def safe_error_message(cls, raw_error: str) -> str:
        """
        Returns a student-friendly, non-revealing error message
        that hides stack traces, internal paths, and DB details.
        """
        lower_err = raw_error.lower()
        if "ollama" in lower_err and ("unreachable" in lower_err or "connect" in lower_err):
            return "Local Ollama service is not running at http://ollama:11434. To enable Ollama, start it via `docker compose --profile ollama up -d`, or select Gemini 2.0 in the model selector."
        if "api_key" in lower_err or "api key" in lower_err or "apikey" in lower_err:
            return "Gemini API key is not configured or invalid. Please provide a valid GOOGLE_API_KEY in your .env file."
        if "timeout" in lower_err or "timed out" in lower_err:
            return "The AI assistant request timed out while processing your study query. Please try again."
        if "rate limit" in lower_err or "quota" in lower_err or "429" in lower_err:
            return "The AI service is experiencing high load. Please wait a moment and try your question again."
        if "connection" in lower_err or "network" in lower_err:
            return "Temporary connection difficulty reaching the language model provider. Please retry."
        if "injection" in lower_err or "security" in lower_err or "prohibited" in lower_err:
            return "Your question could not be processed as it triggered safety policy guidelines. Please rephrase in an educational context."

        return "An unexpected error occurred while generating your response. Please try again or rephrase your question."

