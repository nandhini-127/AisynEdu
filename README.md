# AisynEdu

> **Learn. Connect. Evolve.**

**AisynEdu** is an AI-powered personalized learning platform that helps students understand concepts, generate intelligent study notes, practice quizzes, and learn more effectively.

---

## 🌟 Key Capabilities

- **Agentic AI Tutor**: Pedagogically rigorous conceptual breakdowns with topic drift prevention, adaptive difficulty levels (Beginner, Intermediate, Advanced), and interactive dialogue.
- **Synthesized Study Notes & PDF Export**: Automated generation of structured revision notes, LaTeX mathematical formulations ($...$), and one-click export into beautifully formatted, multi-page print-ready PDF documents.
- **Interactive Practice Quiz Center**: Dynamically generated Multiple Choice Questions (MCQs) with options, answer verification, and in-depth pedagogical explanations.
- **RAG Document Grounding**: Multi-tenant course material indexing with vector embeddings and page-level source citations.
- **Multimodal Visual Learning**: Upload and analyze educational diagrams, charts, and mathematical OCR snapshots.
- **Personalized Analytics & Login Streaks**: Real-time tracking of study habits, subject mastery, quiz history, and consecutive daily login streaks.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons, KaTeX |
| **Backend** | FastAPI, Python 3.10, SQLAlchemy 2.0 (asyncpg), Pydantic v2 |
| **AI Orchestration** | LangGraph, LangChain, Google Gemini API (`google-genai`), Ollama fallback |
| **Document Processing** | PyMuPDF (fitz), ReportLab (PDF Synthesis) |
| **Database & Vector Storage** | PostgreSQL 16 (Alembic migrations), ChromaDB |
| **Deployment** | Docker, Docker Compose, Nginx Reverse Proxy |

---

## 🚀 Quick Start (Docker Compose)

### Prerequisites
- Docker & Docker Compose
- Google Gemini API Key

### Running Locally

1. **Clone the repository and configure environment variables**:
   ```bash
   cp backend/.env.example backend/.env
   # Ensure GOOGLE_API_KEY is configured in .env
   ```

2. **Launch all services**:
   ```bash
   docker-compose up -d --build
   ```

3. **Access the application**:
   - **Frontend UI**: [http://localhost:3000](http://localhost:3000)
   - **Backend API & Swagger Docs**: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
   - **API Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## 📄 License
All rights reserved © AisynEdu.

