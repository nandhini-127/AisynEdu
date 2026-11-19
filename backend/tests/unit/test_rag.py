import os
import uuid
from pathlib import Path
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.entities import Document, User
from app.rag.chunker import DocumentChunk, DocumentChunker
from app.rag.embeddings import SentenceTransformerEmbeddings
from app.rag.evaluator import RAGEvaluator
from app.rag.extractor import (
    CorruptedPDFError,
    EmptyPDFError,
    PDFExtractor,
)
from app.rag.generator import (
    RAGGenerator,
    _is_transient_error,
    extract_text_from_gemini_response,
)
from app.rag.service import (
    DuplicateDocumentError,
    RAGService,
)
from app.rag.vectorstore import ChromaVectorStore
from app.schemas.rag import RAGEvalQuestion

SAMPLE_PDFS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "sample_pdfs"


@pytest_asyncio.fixture
async def sample_user(db_session: AsyncSession) -> User:
    """Creates a sample student user in the test database."""
    user = User(
        id=uuid.uuid4(),
        email=f"student.rag.{uuid.uuid4().hex[:6]}@edunex.ai",
        name="RAG Test Student",
        hashed_password="hashed_secure_password",
        role="student",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestPDFExtractor:
    def test_extract_valid_pdf(self):
        pdf_path = SAMPLE_PDFS_DIR / "computer_networks.pdf"
        assert pdf_path.exists(), f"Sample PDF not found at {pdf_path}"

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        extracted = PDFExtractor.extract_text(pdf_bytes, "computer_networks.pdf")
        assert extracted.page_count == 3
        assert extracted.total_characters > 200
        assert len(extracted.sha256_hash) == 64
        assert "OSI" in extracted.pages[0][1]

    def test_extract_empty_pdf(self):
        with pytest.raises(EmptyPDFError):
            PDFExtractor.extract_text(b"", "empty.pdf")

    def test_extract_corrupted_pdf(self):
        corrupted_bytes = b"This is not a real PDF document at all."
        with pytest.raises(CorruptedPDFError):
            PDFExtractor.extract_text(corrupted_bytes, "corrupted.pdf")


class TestDocumentChunker:
    def test_chunking_preserves_page_numbers_and_metadata(self):
        chunker = DocumentChunker(chunk_size=300, chunk_overlap=30)
        pages = [
            (1, "Page 1 intro. The OSI model has seven layers: Physical, Data Link, Network, Transport, Session, Presentation, Application."),
            (2, "Page 2 transport. TCP is connection-oriented and reliable. UDP is connectionless and low-latency."),
        ]
        doc_id = uuid.uuid4()
        user_id = uuid.uuid4()

        chunks = chunker.split_pages(
            pages=pages,
            doc_id=doc_id,
            user_id=user_id,
            filename="sample.pdf",
            subject="Computer Science",
        )

        assert len(chunks) >= 2
        # Check first chunk metadata
        assert chunks[0].doc_id == str(doc_id)
        assert chunks[0].user_id == str(user_id)
        assert chunks[0].page_number == 1
        assert chunks[0].metadata["filename"] == "sample.pdf"
        assert "OSI" in chunks[0].text

        # Verify page 2 is represented
        p2_chunks = [c for c in chunks if c.page_number == 2]
        assert len(p2_chunks) >= 1
        assert "TCP" in p2_chunks[0].text


class TestSentenceTransformerEmbeddings:
    def test_embedding_generation_and_shape(self):
        embedder = SentenceTransformerEmbeddings.get_instance()
        texts = ["What is the TCP 3-way handshake?", "Virtual memory and paging."]
        vectors = embedder.embed_documents(texts)

        assert len(vectors) == 2
        assert len(vectors[0]) == 384  # all-MiniLM-L6-v2 dimension is 384
        assert len(vectors[1]) == 384

        q_vec = embedder.embed_query("TCP protocol")
        assert len(q_vec) == 384


class TestChromaVectorStore:
    def test_strict_multi_tenant_isolation(self, tmp_path):
        """
        CRITICAL TEST: Ensures user A cannot retrieve user B's document chunks.
        """
        vector_store = ChromaVectorStore(persist_dir=str(tmp_path / "chroma_test"))
        embedder = SentenceTransformerEmbeddings.get_instance()

        user_a_id = uuid.uuid4()
        user_b_id = uuid.uuid4()

        doc_a_id = uuid.uuid4()
        doc_b_id = uuid.uuid4()

        # User A chunks about computer networks
        chunk_a = DocumentChunk(
            chunk_id=f"{doc_a_id}_c0",
            doc_id=str(doc_a_id),
            user_id=str(user_a_id),
            page_number=1,
            chunk_index=0,
            text="TCP uses a three-way handshake: SYN, SYN-ACK, ACK.",
            char_length=50,
            metadata={"filename": "net_a.pdf", "subject": "Networks"},
        )
        vec_a = embedder.embed_documents([chunk_a.text])
        vector_store.upsert_chunks(doc_a_id, user_a_id, [chunk_a], vec_a)

        # User B chunks about biology
        chunk_b = DocumentChunk(
            chunk_id=f"{doc_b_id}_c0",
            doc_id=str(doc_b_id),
            user_id=str(user_b_id),
            page_number=1,
            chunk_index=0,
            text="Mitochondria is the powerhouse of the cell.",
            char_length=42,
            metadata={"filename": "bio_b.pdf", "subject": "Biology"},
        )
        vec_b = embedder.embed_documents([chunk_b.text])
        vector_store.upsert_chunks(doc_b_id, user_b_id, [chunk_b], vec_b)

        # Query as User A searching for biology
        query_vec = embedder.embed_query("powerhouse of cell")
        results_user_a = vector_store.query_similar_chunks(
            query_embedding=query_vec,
            user_id=user_a_id,
            top_k=5,
        )
        # MUST NEVER return User B's chunk!
        assert len(results_user_a) == 0, "Security Violation: User A accessed User B's chunk!"

        # Query as User B searching for biology
        results_user_b = vector_store.query_similar_chunks(
            query_embedding=query_vec,
            user_id=user_b_id,
            top_k=5,
        )
        assert len(results_user_b) == 1
        assert "Mitochondria" in results_user_b[0]["text"]
        assert results_user_b[0]["doc_id"] == str(doc_b_id)

        # Test document vector deletion
        vector_store.delete_document_vectors(doc_b_id, user_b_id)
        post_delete_results = vector_store.query_similar_chunks(
            query_embedding=query_vec,
            user_id=user_b_id,
            top_k=5,
        )
        assert len(post_delete_results) == 0


class TestRAGGenerator:
    def test_grounded_answer_with_citations(self):
        generator = RAGGenerator()
        chunks = [
            {
                "doc_id": "doc-123",
                "filename": "computer_networks.pdf",
                "page": 2,
                "chunk_index": 1,
                "score": 0.88,
                "text": "TCP establishes a connection using the Three-Way Handshake: SYN, SYN-ACK, ACK.",
            }
        ]

        answer, citations, latency_ms, provider = generator.generate_answer(
            query="How does TCP establish a connection?",
            chunks=chunks,
        )

        assert len(citations) == 1
        assert citations[0].document_name == "computer_networks.pdf"
        assert citations[0].page == 2
        assert "[Document: computer_networks.pdf, Page: 2]" in answer
        assert latency_ms >= 0

    def test_abstain_when_no_context(self):
        generator = RAGGenerator()
        answer, citations, latency_ms, provider = generator.generate_answer(
            query="What is quantum entanglement?",
            chunks=[],
        )
        assert len(citations) == 0
        assert "do not contain information" in answer

    def test_transient_error_detection(self):
        # Transient errors should return True (retryable)
        assert _is_transient_error(Exception("429 RESOURCE_EXHAUSTED: Rate limit exceeded"))
        assert _is_transient_error(Exception("503 UNAVAILABLE: Server temporarily busy"))
        assert _is_transient_error(Exception("Request timed out after 25000ms"))
        assert _is_transient_error(Exception("Connection reset by peer"))

        # Permanent errors should return False (non-retryable)
        assert not _is_transient_error(Exception("400 INVALID_ARGUMENT: API_KEY_INVALID"))
        assert not _is_transient_error(Exception("401 UNAUTHORIZED: Invalid credentials"))
        assert not _is_transient_error(Exception("403 PERMISSION_DENIED: Access forbidden"))
        assert not _is_transient_error(Exception("404 NOT_FOUND: Model gemini-invalid not found"))

    def test_bounded_retry_on_transient_error_succeeds(self):
        from unittest.mock import MagicMock, patch

        generator = RAGGenerator(api_key="real-simulated-key", model_name="gemini-2.0-flash")
        chunks = [{"filename": "sample.pdf", "page": 1, "text": "Test chunk text", "score": 0.9}]

        call_count = 0

        def mock_single_attempt(prompt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("429 RESOURCE_EXHAUSTED: Quota exceeded, retry in 1s")
            return "This is the generated answer [Document: sample.pdf, Page: 1].", "gemini (gemini-2.0-flash)"

        with patch.object(generator, "_is_offline_mode", return_value=False):
            with patch.object(generator, "_call_gemini_single_attempt", side_effect=mock_single_attempt):
                with patch("time.sleep", return_value=None):  # Don't delay test
                    answer, citations, latency_ms, provider = generator.generate_answer(
                        query="Test query",
                        chunks=chunks,
                    )

        assert call_count == 2, f"Expected exactly 2 attempts (1 initial + 1 retry), got {call_count}"
        assert "This is the generated answer" in answer
        assert provider == "gemini (gemini-2.0-flash)"

    def test_permanent_error_aborts_immediately_without_retry(self):
        from unittest.mock import MagicMock, patch

        generator = RAGGenerator(api_key="real-simulated-key", model_name="gemini-2.0-flash")
        chunks = [{"filename": "sample.pdf", "page": 1, "text": "Test chunk text", "score": 0.9}]

        call_count = 0

        def mock_single_attempt(prompt):
            nonlocal call_count
            call_count += 1
            raise Exception("400 INVALID_ARGUMENT: API_KEY_INVALID")

        with patch.object(generator, "_is_offline_mode", return_value=False):
            with patch.object(generator, "_call_gemini_single_attempt", side_effect=mock_single_attempt):
                answer, citations, latency_ms, provider = generator.generate_answer(
                    query="Test query",
                    chunks=chunks,
                )

        assert call_count == 1, f"Expected exactly 1 attempt on permanent error, got {call_count}"
        # Preserves grounded fallback synthesis upon LLM failure
        assert provider == "offline-grounded-engine"
        assert "Based on your study materials" in answer

    def test_extract_text_from_various_formats(self):
        # 1. Pure string
        assert extract_text_from_gemini_response("Plain text response") == "Plain text response"

        # 2. Structured content blocks list
        blocks = [{"type": "text", "text": "Extracted text block", "extras": {"sig": "xyz"}}]
        assert extract_text_from_gemini_response(blocks) == "Extracted text block"

        # 3. Stringified content block representation
        raw_repr = "[{'type': 'text', 'text': 'Clean stringified text', 'extras': {'signature': 'abc'}}]"
        assert extract_text_from_gemini_response(raw_repr) == "Clean stringified text"

        # 4. Object with .text or .content
        class MockAIMessage:
            content = "Message content from object"

        assert extract_text_from_gemini_response(MockAIMessage()) == "Message content from object"

        # 5. Empty or None
        assert extract_text_from_gemini_response(None) == ""
        assert extract_text_from_gemini_response("") == ""


@pytest.mark.asyncio
class TestRAGServiceIntegration:
    async def test_duplicate_document_rejection(
        self,
        db_session: AsyncSession,
        sample_user: User,
        tmp_path,
    ):
        pdf_path = SAMPLE_PDFS_DIR / "operating_systems.pdf"
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        vector_store = ChromaVectorStore(persist_dir=str(tmp_path / "chroma_service"))
        service = RAGService(db_session=db_session, vector_store=vector_store)

        # First ingestion succeeds
        doc1 = await service.ingest_document(
            user_id=sample_user.id,
            file_bytes=pdf_bytes,
            filename="operating_systems.pdf",
            subject="Computer Science",
        )
        assert doc1.status == "ready"
        assert doc1.chunk_count > 0

        # Duplicate ingestion raises DuplicateDocumentError
        with pytest.raises(DuplicateDocumentError):
            await service.ingest_document(
                user_id=sample_user.id,
                file_bytes=pdf_bytes,
                filename="operating_systems_copy.pdf",
                subject="Computer Science",
            )

    async def test_end_to_end_query_and_citations(
        self,
        db_session: AsyncSession,
        sample_user: User,
        tmp_path,
    ):
        pdf_path = SAMPLE_PDFS_DIR / "machine_learning.pdf"
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        vector_store = ChromaVectorStore(persist_dir=str(tmp_path / "chroma_service_qa"))
        service = RAGService(db_session=db_session, vector_store=vector_store)

        doc = await service.ingest_document(
            user_id=sample_user.id,
            file_bytes=pdf_bytes,
            filename="machine_learning.pdf",
            subject="Artificial Intelligence",
        )

        response = await service.query(
            user_id=sample_user.id,
            query_text="What is the Self-Attention mechanism formula?",
            top_k=3,
        )

        assert response.context_available is True
        assert len(response.citations) > 0
        assert response.citations[0].document_name == "machine_learning.pdf"
        assert response.latency_ms >= 0
        assert "Attention" in response.answer or "softmax" in response.answer or "Query" in response.answer


@pytest.mark.asyncio
class TestRAGEvaluator:
    async def test_evaluation_benchmark(
        self,
        db_session: AsyncSession,
        sample_user: User,
        tmp_path,
    ):
        pdf_path = SAMPLE_PDFS_DIR / "computer_networks.pdf"
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        vector_store = ChromaVectorStore(persist_dir=str(tmp_path / "chroma_eval"))
        service = RAGService(db_session=db_session, vector_store=vector_store)

        await service.ingest_document(
            user_id=sample_user.id,
            file_bytes=pdf_bytes,
            filename="computer_networks.pdf",
            subject="Computer Science",
        )

        evaluator = RAGEvaluator(rag_service=service)

        test_questions = [
            RAGEvalQuestion(
                question="What are the steps of the TCP three-way handshake?",
                expected_answer="SYN, SYN-ACK, ACK handshake sequence for reliable transport connection establishment.",
                relevant_doc_name="computer_networks.pdf",
                keywords=["SYN", "SYN-ACK", "ACK", "Three-Way Handshake"],
            ),
            RAGEvalQuestion(
                question="How does Distance Vector routing differ from Link State routing?",
                expected_answer="Distance Vector uses Bellman-Ford with hop counts, while Link State uses Dijkstra shortest path.",
                relevant_doc_name="computer_networks.pdf",
                keywords=["Distance Vector", "Link State", "Bellman-Ford", "Dijkstra"],
            ),
        ]

        report = await evaluator.run_evaluation_suite(
            user_id=sample_user.id,
            test_questions=test_questions,
        )

        assert report.total_questions == 2
        assert report.passed_count >= 1
        assert report.mean_retrieval_relevance > 0.2
        assert report.mean_answer_faithfulness > 0.4
        assert report.mean_latency_ms >= 0
