# AisynEdu — Backend Setup & Execution Guide

## Overview
The AisynEdu backend is built with **FastAPI**, **SQLAlchemy 2.0 (asyncpg)**, and **Pydantic v2 Settings**, structured for production-grade agentic AI and RAG workflows.

---

## Architecture Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI application factory & lifecycle management
│   ├── core/
│   │   ├── config.py           # Environment-based configuration (Pydantic Settings)
│   │   ├── database.py         # SQLAlchemy async engine & session management
│   │   ├── security.py         # Native bcrypt hashing & JWT token handling
│   │   └── logging.py          # Structured logging configuration
│   ├── api/
│   │   ├── dependencies.py     # Shared dependency injection (auth, db)
│   │   └── routes/
│   │       ├── health.py       # Health check with DB status
│   │       ├── auth.py         # Authentication (Register, Login, Me)
│   │       └── chat.py         # Sessions & Chat Message handling
│   ├── models/
│   │   └── entities.py         # Declarative PostgreSQL schema entities
│   ├── schemas/
│   │   └── base.py             # Pydantic request/response validation schemas
│   ├── services/
│   │   ├── auth_service.py     # User authentication & registration service
│   │   └── chat_service.py     # Chat session and messaging persistence
│   ├── agents/                 # LangGraph orchestration (Phase 4)
│   ├── rag/                    # Document chunking & embedding pipeline (Phase 5)
│   ├── memory/                 # Conversational memory management (Phase 6)
│   ├── multimodal/             # PDF & image processing (Phase 5)
│   ├── guardrails/             # Safety & guardrail enforcement (Phase 4)
│   ├── analytics/              # Learning analytics & metrics (Phase 6)
│   └── utils/                  # Shared helper utilities
├── alembic/                    # Database migrations
│   ├── versions/
│   │   └── 001_initial.py      # Complete schema DDL migration
│   └── env.py
├── tests/
│   ├── conftest.py             # Pytest fixtures & async test client
│   └── unit/
│       ├── test_security.py    # Unit tests for JWT & password hashing
│       └── test_api.py         # Integration tests for health, auth, & chat APIs
├── requirements.txt            # Production dependencies
├── .env.example                # Environment variable blueprint
├── alembic.ini                 # Alembic configuration
└── Dockerfile                  # Containerization specification
```

---

## Setup & Running Locally

### 1. Prerequisites
- Python 3.10+
- PostgreSQL 15+ (Local or Docker container)

### 2. Environment Variables
Create a `.env` file in the `backend/` directory by copying `.env.example`:
```bash
cp .env.example .env
```
Ensure `DATABASE_URL` points to your PostgreSQL instance:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/edunex_db
SYNC_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/edunex_db
```

### 3. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 4. Run Migrations
Apply database schema using Alembic:
```bash
alembic upgrade head
```

### 5. Start the Development Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive API documentation will be available at:
- **Swagger UI:** `http://localhost:8000/api/v1/docs`
- **ReDoc:** `http://localhost:8000/api/v1/redoc`
- **OpenAPI Schema:** `http://localhost:8000/api/v1/openapi.json`

---

## Running Automated Tests

Run the test suite using `pytest`:
```bash
cd backend
python -m pytest tests -v
```

All unit and API integration tests run with an isolated in-memory test database, validating:
- Health check status reporting
- Password hashing & verification
- Access and refresh JWT token generation and decoding
- User registration, duplicate checks, and credential validation
- Authenticated profile inspection (`/api/v1/auth/me`)
- Study session creation and messaging workflows

