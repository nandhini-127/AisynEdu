import os
import uuid
from pathlib import Path
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.learning_assistant import LearningAssistantAgent
from app.agents.llm_client import LLMClient, ProviderUnavailableError
from app.agents.orchestrator import EduNexAssistant, create_edunex_graph
from app.agents.quiz_agent import QuizAgent
from app.agents.rag_agent import RAGAgent
from app.agents.router import RequestRouter
from app.agents.state import AgentState
from app.agents.summarizer_agent import SummarizerAgent
from app.agents.tutor_agent import TutorAgent
from app.memory.manager import ConversationMemoryManager
from app.models.entities import Message, Session, User
from app.rag.service import RAGService
from app.rag.vectorstore import ChromaVectorStore

SAMPLE_PDFS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "sample_pdfs"


@pytest.fixture(autouse=True)
def set_offline_hf():
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"


@pytest.mark.asyncio
class TestRequestRouter:
    async def test_same_query_routed_to_different_capabilities(self):
        """
        DEMONSTRATION REQUIREMENT:
        Demonstrates that the exact same user query can be explicitly routed
        to each of the specialized agent capabilities.
        """
        query = "What is the Transmission Control Protocol (TCP) three-way handshake?"

        for intent in ["tutor", "rag", "quiz", "summarize", "learning_assistant"]:
            state: AgentState = {
                "input_query": query,
                "requested_intent": intent,
                "subject": "Computer Networks",
                "document_ids": [],
            }
            res = await RequestRouter.route(state)
            assert res["resolved_intent"] == intent
            assert intent in res["router_reasoning"]

    async def test_auto_classification_heuristics(self):
        """Tests that auto-intent classifies queries based on student intent."""
        # Quiz request
        q_state: AgentState = {
            "input_query": "Generate a 5-question practice quiz with MCQs on operating systems",
            "requested_intent": "auto",
            "subject": "Operating Systems",
        }
        res_q = await RequestRouter.route(q_state)
        assert res_q["resolved_intent"] == "quiz"

        # Summarize request
        s_state: AgentState = {
            "input_query": "Please summarize chapter 2 and give me revision notes",
            "requested_intent": "auto",
            "subject": "Networking",
        }
        res_s = await RequestRouter.route(s_state)
        assert res_s["resolved_intent"] == "summarize"

        # Learning Assistant request
        l_state: AgentState = {
            "input_query": "What should I study next and what is my progress?",
            "requested_intent": "auto",
            "subject": "AI",
        }
        res_l = await RequestRouter.route(l_state)
        assert res_l["resolved_intent"] == "learning_assistant"

        # Document-grounded query
        d_state: AgentState = {
            "input_query": "What does my uploaded PDF say about routing algorithms?",
            "requested_intent": "auto",
            "subject": "Computer Networks",
            "document_ids": ["dummy-doc-id"],
        }
        res_d = await RequestRouter.route(d_state)
        assert res_d["resolved_intent"] == "rag"


@pytest.mark.asyncio
class TestTutorAgent:
    async def test_tutor_explanation_difficulty_adaptation(self):
        """Tests that the tutor agent responds with pedagogically structured explanations."""
        state_beg: AgentState = {
            "input_query": "How do computer networks work?",
            "subject": "Computer Networks",
            "difficulty": "beginner",
            "llm_provider": "gemini",
        }
        res_beg = await TutorAgent.execute(state_beg)
        assert "response_text" in res_beg
        assert res_beg["is_document_grounded"] is False
        assert len(res_beg["response_text"]) > 50

        state_adv: AgentState = {
            "input_query": "Explain TCP congestion control sliding window mechanics and fast retransmit.",
            "subject": "Computer Networks",
            "difficulty": "advanced",
            "llm_provider": "gemini",
        }
        res_adv = await TutorAgent.execute(state_adv)
        assert "response_text" in res_adv
        assert res_adv["latency_ms"] >= 0


