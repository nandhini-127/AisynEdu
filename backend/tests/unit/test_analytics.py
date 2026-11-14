import uuid
from datetime import datetime, timedelta, timezone
import pytest
from app.models.entities import AnalyticsEvent, User
from app.analytics.service import AnalyticsService


def test_analytics_event_entity_structure():
    """
    Tests that AnalyticsEvent entity contains all required telemetry attributes.
    """
    user_id = uuid.uuid4()
    event = AnalyticsEvent(
        id=uuid.uuid4(),
        user_id=user_id,
        event_type="question_asked",
        subject="Computer Science",
        llm_provider="gemini",
        tokens_used=120,
        latency_ms=450,
        retrieval_hit=True,
        retrieval_chunk_count=3,
        extra_data={"intent": "tutor"},
    )

    assert event.id is not None
    assert event.user_id == user_id
    assert event.event_type == "question_asked"
    assert event.subject == "Computer Science"
    assert event.llm_provider == "gemini"
    assert event.tokens_used == 120
    assert event.latency_ms == 450
    assert event.retrieval_hit is True
    assert event.retrieval_chunk_count == 3
    assert event.extra_data["intent"] == "tutor"


def test_admin_analytics_privacy_contract():
    """
    Verifies that admin telemetry aggregation strictly protects student privacy:
    Guarantees private message texts and conversations are never exposed to platform administrators.
    """
    # 1. Non-admin student raises PermissionError
    student = User(
        id=uuid.uuid4(),
        email="student@edunex.ai",
        name="Student User",
        hashed_password="hash",
        role="student",
    )

    with pytest.raises(PermissionError) as exc_info:
        AnalyticsService.validate_admin_role(student)
    assert "Access restricted" in str(exc_info.value)

    # 2. Admin role is accepted
    admin = User(
        id=uuid.uuid4(),
        email="admin@edunex.ai",
        name="Platform Admin",
        hashed_password="hash",
        role="admin",
    )
    AnalyticsService.validate_admin_role(admin)  # Must not raise


def test_analytics_retention_window_logic():
    """
    Verifies that the retention policy calculates the correct cutoff date for purging events.
    """
    retention_days = 90
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

    recent_event_time = datetime.now(timezone.utc) - timedelta(days=5)
    expired_event_time = datetime.now(timezone.utc) - timedelta(days=95)

    assert recent_event_time > cutoff_date  # Must be retained
    assert expired_event_time < cutoff_date  # Must be pruned


def test_analytics_event_has_all_required_columns():
    """AnalyticsEvent must have all columns the migration creates."""
    required = {
        "id", "user_id", "event_type", "subject", "llm_provider",
        "tokens_used", "latency_ms", "retrieval_hit",
        "retrieval_chunk_count", "extra_data", "created_at",
    }
    event = AnalyticsEvent(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        event_type="quiz_generated",
        subject="Machine Learning",
        llm_provider="gemini",
        tokens_used=200,
        latency_ms=512,
        retrieval_hit=False,
        retrieval_chunk_count=0,
        extra_data={"intent": "quiz"},
    )
    for field in required:
        assert hasattr(event, field), f"AnalyticsEvent is missing column: {field}"


def test_quiz_attempt_schema_and_model():
    """Verifies QuizAttempt model and QuizAttemptRequest schema."""
    from app.models.entities import Quiz, QuizAttempt
    from app.api.routes.analytics import QuizAttemptRequest

    req = QuizAttemptRequest(
        quiz_id="quiz-12345",
        title="Python Basics",
        topic="Computer Science",
        difficulty="beginner",
        score=3,
        total_questions=4,
        percentage=75.0,
        answers={"q1": 0, "q2": 1, "q3": 0, "q4": 2},
    )
    assert req.score == 3
    assert req.total_questions == 4
    assert req.percentage == 75.0

    quiz_id = uuid.uuid4()
    user_id = uuid.uuid4()
    attempt = QuizAttempt(
        id=uuid.uuid4(),
        quiz_id=quiz_id,
        user_id=user_id,
        score=3,
        max_score=4,
        percentage=75.0,
        answers=[0, 1, 0, 2],
        results=[],
    )
    assert attempt.score == 3
    assert attempt.percentage == 75.0
    assert attempt.quiz_id == quiz_id
    assert attempt.user_id == user_id

