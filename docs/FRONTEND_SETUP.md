# AisynEdu — Frontend Setup & Architecture Guide

## Overview

The **AisynEdu** frontend is a high-performance, modern single-page application (SPA) built using **React 18**, **TypeScript**, and **Tailwind CSS**. It provides students and educators with an intuitive, unified workspace for interacting with specialized LangGraph AI agents, indexing course textbooks, generating interactive quizzes, synthesizing revision notes, and visualizing learning telemetry.

---

## Tech Stack

| Technology | Role |
| :--- | :--- |
| **React 18.3** | Component UI library |
| **TypeScript 5.5** | Type-safe development & interfaces |
| **Vite 5.4** | Ultra-fast build tool and dev server |
| **Tailwind CSS 3.4** | Utility-first responsive styling & dark mode |
| **React Router 6.26** | Client-side routing & protected routes |
| **Axios 1.7** | HTTP client with JWT interceptors & token refresh |
| **React-Markdown + KaTeX** | Rich academic rendering with mathematical formatting ($...$, $$...$$) |
| **Lucide React** | Clean, accessible iconography |
| **Canvas-Confetti** | Celebration feedback upon quiz completion |

---

## Directory Structure

```
frontend/
├── index.html                   # HTML entry point with Inter & KaTeX fonts
├── package.json                 # Project dependencies and build scripts
├── tsconfig.json                # Strict TypeScript configuration
├── vite.config.js               # Dev server configuration with /api reverse proxy
├── tailwind.config.js           # Theme colors, dark mode ('class'), and font families
├── postcss.config.js            # PostCSS pipeline (Tailwind & Autoprefixer)
├── src/
│   ├── main.tsx                 # React DOM root entry
│   ├── App.tsx                  # Route registry and theme/auth providers
│   ├── index.css                # Tailwind directives and KaTeX styling
│   ├── types/                   # Strongly typed contracts
│   │   ├── auth.ts              # User, AuthTokens, Login/Register payloads
│   │   ├── chat.ts              # ChatMessage, ChatSession, Citation
│   │   ├── documents.ts         # DocumentItem, DocumentUploadResponse
│   │   ├── quiz.ts              # Quiz, QuizQuestion, QuizResult
│   │   ├── multimodal.ts        # UploadedImageItem, ExplainImageRequest
│   │   └── analytics.ts         # DashboardAnalytics
│   ├── context/
│   │   ├── AuthContext.tsx      # Authentication state, login, register, logout
│   │   └── ThemeContext.tsx     # Light & dark theme state toggle
│   ├── services/
│   │   ├── api.ts               # Axios instance with Bearer interceptors
│   │   ├── authService.ts       # Auth endpoints & profile management
│   │   ├── chatService.ts       # Session management & LangGraph query dispatch
│   │   ├── documentService.ts   # Document upload, listing, and deletion
│   │   ├── multimodalService.ts # Diagram uploads, Gemini Vision explanations
│   │   ├── quizService.ts       # Quiz generation, scoring, and history
│   │   └── analyticsService.ts  # Telemetry computation & progress tracking
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx      # Main navigation, workspace links, user preview
│   │   │   ├── Navbar.tsx       # Topbar, theme toggle, quick action buttons
│   │   │   ├── Layout.tsx       # Responsive layout shell (Sidebar + Navbar + Content)
│   │   │   └── ProtectedRoute.tsx # Route guard enforcing authentication
│   │   ├── common/
│   │   │   ├── Button.tsx       # Multi-variant button with loading spinner
│   │   │   ├── Card.tsx         # Card container with dark mode border
│   │   │   ├── Input.tsx        # Accessible form input with icons and error text
│   │   │   ├── Badge.tsx        # Status pills for intents and difficulties
│   │   │   ├── Modal.tsx        # Accessible modal with backdrop blur
│   │   │   └── EmptyState.tsx   # Actionable empty state screen
│   │   ├── chat/
│   │   │   ├── ChatMessage.tsx  # Markdown + KaTeX math + citations + quiz preview
│   │   │   ├── ChatInput.tsx    # Multi-agent intent selector + image attachment
│   │   │   ├── CitationBadge.tsx # Document citation pill with page numbers
│   │   │   └── ImageUploaderModal.tsx # Diagram and math illustration uploader
│   │   ├── quiz/
│   │   │   ├── QuizQuestionCard.tsx # MCQ card with options & instant explanations
│   │   │   └── QuizResultView.tsx # Score celebration and performance breakdown
│   │   └── documents/
│   │       ├── DocumentUploadModal.tsx # PDF upload with validation and progress
│   │       └── DocumentListItem.tsx # Document metadata, status, and delete action
│   └── pages/
│       ├── LandingPage.tsx      # Public product landing, feature grid, and CTAs
│       ├── LoginPage.tsx        # User sign-in with validation and error alerts
│       ├── RegisterPage.tsx     # Student registration with password strength meter
│       ├── DashboardPage.tsx    # Overview, KPI cards, recent chats, study materials
│       ├── ChatPage.tsx         # AI Tutor chat, citations, multimodal vision
│       ├── DocumentsPage.tsx    # Document library with search, filter, and upload
│       ├── QuizPage.tsx         # Practice quiz generator, MCQ test, score history
│       ├── StudyNotesPage.tsx   # Automated revision notes and LaTeX formula export
│       ├── AnalyticsPage.tsx    # Progress telemetry, weekly activity, subject charts
│       ├── ProfilePage.tsx      # Account settings, LLM provider, theme selector
│       └── NotFoundPage.tsx     # 404 fallback page
```

