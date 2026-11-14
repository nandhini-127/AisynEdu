# AisynEdu — Complete System Architecture

> **Version:** 1.0  
> **Date:** 2026-11-12  
> **Status:** Design Phase — Awaiting Implementation Approval

---

## Table of Contents
1. [System Overview](#1-system-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Frontend Architecture](#3-frontend-architecture)
4. [Backend Architecture](#4-backend-architecture)
5. [Agent Workflow Architecture](#5-agent-workflow-architecture)
6. [RAG Pipeline Architecture](#6-rag-pipeline-architecture)
7. [Authentication Architecture](#7-authentication-architecture)
8. [Multimodal Processing Architecture](#8-multimodal-processing-architecture)
9. [Database Architecture](#9-database-architecture)
10. [Streaming Architecture](#10-streaming-architecture)
11. [Deployment Architecture](#11-deployment-architecture)
12. [Module Responsibility Map](#12-module-responsibility-map)
13. [Inter-Module Communication](#13-inter-module-communication)

---

## 1. System Overview

EduNex AI is a **personalized educational AI assistant** designed for students to:
- Upload and query study materials (PDFs, images, notes)
- Ask subject-specific questions with AI-generated answers
- Generate quizzes and practice tests
- Summarize chapters and long documents
- Track learning progress over time
- Receive multi-modal explanations (text + diagrams)

### Technology Pillars

| Pillar | Technology | Rationale |
|--------|-----------|-----------|
| Frontend | React 18 + TypeScript + Tailwind CSS | Type-safe, component-driven, modern DX |
| Backend | FastAPI (Python 3.10+) | Async-first, OpenAPI auto-docs, Pydantic validation |
| LLM Primary | Google Gemini 2.0 Flash | Cost-effective, multimodal, long context |
| LLM Optional | Ollama (local) | Privacy, offline operation |
| Agent Orchestration | LangGraph | Stateful multi-agent workflows |
| RAG Framework | LangChain | Document processing + retrieval chains |
| Embeddings | Sentence Transformers (`all-MiniLM-L6-v2`) | Local, free, 384-dim, fast |
| Vector Database | ChromaDB | Persistent, local, no external service |
| Relational Database | PostgreSQL 15 | ACID, complex queries, production-grade |
| Authentication | JWT (RS256) + bcrypt | Stateless, secure, standard |
| Streaming | Server-Sent Events (SSE) | Native browser support, unidirectional |
| Containerization | Docker + Docker Compose | Reproducible, portable |

---

## 2. High-Level Architecture

```mermaid
flowchart TD
    subgraph CLIENT["🖥️ Client Layer"]
        BROWSER["Browser\nReact + TypeScript"]
    end

    subgraph GATEWAY["🔀 API Gateway Layer"]
        NGINX["NGINX\nReverse Proxy + SSL"]
    end

    subgraph BACKEND["⚙️ Backend Layer (FastAPI)"]
        AUTH["Auth Router\n/api/auth"]
        CHAT["Chat Router\n/api/chat"]
        DOC["Documents Router\n/api/documents"]
        QUIZ["Quiz Router\n/api/quiz"]
        PROG["Progress Router\n/api/progress"]
        STREAM["SSE Stream\n/api/stream"]
    end

    subgraph AGENTS["🤖 Agent Orchestration (LangGraph)"]
        ORCH["Agent Orchestrator"]
        QA["Q&A Agent"]
        QUIZ_A["Quiz Agent"]
        SUM_A["Summarizer Agent"]
        PROG_A["Progress Agent"]
        SAFE["Safety Guardrail"]
    end

    subgraph LLM["🧠 LLM Layer"]
        GEMINI["Google Gemini\n2.0 Flash"]
        OLLAMA["Ollama\n(Optional Local)"]
        ROUTER["LLM Router"]
    end

    subgraph RAG["📚 RAG Pipeline (LangChain)"]
        LOADER["Document Loader"]
        CHUNKER["Text Chunker"]
        EMBED["Sentence Transformer\nEmbedder"]
        RETRIEVER["Similarity Retriever"]
    end

    subgraph DATA["💾 Data Layer"]
        PG["PostgreSQL\nUsers, Sessions,\nProgress, Analytics"]
        CHROMA["ChromaDB\nVector Store"]
        S3["File Storage\nUploaded Documents"]
        REDIS["Redis\nSession Cache"]
    end

    BROWSER -->|HTTPS| NGINX
    NGINX --> AUTH & CHAT & DOC & QUIZ & PROG & STREAM
    CHAT --> ORCH
    QUIZ --> ORCH
    DOC --> LOADER
    ORCH --> QA & QUIZ_A & SUM_A & PROG_A
    ORCH --> SAFE
    QA & QUIZ_A & SUM_A --> ROUTER
    ROUTER --> GEMINI & OLLAMA
    QA --> RETRIEVER
    RETRIEVER --> CHROMA
    LOADER --> CHUNKER --> EMBED --> CHROMA
    ORCH --> PG
    AUTH --> PG
    AUTH --> REDIS
    DOC --> S3
    PROG --> PG
    STREAM --> ROUTER
```

---

## 3. Frontend Architecture

### 3.1 Component Tree

```mermaid
flowchart TD
    APP["App.tsx\n(Root)"]

    subgraph ROUTES["React Router v6"]
        AUTH_PAGE["AuthPage\n/auth"]
        DASH["Dashboard\n/dashboard"]
        CHAT_PAGE["ChatPage\n/chat/:subjectId"]
        DOCS_PAGE["DocumentsPage\n/documents"]
        QUIZ_PAGE["QuizPage\n/quiz/:quizId"]
        PROG_PAGE["ProgressPage\n/progress"]
        ANALYTICS["AnalyticsPage\n/analytics"]
    end

    subgraph LAYOUT["Shared Layout"]
        SIDEBAR["Sidebar\n(Nav + Subject list)"]
        TOPBAR["TopBar\n(User menu + LLM selector)"]
        TOAST["Toast Provider"]
    end

    subgraph CHAT_C["Chat Components"]
        MSG_LIST["MessageList"]
        MSG_ITEM["MessageItem\n(Markdown + Code)"]
        INPUT_BOX["InputBox\n(Text + File attach)"]
        STREAM_IND["StreamingIndicator"]
        SRC_PANEL["SourcesPanel\n(RAG citations)"]
    end

    subgraph DOC_C["Document Components"]
        UPLOAD["UploadDropzone\n(PDF, Images)"]
        DOC_LIST["DocumentList"]
        DOC_VIEWER["PDFViewer"]
        PROC_STATUS["ProcessingStatus"]
    end

    subgraph QUIZ_C["Quiz Components"]
        QUIZ_GEN["QuizGenerator\n(Settings form)"]
        QUIZ_PLAY["QuizPlayer\n(MCQ, Fill-blank)"]
        QUIZ_RES["QuizResults\n(Score + Feedback)"]
    end

    subgraph PROG_C["Progress Components"]
        PROG_CHART["ProgressChart\n(Recharts)"]
        STREAK["StudyStreak"]
        MASTERY["MasteryMap\n(Subject heatmap)"]
        TIMELINE["ActivityTimeline"]
    end

    subgraph STATE["Global State (Zustand)"]
        AUTH_STORE["authStore\n(user, token, role)"]
        CHAT_STORE["chatStore\n(messages, session)"]
        DOC_STORE["documentStore\n(files, status)"]
        UI_STORE["uiStore\n(theme, sidebar)"]
    end

    APP --> ROUTES & LAYOUT & STATE
    DASH --> SIDEBAR & TOPBAR
    CHAT_PAGE --> CHAT_C
    DOCS_PAGE --> DOC_C
    QUIZ_PAGE --> QUIZ_C
    PROG_PAGE --> PROG_C
```

### 3.2 Data Flow Pattern

```mermaid
sequenceDiagram
    participant U as User
    participant C as Component
    participant S as Zustand Store
    participant H as React Hook
    participant A as API Client
    participant SSE as SSE Connection
    participant B as Backend

    U->>C: Types question & submits
    C->>S: dispatch addMessage(userMsg)
    C->>H: useChat().sendMessage(text)
    H->>A: POST /api/chat/message
    A->>B: { session_id, content, subject }
    B-->>A: { message_id, stream_url }
    H->>SSE: Connect GET /api/stream/{message_id}
    loop Streaming tokens
        SSE-->>H: data: {"token": "Because..."}
        H->>S: dispatch appendToken(token)
        S-->>C: re-render with new token
    end
    SSE-->>H: data: {"done": true, "sources": [...]}
    H->>S: dispatch finalizeMessage(sources)
    C->>U: Shows complete response + citations
```

### 3.3 Frontend Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Framework | React | 18.3 | Component UI |
| Language | TypeScript | 5.4 | Type safety |
| Routing | React Router | v6 | Client-side routing |
| State | Zustand | 5.x | Lightweight global state |
| Data Fetching | TanStack Query | v5 | Server state + caching |
| Styling | Tailwind CSS | v3 | Utility-first CSS |
| UI Components | shadcn/ui | latest | Accessible components |
| Markdown | react-markdown + rehype | latest | Render LLM Markdown |
| Code Highlight | Prism.js / shiki | latest | Code block syntax |
| Charts | Recharts | v2 | Progress analytics |
| PDF Viewer | react-pdf | v7 | In-app PDF display |
| File Upload | react-dropzone | v14 | Drag-and-drop |
| Forms | React Hook Form + Zod | latest | Validated forms |
| HTTP Client | Axios | v1 | REST API calls |
| SSE | EventSource (native) | — | Streaming |
| Testing | Vitest + Testing Library | latest | Unit + integration |
| Build | Vite | v5 | Fast HMR, ES modules |

### 3.4 Frontend Directory Structure

```
frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── api/                    # API client functions
│   │   ├── authApi.ts
│   │   ├── chatApi.ts
│   │   ├── documentsApi.ts
│   │   ├── quizApi.ts
│   │   └── progressApi.ts
│   ├── components/             # Reusable UI components
│   │   ├── common/             # Button, Input, Modal, Badge
│   │   ├── chat/               # MessageList, InputBox, SourcePanel
│   │   ├── documents/          # UploadDropzone, DocList, PDFViewer
│   │   ├── quiz/               # QuizPlayer, QuizResults
│   │   ├── progress/           # Charts, Streak, MasteryMap
│   │   └── layout/             # Sidebar, TopBar, Footer
│   ├── hooks/                  # Custom React hooks
│   │   ├── useChat.ts
│   │   ├── useSSE.ts
│   │   ├── useDocuments.ts
│   │   ├── useQuiz.ts
│   │   └── useProgress.ts
│   ├── pages/                  # Route-level page components
│   │   ├── AuthPage.tsx
│   │   ├── DashboardPage.tsx
│   │   ├── ChatPage.tsx
│   │   ├── DocumentsPage.tsx
│   │   ├── QuizPage.tsx
│   │   └── ProgressPage.tsx
│   ├── stores/                 # Zustand state stores
│   │   ├── authStore.ts
│   │   ├── chatStore.ts
│   │   ├── documentStore.ts
│   │   └── uiStore.ts
│   ├── types/                  # TypeScript interfaces
│   │   ├── auth.types.ts
│   │   ├── chat.types.ts
│   │   ├── document.types.ts
│   │   └── quiz.types.ts
│   ├── utils/                  # Helper functions
│   │   ├── formatters.ts
│   │   ├── validators.ts
│   │   └── constants.ts
│   ├── App.tsx
│   └── main.tsx
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

---

## 4. Backend Architecture

### 4.1 Layer Diagram

```mermaid
flowchart TD
    subgraph FASTAPI["FastAPI Application"]
        subgraph MIDDLEWARE["Middleware Stack"]
            CORS["CORS Middleware"]
            AUTH_MW["JWT Auth Middleware"]
            LOG_MW["Request Logger"]
            RATE["Rate Limiter\n(slowapi)"]
            ERR["Error Handler"]
        end

        subgraph ROUTERS["API Routers"]
            R_AUTH["auth.py\nPOST /register\nPOST /login\nPOST /refresh\nPOST /logout"]
            R_CHAT["chat.py\nPOST /message\nGET /sessions\nDELETE /session"]
            R_DOCS["documents.py\nPOST /upload\nGET /list\nDELETE /:id\nGET /status"]
            R_QUIZ["quiz.py\nPOST /generate\nGET /:id\nPOST /submit\nGET /history"]
            R_PROG["progress.py\nGET /summary\nGET /subjects\nGET /timeline"]
            R_STREAM["stream.py\nGET /events/:msg_id"]
            R_ADMIN["admin.py\nGET /analytics\nGET /users"]
        end

        subgraph SERVICES["Service Layer"]
            S_AUTH["AuthService\n(JWT, bcrypt)"]
            S_CHAT["ChatService\n(session mgmt)"]
            S_DOC["DocumentService\n(upload, parse)"]
            S_QUIZ["QuizService\n(generation, scoring)"]
            S_PROG["ProgressService\n(tracking, analytics)"]
            S_STREAM["StreamingService\n(SSE publisher)"]
            S_LLM["LLMService\n(provider router)"]
        end

        subgraph REPOS["Repository Layer"]
            REP_USER["UserRepository"]
            REP_SESSION["SessionRepository"]
            REP_DOC["DocumentRepository"]
            REP_QUIZ["QuizRepository"]
            REP_PROG["ProgressRepository"]
        end
    end

    MIDDLEWARE --> ROUTERS
    R_AUTH --> S_AUTH
    R_CHAT --> S_CHAT
    R_DOCS --> S_DOC
    R_QUIZ --> S_QUIZ
    R_PROG --> S_PROG
    R_STREAM --> S_STREAM
    S_AUTH --> REP_USER
    S_CHAT --> REP_SESSION
    S_DOC --> REP_DOC
    S_QUIZ --> REP_QUIZ
    S_PROG --> REP_PROG
    S_CHAT --> AGENTS["LangGraph\nOrchestrator"]
    S_LLM --> AGENTS
```

### 4.2 Backend Directory Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI app factory, middleware, lifespan
│   ├── config.py               # Settings (Pydantic BaseSettings)
│   ├── dependencies.py         # Shared FastAPI dependencies (get_db, get_current_user)
│   │
│   ├── routers/                # HTTP route handlers (thin layer)
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── documents.py
│   │   ├── quiz.py
│   │   ├── progress.py
│   │   ├── stream.py
│   │   └── admin.py
│   │
│   ├── services/               # Business logic layer
│   │   ├── auth_service.py     # Login, register, token management
│   │   ├── chat_service.py     # Session management, message processing
│   │   ├── document_service.py # Upload handling, file processing coordination
│   │   ├── quiz_service.py     # Quiz generation, scoring, history
│   │   ├── progress_service.py # Analytics, streaks, mastery tracking
│   │   ├── streaming_service.py# SSE event queue management
│   │   └── llm_service.py      # LLM provider routing (Gemini / Ollama)
│   │
│   ├── agents/                 # LangGraph agent definitions
│   │   ├── __init__.py
│   │   ├── orchestrator.py     # Main LangGraph StateGraph
│   │   ├── qa_agent.py         # Q&A with RAG
│   │   ├── quiz_agent.py       # Quiz generation
│   │   ├── summarizer_agent.py # Document summarization
│   │   ├── safety_agent.py     # Guardrail checks
│   │   └── progress_agent.py   # Progress insights
│   │
│   ├── rag/                    # RAG pipeline (LangChain)
│   │   ├── __init__.py
│   │   ├── loader.py           # PDF, image, text loaders
│   │   ├── chunker.py          # Text splitting strategies
│   │   ├── embedder.py         # Sentence Transformers embedding
│   │   ├── vectorstore.py      # ChromaDB client
│   │   └── retriever.py        # Similarity search + reranking
│   │
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── session.py
│   │   ├── document.py
│   │   ├── message.py
│   │   ├── quiz.py
│   │   └── progress.py
│   │
│   ├── schemas/                # Pydantic request/response schemas
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── document.py
│   │   ├── quiz.py
│   │   └── progress.py
│   │
│   ├── repositories/           # DB access layer
│   │   ├── user_repo.py
│   │   ├── session_repo.py
│   │   ├── document_repo.py
│   │   ├── quiz_repo.py
│   │   └── progress_repo.py
│   │
│   ├── middleware/
│   │   ├── auth_middleware.py
│   │   ├── rate_limiter.py
│   │   └── request_logger.py
│   │
│   ├── utils/
│   │   ├── security.py         # JWT, password hashing
│   │   ├── file_utils.py       # File validation, storage
│   │   ├── text_utils.py       # Text cleaning, extraction
│   │   └── pdf_utils.py        # PDF/image OCR helpers
│   │
│   └── database.py             # SQLAlchemy async engine + session factory
│
├── alembic/                    # DB migrations
│   ├── versions/
│   └── env.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── alembic.ini
└── Dockerfile
```

---

## 5. Agent Workflow Architecture

```mermaid
flowchart TD
    INPUT["User Input\n{question, subject, intent, session_id}"]

    subgraph LANG["LangGraph StateGraph — EduNexState"]
        ROUTE["Router Node\n(classify intent)"]

        subgraph SAFE_GATE["Safety Guardrail"]
            SAFE_CHK["Content Safety Check\n(prompt injection, profanity,\noff-topic guard)"]
        end

        subgraph QA_FLOW["Q&A Flow"]
            RAG_RET["RAG Retrieval\n(ChromaDB similarity search)"]
            CTX_BUILD["Context Builder\n(merge retrieved chunks)"]
            QA_GEN["Q&A Agent\n(Gemini / Ollama)"]
            CITE["Citation Formatter"]
        end

        subgraph QUIZ_FLOW["Quiz Flow"]
            QUIZ_CTX["Get Document Context"]
            QUIZ_GEN["Quiz Agent\n(MCQ, True/False, Fill-blank)"]
            QUIZ_VAL["Quiz Validator\n(format check, dedup)"]
        end

        subgraph SUM_FLOW["Summarization Flow"]
            SUM_CTX["Load Full Document"]
            SUM_GEN["Summarizer Agent\n(hierarchical summary)"]
        end

        subgraph PROG_FLOW["Progress Flow"]
            PROG_QRY["Query Progress DB"]
            PROG_GEN["Progress Insights Agent"]
        end

        STREAM_OUT["SSE Stream Publisher"]
        MEM_SAVE["Memory Save\n(update PostgreSQL + ChromaDB)"]
    end

    OUTPUT["Streamed Response\n+ sources + metadata"]

    INPUT --> SAFE_CHK
    SAFE_CHK -->|Pass| ROUTE
    SAFE_CHK -->|Fail| STREAM_OUT
    ROUTE -->|qa| RAG_RET
    ROUTE -->|quiz| QUIZ_CTX
    ROUTE -->|summarize| SUM_CTX
    ROUTE -->|progress| PROG_QRY
    RAG_RET --> CTX_BUILD --> QA_GEN --> CITE
    QUIZ_CTX --> QUIZ_GEN --> QUIZ_VAL
    SUM_CTX --> SUM_GEN
    PROG_QRY --> PROG_GEN
    CITE --> STREAM_OUT
    QUIZ_VAL --> STREAM_OUT
    SUM_GEN --> STREAM_OUT
    PROG_GEN --> STREAM_OUT
    STREAM_OUT --> MEM_SAVE --> OUTPUT
```

### 5.1 LangGraph State Definition

```python
# agents/orchestrator.py — EduNexState TypedDict
class EduNexState(TypedDict, total=False):
    # Input
    user_id: str
    session_id: str
    subject: str                    # e.g. "Mathematics"
    question: str                   # Raw user input
    intent: str                     # "qa" | "quiz" | "summarize" | "progress"
    document_ids: list[str]         # Attached document IDs

    # RAG
    retrieved_chunks: list[dict]    # [{text, source, score}]
    context: str                    # Merged context string
    sources: list[dict]             # [{title, page, url}]

    # Generation
    response: str                   # Final LLM response
    quiz_questions: list[dict]      # [{question, options, answer, explanation}]
    summary: str                    # Document summary
    progress_insights: dict         # Progress stats

    # Safety
    safety_passed: bool
    safety_reason: str              # If blocked

    # Memory
    chat_history: list[BaseMessage] # LangChain message history
    token_count: int                # Tokens used this turn

    # Metadata
    llm_provider: str               # "gemini" | "ollama"
    model_name: str
    latency_ms: int
```

---

## 6. RAG Pipeline Architecture

```mermaid
flowchart LR
    subgraph INGEST["📥 Ingestion Pipeline (on Upload)"]
        UP["File Upload\n(PDF / Image / TXT)"]
        VAL["File Validator\n(type, size, virus)"]
        STORE["Object Storage\n(local /uploads)"]
        LOADER["Document Loader\n(PyMuPDF for PDF\nPillow+Tesseract for image\nplain text loader)"]
        CLEAN["Text Cleaner\n(remove boilerplate,\nnormalize whitespace)"]
        CHUNK["Text Chunker\nRecursiveCharacterSplitter\nchunk_size=512\noverlap=50"]
        META["Metadata Tagger\n{doc_id, page, subject,\nuser_id, chunk_index}"]
        EMBED["Sentence Transformer\nall-MiniLM-L6-v2\n384-dim vectors"]
        CHROMA_W["ChromaDB Write\ncollection: user_{user_id}"]
        PG_W["PostgreSQL Write\ndocuments table"]
    end

    subgraph QUERY["🔍 Query Pipeline (on Question)"]
        Q_IN["User Question"]
        Q_EMBED["Query Embedding\n(same model)"]
        SIM["Similarity Search\ntop_k=5, threshold=0.7"]
        RERANK["Cross-Encoder\nReranker (optional)"]
        CTX_MERGE["Context Merger\n(ordered by relevance)"]
        PROMPT_B["Prompt Builder\n(system + context + history + question)"]
        LLM_C["LLM Call\n(Gemini / Ollama)"]
        RESP["Response\n+ source citations"]
    end

    UP --> VAL --> STORE --> LOADER --> CLEAN --> CHUNK --> META --> EMBED --> CHROMA_W
    CHUNK --> PG_W
    Q_IN --> Q_EMBED --> SIM
    CHROMA_W -.->|"vector search"| SIM
    SIM --> RERANK --> CTX_MERGE --> PROMPT_B --> LLM_C --> RESP
```

### 6.1 Embedding Strategy

| Setting | Value |
|---------|-------|
| Model | `sentence-transformers/all-MiniLM-L6-v2` |
| Dimensions | 384 |
| Hosting | Local (no API cost) |
| Chunk Size | 512 tokens |
| Chunk Overlap | 50 tokens |
| Distance Metric | Cosine similarity |
| Retrieval Top-K | 5 |
| Score Threshold | 0.70 |
| Collection Naming | `user_{user_id}_{subject}` |

### 6.2 Multi-Modal Processing

```mermaid
flowchart TD
    INPUT_FILE["Uploaded File"]
    TYPE_DET["MIME Type Detection"]

    subgraph PDF_PATH["PDF Path"]
        PDF_LOAD["PyMuPDF\n(text + images)"]
        PAGE_EXT["Page Extractor\n(text per page)"]
        IMG_EXT["Embedded Image\nExtractor"]
    end

    subgraph IMG_PATH["Image Path"]
        IMG_LOAD["Pillow\nImage Load"]
        PREPROC["Image Preprocessor\n(resize, contrast)"]
        OCR["Tesseract OCR\n(text from image)"]
        VIS_DESC["Gemini Vision\n(describe image content)"]
    end

    subgraph TXT_PATH["Text Path"]
        TXT_LOAD["Plain Text Loader"]
    end

    MERGE["Content Merger\n(text + visual description)"]
    NEXT["→ Chunker"]

    INPUT_FILE --> TYPE_DET
    TYPE_DET -->|".pdf"| PDF_LOAD
    TYPE_DET -->|".jpg .png"| IMG_LOAD
    TYPE_DET -->|".txt .md"| TXT_LOAD
    PDF_LOAD --> PAGE_EXT & IMG_EXT
    IMG_EXT --> VIS_DESC
    IMG_LOAD --> PREPROC --> OCR & VIS_DESC
    PAGE_EXT & VIS_DESC & OCR & TXT_LOAD --> MERGE --> NEXT
```

---

## 7. Authentication Architecture

```mermaid
sequenceDiagram
    participant U as User Browser
    participant FE as React Frontend
    participant BE as FastAPI Backend
    participant DB as PostgreSQL
    participant RC as Redis Cache

    Note over U,RC: Registration Flow
    U->>FE: Fill registration form
    FE->>BE: POST /api/auth/register {name, email, password}
    BE->>BE: Validate (Pydantic) + bcrypt hash password
    BE->>DB: INSERT users (hashed_password)
    DB-->>BE: user_id
    BE-->>FE: 201 Created {user_id}

    Note over U,RC: Login Flow
    U->>FE: Submit credentials
    FE->>BE: POST /api/auth/login {email, password}
    BE->>DB: SELECT user WHERE email=?
    DB-->>BE: user record
    BE->>BE: bcrypt.verify(password, hash)
    BE->>BE: Generate access_token (15min, RS256)
    BE->>BE: Generate refresh_token (7days, RS256)
    BE->>RC: STORE refresh_token_hash (TTL 7d)
    BE-->>FE: {access_token, refresh_token, user}
    FE->>FE: Store access_token (memory)\nStore refresh_token (httpOnly cookie)

    Note over U,RC: Authenticated Request
    U->>FE: Sends question
    FE->>BE: POST /api/chat/message\nAuthorization: Bearer {access_token}
    BE->>BE: Verify JWT signature\nCheck expiry\nExtract user_id
    BE->>DB: Validate user is active
    BE-->>FE: 200 Response

    Note over U,RC: Token Refresh
    FE->>BE: POST /api/auth/refresh\nCookie: refresh_token
    BE->>RC: Verify refresh_token_hash exists
    RC-->>BE: Valid
    BE->>BE: Issue new access_token
    BE-->>FE: {access_token}

    Note over U,RC: Logout
    FE->>BE: POST /api/auth/logout
    BE->>RC: DELETE refresh_token_hash
    BE-->>FE: 204 No Content
    FE->>FE: Clear memory + cookies
```

### 7.1 JWT Configuration

| Parameter | Value |
|-----------|-------|
| Algorithm | RS256 (asymmetric) |
| Access Token TTL | 15 minutes |
| Refresh Token TTL | 7 days |
| Access Token Storage | JavaScript memory (not localStorage) |
| Refresh Token Storage | httpOnly Secure Cookie |
| Revocation | Redis blocklist for refresh tokens |
| Token Claims | `sub` (user_id), `email`, `role`, `iat`, `exp` |

---

## 8. Multimodal Processing Architecture

```mermaid
flowchart TD
    subgraph UPLOAD["Upload Handler"]
        REQ["POST /api/documents/upload\n(multipart/form-data)"]
        AUTH_CHK["Auth Check\n(JWT validate)"]
        SIZE_CHK["Size Check\n(max 50MB)"]
        TYPE_CHK["Type Allowlist\n(.pdf, .png, .jpg, .jpeg, .txt, .md)"]
        VIRU_S["ClamAV Scan\n(optional)"]
        SAVE_RAW["Save to /uploads/{user_id}/"]
        JOB_Q["Enqueue Processing Job\n(BackgroundTasks)"]
        RESP_201["201 {doc_id, status: processing}"]
    end

    subgraph PROC["Background Processor (FastAPI BackgroundTasks)"]
        JOB["Process Document Job"]
        ROUTER_P["Type Router"]

        subgraph PDF["PDF Processor"]
            FITZ["PyMuPDF fitz.open()"]
            PG_ITER["Iterate Pages"]
            TXT_EXTRACT["Extract text per page"]
            IMG_DETECT["Detect embedded images"]
            IMG_GEMINI["Gemini Vision API\n(describe images)"]
            ANNOT["Merge text + visual desc"]
        end

        subgraph IMAGE["Image Processor"]
            PIL["Pillow load + normalize"]
            TESS["Tesseract OCR\n(pytesseract)"]
            GEM_VIS["Gemini Vision\n(full image description)"]
            IMG_MERGE["Merge OCR + AI description"]
        end

        subgraph TEXT["Text Processor"]
            TXT_READ["Read file"]
            TXT_NORM["Normalize encoding\n(chardet + fix_text)"]
        end

        EMBED_P["Sentence Transformer\nEmbedder"]
        CHROMA_S["Store in ChromaDB"]
        PG_UPD["Update DB status\n→ 'ready'"]
        NOTIFY["WebSocket/SSE notify\nclient: 'ready'"]
    end

    REQ --> AUTH_CHK --> SIZE_CHK --> TYPE_CHK --> VIRU_S --> SAVE_RAW --> JOB_Q --> RESP_201
    JOB_Q --> JOB --> ROUTER_P
    ROUTER_P -->|PDF| FITZ --> PG_ITER --> TXT_EXTRACT & IMG_DETECT
    IMG_DETECT --> IMG_GEMINI --> ANNOT
    TXT_EXTRACT --> ANNOT
    ROUTER_P -->|Image| PIL --> TESS & GEM_VIS --> IMG_MERGE
    ROUTER_P -->|Text| TXT_READ --> TXT_NORM
    ANNOT & IMG_MERGE & TXT_NORM --> EMBED_P --> CHROMA_S --> PG_UPD --> NOTIFY
```

---

## 9. Database Architecture

```mermaid
erDiagram
    USERS {
        uuid id PK
        varchar email UK
        varchar name
        varchar hashed_password
        varchar role "student|admin"
        boolean is_active
        varchar preferred_llm "gemini|ollama"
        jsonb settings
        timestamp created_at
        timestamp last_login
    }

    SESSIONS {
        uuid id PK
        uuid user_id FK
        varchar subject
        varchar title
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    MESSAGES {
        uuid id PK
        uuid session_id FK
        uuid user_id FK
        varchar role "user|assistant"
        text content
        jsonb sources "citations array"
        varchar intent "qa|quiz|summarize"
        integer token_count
        integer latency_ms
        varchar llm_provider
        timestamp created_at
    }

    DOCUMENTS {
        uuid id PK
        uuid user_id FK
        varchar filename
        varchar file_type
        bigint file_size_bytes
        varchar subject
        varchar status "processing|ready|failed"
        varchar storage_path
        varchar chroma_collection
        integer chunk_count
        jsonb metadata
        timestamp created_at
        timestamp processed_at
    }

    QUIZZES {
        uuid id PK
        uuid user_id FK
        uuid session_id FK
        uuid document_id FK
        varchar subject
        varchar title
        jsonb questions "array of question objects"
        integer question_count
        varchar difficulty "easy|medium|hard"
        varchar status "draft|completed"
        timestamp created_at
    }

    QUIZ_ATTEMPTS {
        uuid id PK
        uuid quiz_id FK
        uuid user_id FK
        jsonb answers "user answer array"
        integer score
        integer max_score
        integer time_seconds
        timestamp completed_at
    }

    PROGRESS {
        uuid id PK
        uuid user_id FK
        varchar subject
        date study_date
        integer minutes_studied
        integer questions_asked
        integer quizzes_taken
        float avg_quiz_score
        integer documents_uploaded
        jsonb mastery_scores "per-topic object"
    }

    USAGE_EVENTS {
        uuid id PK
        uuid user_id FK
        varchar event_type "chat|quiz|upload|summary"
        varchar subject
        jsonb metadata
        integer token_count
        timestamp created_at
    }

    USERS ||--o{ SESSIONS : "has"
    SESSIONS ||--o{ MESSAGES : "contains"
    USERS ||--o{ MESSAGES : "sends"
    USERS ||--o{ DOCUMENTS : "uploads"
    USERS ||--o{ QUIZZES : "takes"
    USERS ||--o{ PROGRESS : "tracks"
    USERS ||--o{ USAGE_EVENTS : "generates"
    SESSIONS ||--o{ QUIZZES : "includes"
    DOCUMENTS ||--o{ QUIZZES : "generates"
    QUIZZES ||--o{ QUIZ_ATTEMPTS : "has"
```

---

## 10. Streaming Architecture

```mermaid
sequenceDiagram
    participant FE as React Frontend
    participant BE as FastAPI
    participant Q as StreamQueue (asyncio)
    participant AG as LangGraph Agent
    participant LLM as Gemini / Ollama

    FE->>BE: POST /api/chat/message {question}
    BE->>BE: Create message_id
    BE->>Q: Create queue(message_id)
    BE->>AG: invoke_async(state) [background task]
    BE-->>FE: 202 {message_id}

    FE->>BE: GET /api/stream/{message_id}\nAccept: text/event-stream
    BE-->>FE: 200 SSE connection opened

    AG->>LLM: Stream completion request
    loop Token streaming
        LLM-->>AG: token chunk
        AG->>Q: queue.put(token)
        Q-->>BE: yield token
        BE-->>FE: data: {"token": "Because..."}\n\n
    end

    AG->>AG: Build sources, save memory
    AG->>Q: queue.put({"done": true, "sources": [...], "metadata": {...}})
    Q-->>BE: yield final event
    BE-->>FE: data: {"done": true, "sources": [...]}\n\n
    BE-->>FE: event: close\ndata: {}\n\n
    FE->>FE: Close EventSource\nRender final message
```

---

## 11. Deployment Architecture

```mermaid
flowchart TD
    subgraph DEV["Development (Local)"]
        DEV_FE["Vite Dev Server\nlocalhost:5173"]
        DEV_BE["Uvicorn + --reload\nlocalhost:8000"]
        DEV_DB["PostgreSQL (Docker)\nlocalhost:5432"]
        DEV_REDIS["Redis (Docker)\nlocalhost:6379"]
        DEV_CHROMA["ChromaDB (embedded)\n./data/chroma"]
    end

    subgraph DOCKER["Docker Compose (Production)"]
        NGINX_C["nginx:alpine\nport 80/443"]
        FE_C["frontend:latest\n(Vite build served by nginx)"]
        BE_C["backend:latest\n(Uvicorn 4 workers)"]
        PG_C["postgres:15-alpine\nport 5432"]
        REDIS_C["redis:7-alpine\nport 6379"]
        CHROMA_C["chromadb/chroma\nport 8001"]
        OLLAMA_C["ollama/ollama\nport 11434 (optional)"]
    end

    subgraph VOLUMES["Named Volumes"]
        VOL_PG["pg_data"]
        VOL_CHROMA["chroma_data"]
        VOL_UPLOADS["uploads_data"]
        VOL_REDIS["redis_data"]
    end

    NGINX_C --> FE_C & BE_C
    PG_C --> VOL_PG
    CHROMA_C --> VOL_CHROMA
    BE_C --> VOL_UPLOADS
    REDIS_C --> VOL_REDIS
    BE_C --> PG_C & REDIS_C & CHROMA_C & OLLAMA_C
```

### 11.1 Environment Configuration

```
# .env.example
# --- Backend ---
DATABASE_URL=postgresql+asyncpg://edunex:password@localhost:5432/edunex
REDIS_URL=redis://localhost:6379/0
CHROMA_PATH=./data/chroma_db
UPLOADS_PATH=./data/uploads

# --- LLM ---
GOOGLE_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.0-flash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
DEFAULT_LLM_PROVIDER=gemini

# --- Auth ---
JWT_PRIVATE_KEY_PATH=./keys/private.pem
JWT_PUBLIC_KEY_PATH=./keys/public.pem
ACCESS_TOKEN_TTL_MINUTES=15
REFRESH_TOKEN_TTL_DAYS=7

# --- App ---
MAX_UPLOAD_MB=50
ALLOWED_FILE_TYPES=pdf,png,jpg,jpeg,txt,md
CORS_ORIGINS=http://localhost:5173,https://yourdomain.com
LOG_LEVEL=INFO

# --- Frontend ---
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_NAME=EduNex AI
```

---

## 12. Module Responsibility Map

| Module | Location | Responsibility |
|--------|----------|---------------|
| `app/main.py` | Backend | App factory, middleware registration, lifespan events |
| `app/config.py` | Backend | Pydantic Settings — all env vars, validation |
| `app/dependencies.py` | Backend | Shared DI: `get_db()`, `get_current_user()`, `get_llm()` |
| `app/routers/auth.py` | Backend | HTTP handlers for login, register, refresh, logout |
| `app/routers/chat.py` | Backend | Receive messages, dispatch to agent, return message_id |
| `app/routers/documents.py` | Backend | Upload handler, status polling, delete |
| `app/routers/stream.py` | Backend | SSE event stream endpoint |
| `app/services/auth_service.py` | Backend | JWT issue/verify, bcrypt, Redis token management |
| `app/services/chat_service.py` | Backend | Session CRUD, message persistence, history retrieval |
| `app/services/document_service.py` | Backend | File validation, storage, trigger processing pipeline |
| `app/services/llm_service.py` | Backend | Route to Gemini or Ollama, handle failover |
| `app/agents/orchestrator.py` | Agents | LangGraph StateGraph, node wiring, entry point |
| `app/agents/qa_agent.py` | Agents | RAG-augmented Q&A, citation extraction |
| `app/agents/quiz_agent.py` | Agents | Generate MCQ/TF/fill-blank from retrieved content |
| `app/agents/summarizer_agent.py` | Agents | Hierarchical document summarization |
| `app/agents/safety_agent.py` | Agents | Prompt injection detection, content policy |
| `app/agents/progress_agent.py` | Agents | Analyze learning patterns, generate insights |
| `app/rag/loader.py` | RAG | Load PDF/image/text using PyMuPDF, Pillow, Tesseract |
| `app/rag/chunker.py` | RAG | Split text into semantic chunks with overlap |
| `app/rag/embedder.py` | RAG | Sentence Transformer embeddings, batch processing |
| `app/rag/vectorstore.py` | RAG | ChromaDB client, collection management |
| `app/rag/retriever.py` | RAG | Top-K similarity search, threshold filter, reranking |
| `app/models/*.py` | DB | SQLAlchemy async ORM models |
| `app/schemas/*.py` | Validation | Pydantic v2 request/response schemas |
| `app/repositories/*.py` | DB | Async DB queries, CRUD operations |
| `frontend/src/hooks/useSSE.ts` | Frontend | Manage EventSource connection lifecycle |
| `frontend/src/hooks/useChat.ts` | Frontend | Send messages, manage chat state |
| `frontend/src/stores/authStore.ts` | Frontend | JWT storage in memory, refresh logic |

---

## 13. Inter-Module Communication

| From | To | Protocol | Data Format |
|------|----|----------|-------------|
| Browser | NGINX | HTTPS | HTTP/1.1, HTTP/2 |
| NGINX | FastAPI | HTTP (internal) | JSON |
| React → Backend | Axios | REST over HTTPS | JSON |
| React ← Backend | EventSource | SSE | `data: {...}\n\n` |
| FastAPI → LangGraph | Python call | In-process async | TypedDict state |
| FastAPI → PostgreSQL | asyncpg | SQL | SQLAlchemy async |
| FastAPI → Redis | aioredis | Redis protocol | String / Hash |
| FastAPI → ChromaDB | HTTP (embedded) | gRPC / HTTP | Protobuf / JSON |
| LangGraph → Gemini | HTTPS | REST | JSON (LangChain) |
| LangGraph → Ollama | HTTP | REST | JSON |
| LangGraph → ChromaDB | Python | In-process | Vector arrays |
| Background → Frontend | SSE queue | asyncio.Queue | JSON events |

