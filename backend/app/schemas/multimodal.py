from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ExtractedDiagramInfo(BaseModel):
    diagram_index: int
    page: int
    format: str
    width: int
    height: int
    size_bytes: int
    description: Optional[str] = None


class ImageUploadResponse(BaseModel):
    id: UUID
    original_filename: str
    file_type: str
    mime_type: str
    file_size_bytes: int
    width: int
    height: int
    storage_path: str
    created_at: datetime
    extracted_text: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ImageExplainRequest(BaseModel):
    image_id: Optional[UUID] = None
    question: Optional[str] = Field(
        default="Explain this educational diagram and its core components in detail.",
        description="Student question or prompt about the image",
    )
    prompt_type: str = Field(
        default="diagram",
        description="Type of explanation: 'diagram', 'math', 'chart', 'general', or 'ocr'",
    )


class ImageExplainResponse(BaseModel):
    image_id: Optional[UUID] = None
    question: str
    explanation: str
    diagram_type: Optional[str] = None
    extracted_text: Optional[str] = None
    latency_ms: int = 0


class PDFPageQueryRequest(BaseModel):
    document_id: UUID
    page_number: int = Field(..., ge=1, description="1-based page number")
    question: str = Field(..., min_length=2, description="Question regarding this specific page")
    include_diagrams: bool = Field(
        default=True,
        description="Whether to analyze diagrams found on this page",
    )


class PDFPageQueryResponse(BaseModel):
    document_id: UUID
    document_name: str
    page_number: int
    question: str
    answer: str
    page_text_snippet: str
    diagram_count: int = 0
    diagrams: List[ExtractedDiagramInfo] = []
    is_scanned_page: bool = False
    ocr_applied: bool = False
    citations: List[Dict[str, Any]] = []
    latency_ms: int = 0


class MixedQueryRequest(BaseModel):
    text_query: str = Field(..., min_length=1, description="Question from the student")
    image_id: Optional[UUID] = None
    document_ids: List[UUID] = []
    page_number: Optional[int] = None


class MixedQueryResponse(BaseModel):
    answer: str
    image_used: bool = False
    image_id: Optional[UUID] = None
    documents_used: List[str] = []
    citations: List[Dict[str, Any]] = []
    latency_ms: int = 0


class ScannedPageOCRResponse(BaseModel):
    page_number: int
    extracted_text: str
    confidence: float
    ocr_engine: str

