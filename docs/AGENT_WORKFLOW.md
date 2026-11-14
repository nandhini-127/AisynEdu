# EduNex AI — Agent Workflow Design

> **Version:** 1.0  
> **Date:** 2026-11-12  
> **Framework:** LangGraph 0.2+ (StateGraph)  
> **LLM:** Google Gemini 2.0 Flash (primary) + Ollama (optional)

---

## Table of Contents
1. [Agent Overview](#1-agent-overview)
2. [LangGraph State Definition](#2-langgraph-state-definition)
3. [Master Orchestration Workflow](#3-master-orchestration-workflow)
4. [Safety Guardrail Agent](#4-safety-guardrail-agent)
5. [Q&A Agent Workflow](#5-qa-agent-workflow)
6. [Quiz Generation Agent Workflow](#6-quiz-generation-agent-workflow)
7. [Summarization Agent Workflow](#7-summarization-agent-workflow)
8. [Progress Insights Agent Workflow](#8-progress-insights-agent-workflow)
9. [LLM Provider Router](#9-llm-provider-router)
10. [Memory & Context Management](#10-memory--context-management)
11. [System Prompt Templates](#11-system-prompt-templates)
12. [Error Handling & Retry Strategy](#12-error-handling--retry-strategy)
13. [Agent File Structure](#13-agent-file-structure)

---

## 1. Agent Overview

EduNex AI uses **5 specialized agents** orchestrated by LangGraph:

| Agent | File | Responsibility |
|-------|------|---------------|
| **Safety Guardrail** | `safety_agent.py` | Block unsafe inputs before any LLM call |
| **Router** | `orchestrator.py` | Classify intent, route to appropriate agent |
| **Q&A Agent** | `qa_agent.py` | Answer questions using RAG + conversational memory |
| **Quiz Agent** | `quiz_agent.py` | Generate structured quiz questions from documents |
| **Summarizer Agent** | `summarizer_agent.py` | Create hierarchical summaries of documents |
| **Progress Agent** | `progress_agent.py` | Analyze learning data and generate personalized insights |

### Design Principles
1. **Safety First** — Every input passes through the guardrail before reaching any LLM
2. **RAG-Augmented** — All educational responses are grounded in uploaded documents
3. **Stateful** — LangGraph state persists across agent nodes in a single invocation
4. **Streamable** — All LLM calls use streaming mode; tokens are queued for SSE
5. **Idempotent** — Failed nodes can be retried without corrupting state
6. **Observable** — Every node logs entry/exit, latency, and token count

---

## 2. LangGraph State Definition

```python
# agents/state.py

from typing import TypedDict, Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class SourceCitation(TypedDict):
    title: str
    page: Optional[int]
    score: float
    snippet: str
    doc_id: str


class QuizQuestion(TypedDict):
    id: int
    type: str           # "mcq" | "true_false" | "fill_blank"
    question: str
    options: Optional[list[str]]
    answer: str | bool
    explanation: str
    source_chunk: Optional[str]


class EduNexState(TypedDict, total=False):
    # ── Input (set by ChatService before invoking) ──────────────────
    user_id: str
    session_id: str
    message_id: str           # SSE queue key
    subject: str              # e.g. "Mathematics"
    question: str             # Raw user input
    intent: str               # "auto"|"qa"|"quiz"|"summarize"|"progress"
    document_ids: list[str]   # Docs to scope RAG to
    llm_provider: str         # "gemini" | "ollama"
    model_name: str

    # ── Safety ──────────────────────────────────────────────────────
    safety_passed: bool
    safety_reason: str        # Populated if blocked

    # ── Routing ─────────────────────────────────────────────────────
    resolved_intent: str      # After auto-classification
    routing_confidence: float

    # ── RAG ─────────────────────────────────────────────────────────
    retrieved_chunks: list[dict]
    context: str              # Merged context for prompt
    sources: list[SourceCitation]

    # ── Q&A Output ──────────────────────────────────────────────────
    response: str             # Final answer text

    # ── Quiz Output ─────────────────────────────────────────────────
    quiz_questions: list[QuizQuestion]
    quiz_title: str

    # ── Summary Output ──────────────────────────────────────────────
    summary: str
    summary_bullets: list[str]

    # ── Progress Output ─────────────────────────────────────────────
    progress_data: dict
    progress_insights: str

    # ── Conversation Memory ─────────────────────────────────────────
    # Annotated with add_messages reducer for LangGraph message accumulation
    chat_history: Annotated[list[BaseMessage], add_messages]

    # ── Telemetry ───────────────────────────────────────────────────
    total_token_count: int
    total_latency_ms: int
    node_trace: list[str]     # Ordered list of nodes visited
```

---

## 3. Master Orchestration Workflow

```mermaid
flowchart TD
    START(["START"])

    SAFETY["safety_node\n────────────────\nCheck: prompt injection\nCheck: harmful content\nCheck: off-topic\nCheck: input length"]

    ROUTE["router_node\n────────────────\nClassify intent:\n• qa (default)\n• quiz\n• summarize\n• progress\nSet resolved_intent"]

    QA_NODE["qa_node\n────────────────\nRAG retrieval\nContext building\nGemini generation\nCitation extraction"]

    QUIZ_NODE["quiz_node\n────────────────\nDocument context\nQuiz generation\nFormat + validate\nStructure output"]

    SUM_NODE["summarize_node\n────────────────\nFull document load\nHierarchical chunking\nSummary generation\nBullet points"]

    PROG_NODE["progress_node\n────────────────\nQuery progress DB\nPattern analysis\nInsights generation\nRecommendations"]

    STREAM_NODE["stream_node\n────────────────\nPublish to SSE queue\nFormat final response\nAttach metadata"]

    MEMORY_NODE["memory_node\n────────────────\nSave to PostgreSQL\nUpdate ChromaDB ctx\nUpdate progress_daily\nLog usage_event"]

    END_NODE(["END"])

    BLOCKED["blocked_response_node\n────────────────\nReturn safety\nrejection message\nLog blocked event"]

    START --> SAFETY
    SAFETY -->|"safety_passed=True"| ROUTE
    SAFETY -->|"safety_passed=False"| BLOCKED
    BLOCKED --> STREAM_NODE

    ROUTE -->|"qa"| QA_NODE
    ROUTE -->|"quiz"| QUIZ_NODE
    ROUTE -->|"summarize"| SUM_NODE
    ROUTE -->|"progress"| PROG_NODE

    QA_NODE --> STREAM_NODE
    QUIZ_NODE --> STREAM_NODE
    SUM_NODE --> STREAM_NODE
    PROG_NODE --> STREAM_NODE

    STREAM_NODE --> MEMORY_NODE --> END_NODE

    style SAFETY fill:#ff6b6b,color:#fff
    style BLOCKED fill:#ff6b6b,color:#fff
    style QA_NODE fill:#4ecdc4,color:#fff
    style QUIZ_NODE fill:#45b7d1,color:#fff
    style SUM_NODE fill:#96ceb4,color:#fff
    style PROG_NODE fill:#ffeaa7,color:#333
```

### Graph Build Code Pattern

```python
# agents/orchestrator.py

from langgraph.graph import StateGraph, START, END
from .state import EduNexState
from .safety_agent import safety_node, blocked_response_node
from .qa_agent import qa_node
from .quiz_agent import quiz_node
from .summarizer_agent import summarize_node
from .progress_agent import progress_node
from .stream_node import stream_node
from .memory_node import memory_node


def should_continue(state: EduNexState) -> str:
    """Conditional edge: route after safety check."""
    if not state.get("safety_passed", True):
        return "blocked"
    return "route"


def route_intent(state: EduNexState) -> str:
    """Conditional edge: route after intent classification."""
    return state.get("resolved_intent", "qa")


def build_graph() -> StateGraph:
    workflow = StateGraph(EduNexState)

    # Register nodes
    workflow.add_node("safety",    safety_node)
    workflow.add_node("router",    router_node)
    workflow.add_node("blocked",   blocked_response_node)
    workflow.add_node("qa",        qa_node)
    workflow.add_node("quiz",      quiz_node)
    workflow.add_node("summarize", summarize_node)
    workflow.add_node("progress",  progress_node)
    workflow.add_node("stream",    stream_node)
    workflow.add_node("memory",    memory_node)

    # Edges
    workflow.add_edge(START, "safety")
    workflow.add_conditional_edges("safety", should_continue,
        {"blocked": "blocked", "route": "router"})
    workflow.add_conditional_edges("router", route_intent,
        {"qa": "qa", "quiz": "quiz", "summarize": "summarize", "progress": "progress"})
    workflow.add_edge("blocked",   "stream")
    workflow.add_edge("qa",        "stream")
    workflow.add_edge("quiz",      "stream")
    workflow.add_edge("summarize", "stream")
    workflow.add_edge("progress",  "stream")
    workflow.add_edge("stream",    "memory")
    workflow.add_edge("memory",    END)

    return workflow.compile()


edunex_graph = build_graph()
```

---

## 4. Safety Guardrail Agent

```mermaid
flowchart TD
    INPUT["state.question"]

    subgraph CHECKS["Safety Checks (sequential)"]
        LEN_CHK["Length Check\n> 4000 chars → reject"]
        INJ_CHK["Prompt Injection Detection\n'ignore previous', 'act as', 'jailbreak'\npattern matching + LLM classifier"]
        TOPIC_CHK["Off-Topic Guard\nMust relate to: academics, study,\nlearning, education, subjects\nKeyword + LLM classification"]
        HARM_CHK["Harmful Content\nGemini Safety Filters\n(HARM_BLOCK_MEDIUM_AND_ABOVE)"]
        LANG_CHK["Language Check\nEnglish only (Phase 1)\ndetect non-English → warn"]
    end

    PASS["state.safety_passed = True\nContinue to router_node"]
    BLOCK["state.safety_passed = False\nstate.safety_reason = reason\nContinue to blocked_node"]

    INPUT --> LEN_CHK --> INJ_CHK --> TOPIC_CHK --> HARM_CHK --> LANG_CHK
    LANG_CHK -->|all pass| PASS
    LEN_CHK -->|fail| BLOCK
    INJ_CHK -->|fail| BLOCK
    TOPIC_CHK -->|fail| BLOCK
    HARM_CHK -->|fail| BLOCK
```

**Safety Rejection Messages:**

| Reason | User Message |
|--------|-------------|
| `too_long` | "Your message is too long. Please keep it under 4000 characters." |
| `prompt_injection` | "I detected an attempt to manipulate my instructions. I'm here to help with studies only." |
| `off_topic` | "I'm EduNex AI, your educational assistant. I can only help with academic subjects and studying." |
| `harmful_content` | "I can't respond to that content. Please ask an educational question." |
| `unsupported_language` | "Please ask your question in English. Multi-language support is coming soon." |

---

## 5. Q&A Agent Workflow

```mermaid
flowchart TD
    START_QA["qa_node entry\nstate: {question, subject,\ndocument_ids, chat_history}"]

    EMBED_Q["Embed Query\nSentence Transformer\nall-MiniLM-L6-v2"]

    RETRIEVE["ChromaDB Retrieval\ntop_k=5\nthreshold=0.70\nfilter by document_ids"]

    HAS_CTX{{"Retrieved\nchunks > 0?"}}

    BUILD_CTX["Build Context\nOrder by score DESC\nTruncate to 3000 tokens\nFormat with page refs"]

    FALLBACK_CTX["Use Gemini's built-in\nknowledge for subject\n(no document context)"]

    HIST_FMT["Format Chat History\nLast 6 messages\n(3 turns) for context"]

    PROMPT_B["Build Prompt\nSystem: educational expert\nContext: retrieved chunks\nHistory: last 3 turns\nQuestion: user input"]

    LLM_CALL["LLM Call (streaming)\nGemini 2.0 Flash\ntemp=0.3, max_tokens=1500"]

    STREAM_TOK["Stream tokens\nto SSE queue"]

    CITE_EXT["Citation Extractor\nMap [S1] [S2] refs\nto source metadata"]

    SET_STATE["Set state:\nresponse, sources,\ntoken_count, latency_ms"]

    START_QA --> EMBED_Q --> RETRIEVE --> HAS_CTX
    HAS_CTX -->|"Yes"| BUILD_CTX
    HAS_CTX -->|"No"| FALLBACK_CTX
    BUILD_CTX & FALLBACK_CTX --> HIST_FMT --> PROMPT_B --> LLM_CALL
    LLM_CALL --> STREAM_TOK --> CITE_EXT --> SET_STATE
```

---

## 6. Quiz Generation Agent Workflow

```mermaid
flowchart TD
    START_QUIZ["quiz_node entry\nstate: {subject, topic,\ndocument_ids, difficulty,\nquestion_count, question_types}"]

    RETRIEVE_Q["Broad RAG Retrieval\ntop_k=15, threshold=0.60\n(wider net for quiz material)"]

    TOPIC_FILTER["Topic Filter\nIf topic specified:\nfilter chunks by topic relevance"]

    SAMPLE_CTX["Sample Context\nSelect diverse chunks\nacross document sections"]

    QUIZ_PROMPT["Build Quiz Prompt\nSystem: quiz master\nRules: format, difficulty,\nno duplicate questions,\nmust cite source"]

    LLM_CALL_Q["LLM Call\nGemini 2.0 Flash\ntemp=0.5 (more creative)\nmax_tokens=3000"]

    PARSE_JSON["Parse JSON Output\nExtract question array\nValidate schema"]

    VALIDATE_Q["Quiz Validator\n• Check question count\n• Check format compliance\n• Dedup questions\n• Verify answers exist"]

    RETRY_Q{{"Valid?"}}
    RETRY["Retry with feedback\n(max 2 retries)"]

    SET_QUIZ["Set state:\nquiz_questions,\nquiz_title"]

    FAIL_QUIZ["Return partial quiz\nor error message"]

    START_QUIZ --> RETRIEVE_Q --> TOPIC_FILTER --> SAMPLE_CTX --> QUIZ_PROMPT --> LLM_CALL_Q --> PARSE_JSON --> VALIDATE_Q --> RETRY_Q
    RETRY_Q -->|"Yes"| SET_QUIZ
    RETRY_Q -->|"No, attempt < 2"| RETRY --> LLM_CALL_Q
    RETRY_Q -->|"No, attempt = 2"| FAIL_QUIZ
```

**Quiz JSON Format requested from LLM:**
```json
{
  "title": "Thermodynamics — Medium Quiz",
  "questions": [
    {
      "id": 1,
      "type": "mcq",
      "question": "Which law of thermodynamics...",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": "Option B",
      "explanation": "Because...",
      "source_chunk": "Chapter 4, page 12"
    }
  ]
}
```

---

## 7. Summarization Agent Workflow

```mermaid
flowchart TD
    START_SUM["summarize_node entry\nstate: {document_ids, subject}"]

    DOC_CHECK{{"Single doc\nor multiple?"}}

    LOAD_SINGLE["Load all chunks\nfor single document\nordered by chunk_index"]

    LOAD_MULTI["Load representative chunks\nfrom each document\n(top 10 per doc)"]

    HIER_CHECK{{"Total chunks\n> 20?"}}

    MAP_REDUCE["Map-Reduce Summarization\n1. Summarize each chunk\n2. Combine intermediate summaries\n3. Final synthesis"]

    DIRECT_SUM["Direct Summarization\nAll chunks in one prompt\n(fits in context window)"]

    SUM_PROMPT["Build Summary Prompt\nSystem: academic summarizer\nAudience: student\nStyle: clear, structured\nOutput: sections + bullets"]

    LLM_CALL_S["LLM Call\nGemini 2.0 Flash\ntemp=0.2 (factual)\nmax_tokens=2000"]

    FORMAT_S["Format Output\nExtract section headers\nExtract bullet points\nAdd document references"]

    SET_SUM["Set state:\nsummary, summary_bullets"]

    START_SUM --> DOC_CHECK
    DOC_CHECK -->|"Single"| LOAD_SINGLE
    DOC_CHECK -->|"Multiple"| LOAD_MULTI
    LOAD_SINGLE & LOAD_MULTI --> HIER_CHECK
    HIER_CHECK -->|"Yes > 20"| MAP_REDUCE
    HIER_CHECK -->|"No <= 20"| DIRECT_SUM
    MAP_REDUCE & DIRECT_SUM --> SUM_PROMPT --> LLM_CALL_S --> FORMAT_S --> SET_SUM
```

---

## 8. Progress Insights Agent Workflow

```mermaid
flowchart TD
    START_PROG["progress_node entry\nstate: {user_id, subject (optional)}"]

    QUERY_PG["Query PostgreSQL\n• progress_daily (30d)\n• quiz_attempts (all)\n• session count\n• streak calculation"]

    BUILD_STATS["Build Statistics\n• avg quiz score per subject\n• study frequency\n• mastery scores\n• weakest topics\n• strongest topics"]

    PROG_PROMPT["Build Progress Prompt\nSystem: learning coach\nData: student statistics\nTask: personalized insights\n+ actionable recommendations"]

    LLM_CALL_P["LLM Call\nGemini 2.0 Flash\ntemp=0.4\nmax_tokens=800"]

    FORMAT_P["Format Insights\nStructured text:\n• Strengths\n• Areas for improvement\n• Study recommendations\n• Next steps"]

    SET_PROG["Set state:\nprogress_data,\nprogress_insights"]

    START_PROG --> QUERY_PG --> BUILD_STATS --> PROG_PROMPT --> LLM_CALL_P --> FORMAT_P --> SET_PROG
```

---

## 9. LLM Provider Router

```mermaid
flowchart TD
    REQ["LLM Request\n{prompt, temperature,\nmax_tokens, stream}"]

    PREF["Check user.preferred_llm\n+ state.llm_provider override"]

    GEMINI_CHECK{{"Gemini\navailable?"}}
    OLLAMA_CHECK{{"Ollama\navailable?"}}

    GEMINI["Google Gemini\n2.0 Flash\nvia langchain-google-genai"]
    OLLAMA["Ollama Local\nllama3.2:3b (default)\nvia langchain-community"]
    FALLBACK["Fallback Message\n'AI service temporarily\nunavailable. Please retry.'"]

    GEMINI_CALL["ChatGoogleGenerativeAI\n.stream() for SSE\nRetry: 3x with backoff"]
    OLLAMA_CALL["ChatOllama\n.stream() for SSE\nRetry: 2x with backoff"]

    RESPONSE["Streamed Response\nchunks → SSE queue"]

    REQ --> PREF
    PREF -->|"gemini"| GEMINI_CHECK
    PREF -->|"ollama"| OLLAMA_CHECK
    GEMINI_CHECK -->|"Yes"| GEMINI --> GEMINI_CALL --> RESPONSE
    GEMINI_CHECK -->|"No"| OLLAMA_CHECK
    OLLAMA_CHECK -->|"Yes"| OLLAMA --> OLLAMA_CALL --> RESPONSE
    OLLAMA_CHECK -->|"No"| FALLBACK --> RESPONSE
```

**LLM Service Code Pattern:**

```python
# services/llm_service.py

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatOllama

class LLMService:
    def get_llm(self, provider: str, streaming: bool = True):
        if provider == "gemini":
            return ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,       # "gemini-2.0-flash"
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.3,
                max_retries=3,
                streaming=streaming,
            )
        elif provider == "ollama":
            return ChatOllama(
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.OLLAMA_MODEL,       # "llama3.2"
                temperature=0.3,
                streaming=streaming,
            )
        raise ValueError(f"Unknown provider: {provider}")
```

---

## 10. Memory & Context Management

### Conversation Memory Strategy

```mermaid
flowchart LR
    subgraph MEMORY["Memory Layers"]
        SHORT["Short-Term\n(LangGraph State)\nchat_history: last 6 msgs\nIn-memory per request"]
        MED["Medium-Term\n(PostgreSQL)\nFull session history\nQueried on session load"]
        LONG["Long-Term\n(ChromaDB)\nEmbedded conversation\nsummaries per user (future)"]
    end

    NEW_MSG["New Message"] --> SHORT
    SHORT -->|"persist after request"| MED
    MED -->|"loaded on session open"| SHORT
    SHORT -.->|"future: semantic memory"| LONG
```

### History Loading Strategy

```python
# services/chat_service.py

async def load_chat_history(session_id: UUID, limit: int = 6) -> list[BaseMessage]:
    """Load last N messages as LangChain BaseMessage objects."""
    messages = await message_repo.get_recent(session_id, limit=limit)
    history = []
    for msg in messages:
        if msg.role == "user":
            history.append(HumanMessage(content=msg.content))
        else:
            history.append(AIMessage(content=msg.content))
    return history
```

---

## 11. System Prompt Templates

### Q&A System Prompt

```python
QA_SYSTEM_PROMPT = """
You are EduNex AI, a personalized educational assistant for students.

Your role:
- Answer the student's question clearly and accurately
- Use the provided document context as your primary source
- Reference sources as [S1], [S2], etc. where applicable
- If the context doesn't contain the answer, use your general knowledge
  but clearly state: "This is from my general knowledge, not your documents."
- Adapt your explanation to be appropriate for a student studying {subject}
- Use examples, analogies, and step-by-step breakdowns when helpful
- Format responses with Markdown (headers, bold, bullet points, code blocks)

Rules:
- Never fabricate facts or citations
- Never hallucinate page numbers you don't have
- If unsure, say so and suggest the student verify
- Keep responses focused and educational
- Do not engage with off-topic requests

Document Context:
{context}

Conversation History:
{chat_history}
"""
```

### Quiz System Prompt

```python
QUIZ_SYSTEM_PROMPT = """
You are EduNex AI Quiz Master. Generate a high-quality educational quiz.

Requirements:
- Subject: {subject}
- Topic: {topic}
- Difficulty: {difficulty} (easy=recall, medium=understanding, hard=application/analysis)
- Question count: {question_count}
- Question types: {question_types}
- Base all questions on the provided document context
- Each question must have a clear, unambiguous answer
- Explanations must reference the source material

Output ONLY valid JSON in this exact schema:
{{
  "title": "Quiz title",
  "questions": [
    {{
      "id": 1,
      "type": "mcq",
      "question": "Question text?",
      "options": ["A", "B", "C", "D"],
      "answer": "B",
      "explanation": "Because...",
      "source_chunk": "Document section reference"
    }}
  ]
}}

Document Context:
{context}
"""
```

### Summarization System Prompt

```python
SUMMARY_SYSTEM_PROMPT = """
You are EduNex AI, creating a study summary for a student.

Subject: {subject}
Document: {document_title}

Create a clear, structured study summary that:
1. Identifies the main topic and purpose
2. Organizes key concepts into logical sections
3. Highlights important definitions, formulas, and facts
4. Uses bullet points for easy review
5. Notes any relationships between concepts
6. Ends with 5-7 key takeaways for exam preparation

Format:
## Overview
## Key Concepts
### [Concept 1]
### [Concept 2]
## Important Formulas / Definitions
## Key Takeaways
- •
- •

Keep language clear and appropriate for a student studying {subject}.
"""
```

---

## 12. Error Handling & Retry Strategy

```mermaid
flowchart TD
    LLM_CALL["LLM API Call"]
    SUCCESS["Success\nReturn response"]
    ERR_TEMP["Temporary Error\n503, 504, UNAVAILABLE,\nDEADLINE_EXCEEDED"]
    ERR_PERM["Permanent Error\n400, 401, 403\nInvalid request"]
    ERR_RATE["Rate Limited\n429 Too Many Requests"]

    RETRY1["Retry 1\nwait: 2s"]
    RETRY2["Retry 2\nwait: 4s"]
    RETRY3["Retry 3\nwait: 8s (exponential)"]

    FALLBACK_PROV["Try Ollama\n(if configured)"]
    FAIL_MSG["Return friendly\nerror message\nLog to usage_events"]

    LLM_CALL -->|"200"| SUCCESS
    LLM_CALL -->|"5xx"| ERR_TEMP
    LLM_CALL -->|"4xx"| ERR_PERM
    LLM_CALL -->|"429"| ERR_RATE

    ERR_TEMP --> RETRY1 --> RETRY2 --> RETRY3
    ERR_RATE --> RETRY1
    RETRY3 -->|"still fails"| FALLBACK_PROV
    FALLBACK_PROV -->|"fails"| FAIL_MSG
    ERR_PERM --> FAIL_MSG
    RETRY1 & RETRY2 -->|"success"| SUCCESS
```

**Retry Decorator:**
```python
# utils/retry.py

from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log
)

RETRYABLE_ERRORS = (
    "503", "504", "UNAVAILABLE", "DEADLINE_EXCEEDED", "429"
)

def is_retryable(exception: Exception) -> bool:
    return any(code in str(exception) for code in RETRYABLE_ERRORS)

llm_retry = retry(
    retry=retry_if_exception_type(Exception) & is_retryable,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
```

---

## 13. Agent File Structure

```
backend/app/agents/
├── __init__.py
├── state.py                   # EduNexState TypedDict definition
├── orchestrator.py            # LangGraph build_graph(), edunex_graph
├── safety_agent.py            # safety_node(), blocked_response_node()
├── router_node.py             # router_node() — intent classification
├── qa_agent.py                # qa_node() — RAG-augmented Q&A
├── quiz_agent.py              # quiz_node() — quiz generation
├── summarizer_agent.py        # summarize_node() — document summary
├── progress_agent.py          # progress_node() — learning insights
├── stream_node.py             # stream_node() — SSE publisher
├── memory_node.py             # memory_node() — DB persistence
└── prompts/
    ├── __init__.py
    ├── qa_prompts.py          # QA_SYSTEM_PROMPT, QA_USER_TEMPLATE
    ├── quiz_prompts.py        # QUIZ_SYSTEM_PROMPT
    ├── summary_prompts.py     # SUMMARY_SYSTEM_PROMPT
    ├── progress_prompts.py    # PROGRESS_SYSTEM_PROMPT
    └── safety_prompts.py     # SAFETY_CLASSIFIER_PROMPT

backend/app/rag/
├── __init__.py
├── loader.py                  # PDF, image, text document loaders
├── chunker.py                 # RecursiveCharacterTextSplitter config
├── embedder.py                # SentenceTransformer wrapper + batch embed
├── vectorstore.py             # ChromaDB client + collection management
└── retriever.py               # Query, filter, threshold, format chunks
```

### Key Design Rules for All Agent Nodes

1. **Every node is a pure function:** `(state: EduNexState) → dict`
2. **Return only the keys being updated** — LangGraph merges into state
3. **Never mutate the input state dict** — treat it as immutable
4. **Always append to `node_trace`** — for debugging and observability
5. **Stream tokens via `asyncio.Queue`** — never block waiting for full response
6. **Log latency and token count** — update `total_latency_ms`, `total_token_count`

```python
# Template for every agent node
async def qa_node(state: EduNexState) -> dict:
    start_ms = time.monotonic() * 1000
    logger.info(f"[qa_node] entry | session={state['session_id']}")

    # ... node logic ...

    latency = int(time.monotonic() * 1000 - start_ms)
    logger.info(f"[qa_node] exit | latency={latency}ms | tokens={tokens}")

    return {
        "response": response_text,
        "sources": citations,
        "total_token_count": state.get("total_token_count", 0) + tokens,
        "total_latency_ms": state.get("total_latency_ms", 0) + latency,
        "node_trace": state.get("node_trace", []) + ["qa_node"],
    }
```

