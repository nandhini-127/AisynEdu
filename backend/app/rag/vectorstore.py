import logging
import os
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.config import settings

logger = logging.getLogger("edunex.rag.vectorstore")


class ChromaVectorStore:
    """
    Manages vector storage and similarity search in ChromaDB.
    Enforces strict user-level data isolation to prevent cross-tenant vector retrieval.
    """

    COLLECTION_NAME = "edunex_document_chunks"

    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
        try:
            os.makedirs(self.persist_dir, exist_ok=True)
        except (PermissionError, OSError):
            import tempfile
            self.persist_dir = os.path.join(tempfile.gettempdir(), "edunex_chroma")
            os.makedirs(self.persist_dir, exist_ok=True)
        self._client = None
        self._collection = None

    def _get_collection(self):
        if self._collection is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            try:
                self._client = chromadb.PersistentClient(
                    path=self.persist_dir,
                    settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
                )
                self._collection = self._client.get_or_create_collection(
                    name=self.COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception as e:
                import tempfile
                logger.warning(
                    "Failed to open ChromaDB at %s: %s. Falling back to temporary directory.",
                    self.persist_dir,
                    str(e),
                )
                self.persist_dir = os.path.join(tempfile.gettempdir(), "edunex_chroma")
                os.makedirs(self.persist_dir, exist_ok=True)
                self._client = chromadb.PersistentClient(
                    path=self.persist_dir,
                    settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
                )
                self._collection = self._client.get_or_create_collection(
                    name=self.COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"},
                )
            logger.info("Connected to ChromaDB collection '%s' at %s", self.COLLECTION_NAME, self.persist_dir)
        return self._collection

    def upsert_chunks(
        self,
        doc_id: UUID,
        user_id: UUID,
        chunks: List[Any],  # List[DocumentChunk]
        embeddings: List[List[float]],
    ) -> int:
        """
        Upserts document chunks into ChromaDB with their embeddings and metadata.
        """
        if not chunks:
            return 0

        collection = self._get_collection()

        ids: List[str] = []
        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for chunk in chunks:
            ids.append(chunk.chunk_id)
            documents.append(chunk.text)
            # Ensure all metadata values are primitive types (str, int, float, bool)
            safe_meta = {
                "doc_id": str(doc_id),
                "user_id": str(user_id),
                "filename": str(chunk.metadata.get("filename", "")),
                "subject": str(chunk.metadata.get("subject", "")),
                "page": int(chunk.page_number),
                "chunk_index": int(chunk.chunk_index),
                "char_length": int(chunk.char_length),
            }
            metadatas.append(safe_meta)

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        logger.info(
            "Upserted %d chunks for document %s (user %s)",
            len(chunks),
            str(doc_id)[:8],
            str(user_id)[:8],
        )
        return len(chunks)

    def delete_document_vectors(self, doc_id: UUID, user_id: UUID) -> int:
        """
        Deletes all chunks belonging to a document under the specified user.
        Strictly prevents deleting or modifying other users' data.
        """
        collection = self._get_collection()
        where_filter = {
            "$and": [
                {"user_id": {"$eq": str(user_id)}},
                {"doc_id": {"$eq": str(doc_id)}},
            ]
        }

        try:
            # Query existing count before deletion for logging
            existing = collection.get(where=where_filter)
            count = len(existing["ids"]) if existing and "ids" in existing else 0

            if count > 0:
                collection.delete(where=where_filter)
                logger.info("Deleted %d vector chunks for doc %s (user %s)", count, str(doc_id)[:8], str(user_id)[:8])
            return count
        except Exception as e:
            logger.error("Error deleting vectors for doc %s: %s", str(doc_id), str(e))
            raise RuntimeError(f"Failed to delete document vectors: {str(e)}") from e

    def query_similar_chunks(
        self,
        query_embedding: List[float],
        user_id: UUID,
        doc_ids: Optional[List[UUID]] = None,
        subject: Optional[str] = None,
        top_k: int = 4,
        similarity_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top-K most semantically similar chunks for a user.
        CRITICAL: Always enforces user_id filter so users NEVER access other users' documents.
        """
        collection = self._get_collection()

        # Build compound filter with mandatory user_id
        filters: List[Dict[str, Any]] = [{"user_id": {"$eq": str(user_id)}}]

        if doc_ids:
            if len(doc_ids) == 1:
                filters.append({"doc_id": {"$eq": str(doc_ids[0])}})
            else:
                filters.append({"doc_id": {"$in": [str(d) for d in doc_ids]}})

        if subject:
            filters.append({"subject": {"$eq": subject}})

        if len(filters) == 1:
            where_clause = filters[0]
        else:
            where_clause = {"$and": filters}

        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_clause,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.error("ChromaDB query error: %s", str(e))
            return []

        retrieved: List[Dict[str, Any]] = []

        if not results or not results["documents"] or len(results["documents"][0]) == 0:
            return retrieved

        docs = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)
        ids = results["ids"][0] if results.get("ids") else [""] * len(docs)

        min_threshold = similarity_threshold if similarity_threshold is not None else settings.RAG_SIMILARITY_THRESHOLD

        for doc_text, meta, dist, chunk_id in zip(docs, metadatas, distances, ids):
            # Chroma with cosine distance returns d in [0, 2]. Cosine similarity s = 1.0 - d
            cosine_similarity = round(1.0 - float(dist), 4)

            # Apply similarity threshold filtering
            if cosine_similarity < min_threshold:
                logger.debug(
                    "Filtered out chunk %s with similarity %.3f < threshold %.3f",
                    chunk_id,
                    cosine_similarity,
                    min_threshold,
                )
                continue

            retrieved.append({
                "chunk_id": chunk_id,
                "text": doc_text,
                "score": cosine_similarity,
                "doc_id": meta.get("doc_id"),
                "filename": meta.get("filename"),
                "subject": meta.get("subject"),
                "page": meta.get("page", 1),
                "chunk_index": meta.get("chunk_index", 0),
            })

        logger.info(
            "Retrieved %d relevant chunks for user %s (top_k=%d, threshold=%.2f)",
            len(retrieved),
            str(user_id)[:8],
            top_k,
            min_threshold,
        )
        return retrieved
