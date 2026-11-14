import asyncio
import os
import sys
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Default WindowsProactorEventLoopPolicy is used on Windows

# Set test environment flag before loading settings
os.environ["ENVIRONMENT"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key-for-unit-testing-32-chars-min"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["GOOGLE_API_KEY"] = "test-mock-key"
os.environ["GEMINI_API_KEY"] = "test-mock-key"

from app.core.config import settings
settings.ENVIRONMENT = "testing"
settings.GOOGLE_API_KEY = "test-mock-key"
settings.GEMINI_API_KEY = "test-mock-key"

import tempfile
from pathlib import Path
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy.pool import NullPool
from app.core.database import Base, get_db
from app.main import app

# Isolated file-based SQLite database in OS temp directory for unit/integration testing
TEST_DB_FILE = Path(tempfile.gettempdir()) / "edunex_test_runner.db"
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE.as_posix()}"
SYNC_DATABASE_URL = f"sqlite:///{TEST_DB_FILE.as_posix()}"

sync_engine = create_sync_engine(
    SYNC_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
    poolclass=NullPool,
)
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
    poolclass=NullPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides a transactional database session per test with tables created."""
    Base.metadata.create_all(bind=sync_engine)

    async with TestingSessionLocal() as session:
        yield session

    Base.metadata.drop_all(bind=sync_engine)


@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provides a test HTTP client with overridden database dependency."""
    Base.metadata.create_all(bind=sync_engine)

    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=sync_engine)

