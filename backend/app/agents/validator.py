"""
Relevance and Topic Drift Validator for EduNex AI Agent Pipeline.
Ensures generated responses strictly adhere to the user's requested technical domain
and detects cross-subject contamination (e.g., ML concepts answering GPU queries).
"""
import logging
import re
from typing import Optional, Tuple

logger = logging.getLogger("edunex.agents.validator")

# Domain keyword definitions
DOMAIN_TOPICS = {
    "gpu_hardware": {
        "keywords": [
            "gpu", "cuda", "tensor core", "tensor cores", "cuda core", "cuda cores",
            "vram", "memory bandwidth", "streaming multiprocessor", "sm", "warp",
            "simt", "simd", "parallel processing", "graphics processing", "hbm",
            "gddr", "pcie", "nvlink", "shader", "rasterization", "alu", "fp32", "fp16", "int8"
        ],
        "incompatible_topics": ["machine_learning_algorithms", "dbms"],
    },
    "machine_learning_algorithms": {
        "keywords": [
            "machine learning", "supervised learning", "unsupervised learning", "reinforcement learning",
            "overfitting", "underfitting", "bias-variance", "cross-validation", "hyperparameter",
            "decision tree", "random forest", "gradient boosting", "regression", "classification",
            "clustering", "k-means", "knn", "svm", "support vector"
        ],
        "incompatible_topics": ["gpu_hardware"],
    },
    "deep_learning": {
        "keywords": [
            "deep learning", "neural network", "backpropagation", "activation function",
            "cnn", "convolutional", "rnn", "recurrent", "lstm", "transformer", "attention mechanism",
            "multi-head attention", "self-attention", "gradient descent", "loss function"
        ],
        "incompatible_topics": [],
    },
    "operating_systems": {
        "keywords": [
            "operating system", "process", "thread", "scheduling", "deadlock", "virtual memory",
            "paging", "kernel", "mutex", "semaphore", "system call", "round robin", "context switch"
        ],
        "incompatible_topics": ["dbms"],
    },
    "dbms": {
        "keywords": [
            "database", "sql", "relational", "acid", "indexing", "b-tree", "b+ tree", "hash index",
            "transaction", "normalization", "foreign key", "join", "query optimization"
        ],
        "incompatible_topics": ["operating_systems", "gpu_hardware"],
    },
    "networking": {
        "keywords": [
            "networking", "tcp", "udp", "osi model", "ip address", "packet", "routing",
            "handshake", "socket", "http", "dns", "firewall", "subnet"
        ],
        "incompatible_topics": [],
    },
}


class TopicRelevanceValidator:
    """
    Validates that a generated AI response matches the intended topic domain
    and does not suffer from topic drift or unrelated subject hallucination.
    """

    @classmethod
    def detect_query_domain(cls, query: str, subject: str = "") -> Optional[str]:
        """Identifies the dominant technical domain of the query."""
        text = f"{query} {subject}".lower()
        best_domain = None
        max_matches = 0

        for domain, info in DOMAIN_TOPICS.items():
            matches = sum(1 for kw in info["keywords"] if re.search(r"\b" + re.escape(kw) + r"\b", text))
            if matches > max_matches:
                max_matches = matches
                best_domain = domain

        return best_domain if max_matches > 0 else None

    @classmethod
    def validate_response_relevance(
        cls, query: str, response: str, subject: str = ""
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates response relevance.
        Returns:
            (is_relevant, detected_domain, drift_reason)
        """
        if not response or len(response.strip()) < 30:
            return False, None, "Response is too short or empty."

        query_domain = cls.detect_query_domain(query, subject)
        if not query_domain:
            # General query: ensure response does not contain unrelated GPU hardware contamination
            is_gpu_query = bool(re.search(r"\b(gpu|cuda|vram|tensor core)\b", f"{query} {subject}".lower()))
            if not is_gpu_query:
                gpu_terms = ["cuda", "tensor core", "tensor cores", "streaming multiprocessor", "vram"]
                gpu_hits = sum(1 for kw in gpu_terms if re.search(r"\b" + kw + r"\b", response.lower()))
                if gpu_hits >= 2:
                    return False, "general", "Response contained unrelated GPU hardware concepts for a non-hardware query."
            return True, None, None

        resp_lower = response.lower()
        domain_info = DOMAIN_TOPICS[query_domain]

        # Count occurrences of domain keywords in the generated response
        domain_keyword_hits = sum(
            1 for kw in domain_info["keywords"] if re.search(r"\b" + re.escape(kw) + r"\b", resp_lower)
        )

        # Check for incompatible domain contamination
        # E.g., if user asks about GPU Hardware, but response contains 0 GPU keywords
        # and has terms like 'overfitting', 'cross-validation', 'dataset split'
        drift_detected = False
        drift_reason = None

        if domain_keyword_hits == 0:
            for incompatible in domain_info.get("incompatible_topics", []):
                incomp_info = DOMAIN_TOPICS[incompatible]
                incomp_hits = sum(
                    1 for kw in incomp_info["keywords"] if re.search(r"\b" + re.escape(kw) + r"\b", resp_lower)
                )
                if incomp_hits >= 2:
                    drift_detected = True
                    drift_reason = (
                        f"Response drifted from requested domain '{query_domain}' into '{incompatible}'. "
                        f"Expected terms like {domain_info['keywords'][:4]} but found {incomp_info['keywords'][:3]}."
                    )
                    break

        if drift_detected:
            logger.warning("Topic drift detected: %s", drift_reason)
            return False, query_domain, drift_reason

        return True, query_domain, None

