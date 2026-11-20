from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from app.core.security import validate_password_strength


# Standard response wrapper
class ApiResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
    error: Optional[Any] = None


# Health
class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    database: str
    timestamp: datetime


# Auth & Users
class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=100)
    role: str = "student"
    preferred_llm: str = "gemini"

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("name", mode="before")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        valid_roles = ["student", "admin"]
        if v not in valid_roles:
            raise ValueError(f"Role must be one of {valid_roles}")
        return v


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, v: str) -> str:
        validate_password_strength(v)
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v


class UserRead(UserBase):
    id: UUID
    is_active: bool
    settings: Dict[str, Any] = {}
    created_at: datetime
    last_login: Optional[datetime] = None
    current_streak: int = 0
    longest_streak: int = 0
    last_login_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    preferred_llm: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

    @field_validator("name", mode="before")
    @classmethod
    def sanitize_name(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            return v.strip()
        return v


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def check_new_password_strength(cls, v: str) -> str:
        validate_password_strength(v)
        return v


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # in seconds (30 mins default)
    user: UserRead
    streak_increased: Optional[bool] = None


class TokenRefreshRequest(BaseModel):
    refresh_token: Optional[str] = None


class AdminUserUpdate(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[str] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid_roles = ["student", "admin"]
            if v not in valid_roles:
                raise ValueError(f"Role must be one of {valid_roles}")
        return v


# Chat & Sessions
class SessionCreate(BaseModel):
    subject: str = Field(..., min_length=1, max_length=200)
    title: Optional[str] = None
    document_ids: List[UUID] = []


class SessionRead(BaseModel):
    id: UUID
    subject: str
    title: Optional[str] = None
    is_active: bool
    document_ids: List[UUID] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    session_id: UUID
    content: str = Field(..., min_length=1)
    intent: str = "auto"
    difficulty: str = "intermediate"
    document_ids: List[UUID] = []
    llm_override: Optional[str] = None


class MessageRead(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    sources: List[Dict[str, Any]] = []
    intent: str
    token_count: int
    latency_ms: int
    llm_provider: Optional[str] = None
    created_at: datetime
    quiz_data: Optional[List[Dict[str, Any]]] = None
    summary_data: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[str]] = None
    is_fallback: bool = False
    fallback_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ExportPDFRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300, description="Notes topic or title")
    subject: Optional[str] = Field("General Studies", max_length=200, description="Academic subject")
    content: str = Field(..., min_length=1, description="Markdown formatted notes content")
