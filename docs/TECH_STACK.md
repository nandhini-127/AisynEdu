# EduNex AI — Technology Stack

> **Document:** Technology choices, version requirements, and dependency strategy  
> **Last Updated:** 2026-11-12  
> **Python Version:** 3.10.11

---

## Core Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Language** | Python | 3.10.11 | Primary language |
| **LLM Provider** | Google Gemini | API | Core AI backbone |
| **LLM Framework** | LangChain | ≥ 0.3.0 | LLM abstraction & chains |
| **Agent Workflow** | LangGraph | ≥ 0.2.0 | Multi-agent orchestration |
| **Gemini SDK** | langchain-google-genai | ≥ 2.0.0 | Gemini integration |
| **Web UI** | Gradio | ≥ 5.0.0 | Chat + upload interface |
| **Vector Store** | ChromaDB | ≥ 0.5.0 | RAG document storage |
| **Web Search** | Tavily | ≥ 0.5.0 | Live web search for agents |
| **Environment** | python-dotenv | ≥ 1.0.0 | Secrets management |

---

## Dependency Details

### Production Requirements (`requirements.txt`)

```txt
# LLM & Agent Framework
langchain>=0.3.0
langchain-core>=0.3.0
langchain-community>=0.3.0
langchain-google-genai>=2.0.0
langgraph>=0.2.0

# Web UI
gradio>=5.0.0

# Web Search
tavily-python>=0.5.0

# Document Processing (RAG)
chromadb>=0.5.0
pymupdf>=1.24.0          # PDF loading (fitz)

# Configuration
python-dotenv>=1.0.0

# Utilities
pydantic>=2.0.0
httpx>=0.27.0
tenacity>=8.0.0           # Retry logic

# Testing
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

### Development Requirements (`requirements-dev.txt`)

```txt
-r requirements.txt

# Code quality
ruff>=0.5.0
black>=24.0.0
mypy>=1.10.0

# Security
detect-secrets>=1.5.0

# Notebooks (reference only)
jupyterlab>=4.0.0
ipywidgets>=8.0.0
```

---

## LLM Configuration

### Primary Model: Google Gemini

| Setting | Value |
|---------|-------|
| Model | `gemini-2.0-flash` |
| Fallback | `gemini-1.5-flash` |
| Max Retries | 3 |
| Timeout | 60 seconds |
| Temperature | 0.3 (educational — factual) |
| Max Output Tokens | 2048 |

> **Why Gemini?** Already used in Mini Project 3 (IntelliResearch). The team has API keys, existing integration code, and familiarity with its capabilities.

> **CRITICAL BUG IN MINI PROJECT 3:** `gemini-3.5-flash` does NOT exist. Use `gemini-2.0-flash` or `gemini-1.5-flash`.

### Model Selection Strategy
```python
# config/settings.py
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
```

---

## Agent Framework: LangGraph

### Why LangGraph?
- Already proven in Mini Project 3 (IntelliResearch)
- Supports stateful multi-agent workflows
- Native streaming support
- Built on LangChain ecosystem

### Agent State Pattern (from IntelliResearch):
```python
class EduNexState(TypedDict, total=False):
    subject: str              # e.g., "Mathematics"
    question: str             # Student's question
    intent: str               # "explain" | "quiz" | "research"
    knowledge_response: str   # Core answer
    web_findings: list[dict]  # Research results
    summary: str              # Student-friendly summary
    quiz_questions: list[dict] # Practice questions
    sources: list[dict]       # Citations
    chat_history: list        # Conversation memory
```

---

## User Interface: Gradio

### Why Gradio?
- Already used in Mini Project 3
- Rapid prototyping
- Built-in file upload support
- Easy auth with `auth=` parameter
- Markdown rendering in outputs

### Planned UI Layout
```
EduNex AI
├── Chat Tab
│   ├── Subject selector (dropdown)
│   ├── Chat interface (gr.ChatInterface)
│   └── Clear History button
├── Research Tab
│   ├── Topic input
│   ├── Report output (Markdown)
│   └── Sources output
├── Document Q&A Tab
│   ├── File upload (PDF, TXT)
│   ├── Question input
│   └── Answer output
└── Quiz Tab
    ├── Subject + topic input
    └── Generated questions output
