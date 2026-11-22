from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.service import AnalyticsService
from app.api.dependencies import get_current_user, require_admin
from app.core.database import get_db
from app.models.entities import User
from app.schemas.base import ApiResponse

router = APIRouter(prefix="/analytics", tags=["Telemetry & Analytics"])


class QuizAttemptRequest(BaseModel):
    quiz_id: Optional[str] = None
    title: Optional[str] = None
    topic: Optional[str] = None
    difficulty: Optional[str] = "medium"
    score: int = Field(default=0, ge=0)
    total_questions: int = Field(default=0, ge=0)
    percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    answers: Optional[Any] = None
    details: Optional[List[Dict[str, Any]]] = None
    questions: Optional[List[Dict[str, Any]]] = None


@router.post("/quiz-attempt", response_model=ApiResponse)
async def record_quiz_attempt(
    payload: QuizAttemptRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Records a completed quiz attempt for the authenticated student.
    Persists the quiz & attempt records and updates student dashboard analytics.
    """
    attempt = await AnalyticsService.record_quiz_attempt(
        db=db,
        user_id=current_user.id,
        quiz_id_str=payload.quiz_id,
        title=payload.title,
        topic=payload.topic,
        difficulty=payload.difficulty or "medium",
        score=payload.score,
        total_questions=payload.total_questions,
        percentage=payload.percentage,
        answers=payload.answers,
        details=payload.details,
        questions=payload.questions,
    )
    return ApiResponse(
        success=True,
        message="Quiz attempt recorded successfully.",
        data={
            "attempt_id": str(attempt.id),
            "quiz_id": str(attempt.quiz_id),
            "score": attempt.score,
            "total_questions": attempt.max_score,
            "percentage": attempt.percentage,
        },
    )


@router.get("/quiz-history", response_model=ApiResponse)
async def get_user_quiz_history(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves recent quiz attempts strictly for the authenticated student.
    Guarantees complete multi-tenant user isolation.
    """
    history = await AnalyticsService.get_user_quiz_history(db, current_user.id, limit=limit)
    return ApiResponse(
        success=True,
        message=f"Retrieved {len(history)} quiz attempt(s).",
        data=history,
    )


@router.get("/student", response_model=ApiResponse)
async def get_student_telemetry(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns personalized learning metrics, questions asked, quiz scores,
    and weekly study activity strictly for the authenticated student.
    """
    data = await AnalyticsService.get_student_analytics(db, current_user.id)
    return ApiResponse(
        success=True,
        message="Student analytics retrieved successfully.",
        data=data,
    )


@router.get("/admin", response_model=ApiResponse)
async def get_admin_telemetry(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns platform-level telemetry for administrators.
    Guarantees student conversation privacy: private chat messages are omitted.
    """
    data = await AnalyticsService.get_admin_analytics(db, current_user)
    return ApiResponse(
        success=True,
        message="Platform telemetry retrieved successfully.",
        data=data,
    )


@router.delete("/prune", response_model=ApiResponse)
async def prune_old_events(
    days: int = Query(90, ge=7, le=365, description="Retention window in days"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Executes telemetry retention policy, deleting events older than the specified days.
    """
    pruned_count = await AnalyticsService.prune_expired_events(db, retention_days=days)
    return ApiResponse(
        success=True,
        message=f"Successfully pruned {pruned_count} analytics records older than {days} days.",
        data={"pruned_count": pruned_count, "retention_days": days},
    )

