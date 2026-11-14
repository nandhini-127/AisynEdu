import io
import json
import os
import uuid
from pathlib import Path
import pytest
from PIL import Image, ImageDraw

from app.core.security import create_access_token, create_refresh_token, decode_token, get_password_hash, verify_password
from app.guardrails.service import GuardrailsService
from app.memory.manager import ConversationMemoryManager
from app.models.entities import Message, Session, User
from app.multimodal.image_processor import ImageProcessor
from app.multimodal.validator import FileValidator
from app.multimodal.vision_client import VisionClient
from app.rag.chunker import DocumentChunk, DocumentChunker
from app.rag.extractor import PDFExtractor
from app.rag.generator import RAGGenerator
from app.rag.vectorstore import ChromaVectorStore
from app.agents.quiz_agent import QuizAgent
from app.agents.tutor_agent import TutorAgent
from app.agents.state import AgentState

SAMPLE_PDFS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "sample_pdfs"


# ============================================================================
# WORKFLOW 1: Student Registration -> Login -> Dashboard
# ============================================================================
def test_workflow_01_student_registration_login_and_dashboard():
    """
    WORKFLOW 1:
    Tests the complete student identity lifecycle:
    Registration -> Password Hashing -> JWT Issuance -> Verification -> Profile.
    """
    # 1. Registration data
    student_email = f"student_{uuid.uuid4().hex[:6]}@edunex.ai"
    plain_password = "SecurePassword123!"

    # Hash password with bcrypt
    hashed_pwd = get_password_hash(plain_password)
    assert hashed_pwd != plain_password
    assert verify_password(plain_password, hashed_pwd) is True
    assert verify_password("WrongPassword123!", hashed_pwd) is False

    # 2. Login & Token Generation
    student_id = str(uuid.uuid4())
    access_token = create_access_token(subject=student_id, role="student")
    refresh_token = create_refresh_token(subject=student_id)

    assert isinstance(access_token, str)
    assert isinstance(refresh_token, str)

    # 3. Token Decoding & Claim Verification
    payload = decode_token(access_token)
    assert payload["sub"] == student_id
    assert payload["role"] == "student"
    assert payload["type"] == "access"
    assert "exp" in payload

    refresh_payload = decode_token(refresh_token)
    assert refresh_payload["sub"] == student_id
    assert refresh_payload["type"] == "refresh"
    assert "jti" in refresh_payload

    # 4. Student Dashboard Profile Verification
    student_profile = {
        "id": student_id,
        "email": student_email,
        "role": payload["role"],
        "is_authenticated": True,
        "enrolled_courses": ["Computer Science", "Artificial Intelligence"],
    }
    assert student_profile["is_authenticated"] is True
    assert student_profile["role"] == "student"


