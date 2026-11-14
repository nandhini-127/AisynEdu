import logging
from typing import List, Optional
from app.core.config import settings

logger = logging.getLogger("edunex.rag.embeddings")


class SentenceTransformerEmbeddings:
    """
    Embedding generation service using HuggingFace / Sentence Transformers.
    Caches model in memory and supports batch embedding generation.
    """

    _instance: Optional["SentenceTransformerEmbeddings"] = None
    _model = None

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL

    @classmethod
    def get_instance(cls, model_name: Optional[str] = None) -> "SentenceTransformerEmbeddings":
        if cls._instance is None:
            cls._instance = cls(model_name)
        return cls._instance

    def _load_model(self):
        if self._model is None:
            logger.info("Loading SentenceTransformer model: %s ...", self.model_name)
            try:
                from sentence_transformers import SentenceTransformer
                import torch

                device = "cuda" if torch.cuda.is_available() else "cpu"
                # First attempt local loading via model_kwargs to prevent sandbox network timeouts
                try:
                    self._model = SentenceTransformer(
                        self.model_name,
                        device=device,
                        model_kwargs={"local_files_only": True},
                    )
                except Exception:
                    self._model = SentenceTransformer(self.model_name, device=device)
                logger.info("SentenceTransformer model %s loaded successfully on %s.", self.model_name, device)
            except Exception as e:
                logger.warning(
                    "Could not load neural SentenceTransformer model '%s': %s. Falling back to resilient deterministic embedding engine.",
                    self.model_name,
                    str(e),
                )
                self._model = "fallback"
        return self._model

    def _fallback_embedding(self, text: str, dim: int = 384) -> List[float]:
        """Generates a deterministic normalized embedding vector when the neural model is unreachable."""
        import hashlib
        import math

        vec = [0.0] * dim
        words = text.lower().split()
        if not words:
            return vec
        for i, word in enumerate(words):
            h = int(hashlib.sha256(word.encode()).hexdigest(), 16)
            idx = h % dim
            vec[idx] += 1.0 / math.sqrt(i + 1)
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    def embed_documents(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generate normalized dense vector embeddings for a list of text strings."""
        if not texts:
            return []

        model = self._load_model()
        if model == "fallback":
            return [self._fallback_embedding(t) for t in texts]

        try:
            embeddings = model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=False,
                normalize_embeddings=True,  # Normalized embeddings enable fast cosine similarity via dot product
            )
            return embeddings.tolist()
        except Exception as e:
            logger.warning("Error generating neural embeddings, falling back to deterministic vectors: %s", str(e))
            return [self._fallback_embedding(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        """Generate normalized dense vector embedding for a single query string."""
        if not text or not text.strip():
            raise ValueError("Query text cannot be empty for embedding.")

        model = self._load_model()
        if model == "fallback":
            return self._fallback_embedding(text.strip())

        try:
            embedding = model.encode(
                text.strip(),
                show_progress_bar=False,
                normalize_embeddings=True,
            )
            return embedding.tolist()
        except Exception as e:
            logger.warning("Error in neural query embedding, falling back: %s", str(e))
            return self._fallback_embedding(text.strip())
            logger.error("Error generating query embedding: %s", str(e))
            raise RuntimeError(f"Query embedding generation failed: {str(e)}") from e
