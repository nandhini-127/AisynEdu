from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.entities import User
from app.schemas.base import (
    ApiResponse,
    ChangePasswordRequest,
    Token,
    TokenRefreshRequest,
    UserCreate,
    UserLogin,
    UserRead,
    UserUpdate,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication & User Management"])


def get_client_ip(request: Request) -> str:
    """Extracts client IP address considering proxy headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post(
    "/register", response_model=ApiResponse, status_code=status.HTTP_201_CREATED
)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Registers a new student or user with strict password strength validation.
    """
    try:
        user = await AuthService.register_user(db, user_in)
        return ApiResponse(
            success=True,
            message="User account registered successfully",
            data=UserRead.model_validate(user),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=ApiResponse)
async def login(
    creds: UserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticates user with rate-limiting protection.
    Issues JWT access token and revocable refresh token.
    """
    client_ip = get_client_ip(request)
    try:
        token_data = await AuthService.authenticate_user(
            db, creds, client_ip=client_ip
        )

        # Set secure HTTP-only refresh cookie
        response.set_cookie(
            key="refresh_token",
            value=token_data.refresh_token,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
            httponly=settings.COOKIE_HTTPONLY,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            path="/api/v1/auth",
        )

        return ApiResponse(
            success=True,
            message="Authentication successful",
            data=token_data,
        )
    except ValueError as e:
        error_msg = str(e)
        if "Too many failed login attempts" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=error_msg
        )


@router.post("/refresh", response_model=ApiResponse)
async def refresh_token(
    request: Request,
    response: Response,
    body: TokenRefreshRequest = TokenRefreshRequest(),
    db: AsyncSession = Depends(get_db),
):
    """
    Refreshes access token using rotation pattern.
    Accepts refresh token from request body or HTTP-only cookie.
    """
    token_str = body.refresh_token or request.cookies.get("refresh_token")
    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token must be provided in request body or cookie",
        )

    try:
        new_token_data = await AuthService.refresh_tokens(db, token_str)

        # Rotate cookie
        response.set_cookie(
            key="refresh_token",
            value=new_token_data.refresh_token,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
            httponly=settings.COOKIE_HTTPONLY,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            path="/api/v1/auth",
        )

        return ApiResponse(
            success=True,
            message="Tokens refreshed successfully",
            data=new_token_data,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
        )


@router.post("/logout", response_model=ApiResponse)
async def logout(
    request: Request,
    response: Response,
    body: TokenRefreshRequest = TokenRefreshRequest(),
    db: AsyncSession = Depends(get_db),
):
    """
    Logs out the user, invalidating the refresh token and deleting the session cookie.
    """
    token_str = body.refresh_token or request.cookies.get("refresh_token")
    if token_str:
        await AuthService.revoke_refresh_token(db, token_str)

    # Delete cookie
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
        secure=settings.COOKIE_SECURE,
        httponly=settings.COOKIE_HTTPONLY,
        samesite=settings.COOKIE_SAMESITE,
    )

    return ApiResponse(
        success=True,
        message="Logged out successfully and token invalidated",
        data=None,
    )


@router.get("/me", response_model=ApiResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """
    Returns the authenticated user's private profile.
    """
    return ApiResponse(
        success=True,
        message="Profile retrieved",
        data=UserRead.model_validate(current_user),
    )


@router.patch("/me", response_model=ApiResponse)
async def update_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Updates profile settings, name, or learning preferences.
    """
    updated_user = await AuthService.update_profile(
        db, current_user, update_data
    )
    return ApiResponse(
        success=True,
        message="Profile updated successfully",
        data=UserRead.model_validate(updated_user),
    )


@router.post("/change-password", response_model=ApiResponse)
async def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Changes user password and invalidates all existing user refresh tokens.
    """
    try:
        await AuthService.change_password(db, current_user, req)
        return ApiResponse(
            success=True,
            message="Password changed successfully. All previous sessions have been terminated.",
            data=None,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
