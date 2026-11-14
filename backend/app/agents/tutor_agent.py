import json
import logging
import re
import time
from typing import Dict
from app.agents.llm_client import LLMClient
from app.agents.prompts.tutor_prompts import TUTOR_SYSTEM_PROMPT, build_tutor_prompt
from app.agents.state import AgentState
from app.agents.validator import TopicRelevanceValidator

logger = logging.getLogger("edunex.agents.tutor")


class TutorAgent:
    """
    Pedagogical Tutor Agent adapting conceptual explanations across beginner,
    intermediate, and advanced difficulty levels with real-world applications.
    Includes active topic drift validation and auto-regeneration.
    """

    @classmethod
    def _format_if_raw_json(cls, text: str) -> str:
        """If response was returned as raw JSON dictionary, formats it to clean Markdown."""
        clean = text.strip()
        if (clean.startswith("{") and clean.endswith("}")) or (clean.startswith("```json") and clean.endswith("```")):
            try:
                # Strip code fence if present
                raw_json = re.sub(r"^```json\s*", "", clean)
                raw_json = re.sub(r"\s*```$", "", raw_json)
                data = json.loads(raw_json)
                if isinstance(data, dict):
                    parts = []
                    if "overview" in data and data["overview"]:
                        parts.append(f"### Conceptual Overview\n{data['overview']}")
                    if "key_points" in data and isinstance(data["key_points"], list) and data["key_points"]:
                        parts.append("### Key Takeaways\n" + "\n".join(f"- {p}" for p in data["key_points"]))
                    if "definitions" in data and isinstance(data["definitions"], dict) and data["definitions"]:
                        parts.append("### Core Definitions\n" + "\n".join(f"- **{k}**: {v}" for k, v in data["definitions"].items()))
                    if "revision_notes" in data and isinstance(data["revision_notes"], list) and data["revision_notes"]:
                        parts.append("### Revision Notes\n" + "\n".join(f"- {n}" for n in data["revision_notes"]))
                    if parts:
                        return "\n\n".join(parts)
            except Exception:
                pass
        return text

    @classmethod
    async def execute(cls, state: AgentState) -> Dict:
        start_time = time.perf_counter()
        query = state.get("input_query", "")
        subject = state.get("subject", "General Education")
        difficulty = state.get("difficulty", "intermediate")
        provider = state.get("llm_provider", "gemini")
        model = state.get("model_name")

        # Format previous messages if present
        history_str = ""
        if "messages" in state and state["messages"]:
            history_lines = []
            for m in state["messages"][-4:]:  # last 4 turns
                speaker = "Student" if m.type == "human" else "Tutor"
                history_lines.append(f"{speaker}: {m.content}")
            history_str = "\n".join(history_lines)

        user_prompt = build_tutor_prompt(
            query=query,
            subject=subject,
            difficulty=difficulty,
            history_context=history_str,
        )

        client = LLMClient(provider=provider, model_name=model)
        response_text = await client.generate_response(
            prompt=user_prompt,
            system_prompt=TUTOR_SYSTEM_PROMPT,
            temperature=0.3,
        )

        response_text = cls._format_if_raw_json(response_text)

        # Topic Relevance & Drift Validation
        is_relevant, detected_domain, drift_reason = TopicRelevanceValidator.validate_response_relevance(
            query=query,
            response=response_text,
            subject=subject,
        )

        if not is_relevant and detected_domain:
            logger.warning(
                "Topic drift detected for query '%s' (domain=%s): %s. Triggering corrective regeneration.",
                query,
                detected_domain,
                drift_reason,
            )
            corrective_prompt = (
                f"CORRECTION: Your previous explanation drifted off-topic ({drift_reason}).\n"
                f"The student asked: '{query}' under subject '{subject}'.\n"
                f"You MUST focus EXCLUSIVELY on {detected_domain.replace('_', ' ').upper()} concepts.\n"
                f"Do NOT mention unrelated topics or other domains.\n\n"
                f"{user_prompt}"
            )
            retry_text = await client.generate_response(
                prompt=corrective_prompt,
                system_prompt=TUTOR_SYSTEM_PROMPT,
                temperature=0.1,
            )
            retry_text = cls._format_if_raw_json(retry_text)
            if retry_text and len(retry_text.strip()) > 30:
                response_text = retry_text

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        logger.info(
            "TutorAgent completed explanation (difficulty=%s, latency=%dms)",
            difficulty,
            latency_ms,
        )

        return {
            "response_text": response_text,
            "is_document_grounded": False,
            "citations": [],
            "latency_ms": latency_ms,
        }