```

---

## RAG (Retrieval-Augmented Generation) Stack

| Component | Technology | Reason |
|-----------|-----------|--------|
| Embeddings | Google Generative AI Embeddings | Consistent with Gemini |
| Vector Store | ChromaDB | Local, file-based, no server needed |
| Document Loader | PyMuPDF + LangChain | PDF, TXT, DOCX support |
| Chunker | RecursiveCharacterTextSplitter | Standard LangChain chunker |
| Retriever | Similarity search + score threshold | Quality filter |

---

## Memory & Persistence

| Component | Technology | Reason |
|-----------|-----------|--------|
| Chat History | LangChain ConversationHistory | Built-in LangChain |
| Storage Backend | SQLite (file-based) | No external DB needed |
| Session Management | UUID-based session IDs | Simple, stateless |

---

## Environment Variables

```bash
# .env.example (commit this — no real values)

# Required
GOOGLE_API_KEY=your_google_ai_studio_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here

# Optional (with defaults)
GEMINI_MODEL=gemini-2.0-flash
MAX_SEARCH_RESULTS=5
MAX_UPLOAD_MB=10
GRADIO_PORT=7860
GRADIO_HOST=127.0.0.1
LOG_LEVEL=INFO
CHROMA_PATH=./data/chroma_db
HISTORY_DB_PATH=./data/chat_history.db
```

---

## Security Considerations

| Area | Approach |
|------|---------|
| API Keys | `.env` file, never committed |
| Input Sanitization | Strip control characters, length limits |
| File Upload | Allowlist: `.pdf`, `.txt`, `.docx` only; 10MB max |
| Rate Limiting | Simple token bucket per session |
| Gradio Auth | `auth=("user", os.getenv("UI_PASSWORD"))` |

---

## What is NOT Used (and Why)

| Technology | Reason NOT Used |
|-----------|----------------|
| OpenAI GPT-4 | No OpenAI API key; Gemini is established |
| Pinecone / Weaviate | Requires cloud account; ChromaDB is local |
| PostgreSQL / MySQL | Overkill for SQLite chat history |
| Docker (Phase 1–7) | Added in Phase 9 only |
| PyTorch training | EduNex uses APIs, not local model training |
| tiktoken | Gemini uses its own tokenizer |
| LlamaIndex | LangChain already established in Mini P3 |
| Chainlit | Gradio already established in Mini P3 |

---

## Package Conflicts to Watch

| Conflict | Issue | Resolution |
|---------|-------|-----------|
| `torch==1.12.1` (global) | Very outdated | Use venv; isolate from global |
| `pandas==1.5.3` (global) | LangChain prefers ≥ 2.0 | Use venv |
| `tensorflow==2.15.0` | Heavy; not needed for EduNex | Don't import |
| `googletrans==4.0.0rc1` | Unofficial Google API; deprecated | Avoid |

---

## Recommended Venv Setup

```bash
# From d:\Skill Nexis Internship\Project - Chatbot\

python -m venv venv
venv\Scripts\activate          # Windows

pip install --upgrade pip
pip install -r requirements.txt
```

> **ALWAYS use the venv.** Never install EduNex AI dependencies into the global Python to avoid conflicts with Mini Projects 1–3.

---

## Version Compatibility Matrix

| Package | Min Version | Max Tested | Notes |
|---------|------------|-----------|-------|
| Python | 3.10 | 3.12 | 3.10 installed |
| langchain | 0.3.0 | latest | Breaking changes at 0.3 |
| langgraph | 0.2.0 | latest | Stable API since 0.2 |
| gradio | 5.0.0 | latest | v5 has new ChatInterface |
| chromadb | 0.5.0 | latest | v0.5 changed client API |
| pydantic | 2.0.0 | 2.x | LangChain requires v2 |

