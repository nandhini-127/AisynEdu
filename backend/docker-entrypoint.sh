#!/bin/sh
set -e

echo "========================================================"
echo "          Starting AisynEdu Backend Container          "
echo "========================================================"

# Check and execute Alembic database migrations if DATABASE_URL is set
if [ -n "$DATABASE_URL" ]; then
    echo "Applying database migrations via Alembic..."
    if ! alembic upgrade head; then
        echo "ERROR: Database migration failed. Aborting container startup to protect data integrity." >&2
        exit 1
    fi
    echo "Database migrations applied successfully."
else
    echo "DATABASE_URL not set; skipping automated Alembic migrations."
fi

# Ensure required persistent storage directories exist without failing on volume mount permissions
mkdir -p /app/data/uploads /app/data/uploads/images /app/data/chroma 2>/dev/null || true

echo "Launching AisynEdu FastAPI service..."
exec "$@"

