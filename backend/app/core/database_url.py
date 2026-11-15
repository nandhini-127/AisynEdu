import os
import re
import urllib.parse
from typing import Any, Dict, Optional
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
    Also catches placeholders like 'none', 'null', 'undefined', or empty values.
    """
    if not val:
        return False
    v = str(val).strip().strip("'\"")
    if not v:
        return False
    if v.startswith("${{") and v.endswith("}}"):
        return True
    if v.startswith("${") and v.endswith("}"):
        return True
    if "{{" in v and "}}" in v:
        return True
    if v.lower() in ("none", "null", "undefined", "<empty>"):
        return True
    if v.startswith("$") and not any(v.startswith(s) for s in ("sqlite", "postgres")):
        return True
    return False


def get_safe_database_diagnostics(url: Optional[str]) -> Dict[str, Any]:
    """
    Extracts safe diagnostic metrics from a database URL string without exposing
    any sensitive information (no usernames, passwords, tokens, or full URLs).
    Returns only structural metrics:
    - is_configured: bool
    - is_template: bool
    - scheme: str
    - host_present: bool
    - port_present: bool
    - database_present: bool
    - is_valid: bool
    """
    if url is None or not str(url).strip():
        return {
            "is_configured": False,
            "is_template": False,
            "scheme": "<empty>",
            "host_present": False,
            "port_present": False,
            "database_present": False,
            "is_valid": False,
        }

    clean = str(url).strip()
    while (clean.startswith('"') and clean.endswith('"')) or (clean.startswith("'") and clean.endswith("'")):
        clean = clean[1:-1].strip()

    is_tmpl = is_unresolved_template(clean)
    scheme = "<none>"
    host_present = False
    port_present = False
    database_present = False
    is_valid = False

    try:
        parsed = make_url(clean)
        scheme = parsed.drivername or "<none>"
        host_present = bool(parsed.host)
        port_present = bool(parsed.port)
        database_present = bool(parsed.database)
        is_valid = bool(parsed.drivername and (parsed.host or parsed.database))
    except Exception:
        # Fallback inspection if make_url fails
        if "://" in clean:
            scheme = clean.split("://", 1)[0].lower()
            rest = clean.split("://", 1)[1]
            if "@" in rest:
                hostpart = rest.rsplit("@", 1)[1]
                host_present = bool(hostpart.split("/")[0])
                database_present = "/" in hostpart and bool(hostpart.split("/")[1].split("?")[0])

    return {
        "is_configured": bool(clean),
        "is_template": is_tmpl,
        "scheme": scheme,
        "host_present": host_present,
        "port_present": port_present,
        "database_present": database_present,
        "is_valid": is_valid,
    }


def log_safe_database_diagnostics(url: Optional[str], label: str = "DATABASE_URL") -> None:
    """
    Logs safe diagnostic information about a database URL without exposing credentials.
    """
    import logging
    diag_logger = logging.getLogger("edunex.core.database")
    diag = get_safe_database_diagnostics(url)
    diag_logger.info(
        "[DB-DIAGNOSTIC] %s: configured=%s, scheme='%s', host_present=%s, "
        "port_present=%s, db_present=%s, is_railway_template=%s, is_valid_sqlalchemy_url=%s",
        label,
        diag["is_configured"],
        diag["scheme"],
        diag["host_present"],
        diag["port_present"],
        diag["database_present"],
        diag["is_template"],
        diag["is_valid"],
    )


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
        "POSTGRES_DATABASE_URL",
        "POSTGRESQL_URL",
    ]
    for var in candidates:
        val = os.getenv(var)
        if val and not is_unresolved_template(val) and val.strip():
            clean_val = val.strip().strip("'\"")
            if any(clean_val.startswith(p) for p in ("postgres://", "postgresql://", "postgresql+asyncpg://")):
                return clean_val

    # 2. Reconstruct from individual PG* or POSTGRES_* environment variables (standard Railway PostgreSQL service)
    pghost = os.getenv("PGHOST") or os.getenv("POSTGRES_HOST") or os.getenv("POSTGRESQL_HOST") or os.getenv("DB_HOST")
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
    clean_url = raw_val
    while (clean_url.startswith('"') and clean_url.endswith('"')) or (clean_url.startswith("'") and clean_url.endswith("'")):
        clean_url = clean_url[1:-1].strip()

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