---

## Application Pages & Workflows

### 1. Landing Page (`/`)
- Professional SaaS hero introducing EduNex AI with call-to-actions.
- Feature grid detailing the Agentic Tutor, RAG Document Grounding, Multimodal Vision, Quiz Engine, and Study Summaries.
- 3-step visual workflow (*Upload Materials* &rarr; *Engage with Tutor* &rarr; *Test & Master*).
- Dark/light mode toggle in navigation.

### 2. Authentication (`/login`, `/register`)
- **Login**: Email and password authentication with clear error alerts.
- **Registration**: Name, email, password with an interactive 5-point security requirement checklist (length, uppercase, lowercase, digit, special character).
- Default LLM provider choice (Gemini 2.0 Flash vs. Ollama Local).
- JWT storage in `localStorage` with automated refresh token rotation.
- **Protected Routes**: Unauthenticated users visiting `/dashboard`, `/chat`, `/documents`, etc., are automatically redirected to `/login`.

### 3. Student Dashboard (`/dashboard`)
- Personalized welcome banner with daily motivation.
- 4 primary KPI metrics: *Questions Explored*, *Indexed Materials*, *Quizzes Completed*, and *Study Day Streak*.
- Recent study conversations list with quick-resume buttons.
- Uploaded study materials preview with processing status badges.
- Quick actions to initiate new chats, upload materials, or take quizzes.

### 4. AI Tutor Chat (`/chat`)
- Unified interface connected directly to the FastAPI `/api/v1/chat/message` endpoint.
- Session selector sidebar with "+ New Chat" session creation modal.
- Rich Markdown rendering with mathematical equations rendered via KaTeX ($E = mc^2$ and block equations).
- Document citations with source document name and page number.
- Multimodal diagram and math illustration uploader (`ImageUploaderModal`).
- Intent routing selector:
  - **Auto**: Routes automatically to the optimal agent capability.
  - **Concept Explanation**: Beginner to advanced conceptual deep dive.
  - **Document Search (RAG)**: Textbook-grounded retrieval.
  - **Generate Quiz**: Practice questions directly inside the chat thread.
  - **Summarize Notes**: High-yield revision points.
- Model provider toggle (Gemini 2.0 Flash vs. Ollama).

### 5. Document Library (`/documents`)
- File upload supporting academic PDFs up to 25 MB.
- Real-time indexing status (`ready`, `processing`, `failed`).
- Metadata inspection: File size in MB, chunk count, upload timestamp, and subject classification.
- Document search and subject filtering.
- One-click "Ask Tutor" to launch an AI session grounded specifically in that document.
- Secure document deletion removing vector embeddings from ChromaDB.

### 6. Quiz Center (`/quiz`)
- Custom practice quiz generator with difficulty (Beginner, Intermediate, Advanced), topic, question count, and optional document grounding.
- Interactive multiple-choice questions (A, B, C, D) with sleek selection feedback.
- Automated scoring with score percentage, mastery rating, and confetti celebration for scores &ge; 70%.
- Step-by-step pedagogical explanation for every question.
- Quiz history tracking.

### 7. Study Notes & Summaries (`/notes`)
- Synthesizes structured revision notes from course topics or uploaded textbooks.
- Sections: Core Definitions, Mechanisms, Mathematical Relations, and Exam Pitfalls.
- One-click copy and Markdown (.md) file download.
- Saved notes archive.

### 8. Analytics Dashboard (`/analytics`)
- Visual telemetry on learning activity:
  - Weekly 7-day bar chart comparing questions asked vs. quizzes taken.
  - Subject focus breakdown bars (e.g. Computer Science, Mathematics, Physics).
  - Study streak and average quiz score.

### 9. User Profile (`/profile`)
- Displays account details, email, role, and membership date.
- Update full name and default LLM orchestrator (Gemini 2.0 Flash vs. Ollama Local).
- Theme toggle (Light / Dark).
- Secure logout.

---

## Setup & Execution

### Prerequisites
- Node.js &ge; 18.x (tested on Node v24.15.0)
- npm &ge; 9.x (tested on npm 11.12.1)
- Running EduNex AI backend on `http://127.0.0.1:8000`

### Installation
```bash
cd frontend
npm install
```

### Development Server
```bash
npm run dev
```
The application will launch at `http://localhost:3000`. Vite's built-in reverse proxy automatically forwards all `/api/*` requests to the FastAPI backend (`http://127.0.0.1:8000`).

### Production Build
```bash
npm run build
```
Generates optimized, minified production assets in `frontend/dist/`.

