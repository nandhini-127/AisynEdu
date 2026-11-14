import re
from typing import List, Optional, Tuple


class PromptInjectionDetector:
    """
    Detects adversarial prompt injections, instruction overrides,
    role-playing jailbreaks, and system prompt extraction attacks.
    """

    # Direct override patterns
    INJECTION_PATTERNS = [
        r"ignore\s+(?:all\s+)?(?:(?:previous|prior|above|system)\s+)*(?:instructions|prompts|directives|rules)",
        r"disregard\s+(?:all\s+)?(?:(?:previous|prior|above|system)\s+)*(?:instructions|prompts|directives|rules)",
        r"(?:reveal|print|show|repeat|display|output)\s+(?:the\s+)?(?:system\s+prompt|developer\s+instructions|initial\s+prompt)",
        r"what\s+(?:are|is)\s+your\s+(?:system\s+prompt|initial\s+instructions|developer\s+prompt)",
        r"(?:act\s+as|you\s+are\s+now)\s+(?:dan|unrestricted|jailbreak|chaos\s*gpt|an\s+evil\s+ai)",
        r"bypass\s+(?:all\s+)?(?:safety|content|ethical|system)\s+(?:filters|guidelines|guardrails|policies)",
        r"do\s+anything\s+now",
        r"simulate\s+(?:a\s+)?(?:mode|persona)\s+without\s+(?:rules|filters|boundaries)",
        r"---+\s*(?:begin|start|end)\s*(?:system|admin|override)\s*---+",
        r"\[system\s*override\]",
        r"<<sys>>",
        r"\[INST\]",
    ]

    _compiled_injection = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

    @classmethod
    def scan_for_injection(cls, text: str) -> Tuple[bool, Optional[str]]:
        """
        Scans text for prompt injection patterns.
        Returns (is_injected, matched_pattern).
        """
        if not text:
            return False, None

        normalized = text.strip()
        for pattern in cls._compiled_injection:
            match = pattern.search(normalized)
            if match:
                return True, match.group(0)

        return False, None


class EducationalDomainFilter:
    """
    Restricts assistant queries to educational, academic, and learning domains.
    Rejects malicious code execution, illegal weapon guides, and dangerous topics.
    """

    HARMFUL_PATTERNS = [
        r"(?:how\s+to\s+)?(?:build|make|create|synthesize)\s+(?:an?\s+)?(?:bomb|explosive|weapon|poison|toxin|meth)",
        r"(?:write|generate|create)\s+(?:an?\s+)?(?:malware|ransomware|keylogger|ddos\s+script|exploit\s+payload)",
        r"(?:how\s+to\s+)?(?:hack|infiltrate|crack|bypass\s+auth)\s+(?:into\s+)?(?:an?\s+)?(?:bank|government|server|wifi)",
        r"(?:how\s+to\s+)?(?:commit\s+)?(?:[a-zA-Z]+\s+)?(?:fraud|identity\s+theft|money\s+laundering)",
    ]

    _compiled_harmful = [re.compile(p, re.IGNORECASE) for p in HARMFUL_PATTERNS]

    @classmethod
    def check_educational_scope(cls, text: str) -> Tuple[bool, Optional[str]]:
        """
        Returns (is_acceptable, violation_reason).
        """
        if not text:
            return True, None

        for pattern in cls._compiled_harmful:
            match = pattern.search(text)
            if match:
                return False, f"Query falls outside educational scope: prohibited topic detected ({match.group(0)})."

        return True, None


class PIISanitizer:
    """
    Detects and redacts sensitive Personally Identifiable Information (PII)
    such as Social Security Numbers, Credit Card Numbers, and API Keys.
    """

    # Credit Cards (13-16 digits with dashes or spaces)
    CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
    # US SSN (3-2-4 digits)
    SSN_PATTERN = re.compile(r"\b\d{3}[-\s]\d{2}[-\s]\d{4}\b")
    # Standard API Key formats (sk-..., AIzaSy..., edunex_secret_...)
    API_KEY_PATTERN = re.compile(r"\b(?:sk-[a-zA-Z0-9]{32,}|AIzaSy[a-zA-Z0-9_-]{33}|ghp_[a-zA-Z0-9]{36})\b")
    # Email pattern
    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")

    @classmethod
    def sanitize_pii(cls, text: str) -> Tuple[str, bool]:
        """
        Redacts sensitive tokens from user input, returning (sanitized_text, had_pii).
        """
        if not text:
            return text, False

        had_pii = False
        sanitized = text

        if cls.CREDIT_CARD_PATTERN.search(sanitized):
            sanitized = cls.CREDIT_CARD_PATTERN.sub("[REDACTED_CREDIT_CARD]", sanitized)
            had_pii = True

        if cls.SSN_PATTERN.search(sanitized):
            sanitized = cls.SSN_PATTERN.sub("[REDACTED_SSN]", sanitized)
            had_pii = True

        if cls.API_KEY_PATTERN.search(sanitized):
            sanitized = cls.API_KEY_PATTERN.sub("[REDACTED_API_KEY]", sanitized)
            had_pii = True

        return sanitized, had_pii
