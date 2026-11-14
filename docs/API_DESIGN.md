# EduNex AI — API Design Specification

> **Version:** 1.0  
> **Base URL:** `http://localhost:8000/api` (dev) · `https://api.edunex.ai/api` (prod)  
> **Auth:** Bearer JWT (RS256) in `Authorization` header  
> **Format:** JSON request/response bodies  
> **OpenAPI Docs:** `/docs` (Swagger UI) · `/redoc` (ReDoc)

---

## Table of Contents
1. [General Conventions](#1-general-conventions)
2. [Authentication Endpoints](#2-authentication-endpoints)
3. [Chat & Session Endpoints](#3-chat--session-endpoints)
4. [Document Endpoints](#4-document-endpoints)
5. [Quiz Endpoints](#5-quiz-endpoints)
6. [Progress Endpoints](#6-progress-endpoints)
7. [Streaming Endpoint](#7-streaming-endpoint)
8. [Admin / Analytics Endpoints](#8-admin--analytics-endpoints)
9. [Error Response Format](#9-error-response-format)
10. [Rate Limits](#10-rate-limits)
11. [Pydantic Schemas Reference](#11-pydantic-schemas-reference)

---

## 1. General Conventions

### Request Headers

```
Content-Type: application/json
Authorization: Bearer <access_token>     # Required for all protected endpoints
X-Request-ID: <uuid>                     # Optional; echoed in response headers
```

### Response Envelope

All responses follow a consistent envelope:

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-11-12T13:00:00Z",
    "version": "1.0"
  }
}
```

### Pagination (list endpoints)

```json
{
  "success": true,
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 150,
    "has_next": true
  }
}
```

### Standard HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 202 | Accepted (async processing started) |
| 204 | No Content (delete success) |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (invalid/missing token) |
| 403 | Forbidden (insufficient role) |
| 404 | Not Found |
| 409 | Conflict (e.g., email already exists) |
| 422 | Unprocessable Entity (Pydantic error) |
| 429 | Too Many Requests |
| 500 | Internal Server Error |
| 503 | Service Unavailable (LLM provider down) |

---

## 2. Authentication Endpoints

### `POST /api/auth/register`

Register a new student account.

**Request Body:**
```json
{
  "name": "Nandhini",
  "email": "nandhini@example.com",
  "password": "SecurePass123!",
  "role": "student"
}
```

**Validation:**
- `email`: valid format, unique in DB
- `password`: min 8 chars, 1 uppercase, 1 digit, 1 special char
- `role`: `"student"` | `"admin"` (admin requires invite token — future)

**Response `201`:**
```json
{
  "success": true,
  "data": {
    "user_id": "uuid",
    "name": "Nandhini",
    "email": "nandhini@example.com",
    "role": "student",
    "created_at": "2026-11-12T13:00:00Z"
  }
}
```

---

### `POST /api/auth/login`

Authenticate and receive tokens.

**Request Body:**
```json
{
  "email": "nandhini@example.com",
  "password": "SecurePass123!"
}
```

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 900,
    "user": {
      "id": "uuid",
      "name": "Nandhini",
      "email": "nandhini@example.com",
      "role": "student",
      "preferred_llm": "gemini"
    }
  }
}
```

**Side effect:** Sets `refresh_token` as httpOnly Secure SameSite=Strict cookie (7 days TTL).

---

### `POST /api/auth/refresh`

Exchange refresh token for new access token.

**Headers:** Cookie: `refresh_token=...`  
**Request Body:** _(none)_

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "expires_in": 900
  }
}
```

---

### `POST /api/auth/logout`

Revoke refresh token.

**Auth:** Required  
**Request Body:** _(none)_  
**Response `204`:** No Content

---

### `GET /api/auth/me`

Get current user profile.

**Auth:** Required

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "Nandhini",
    "email": "nandhini@example.com",
    "role": "student",
    "preferred_llm": "gemini",
    "settings": {
      "theme": "dark",
      "language": "en",
      "notifications": true
    },
    "created_at": "2026-11-12T13:00:00Z",
    "last_login": "2026-11-12T13:25:00Z"
  }
}
```

---

### `PATCH /api/auth/me`

Update user profile / preferences.

**Auth:** Required  
**Request Body:**
```json
{
  "name": "Nandhini S",
  "preferred_llm": "ollama",
  "settings": {
    "theme": "light"
  }
}
```

**Response `200`:** Updated user object (same as `/me`)

---

## 3. Chat & Session Endpoints

### `POST /api/sessions`

Create a new chat session.

**Auth:** Required  
**Request Body:**
```json
{
  "subject": "Mathematics",
  "title": "Calculus — Derivatives",
  "document_ids": ["uuid1", "uuid2"]
}
```

**Response `201`:**
```json
{
  "success": true,
  "data": {
    "session_id": "uuid",
    "subject": "Mathematics",
    "title": "Calculus — Derivatives",
    "document_ids": ["uuid1", "uuid2"],
    "created_at": "2026-11-12T13:00:00Z"
  }
}
```

---

### `GET /api/sessions`

List all sessions for current user.

**Auth:** Required  
**Query Params:** `?page=1&page_size=20&subject=Mathematics`

**Response `200`:**
```json
{
  "success": true,
  "data": [
    {
      "session_id": "uuid",
      "subject": "Mathematics",
      "title": "Calculus — Derivatives",
      "last_message_at": "2026-11-12T13:30:00Z",
      "message_count": 12,
      "is_active": true
    }
  ],
  "pagination": { "page": 1, "page_size": 20, "total": 5, "has_next": false }
}
```

---

### `GET /api/sessions/{session_id}`

Get a session with its full message history.

**Auth:** Required  
**Response `200`:**
```json
{
  "success": true,
  "data": {
    "session_id": "uuid",
    "subject": "Mathematics",
    "title": "Calculus — Derivatives",
    "messages": [
      {
        "id": "uuid",
        "role": "user",
        "content": "What is the derivative of x^2?",
        "created_at": "2026-11-12T13:00:00Z"
      },
      {
        "id": "uuid",
        "role": "assistant",
        "content": "The derivative of x² is **2x**...",
        "sources": [
          { "title": "Calculus Chapter 3", "page": 42, "score": 0.95 }
        ],
        "intent": "qa",
        "token_count": 312,
        "latency_ms": 1240,
        "created_at": "2026-11-12T13:00:05Z"
      }
    ]
  }
}
```

---

### `POST /api/chat/message`

Send a message and start agent processing.

**Auth:** Required  
**Request Body:**
```json
{
  "session_id": "uuid",
  "content": "Explain integration by parts with an example",
  "intent": "qa",
  "document_ids": ["uuid1"],
  "llm_override": null
}
```

**Fields:**
- `intent`: `"qa"` | `"quiz"` | `"summarize"` | `"progress"` | `"auto"` (default)
- `llm_override`: `"gemini"` | `"ollama"` | `null` (use user preference)
- `document_ids`: scope retrieval to specific uploaded docs

**Response `202`:**
```json
{
  "success": true,
  "data": {
    "message_id": "uuid",
    "stream_url": "/api/stream/uuid",
    "status": "processing"
  }
}
```

---

### `DELETE /api/sessions/{session_id}`

Delete a session and all its messages.

**Auth:** Required  
**Response `204`:** No Content

---

## 4. Document Endpoints

### `POST /api/documents/upload`

Upload a study document.

**Auth:** Required  
**Content-Type:** `multipart/form-data`  
**Request Body:**
```
file: <binary>
subject: "Physics"
title: "Thermodynamics Chapter 4"
```

**Validation:**
- Max file size: 50MB
- Allowed types: `pdf`, `png`, `jpg`, `jpeg`, `txt`, `md`

**Response `202`:**
```json
{
  "success": true,
  "data": {
    "document_id": "uuid",
    "filename": "thermo_ch4.pdf",
    "file_type": "pdf",
    "file_size_bytes": 2456789,
    "subject": "Physics",
    "title": "Thermodynamics Chapter 4",
    "status": "processing",
    "created_at": "2026-11-12T13:00:00Z"
  }
}
```

---

### `GET /api/documents`

List all documents for current user.

**Auth:** Required  
**Query Params:** `?subject=Physics&status=ready&page=1`

**Response `200`:**
```json
{
  "success": true,
  "data": [
    {
      "document_id": "uuid",
      "filename": "thermo_ch4.pdf",
      "file_type": "pdf",
      "subject": "Physics",
      "status": "ready",
      "chunk_count": 42,
      "created_at": "2026-11-12T13:00:00Z",
      "processed_at": "2026-11-12T13:01:30Z"
    }
  ]
}
```

---

### `GET /api/documents/{document_id}/status`

Poll processing status.

**Auth:** Required  
**Response `200`:**
```json
{
  "success": true,
  "data": {
    "document_id": "uuid",
    "status": "ready",
    "chunk_count": 42,
    "processed_at": "2026-11-12T13:01:30Z",
    "error_message": null
  }
}
```

**Status values:** `processing` → `ready` | `failed`

---

### `DELETE /api/documents/{document_id}`

Delete a document and its vectors.

**Auth:** Required  
**Response `204`:** No Content  
**Side effects:** Removes from ChromaDB collection + file storage

---

## 5. Quiz Endpoints

### `POST /api/quiz/generate`

Generate a quiz from documents or a topic.

**Auth:** Required  
**Request Body:**
```json
{
  "session_id": "uuid",
  "document_ids": ["uuid1"],
  "subject": "Physics",
  "topic": "Laws of Thermodynamics",
  "question_count": 5,
  "difficulty": "medium",
  "question_types": ["mcq", "true_false", "fill_blank"]
}
```

**Response `202`:**
```json
{
  "success": true,
  "data": {
    "quiz_id": "uuid",
    "status": "generating",
    "stream_url": "/api/stream/quiz_uuid"
  }
}
```

---

### `GET /api/quiz/{quiz_id}`

Get a generated quiz.

**Auth:** Required  
**Response `200`:**
```json
{
  "success": true,
  "data": {
    "quiz_id": "uuid",
    "title": "Thermodynamics Quiz",
    "subject": "Physics",
    "difficulty": "medium",
    "status": "ready",
    "questions": [
      {
        "id": 1,
        "type": "mcq",
        "question": "Which law states that energy cannot be created or destroyed?",
        "options": ["Zeroth", "First", "Second", "Third"],
        "answer": "First",
        "explanation": "The First Law of Thermodynamics is the law of conservation of energy.",
        "source_chunk": "Thermo Ch4, page 12"
      },
      {
        "id": 2,
        "type": "true_false",
        "question": "Entropy always decreases in a closed system.",
        "answer": false,
        "explanation": "The Second Law states entropy tends to increase."
      },
      {
        "id": 3,
        "type": "fill_blank",
        "question": "The ______ law of thermodynamics defines temperature.",
        "answer": "Zeroth",
        "explanation": "The Zeroth Law establishes thermal equilibrium."
      }
    ],
    "created_at": "2026-11-12T13:00:00Z"
  }
}
```

---

### `POST /api/quiz/{quiz_id}/submit`

Submit quiz answers for scoring.

**Auth:** Required  
**Request Body:**
```json
{
  "answers": [
    { "question_id": 1, "answer": "First" },
    { "question_id": 2, "answer": false },
    { "question_id": 3, "answer": "Zeroth" }
  ],
  "time_seconds": 180
}
```

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "attempt_id": "uuid",
    "quiz_id": "uuid",
    "score": 3,
    "max_score": 3,
    "percentage": 100.0,
    "time_seconds": 180,
    "results": [
      {
        "question_id": 1,
        "is_correct": true,
        "user_answer": "First",
        "correct_answer": "First",
        "explanation": "Correct! The First Law..."
      }
    ],
    "feedback": "Excellent! You have a strong grasp of Thermodynamics fundamentals.",
    "completed_at": "2026-11-12T13:05:00Z"
  }
}
```

---

### `GET /api/quiz/history`

Get user's quiz attempt history.

**Auth:** Required  
**Query Params:** `?subject=Physics&page=1&page_size=10`

**Response `200`:**
```json
{
  "success": true,
  "data": [
    {
      "attempt_id": "uuid",
      "quiz_title": "Thermodynamics Quiz",
      "subject": "Physics",
      "score": 3,
      "max_score": 3,
      "percentage": 100.0,
      "completed_at": "2026-11-12T13:05:00Z"
    }
  ]
}
```

---

## 6. Progress Endpoints

### `GET /api/progress/summary`

Get overall learning progress summary.

**Auth:** Required  
**Query Params:** `?period=30d` (7d | 30d | 90d | all)

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "period": "30d",
    "total_sessions": 24,
    "total_questions_asked": 186,
    "total_quizzes_taken": 12,
    "avg_quiz_score": 78.4,
    "total_documents_uploaded": 8,
    "current_streak_days": 5,
    "longest_streak_days": 12,
    "subjects_studied": ["Mathematics", "Physics", "Chemistry"],
    "most_active_subject": "Mathematics",
    "tokens_used": 125000,
    "study_time_minutes": 320
  }
}
```

---

### `GET /api/progress/subjects`

Get per-subject progress breakdown.

**Auth:** Required

**Response `200`:**
```json
{
  "success": true,
  "data": [
    {
      "subject": "Mathematics",
      "sessions": 10,
      "questions_asked": 80,
      "quizzes_taken": 5,
      "avg_quiz_score": 82.0,
      "mastery_scores": {
        "Calculus": 85,
        "Algebra": 70,
        "Geometry": 65
      },
      "last_studied": "2026-11-12",
      "study_time_minutes": 140
    }
  ]
}
```

---

### `GET /api/progress/timeline`

Get daily activity for a heatmap/chart.

**Auth:** Required  
**Query Params:** `?start=2026-10-01&end=2026-11-12`

**Response `200`:**
```json
{
  "success": true,
  "data": [
    {
      "date": "2026-11-12",
      "sessions": 2,
      "questions": 15,
      "quizzes": 1,
      "study_minutes": 25,
      "avg_quiz_score": 90.0
    }
  ]
}
```

---

## 7. Streaming Endpoint

### `GET /api/stream/{message_id}`

Connect to SSE stream for a processing message or quiz generation.

**Auth:** Required (via `?token=<access_token>` query param — EventSource cannot set headers)  
**Accept:** `text/event-stream`

**Response:** `200 text/event-stream`

**SSE Event Types:**

```
# Token streaming (Q&A / Summarization)
event: token
data: {"token": "The "}

event: token
data: {"token": "derivative "}

# Safety block
event: blocked
data: {"reason": "off_topic", "message": "I can only help with academic topics."}

# Sources (sent after generation complete)
event: sources
data: {"sources": [{"title": "Calculus Ch3", "page": 42, "score": 0.95}]}

# Quiz questions (streamed as array)
event: quiz_question
data: {"question_index": 0, "question": {...}}

# Completion signal
event: done
data: {"message_id": "uuid", "token_count": 312, "latency_ms": 1240, "intent": "qa"}

# Error
event: error
data: {"code": "LLM_UNAVAILABLE", "message": "Gemini API is temporarily unavailable."}

# Keep-alive (every 15s)
: keep-alive
```

**Client-side usage:**
```typescript
const es = new EventSource(`/api/stream/${messageId}?token=${accessToken}`);
es.addEventListener('token', (e) => appendToken(JSON.parse(e.data).token));
es.addEventListener('done', (e) => finalize(JSON.parse(e.data)));
es.addEventListener('error', () => es.close());
```

---

## 8. Admin / Analytics Endpoints

> **Role required:** `admin`

### `GET /api/admin/analytics`

Platform-wide usage analytics.

**Auth:** Required (admin role)  
**Query Params:** `?period=30d`

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "total_users": 150,
    "active_users_30d": 48,
    "total_sessions": 1240,
    "total_messages": 8900,
    "total_documents": 320,
    "total_quizzes": 480,
    "avg_quiz_score_platform": 74.2,
    "llm_usage": {
      "gemini": 7200,
      "ollama": 1700
    },
    "total_tokens_used": 2450000,
    "top_subjects": ["Mathematics", "Physics", "Chemistry", "History", "English"],
    "daily_active_users": [
      { "date": "2026-11-12", "count": 24 }
    ]
  }
}
```

---

### `GET /api/admin/users`

List all users with usage stats.

**Auth:** Required (admin role)  
**Query Params:** `?page=1&page_size=50&sort=last_login`

**Response `200`:** Paginated user list with usage metrics.

---

## 9. Error Response Format

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request body is invalid.",
    "details": [
      {
        "field": "password",
        "message": "Password must be at least 8 characters."
      }
    ]
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-11-12T13:00:00Z"
  }
}
```

### Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| `VALIDATION_ERROR` | 422 | Pydantic schema failure |
| `INVALID_CREDENTIALS` | 401 | Wrong email or password |
| `TOKEN_EXPIRED` | 401 | Access token expired |
| `TOKEN_INVALID` | 401 | Malformed JWT |
| `REFRESH_TOKEN_INVALID` | 401 | Refresh token invalid/revoked |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource does not exist |
| `EMAIL_TAKEN` | 409 | Email already registered |
| `FILE_TOO_LARGE` | 400 | Exceeds 50MB limit |
| `FILE_TYPE_UNSUPPORTED` | 400 | File type not allowed |
| `RATE_LIMITED` | 429 | Too many requests |
| `LLM_UNAVAILABLE` | 503 | Gemini / Ollama not responding |
| `SAFETY_BLOCKED` | 400 | Content safety check failed |
| `DOCUMENT_NOT_READY` | 400 | Tried to query processing document |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

---

## 10. Rate Limits

| Endpoint Group | Limit | Window |
|----------------|-------|--------|
| `POST /api/auth/login` | 5 requests | 15 minutes (per IP) |
| `POST /api/auth/register` | 3 requests | 1 hour (per IP) |
| `POST /api/chat/message` | 30 requests | 1 hour (per user) |
| `POST /api/documents/upload` | 10 requests | 1 hour (per user) |
| `POST /api/quiz/generate` | 15 requests | 1 hour (per user) |
| `GET /api/stream/*` | 50 connections | 1 hour (per user) |
| All other endpoints | 100 requests | 1 minute (per user) |

**Rate limit headers on all responses:**
```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 24
X-RateLimit-Reset: 1731409200
```

---

## 11. Pydantic Schemas Reference

### Auth Schemas

```python
# schemas/auth.py

class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("password")
    def password_strength(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError("Must contain uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Must contain digit")
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900
    user: UserResponse

class UserResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    role: str
    preferred_llm: str
    model_config = ConfigDict(from_attributes=True)
```

### Chat Schemas

```python
# schemas/chat.py

class SendMessageRequest(BaseModel):
    session_id: UUID
    content: str = Field(min_length=1, max_length=4000)
    intent: Literal["qa", "quiz", "summarize", "progress", "auto"] = "auto"
    document_ids: list[UUID] = Field(default_factory=list)
    llm_override: Optional[Literal["gemini", "ollama"]] = None

class MessageResponse(BaseModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    sources: list[SourceCitation] = []
    intent: str
    token_count: int
    latency_ms: int
    created_at: datetime

class SourceCitation(BaseModel):
    title: str
    page: Optional[int]
    score: float
    snippet: str
```

### Document Schemas

```python
# schemas/document.py

class DocumentUploadResponse(BaseModel):
    document_id: UUID
    filename: str
    file_type: str
    file_size_bytes: int
    subject: str
    status: Literal["processing", "ready", "failed"]
    created_at: datetime

class DocumentStatusResponse(BaseModel):
    document_id: UUID
    status: Literal["processing", "ready", "failed"]
    chunk_count: Optional[int]
    processed_at: Optional[datetime]
    error_message: Optional[str]
```

### Quiz Schemas

```python
# schemas/quiz.py

class QuizGenerateRequest(BaseModel):
    session_id: Optional[UUID] = None
    document_ids: list[UUID] = Field(min_length=1)
    subject: str
    topic: Optional[str] = None
    question_count: int = Field(default=5, ge=3, le=20)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    question_types: list[Literal["mcq", "true_false", "fill_blank"]] = ["mcq"]

class QuizQuestion(BaseModel):
    id: int
    type: Literal["mcq", "true_false", "fill_blank"]
    question: str
    options: Optional[list[str]] = None  # MCQ only
    answer: Union[str, bool]
    explanation: str
    source_chunk: Optional[str] = None

class QuizSubmitRequest(BaseModel):
    answers: list[QuizAnswer]
    time_seconds: int

class QuizAnswer(BaseModel):
    question_id: int
    answer: Union[str, bool]
```

