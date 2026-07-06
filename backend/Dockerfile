# ═══════════════════════════════════════════════════════════════════
#  Multi-target Dockerfile — Start-up Evolution Engine Backend
#  Targets: api-gateway | worker-engine
# ═══════════════════════════════════════════════════════════════════

# ── Shared Builder Stage ──────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── Shared Base Runtime ───────────────────────────────────────────
FROM python:3.13-slim AS runtime-base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local

# Copy backend source into /app/backend so that
# `from backend.app.main import app` resolves correctly with PYTHONPATH=/app
COPY . /app/backend

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app

# ── Target: API Gateway ──────────────────────────────────────────
FROM runtime-base AS api-gateway

ENV SERVICE_ROLE=api-gateway

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--loop", "uvloop", \
     "--http", "httptools", \
     "--limit-concurrency", "500", \
     "--timeout-keep-alive", "30", \
     "--access-log", \
     "--no-server-header"]

# ── Target: Worker Engine ────────────────────────────────────────
FROM runtime-base AS worker-engine

ENV SERVICE_ROLE=worker-engine

CMD ["python", "-m", "backend.worker.main"]
