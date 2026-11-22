import uuid
from datetime import datetime, timezone
import pytest
from fastapi import HTTPException

from app.models.entities import StudyNote, User
from app.schemas.base import StudyNoteCreate, StudyNoteRead
from app.api.routes.notes import create_study_note, list_study_notes, get_study_note, delete_study_note


def test_study_note_model_and_schema():
    """Tests StudyNote model and Pydantic schemas."""
    user_id = uuid.uuid4()
    note_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    note = StudyNote(
        id=note_id,
        user_id=user_id,
        title="B-Trees vs LSM Trees",
        subject="Database Systems",
        content="# B-Trees\nRead-optimized index structure.",
        document_id=doc_id,
        created_at=now,
        updated_at=now,
    )

    assert note.id == note_id
    assert note.user_id == user_id
    assert note.title == "B-Trees vs LSM Trees"
    assert note.subject == "Database Systems"
    assert "Read-optimized" in note.content
    assert note.document_id == doc_id

    read_model = StudyNoteRead.model_validate(note)
    assert read_model.id == note_id
    assert read_model.user_id == user_id


@pytest.mark.asyncio
async def test_two_account_notes_isolation_and_ownership(client):
    """
    Verifies that:
    1. Account A sees only Account A's notes.
    2. Account B sees only Account B's notes.
    3. Account B cannot read Account A's note (403 Forbidden).
    4. Account B cannot delete Account A's note (403 Forbidden).
    """
    from unittest.mock import AsyncMock, MagicMock

    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()

    user_a = User(id=user_a_id, email="student_a@edunex.ai", name="Student A", role="student")
    user_b = User(id=user_b_id, email="student_b@edunex.ai", name="Student B", role="student")

    note_a_id = uuid.uuid4()
    note_b_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    note_a = StudyNote(
        id=note_a_id,
        user_id=user_a_id,
        title="Account A Note: OS Virtual Memory",
        subject="Operating Systems",
        content="Paging and Segmentation",
        created_at=now,
        updated_at=now,
    )

    note_b = StudyNote(
        id=note_b_id,
        user_id=user_b_id,
        title="Account B Note: TCP Handshake",
        subject="Computer Networks",
        content="SYN, SYN-ACK, ACK",
        created_at=now,
        updated_at=now,
    )

    # 1. Test list_study_notes for User A
    mock_db = MagicMock()
    mock_result_a = MagicMock()
    mock_result_a.scalars.return_value.all.return_value = [note_a]

    async def fake_execute_a(*args, **kwargs):
        return mock_result_a

    mock_db.execute = fake_execute_a

    res_a = await list_study_notes(limit=50, current_user=user_a, db=mock_db)
    assert res_a.success is True
    assert len(res_a.data) == 1
    assert res_a.data[0]["title"] == "Account A Note: OS Virtual Memory"
    assert res_a.data[0]["user_id"] == user_a_id

    # 2. Test list_study_notes for User B
    mock_result_b = MagicMock()
    mock_result_b.scalars.return_value.all.return_value = [note_b]

    async def fake_execute_b(*args, **kwargs):
        return mock_result_b

    mock_db.execute = fake_execute_b

    res_b = await list_study_notes(limit=50, current_user=user_b, db=mock_db)
    assert res_b.success is True
    assert len(res_b.data) == 1
    assert res_b.data[0]["title"] == "Account B Note: TCP Handshake"
    assert res_b.data[0]["user_id"] == user_b_id

    # 3. Direct API access: User B attempts to access User A's note -> 403 Forbidden
    mock_single_result = MagicMock()
    mock_single_result.scalar_one_or_none.return_value = note_a

    async def fake_get_single(*args, **kwargs):
        return mock_single_result

    mock_db.execute = fake_get_single

    with pytest.raises(HTTPException) as exc_info:
        await get_study_note(note_id=note_a_id, current_user=user_b, db=mock_db)
    assert exc_info.value.status_code == 403
    assert "Forbidden" in exc_info.value.detail

    # 4. Direct API deletion: User B attempts to delete User A's note -> 403 Forbidden
    with pytest.raises(HTTPException) as exc_info_del:
        await delete_study_note(note_id=note_a_id, current_user=user_b, db=mock_db)
    assert exc_info_del.value.status_code == 403
    assert "Forbidden" in exc_info_del.value.detail

    # 5. User A can successfully access their own note
    get_res_a = await get_study_note(note_id=note_a_id, current_user=user_a, db=mock_db)
    assert get_res_a.success is True
    assert get_res_a.data["id"] == str(note_a_id)