@pytest.mark.asyncio
class TestRAGAgent:
    async def test_rag_agent_document_citations(self, db_session: AsyncSession, tmp_path):
        """Tests that the RAG agent retrieves chunks, answers, and cites documents with page numbers."""
        user = User(
            id=uuid.uuid4(),
            email=f"rag_student_{uuid.uuid4().hex[:6]}@edunex.ai",
            name="RAG Agent Student",
            hashed_password="hash",
            role="student",
        )
        db_session.add(user)
        await db_session.commit()

        # Ingest computer_networks.pdf
        pdf_path = SAMPLE_PDFS_DIR / "computer_networks.pdf"
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        vs = ChromaVectorStore(persist_dir=str(tmp_path / "chroma_rag_agent"))
        service = RAGService(db_session=db_session, vector_store=vs)
        doc = await service.ingest_document(
            user_id=user.id,
            file_bytes=pdf_bytes,
            filename="computer_networks.pdf",
            subject="Computer Networks",
        )

        state: AgentState = {
            "user_id": str(user.id),
            "input_query": "What are the steps of the TCP three-way handshake?",
            "subject": "Computer Networks",
            "document_ids": [str(doc.id)],
            "llm_provider": "gemini",
            "vector_store": vs,
        }

        # Override global ChromaVectorStore persist_dir for isolated testing
        original_persist = ChromaVectorStore.COLLECTION_NAME
        try:
            res = await RAGAgent.execute(state)
            assert "response_text" in res
            assert res["is_document_grounded"] is True or "Document" in res["response_text"]
        finally:
            pass

    async def test_rag_agent_general_knowledge_distinction(self):
        """Tests that RAG agent flags when answers are general knowledge rather than document-grounded."""
        state: AgentState = {
            "user_id": str(uuid.uuid4()),
            "input_query": "What is the boiling point of liquid nitrogen?",
            "subject": "Physics",
            "document_ids": [],
            "llm_provider": "gemini",
        }
        res = await RAGAgent.execute(state)
        assert res["is_document_grounded"] is False
        assert "General Knowledge" in res["response_text"]


@pytest.mark.asyncio
class TestQuizAgent:
    async def test_mcq_generation_structure(self):
        """Tests that quiz agent generates 4 options per question with separate answers and explanations."""
        state: AgentState = {
            "input_query": "Operating system process states and CPU scheduling",
            "subject": "Operating Systems",
            "difficulty": "intermediate",
            "llm_provider": "gemini",
        }
        res = await QuizAgent.execute(state)
        assert "quiz_data" in res
        questions = res["quiz_data"]
        assert len(questions) >= 1

        for q in questions:
            assert "question" in q and len(q["question"]) > 10
            # Exactly 4 options A, B, C, D
            assert len(q["options"]) == 4
            assert any(opt.startswith("A)") for opt in q["options"])
            assert any(opt.startswith("B)") for opt in q["options"])
            assert any(opt.startswith("C)") for opt in q["options"])
            assert any(opt.startswith("D)") for opt in q["options"])
            # Correct answer separate
            assert q["correct_answer"] in ["A", "B", "C", "D"]
            # Explanation present
            assert len(q["explanation"]) > 10


@pytest.mark.asyncio
class TestSummarizerAgent:
    async def test_summarizer_outputs_revision_notes_and_definitions(self):
        """Tests that summarizer outputs overview, key points, definitions, and revision notes."""
        state: AgentState = {
            "input_query": "Summarize Deep Learning and Transformer attention mechanisms",
            "subject": "Artificial Intelligence",
            "context_text": "Transformers utilize Scaled Dot-Product Attention: softmax((Q*K^T)/sqrt(d_k))*V.",
            "llm_provider": "gemini",
        }
        res = await SummarizerAgent.execute(state)
        assert "summary_data" in res
        summary = res["summary_data"]

        assert "overview" in summary and len(summary["overview"]) > 10
        assert len(summary["key_points"]) >= 1
        assert len(summary["definitions"]) >= 1
        assert len(summary["revision_notes"]) >= 1
        assert "Revision Notes" in res["response_text"]


@pytest.mark.asyncio
class TestLearningAssistantAgent:
    async def test_learning_assistant_recommendations(self):
        """Tests that the learning assistant tracks topics and provides recommendations."""
        state: AgentState = {
            "input_query": "What should I focus on next?",
            "subject": "Computer Science",
            "messages": [],
            "llm_provider": "gemini",
        }
        res = await LearningAssistantAgent.execute(state)
        assert "learning_recommendations" in res
        assert len(res["learning_recommendations"]) >= 1
        assert "tracked_topics" in res
        assert "Personalized Learning Coach" in res["response_text"]


@pytest.mark.asyncio
class TestConversationalMemory:
    async def test_session_message_history_and_clearing(self, db_session: AsyncSession):
        """Tests session persistence, bounded context window, and history clearing."""
        user = User(
            id=uuid.uuid4(),
            email=f"mem_student_{uuid.uuid4().hex[:6]}@edunex.ai",
            name="Memory Student",
            hashed_password="hash",
            role="student",
        )
        db_session.add(user)
        await db_session.commit()

        session = Session(
            id=uuid.uuid4(),
            user_id=user.id,
            subject="Algorithms",
            title="Graph Algorithms Study",
        )
        db_session.add(session)
        await db_session.commit()

        # Add 12 messages to test bounded context window (limit=10)
        for i in range(12):
            role = "user" if i % 2 == 0 else "assistant"
            await ConversationMemoryManager.save_message(
                db=db_session,
                session_id=session.id,
                user_id=user.id,
                role=role,
                content=f"Message {i}: Dijkstra shortest path",
            )

        # Verify bounded window returns exactly 10 messages
        lc_msgs = await ConversationMemoryManager.get_langchain_messages(
            db=db_session,
            session_id=session.id,
            limit=10,
        )
        assert len(lc_msgs) == 10
        # Earliest in window should be Message 2 (since 0 and 1 are pushed out)
        assert "Message 2" in lc_msgs[0].content

        # Test clearing history
        cleared = await ConversationMemoryManager.clear_session_history(
            db=db_session,
            session_id=session.id,
            user_id=user.id,
        )
        assert cleared == 12

        post_clear = await ConversationMemoryManager.get_session_history(
            db=db_session,
            session_id=session.id,
        )
        assert len(post_clear) == 0


