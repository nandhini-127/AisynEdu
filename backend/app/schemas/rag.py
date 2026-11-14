from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class DocumentRead(BaseModel):
    id: UUID
    user_id: UUID
    original_filename: str
    file_type: str
    file_size_bytes: int
    subject: str
    title: Optional[str] = None
    status: str
    chunk_count: int
    metadata: Dict[str, Any] = Field(default_factory=dict, alias="metadata_")
    error_message: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DocumentUploadResponse(BaseModel):
    document: DocumentRead
    chunk_count: int
    message: str


class DocumentQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=2000, description="Question asked by student")
    document_ids: Optional[List[UUID]] = Field(default=None, description="Optional filter to specific document IDs")
    subject: Optional[str] = Field(default=None, description="Optional subject filter")
    top_k: Optional[int] = Field(default=4, ge=1, le=20, description="Number of top chunks to retrieve")
    similarity_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Minimum cosine similarity")


class SourceCitation(BaseModel):
    document_id: str
    document_name: str
    page: int
    chunk_index: int
    score: float
    text_snippet: str


class DocumentQueryResponse(BaseModel):
    query: str
    answer: str
    citations: List[SourceCitation]
    retrieved_chunks_count: int
    latency_ms: int
    llm_provider: str
    context_available: bool


class RAGEvalQuestion(BaseModel):
    question: str
    expected_answer: str
    relevant_doc_name: str
    keywords: List[str] = []


class RAGEvalResult(BaseModel):
    question: str
    expected_answer: str
    generated_answer: str
    citations: List[SourceCitation]
    retrieval_relevance: float  # [0.0 - 1.0]
    answer_faithfulness: float  # [0.0 - 1.0]
    latency_ms: int
    passed: bool


class RAGEvalReport(BaseModel):
    total_questions: int
    passed_count: int
    mean_retrieval_relevance: float
    mean_answer_faithfulness: float
    mean_latency_ms: float
    results: List[RAGEvalResult]

