import os
import pytest
from app.core.database_url import (
    normalize_database_url,
    normalize_async_database_url,
    normalize_sync_database_url,
    mask_database_url,
    is_unresolved_template,
)


def test_postgres_scheme_normalization():
    """Verify postgres:// is converted to postgresql+asyncpg for async and postgresql for sync."""
    raw = "postgres://user:secret@localhost:5432/edunex_db"

    async_url = normalize_async_database_url(raw)
    assert async_url == "postgresql+asyncpg://user:secret@localhost:5432/edunex_db"

    sync_url = normalize_sync_database_url(raw)
    assert sync_url == "postgresql://user:secret@localhost:5432/edunex_db"


def test_postgresql_scheme_normalization():
    """Verify postgresql:// is converted to postgresql+asyncpg for async and postgresql for sync."""
    raw = "postgresql://user:secret@localhost:5432/edunex_db"

    async_url = normalize_async_database_url(raw)
    assert async_url == "postgresql+asyncpg://user:secret@localhost:5432/edunex_db"

    sync_url = normalize_sync_database_url(raw)
    assert sync_url == "postgresql://user:secret@localhost:5432/edunex_db"


def test_postgresql_asyncpg_preservation():
    """Verify postgresql+asyncpg:// is preserved for async and normalized to postgresql for sync."""
    raw = "postgresql+asyncpg://user:secret@localhost:5432/edunex_db"

    async_url = normalize_async_database_url(raw)
    assert async_url == "postgresql+asyncpg://user:secret@localhost:5432/edunex_db"

    sync_url = normalize_sync_database_url(raw)
    assert sync_url == "postgresql://user:secret@localhost:5432/edunex_db"


def test_quoted_url_handling():
    """Verify double and single quoted URLs from environment variables are properly stripped."""
    double_quoted = '"postgresql://user:secret@localhost:5432/edunex_db"'
    single_quoted = "'postgres://user:secret@localhost:5432/edunex_db'"

    assert normalize_async_database_url(double_quoted) == "postgresql+asyncpg://user:secret@localhost:5432/edunex_db"
    assert normalize_async_database_url(single_quoted) == "postgresql+asyncpg://user:secret@localhost:5432/edunex_db"


def test_special_characters_in_password():
    """Verify passwords with special characters (both pre-encoded and unencoded) are handled cleanly."""
    # Pre-encoded password: p%40ss%23123 (p@ss#123)
    encoded_url = "postgres://admin:p%40ss%23123@db.railway.internal:5432/production"
    async_res = normalize_async_database_url(encoded_url)
    assert async_res == "postgresql+asyncpg://admin:p%40ss%23123@db.railway.internal:5432/production"

    # Raw unencoded password with @ and #
    raw_url = "postgres://admin:p@ss#123@db.railway.internal:5432/production"
    async_res2 = normalize_async_database_url(raw_url)
    assert "postgresql+asyncpg://admin:p%40ss%23123@db.railway.internal:5432/production" == async_res2


def test_query_parameters_preserved():
    """Verify query parameters like ?sslmode=require are preserved."""
    url_with_query = "postgres://user:pass@ep-cool.railway.internal:5432/db?sslmode=require"
    async_url = normalize_async_database_url(url_with_query)
    assert async_url == "postgresql+asyncpg://user:pass@ep-cool.railway.internal:5432/db?sslmode=require"

    sync_url = normalize_sync_database_url(url_with_query)
    assert sync_url == "postgresql://user:pass@ep-cool.railway.internal:5432/db?sslmode=require"


def test_sqlite_url_handling():
    """Verify sqlite URLs for local development and unit tests."""
    sqlite_raw = "sqlite:///./test.db"
    assert normalize_async_database_url(sqlite_raw) == "sqlite+aiosqlite:///./test.db"
    assert normalize_sync_database_url(sqlite_raw) == "sqlite:///./test.db"

    sqlite_async = "sqlite+aiosqlite:///./test.db"
    assert normalize_async_database_url(sqlite_async) == "sqlite+aiosqlite:///./test.db"
    assert normalize_sync_database_url(sqlite_async) == "sqlite:///./test.db"


def test_unresolved_railway_template_without_fallback():
    """Verify unresolved Railway templates ${{Postgres.DATABASE_URL}} raise clear ValueError."""
    templates = [
        "${{Postgres.DATABASE_URL}}",
        "${{ Postgres.DATABASE_URL }}",
        "${{DATABASE_URL}}",
        "${DATABASE_URL}",
    ]
    for tmpl in templates:
        assert is_unresolved_template(tmpl) is True
        with pytest.raises(ValueError) as excinfo:
            normalize_database_url(tmpl, allow_fallback=False)
        assert "Unresolved database variable template" in str(excinfo.value)


def test_unresolved_railway_template_fallback_to_pghost(monkeypatch):
    """Verify fallback to standard Railway PG* env vars when template is unresolved."""
    monkeypatch.setenv("PGHOST", "postgres.railway.internal")
    monkeypatch.setenv("PGPORT", "5432")
    monkeypatch.setenv("PGUSER", "postgres")
    monkeypatch.setenv("PGPASSWORD", "railway_secret_pwd")
    monkeypatch.setenv("PGDATABASE", "railway")

    res = normalize_async_database_url("${{Postgres.DATABASE_URL}}")
    assert res == "postgresql+asyncpg://postgres:railway_secret_pwd@postgres.railway.internal:5432/railway"


