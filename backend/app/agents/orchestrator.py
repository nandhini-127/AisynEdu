import logging
import time
from typing import Any, Dict, Optional
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.learning_assistant import LearningAssistantAgent
from app.agents.quiz_agent import QuizAgent
from app.agents.rag_agent import RAGAgent
from app.agents.router import RequestRouter
from app.agents.state import AgentState
from app.agents.summarizer_agent import SummarizerAgent
from app.agents.tutor_agent import TutorAgent

logger = logging.getLogger("edunex.agents.orchestrator")


async def router_node(state: AgentState) -> Dict:
    """Classifies user intent and routes to the appropriate capability."""
    try:
        routing_result = await RequestRouter.route(state)
        return {
            "resolved_intent": routing_result["resolved_intent"],
            "router_reasoning": routing_result["router_reasoning"],
            "iteration_count": state.get("iteration_count", 0) + 1,
        }
    except Exception as e:
        logger.error("Error in router_node: %s", str(e), exc_info=True)
        return {
            "resolved_intent": "tutor",
            "router_reasoning": f"Routing failed with error: {str(e)}. Defaulted to tutor.",
            "error": str(e),
        }


async def tutor_node(state: AgentState) -> Dict:
    """Executes the conceptual Tutor Agent."""
    try:
        return await TutorAgent.execute(state)
    except Exception as e:
        logger.error("TutorAgent error: %s", str(e), exc_info=True)
        return {
            "error": str(e),
            "response_text": f"I encountered an error preparing your explanation: {str(e)}",
        }


async def rag_node(state: AgentState) -> Dict:
    """Executes the document-grounded RAG Agent."""
    try:
        return await RAGAgent.execute(state)
    except Exception as e:
        logger.error("RAGAgent error: %s", str(e), exc_info=True)
        return {
            "error": str(e),
            "response_text": f"I encountered an error searching your study materials: {str(e)}",
        }


async def quiz_node(state: AgentState) -> Dict:
    """Executes the MCQ Quiz Generation Agent."""
    try:
        return await QuizAgent.execute(state)
    except Exception as e:
        logger.error("QuizAgent error: %s", str(e), exc_info=True)
        return {
            "error": str(e),
            "response_text": f"I encountered an error generating your practice quiz: {str(e)}",
        }


async def summarize_node(state: AgentState) -> Dict:
    """Executes the Summarization and Revision Notes Agent."""
    try:
        return await SummarizerAgent.execute(state)
    except Exception as e:
        logger.error("SummarizerAgent error: %s", str(e), exc_info=True)
        return {
            "error": str(e),
            "response_text": f"I encountered an error generating your summary: {str(e)}",
        }


async def learning_assistant_node(state: AgentState) -> Dict:
    """Executes the Personalized Learning Coach Agent."""
    try:
        return await LearningAssistantAgent.execute(state)
    except Exception as e:
        logger.error("LearningAssistantAgent error: %s", str(e), exc_info=True)
        return {
            "error": str(e),
            "response_text": f"I encountered an error preparing your study recommendations: {str(e)}",
        }


async def error_node(state: AgentState) -> Dict:
    """Fallback handler for unhandled graph routing errors."""
    err = state.get("error", "An unknown error occurred during agent processing.")
    return {
        "response_text": f"I apologize, but I could not fulfill your request due to an error: {err}",
        "is_document_grounded": False,
        "citations": [],
    }


async def postprocess_node(state: AgentState) -> Dict:
    """Validates execution boundaries and appends the assistant message."""
    resp = state.get("response_text", "No response generated.")
    return {
        "messages": [AIMessage(content=resp)],
    }


def route_decision(state: AgentState) -> str:
    """Conditional edge routing based on resolved intent and loop prevention."""
    # Loop prevention / execution limit check
    if state.get("iteration_count", 0) > state.get("max_iterations", 5):
        logger.warning("Agent execution limit exceeded. Routing to error_node.")
        return "error_node"

    intent = state.get("resolved_intent", "tutor").lower()
    if intent == "tutor":
        return "tutor_node"
    elif intent == "rag":
        return "rag_node"
    elif intent == "quiz":
        return "quiz_node"
    elif intent == "summarize":
        return "summarize_node"
    elif intent == "learning_assistant":
        return "learning_assistant_node"
    else:
        return "error_node"


def create_edunex_graph(checkpointer: Optional[Any] = None) -> Any:
    """
    Constructs and compiles the master EduNex AI LangGraph workflow.
    """
    workflow = StateGraph(AgentState)

    # Add processing nodes
    workflow.add_node("router_node", router_node)
    workflow.add_node("tutor_node", tutor_node)
    workflow.add_node("rag_node", rag_node)
    workflow.add_node("quiz_node", quiz_node)
    workflow.add_node("summarize_node", summarize_node)
    workflow.add_node("learning_assistant_node", learning_assistant_node)
    workflow.add_node("error_node", error_node)
    workflow.add_node("postprocess_node", postprocess_node)

    # Set Entry point
    workflow.add_edge(START, "router_node")

    # Add conditional branching
    workflow.add_conditional_edges(
        "router_node",
        route_decision,
        {
            "tutor_node": "tutor_node",
            "rag_node": "rag_node",
            "quiz_node": "quiz_node",
            "summarize_node": "summarize_node",
            "learning_assistant_node": "learning_assistant_node",
            "error_node": "error_node",
        },
    )

    # Connect all agent nodes to postprocess and exit
    workflow.add_edge("tutor_node", "postprocess_node")
    workflow.add_edge("rag_node", "postprocess_node")
    workflow.add_edge("quiz_node", "postprocess_node")
    workflow.add_edge("summarize_node", "postprocess_node")
    workflow.add_edge("learning_assistant_node", "postprocess_node")
    workflow.add_edge("error_node", "postprocess_node")
    workflow.add_edge("postprocess_node", END)

    memory = checkpointer or MemorySaver()
    return workflow.compile(checkpointer=memory)


class EduNexAssistant:
    """
    Unified entrypoint to invoke the compiled LangGraph assistant.
    """

    _app = None

    @classmethod
    def get_app(cls):
        if cls._app is None:
            cls._app = create_edunex_graph()
        return cls._app

    @classmethod
    async def process_student_query(
        cls,
        user_id: str,
        session_id: str,
        subject: str,
        query: str,
        requested_intent: str = "auto",
        difficulty: str = "intermediate",
        document_ids: Optional[list] = None,
        llm_provider: str = "gemini",
        model_name: Optional[str] = None,
        previous_messages: Optional[list] = None,
    ) -> AgentState:
        """
        Executes a student turn through the LangGraph agent workflow with conversation threading.
        """
        app = cls.get_app()

        initial_messages = []
        if previous_messages:
            initial_messages.extend(previous_messages)
        initial_messages.append(HumanMessage(content=query))

        initial_state: AgentState = {
            "user_id": user_id,
            "session_id": session_id,
            "subject": subject,
            "messages": initial_messages,
            "input_query": query,
            "requested_intent": requested_intent,
            "difficulty": difficulty,
            "document_ids": [str(d) for d in (document_ids or [])],
            "llm_provider": llm_provider,
            "model_name": model_name or "",
            "iteration_count": 0,
            "max_iterations": 5,
        }

        config = {
            "configurable": {"thread_id": str(session_id)},
            "recursion_limit": 10,
        }

        result = await app.ainvoke(initial_state, config=config)
        return result

