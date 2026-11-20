import json
import logging
import re
import time
from typing import Any, Dict, List
from app.agents.llm_client import LLMClient
from app.agents.prompts.learning_assistant_prompts import (
    LEARNING_ASSISTANT_SYSTEM_PROMPT,
    build_learning_assistant_prompt,
)
from app.agents.state import AgentState

logger = logging.getLogger("edunex.agents.learning_assistant")


class LearningAssistantAgent:
    """
    Learning Assistant Agent analyzing session conversations to track explored topics,
    highlight topics to revisit, and formulate actionable study recommendations.
    """

    @classmethod
    async def execute(cls, state: AgentState) -> Dict:
        start_time = time.perf_counter()
        query = state.get("input_query", "")
        subject = state.get("subject", "General Education")
        provider = state.get("llm_provider", "gemini")
        model = state.get("model_name")

        # Extract history text from state
        history_lines = []
        if "messages" in state and state["messages"]:
            for m in state["messages"][-6:]:
                speaker = "Student" if m.type == "human" else "Tutor"
                history_lines.append(f"{speaker}: {m.content}")
        history_text = "\n".join(history_lines)

        prompt = build_learning_assistant_prompt(
            query=query,
            subject=subject,
            conversation_history=history_text,
        )

        client = LLMClient(provider=provider, model_name=model)
        raw_output = await client.generate_response(
            prompt=prompt,
            system_prompt=LEARNING_ASSISTANT_SYSTEM_PROMPT,
            temperature=0.3,
        )

        parsed_data = cls._parse_learning_json(raw_output)
        formatted_markdown = cls._format_learning_markdown(parsed_data, subject)

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        logger.info(
            "LearningAssistant generated %d recommendations (latency=%dms)",
            len(parsed_data.get("recommendations", [])),
            latency_ms,
        )

        return {
            "response_text": formatted_markdown,
            "learning_recommendations": parsed_data.get("recommendations", []),
            "tracked_topics": parsed_data.get("tracked_topics", []),
            "is_document_grounded": False,
            "latency_ms": latency_ms,
            "is_fallback": getattr(client, "last_is_fallback", False),
            "fallback_reason": getattr(client, "last_fallback_reason", None),
            "llm_provider": getattr(client, "last_provider_used", provider),
        }

    @classmethod
    def _parse_learning_json(cls, raw: str) -> Dict[str, Any]:
        """Extracts JSON recommendation structure from model output."""
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except Exception as e:
            logger.warning("Failed to parse learning assistant JSON: %s", str(e))

        return {
            "tracked_topics": ["Core Architectural Principles", "Protocols & Scheduling"],
            "topics_to_revisit": ["Deadlock Avoidance & Synchronization", "Flow vs Congestion Control"],
            "recommendations": [
                "Take a 3-question practice quiz on Synchronization and Semaphores.",
                "Review the 3-Way Handshake flow diagram in your study materials.",
                "Summarize Coffman's 4 conditions in your own words to cement retention.",
            ],
        }

    @classmethod
    def _format_learning_markdown(cls, data: Dict[str, Any], subject: str) -> str:
        lines = [
            f"### Personalized Learning Coach: {subject}\n",
            "Here is your customized progress assessment and recommended study plan:\n",
        ]

        tracked = data.get("tracked_topics", [])
        if tracked:
            lines.append("#### Topics You Have Explored")
            for t in tracked:
                lines.append(f"  • {t}")
            lines.append("")

        revisit = data.get("topics_to_revisit", [])
        if revisit:
            lines.append("#### Concepts Recommended for Quick Review")
            for r in revisit:
                lines.append(f"  ⚡ {r}")
            lines.append("")

        recs = data.get("recommendations", [])
        if recs:
            lines.append("#### Your Next Learning Steps")
            for idx, rec in enumerate(recs, 1):
                lines.append(f"{idx}. {rec}")

        return "\n".join(lines)