def test_empty_database_url_handling(monkeypatch):
    """Verify empty or whitespace-only database URLs raise ValueError when no fallback exists."""
    # Ensure no fallback variables exist
    for var in ["PGHOST", "POSTGRES_HOST", "DATABASE_PRIVATE_URL", "DATABASE_PUBLIC_URL", "POSTGRES_URL"]:
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(ValueError) as exc:
        normalize_database_url("", allow_fallback=False)
    assert "empty or unconfigured" in str(exc.value)

    with pytest.raises(ValueError) as exc2:
        normalize_database_url("   ", allow_fallback=False)
    assert "empty or unconfigured" in str(exc2.value)


def test_invalid_url_handling():
    """Verify completely invalid URLs raise ValueError with masked output."""
    with pytest.raises(ValueError) as exc:
        normalize_database_url("http://invalid_db_protocol:5432/db", allow_fallback=False)
    assert "Unsupported database protocol" in str(exc.value)

    with pytest.raises(ValueError) as exc2:
        normalize_database_url("not_a_valid_url_at_all", allow_fallback=False)
    assert "Could not parse" in str(exc2.value) or "Unsupported" in str(exc2.value)


def test_mask_database_url():
    """Verify credentials are never exposed in masked output."""
    url = "postgresql+asyncpg://super_user:very_secret_password_123@db.example.com:5432/mydb"
    masked = mask_database_url(url)
    assert "very_secret_password_123" not in masked
    assert "super_user:***@db.example.com" in masked

    assert mask_database_url("") == "<empty>"
    assert mask_database_url(None) == "<empty>"


def test_local_docker_configuration():
    """Verify standard local Docker compose configuration parses without issue."""
    local_url = "postgresql+asyncpg://postgres:postgres@postgres:5432/edunex_db"
    assert normalize_async_database_url(local_url) == local_url
    assert normalize_sync_database_url(local_url) == "postgresql://postgres:postgres@postgres:5432/edunex_db"


def test_railway_production_configuration():
    """Verify Railway production configuration parses and normalizes scheme."""
    railway_url = "postgres://postgres:AbCdEf123456@postgres.railway.internal:5432/railway"
    expected = "postgresql+asyncpg://postgres:AbCdEf123456@postgres.railway.internal:5432/railway"
    assert normalize_async_database_url(railway_url) == expected


def test_safe_database_diagnostics():
    """Verify safe diagnostics report structure without leaking secrets."""
    from app.core.database_url import get_safe_database_diagnostics

    secret_url = "postgresql+asyncpg://secret_user:super_secret_password_999@postgres.railway.internal:5432/railway_prod"
    diag = get_safe_database_diagnostics(secret_url)

    assert diag["is_configured"] is True
    assert diag["scheme"] == "postgresql+asyncpg"
    assert diag["host_present"] is True
    assert diag["port_present"] is True
    assert diag["database_present"] is True
    assert diag["is_valid"] is True
    assert diag["is_template"] is False

    # String representation must never contain password
    diag_str = str(diag)
    assert "super_secret_password_999" not in diag_str
    assert "secret_user" not in diag_str

    # Test template diagnostic
    tmpl_diag = get_safe_database_diagnostics("${{Postgres.DATABASE_URL}}")
    assert tmpl_diag["is_template"] is True


def test_production_settings_loading_with_unresolved_railway_template(monkeypatch):
    """
    REGRESSION TEST:
    Reproduces exact Railway production path where DATABASE_URL=${{Postgres.DATABASE_URL}}
    and Railway provides standard PG* fallback variables.
    """
    from app.core.config import Settings
    from sqlalchemy.ext.asyncio import create_async_engine

    monkeypatch.setenv("DATABASE_URL", "${{Postgres.DATABASE_URL}}")
    monkeypatch.setenv("SYNC_DATABASE_URL", "${{Postgres.DATABASE_URL}}")
    monkeypatch.setenv("PGHOST", "postgres.railway.internal")
    monkeypatch.setenv("PGPORT", "5432")
    monkeypatch.setenv("PGUSER", "postgres")
    monkeypatch.setenv("PGPASSWORD", "railway_secret_pwd")
    monkeypatch.setenv("PGDATABASE", "railway")

    # Load Pydantic Settings
    test_settings = Settings()
    expected_async = "postgresql+asyncpg://postgres:railway_secret_pwd@postgres.railway.internal:5432/railway"
    expected_sync = "postgresql://postgres:railway_secret_pwd@postgres.railway.internal:5432/railway"

    assert test_settings.DATABASE_URL == expected_async
    assert test_settings.SYNC_DATABASE_URL == expected_sync

    # Test create_async_engine succeeds without ArgumentError
    engine = create_async_engine(test_settings.DATABASE_URL)
    assert engine.url.drivername == "postgresql+asyncpg"
    assert engine.url.host == "postgres.railway.internal"
    assert engine.url.database == "railway"


def test_production_settings_loading_with_quoted_railway_url(monkeypatch):
    """
    REGRESSION TEST:
    Reproduces Railway production path where DATABASE_URL is wrapped in quotes.
    """
    from app.core.config import Settings
    from sqlalchemy.ext.asyncio import create_async_engine

    monkeypatch.setenv("DATABASE_URL", '"postgres://postgres:pwd123@postgres.railway.internal:5432/railway"')
    test_settings = Settings()
    expected = "postgresql+asyncpg://postgres:pwd123@postgres.railway.internal:5432/railway"
    assert test_settings.DATABASE_URL == expected

    engine = create_async_engine(test_settings.DATABASE_URL)
    assert engine.url.drivername == "postgresql+asyncpg"
    assert engine.url.host == "postgres.railway.internal"
