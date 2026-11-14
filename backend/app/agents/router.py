import json
import logging
import re
from typing import Dict, Tuple

from app.agents.llm_client import LLMClient
from app.agents.prompts.router_prompts import ROUTER_SYSTEM_PROMPT, build_router_prompt
from app.agents.state import AgentState

logger = logging.getLogger("edunex.agents.router")

VALID_INTENTS = {"tutor", "rag", "quiz", "summarize", "learning_assistant"}


class RequestRouter:
    """
    Central request router classifying student queries into specialized agent capabilities.
    Supports both explicit overrides and semantic auto-classification.
    """

    @classmethod
    async def route(cls, state: AgentState) -> Dict:
        requested = (state.get("requested_intent") or "auto").lower().strip()
        query = state.get("input_query", "")
        subject = state.get("subject", "General Education")
        has_docs = bool(state.get("document_ids"))

        # Normalize aliases so frontend can send 'summary' or 'learning_path' freely
        _ALIASES = {
            "summary": "summarize",
            "learning_path": "learning_assistant",
            "notes": "summarize",
            "summarise": "summarize",
        }
        requested = _ALIASES.get(requested, requested)

        # 1. Direct explicit routing override
        if requested in VALID_INTENTS:
            logger.info("Direct intent routing override applied: '%s'", requested)
            return {
                "resolved_intent": requested,
                "router_reasoning": f"Explicitly requested by student: {requested}",
            }

        # 2. Rule-based heuristic fast path for clear keywords
        fast_intent, reasoning = cls._heuristic_classify(query, has_docs)
        if fast_intent:
            logger.info("Fast-path heuristic routed to '%s': %s", fast_intent, reasoning)
            return {
                "resolved_intent": fast_intent,
                "router_reasoning": reasoning,
            }

        # 3. LLM semantic classification for ambiguous queries
        provider = state.get("llm_provider", "gemini")
        model = state.get("model_name")
        client = LLMClient(provider=provider, model_name=model)

        prompt = build_router_prompt(query=query, subject=subject, has_documents=has_docs)
        try:
            raw = await client.generate_response(
                prompt=prompt,
                system_prompt=ROUTER_SYSTEM_PROMPT,
                temperature=0.0,
            )
            intent, reason = cls._parse_router_json(raw, fallback="tutor")
            return {
                "resolved_intent": intent,
                "router_reasoning": reason,
            }
        except Exception as e:
            logger.warning("Semantic router fallback to 'tutor': %s", str(e))
            return {
                "resolved_intent": "rag" if has_docs else "tutor",
                "router_reasoning": "Fallback routing based on document availability.",
            }

    @classmethod
    def _heuristic_classify(cls, query: str, has_docs: bool) -> Tuple[str, str]:
        """Fast-path classification based on deterministic keyword matching."""
        q = query.lower()

        # Quiz patterns
        if any(w in q for w in ["quiz", "mcq", "multiple choice", "test me", "practice questions"]):
            return "quiz", "Matched quiz generation keywords."

        # Summarization patterns
        if any(w in q for w in ["summarize", "summary", "revision notes", "outline chapter", "key points of"]):
            return "summarize", "Matched summarization keywords."

        # Learning Assistant / Progress patterns
        if any(w in q for w in ["what should i study", "recommend", "my progress", "what to review", "study plan"]):
            return "learning_assistant", "Matched learning assistant and coaching keywords."

        # RAG patterns (explicit reference to uploaded documents)
        if has_docs and any(w in q for w in ["document", "pdf", "file", "uploaded", "notes say", "in my notes", "from the material", "page", "textbook"]):
            return "rag", "Matched uploaded document references."

        # General conceptual inquiries default to tutor
        return "tutor", "Defaulted to conceptual tutor breakdown."

    @classmethod
    def _parse_router_json(cls, raw: str, fallback: str = "tutor") -> Tuple[str, str]:
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                intent = str(data.get("intent", fallback)).lower().strip()
                if intent in VALID_INTENTS:
                    return intent, str(data.get("reasoning", "Classified by LLM router"))
        except Exception:
            pass
        return fallback, "Default router assignment."

