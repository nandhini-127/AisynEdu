from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings
from app.core.database_url import (
    normalize_async_database_url,
    log_safe_database_diagnostics,
    mask_database_url,
)
from app.core.logging import logger

# Base model for all SQLAlchemy declarative entities
class Base(DeclarativeBase):
    pass

# Ensure the database URL is fully normalized for async operations
try:
    async_db_url = normalize_async_database_url(settings.DATABASE_URL)
    log_safe_database_diagnostics(async_db_url, label="app.core.database:create_async_engine")
except Exception as norm_err:
    logger.error("Failed to normalize async database URL: %s", str(norm_err))
    raise RuntimeError(
        f"Database URL configuration error: {str(norm_err)}"
    ) from norm_err

# Engine configuration adapted for PostgreSQL in production and SQLite in testing/local
engine_kwargs = {
    "echo": False,
    "future": True,
}
if "sqlite" in async_db_url:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

# Async engine for production PostgreSQL operations
try:
    logger.info("Initializing async database engine with target: %s", mask_database_url(async_db_url))
    engine = create_async_engine(
        async_db_url,
        **engine_kwargs,
    )
except Exception as e:
    logger.error("Failed to initialize database engine for %s: %s", mask_database_url(async_db_url), str(e))
    raise RuntimeError(
        f"Database engine initialization failed for {mask_database_url(async_db_url)}. "
        f"Original error: {str(e)}"
    ) from e

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing database sessions per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session rollback triggered by error: {str(e)}")
            raise
        finally:
            await session.close()

