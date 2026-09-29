#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
#  Entrypoint — Start-up Evolution Engine (API Gateway & Worker)
#  Runs Alembic migrations before starting the application.
# ═══════════════════════════════════════════════════════════════════
set -e

echo "[entrypoint] SERVICE_ROLE=${SERVICE_ROLE:-unknown}"

# ── 1. Wait for PostgreSQL to accept connections ──────────────────
echo "[entrypoint] Waiting for PostgreSQL..."
python -c "
import asyncio, os, sys
async def wait():
    import asyncpg
    host = os.environ.get('POSTGRES_HOST', 'localhost')
    port = int(os.environ.get('POSTGRES_PORT', 5432))
    user = os.environ.get('POSTGRES_USER', 'postgres')
    password = os.environ.get('POSTGRES_PASSWORD', 'postgres')
    db = os.environ.get('POSTGRES_DB', 'startup_evolution')
    dsn = f'postgresql://{user}:{password}@{host}:{port}/{db}'
    for i in range(30):
        try:
            conn = await asyncpg.connect(dsn)
            await conn.close()
            print(f'[entrypoint] PostgreSQL ready after {i+1}s')
            return
        except Exception:
            await asyncio.sleep(1)
    print('[entrypoint] ERROR: PostgreSQL not reachable after 30s', file=sys.stderr)
    sys.exit(1)
asyncio.run(wait())
"

# ── 1b. Wait for Ollama and pull model if needed ────────────────
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-nemotron-3-super:cloud}"
if [ -n "$OLLAMA_HOST" ]; then
    echo "[entrypoint] Waiting for Ollama at ${OLLAMA_HOST}..."
    for i in $(seq 1 30); do
        if python -c "import httpx; httpx.get('${OLLAMA_HOST}/api/tags').raise_for_status()" 2>/dev/null; then
            echo "[entrypoint] Ollama ready after ${i}s"
            # Pull model if not already present
            echo "[entrypoint] Ensuring model '${OLLAMA_MODEL}' is available..."
            python -c "
import httpx, json, sys
try:
    r = httpx.post('${OLLAMA_HOST}/api/pull', json={'name': '${OLLAMA_MODEL}'}, timeout=300.0)
    print('[entrypoint] Model pull response:', r.status_code)
except Exception as e:
    print(f'[entrypoint] WARNING: Model pull failed: {e}', file=sys.stderr)
" 2>&1 || echo "[entrypoint] WARNING: Model pull skipped"
            break
        fi
        sleep 1
    done
fi

# ── 2. Run Alembic migrations ────────────────────────────────────
echo "[entrypoint] Running Alembic migrations..."
cd /app/backend

# Run migrations; if alembic_version table already has the correct version,
# the upgrade is a no-op. If a race condition causes a type conflict on
# alembic_version table creation, check current state and continue.
if alembic -c alembic.ini upgrade head 2>&1; then
    echo "[entrypoint] Migrations complete."
else
    # Check if we're already at the target version despite the error
    CURRENT=$(alembic -c alembic.ini current 2>&1 || true)
    if echo "$CURRENT" | grep -q "0001_initial"; then
        echo "[entrypoint] Migrations already applied (current: 0001_initial). Continuing."
    else
        echo "[entrypoint] ERROR: Alembic migration failed and current version is unknown."
        echo "[entrypoint] $CURRENT"
        exit 1
    fi
fi

# ── 3. Execute the main command ──────────────────────────────────
echo "[entrypoint] Starting: $@"
exec "$@"
