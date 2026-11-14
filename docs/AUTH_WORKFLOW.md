# EduNex AI — Authentication and User Management Workflow

> **Document Version:** 1.0  
> **Target System:** EduNex AI Backend  
> **Security Standards:** NIST SP 800-63B / OWASP Top 10 Guidelines

---

## Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [Registration Workflow & Validation](#2-registration-workflow--validation)
3. [Password Security & Hashing](#3-password-security--hashing)
4. [Authentication & Token Issuance](#4-authentication--token-issuance)
5. [Token Rotation & Invalidation](#5-token-rotation--invalidation)
6. [Rate Limiting Mechanism](#6-rate-limiting-mechanism)
7. [Role-Based Access Control (RBAC)](#7-role-based-access-control-rbac)
8. [Data Isolation & Ownership Enforcement](#8-data-isolation--ownership-enforcement)
9. [API Endpoint Reference](#9-api-endpoint-reference)
10. [Test Coverage & Verification](#10-test-coverage--verification)

---

## 1. Architecture Overview

EduNex AI implements a **stateless access token + stateful refresh token** security model:

```
┌────────────────────────────────────────────────────────────────────────┐
│                             CLIENT APP                                 │
└──────────────────┬─────────────────────────────────▲───────────────────┘
     1. /auth/login│                                 │ 2. JWT Access Token (Memory)
                   │                                 │    Refresh Token (HTTP-Only Cookie)
┌──────────────────▼─────────────────────────────────┴───────────────────┐
│                          FASTAPI BACKEND                               │
│                                                                        │
│  ┌─────────────────────────┐         ┌──────────────────────────────┐  │
│  │   Rate Limiter Guard    │         │      JWT Token Service       │  │
│  │ (Sliding Window Limits) │         │   (HS256 / JTI Identifiers)  │  │
│  └───────────┬─────────────┘         └──────────────┬───────────────┘  │
│              │                                      │                  │
│  ┌───────────▼─────────────┐         ┌──────────────▼───────────────┐  │
│  │    Auth & User Service  │         │   RBAC & Ownership Security  │  │
│  │  (Bcrypt Hash Verify)   │         │  (Student vs Admin Isolation)│  │
│  └───────────┬─────────────┘         └──────────────┬───────────────┘  │
└──────────────┼──────────────────────────────────────┼──────────────────┘
               │                                      │
┌──────────────▼──────────────────────────────────────▼──────────────────┐
│                         POSTGRESQL DATABASE                            │
│  ┌──────────────────────────────┐   ┌───────────────────────────────┐  │
│  │         users table          │   │     refresh_tokens table      │  │
│  │  (email, bcrypt_hash, role)  │   │  (jti, user_id, is_revoked)   │  │
│  └──────────────────────────────┘   └───────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Registration Workflow & Validation

### Sanitization and Validation Pipeline
1. **Email Normalization:** Trims leading/trailing whitespace and converts to lowercase before lookup or insertion.
2. **Name Sanitization:** Strips leading/trailing whitespace and enforces `min_length=2, max_length=100`.
3. **Duplicate Prevention:** Query checks existing email addresses and returns `HTTP 400 Bad Request` if duplicate.
4. **Password Policy Enforcement:**
   - Minimum 8 characters.
   - At least 1 uppercase letter (`[A-Z]`).
   - At least 1 lowercase letter (`[a-z]`).
   - At least 1 numeric digit (`[0-9]`).
   - At least 1 special character (`[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?~`]`).

```
Registration Input
       │
       ▼
[Email Normalized & Unique Check] ──(Duplicate)──> 400 Bad Request
       │
       ▼
[Password Complexity Regex Check] ──(Weak)───────> 422 Unprocessable Content
       │
       ▼
[Bcrypt Hash Generation (Rounds=12)]
       │
       ▼
[Insert User Record in PostgreSQL] ──────────────> 201 Created
```

---

## 3. Password Security & Hashing

- **Algorithm:** Native `bcrypt` algorithm with automated salt generation.
- **Work Factor / Rounds:** `12` rounds (balancing security and CPU performance).
- **Truncation Guard:** Explicitly caps password input at 72 bytes before hashing to respect bcrypt specifications without silent truncation vulnerabilities.
- **Storage:** Plain-text passwords are **never** stored in memory beyond request verification and are **never** written to database or logs.

---

## 4. Authentication & Token Issuance

### Login Flow:
1. Client submits credentials to `POST /api/v1/auth/login`.
2. **Rate Limiting Check:** Queries `login_rate_limiter` for key `IP:email`. If threshold exceeded, returns `HTTP 429 Too Many Requests` with retry delay.
3. **Credential Verification:** Compares input password against stored hash using `bcrypt.checkpw()`. If invalid, increments rate limiter counter and returns `HTTP 401 Unauthorized`.
4. **Token Generation:**
   - **Access Token:** Short-lived JWT (30 minutes default) containing `sub` (User UUID), `role` (`student` or `admin`), `type: "access"`, `iat`, and `exp`.
   - **Refresh Token:** Long-lived JWT (7 days default) containing `sub` (User UUID), unique `jti` (UUID hex string), `type: "refresh"`, `iat`, and `exp`.
5. **Persistence:** The `jti`, expiration timestamp, and revocation flag are recorded in the `refresh_tokens` table.
6. **Delivery:**
   - Returned in JSON payload for client memory storage.
   - Set in HTTP-only, secure, same-site cookie (`refresh_token`) scoped to `/api/v1/auth`.

---

## 5. Token Rotation & Invalidation

### Refresh Token Rotation Pattern
When `POST /api/v1/auth/refresh` is invoked:
1. Decodes and verifies JWT signature and expiration.
2. Locates matching `RefreshToken` row in database using `token_jti`.
3. Verifies that `is_revoked == False` and `expires_at > now`.
4. **Invalidates Old Token:** Marks the existing refresh token as `is_revoked = True`.
5. **Issues New Pair:** Generates brand new access token and fresh refresh token with new `jti`.
6. Stored in DB and returned to client.

### Logout:
- Client invokes `POST /api/v1/auth/logout`.
- Marks the active refresh token as `is_revoked = True`.
- Clears the HTTP-only cookie.
- Reusing a revoked refresh token fails with `HTTP 401 Unauthorized`.

### Password Change Invalidation:
- When a user changes their password via `POST /api/v1/auth/change-password`, all active refresh tokens for that user ID are marked revoked. This immediately terminates all active sessions across all devices.

---

## 6. Rate Limiting Mechanism

EduNex AI incorporates a thread-safe sliding window rate limiter in `app/core/rate_limiter.py`:
- **Default Limit:** Max 5 failed attempts per 5-minute sliding window.
- **Tracking Key:** Combination of client IP address and email.
- **Auto-Reset:** Automatically resets upon successful password verification.
- **Protection:** Prevents brute-force dictionary attacks against user accounts.

---

## 7. Role-Based Access Control (RBAC)

EduNex AI provides role-based authorization via FastAPI dependency factories:
- **Roles:**
  - `student`: Standard learner access to personal study sessions, document queries, and quizzes.
  - `admin`: Platform administrative control, user auditing, and system metrics.
- **Dependencies (`app/api/dependencies.py`):**
  - `get_current_user`: Ensures valid JWT token and active user account.
  - `require_role(allowed_roles: List[str])`: Verifies role membership, raising `HTTP 403 Forbidden` if unauthorized.
  - `require_admin`: Direct dependency for admin-only routes.

---

## 8. Data Isolation & Ownership Enforcement

To ensure student privacy and data integrity:
- Every study session, message, document, and quiz is linked to `user_id`.
- The helper `verify_resource_ownership(resource_owner_id, current_user)` is enforced on all resource queries:
  - If `resource_owner_id != current_user.id` and `current_user.role != "admin"`, access is denied with `HTTP 403 Forbidden`.
  - Student A cannot view, inspect, or post into Student B's study sessions.

---

## 9. API Endpoint Reference

| Method | Endpoint | Auth Required | Role | Description |
|---|---|---|---|---|
| `POST` | `/api/v1/auth/register` | No | Any | Register student account with password validation |
| `POST` | `/api/v1/auth/login` | No | Any | Authenticate credentials; returns access & refresh tokens |
| `POST` | `/api/v1/auth/refresh` | No (Token in body/cookie) | Any | Rotate refresh token and issue new access token |
| `POST` | `/api/v1/auth/logout` | No (Token in body/cookie) | Any | Invalidate refresh token and clear cookie |
| `GET` | `/api/v1/auth/me` | Bearer Token | Any | Retrieve authenticated user profile |
| `PATCH` | `/api/v1/auth/me` | Bearer Token | Any | Update profile details (name, preferred LLM, settings) |
| `POST` | `/api/v1/auth/change-password` | Bearer Token | Any | Change password and revoke all active sessions |
| `GET` | `/api/v1/admin/users` | Bearer Token | `admin` | List all registered users (paginated) |
| `PATCH` | `/api/v1/admin/users/{user_id}` | Bearer Token | `admin` | Activate/deactivate user account or change role |

---

## 10. Test Coverage & Verification

Automated test suites under `tests/unit/test_auth_management.py` and `tests/unit/test_security.py` verify:
1. ✅ **Registration Validation:** Rejection of short, missing uppercase, missing digit, or missing special character passwords.
2. ✅ **Brute-Force Rate Limiting:** 5 failed logins trigger `HTTP 429 Too Many Requests`, followed by reset on successful login.
3. ✅ **Unauthorized & Expired Tokens:** Rejection of expired tokens, malformed JWTs, and missing Authorization headers with `HTTP 401`.
4. ✅ **Profile Updates & Password Changes:** Accurate updating of profile attributes, rejection of incorrect old passwords, and validation of new passwords.
5. ✅ **Refresh Token Rotation & Revocation:** Old refresh token invalidation, rejection of reused tokens, and clean logout revocation.
6. ✅ **Role-Based Authorization:** Students attempting to access `/api/v1/admin/users` receive `HTTP 403 Forbidden`; administrators succeed with `HTTP 200 OK`.
7. ✅ **Cross-User Resource Isolation:** Attempts to access or post to another student's session are strictly denied with `HTTP 403 Forbidden`.

