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

# ── 1b. Confirm remote Ollama Cloud is reachable; never pull weights ─
OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
if [[ "$OLLAMA_HOST" == https://ollama.com* ]]; then
    echo "[entrypoint] Using remote Ollama Cloud at ${OLLAMA_HOST}; no local model pull."
    python -c "import os, httpx; key=os.environ.get('OLLAMA_API_KEY'); headers={'Authorization': f'Bearer {key}'} if key else {}; httpx.get(os.environ['OLLAMA_HOST'].rstrip('/') + '/api/tags', headers=headers, timeout=15.0).raise_for_status()"
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
