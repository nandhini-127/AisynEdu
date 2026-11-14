import json
import logging
import re
import time
from typing import Any, Dict, List
from app.agents.llm_client import LLMClient
from app.agents.prompts.quiz_prompts import QUIZ_SYSTEM_PROMPT, build_quiz_prompt
from app.agents.state import AgentState, QuizQuestionDict

logger = logging.getLogger("edunex.agents.quiz")


class QuizAgent:
    """
    Assessment Agent generating 4-option MCQs from study materials or academic topics,
    storing correct answers separately, and providing pedagogical explanations.
    """

    @classmethod
    async def execute(cls, state: AgentState) -> Dict:
        start_time = time.perf_counter()
        query = state.get("input_query", "")
        subject = state.get("subject", "General Education")
        difficulty = state.get("difficulty", "intermediate")
        context = state.get("context_text", "")
        provider = state.get("llm_provider", "gemini")
        model = state.get("model_name")

        prompt = build_quiz_prompt(
            query=query,
            subject=subject,
            difficulty=difficulty,
            context=context,
            count=3,
        )

        client = LLMClient(provider=provider, model_name=model)
        raw_output = await client.generate_response(
            prompt=prompt,
            system_prompt=QUIZ_SYSTEM_PROMPT,
            temperature=0.3,
        )

        quiz_questions = cls._parse_quiz_json(raw_output, difficulty)

        # Build readable student presentation
        formatted_text = cls._format_quiz_markdown(quiz_questions, subject, difficulty)

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        logger.info(
            "QuizAgent generated %d questions (difficulty=%s, latency=%dms)",
            len(quiz_questions),
            difficulty,
            latency_ms,
        )

        return {
            "response_text": formatted_text,
            "quiz_data": quiz_questions,
            "is_document_grounded": bool(context),
            "latency_ms": latency_ms,
        }

    @classmethod
    def _parse_quiz_json(cls, raw: str, difficulty: str) -> List[QuizQuestionDict]:
        """Extracts JSON list from model response."""
        try:
            # Look for JSON array in output
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                questions: List[QuizQuestionDict] = []
                for idx, item in enumerate(data, 1):
                    questions.append(
                        QuizQuestionDict(
                            id=int(item.get("id", idx)),
                            question=str(item.get("question", "")),
                            options=list(item.get("options", [])),
                            correct_answer=str(item.get("correct_answer", "A")).upper().strip()[:1],
                            explanation=str(item.get("explanation", "")),
                            difficulty=str(item.get("difficulty", difficulty)),
                        )
                    )
                return questions
        except Exception as e:
            logger.warning("Failed to parse JSON quiz questions: %s. Using default structure.", str(e))

        # Fallback question if JSON parsing fails
        return [
            QuizQuestionDict(
                id=1,
                question="Which protocol operates at Layer 4 of the OSI model to provide reliable delivery?",
                options=[
                    "A) Internet Protocol (IP)",
                    "B) Transmission Control Protocol (TCP)",
                    "C) User Datagram Protocol (UDP)",
                    "D) Hypertext Transfer Protocol (HTTP)",
                ],
                correct_answer="B",
                explanation="TCP operates at Layer 4 (Transport) and guarantees in-order, reliable delivery via the 3-way handshake.",
                difficulty=difficulty,
            )
        ]

    @classmethod
    def _format_quiz_markdown(cls, questions: List[QuizQuestionDict], subject: str, difficulty: str) -> str:
        """Formats the questions and options for student view, concealing answers until submission."""
        lines = [
            f"### Practice Quiz: {subject} ({difficulty.capitalize()} Level)\n",
            "Test your knowledge! Reply with your chosen options (e.g. `1: B, 2: C`).\n",
        ]

        for q in questions:
            lines.append(f"**Question {q['id']}:** {q['question']}")
            for opt in q["options"]:
                lines.append(f"  - {opt}")
            lines.append("")

        lines.append("<details>")
        lines.append("<summary><b>Click to View Answers & Explanations</b></summary>\n")
        for q in questions:
            lines.append(f"**Question {q['id']} Answer:** **{q['correct_answer']}**")
            lines.append(f"*{q['explanation']}*\n")
        lines.append("</details>")

        return "\n".join(lines)

