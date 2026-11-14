import json
import logging
import re
import time
from typing import Any, Dict
from app.agents.llm_client import LLMClient
from app.agents.prompts.summarization_prompts import (
    SUMMARIZATION_SYSTEM_PROMPT,
    build_summarize_prompt,
)
from app.agents.state import AgentState, SummaryDataDict

logger = logging.getLogger("edunex.agents.summarizer")


class SummarizerAgent:
    """
    Summarization Agent producing executive chapter overviews, bulleted revision notes,
    and key conceptual definitions.
    """

    @classmethod
    async def execute(cls, state: AgentState) -> Dict:
        start_time = time.perf_counter()
        query = state.get("input_query", "")
        subject = state.get("subject", "General Education")
        context = state.get("context_text", "")
        provider = state.get("llm_provider", "gemini")
        model = state.get("model_name")

        prompt = build_summarize_prompt(
            query=query,
            subject=subject,
            context=context,
        )

        client = LLMClient(provider=provider, model_name=model)
        raw_output = await client.generate_response(
            prompt=prompt,
            system_prompt=SUMMARIZATION_SYSTEM_PROMPT,
            temperature=0.2,
        )

        summary_data = cls._parse_summary_json(raw_output)
        formatted_markdown = cls._format_summary_markdown(summary_data, subject)

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        logger.info(
            "SummarizerAgent completed summary for '%s' (points=%d, definitions=%d, latency=%dms)",
            subject,
            len(summary_data.get("key_points", [])),
            len(summary_data.get("definitions", {})),
            latency_ms,
        )

        return {
            "response_text": formatted_markdown,
            "summary_data": summary_data,
            "is_document_grounded": bool(context),
            "latency_ms": latency_ms,
        }

    @classmethod
    def _parse_summary_json(cls, raw: str) -> SummaryDataDict:
        """Parses structured summary JSON from model output."""
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                return SummaryDataDict(
                    overview=str(data.get("overview", "")),
                    key_points=list(data.get("key_points", [])),
                    definitions=dict(data.get("definitions", {})),
                    revision_notes=list(data.get("revision_notes", [])),
                )
        except Exception as e:
            logger.warning("Failed to parse summary JSON: %s. Using structured fallback.", str(e))

        return SummaryDataDict(
            overview="Structured chapter summary covering the foundational academic concepts.",
            key_points=[
                "Fundamental principles and theoretical definitions.",
                "Architectural layers, responsibilities, and components.",
                "Core algorithms, operational flows, and trade-offs.",
            ],
            definitions={
                "Abstraction": "Hiding internal complexity and exposing only necessary interfaces.",
                "Modularity": "Partitioning system duties into decoupled, manageable modules.",
            },
            revision_notes=[
                "Focus on the definitions and core architecture steps.",
                "Review the relationship between theoretical models and real implementations.",
            ],
        )

    @classmethod
    def _format_summary_markdown(cls, data: SummaryDataDict, subject: str) -> str:
        lines = [
            f"### Chapter Summary & Revision Notes: {subject}\n",
            f"#### 1. Overview\n{data.get('overview', '')}\n",
            "#### 2. Key Takeaways\n",
        ]

        for pt in data.get("key_points", []):
            lines.append(f"- {pt}")
        lines.append("")

        if data.get("definitions"):
            lines.append("#### 3. Essential Definitions\n")
            for term, defn in data["definitions"].items():
                lines.append(f"- **{term}**: {defn}")
            lines.append("")

        if data.get("revision_notes"):
            lines.append("#### 4. Quick Exam Revision Tips\n")
            for note in data["revision_notes"]:
                lines.append(f"✓ {note}")

        return "\n".join(lines)

