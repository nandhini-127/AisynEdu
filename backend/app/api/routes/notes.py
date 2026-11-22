import logging
import uuid
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.entities import StudyNote, User
from app.schemas.base import ApiResponse, StudyNoteCreate, StudyNoteRead

logger = logging.getLogger("edunex.api.notes")

router = APIRouter(prefix="/notes", tags=["Study Notes"])


@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_study_note(
    payload: StudyNoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a new revision study note associated strictly with the authenticated student's unique ID.
    """
    note = StudyNote(
        id=uuid.uuid4(),
        user_id=current_user.id,
        title=payload.title.strip(),
        subject=payload.subject.strip() if payload.subject else "General Studies",
        content=payload.content,
        document_id=payload.document_id,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)

    logger.info("Study note created [id=%s user_id=%s title=%s]", note.id, current_user.id, note.title)
    return ApiResponse(
        success=True,
        message="Study note created successfully.",
        data=StudyNoteRead.model_validate(note).model_dump(),
    )


@router.get("", response_model=ApiResponse)
async def list_study_notes(
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves study notes history strictly belonging to the authenticated student.
    Enforces user ownership filtering at the database query level.
    """
    query = (
        select(StudyNote)
        .where(StudyNote.user_id == current_user.id)
        .order_by(desc(StudyNote.created_at))
        .limit(limit)
    )
    notes = (await db.execute(query)).scalars().all()
    data = [StudyNoteRead.model_validate(n).model_dump() for n in notes]

    return ApiResponse(
        success=True,
        message=f"Retrieved {len(data)} study note(s).",
        data=data,
    )


@router.get("/{note_id}", response_model=ApiResponse)
async def get_study_note(
    note_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves a single study note. Verifies student ownership before returning.
    Denies direct API access to other students' study notes with 403 Forbidden.
    """
    note = (await db.execute(select(StudyNote).where(StudyNote.id == note_id))).scalar_one_or_none()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study note not found.",
        )

    if note.user_id != current_user.id:
        logger.warning(
            "Unauthorized access attempt to study note %s by user %s (owner: %s)",
            note_id, current_user.id, note.user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to access this study note.",
        )

    return ApiResponse(
        success=True,
        data=StudyNoteRead.model_validate(note).model_dump(),
    )


@router.delete("/{note_id}", response_model=ApiResponse)
async def delete_study_note(
    note_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Deletes a single study note. Verifies student ownership before deleting.
    Denies direct deletion of other students' study notes with 403 Forbidden.
    """
    note = (await db.execute(select(StudyNote).where(StudyNote.id == note_id))).scalar_one_or_none()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study note not found.",
        )

    if note.user_id != current_user.id:
        logger.warning(
            "Unauthorized delete attempt on study note %s by user %s (owner: %s)",
            note_id, current_user.id, note.user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to delete this study note.",
        )

    await db.delete(note)
    await db.commit()

    logger.info("Study note deleted [id=%s user_id=%s]", note_id, current_user.id)
    return ApiResponse(
        success=True,
        message="Study note deleted successfully.",
        data={"id": str(note_id)},
    )

