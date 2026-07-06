# Start-up Evolution Engine

An AI-powered platform that transforms raw startup ideas into investor-ready blueprints through an 8-stage compilation pipeline with real-time market grounding via live web search.

---

## Table of Contents

- [What It Does](#what-it-does)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Pipeline Stages](#pipeline-stages)
- [Real-Time Search Integration](#real-time-search-integration)
- [Prerequisites](#prerequisites)
- [Quick Start (Local Development)](#quick-start-local-development)
- [Docker Deployment](#docker-deployment)
- [Environment Variables](#environment-variables)
- [API Endpoints](#api-endpoints)
- [Running Tests](#running-tests)
- [Troubleshooting](#troubleshooting)

---

## What It Does

A founder describes their startup idea in plain text. The platform:

1. **Extracts** structured business DNA (category, business model, revenue streams)
2. **Generates** a product feature set with MoSCoW prioritization
3. **Builds** a phased delivery roadmap with milestone tasks
4. **Designs** an org chart with hiring sequence and salary estimates
5. **Analyzes** SWOT with real-time market data and funding schemes
6. **Projects** financial models with regional cost benchmarks and subsidies
7. **Compiles** an investor-ready Blueprint with health scores
8. **Produces** a Legal & Compliance doc pack with active grants, registration requirements, and regulatory directories

Every stage uses structured Pydantic output schemas validated against the LLM response. Real-time web search (Tavily / Google Custom Search) grounds Stages 5, 6, and 8 in live market facts.

---

## Architecture

```
                        Founder's Browser
                              |
                     +--------v--------+
                     |   Next.js 16    |   Port 3000
                     |   React 19 UI   |
                     +--------+--------+
                              |
                     REST API + SSE Stream
                              |
                     +--------v--------+
                     |   FastAPI        |   Port 8000
                     |   API Gateway    |
                     +--+-----+-----+--+
                        |     |     |
              +---------+     |     +---------+
              |               |               |
     +--------v---+   +------v------+   +----v--------+
     |  PostgreSQL |   |    Redis     |   |   ARQ       |
     |  16 (data)  |   |  7 (cache + |   |   Worker    |
     |             |   |   Pub/Sub)  |   |   Engine    |
     +-------------+   +-------------+   +----+--------+
                                                |
                                        +-------v--------+
                                        |  8-Stage        |
                                        |  Pipeline       |
                                        |  Orchestrator   |
                                        +-------+--------+
                                                |
                                    +-----------+-----------+
                                    |           |           |
                               +----v---+ +----v---+ +----v---+
                               | Tavily | | Google | | Gemini |
                               | Search | | CSE    | | /LLM   |
                               +--------+ +--------+ +--------+
```

**4-Tier Docker Deployment:**

| Tier | Service | Port | Purpose |
|------|---------|------|---------|
| 1 | `postgres` | 5432 | Persistent data storage |
| 1 | `redis` | 6379 | Cache, Pub/Sub, ARQ job queue |
| 2 | `api-gateway` | 8000 | FastAPI REST + SSE streaming |
| 3 | `worker-engine` | — | ARQ background pipeline executor |
| 4 | `frontend-service` | 3000 | Next.js production build |

---

## Tech Stack

**Frontend:**
- Next.js 16 (App Router), React 19, TypeScript
- Tailwind CSS, shadcn/ui components
- Zustand (state), TanStack Query (data fetching)
- Recharts (charts), Motion (animations)

**Backend:**
- Python 3.13+, FastAPI, SQLAlchemy 2.0 (async)
- PostgreSQL 16 (asyncpg), Redis 7
- Pydantic V2 (structured LLM output validation)
- ARQ (async task queue), Jinja2 (prompt templating)
- httpx (HTTP client for search + LLM)

**AI/LLM:**
- Gemini API / Ollama (configurable via `OLLAMA_HOST`)
- Tavily Search API (primary, AI-optimized)
- Google Custom Search JSON API (fallback)

---

## Project Structure

```
.
├── backend/
│   ├── app/                    # FastAPI application factory + health routes
│   ├── ai/
│   │   ├── gemini.py           # LLM adapter (structured JSON generation)
│   │   ├── context.py          # Context assembly + checksum computation
│   │   └── provider.py         # Abstract LLM provider interface
│   ├── api/
│   │   └── v1/
│   │       ├── router.py       # Central router registration
│   │       ├── generator.py    # POST /run — trigger pipeline
│   │       ├── streams.py      # SSE event streaming
│   │       └── intake.py       # Interactive onboarding chat
│   ├── core/
│   │   ├── config.py           # Pydantic Settings (all env vars)
│   │   ├── logging.py          # Structured logging + context vars
│   │   └── exceptions.py       # Custom business exceptions
│   ├── models/
│   │   ├── project.py          # Project, ProjectVersion
│   │   ├── results.py          # DNAResult, FeatureResult, ..., LegalComplianceResult
│   │   ├── blueprint.py        # Blueprint (final output)
│   │   └── workflow.py         # GenerationSession, WorkflowEvent
│   ├── modules/
│   │   ├── dna/                # Stage 1: Business DNA extraction
│   │   ├── features/           # Stage 2: Product feature generation
│   │   ├── roadmap/            # Stage 3: Delivery roadmap
│   │   ├── team/               # Stage 4: Org chart + hiring plan
│   │   ├── swot/               # Stage 5: SWOT + real-time market data
│   │   ├── cost/               # Stage 6: Financial model + subsidies
│   │   ├── blueprint/          # Stage 7: Investor blueprint compilation
│   │   └── legal_compliance/   # Stage 8: Legal & compliance doc pack
│   ├── orchestrator/
│   │   └── engine.py           # WorkflowOrchestrator + BaseModule
│   ├── services/
│   │   ├── assistant.py        # Interactive intake consultation
│   │   └── project.py          # Project CRUD service
│   ├── utils/
│   │   ├── checksum.py         # Deterministic SHA-256 input hashing
│   │   └── search.py           # Web search provider (Tavily + Google CSE)
│   ├── worker/
│   │   ├── main.py             # ARQ WorkerSettings
│   │   └── tasks.py            # run_compilation_pipeline task
│   ├── cache/                  # Redis connection manager
│   ├── database/               # Async session factory
│   ├── schemas/                # Pydantic request/response models
│   ├── repositories/           # Generic CRUD repository pattern
│   ├── tests/                  # pytest + pytest-asyncio suite
│   └── requirements.txt
├── src/
│   ├── app/                    # Next.js App Router pages
│   ├── components/             # React components (IntakeChat, etc.)
│   ├── lib/
│   │   └── api-client.ts       # Typed HTTP client for backend API
│   ├── store/
│   │   ├── useIntakeStore.ts   # Intake consultation state
│   │   └── use-blueprint-store.ts
│   └── types/                  # TypeScript type definitions
├── docker-compose.yml          # 4-tier production deployment
├── backend/Dockerfile          # Multi-target: api-gateway | worker-engine
├── Dockerfile                  # Next.js production build
└── package.json                # Frontend dependencies + dev scripts
```

---

## Pipeline Stages

| # | Stage | Critical | Description |
|---|-------|----------|-------------|
| 1 | `dna` | Yes | Extracts business category, model, revenue streams, USP |
| 2 | `features` | Yes | Generates features with MoSCoW priority and complexity scores |
| 3 | `roadmap` | Yes | Phased delivery timeline with milestone tasks |
| 4 | `team` | Yes | Org chart, roles, salaries, hiring sequence |
| 5 | `swot` | No | SWOT matrix + mitigation strategies (real-time market data) |
| 6 | `cost` | Yes | Operational costs, budget scenarios, funding targets (real-time cost data) |
| 7 | `blueprint` | Yes | Aggregates all modules, health scoring, executive summary |
| 8 | `legal_compliance` | Yes | Funding schemes, registrations, compliance directories (real-time search) |

**Cache Strategy:** Before each stage, a deterministic SHA-256 checksum is computed from the stage's inputs (project base + all upstream results). If the checksum matches a stored result, the LLM call is skipped entirely.

---

## Real-Time Search Integration

Stages 5 (SWOT), 6 (Cost), and 8 (Legal & Compliance) perform live web searches to ground LLM outputs in verified market facts.

**Provider chain:** Tavily (primary) -> Google Custom Search (fallback) -> Graceful degradation

**How it works:**
1. Each module builds region + industry-qualified search queries
2. Queries execute concurrently via `asyncio.gather`
3. Results are formatted into labeled context blocks:
   - `[REAL-TIME_MARKET_DATA]...[/REAL-TIME_MARKET_DATA]`
   - `[REAL-TIME_FUNDING_DATA]...[/REAL-TIME_FUNDING_DATA]`
   - `[REAL-TIME_COMPLIANCE_DATA]...[/REAL-TIME_COMPLIANCE_DATA]`
4. Blocks are injected directly into the Jinja2 prompt template
5. The LLM is instructed to reference specific scheme names, URLs, and data points from the search results

**Search queries per module:**

| Module | Queries |
|--------|---------|
| SWOT | `"{industry} market trends 2026 opportunities"`, `"government startup grants {industry}"` |
| Cost | `"{industry} startup costs {region} 2026"`, `"startup subsidy scheme {region}"` |
| Legal | `"business registration {region} 2026"`, `"data protection law {region} {industry}"` |

---

## Prerequisites

- **Node.js** v18+ (v20 recommended)
- **Python** v3.13+
- **PostgreSQL** 16 (local or Docker)
- **Redis** 7 (local or Docker)
- **Docker** + Docker Compose (for containerized deployment)
- **Tavily API key** (free tier: 1000 queries/month) or **Google Custom Search API key**

---

## Quick Start (Local Development)

### 1. Clone and install dependencies

```bash
git clone <your-repo-url>
cd Start-up-Evolution-Engine

# Frontend
npm install

# Backend
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
cd ..
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
SECRET_KEY=<generate a 64-char random string>
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=startup_evolution
GEMINI_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here     # optional but recommended
```

### 3. Start databases (if not using Docker)

```bash
# PostgreSQL and Redis must be running locally
# Verify:
pg_isready
redis-cli ping
```

### 4. Run database migrations

```bash
cd backend
alembic upgrade head
cd ..
```

### 5. Start all services

```bash
npm run dev
```

This runs concurrently:
- **Frontend:** http://localhost:3000
- **Backend:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

### 6. Trigger a pipeline run

```bash
curl -X POST http://localhost:8000/api/v1/generator/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "<uuid>",
    "correlation_id": "<any-unique-string>"
  }'
```

SSE stream: `GET /api/v1/streams/{session_id}`

---

## Docker Deployment

### Build and start all 4 tiers

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your values

# Build and launch
docker compose up -d --build
```

### Verify services

```bash
docker compose ps

# Expected:
# see-postgres      running   0.0.0.0:5432->5432/tcp
# see-redis         running   0.0.0.0:6379->6379/tcp
# see-api-gateway   running   0.0.0.0:8000->8000/tcp
# see-worker-engine running
# see-frontend      running   0.0.0.0:3000->3000/tcp
```

### View logs

```bash
docker compose logs -f api-gateway
docker compose logs -f worker-engine
```

### Stop

```bash
docker compose down           # stop containers
docker compose down -v        # stop + delete volumes (fresh start)
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | — | JWT signing key (min 32 chars) |
| `POSTGRES_USER` | No | `postgres` | PostgreSQL username |
| `POSTGRES_PASSWORD` | No | `postgres` | PostgreSQL password |
| `POSTGRES_HOST` | No | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | No | `5432` | PostgreSQL port |
| `POSTGRES_DB` | No | `startup_evolution` | Database name |
| `REDIS_HOST` | No | `localhost` | Redis host |
| `REDIS_PORT` | No | `6379` | Redis port |
| `GEMINI_API_KEY` | Yes | — | Gemini / Ollama API key |
| `OLLAMA_HOST` | No | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | No | `nemotron-3-super:cloud` | Model to use |
| `TAVILY_API_KEY` | No | — | Tavily search API key (recommended) |
| `GOOGLE_SEARCH_API_KEY` | No | — | Google Custom Search API key |
| `GOOGLE_CSE_ID` | No | — | Google Custom Search Engine ID |
| `ENVIRONMENT` | No | `development` | `development` / `staging` / `production` |
| `SERVICE_ROLE` | No | `api-gateway` | `api-gateway` / `worker-engine` |
| `ALLOWED_ORIGINS` | No | `http://localhost:3000` | CORS origins (comma-separated) |
| `NEXT_PUBLIC_API_URL` | No | `http://localhost:8000` | Frontend API base URL |
| `NEXT_PUBLIC_STREAM_URL` | No | `http://localhost:8000` | Frontend SSE base URL |

---

## API Endpoints

### Pipeline

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/generator/run` | Trigger full pipeline (returns 202 + session_id) |
| `POST` | `/api/v1/generator/enhance` | Enhance a raw idea description |
| `GET` | `/api/v1/streams/{session_id}` | SSE stream for pipeline progress events |

### Intake Consultation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/intake/start` | Start intake session with raw idea |
| `POST` | `/api/v1/intake/message` | Submit answer to follow-up question |
| `POST` | `/api/v1/intake/finalize` | Finalize and get enriched package |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health/liveness` | Liveness probe |
| `GET` | `/api/v1/health/readiness` | Readiness probe |

### Docs

| Endpoint | Description |
|----------|-------------|
| `/docs` | Swagger UI (interactive API explorer) |
| `/redoc` | ReDoc (alternative API docs) |

---

## Running Tests

```bash
cd backend
pytest -v
```

Tests use an in-memory SQLite database and mock the LLM adapter. No external services required.

---

## Troubleshooting

**Pipeline fails with "Module not registered"**
- Ensure `worker-engine` container is running: `docker compose logs worker-engine`

**Search returns "No search provider configured"**
- Set `TAVILY_API_KEY` in `.env` (free at https://tavily.com)
- Or set both `GOOGLE_SEARCH_API_KEY` and `GOOGLE_CSE_ID`

**Database connection refused**
- Verify PostgreSQL is running: `pg_isready`
- Check `POSTGRES_HOST` matches your setup (`localhost` for local, `postgres` for Docker)

**Redis connection refused**
- Verify Redis is running: `redis-cli ping`
- Check `REDIS_HOST` matches your setup

**Frontend can't reach backend**
- Verify `NEXT_PUBLIC_API_URL` points to `http://localhost:8000` (local) or `http://api-gateway:8000` (Docker)
- Check CORS: ensure your frontend origin is in `ALLOWED_ORIGINS`

**ALEMBIC / migrations not available**
- The project uses SQLAlchemy `create_all()` for schema creation
- Run: `cd backend && python -c "from backend.database.session import engine; from backend.models.base import Base; import backend.models; asyncio.run(Base.metadata.create_all(engine))"`
