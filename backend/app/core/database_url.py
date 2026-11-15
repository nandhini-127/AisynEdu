import os
import re
import urllib.parse
from typing import Optional
from sqlalchemy.engine.url import make_url, URL


def mask_database_url(url: Optional[str]) -> str:
    """
    Safely masks database credentials (username/password) for logging and error reporting.
    Guarantees secrets are never exposed in log files or console output.
    """
    if not url or not str(url).strip():
        return "<empty>"
    clean = str(url).strip().strip("'\"")
    try:
        parsed = make_url(clean)
        return parsed.render_as_string(hide_password=True)
    except Exception:
        # Fallback regex masking if URL cannot be parsed by SQLAlchemy make_url
        return re.sub(r"://([^:@]+):([^@]+)@", r"://\1:***@", clean)


def is_unresolved_template(val: Optional[str]) -> bool:
    """
    Checks if a string is an unresolved template variable from Railway, Docker, or shell.
    Examples: '${{Postgres.DATABASE_URL}}', '${{ Postgres.DATABASE_URL }}', '${DATABASE_URL}'.
    """
    if not val:
        return False
    v = str(val).strip().strip("'\"")
    if v.startswith("${{") and v.endswith("}}"):
        return True
    if v.startswith("${") and v.endswith("}"):
        return True
    if v.startswith("$") and not any(v.startswith(s) for s in ("sqlite", "postgres")):
        return True
    return False


def resolve_fallback_from_env() -> Optional[str]:
    """
    Attempts to discover alternative database connection variables or reconstruct
    the connection string from standard Railway/PostgreSQL environment variables.
    """
    # 1. Alternative direct connection strings provided by Railway
    candidates = [
        "DATABASE_PRIVATE_URL",
        "DATABASE_PUBLIC_URL",
        "POSTGRES_URL",
        "POSTGRES_PRIVATE_URL",
        "POSTGRES_PUBLIC_URL",
    ]
    for var in candidates:
        val = os.getenv(var)
        if val and not is_unresolved_template(val) and val.strip():
            return val.strip().strip("'\"")

    # 2. Reconstruct from individual PG* or POSTGRES_* environment variables (standard Railway PostgreSQL service)
    pghost = os.getenv("PGHOST") or os.getenv("POSTGRES_HOST")
    if pghost and not is_unresolved_template(pghost):
        pgport = os.getenv("PGPORT") or os.getenv("POSTGRES_PORT") or "5432"
        pguser = os.getenv("PGUSER") or os.getenv("POSTGRES_USER") or "postgres"
        pgpassword = os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD") or ""
        pgdatabase = os.getenv("PGDATABASE") or os.getenv("POSTGRES_DB") or "railway"

        user_enc = urllib.parse.quote(pguser, safe="")
        pass_enc = urllib.parse.quote(pgpassword, safe="")
        auth = f"{user_enc}:{pass_enc}@" if pguser else ""
        return f"postgresql://{auth}{pghost}:{pgport}/{pgdatabase}"

    return None


def normalize_database_url(
    url: Optional[str],
    is_async: bool = True,
    allow_fallback: bool = True,
) -> str:
    """
    Robustly normalizes a database URL for async (postgresql+asyncpg) or sync (postgresql).
    
    Guarantees:
    - Async engine receives a valid 'postgresql+asyncpg://' or 'sqlite+aiosqlite:///' URL.
    - Sync engine/Alembic receives a valid 'postgresql://' or 'sqlite:///' URL.
    - Strips surrounding quotes and whitespace.
    - Detects unresolved Railway templates (${{Postgres.DATABASE_URL}}) and attempts fallback.
    - Correctly handles and preserves URL-encoded credentials and raw special characters.
    - Never corrupts credentials or replaces strings blindly.
    """
    raw_val = str(url).strip() if url is not None else ""
    clean_url = raw_val.strip("'\"")

    if not clean_url:
        if allow_fallback:
            fallback = resolve_fallback_from_env()
            if fallback:
                return normalize_database_url(fallback, is_async=is_async, allow_fallback=False)
        raise ValueError("Database connection URL is empty or unconfigured.")

    if is_unresolved_template(clean_url):
        if allow_fallback:
            fallback = resolve_fallback_from_env()
            if fallback:
                return normalize_database_url(fallback, is_async=is_async, allow_fallback=False)
        raise ValueError(
            f"Unresolved database variable template: '{clean_url}'. "
            "Railway template variable was not expanded by the orchestrator. "
            "Ensure the PostgreSQL service is named correctly or configure DATABASE_URL directly."
        )

    # SQLite handling (used in unit tests and local testing)
    if clean_url.startswith("sqlite"):
        try:
            parsed = make_url(clean_url)
            target_driver = "sqlite+aiosqlite" if is_async else "sqlite"
            return parsed.set(drivername=target_driver).render_as_string(hide_password=False)
        except Exception as e:
            raise ValueError(f"Invalid SQLite database URL: {mask_database_url(clean_url)}. {e}")

    # PostgreSQL / Postgres URL sanitization:
    # Handle passwords or usernames with unencoded special characters (e.g. raw '@', ':', '#')
    if "://" in clean_url:
        scheme, rest = clean_url.split("://", 1)
        if "@" in rest:
            userinfo, hostpath = rest.rsplit("@", 1)
            if ":" in userinfo:
                user, pwd = userinfo.split(":", 1)
                clean_user = urllib.parse.quote(urllib.parse.unquote(user), safe="")
                clean_pwd = urllib.parse.quote(urllib.parse.unquote(pwd), safe="")
                userinfo = f"{clean_user}:{clean_pwd}"
            else:
                userinfo = urllib.parse.quote(urllib.parse.unquote(userinfo), safe="")
            clean_url = f"{scheme}://{userinfo}@{hostpath}"

    try:
        parsed = make_url(clean_url)
    except Exception as e:
        raise ValueError(
            f"Could not parse SQLAlchemy database URL from given string: {mask_database_url(clean_url)}. {e}"
        )

    # Validate that the scheme is a supported database protocol
    valid_schemes = {
        "postgres",
        "postgresql",
        "postgresql+asyncpg",
        "postgresql+psycopg2",
        "postgresql+psycopg",
        "sqlite",
        "sqlite+aiosqlite",
    }
    if parsed.drivername.lower() not in valid_schemes:
        raise ValueError(
            f"Unsupported database protocol '{parsed.drivername}' in URL: {mask_database_url(clean_url)}. "
            "Expected PostgreSQL (postgresql://, postgres://, postgresql+asyncpg://) or SQLite."
        )

    target_driver = "postgresql+asyncpg" if is_async else "postgresql"
    normalized = parsed.set(drivername=target_driver)
    return normalized.render_as_string(hide_password=False)


def normalize_async_database_url(url: Optional[str]) -> str:
    """Normalizes URL for asynchronous SQLAlchemy operations (asyncpg / aiosqlite)."""
    return normalize_database_url(url, is_async=True, allow_fallback=True)


def normalize_sync_database_url(url: Optional[str]) -> str:
    """Normalizes URL for synchronous operations and migrations (psycopg / sqlite)."""
    return normalize_database_url(url, is_async=False, allow_fallback=True)
