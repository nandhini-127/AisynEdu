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

        quiz_questions = cls._parse_quiz_json(raw_output, difficulty, query, subject)

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
            "is_fallback": getattr(client, "last_is_fallback", False),
            "fallback_reason": getattr(client, "last_fallback_reason", None),
            "llm_provider": getattr(client, "last_provider_used", provider),
        }

    @classmethod
    def _parse_quiz_json(cls, raw: str, difficulty: str, query: str = "", subject: str = "") -> List[QuizQuestionDict]:
        """Extracts JSON list from model response, sanitizes instruction leakage, and falls back contextually."""
        try:
            # Look for JSON array in output
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                questions: List[QuizQuestionDict] = []
                for idx, item in enumerate(data, 1):
                    q_text = str(item.get("question", "")).strip()
                    # Sanitize prompt instruction phrases if leaked into question
                    instruction_phrases = [
                        "generate a beginner difficulty quiz",
                        "generate an intermediate difficulty quiz",
                        "generate an advanced difficulty quiz",
                        "generate a intermediate difficulty quiz",
                        "generate a advanced difficulty quiz",
                        "multiple choice questions on the topic",
                        "provide 4 clear options",
                        "return valid json only",
                    ]
                    for ip in instruction_phrases:
                        if ip in q_text.lower():
                            q_text = re.sub(rf"(?i){re.escape(ip)}.*?:?\s*", "", q_text).strip()

                    raw_options = list(item.get("options", []))
                    clean_options: List[str] = []
                    prefixes = ["A) ", "B) ", "C) ", "D) "]
                    for o_idx, opt in enumerate(raw_options[:4]):
                        opt_str = str(opt).strip()
                        # If option already has prefix, normalize it; otherwise add prefix
                        if re.match(r"^[A-Da-d][).\s]", opt_str):
                            opt_clean = re.sub(r"^[A-Da-d][).\s]+\s*", "", opt_str).strip()
                            clean_options.append(f"{prefixes[o_idx]}{opt_clean}")
                        else:
                            clean_options.append(f"{prefixes[o_idx]}{opt_str}")

                    # Only accept questions with at least 4 valid options and non-empty text
                    if len(clean_options) == 4 and len(q_text) >= 10:
                        questions.append(
                            QuizQuestionDict(
                                id=int(item.get("id", idx)),
                                question=q_text,
                                options=clean_options,
                                correct_answer=str(item.get("correct_answer", "A")).upper().strip()[:1],
                                explanation=str(item.get("explanation", "")),
                                difficulty=str(item.get("difficulty", difficulty)),
                            )
                        )
                if questions:
                    return questions
        except Exception as e:
            logger.warning("Failed to parse JSON quiz questions: %s.", str(e))

        # Check if model responded in structured Markdown instead of raw JSON
        md_questions = cls._parse_markdown_questions(raw, difficulty)
        if md_questions:
            return md_questions

        # Context-aware fallback using the educational engine tailored to the exact topic
        try:
            fallback_client = LLMClient()
            fallback_raw = fallback_client._generate_offline_mock(
                f"Subject: {subject}\nTarget Topic: {query}",
                "quiz multiple choice",
            )
            fallback_match = re.search(r"\[.*\]", fallback_raw, re.DOTALL)
            if fallback_match:
                fallback_data = json.loads(fallback_match.group(0))
                return [
                    QuizQuestionDict(
                        id=int(item.get("id", idx)),
                        question=str(item.get("question", "")),
                        options=list(item.get("options", [])),
                        correct_answer=str(item.get("correct_answer", "A")).upper().strip()[:1],
                        explanation=str(item.get("explanation", "")),
                        difficulty=str(item.get("difficulty", difficulty)),
                    )
                    for idx, item in enumerate(fallback_data, 1)
                ]
        except Exception:
            pass

        # Final resilient baseline tailored specifically to the requested topic
        topic_label = query or subject or "Academic Concept"
        return [
            QuizQuestionDict(
                id=1,
                question=f"Which statement best characterizes the primary scope, formal definition, or significance of {topic_label}?",
                options=[
                    f"A) It establishes foundational principles, operational frameworks, and standardized methods in {topic_label}.",
                    f"B) It represents an unverified anecdotal concept without recognized curriculum documentation.",
                    f"C) It asserts that {topic_label} has no systematic methods or practical applications.",
                    f"D) It restricts study exclusively to subjective speculation without empirical validation.",
                ],
                correct_answer="A",
                explanation=f"Understanding {topic_label} begins with mastering its standard definition, foundational axioms, and primary scope of study.",
                difficulty=difficulty,
            )
        ]

    @classmethod
    def _parse_markdown_questions(cls, raw: str, difficulty: str) -> List[QuizQuestionDict]:
        """Parses questions formatted as Markdown text (**Question X:** ... A) ... B) ...)."""
        questions: List[QuizQuestionDict] = []
        try:
            # Parse answers from <details> if present
            answers_map: Dict[int, Dict[str, str]] = {}
            ans_matches = re.finditer(
                r"\*\*Question\s*(\d+)\s*Answer:\*\*\s*\*\*([A-Da-d])\*\*(?:[\s\S]*?\*([^*]+)\*)?",
                raw,
            )
            for m in ans_matches:
                q_id = int(m.group(1))
                answers_map[q_id] = {
                    "answer": m.group(2).upper(),
                    "explanation": (m.group(3) or "").strip(),
                }

            # Split into question blocks
            blocks = re.split(r"\*\*(?:Question\s*\d+|Q\d+)[:.]?\*\*", raw, flags=re.IGNORECASE)
            for idx, block in enumerate(blocks[1:], 1):
                lines = [line.strip() for line in block.strip().split("\n") if line.strip()]
                if not lines:
                    continue
                q_text = re.sub(r"^[:\s-]+", "", lines[0]).strip()
                raw_options: List[str] = []
                for line in lines[1:]:
                    opt_match = re.match(r"^[-*]?\s*([A-Da-d])[).]\s*(.*)$", line)
                    if opt_match:
                        raw_options.append(f"{opt_match.group(1).upper()}) {opt_match.group(2).strip()}")

                if len(raw_options) >= 2 and len(q_text) >= 10:
                    ans_info = answers_map.get(idx, {})
                    questions.append(
                        QuizQuestionDict(
                            id=idx,
                            question=q_text,
                            options=raw_options[:4],
                            correct_answer=ans_info.get("answer", "A"),
                            explanation=ans_info.get("explanation", f"Pedagogical explanation for question {idx}."),
                            difficulty=difficulty,
                        )
                    )
        except Exception:
            pass
        return questions

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

