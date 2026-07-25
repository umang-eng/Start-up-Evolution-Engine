<div align="center">

# Start-up Evolution Engine

**An AI-powered venture studio that transforms raw startup ideas into investor-grade, execution-ready blueprints through a 14-stage evidence-driven pipeline with multi-agent intelligence, competitive moat analysis, and investment committee simulation.**

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
- [14-Stage Pipeline](#14-stage-pipeline)
- [Evidence & Confidence System](#evidence--confidence-system)
- [Multi-Agent Decision System](#multi-agent-decision-system)
- [Intelligence Modules](#intelligence-modules)
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

### Core Pipeline (Stages 1-8)
1. **Extracts** structured business DNA — category, business model, revenue streams, USP, and six strategic scores with real-time market grounding
2. **Generates** 5-20 product features with MoSCoW prioritization, user stories, effort estimates, and dependency graphs
3. **Builds** a phased delivery roadmap with 15-40 tasks, acceptance criteria, risk levels, and critical path identification
4. **Designs** an org chart with 3-12 roles, equity structures, compensation packages, and hiring sequences
5. **Analyzes** a SWOT matrix with threat severity scoring (impact × probability) and founder action items
6. **Projects** financial models with feature-level cost breakdowns, phase costs, and funding runway targets
7. **Compiles** an investor-ready Blueprint with competitive analysis, market positioning, and next steps
8. **Produces** a Legal & Compliance document pack with government grants, registration requirements, and regulatory directories

### Intelligence Pipeline (Stages 9-14)
9. **Assesses** competitive moats across 10 dimensions (network effects, data moat, brand, technology, switching costs, economies of scale, regulatory, distribution, community, AI flywheel) with difficulty/time/cost estimates
10. **Stress tests** against 10+ scenarios (competitor entry, open-source alternatives, price wars, regulatory changes, recession, funding freeze) with mitigation strategies and recovery plans
11. **Generates** investor-grade financials — unit economics, projections (monthly Y1, quarterly Y2-3), best/base/worst scenarios, valuation, and funding requirements
12. **Simulates** an Investment Committee with 5 VC partners voting on the deal, producing term sheets, due diligence checklists, and investment theses
13. **Creates** product execution assets — PRDs, 15-25 user stories, technical architecture, sprint backlogs, release plans, QA and deployment strategies
14. **Plans** global expansion with multi-country waves, regulatory analysis, localization needs, hiring costs, and GTM strategies per market

Every stage uses **structured Pydantic output schemas** validated against the LLM response. Every score includes **confidence, evidence, and uncertainty explanations**. A **deterministic SHA-256 cache** skips LLM calls when inputs haven't changed. **Real-time web search** grounds analysis in live market facts.

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
       +-------------+   +-------------+   +----+--------/
                                                 |
                                         +-------v--------+
                                         |  14-Stage       |
                                         |  Pipeline       |
                                         |  Orchestrator   |
                                         +-------+--------+
                                                 |
                              +------------------+------------------+
                              |                  |                  |
                    +---------v--------+ +-------v-------+ +-------v-------+
                    |  Core Pipeline   | | Intelligence  | | Agent Mesh    |
                    |  (8 stages)      | | Pipeline      | | (7 agents +   |
                    |  DNA→Blueprint   | | (6 modules)   | |  Judge)       |
                    +------------------+ +---------------+ +---------------+
                              |                  |                  |
                    +---------v--------+ +-------v-------+ +-------v-------+
                    |  LLM (Gemini)    | | Evidence      | | Search        |
                    |  Structured JSON  | | Collector     | | (Tavily/Google)|
                    +------------------+ +---------------+ +---------------+
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
│   ├── modules/
│   │   ├── dna/                  # Stage 1: Business DNA extraction
│   │   ├── features/             # Stage 2: Product feature generation
│   │   ├── roadmap/              # Stage 3: Delivery roadmap
│   │   ├── team/                 # Stage 4: Org chart + hiring
│   │   ├── swot/                 # Stage 5: SWOT + market data
│   │   ├── cost/                 # Stage 6: Financial model
│   │   ├── blueprint/            # Stage 7: Investor blueprint
│   │   ├── legal_compliance/     # Stage 8: Legal & compliance
│   │   ├── evidence/             # Evidence & confidence infrastructure
│   │   │   ├── types.py          # EvidenceSource, ConfidenceScore, ExplainableDecision
│   │   │   ├── collector.py      # Web search evidence gathering
│   │   │   ├── multi_agent.py    # 7 specialized agents + Judge
│   │   │   ├── pipeline.py       # Decision pipeline orchestrator
│   │   │   └── agents/           # Agent implementations
│   │   │       ├── market_analyst.py
│   │   │       ├── product_strategist.py
│   │   │       ├── technical_architect.py
│   │   │       ├── financial_analyst.py
│   │   │       ├── gtm_strategist.py
│   │   │       ├── risk_analyst.py
│   │   │       ├── devils_advocate.py
│   │   │       └── judge.py
│   │   ├── competitive_moat/     # Stage 9: Competitive moat analysis
│   │   ├── stress_test/          # Stage 10: Market stress testing
│   │   ├── financial_intelligence/ # Stage 11: Financial intelligence engine
│   │   ├── investment_committee/ # Stage 12: Investment committee simulation
│   │   ├── product_execution/    # Stage 13: Product execution engine
│   │   ├── global_expansion/     # Stage 14: Global expansion engine
│   │   ├── meeting_health/       # Meeting health analysis (9 dimensions)
│   │   ├── meeting_timeline/     # Timeline event extraction
│   │   └── meeting_sync/         # Blueprint synchronization engine
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
│   └── requirements.txt
├── tests/
│   ├── agents/                   # Agent mesh unit tests (74 tests)
│   │   ├── test_types.py
│   │   ├── test_tools.py
│   │   ├── test_context_bus.py
│   │   ├── test_base.py
│   │   ├── test_workflows.py
│   │   ├── test_dna_e2e.py
│   │   └── test_worker_integration.py
│   └── intelligence/             # Intelligence pipeline tests (58 tests)
│       ├── test_evidence_types.py
│       ├── test_multi_agent.py
│       ├── test_competitive_moat.py
│       ├── test_stress_test.py
│       ├── test_financial_intelligence.py
│       ├── test_investment_committee.py
│       ├── test_product_execution.py
│       └── test_global_expansion.py
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

## 14-Stage Pipeline

The pipeline runs stages in a dependency-aware order with parallel execution:

```
Core Pipeline (Stages 1-8)
──────────────────────────
[dna] → [features] → [roadmap] → [team] → [swot] + [cost] → [blueprint] + [legal]
                                                          (parallel)     (parallel)

Intelligence Pipeline (Stages 9-14) — all run in parallel after core completes
─────────────────────────────────────────────────────────────────────────────
[competitive_moat] + [stress_test] + [financial_intelligence]
[investment_committee] + [product_execution] + [global_expansion]
```

### Core Pipeline Stages

| # | Stage | Module | Output Schema | Parallel | Description |
|---|-------|--------|---------------|----------|-------------|
| 1 | `dna` | `DNAModule` | `DNAOutput` | No | Business category, model, revenue streams, USP, 6 strategic scores with real-time market grounding |
| 2 | `features` | `FeatureExtractorModule` | `FeatureExtractorOutput` | No | 5-20 features with MoSCoW priority, user stories, effort estimates (XS-XL), business value, success metrics |
| 3 | `roadmap` | `RoadmapGeneratorModule` | `RoadmapOutput` | No | 3-8 phases, 15-40 tasks with acceptance criteria, risk levels, critical path, feature IDs |
| 4 | `team` | `TeamGeneratorModule` | `TeamOutput` | No | 3-12 roles with equity, compensation structure, cofounder recommendation, hiring risks |
| 5 | `swot` | `SWOTBuilderModule` | `SWOTOutput` | Yes | SWOT matrix with threat severity (impact × probability), competitor positioning, market validation |
| 6 | `cost` | `CostEstimatorModule` | `CostOutput` | Yes | Feature-level cost breakdown, phase costs, contingency, break-even analysis, funding scenarios |
| 7 | `blueprint` | `BlueprintComposerModule` | `BlueprintOutput` | No | Competitive analysis, market positioning, investment readiness checklist, next steps, expansion opportunities |
| 8 | `legal_compliance` | `LegalComplianceModule` | `LegalComplianceOutput` | No | Funding sources, registration requirements, compliance directories, data protection |

### Intelligence Pipeline Stages

| # | Stage | Module | Description |
|---|-------|--------|-------------|
| 9 | `competitive_moat` | `CompetitiveMoatModule` | 10-moat analysis: network effects, data, brand, technology, switching costs, scale, regulatory, distribution, community, AI flywheel. Each scored with difficulty/time/cost to copy |
| 10 | `stress_test` | `StressTestModule` | 10+ scenarios: competitor entry, open-source, price war, regulation, recession, acquisition changes, infrastructure costs, funding freeze. Each with impact, probability, mitigation, recovery |
| 11 | `financial_intelligence` | `FinancialIntelligenceModule` | Unit economics, monthly Y1 + quarterly Y2-3 projections, best/base/worst scenarios, valuation, funding requirements |
| 12 | `investment_committee` | `InvestmentCommitteeModule` | 5 VC partners with individual votes, term sheet, due diligence checklist, investment thesis |
| 13 | `product_execution` | `ProductExecutionModule` | PRDs, 15-25 user stories, technical architecture, sprint backlogs, release plan, QA/deployment strategy |
| 14 | `global_expansion` | `GlobalExpansionModule` | Multi-country waves with market size, regulations, localization, pricing, hiring, GTM per market |

---

## Evidence & Confidence System

Every claim, score, and recommendation is backed by structured evidence.

### Core Types

```python
class EvidenceSource(BaseModel):
    source_name: str        # "Statista", "Crunchbase", "Gartner"
    source_url: str         # URL or reference ID
    source_type: Literal["WEB_SEARCH", "DATABASE", "LLM_KNOWLEDGE",
                         "USER_INPUT", "CALCULATION", "API"]
    retrieval_date: str     # ISO date when retrieved
    snippet: str            # Relevant excerpt (max 500 chars)
    relevance_score: float  # 0.0-1.0

class ConfidenceScore(BaseModel):
    score: float                        # 0-100 percentage
    evidence: list[EvidenceSource]      # Supporting citations
    missing_information: list[str]      # What would increase confidence
    assumptions: list[str]              # Key assumptions made
    alternative_interpretations: list[str]  # Other readings of the data

class ExplainableDecision(BaseModel):
    decision: str                       # The recommendation
    rationale: str                      # Why this was chosen
    evidence: list[EvidenceSource]      # Supporting citations
    assumptions: list[str]              # Key assumptions
    alternatives_rejected: list[str]    # What was considered and rejected
    what_would_change_it: list[str]     # New info that would change decision
    confidence: float                   # 0-100
```

### Explainability

Every recommendation answers:
- **Why was this chosen?** — rationale citing specific evidence
- **Which evidence supports it?** — linked EvidenceSource list
- **Which assumptions were made?** — explicit assumption list
- **What alternatives were rejected?** — with reasons
- **What would change the recommendation?** — new information triggers

### Evidence Collection

The `collector.py` module gathers evidence from multiple sources:
- **Market data**: size, growth, CAGR, trends
- **Competitor intelligence**: funding, features, pricing
- **Financial benchmarks**: CAC, LTV, margins by stage/industry
- **Regulatory data**: compliance requirements by country

---

## Multi-Agent Decision System

7 specialized agents produce independent assessments. The Judge synthesizes them into a consensus verdict.

### Agent Roles

| Agent | Expertise | What it assesses |
|-------|-----------|-----------------|
| **Market Analyst** | Market sizing, trends, timing | TAM/SAM/SOM, growth rate, competitive intensity, timing |
| **Product Strategist** | Product-market fit, differentiation | PMF signals, differentiation strength, feature viability |
| **Technical Architect** | Architecture, scalability | Feasibility, scalability readiness, technology risk |
| **Financial Analyst** | Unit economics, fundraising | Viability, LTV:CAC, burn rate, fundraising readiness |
| **GTM Strategist** | Channels, acquisition | Channel strategy, CAC viability, launch readiness |
| **Risk Analyst** | Risk identification, mitigation | Risk level, mitigation quality, overall risk position |
| **Devil's Advocate** | Contrarian analysis | Assumption challenges, weaknesses, contrarian case |

### Judge (Investment Committee)

The Judge:
1. Collects all 7 agent opinions
2. Identifies agreements (findings in 60%+ of agents)
3. Detects conflicts (opposing assessments)
4. Resolves conflicts by weighing agent confidence
5. Produces consensus scores (averaged from agents)
6. Assigns overall confidence with evidence

### Usage

```python
from backend.modules.evidence.pipeline import run_decision_pipeline

result = await run_decision_pipeline(
    context={
        "industry": "SaaS",
        "product_description": "CRM platform",
        "target_market": "SMBs",
        "features": [...],
        "cost_output": {...},
    },
    evidence=[...],  # Pre-gathered evidence
    stages=["Market Analyst", "Financial Analyst"],  # Optional filter
)

# result["opinions"]  → list of 7 AgentOpinion dicts
# result["verdict"]   → JudgeVerdict with final assessment
```

---

## Intelligence Modules

### 9. Competitive Moat Analysis

Replaces simple SWOT thinking with deep moat assessment across 10 dimensions:

| Moat Type | What it measures | Scoring |
|-----------|-----------------|---------|
| Network Effects | Product value increases with users | 0-10 + difficulty/time/cost to copy |
| Data Moat | Proprietary data improves the product | 0-10 + difficulty/time/cost to copy |
| Brand Moat | Brand recognition/trust competitors lack | 0-10 + difficulty/time/cost to copy |
| Technology Moat | Proprietary technology hard to replicate | 0-10 + difficulty/time/cost to copy |
| Switching Costs | Cost for customers to switch | 0-10 + difficulty/time/cost to copy |
| Economies of Scale | Cost advantages at scale | 0-10 + difficulty/time/cost to copy |
| Regulatory Advantage | Licenses, patents, regulations | 0-10 + difficulty/time/cost to copy |
| Distribution Advantage | Unique customer access | 0-10 + difficulty/time/cost to copy |
| Community Advantage | Community/network lock-in | 0-10 + difficulty/time/cost to copy |
| AI/Data Flywheel | Self-reinforcing improvement loop | 0-10 + difficulty/time/cost to copy |

### 10. Market Stress Testing

Simulates 10+ negative scenarios with full impact assessment:

| Scenario | Impact Levels | Output |
|----------|--------------|--------|
| Large competitor enters | CATASTROPHIC → NEGLIGIBLE | Mitigation + recovery plan |
| Open-source alternative | CATASTROPHIC → NEGLIGIBLE | Mitigation + recovery plan |
| Price war | CATASTROPHIC → NEGLIGIBLE | Mitigation + recovery plan |
| Regulatory change | CATASTROPHIC → NEGLIGIBLE | Mitigation + recovery plan |
| Economic recession | CATASTROPHIC → NEGLIGIBLE | Mitigation + recovery plan |
| Customer acquisition changes | CATASTROPHIC → NEGLIGIBLE | Mitigation + recovery plan |
| Infrastructure cost surge | CATASTROPHIC → NEGLIGIBLE | Mitigation + recovery plan |
| Funding freeze | CATASTROPHIC → NEGLIGIBLE | Mitigation + recovery plan |
| Key person departure | CATASTROPHIC → NEGLIGIBLE | Mitigation + recovery plan |

Each scenario includes: trigger event, probability, time to manifest, duration, affected areas, early warning signs, pre-positioning actions.

### 11. Financial Intelligence Engine

Investor-grade financial analysis:

**Core Metrics:** ARR, MRR, Gross Margin, CAC, LTV, LTV:CAC, Burn Rate, Burn Multiple, Payback Period, Cash Runway, Break-even Month

**Projections:** Monthly for Year 1, Quarterly for Years 2-3 (revenue, costs, profit, cash balance, customers)

**Scenarios:** Best Case (20%), Base Case (60%), Worst Case (20%) — each with revenue, break-even, funding required, valuation

**Valuation:** Revenue multiple approach, comparable company analysis

### 12. Investment Committee Simulation

Realistic VC review with 5 partners:

| Partner | Focus | Personality |
|---------|-------|-------------|
| Market-focused | Market size & timing | Growth-oriented |
| Technical | Technology moat | Deep diligence |
| Financial | Unit economics | Conservative |
| Growth | Scalability | Aggressive |
| Risk-averse | Downside protection | Skeptical |

**Outputs:** Individual votes (INVEST/PASS/CONDITIONAL), term sheet, due diligence checklist, investment thesis, reasons to invest/not, fatal risks

### 13. Product Execution Engine

Generates execution-ready assets:
- **Product Vision**: Clear, inspiring statement
- **PRD**: Problem, solution, users, success metrics
- **User Stories**: 15-25 stories with acceptance criteria (P0-P3)
- **Technical Architecture**: Components, data flow, API design, DB schema
- **Sprint Plan**: 6-8 sprints (2 weeks each) with goals and story allocation
- **Release Plan**: v1.0 scope, milestones, success metrics, rollback plan
- **QA Strategy**: Testing approach and automation
- **Deployment Strategy**: CI/CD, environments, monitoring

### 14. Global Expansion Engine

Multi-country expansion analysis with 3 waves:

**Per Country:** Market size, local competitors, regulatory requirements, localization needs, hiring costs, pricing adjustment, tax considerations, GTM strategy, risks, priority tier

**Expansion Waves:**
- Wave 1 (0-12 months): Easiest, highest ROI markets
- Wave 2 (12-24 months): Moderate complexity
- Wave 3 (24-36 months): Most challenging, high potential

---

## Agent Mesh System

A pluggable multi-agent system that can replace any pipeline stage's single LLM call with a team of specialized agents collaborating through structured workflows.

### Agent Roles (Pipeline Mesh)

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
- **Meeting Health Analysis** — 9-dimension scoring (Focus, Clarity, Participation, Decision Quality, Execution Readiness, Innovation, Strategic Alignment, Conflict Resolution, Time Efficiency)
- **Timeline Extraction** — automatically extracts decisions, pivots, hires, funding events, milestones, and strategy changes from meeting transcripts
- **Combined Analysis** — runs all intelligence engines in a single call for comprehensive meeting insights

### API Endpoints

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
| `GET` | `/api/v1/meetings/{id}/health` | Run 9-dimension health analysis |
| `GET` | `/api/v1/meetings/{id}/timeline` | Extract timeline events |
| `POST` | `/api/v1/meetings/{id}/analyze` | Run all intelligence engines |

---

## Real-Time Search Integration

Multiple stages perform live web searches to ground LLM outputs in verified market facts.

**Provider chain:** Tavily (primary) → Google Custom Search (fallback) → Graceful degradation

### How It Works

1. Each module builds region + industry-qualified search queries
2. Queries execute concurrently via `asyncio.gather`
3. Results are formatted into structured EvidenceSource objects
4. Evidence is injected into prompts with source citations
5. The LLM is instructed to reference specific data points

### Search Coverage

| Module | Sample Queries |
|--------|---------------|
| DNA | `"{industry} market size TAM 2026 report"`, `"{industry} competitive landscape top players"` |
| SWOT | `"{industry} market trends 2026 opportunities"`, `"government startup grants {industry}"` |
| Cost | `"{industry} startup costs {region} 2026"`, `"startup subsidy scheme {region}"` |
| Legal | `"business registration {region} 2026"`, `"data protection law {region} {industry}"` |
| Competitive Moat | `"{industry} competitive moat barriers entry defensibility"` |
| Stress Test | `"{industry} industry risks threats challenges disruption 2025"` |
| Financial | `"{industry} {stage} startup SaaS benchmarks metrics 2025"` |
| Investment Committee | `"{industry} startup valuation multiples funding rounds 2025"` |
| Global Expansion | `"{industry} international expansion global markets 2025"` |

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
- All 6 intelligence stages (9-14) run in parallel after core pipeline completes

### Connection Pooling

- PostgreSQL: 20 persistent connections + 10 overflow
- Redis: Persistent connection with keepalive
- `pool_pre_ping=True` prevents stale connections

### Prompt Compression

Context dictionaries are compressed before injection into prompts:
- Full structured data preserved between stages
- Only compressed at extreme limits (25 features, 8 phases, 15 roles, 10 items per list)
- Evidence and confidence always preserved

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
| `GET` | `/api/v1/meetings/{id}/health` | Run 9-dimension health analysis |
| `GET` | `/api/v1/meetings/{id}/timeline` | Extract timeline events |
| `POST` | `/api/v1/meetings/{id}/analyze` | Run all intelligence engines |

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

### Intelligence pipeline tests (58 tests)

```bash
pytest tests/intelligence/ -v
```

### All tests (132 tests)

```bash
pytest tests/ -v
```

### Test categories

| Category | Files | What's Tested |
|----------|-------|---------------|
| Agent Types | `test_types.py` | Pydantic model validation, defaults, boundaries |
| Agent Tools | `test_tools.py` | Tool registry, search, DB, calculations, safe_execute |
| Context Bus | `test_context_bus.py` | Publish/subscribe, timeout, observation retrieval |
| Base Agent | `test_base.py` | Safe run, budget enforcement, tool errors, observation flow |
| Workflows | `test_workflows.py` | Sequential, parallel (merge strategies), debate (convergence, non-convergence) |
| DNA E2E | `test_dna_e2e.py` | Researcher, Analyst, Reviewer with mocked tools |
| Worker Integration | `test_worker_integration.py` | Feature flag routing, module registration |
| Evidence Types | `test_evidence_types.py` | EvidenceSource, ConfidenceScore, ExplainableDecision, ScenarioAnalysis |
| Multi-Agent | `test_multi_agent.py` | All 7 agents, Judge deliberation, conflict detection, pipeline |
| Competitive Moat | `test_competitive_moat.py` | Moat dimensions, scoring, module initialization |
| Stress Test | `test_stress_test.py` | Scenario creation, categories, output validation |
| Financial Intel | `test_financial_intelligence.py` | Unit economics, projections, scenarios, module fallback |
| Investment Committee | `test_investment_committee.py` | Committee members, votes, term sheet, module fallback |
| Product Execution | `test_product_execution.py` | User stories, sprints, architecture, release plan |
| Global Expansion | `test_global_expansion.py` | Countries, waves, tiers, expansion output |

Tests use mocked LLM responses and in-memory databases. No external services required.

---

## Troubleshooting

### Pipeline fails with "Module not registered"
- Ensure `worker-engine` container is running: `docker compose logs worker-engine`
- Check `worker/tasks.py` has all modules registered

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

### Intelligence pipeline failures
- Intelligence modules are non-critical — core pipeline continues if they fail
- Check logs: `docker compose logs worker-engine | grep -i "competitive_moat\|stress_test\|financial"`
- Intelligence modules require Gemini API key for LLM generation
- Evidence collection requires Tavily or Google Search API key

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes and add tests
4. Run the full test suite: `pytest tests/ -v`
5. Ensure Docker builds: `docker compose up -d --build`
6. Submit a pull request

### Code Conventions

- **Backend**: Python 3.13+, type hints, async/await, Pydantic V2, SQLAlchemy 2.0 async
- **Frontend**: TypeScript, React 19, Tailwind CSS, Zustand stores, TanStack Query
- **Tests**: pytest + pytest-asyncio, mocked external services, 132 tests total
- **Git**: Conventional commits, feature branches, no direct commits to `main`

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
