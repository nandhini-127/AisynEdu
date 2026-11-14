from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import require_admin
from app.core.database import get_db
from app.models.entities import User
from app.schemas.base import AdminUserUpdate, ApiResponse, UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/admin", tags=["Administrator Management"])


@router.get("/users", response_model=ApiResponse)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    role: Optional[str] = Query(None),
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists platform users. Requires administrator privileges.
    """
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    stmt = stmt.offset(skip).limit(limit).order_by(User.created_at.desc())

    result = await db.execute(stmt)
    users = result.scalars().all()

    return ApiResponse(
        success=True,
        message="Users retrieved",
        data=[UserRead.model_validate(u) for u in users],
    )


@router.patch("/users/{user_id}", response_model=ApiResponse)
async def update_user_status(
    user_id: UUID,
    update_data: AdminUserUpdate,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Updates user activation status or role. Requires administrator privileges.
    """
    try:
        updated = await AuthService.admin_update_user(db, user_id, update_data)
        return ApiResponse(
            success=True,
            message="User status updated",
            data=UserRead.model_validate(updated),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

