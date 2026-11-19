# ==============================================================================
# EduNex AI — Production Backend Dockerfile
# Multi-stage security-hardened container for FastAPI + LangGraph + PyMuPDF
# ==============================================================================

FROM python:3.10-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered streaming logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

# Install system runtime dependencies (libpq for postgres, curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and pre-install lightweight CPU-only PyTorch wheel
# This prevents downloading ~2.5GB of unused CUDA binaries, dramatically accelerates builds,
# and avoids cross-platform binary wheel SHA256 hash mismatches from standard PyPI.
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir torch==2.2.2 --index-url https://download.pytorch.org/whl/cpu

# Install application requirements (sentence-transformers will detect pre-installed CPU torch)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create application user for security (never run as root in production)
RUN groupadd -g 1001 edunex && \
    useradd -u 1001 -g edunex -m -s /bin/bash edunex

# Copy application source code
COPY . .

# Create persistent storage directories and assign permissions to non-root user
RUN mkdir -p /app/data/uploads /app/data/uploads/images /app/data/chroma && \
    chmod +x /app/docker-entrypoint.sh && \
    chown -R edunex:edunex /app && \
    chmod -R 777 /app/data

USER edunex

EXPOSE 8000

# Container healthcheck querying FastAPI /api/v1/health (use 127.0.0.1 to avoid ipv6 resolution mismatch)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT:-8000}/api/v1/health || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
