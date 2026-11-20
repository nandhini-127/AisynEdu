from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class SourceCitationDict(TypedDict):
    document_id: str
    document_name: str
    page: int
    chunk_index: int
    score: float
    text_snippet: str


class QuizQuestionDict(TypedDict):
    id: int
    question: str
    options: List[str]          # exactly 4 options: ["A) ...", "B) ...", "C) ...", "D) ..."]
    correct_answer: str         # "A" | "B" | "C" | "D"
    explanation: str
    difficulty: str


class SummaryDataDict(TypedDict):
    overview: str
    key_points: List[str]
    definitions: Dict[str, str]
    revision_notes: List[str]


class AgentState(TypedDict, total=False):
    """
    Central typed state passed through the EduNex AI LangGraph workflow.
    """
    # ── User & Session Context ─────────────────────────────────────────
    user_id: str
    session_id: str
    subject: str

    # ── Conversational Messages (appends using add_messages reducer) ──
    messages: Annotated[List[BaseMessage], add_messages]

    # ── User Query & Parameters ────────────────────────────────────────
    input_query: str
    requested_intent: str       # "auto" | "tutor" | "rag" | "quiz" | "summarize" | "learning_assistant"
    difficulty: str             # "beginner" | "intermediate" | "advanced"
    document_ids: List[str]     # Scoped documents for RAG, Quizzes, or Summarization

    # ── Model & Provider Configuration ─────────────────────────────────
    llm_provider: str           # "gemini" | "ollama"
    model_name: str

    # ── Router Resolution ──────────────────────────────────────────────
    resolved_intent: str        # "tutor" | "rag" | "quiz" | "summarize" | "learning_assistant"
    router_reasoning: str

    # ── Context & Grounding ────────────────────────────────────────────
    retrieved_chunks: List[Dict[str, Any]]
    context_text: str
    is_document_grounded: bool   # True if grounded in docs, False if general knowledge

    # ── Generated Output ───────────────────────────────────────────────
    response_text: str
    citations: List[SourceCitationDict]

    # ── Specialized Agent Payloads ─────────────────────────────────────
    quiz_data: List[QuizQuestionDict]
    summary_data: SummaryDataDict
    learning_recommendations: List[str]
    tracked_topics: List[str]

    # ── Multimodal Context ─────────────────────────────────────────────
    image_id: Optional[str]
    image_bytes: Optional[bytes]
    image_mime_type: Optional[str]
    image_analysis: Optional[str]
    pdf_page_number: Optional[int]

    # ── Loop Prevention & Observability ────────────────────────────────
    iteration_count: int
    max_iterations: int
    latency_ms: int
    error: Optional[str]
    is_fallback: bool
    fallback_reason: Optional[str]