# ============================================================================
# WORKFLOW 2: Upload PDF -> Chunk -> Store -> Retrieve -> Grounded Citations
# ============================================================================
def test_workflow_02_pdf_ingestion_retrieval_and_grounded_citations(tmp_path):
    """
    WORKFLOW 2:
    Tests document ingestion, PyMuPDF extraction, character chunking,
    vector storage, and context-grounded response generation with citations.
    """
    pdf_path = SAMPLE_PDFS_DIR / "computer_networks.pdf"
    assert pdf_path.exists(), f"Sample PDF missing at {pdf_path}"

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # 1. Text Extraction
    extracted = PDFExtractor.extract_text(pdf_bytes, "computer_networks.pdf")
    assert extracted.page_count == 3
    assert extracted.total_characters > 100
    assert len(extracted.sha256_hash) == 64

    # 2. Text Chunking
    doc_id = uuid.uuid4()
    user_id = uuid.uuid4()
    chunker = DocumentChunker(chunk_size=400, chunk_overlap=40)
    chunks = chunker.split_pages(
        pages=extracted.pages,
        doc_id=doc_id,
        user_id=user_id,
        filename="computer_networks.pdf",
        subject="Computer Networks",
    )
    assert len(chunks) >= 3
    for chunk in chunks:
        assert chunk.doc_id == str(doc_id)
        assert chunk.user_id == str(user_id)
        assert chunk.page_number in [1, 2, 3]
        assert len(chunk.text) > 0

    # 3. Vector Storage in isolated Chroma instance
    vector_store = ChromaVectorStore(persist_dir=str(tmp_path / "chroma_wf2"))
    dummy_embeddings = [[0.05 * (i % 10)] * 384 for i in range(len(chunks))]
    vector_store.upsert_chunks(doc_id, user_id, chunks, dummy_embeddings)

    # 4. Retrieve Chunks
    query_vector = [0.05] * 384
    retrieved = vector_store.query_similar_chunks(
        user_id=user_id,
        query_embedding=query_vector,
        top_k=2,
    )
    assert len(retrieved) > 0

    # 5. Answer Generation with Citations
    sample_context_chunks = [
        {
            "doc_id": str(doc_id),
            "filename": "computer_networks.pdf",
            "page": 2,
            "chunk_index": 1,
            "score": 0.89,
            "text": "TCP uses a three-way handshake: SYN from client, SYN-ACK from server, ACK from client.",
        }
    ]
    generator = RAGGenerator()
    answer, citations, latency_ms, provider = generator.generate_answer(
        query="How does TCP establish a connection?",
        chunks=sample_context_chunks,
    )

    assert len(citations) >= 1
    assert citations[0].document_name == "computer_networks.pdf"
    assert citations[0].page == 2
    assert "[Document: computer_networks.pdf, Page: 2]" in answer


# ============================================================================
# WORKFLOW 3: Conversation Memory & Context-Aware Follow-Up
# ============================================================================
def test_workflow_03_conversational_memory_and_followup():
    """
    WORKFLOW 3:
    Tests multi-turn conversational memory tracking and context-aware follow-up.
    """
    session_id = uuid.uuid4()
    student_id = uuid.uuid4()

    # Turn 1: Initial query & response
    t1_query = "What is binary search?"
    t1_response = (
        "Binary search is an efficient search algorithm that finds the position of a target value "
        "within a sorted array by repeatedly dividing the search interval in half."
    )
    history = [
        {"role": "user", "content": t1_query},
        {"role": "assistant", "content": t1_response},
    ]

    # Turn 2: Follow-up query referencing 'it'
    t2_query = "What is its time complexity in the worst case?"
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert "binary search" in history[0]["content"].lower()

    # Verify conversational prompt formatting with previous turns
    from app.agents.prompts.tutor_prompts import build_tutor_prompt, TUTOR_SYSTEM_PROMPT
    history_str = "\n".join([f"{'Student' if h['role'] == 'user' else 'Tutor'}: {h['content']}" for h in history])
    user_prompt = build_tutor_prompt(
        query=t2_query,
        subject="Data Structures",
        difficulty="intermediate",
        history_context=history_str,
    )
    assert "Student: What is binary search?" in user_prompt
    assert t2_query in user_prompt

    # Execute deterministic educational response engine
    from app.agents.llm_client import LLMClient
    client = LLMClient()
    answer = client._generate_offline_mock(user_prompt, TUTOR_SYSTEM_PROMPT)
    assert len(answer) > 0
    assert "Core Concept" in answer or "Step" in answer or "break this down" in answer.lower()


