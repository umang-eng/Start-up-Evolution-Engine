<div align="center">

# Start-up Evolution Engine

**An AI-powered platform that transforms raw startup ideas into investor-ready blueprints through an 8-stage compilation pipeline with real-time market grounding, conversation intelligence, and a pluggable multi-agent mesh.**

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Next.js 16](https://img.shields.io/badge/next.js-16-black?style=flat&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [8-Stage Compilation Pipeline](#8-stage-compilation-pipeline)
- [Agent Mesh System](#agent-mesh-system)
- [Conversation Intelligence](#conversation-intelligence)
- [Real-Time Search Integration](#real-time-search-integration)
- [Authentication & Security](#authentication--security)
- [Caching & Performance](#caching--performance)
- [Prerequisites](#prerequisites)
- [Quick Start (Local Development)](#quick-start-local-development)
- [Docker Deployment](#docker-deployment)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [Running Tests](#running-tests)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Overview

A founder describes their startup idea in plain text. The platform then:

1. **Extracts** structured business DNA — category, business model, revenue streams, USP, and six strategic scores (innovation, scalability, complexity, market opportunity, risk, competition)
2. **Generates** a product feature set with MoSCoW prioritization, complexity scores, and dependency graphs
3. **Builds** a phased delivery roadmap with milestone tasks, timeline estimates, and launch readiness scoring
4. **Designs** an org chart with RACI matrix, hiring sequence, and salary estimates across 8 departments
5. **Analyzes** a SWOT matrix with real-time market data, threat severity scoring, and founder action items across 4 time horizons
6. **Projects** financial models with regional cost benchmarks, 3 budget scenarios (lean/balanced/aggressive), and funding runway targets
7. **Compiles** an investor-ready Blueprint with 6 health indicators, conflict resolution logs, and executive summaries
8. **Produces** a Legal & Compliance document pack with active government grants, registration requirements, and regulatory directories — all grounded in live web search

Every stage uses **structured Pydantic output schemas** validated against the LLM response. A **deterministic SHA-256 cache** skips LLM calls when inputs haven't changed. **Real-time web search** (Tavily / Google Custom Search) grounds stages 5, 6, and 8 in live market facts.

The platform also includes **Conversation Intelligence** — record or upload meeting audio, transcribe it with Whisper.cpp, and generate AI-powered intelligence reports with action items, decisions, risks, and follow-ups.

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
                                    +------------+------------+
                                    |            |            |
                               +----v---+  +----v---+  +----v---+
                               | Agent  |  |  LLM   |  | Search |
                               |  Mesh  |  | Gemini |  | Tavily |
                               +--------+  +--------+  +--------+
                                    |
                        +-----------+-----------+
                        |           |           |
                   +----v---+ +----v---+ +----v---+
                   |Research| |Analyst | |Reviewer|
                   |  er    | |        | |        |
                   +--------+ +--------+ +--------+
```

### 5-Tier Docker Deployment

| Tier | Service | Container | Port | Purpose |
|------|---------|-----------|------|---------|
| 1 | PostgreSQL 16 | `see-postgres` | 5432 | Persistent data storage |
| 1 | Redis 7 | `see-redis` | 6379 | Cache, Pub/Sub, ARQ job queue |
| 2 | Ollama | `see-ollama` | 11435 | Local LLM inference + cloud model proxy |
| 2 | Whisper.cpp | `see-whisper` | 9000 | Speech-to-text transcription |
| 3 | FastAPI | `see-api-gateway` | 8000 | REST API + SSE streaming |
| 4 | ARQ Worker | `see-worker-engine` | — | Background pipeline executor |
| 5 | Next.js | `see-frontend` | 3000 | Production React build |

---

## Tech Stack

### Frontend

| Category | Technology |
|----------|------------|
| Framework | Next.js 16 (App Router), React 19, TypeScript |
| Styling | Tailwind CSS, shadcn/ui components |
| State Management | Zustand (client state) |
| Data Fetching | TanStack Query (server state) |
| Charts | Recharts |
| Animations | Motion (Framer Motion) |
| Auth | JWT access + refresh tokens |

### Backend

| Category | Technology |
|----------|------------|
| Framework | FastAPI (async), Python 3.13+ |
| ORM | SQLAlchemy 2.0 (async, asyncpg) |
| Database | PostgreSQL 16 |
| Cache / Queue | Redis 7 (ARQ task queue, Pub/Sub) |
| Validation | Pydantic V2 (structured LLM output) |
| Templating | Jinja2 (prompt templates) |
| HTTP Client | httpx (search + LLM calls) |
| Auth | bcrypt (passwords), JWT (access/refresh) |
| Transcription | Whisper.cpp (speech-to-text) |

### AI / LLM

| Category | Technology |
|----------|------------|
| Primary LLM | Ollama (local + cloud model proxy) |
| Default Model | `nemotron-3-super:cloud` (NVIDIA cloud) |
| Structured Output | JSON schema-constrained generation |
| Primary Search | Tavily Search API (AI-optimized) |
| Fallback Search | Google Custom Search JSON API |
| Transcription | Whisper.cpp (`base` model) |

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI application factory
│   │   └── health.py             # Liveness + readiness probes
│   ├── ai/
│   │   ├── gemini.py             # LLM adapter (structured JSON generation)
│   │   ├── context.py            # Context assembly + checksum computation
│   │   └── provider.py           # Abstract LLM provider interface
│   ├── api/
│   │   └── v1/
│   │       ├── router.py         # Central router registration
│   │       ├── auth.py           # Register, login, refresh, me
│   │       ├── projects.py       # Project CRUD
│   │       ├── generator.py      # POST /run — trigger pipeline
│   │       ├── streams.py        # SSE event streaming
│   │       ├── intake.py         # Interactive onboarding chat
│   │       ├── blueprints.py     # Blueprint retrieval + share links
│   │       ├── exports.py        # PDF + PowerPoint export
│   │       └── meetings.py       # Conversation Intelligence endpoints
│   ├── agents/                   # Multi-agent mesh system
│   │   ├── types.py              # Pydantic contracts (AgentRole, budgets, findings)
│   │   ├── tools.py              # Tool ABC + registry (web search, DB, calculations)
│   │   ├── context_bus.py        # Inter-agent observation pub/sub
│   │   ├── base.py               # BaseAgent ABC with budget enforcement
│   │   ├── workflows.py          # Sequential, Parallel, Debate workflows
│   │   ├── config.py             # Per-stage feature flags (all disabled by default)
│   │   ├── module.py             # AgentModule — drop-in BaseModule replacement
│   │   └── agents/
│   │       ├── researcher.py     # Gathers market + project data
│   │       ├── analyst.py        # Computes health indicators + metrics
│   │       ├── synthesizer.py    # LLM-powered output generation (schema-bound)
│   │       └── reviewer.py       # Validates output quality + completeness
│   ├── core/
│   │   ├── config.py             # Pydantic Settings (all env vars)
│   │   ├── logging.py            # Structured JSON logging + correlation IDs
│   │   └── exceptions.py         # Custom business exceptions
│   ├── models/
│   │   ├── base.py               # DeclarativeBase + mixins (UUID, timestamps)
│   │   ├── user.py               # User (email, hashed_password, role)
│   │   ├── project.py            # Project, ProjectVersion
│   │   ├── results.py            # DNAResult, FeatureResult, ..., LegalComplianceResult
│   │   ├── blueprint.py          # Blueprint (final compiled output)
│   │   ├── workflow.py           # GenerationSession, WorkflowEvent
│   │   ├── meeting.py            # Meeting, MeetingSegment, Transcript, MeetingReport
│   │   ├── audit.py              # AuditLog
│   │   └── analytics.py          # AnalyticsLog (token usage, latency, cost)
│   ├── modules/
│   │   ├── dna/                  # Stage 1: Business DNA extraction
│   │   │   ├── module.py         # DNAModule(BaseModule)
│   │   │   └── schemas.py        # DNAOutput, DNAScores, DNAPayload
│   │   ├── features/             # Stage 2: Product feature generation
│   │   │   ├── module.py         # FeatureExtractorModule
│   │   │   └── schemas.py        # FeatureExtractorOutput, FeatureItem
│   │   ├── roadmap/              # Stage 3: Delivery roadmap
│   │   │   ├── module.py         # RoadmapGeneratorModule
│   │   │   └── schemas.py        # RoadmapOutput, RoadmapPhase, LaunchReadinessPlan
│   │   ├── team/                 # Stage 4: Org chart + hiring
│   │   │   ├── module.py         # TeamGeneratorModule
│   │   │   └── schemas.py        # TeamOutput, RoleCard, RACIAssignment
│   │   ├── swot/                 # Stage 5: SWOT + market data
│   │   │   ├── module.py         # SWOTBuilderModule
│   │   │   └── schemas.py        # SWOTOutput, ThreatMitigation, FounderAction
│   │   ├── cost/                 # Stage 6: Financial model
│   │   │   ├── module.py         # CostEstimatorModule
│   │   │   └── schemas.py        # CostOutput, BudgetScenario, FundingRequirement
│   │   ├── blueprint/            # Stage 7: Investor blueprint
│   │   │   ├── module.py         # BlueprintComposerModule
│   │   │   └── schemas.py        # BlueprintOutput, ExecutiveSummary, HealthIndicators
│   │   └── legal_compliance/     # Stage 8: Legal & compliance
│   │       ├── module.py         # LegalComplianceModule
│   │       └── schemas.py        # LegalComplianceOutput, FundingSource, RegistrationRequirement
│   ├── orchestrator/
│   │   └── engine.py             # WorkflowOrchestrator + BaseModule ABC
│   ├── services/
│   │   ├── assistant.py          # Interactive intake consultation
│   │   ├── project.py            # Project CRUD service
│   │   └── meeting.py            # Meeting + report generation service
│   ├── repositories/
│   │   └── meeting.py            # Meeting data access layer
│   ├── utils/
│   │   ├── checksum.py           # Deterministic SHA-256 input hashing
│   │   └── search.py             # Web search provider (Tavily + Google CSE)
│   ├── worker/
│   │   ├── main.py               # ARQ WorkerSettings
│   │   └── tasks.py              # run_compilation_pipeline + module registration
│   ├── cache/                    # Redis connection manager
│   ├── database/                 # Async session factory + connectivity verification
│   ├── schemas/                  # Pydantic request/response models
│   ├── tests/                    # pytest + pytest-asyncio suite
│   └── requirements.txt
├── tests/
│   └── agents/                   # Agent mesh unit tests (74 tests)
│       ├── test_types.py
│       ├── test_tools.py
│       ├── test_context_bus.py
│       ├── test_base.py
│       ├── test_workflows.py
│       ├── test_dna_e2e.py
│       └── test_worker_integration.py
├── src/
│   ├── app/                      # Next.js App Router pages
│   │   ├── page.tsx              # Main workspace + pipeline visualization
│   │   ├── login/page.tsx        # Login
│   │   ├── signup/page.tsx       # Registration
│   │   ├── meetings/page.tsx     # Conversation Intelligence
│   │   └── layout.tsx            # Root layout + providers
│   ├── components/
│   │   ├── IntakeChat.tsx        # Intake consultation chat
│   │   ├── ui/                   # Shadcn UI primitives
│   │   ├── shared/               # Auth, navbar, sidebar, glass panels
│   │   └── meetings/             # Audio recorder, transcript uploader, report viewer
│   ├── lib/
│   │   └── api-client.ts         # Typed HTTP + SSE client for backend
│   ├── store/                    # Zustand stores (blueprint, meeting, intake, settings)
│   └── types/                    # TypeScript type definitions
├── scripts/
│   └── shadow_validate.py        # Agent mesh shadow-mode validation
├── docker-compose.yml            # 5-tier production deployment
├── backend/Dockerfile            # Multi-target: api-gateway | worker-engine
├── Dockerfile                    # Next.js production build
├── .env.example                  # Environment variable template
└── package.json                  # Frontend dependencies + scripts
```

---

## 8-Stage Compilation Pipeline

The pipeline runs stages in a dependency-aware order with parallel execution where possible:

```
[dna] → [features] → [roadmap] → [team] → [swot] + [cost] → [blueprint] + [legal_compliance]
                                                           (parallel)        (parallel)
```

### Stage Details

| # | Stage | Module | Output Schema | Parallel | Description |
|---|-------|--------|---------------|----------|-------------|
| 1 | `dna` | `DNAModule` | `DNAOutput` | No | Business category, model, revenue streams, USP, 6 strategic scores (0-100) |
| 2 | `features` | `FeatureExtractorModule` | `FeatureExtractorOutput` | No | 5 features with MoSCoW priority, complexity, and dependency graph |
| 3 | `roadmap` | `RoadmapGeneratorModule` | `RoadmapOutput` | No | Phased delivery timeline with 12 tasks, milestones, and launch readiness score |
| 4 | `team` | `TeamGeneratorModule` | `TeamOutput` | No | Org chart (3-4 roles), RACI matrix, hiring sequence, salary estimates |
| 5 | `swot` | `SWOTBuilderModule` | `SWOTOutput` | Yes | SWOT matrix, threat mitigations (severity 1-9), founder actions across 4 horizons |
| 6 | `cost` | `CostEstimatorModule` | `CostOutput` | Yes | Operational costs, 3 budget scenarios, funding requirements, runway analysis |
| 7 | `blueprint` | `BlueprintComposerModule` | `BlueprintOutput` | No | Aggregates all modules, health scoring (6 indicators), executive summary, conflict resolution |
| 8 | `legal_compliance` | `LegalComplianceModule` | `LegalComplianceOutput` | No | Funding sources, registration requirements, compliance directories, data protection |

### Output Schemas (Key Fields)

**DNAOutput** — `category`, `business_model`, `revenue_streams[]`, `value_proposition`, `usp`, `target_segments[]`, `scores.{innovation, scalability, complexity, market_opportunity, risk_factor, competition}`, `executive_summary`, `strategic_recommendations[]`, `confidence_score`

**FeatureExtractorOutput** — `features[].{id, name, category[CORE/ADVANCED/FUTURE/COMPETITIVE/GROWTH], priority[MoSCoW], complexity[LOW/MEDIUM/HIGH], dependencies[]}`, `mvp_scope_rationale`, `core_stack`, `blockers`

**RoadmapOutput** — `phases[].{phase_id, name, duration_months, milestones[], tasks[].{id, title, duration_weeks, assigned_role_id, dependencies[]}}`, `launch_readiness_plan.{readiness_score, checklist[]}`

**TeamOutput** — `org_chart[].{role_id, title, department, reports_to, responsibilities[], required_skills[], estimated_salary_usd, hiring_stage}`, `raci_matrix[]`, `recommended_team_size`, `hiring_sequence[]`

**SWOTOutput** — `strengths[]`, `weaknesses[]`, `opportunities[]`, `threats[].{description, impact, probability, severity}`, `mitigations[].{threat_description, mitigation_strategy, action_item_id}`, `founder_actions[].{horizon, action, priority}`

**CostOutput** — `operational_costs[].{category, monthly_usd, is_mvp_critical}`, `budget_scenarios[].{name[LEAN/BALANCED/AGGRESSIVE], monthly_burn_usd, runway_months}`, `funding_requirements.{minimum_target_usd, optimal_target_usd}`, `mvp_cost_estimate`, `year_1_cost_estimate`, `financial_risk_level`

**BlueprintOutput** — `executive_summary.{business_summary, strategic_summary, execution_summary, financial_summary, founder_directives}`, `health_indicators.{composite_score, execution_readiness, funding_readiness, growth_readiness, risk_exposure, strategic_strength}`, `startup_dna`, `product_architecture`, `execution_roadmap`, `team_structure`, `swot_analysis`, `financial_plan`, `conflict_resolution_log[]`, `legal_compliance`

**LegalComplianceOutput** — `funding_sources[].{scheme_name, scheme_type, amount_range, application_url, relevance_score}`, `registration_requirements[].{requirement_name, authority, category, is_mandatory, estimated_cost, timeline}`, `compliance_directories[]`, `industry_specific_licenses[]`, `data_protection_requirements[]`, `estimated_compliance_budget_usd`

---

## Agent Mesh System

A pluggable multi-agent system that can replace any pipeline stage's single LLM call with a team of specialized agents collaborating through structured workflows.

### Agent Roles

| Role | Purpose | Tools Used |
|------|---------|------------|
| **Researcher** | Gathers market data, project context, competitive landscape | WebSearchTool, DatabaseTool |
| **Analyst** | Computes health indicators, metrics, trend analysis | CalculationTool |
| **Synthesizer** | Generates structured output via LLM (schema-bound) | None (LLM direct) |
| **Reviewer** | Validates output quality, completeness, score ranges | None (validation only) |

### Workflow Patterns

| Pattern | Use Case | Behavior |
|---------|----------|----------|
| **Sequential** | DNA, Features, Roadmap, Team, Cost, Blueprint, Legal | Agents execute in order, each building on the previous output |
| **Debate** | SWOT | Synthesizer produces output → Reviewer critiques → Synthesizer revises (up to N rounds). Non-convergence produces best-effort output with `unresolved_issues` metadata |
| **Parallel** | (Available) | Multiple agents run simultaneously, results merged via namespace or override strategy |

### Per-Stage Configuration (`backend/agents/config.py`)

All stages default to `enabled=False`. Each stage defines:
- **Workflow type**: `sequential` or `debate`
- **Agent team**: Which roles participate
- **Budgets**: `max_tokens` (4000), `timeout_s` (30s), `max_tool_calls` (2-4 per agent)
- **Web research**: Whether the Researcher agent fetches live market data

### Enabling Agent Mesh

In `backend/agents/config.py`, flip the `enabled` flag:

```python
AGENT_MESH_CONFIG = {
    "dna": StageAgentConfig(
        enabled=True,  # <-- Flip this
        workflow="sequential",
        agents=[AgentRole.RESEARCHER, AgentRole.ANALYST, AgentRole.SYNTHESIZER, AgentRole.REVIEWER],
        ...
    ),
    ...
}
```

The worker automatically routes to `AgentModule` for enabled stages and falls back to the original `BaseModule` for disabled ones.

### Key Files

| File | Purpose |
|------|---------|
| `backend/agents/types.py` | Pydantic contracts: `AgentRole`, `ToolCallResult`, `Observation`, `ResearchFindings`, `AnalysisReport`, `ReviewCritique`, `AgentBudget`, `StageAgentConfig` |
| `backend/agents/tools.py` | `Tool` ABC with `safe_execute()` (never raises), `WebSearchTool`, `DatabaseTool`, `CalculationTool`, `ToolRegistry` |
| `backend/agents/context_bus.py` | `AgentContextBus` with publish/subscribe, required timeout on `subscribe()` |
| `backend/agents/base.py` | `BaseAgent` ABC: `safe_run()`, `use_tool()` (budget-enforced), `publish_observation()`, `wait_for_observation()` |
| `backend/agents/workflows.py` | `SequentialWorkflow`, `ParallelWorkflow` (namespace/override merge), `DebateWorkflow` (max rounds, non-convergence handling) |
| `backend/agents/module.py` | `AgentModule(BaseModule)` — drop-in replacement, creates agent team per stage, runs workflow, persists result |
| `backend/agents/config.py` | `AGENT_MESH_CONFIG` — per-stage feature flags, all disabled by default |

---

## Conversation Intelligence

A full-stack meeting transcription and AI analysis system.

### Workflow

```
Record Audio → Upload → Whisper Transcribe → Store Transcript → Generate AI Report
     or                                                          ↓
Upload Text/File                                          Executive Summary
                                                            Key Points
                                                            Decisions
                                                            Action Items (owner, priority, deadline)
                                                            Risks & Concerns
                                                            Agreements / Disagreements
                                                            Technical Topics
                                                            Business Opportunities
                                                            Follow-up Items
```

### Features

- **Browser audio recording** with waveform visualization
- **Multi-format upload** (webm, mp4, mp3, wav, ogg, m4a, flac)
- **Whisper.cpp transcription** with Bearer token authentication
- **Streaming transcript segments** (real-time upload during recording)
- **AI-powered intelligence reports** via Gemini/Ollama
- **Structured report fields**: executive summary, decisions, action items with owners, risks, agreements, technical topics, business opportunities
- **Report viewer** with collapsible sections, priority badges, copy-to-clipboard

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/meetings` | Create meeting session |
| `GET` | `/api/v1/meetings` | List user meetings |
| `GET` | `/api/v1/meetings/{id}` | Get meeting details |
| `DELETE` | `/api/v1/meetings/{id}` | Delete meeting + transcripts |
| `POST` | `/api/v1/meetings/{id}/transcript` | Upload complete transcript |
| `POST` | `/api/v1/meetings/{id}/transcript/segments` | Upload streaming segments |
| `POST` | `/api/v1/meetings/{id}/transcript/audio` | Upload audio for transcription |
| `GET` | `/api/v1/meetings/{id}/transcript` | Fetch transcript |
| `POST` | `/api/v1/meetings/{id}/report/generate` | Generate AI report |
| `GET` | `/api/v1/meetings/{id}/report` | Fetch AI report |

---

## Real-Time Search Integration

Stages 5 (SWOT), 6 (Cost), and 8 (Legal & Compliance) perform live web searches to ground LLM outputs in verified market facts.

**Provider chain:** Tavily (primary) → Google Custom Search (fallback) → Graceful degradation

### How It Works

1. Each module builds region + industry-qualified search queries
2. Queries execute concurrently via `asyncio.gather`
3. Results are formatted into labeled context blocks:
   - `[REAL-TIME_MARKET_DATA]...[/REAL-TIME_MARKET_DATA]`
   - `[REAL-TIME_FUNDING_DATA]...[/REAL-TIME_FUNDING_DATA]`
   - `[REAL-TIME_COMPLIANCE_DATA]...[/REAL-TIME_COMPLIANCE_DATA]`
4. Blocks are injected into the Jinja2 prompt template
5. The LLM is instructed to reference specific scheme names, URLs, and data points

### Search Queries Per Module

| Module | Sample Queries |
|--------|---------------|
| SWOT | `"{industry} market trends 2026 opportunities"`, `"government startup grants {industry}"` |
| Cost | `"{industry} startup costs {region} 2026"`, `"startup subsidy scheme {region}"` |
| Legal | `"business registration {region} 2026"`, `"data protection law {region} {industry}"` |

---

## Authentication & Security

- **Password hashing**: bcrypt with salt
- **JWT tokens**: Access (15 min) + Refresh (7 days) with HS256 signing
- **CORS**: Configurable via `ALLOWED_ORIGINS` (comma-separated)
- **Rate limiting**: Configurable per-endpoint
- **Secret key**: Minimum 32 characters, validated at startup
- **Whisper auth**: Bearer token authentication (`WHISPER_API_KEY`)

---

## Caching & Performance

### Deterministic Cache

Before each pipeline stage, a SHA-256 checksum is computed from:
- Project base fields (title, description, industry)
- All upstream stage results

If the checksum matches a stored result, the LLM call is skipped entirely. This means re-running a pipeline on unchanged data is near-instant.

### Parallel Execution

The orchestrator runs independent stages concurrently:
- Stages 5 (SWOT) and 6 (Cost) run in parallel
- Stages 7 (Blueprint) and 8 (Legal) run in parallel

### Connection Pooling

- PostgreSQL: 20 persistent connections + 10 overflow
- Redis: Persistent connection with keepalive
- `pool_pre_ping=True` prevents stale connections

### Prompt Compression

Context dictionaries are recursively compressed before injection into prompts:
- Lists capped at 12 items
- Descriptions truncated to 500 characters
- Nested objects flattened

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Node.js | v18+ (v20 recommended) | Frontend build |
| Python | v3.13+ | Backend runtime |
| PostgreSQL | 16 | Local or Docker |
| Redis | 7 | Local or Docker |
| Docker | Latest | Containerized deployment |
| Docker Compose | v2+ | Multi-container orchestration |
| Tavily API Key | — | Free tier: 1000 queries/month (recommended) |
| Gemini API Key | — | For LLM inference (or use Ollama cloud proxy) |

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
OLLAMA_API_KEY=your_key_here     # for cloud models
WHISPER_API_KEY=see-whisper-secret-key-2026
```

### 3. Start databases (if not using Docker)

```bash
# PostgreSQL and Redis must be running locally
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

### 6. Create an account and project

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "founder@example.com", "password": "securepass123"}'

# Login (get JWT)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "founder@example.com", "password": "securepass123"}'

# Create project
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{"title": "AI Fitness Coach", "description": "AI-powered personal training app", "industry": "Health & Fitness"}'
```

### 7. Trigger a pipeline run

```bash
curl -X POST http://localhost:8000/api/v1/generator/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "project_id": "<uuid>",
    "correlation_id": "<any-unique-string>"
  }'
```

### 8. Stream progress (SSE)

```bash
curl -N http://localhost:8000/api/v1/streams/<session_id>
```

---

## Docker Deployment

### Build and start all tiers

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
# see-ollama        running   0.0.0.0:11435->11434/tcp
# see-whisper       running   0.0.0.0:9000->9000/tcp
# see-api-gateway   running   0.0.0.0:8000->8000/tcp
# see-worker-engine running
# see-frontend      running   0.0.0.0:3000->3000/tcp
```

### View logs

```bash
docker compose logs -f api-gateway
docker compose logs -f worker-engine
docker compose logs -f see-whisper
```

### Stop

```bash
docker compose down           # stop containers
docker compose down -v        # stop + delete volumes (fresh start)
```

### Rebuild after code changes

```bash
docker compose up -d --build api-gateway worker-engine
```

---

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing key (min 32 chars). Generate with: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `GEMINI_API_KEY` | Gemini / Ollama API key for LLM inference |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `postgres` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `postgres` | PostgreSQL password |
| `POSTGRES_HOST` | `localhost` | PostgreSQL host (`postgres` inside Docker) |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `startup_evolution` | Database name |

### Redis

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `localhost` | Redis host (`redis` inside Docker) |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_PASSWORD` | — | Redis password (optional) |

### AI / LLM

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama endpoint (`http://ollama:11434` in Docker) |
| `OLLAMA_MODEL` | `nemotron-3-super:cloud` | Model to use |
| `OLLAMA_API_KEY` | — | Required for cloud models |

### Whisper (Speech-to-Text)

| Variable | Default | Description |
|----------|---------|-------------|
| `WHISPER_HOST` | `http://localhost:9000` | Whisper endpoint (`http://whisper:9000` in Docker) |
| `WHISPER_API_KEY` | `see-whisper-secret-key-2026` | Bearer token for Whisper auth |

### Search

| Variable | Default | Description |
|----------|---------|-------------|
| `TAVILY_API_KEY` | — | Tavily search API key (recommended) |
| `GOOGLE_SEARCH_API_KEY` | — | Google Custom Search API key (fallback) |
| `GOOGLE_CSE_ID` | — | Google Custom Search Engine ID |

### Application

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | `development` / `staging` / `production` |
| `SERVICE_ROLE` | `api-gateway` | `api-gateway` / `worker-engine` |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS origins (comma-separated) |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Frontend API base URL |
| `NEXT_PUBLIC_STREAM_URL` | `http://localhost:8000` | Frontend SSE base URL |

### Docker Port Overrides

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_EXTERNAL_PORT` | `5432` | Host port for PostgreSQL |
| `REDIS_EXTERNAL_PORT` | `6379` | Host port for Redis |
| `API_EXTERNAL_PORT` | `8000` | Host port for API gateway |
| `FRONTEND_EXTERNAL_PORT` | `3000` | Host port for frontend |
| `OLLAMA_EXTERNAL_PORT` | `11435` | Host port for Ollama |
| `WHISPER_EXTERNAL_PORT` | `9000` | Host port for Whisper |

---

## API Reference

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Register (email + password) → 201 |
| `POST` | `/api/v1/auth/login` | Login → JWT access + refresh tokens |
| `POST` | `/api/v1/auth/refresh` | Refresh JWT session |
| `GET` | `/api/v1/auth/me` | Get authenticated user profile |

### Projects

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/projects` | Create project workspace → 201 |
| `GET` | `/api/v1/projects` | List user projects (offset/limit) |
| `GET` | `/api/v1/projects/{id}` | Get project details |
| `DELETE` | `/api/v1/projects/{id}` | Delete project + cascade results |

### Pipeline

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/generator/run` | Trigger compilation pipeline → 202 |
| `POST` | `/api/v1/generator/enhance` | AI-powered idea enhancement |
| `GET` | `/api/v1/streams/{session_id}` | SSE stream for pipeline progress |

### Intake Consultation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/intake/start` | Start consultation with raw idea |
| `POST` | `/api/v1/intake/message` | Submit answer to follow-up question |
| `POST` | `/api/v1/intake/finalize` | Finalize and create project |

### Blueprints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/blueprints/{project_id}` | Get compiled blueprint |
| `GET` | `/api/v1/blueprints/shared/{token}` | Get blueprint via share link |

### Exports

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/exports/pdf/{project_id}` | Export as PDF |
| `POST` | `/api/v1/exports/deck/{project_id}` | Export as PowerPoint deck |
| `POST` | `/api/v1/exports/share-link/{project_id}` | Generate public share URL |

### Conversation Intelligence

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/meetings` | Create meeting session |
| `GET` | `/api/v1/meetings` | List user meetings |
| `GET` | `/api/v1/meetings/{id}` | Get meeting details |
| `PATCH` | `/api/v1/meetings/{id}` | Update meeting metadata |
| `DELETE` | `/api/v1/meetings/{id}` | Delete meeting + transcripts |
| `POST` | `/api/v1/meetings/{id}/transcript` | Upload complete transcript |
| `POST` | `/api/v1/meetings/{id}/transcript/segments` | Upload streaming segments |
| `POST` | `/api/v1/meetings/{id}/transcript/audio` | Upload audio for transcription |
| `GET` | `/api/v1/meetings/{id}/transcript` | Fetch transcript |
| `POST` | `/api/v1/meetings/{id}/report/generate` | Generate AI report |
| `GET` | `/api/v1/meetings/{id}/report` | Fetch AI report |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health/liveness` | Liveness probe |
| `GET` | `/api/v1/health/readiness` | Readiness probe (verifies DB + Redis) |

### Documentation

| Endpoint | Description |
|----------|-------------|
| `/docs` | Swagger UI (interactive API explorer) |
| `/redoc` | ReDoc (alternative API docs) |

---

## Database Schema

### Core Tables

| Table | Key Columns | Relationships |
|-------|-------------|---------------|
| `users` | id, email, hashed_password, role, is_active | → projects, audit_logs |
| `projects` | id, user_id, title, description, industry, region | → all result tables, blueprint, versions |
| `project_versions` | id, project_id, version_label, snapshot_data (JSONB) | → project |

### Result Tables (all share: project_id, data JSONB, hash_checksum)

| Table | Stage |
|-------|-------|
| `dna_results` | 1 — Business DNA |
| `feature_results` | 2 — Product Features |
| `roadmap_results` | 3 — Delivery Roadmap |
| `team_results` | 4 — Team Structure |
| `swot_results` | 5 — SWOT Analysis |
| `cost_results` | 6 — Financial Model |
| `legal_compliance_results` | 8 — Legal & Compliance |

### Blueprint & Workflow

| Table | Key Columns |
|-------|-------------|
| `blueprints` | project_id, data (JSONB), health_score, version |
| `generation_sessions` | project_id, status, correlation_id, current_stage, progress_percentage, cache_hits, cache_misses |
| `workflow_events` | session_id, event_type, stage, payload (JSONB) |

### Meeting Intelligence

| Table | Key Columns |
|-------|-------------|
| `meetings` | user_id, project_id, title, status, duration_seconds, speaker_count, language |
| `meeting_segments` | meeting_id, speaker, text, start_time_ms, end_time_ms, confidence |
| `transcripts` | meeting_id, raw_text, word_count, language_detected |
| `meeting_reports` | meeting_id, status, executive_summary, key_points, decisions, action_items, ... |

### Analytics & Audit

| Table | Key Columns |
|-------|-------------|
| `analytics_logs` | project_id, module_name, prompt_tokens, completion_tokens, latency_ms, estimated_cost_usd |
| `audit_logs` | user_id, action, resource_type, resource_id, data (JSONB) |

---

## Running Tests

### Backend tests

```bash
cd backend
pytest -v
```

### Agent mesh tests (74 tests)

```bash
pytest tests/agents/ -v
```

### Test categories

| Category | Files | What's Tested |
|----------|-------|---------------|
| Types | `test_types.py` | Pydantic model validation, defaults, boundaries |
| Tools | `test_tools.py` | Tool registry, search, DB, calculations, safe_execute |
| Context Bus | `test_context_bus.py` | Publish/subscribe, timeout, observation retrieval |
| Base Agent | `test_base.py` | Safe run, budget enforcement, tool errors, observation flow |
| Workflows | `test_workflows.py` | Sequential, parallel (merge strategies), debate (convergence, non-convergence) |
| DNA E2E | `test_dna_e2e.py` | Researcher, Analyst, Reviewer with mocked tools |
| Worker Integration | `test_worker_integration.py` | Feature flag routing, module registration |

Tests use mocked LLM responses and in-memory databases. No external services required.

---

## Troubleshooting

### Pipeline fails with "Module not registered"
- Ensure `worker-engine` container is running: `docker compose logs worker-engine`
- Check `worker/tasks.py` has all 8 modules registered

### Search returns "No search provider configured"
- Set `TAVILY_API_KEY` in `.env` (free at https://tavily.com)
- Or set both `GOOGLE_SEARCH_API_KEY` and `GOOGLE_CSE_ID`
- Search is optional — stages degrade gracefully without it

### Database connection refused
- Verify PostgreSQL is running: `pg_isready`
- Check `POSTGRES_HOST` matches your setup (`localhost` for local, `postgres` for Docker)
- **Common issue**: Local PostgreSQL may conflict with Docker on port 5432. Stop local PostgreSQL or change Docker port

### Redis connection refused
- Verify Redis is running: `redis-cli ping`
- Check `REDIS_HOST` matches your setup

### Frontend can't reach backend
- Verify `NEXT_PUBLIC_API_URL` points to `http://localhost:8000` (local) or `http://api-gateway:8000` (Docker)
- Check CORS: ensure your frontend origin is in `ALLOWED_ORIGINS`

### Whisper transcription fails
- Verify Whisper container is running: `docker compose logs see-whisper`
- Check `WHISPER_API_KEY` is set (default: `see-whisper-secret-key-2026`)
- Ensure audio file format is supported (webm, mp4, mp3, wav, ogg, m4a, flac)

### Ollama model not found
- The default model `nemotron-3-super:cloud` is proxied to NVIDIA cloud
- For local models, pull first: `docker exec see-ollama ollama pull llama3`
- Set `OLLAMA_MODEL` to the pulled model name

### Agent mesh not activating
- All stages default to `enabled=False` in `backend/agents/config.py`
- Flip `enabled=True` for the desired stage(s)
- Worker must restart to pick up config changes: `docker compose restart worker-engine`

### Port 5432 conflict (Windows)
- Local PostgreSQL 18 may be running alongside Docker
- Stop the local service: `net stop postgresql-x64-18`
- Or remap Docker port in `.env`: `POSTGRES_EXTERNAL_PORT=5433`

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes and add tests
4. Run the full test suite: `pytest tests/agents/ -v && cd backend && pytest -v`
5. Ensure Docker builds: `docker compose up -d --build`
6. Submit a pull request

### Code Conventions

- **Backend**: Python 3.13+, type hints, async/await, Pydantic V2, SQLAlchemy 2.0 async
- **Frontend**: TypeScript, React 19, Tailwind CSS, Zustand stores, TanStack Query
- **Tests**: pytest + pytest-asyncio, mocked external services, 74 agent mesh tests
- **Git**: Conventional commits, feature branches, no direct commits to `main`

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
