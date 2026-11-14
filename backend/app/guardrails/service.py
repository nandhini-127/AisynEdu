import logging
from typing import Any, Dict, List, Optional, Tuple
from app.guardrails.input_guard import (
    EducationalDomainFilter,
    PIISanitizer,
    PromptInjectionDetector,
)
from app.guardrails.document_guard import DocumentGuard
from app.guardrails.output_guard import OutputGuard

logger = logging.getLogger("edunex.guardrails")


class ValidationResult:
    def __init__(
        self,
        is_safe: bool,
        sanitized_text: str,
        risk_category: Optional[str] = None,
        reason: Optional[str] = None,
        had_pii: bool = False,
    ):
        self.is_safe = is_safe
        self.sanitized_text = sanitized_text
        self.risk_category = risk_category
        self.reason = reason
        self.had_pii = had_pii

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_safe": self.is_safe,
            "sanitized_text": self.sanitized_text,
            "risk_category": self.risk_category,
            "reason": self.reason,
            "had_pii": self.had_pii,
        }


class GuardrailsService:
    """
    Production-grade AI safety orchestration service for EduNex AI.
    Enforces:
    1. Input validation & prompt injection detection.
    2. Educational scope boundaries.
    3. PII masking.
    4. Document untrusted context sandboxing.
    5. Output validation & hallucination mitigation.
    """

    @classmethod
    def validate_user_query(cls, query: str) -> ValidationResult:
        """
        Validates and sanitizes student input queries.
        """
        if not query or not query.strip():
            return ValidationResult(
                is_safe=False,
                sanitized_text="",
                risk_category="EMPTY_INPUT",
                reason="Query cannot be empty.",
            )

        # 1. Prompt Injection Scanning
        is_injection, matched = PromptInjectionDetector.scan_for_injection(query)
        if is_injection:
            logger.warning("Prompt injection attempt detected: matched pattern '%s'", matched)
            return ValidationResult(
                is_safe=False,
                sanitized_text=query,
                risk_category="PROMPT_INJECTION",
                reason="Adversarial instruction or system override attempt detected.",
            )

        # 2. Educational Scope Restrictions
        is_in_scope, scope_violation = EducationalDomainFilter.check_educational_scope(query)
        if not is_in_scope:
            logger.warning("Prohibited educational scope violation: %s", scope_violation)
            return ValidationResult(
                is_safe=False,
                sanitized_text=query,
                risk_category="OUT_OF_SCOPE",
                reason=scope_violation or "Query falls outside educational scope.",
            )

        # 3. PII Redaction
        sanitized_query, had_pii = PIISanitizer.sanitize_pii(query)
        if had_pii:
            logger.info("PII detected and redacted from student input.")

        return ValidationResult(
            is_safe=True,
            sanitized_text=sanitized_query,
            had_pii=had_pii,
        )

    @classmethod
    def sanitize_and_sandbox_documents(cls, chunks: List[Dict[str, Any]]) -> str:
        """
        Formats retrieved vector chunks into an isolated untrusted data context block.
        """
        return DocumentGuard.format_untrusted_context(chunks)

    @classmethod
    def sanitize_document_text(cls, text: str) -> str:
        """
        Sanitizes text extracted from documents before indexing in ChromaDB.
        """
        return DocumentGuard.sanitize_raw_text(text)

    @classmethod
    def validate_assistant_output(
        cls,
        output_text: str,
        is_document_grounded: bool = False,
        retrieved_context: Optional[str] = None,
    ) -> Tuple[str, bool, Dict[str, Any]]:
        """
        Validates model output to ensure no secrets or system instructions leak,
        and adds grounding disclaimers where appropriate.
        """
        return OutputGuard.validate_output(
            output_text=output_text,
            is_document_grounded=is_document_grounded,
            retrieved_context=retrieved_context,
        )

    @classmethod
    def get_safe_error(cls, exc: Exception) -> str:
        """
        Maps raw exceptions to safe, student-friendly messages.
        """
        return OutputGuard.safe_error_message(str(exc))

