# EduNex AI — Implementation Plan

> **Project:** EduNex AI — Production-Oriented Educational AI Assistant  
> **Foundation:** NEXIS SOLUTIONS LLMs codebase + Mini-Projects 1–3  
> **Target Stack:** Python 3.10, Gemini API, LangChain, LangGraph, Gradio/Streamlit  
> **Status:** Phase 1 Audit Complete — Awaiting Phase 2 Approval

---

## Vision

EduNex AI is a **multi-agent educational AI assistant** that helps students:
- Ask questions on any academic subject
- Receive structured, curriculum-aligned answers
- Upload and query documents (PDFs, notes)
- Get personalized explanations, quizzes, and summaries
- Access web-grounded research on complex topics

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        EduNex AI                                 │
├────────────────┬────────────────────────────────────────────────-┤
│   Frontend UI  │   Gradio (or Streamlit) Web Interface            │
├────────────────┼─────────────────────────────────────────────────┤
│   API Layer    │   FastAPI / Python backend                       │
├────────────────┼─────────────────────────────────────────────────┤
│   Agent Layer  │   LangGraph Multi-Agent Workflow                 │
│                │   ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
│                │   │ Query    │ │  RAG     │ │   Report     │   │
│                │   │ Analyzer │→│  Agent   │→│  Generator   │   │
│                │   └──────────┘ └──────────┘ └──────────────┘   │
├────────────────┼─────────────────────────────────────────────────┤
│   LLM Layer    │   Google Gemini (via langchain-google-genai)     │
├────────────────┼─────────────────────────────────────────────────┤
│   Data Layer   │   ChromaDB (vector store) + SQLite (chat history)│
├────────────────┼─────────────────────────────────────────────────┤
│   External APIs│   Tavily (web search) + Google AI Studio         │
└────────────────┴─────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1 — Audit & Planning (CURRENT — COMPLETE)
- [x] Inspect GitHub reference repository
- [x] Read all mini-project source files
- [x] Identify reusable components
- [x] Identify missing components
- [x] Create CODEBASE_AUDIT.md
- [x] Create IMPLEMENTATION_PLAN.md
- [x] Create TECH_STACK.md

**Deliverable:** Three documentation files  
**Status:** ✅ Complete

---

### Phase 2 — Project Foundation & Environment Setup
**Awaiting your approval before starting**

Tasks:
1. Create project directory structure
2. Create `requirements.txt` with pinned versions
3. Create `.env.example` (never expose real keys)
4. Create `.gitignore`
5. Create `config/settings.py` (fix `gemini-3.5-flash` → `gemini-2.0-flash`)
6. Create virtual environment setup script
7. Validate imports and environment health check script

**Deliverable:** Runnable empty project scaffold  
**Estimated Time:** 30 minutes

---

### Phase 3 — Core LLM & Configuration Layer
**Requires Phase 2 approval**

Tasks:
1. `config/settings.py` — Gemini LLM factory, model config, env validation
2. `config/prompts.py` — Subject-specific system prompts (Math, Science, History, etc.)
3. `utils/helpers.py` — Port from IntelliResearch: `extract_text_content()`, retry decorator
4. `utils/logger.py` — Structured logging setup
5. Test: `python -c "from config.settings import get_llm; print(get_llm())"` passes

**Reused From:** Mini Project 3's `config/settings.py`, `utils/helpers.py`  
**Deliverable:** Working LLM connection  
**Estimated Time:** 1 hour

---

### Phase 4 — Multi-Agent LangGraph Workflow
**Requires Phase 3 approval**

Tasks:
1. `agents/query_agent.py` — Classify & analyze student questions
2. `agents/knowledge_agent.py` — Answer from built-in knowledge + educational context
3. `agents/research_agent.py` — Web search via Tavily (port from IntelliResearch)
4. `agents/summarizer_agent.py` — Create student-friendly summaries (port + adapt)
5. `agents/quiz_agent.py` — Generate practice questions on the topic
6. `workflow/graph.py` — LangGraph StateGraph connecting all agents
7. `workflow/state.py` — EduNexState TypedDict

**Agent Pipeline:**
```
START → query_agent → knowledge_agent → [research_agent?] → summarizer_agent → [quiz_agent?] → END
```

**Reused From:** Mini Project 3's full agent + workflow structure  
**Deliverable:** Working multi-agent pipeline (testable from CLI)  
**Estimated Time:** 2–3 hours

---

### Phase 5 — Document Processing (RAG)
**Requires Phase 4 approval**

Tasks:
1. `rag/loader.py` — PDF, TXT, DOCX file loading (PyMuPDF / LangChain loaders)
2. `rag/chunker.py` — Recursive character text splitter
3. `rag/embedder.py` — Google Generative AI embeddings
4. `rag/vectorstore.py` — ChromaDB setup and querying
5. `rag/retriever.py` — Similarity search with score threshold
6. Update `workflow/graph.py` — Add RAG retrieval step before knowledge agent

