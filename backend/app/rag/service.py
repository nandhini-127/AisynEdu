import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.entities import Document
from app.rag.chunker import DocumentChunker
from app.rag.embeddings import SentenceTransformerEmbeddings
from app.rag.extractor import ExtractedDocument, PDFExtractor
from app.rag.generator import RAGGenerator
from app.rag.vectorstore import ChromaVectorStore
from app.schemas.rag import DocumentQueryResponse, SourceCitation

logger = logging.getLogger("edunex.rag.service")


class DuplicateDocumentError(Exception):
    """Raised when an identical document has already been ingested by the user."""
    pass


class DocumentNotFoundError(Exception):
    """Raised when a document is not found or not owned by user."""
    pass


class RAGService:
    """
    High-level orchestrator for document ingestion, text splitting, embedding generation,
    vector storage in ChromaDB, and grounded QA with source citations.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        vector_store: Optional[ChromaVectorStore] = None,
        embeddings: Optional[SentenceTransformerEmbeddings] = None,
        generator: Optional[RAGGenerator] = None,
        chunker: Optional[DocumentChunker] = None,
    ):
        self.db = db_session
        self.vector_store = vector_store or ChromaVectorStore()
        self.embeddings = embeddings or SentenceTransformerEmbeddings.get_instance()
        self.generator = generator or RAGGenerator()
        self.chunker = chunker or DocumentChunker(
            chunk_size=settings.RAG_CHUNK_SIZE,
            chunk_overlap=settings.RAG_CHUNK_OVERLAP,
        )

    async def ingest_document(
        self,
        user_id: UUID,
        file_bytes: bytes,
        filename: str,
        subject: str,
    ) -> Document:
        """
        Ingests a PDF document:
        1. Validates and extracts text per-page.
        2. Detects duplicates via SHA-256 for the user.
        3. Saves original file to disk.
        4. Chunks text with page preservation.
        5. Computes vector embeddings.
        6. Stores chunks in ChromaDB with tenant metadata.
        7. Persists Document record in PostgreSQL.
        """
        # Step 1: Validate & Extract Text
        extracted: ExtractedDocument = PDFExtractor.extract_text(file_bytes, filename)

        # Step 2: Duplicate Document Detection (check user's documents for matching SHA-256)
        query = select(Document).where(Document.user_id == user_id)
        result = await self.db.execute(query)
        user_docs = result.scalars().all()

        for doc in user_docs:
            if doc.metadata_ and doc.metadata_.get("sha256") == extracted.sha256_hash:
                raise DuplicateDocumentError(
                    f"A document identical to '{filename}' has already been uploaded as '{doc.original_filename}'."
                )

        # Step 3: Save physical file to disk
        try:
            user_upload_dir = Path(settings.UPLOAD_DIR) / str(user_id)
            user_upload_dir.mkdir(parents=True, exist_ok=True)
            storage_path = user_upload_dir / f"{extracted.sha256_hash[:16]}_{filename}"
            with open(storage_path, "wb") as f:
                f.write(file_bytes)
        except (PermissionError, OSError) as e:
            import tempfile
            logger.warning("Permission denied for %s, falling back to temp dir: %s", settings.UPLOAD_DIR, str(e))
            user_upload_dir = Path(tempfile.gettempdir()) / "edunex_uploads" / str(user_id)
            user_upload_dir.mkdir(parents=True, exist_ok=True)
            storage_path = user_upload_dir / f"{extracted.sha256_hash[:16]}_{filename}"
            with open(storage_path, "wb") as f:
                f.write(file_bytes)

        # Step 4: Create Document record in DB with status "processing"
        doc_record = Document(
            user_id=user_id,
            original_filename=filename,
            file_type="pdf",
            file_size_bytes=extracted.file_size_bytes,
            subject=subject,
            title=extracted.metadata.get("title", filename),
            status="processing",
            storage_path=str(storage_path),
            chroma_collection=ChromaVectorStore.COLLECTION_NAME,
            chunk_count=0,
            metadata_={
                "sha256": extracted.sha256_hash,
                "page_count": extracted.page_count,
                "total_characters": extracted.total_characters,
                "title": extracted.metadata.get("title"),
                "author": extracted.metadata.get("author"),
            },
        )
        self.db.add(doc_record)
        await self.db.commit()
        await self.db.refresh(doc_record)

        try:
            # Step 5: Chunk text preserving page numbers
            chunks = self.chunker.split_pages(
                pages=extracted.pages,
                doc_id=doc_record.id,
                user_id=user_id,
                filename=filename,
                subject=subject,
            )

            if not chunks:
                raise ValueError("No text chunks could be produced from document.")

            # Step 6: Generate vector embeddings
            chunk_texts = [c.text for c in chunks]
            embeddings_list = self.embeddings.embed_documents(chunk_texts)

            # Step 7: Store in ChromaDB
            self.vector_store.upsert_chunks(
                doc_id=doc_record.id,
                user_id=user_id,
                chunks=chunks,
                embeddings=embeddings_list,
            )

            # Step 8: Update Document record status to "ready"
            doc_record.status = "ready"
            doc_record.chunk_count = len(chunks)
            doc_record.processed_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(doc_record)

            logger.info(
                "Successfully ingested document %s (%s) with %d chunks",
                filename,
                str(doc_record.id),
                len(chunks),
            )
            return doc_record

        except Exception as e:
            logger.error("Failed to process document %s: %s", filename, str(e))
            doc_record.status = "failed"
            doc_record.error_message = str(e)
            await self.db.commit()
            # Clean up any partial vectors
            try:
                self.vector_store.delete_document_vectors(doc_record.id, user_id)
            except Exception:
                pass
            raise

    async def list_user_documents(
        self,
        user_id: UUID,
        subject: Optional[str] = None,
    ) -> List[Document]:
        """List all documents owned by user."""
        query = select(Document).where(Document.user_id == user_id)
        if subject:
            query = query.where(Document.subject == subject)
        query = query.order_by(Document.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_document(self, user_id: UUID, doc_id: UUID) -> Document:
        """Get single document by ID with user ownership check."""
        query = select(Document).where(Document.id == doc_id, Document.user_id == user_id)
        result = await self.db.execute(query)
        doc = result.scalar_one_or_none()
        if not doc:
            raise DocumentNotFoundError(f"Document {doc_id} not found or access denied.")
        return doc

    async def delete_document(self, user_id: UUID, doc_id: UUID) -> bool:
        """
        Deletes a document:
        1. Validates ownership.
        2. Deletes vector chunks from ChromaDB.
        3. Deletes file from storage.
        4. Deletes record from PostgreSQL.
        """
        doc = await self.get_document(user_id, doc_id)

        # Remove vector chunks
        self.vector_store.delete_document_vectors(doc_id, user_id)

        # Remove physical file
        if doc.storage_path and os.path.exists(doc.storage_path):
            try:
                os.remove(doc.storage_path)
            except OSError as e:
                logger.warning("Failed to remove file %s: %s", doc.storage_path, str(e))

        # Delete database row
        await self.db.delete(doc)
        await self.db.commit()
        logger.info("Deleted document %s and its vectors for user %s", str(doc_id), str(user_id))
        return True

    async def query(
        self,
        user_id: UUID,
        query_text: str,
        doc_ids: Optional[List[UUID]] = None,
        subject: Optional[str] = None,
        top_k: int = 4,
        similarity_threshold: Optional[float] = None,
    ) -> DocumentQueryResponse:
        """
        Performs semantic retrieval and grounded question answering with source citations.
        Strictly enforces tenant isolation and records fine-grained pipeline latency.
        """
        pipeline_start = time.perf_counter()

        # Validate that specified doc_ids belong to the requesting user
        if doc_ids:
            for d_id in doc_ids:
                await self.get_document(user_id, d_id)

        # 1. Embed query
        embed_start = time.perf_counter()
        query_vector = self.embeddings.embed_query(query_text)
        embed_ms = (time.perf_counter() - embed_start) * 1000

        # 2. Retrieve top-K chunks with user filter
        retrieval_start = time.perf_counter()
        retrieved_chunks = self.vector_store.query_similar_chunks(
            query_embedding=query_vector,
            user_id=user_id,
            doc_ids=doc_ids,
            subject=subject,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )
        retrieval_ms = (time.perf_counter() - retrieval_start) * 1000

        # 3. Grounded answer generation
        answer, citations, latency_ms, provider = self.generator.generate_answer(
            query=query_text,
            chunks=retrieved_chunks,
        )

        total_ms = (time.perf_counter() - pipeline_start) * 1000

        logger.info(
            "[RAG-TIMING] Query Embedding: %.1fms | Vector Retrieval (%d chunks): %.1fms | "
            "LLM Generation: %dms (provider=%s) | Total Pipeline: %.1fms",
            embed_ms,
            len(retrieved_chunks),
            retrieval_ms,
            latency_ms,
            provider,
            total_ms,
        )

        return DocumentQueryResponse(
            query=query_text,
            answer=answer,
            citations=citations,
            retrieved_chunks_count=len(retrieved_chunks),
            latency_ms=latency_ms,
            llm_provider=provider,
            context_available=len(retrieved_chunks) > 0,
        )
