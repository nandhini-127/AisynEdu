import logging
import re
import time
from typing import List, Optional
from uuid import UUID

from app.rag.service import RAGService
from app.schemas.rag import RAGEvalQuestion, RAGEvalReport, RAGEvalResult

logger = logging.getLogger("edunex.rag.evaluator")


class RAGEvaluator:
    """
    Evaluates retrieval relevance, answer faithfulness, citation accuracy,
    and end-to-end latency for EduNex AI RAG pipeline.
    """

    def __init__(self, rag_service: RAGService):
        self.rag_service = rag_service

    @staticmethod
    def calculate_retrieval_relevance(
        retrieved_texts: List[str],
        keywords: List[str],
        expected_answer: str,
    ) -> float:
        """
        Calculates retrieval relevance score [0.0 - 1.0] based on keyword matching
        and term overlap between retrieved context and expected knowledge.
        """
        if not retrieved_texts:
            return 0.0

        combined_context = " ".join(retrieved_texts).lower()

        # Keyword matching
        if keywords:
            matched_keywords = sum(1 for kw in keywords if kw.lower() in combined_context)
            keyword_score = matched_keywords / len(keywords)
        else:
            keyword_score = 0.5

        # Term overlap with expected answer
        expected_words = set(re.findall(r"\w{4,}", expected_answer.lower()))
        if expected_words:
            matched_terms = sum(1 for word in expected_words if word in combined_context)
            term_score = matched_terms / len(expected_words)
        else:
            term_score = 1.0

        return round(0.5 * keyword_score + 0.5 * term_score, 3)

    @staticmethod
    def calculate_faithfulness(
        generated_answer: str,
        retrieved_texts: List[str],
    ) -> float:
        """
        Calculates answer faithfulness [0.0 - 1.0].
        A faithful answer only contains claims that can be traced back to the retrieved context chunks.
        """
        if not retrieved_texts:
            if "do not contain information" in generated_answer.lower():
                return 1.0  # Perfect faithfulness: correctly abstained when context missing
            return 0.0

        combined_context = " ".join(retrieved_texts).lower()
        answer_sentences = [
            s.strip() for s in re.split(r"[.!?]\s+", generated_answer) if len(s.strip()) > 15
        ]

        if not answer_sentences:
            return 1.0

        supported_sentences = 0
        for sentence in answer_sentences:
            # Clean citations [Document: ..., Page: ...]
            clean_sentence = re.sub(r"\[Document:.*?\]", "", sentence).strip().lower()
            words = set(re.findall(r"\w{4,}", clean_sentence))
            if not words:
                supported_sentences += 1
                continue

            # Check overlap fraction of words in retrieved context
            overlap = sum(1 for w in words if w in combined_context) / len(words)
            if overlap >= 0.6:  # 60% or more content words present in context
                supported_sentences += 1

        return round(supported_sentences / len(answer_sentences), 3)

    async def evaluate_question(
        self,
        user_id: UUID,
        eval_q: RAGEvalQuestion,
        doc_ids: Optional[List[UUID]] = None,
    ) -> RAGEvalResult:
        """Evaluates a single question against the RAG pipeline."""
        start_time = time.perf_counter()

        response = await self.rag_service.query(
            user_id=user_id,
            query_text=eval_q.question,
            doc_ids=doc_ids,
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        retrieved_texts = [c.text_snippet for c in response.citations]

        # Calculate metrics
        relevance = self.calculate_retrieval_relevance(
            retrieved_texts=retrieved_texts,
            keywords=eval_q.keywords,
            expected_answer=eval_q.expected_answer,
        )

        faithfulness = self.calculate_faithfulness(
            generated_answer=response.answer,
            retrieved_texts=retrieved_texts,
        )

        # Check citation presence
        citation_valid = (
            len(response.citations) > 0
            if response.context_available
            else True
        )

        passed = relevance >= 0.3 and faithfulness >= 0.5 and citation_valid

        return RAGEvalResult(
            question=eval_q.question,
            expected_answer=eval_q.expected_answer,
            generated_answer=response.answer,
            citations=response.citations,
            retrieval_relevance=relevance,
            answer_faithfulness=faithfulness,
            latency_ms=latency_ms,
            passed=passed,
        )

    async def run_evaluation_suite(
        self,
        user_id: UUID,
        test_questions: List[RAGEvalQuestion],
        doc_ids: Optional[List[UUID]] = None,
    ) -> RAGEvalReport:
        """Runs the entire evaluation suite and produces an aggregated benchmark report."""
        results: List[RAGEvalResult] = []

        for q in test_questions:
            res = await self.evaluate_question(user_id=user_id, eval_q=q, doc_ids=doc_ids)
            results.append(res)

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        mean_relevance = round(sum(r.retrieval_relevance for r in results) / total, 3) if total > 0 else 0.0
        mean_faithfulness = round(sum(r.answer_faithfulness for r in results) / total, 3) if total > 0 else 0.0
        mean_latency = round(sum(r.latency_ms for r in results) / total, 1) if total > 0 else 0.0

        return RAGEvalReport(
            total_questions=total,
            passed_count=passed,
            mean_retrieval_relevance=mean_relevance,
            mean_answer_faithfulness=mean_faithfulness,
            mean_latency_ms=mean_latency,
            results=results,
        )