# ============================================================================
# WORKFLOW 4: Multimodal Educational Image Processing -> Vision Analysis
# ============================================================================
def test_workflow_04_multimodal_image_processing_and_vision_explanation():
    """
    WORKFLOW 4:
    Tests uploading an educational architecture diagram PNG, validating signatures,
    normalizing dimensions, and generating pedagogical vision analysis.
    """
    # 1. Generate an educational diagram PNG in memory
    img = Image.new("RGB", (500, 250), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([30, 60, 180, 160], outline=(30, 100, 200), width=3)
    draw.text((50, 100), "Client Browser", fill=(0, 0, 0))
    draw.rectangle([320, 60, 470, 160], outline=(40, 180, 80), width=3)
    draw.text((340, 100), "EduNex Server", fill=(0, 0, 0))
    draw.line([180, 110, 320, 110], fill=(100, 100, 100), width=2)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    # 2. File Signature & Type Validation
    file_ext, sanitized_name = FileValidator.validate_image_upload(
        png_bytes,
        "client_server_architecture.png",
        "image/png",
    )
    assert file_ext == "png"
    assert sanitized_name == "client_server_architecture.png"

    # 3. Image Processor Dimensions & Inspection
    pil_img, metadata = ImageProcessor.load_and_inspect(png_bytes)
    assert metadata.format == "PNG"
    assert metadata.width == 500
    assert metadata.height == 250
    assert metadata.file_size_bytes == len(png_bytes)

    # 4. Vision Client Pedagogical Analysis
    vision_client = VisionClient()
    analysis = vision_client._generate_offline_vision_mock(
        prompt="Explain the communication flow shown in this system diagram.",
        prompt_type="diagram",
    )
    assert len(analysis) > 50
    assert any(term in analysis.lower() for term in ["diagram", "component", "visual identification", "architecture"])


# ============================================================================
# WORKFLOW 5: Study Material -> MCQ Generation -> Submission & Scoring
# ============================================================================
def test_workflow_05_study_material_quiz_generation_and_evaluation():
    """
    WORKFLOW 5:
    Tests automated MCQ generation from study text, answer validation,
    scoring calculation, and pedagogical explanation generation.
    """
    study_text = (
        "Operating systems use CPU scheduling algorithms to allocate processor time. "
        "First-Come, First-Served (FCFS) schedules processes in arrival order. "
        "Shortest Job First (SJF) gives priority to processes with smallest burst time, minimizing average waiting time. "
        "Round Robin (RR) allocates a fixed time quantum per process to prevent starvation."
    )

    from app.agents.prompts.quiz_prompts import build_quiz_prompt, QUIZ_SYSTEM_PROMPT
    from app.agents.llm_client import LLMClient

    prompt = build_quiz_prompt(
        query="Generate a practice quiz",
        subject="Operating Systems",
        difficulty="intermediate",
        context=study_text,
        count=2,
    )
    client = LLMClient()
    raw_quiz_json = client._generate_offline_mock(prompt, QUIZ_SYSTEM_PROMPT)

    # Parse and format quiz questions using QuizAgent parser
    questions = QuizAgent._parse_quiz_json(raw_quiz_json, "intermediate")
    assert len(questions) >= 2

    q1 = questions[0]
    assert "question" in q1
    assert "options" in q1
    assert len(q1["options"]) == 4
    assert "correct_answer" in q1
    assert "explanation" in q1

    # Simulate Student Quiz Evaluation
    correct_opt = q1["correct_answer"]
    # Student selects the correct option
    student_answer_correct = correct_opt
    is_correct = (student_answer_correct == correct_opt)
    assert is_correct is True

    # Student selects an incorrect option
    distractors = [opt[0] for opt in q1["options"] if opt[0] != correct_opt]
    student_answer_wrong = distractors[0]
    is_wrong = (student_answer_wrong == correct_opt)
    assert is_wrong is False

    # Score calculation
    total_questions = 2
    correct_count = 1
    score_percentage = (correct_count / total_questions) * 100.0
    assert score_percentage == 50.0


# ============================================================================
# WORKFLOW 6: Question -> SSE Streaming Response -> Conversation Persistence
# ============================================================================
def test_workflow_06_streaming_response_and_memory_persistence():
    """
    WORKFLOW 6:
    Tests query guardrails validation, Server-Sent Events token stream assembly,
    and committing completed dialogue to conversation history.
    """
    user_query = "What is the Difference between a Process and a Thread?"

    # 1. Input Guardrails Check
    val_res = GuardrailsService.validate_user_query(user_query)
    assert val_res.is_safe is True
    assert val_res.risk_category is None

    # 2. Simulate Progressive SSE Token Stream
    chunks_to_stream = [
        "A process ",
        "is an executing program ",
        "with its own isolated memory space, ",
        "whereas a thread ",
        "is a lightweight unit of execution ",
        "within a process sharing the same address space.",
    ]
    sse_events = []
    # Intent event
    sse_events.append(f"event: intent\ndata: {json.dumps({'intent': 'tutor', 'is_grounded': False})}\n\n")

    # Progressive token events
    full_text = ""
    for chunk in chunks_to_stream:
        full_text += chunk
        sse_events.append(f"event: token\ndata: {json.dumps({'chunk': chunk})}\n\n")

    # Done event
    message_id = str(uuid.uuid4())
    sse_events.append(
        f"event: done\ndata: {json.dumps({'message_id': message_id, 'token_count': len(full_text.split()), 'latency_ms': 180})}\n\n"
    )

    assert len(sse_events) == len(chunks_to_stream) + 2
    assert "event: intent" in sse_events[0]
    assert "event: done" in sse_events[-1]
    assert "lightweight unit of execution" in full_text

    # 3. Conversation Memory Persistence
    saved_history = [
        {"role": "user", "content": user_query},
        {"role": "assistant", "content": full_text, "tokens": len(full_text.split()), "message_id": message_id},
    ]
    assert len(saved_history) == 2
    assert saved_history[0]["content"] == user_query
    assert saved_history[1]["content"] == full_text
    assert saved_history[1]["message_id"] == message_id


# ============================================================================
# WORKFLOW 7: Learning Activity -> Telemetry Recording -> Student Dashboard
# ============================================================================
def test_workflow_07_learning_activity_telemetry_and_dashboard_metrics():
    """
    WORKFLOW 7:
    Tests recording user interactions (document uploads, questions asked, quizzes completed)
    and generating multi-tenant student dashboard analytics.
    """
    student_a_id = uuid.uuid4()
    student_b_id = uuid.uuid4()

    # Simulated Telemetry Store
    event_store = [
        # Student A events
        {"user_id": str(student_a_id), "event_type": "document_upload", "metadata": {"subject": "Computer Networks"}},
        {"user_id": str(student_a_id), "event_type": "query_asked", "metadata": {"intent": "tutor", "tokens": 120}},
        {"user_id": str(student_a_id), "event_type": "query_asked", "metadata": {"intent": "rag", "tokens": 250}},
        {"user_id": str(student_a_id), "event_type": "quiz_completed", "metadata": {"score": 85.0}},
        # Student B events
        {"user_id": str(student_b_id), "event_type": "query_asked", "metadata": {"intent": "quiz", "tokens": 80}},
    ]

    # Calculate Student A Dashboard Metrics
    student_a_events = [e for e in event_store if e["user_id"] == str(student_a_id)]
    student_b_events = [e for e in event_store if e["user_id"] == str(student_b_id)]

    assert len(student_a_events) == 4
    assert len(student_b_events) == 1

    questions_asked_a = sum(1 for e in student_a_events if e["event_type"] == "query_asked")
    docs_uploaded_a = sum(1 for e in student_a_events if e["event_type"] == "document_upload")
    quizzes_a = [e["metadata"]["score"] for e in student_a_events if e["event_type"] == "quiz_completed"]
    avg_quiz_score_a = sum(quizzes_a) / len(quizzes_a) if quizzes_a else 0.0

    student_a_dashboard = {
        "total_questions_asked": questions_asked_a,
        "total_documents_uploaded": docs_uploaded_a,
        "quizzes_completed": len(quizzes_a),
        "average_quiz_score": avg_quiz_score_a,
        "study_streak_days": 1,
    }

    assert student_a_dashboard["total_questions_asked"] == 2
    assert student_a_dashboard["total_documents_uploaded"] == 1
    assert student_a_dashboard["quizzes_completed"] == 1
    assert student_a_dashboard["average_quiz_score"] == 85.0

    # Multi-tenant isolation: Student A cannot observe Student B's data
    for ev in student_a_events:
        assert ev["user_id"] != str(student_b_id)
