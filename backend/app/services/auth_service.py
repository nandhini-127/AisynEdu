import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import UUID
from zoneinfo import ZoneInfo
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.rate_limiter import login_rate_limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    validate_password_strength,
    verify_password,
)
from app.models.entities import RefreshToken, User
from app.schemas.base import (
    AdminUserUpdate,
    ChangePasswordRequest,
    Token,
    UserCreate,
    UserLogin,
    UserRead,
    UserUpdate,
)


class AuthService:
    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        normalized_email = email.strip().lower()
        result = await db.execute(select(User).where(User.email == normalized_email))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def register_user(db: AsyncSession, user_in: UserCreate) -> User:
        normalized_email = user_in.email.strip().lower()
        existing = await AuthService.get_user_by_email(db, normalized_email)
        if existing:
            raise ValueError("Email is already registered")

        # Validate password rules
        validate_password_strength(user_in.password)

        new_user = User(
            email=normalized_email,
            name=user_in.name.strip(),
            hashed_password=get_password_hash(user_in.password),
            role=user_in.role,
            preferred_llm=user_in.preferred_llm,
            is_active=True,
            current_streak=0,
            longest_streak=0,
            last_login_date=None,
            settings={},
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user

    @staticmethod
    def update_login_streak(user: User, target_date: Optional[date] = None) -> bool:
        """
        Calculates and updates user's daily login streak based on calendar days in configured timezone.
        Uses date-based comparison in Asia/Kolkata timezone.
        
        Rules:
        1. First login -> current_streak = 1, longest_streak = 1, last_login_date = today.
        2. Multiple logins on same calendar day -> streak unchanged, returns False.
        3. Login on consecutive calendar day -> current_streak += 1, returns True.
        4. Missed >= 1 calendar days -> current_streak = 1, returns True.
        5. Track longest_streak separately: max(longest_streak, current_streak).
        """
        if target_date is None:
            try:
                tz = ZoneInfo(settings.TIMEZONE)
            except Exception:
                tz = timezone(timedelta(hours=5, minutes=30))
            today = datetime.now(tz).date()
        else:
            today = target_date

        last_date = user.last_login_date

        # Rule 2 & 5: Multiple logins on same calendar day count as only ONE streak day
        if last_date == today:
            return False

        # Rule 3: Consecutive calendar day login
        if last_date == today - timedelta(days=1):
            user.current_streak = (user.current_streak or 0) + 1
            streak_increased = True
        else:
            # Rule 1 & 4: First login ever or missed 1+ calendar days
            user.current_streak = 1
            streak_increased = True

        # Rule 6: Track longest streak separately
        if user.current_streak > (user.longest_streak or 0):
            user.longest_streak = user.current_streak

        user.last_login_date = today
        return streak_increased

    @staticmethod
    async def authenticate_user(
        db: AsyncSession, creds: UserLogin, client_ip: str = "unknown"
    ) -> Token:
        rate_limit_key = f"{client_ip}:{creds.email.lower()}"
        is_limited, retry_after = login_rate_limiter.is_rate_limited(rate_limit_key)
        if is_limited:
            raise ValueError(
                f"Too many failed login attempts. Please try again in {retry_after} seconds."
            )

        # Use row-level locking (with_for_update) to prevent race conditions on concurrent logins
        result = await db.execute(
            select(User).where(User.email == creds.email.strip().lower()).with_for_update()
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(creds.password, user.hashed_password):
            login_rate_limiter.record_failure(rate_limit_key)
            raise ValueError("Invalid email or password")

        if not user.is_active:
            raise ValueError("Account is deactivated")

        # Reset rate limit tracker on successful authentication
        login_rate_limiter.reset(rate_limit_key)

        # Update login streak based on actual calendar days in Asia/Kolkata
        streak_increased = AuthService.update_login_streak(user)

        # Update last login timestamp
        user.last_login = datetime.now(timezone.utc)

        # Issue access & refresh tokens
        access_token = create_access_token(subject=user.id, role=user.role)
        refresh_token_str = create_refresh_token(subject=user.id)
        refresh_payload = decode_token(refresh_token_str)
        jti = refresh_payload.get("jti")
        exp_ts = refresh_payload.get("exp")
        expire_at = datetime.fromtimestamp(exp_ts, tz=timezone.utc) if exp_ts else datetime.now(timezone.utc)

        # Persist refresh token for tracking and revocation
        db_refresh = RefreshToken(
            user_id=user.id,
            token_jti=jti,
            expires_at=expire_at,
            is_revoked=False,
        )
        db.add(db_refresh)
        await db.commit()
        await db.refresh(user)

        return Token(
            access_token=access_token,
            refresh_token=refresh_token_str,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserRead.model_validate(user),
            streak_increased=streak_increased,
        )

    @staticmethod
    async def refresh_tokens(db: AsyncSession, refresh_token_str: str) -> Token:
        payload = decode_token(refresh_token_str)
        user_id_str = payload.get("sub")
        jti = payload.get("jti")
        token_type = payload.get("type")

        if not user_id_str or not jti or token_type != "refresh":
            raise ValueError("Invalid or malformed refresh token")

        try:
            user_uuid = UUID(user_id_str)
        except ValueError:
            raise ValueError("Malformed token identifier")

        # Find active refresh token in database
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_jti == jti,
                RefreshToken.user_id == user_uuid,
            )
        )
        token_record = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if not token_record or token_record.is_revoked:
            raise ValueError("Refresh token has been revoked or is invalid")

        # Normalize timezone awareness for cross-database engine compatibility (Postgres / SQLite)
        expires_at = token_record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < now:
            token_record.is_revoked = True
            await db.commit()
            raise ValueError("Refresh token has expired. Please login again.")

        # Invalidate old refresh token (Token Rotation security pattern)
        token_record.is_revoked = True

        # Fetch active user
        user = await AuthService.get_user_by_id(db, user_uuid)
        if not user or not user.is_active:
            await db.commit()
            raise ValueError("User account is inactive or not found")

        # Issue rotated tokens
        new_access_token = create_access_token(subject=user.id, role=user.role)
        new_refresh_token_str = create_refresh_token(subject=user.id)
        new_payload = decode_token(new_refresh_token_str)
        new_jti = new_payload.get("jti")
        new_exp_ts = new_payload.get("exp")
        new_expire = datetime.fromtimestamp(new_exp_ts, tz=timezone.utc) if new_exp_ts else datetime.now(timezone.utc)

        new_token_record = RefreshToken(
            user_id=user.id,
            token_jti=new_jti,
            expires_at=new_expire,
            is_revoked=False,
        )
        db.add(new_token_record)
        await db.commit()

        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token_str,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserRead.model_validate(user),
        )

    @staticmethod
    async def revoke_refresh_token(db: AsyncSession, refresh_token_str: str) -> bool:
        """Revokes a refresh token during user logout."""
        payload = decode_token(refresh_token_str)
        jti = payload.get("jti")
        if not jti:
            return False

        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token_jti == jti)
        )
        token_record = result.scalar_one_or_none()
        if token_record:
            token_record.is_revoked = True
            await db.commit()
            return True
        return False

    @staticmethod
    async def revoke_all_user_tokens(db: AsyncSession, user_id: UUID) -> None:
        """Revokes all active refresh tokens for a user (e.g., on password change)."""
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked == False)
            .values(is_revoked=True)
        )
        await db.commit()

    @staticmethod
    async def update_profile(
        db: AsyncSession, user: User, update_data: UserUpdate
    ) -> User:
        if update_data.name is not None:
            user.name = update_data.name.strip()
        if update_data.preferred_llm is not None:
            user.preferred_llm = update_data.preferred_llm
        if update_data.settings is not None:
            merged_settings = dict(user.settings or {})
            merged_settings.update(update_data.settings)
            user.settings = merged_settings

        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def change_password(
        db: AsyncSession, user: User, req: ChangePasswordRequest
    ) -> None:
        if not verify_password(req.current_password, user.hashed_password):
            raise ValueError("Current password is incorrect")

        validate_password_strength(req.new_password)

        if req.current_password == req.new_password:
            raise ValueError("New password must be different from current password")

        user.hashed_password = get_password_hash(req.new_password)
        # Revoke all existing sessions/refresh tokens for security
        await AuthService.revoke_all_user_tokens(db, user.id)
        await db.commit()
        await db.refresh(user)

    @staticmethod
    async def admin_update_user(
        db: AsyncSession, target_user_id: UUID, update_data: AdminUserUpdate
    ) -> User:
        user = await AuthService.get_user_by_id(db, target_user_id)
        if not user:
            raise ValueError("Target user not found")

        if update_data.is_active is not None:
            user.is_active = update_data.is_active
        if update_data.role is not None:
            user.role = update_data.role

        await db.commit()
        await db.refresh(user)
        return user