**New Dependencies:** `chromadb`, `langchain-community`, `pymupdf`  
**Deliverable:** Upload a PDF → ask questions about it  
**Estimated Time:** 2 hours

---

### Phase 6 — Conversation Memory
**Requires Phase 5 approval**

Tasks:
1. `memory/chat_history.py` — SQLite-backed conversation storage
2. `memory/session_manager.py` — Session ID management
3. Update LangGraph state to include `chat_history: list[BaseMessage]`
4. Update prompts to include conversation context
5. Add "clear history" functionality

**New Dependencies:** `langchain-community` (SQLiteChatMessageHistory)  
**Deliverable:** EduNex AI remembers the conversation  
**Estimated Time:** 1–2 hours

---

### Phase 7 — Gradio Web Interface
**Requires Phase 6 approval**

Tasks:
1. `app.py` — Main Gradio application (port structure from IntelliResearch)
2. Subject selector (dropdown: Math, Science, English, History, etc.)
3. Chat interface with streaming responses
4. Document upload panel (PDF, TXT)
5. Quiz tab (practice questions on current topic)
6. Research tab (web-grounded answers)
7. Tabbed output: Answer | Sources | Quiz | Summary
8. Launch config: host, port, auth (basic password)

**Reused From:** Mini Project 3's `app.py` structure  
**Deliverable:** Full working web UI  
**Estimated Time:** 2–3 hours

---

### Phase 8 — Testing & Quality Assurance
**Requires Phase 7 approval**

Tasks:
1. `tests/test_config.py` — Settings validation tests
2. `tests/test_agents.py` — Agent unit tests (mock LLM)
3. `tests/test_workflow.py` — End-to-end workflow test
4. `tests/test_rag.py` — Document upload and retrieval test
5. `tests/test_ui.py` — Gradio interface smoke test
6. Manual evaluation: 10 educational questions across 5 subjects

**New Dependencies:** `pytest`, `pytest-asyncio`  
**Deliverable:** Test suite with >70% coverage  
**Estimated Time:** 2 hours

---

### Phase 9 — Security Hardening & Production Prep
**Requires Phase 8 approval**

Tasks:
1. Input sanitization for all user inputs
2. Rate limiting (token bucket per session)
3. File upload validation (type, size limits)
4. Environment variable validation on startup
5. Error handling — graceful fallback messages
6. Secrets scanning (`detect-secrets` baseline)
7. `Dockerfile` for containerized deployment
8. `README.md` — full setup and usage guide

**Deliverable:** Production-ready application  
**Estimated Time:** 2–3 hours

---

## Reusable Component Mapping

| EduNex AI Component | Sourced From | Adaptation Needed |
|---------------------|-------------|-------------------|
| `config/settings.py` | Mini Project 3 | Fix model name, add subject config |
| `utils/helpers.py` | Mini Project 3 | Port directly |
| `agents/research_agent.py` | Mini Project 3 | Port directly |
| `agents/summarizer_agent.py` | Mini Project 3 | Adapt prompts for education |
| `workflow/graph.py` | Mini Project 3 | Extend with new agent nodes |
| `app.py` (Gradio) | Mini Project 3 | Extend with chat + upload |
| Retry logic | Mini Project 3 | Port directly |
| Token counting | Mini Project 1 | Adapt for Gemini tokenization |
| Training loop pattern | Mini Project 2 | Reference only |
| GPT model architecture | NEXIS LLMs repo | Reference/learning only |
| Chainlit UI patterns | NEXIS LLMs repo | Adapt for Gradio |
| Instruction formatting | NEXIS LLMs ch07 | Adapt for educational prompts |

---

## Missing Components (Must Build)

| Component | Description | Phase |
|-----------|-------------|-------|
| `agents/query_agent.py` | Question classifier & intent detector | 4 |
| `agents/knowledge_agent.py` | Core educational answering agent | 4 |
| `agents/quiz_agent.py` | Quiz/practice question generator | 4 |
| `rag/` module | Full RAG pipeline | 5 |
| `memory/` module | Conversation persistence | 6 |
| `config/prompts.py` | Educational system prompts per subject | 3 |
| `utils/logger.py` | Structured logging | 3 |
| Subject selector UI | Gradio dropdown for subject | 7 |
| File upload UI | PDF/TXT upload widget | 7 |
| Rate limiter | Per-session throttling | 9 |

---

## Recommended Implementation Order

```
Phase 1 (Done) → Phase 2 → Phase 3 → Phase 4 → Phase 7 (basic UI)
                                                      ↓
                                              Phase 5 (RAG)
                                                      ↓
                                              Phase 6 (Memory)
                                                      ↓
                                       Phase 7 (Full UI with all tabs)
                                                      ↓
                                              Phase 8 (Testing)
                                                      ↓
                                              Phase 9 (Hardening)
```

**Minimum Viable Product (MVP):** Phases 2 + 3 + 4 + 7 (basic)  
→ A working educational chatbot without RAG or memory  
**Full Product:** All 9 phases