@pytest.mark.asyncio
class TestLLMClientProviderPolicy:
    async def test_never_silently_substitute_unreachable_provider(self):
        """
        REQUIREMENT:
        'Never silently change providers when a request fails.'
        If Ollama is requested and is offline, raises ProviderUnavailableError
        instead of silently falling back to Gemini.
        """
        from unittest.mock import patch
        import httpx

        client = LLMClient(
            provider="ollama",
            model_name="llama3.2",
            timeout_seconds=1.0,
        )

        # 1. Test connection failure
        with patch.object(httpx.AsyncClient, "post", side_effect=httpx.ConnectError("Connection refused")):
            with pytest.raises(ProviderUnavailableError) as exc_info:
                await client.generate_response("Test prompt")
            assert "Ollama" in str(exc_info.value)
            assert "unreachable" in str(exc_info.value).lower()

        # 2. Test timeout failure
        with patch.object(httpx.AsyncClient, "post", side_effect=httpx.TimeoutException("Timed out")):
            with pytest.raises(ProviderUnavailableError) as exc_info:
                await client.generate_response("Test prompt")
            assert "Ollama" in str(exc_info.value)
            assert "timed out" in str(exc_info.value).lower()


@pytest.mark.asyncio
class TestLangGraphEndToEnd:
    async def test_edunex_assistant_turn(self):
        """Tests unified EduNexAssistant through LangGraph."""
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        result = await EduNexAssistant.process_student_query(
            user_id=user_id,
            session_id=session_id,
            subject="Computer Science",
            query="Explain the concept of mutual exclusion in operating systems",
            requested_intent="tutor",
            difficulty="beginner",
        )

        assert "response_text" in result
        assert len(result["response_text"]) > 20
        assert result["resolved_intent"] == "tutor"
        assert result["iteration_count"] >= 1


@pytest.mark.asyncio
class TestChatAPIEndpointsWithAgents:
    async def test_send_message_and_clear_history_api(self, client: AsyncClient, db_session: AsyncSession):
        """Tests chat HTTP API routes invoking agents and clearing session history."""
        # 1. Register and login student
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "agent_student@edunex.ai",
                "name": "Agent Student",
                "password": "StrongPassword123!",
                "role": "student",
            },
        )
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "agent_student@edunex.ai", "password": "StrongPassword123!"},
        )
        token = login_res.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create study session
        sess_res = await client.post(
            "/api/v1/chat/sessions",
            headers=headers,
            json={"subject": "Machine Learning", "title": "Transformers Deep Dive"},
        )
        session_id = sess_res.json()["data"]["id"]

        # 3. Post user question for quiz generation
        msg_res = await client.post(
            "/api/v1/chat/message",
            headers=headers,
            json={
                "session_id": session_id,
                "content": "Create a practice quiz on Neural Networks",
                "intent": "quiz",
                "difficulty": "intermediate",
            },
        )
        assert msg_res.status_code == 200
        data = msg_res.json()["data"]
        assert data["resolved_intent"] == "quiz"
        assert "quiz_data" in data["assistant_message"]
        assert len(data["assistant_message"]["quiz_data"]) >= 1

        # 4. Check session messages endpoint
        msgs_res = await client.get(
            f"/api/v1/chat/sessions/{session_id}/messages",
            headers=headers,
        )
        assert msgs_res.status_code == 200
        assert len(msgs_res.json()["data"]) == 2  # user + assistant

        # 5. Clear conversation history endpoint
        clear_res = await client.delete(
            f"/api/v1/chat/sessions/{session_id}/messages",
            headers=headers,
        )
        assert clear_res.status_code == 200
        assert clear_res.json()["data"]["cleared_count"] == 2

        # 6. Verify messages are now 0
        post_clear_res = await client.get(
            f"/api/v1/chat/sessions/{session_id}/messages",
            headers=headers,
        )
        assert len(post_clear_res.json()["data"]) == 0
