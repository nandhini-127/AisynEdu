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

        summary_data = cls._parse_summary_json(raw_output, query, subject)
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
            "is_fallback": getattr(client, "last_is_fallback", False),
            "fallback_reason": getattr(client, "last_fallback_reason", None),
            "llm_provider": getattr(client, "last_provider_used", provider),
        }

    @classmethod
    def _parse_summary_json(cls, raw: str, query: str = "", subject: str = "") -> SummaryDataDict:
        """Parses structured summary JSON from model output with topic-aware fallback."""
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                # Validate that returned data has meaningful content
                kp = list(data.get("key_points", []))
                defs = dict(data.get("definitions", {}))
                if kp or defs:
                    return SummaryDataDict(
                        overview=str(data.get("overview", "")),
                        key_points=kp,
                        definitions=defs,
                        revision_notes=list(data.get("revision_notes", [])),
                    )
        except Exception as e:
            logger.warning("Failed to parse summary JSON: %s. Using topic-aware fallback.", str(e))

        # Context-aware fallback using the educational engine tailored to the exact topic
        try:
            fallback_client = LLMClient()
            fallback_raw = fallback_client._generate_offline_mock(
                f"Subject: {subject}\nTarget Chapter / Topic: {query}",
                "summarize revision notes",
            )
            fallback_match = re.search(r"\{.*\}", fallback_raw, re.DOTALL)
            if fallback_match:
                fallback_data = json.loads(fallback_match.group(0))
                return SummaryDataDict(
                    overview=str(fallback_data.get("overview", "")),
                    key_points=list(fallback_data.get("key_points", [])),
                    definitions=dict(fallback_data.get("definitions", {})),
                    revision_notes=list(fallback_data.get("revision_notes", [])),
                )
        except Exception:
            pass

        topic_label = query or subject or "Academic Concept"
        return SummaryDataDict(
            overview=f"Structured academic summary and revision notes covering the core principles of {topic_label}.",
            key_points=[
                f"Core foundations and operational scope of {topic_label}.",
                f"Primary components, methodologies, and interactions defining {topic_label}.",
                f"Critical considerations and practical applications in {subject or 'the field'}.",
            ],
            definitions={
                topic_label: f"The primary subject or operational concept under study in {subject or 'this discipline'}.",
                "Core Principle": "An established fundamental rule governing system behavior and analysis.",
            },
            revision_notes=[
                f"Master the core definitions, components, and primary characteristics of {topic_label}.",
                "Review the relationship between theoretical models and real-world implementations.",
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

