# AI Venture Studio — Pipeline Architecture

## Overview

The pipeline has evolved from an 8-stage startup analyzer into a **14-stage evidence-driven AI Venture Studio** that produces investor-grade, execution-ready outputs with full explainability.

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CORE PIPELINE (Stages 1-8)                      │
├─────────────────────────────────────────────────────────────────────┤
│  1. DNA  →  2. Features  →  3. Roadmap  →  4. Team                 │
│                        ↓                                            │
│               5. SWOT + 6. Cost (parallel)                          │
│                        ↓                                            │
│          7. Blueprint + 8. Legal Compliance (parallel)              │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                 INTELLIGENCE PIPELINE (Stages 9-14)                 │
│                    (all run in parallel)                             │
├─────────────────────────────────────────────────────────────────────┤
│  9. Competitive Moat    │  12. Investment Committee                 │
│  10. Stress Test        │  13. Product Execution                    │
│  11. Financial Intel    │  14. Global Expansion                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Total: 132 tests passing (74 core + 58 intelligence)**

---

## Evidence & Confidence Infrastructure

Every claim, score, and recommendation is backed by structured evidence.

### EvidenceSource
```python
class EvidenceSource(BaseModel):
    source_name: str        # "Statista", "Crunchbase", "Gartner"
    source_url: str         # URL or reference ID
    source_type: Literal["WEB_SEARCH", "DATABASE", "LLM_KNOWLEDGE",
                         "USER_INPUT", "CALCULATION", "API"]
    retrieval_date: str     # ISO date when retrieved
    snippet: str            # Relevant excerpt (max 500 chars)
    relevance_score: float  # 0.0-1.0
```

### ConfidenceScore
```python
class ConfidenceScore(BaseModel):
    score: float                        # 0-100 percentage
    evidence: list[EvidenceSource]      # Supporting citations
    missing_information: list[str]      # What would increase confidence
    assumptions: list[str]              # Key assumptions made
    alternative_interpretations: list[str]  # Other readings of the data
```

### ExplainableDecision
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

7 specialized agents produce independent assessments. The Judge synthesizes them.

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

### Decision Pipeline
```python
result = await run_decision_pipeline(
    context={...},          # Industry, product, features, etc.
    evidence=[...],         # Pre-gathered evidence
    stages=["Market Analyst", "Financial Analyst"],  # Optional filter
)
# result["opinions"]  → list of 7 AgentOpinion dicts
# result["verdict"]   → JudgeVerdict with final assessment
```

---

## 6 Intelligence Modules

### 9. Competitive Moat Analysis

Replaces simple SWOT thinking with deep moat assessment across 10 dimensions:

| Moat Type | What it measures |
|-----------|-----------------|
| Network Effects | Product value increases with users |
| Data Moat | Proprietary data improves the product |
| Brand Moat | Brand recognition/trust competitors lack |
| Technology Moat | Proprietary technology hard to replicate |
| Switching Costs | Cost for customers to switch |
| Economies of Scale | Cost advantages at scale |
| Regulatory Advantage | Licenses, patents, regulations |
| Distribution Advantage | Unique customer access |
| Community Advantage | Community/network lock-in |
| AI/Data Flywheel | Self-reinforcing improvement loop |

Each dimension scored with:
- **Strength**: 0-10 (none → fortress)
- **Difficulty to Copy**: TRIVIAL → NEAR_IMPOSSIBLE
- **Time to Copy**: months for well-funded competitor
- **Cost to Copy**: USD estimate

### 10. Market Stress Testing

Simulates 10+ negative scenarios with full impact assessment:

| Scenario | Impact | Probability | Recovery |
|----------|--------|-------------|----------|
| Large competitor enters | SEVERE | 0.3 | Differentiate on niche |
| Open-source alternative | MODERATE | 0.4 | Build community moat |
| Price war | MODERATE | 0.3 | Emphasize value, not price |
| Regulatory change | SEVERE | 0.2 | Compliance roadmap |
| Economic recession | CATASTROPHIC | 0.25 | Cut burn, focus on retention |
| Customer acquisition halves | SEVERE | 0.35 | Channel diversification |
| Infrastructure cost surge | MODERATE | 0.2 | Optimize, negotiate |
| Funding freeze | CATASTROPHIC | 0.2 | Path to profitability |
| Key person departure | SEVERE | 0.3 | Knowledge documentation |

Each scenario includes: early warning signs, pre-positioning actions, recovery plan.

### 11. Financial Intelligence Engine

Investor-grade financial analysis:

**Core Metrics:**
- ARR, MRR (with growth assumptions)
- Gross Margin, CAC, LTV, LTV:CAC Ratio
- Burn Rate, Burn Multiple, Payback Period
- Cash Runway, Break-even Month

**Unit Economics:**
- CAC by channel (organic, paid, referral)
- LTV with churn assumptions
- Contribution margin, expansion rate

**Projections:**
- Monthly for Year 1, Quarterly for Years 2-3
- Revenue, costs, profit, cash balance, customers

**Scenarios:**
- Best Case (20% probability)
- Base Case (60% probability)
- Worst Case (20% probability)

**Valuation:**
- Revenue multiple approach
- Comparable company analysis

### 12. Investment Committee Simulation

Realistic VC review with 5 partners:

| Partner | Focus | Personality |
|---------|-------|-------------|
| Market-focused | Market size & timing | Growth-oriented |
| Technical | Technology moat | Deep diligence |
| Financial | Unit economics | Conservative |
| Growth | Scalability | Aggressive |
| Risk-averse | Downside protection | Skeptical |

**Outputs:**
- Individual votes (INVEST / PASS / CONDITIONAL)
- Term sheet (valuation, equity, board seats, protective provisions)
- Due diligence checklist (8-12 items)
- Investment thesis, reasons to invest/not, fatal risks

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

All outputs synchronized with features and roadmap from earlier stages.

### 14. Global Expansion Engine

Multi-country expansion analysis with 3 waves:

**Per Country:**
- Market size (USD), local competitors
- Regulatory requirements, localization needs
- Hiring costs, pricing adjustment vs US
- Tax considerations, GTM strategy
- Country-specific risks, expansion priority (TIER_1/2/3)

**Expansion Waves:**
- Wave 1 (0-12 months): Easiest, highest ROI
- Wave 2 (12-24 months): Moderate complexity
- Wave 3 (24-36 months): Most challenging, high potential

---

## Pipeline Integration

### Orchestrator Changes

The `WorkflowOrchestrator` now manages 14 stages:

```python
STAGES_ORDER = [
    # Core pipeline (stages 1-8)
    "dna", "features", "roadmap", "team", "swot", "cost",
    "blueprint", "legal_compliance",
    # Intelligence pipeline (stages 9-14)
    "competitive_moat", "stress_test", "financial_intelligence",
    "investment_committee", "product_execution", "global_expansion",
]
```

### Parallel Execution Groups

```
Group 1: [dna]
Group 2: [features]
Group 3: [roadmap]
Group 4: [team]
Group 5: [swot, cost]              ← parallel
Group 6: [blueprint, legal]        ← parallel
Group 7: [moat, stress, finance,   ← all 6 in parallel
           IC, product, expansion]
```

### Graceful Degradation

Intelligence modules are **non-critical** — if any fails, the core pipeline continues. This ensures the 8 core stages always complete even if intelligence modules encounter issues.

### Context Propagation

Full structured data flows between all stages:
- DNA scores, competitor landscape, key risks → all downstream
- Features with user stories, effort estimates, dependencies → roadmap, team, cost
- Roadmap phases with acceptance criteria, feature IDs → team, cost, blueprint
- Team with equity, compensation, hiring risks → cost, blueprint
- SWOT with mitigations, severity scores → blueprint
- Cost with feature breakdowns, phase costs → blueprint

---

## Module Summary

| Module | Stage | Input Stages | Output |
|--------|-------|--------------|--------|
| DNA | 1 | — | Market analysis, scores, competitors |
| Features | 2 | DNA | 5-20 features with user stories |
| Roadmap | 3 | DNA, Features | 3-8 phases, 15-40 tasks |
| Team | 4 | DNA, Roadmap | 3-12 roles with equity/salary |
| SWOT | 5 | DNA, Features, Roadmap | Threats with severity, mitigations |
| Cost | 6 | Features, Roadmap, Team | Feature/phase cost breakdowns |
| Blueprint | 7 | All core | Executive summary, health, next steps |
| Legal | 8 | Blueprint | Compliance documents |
| Competitive Moat | 9 | All core | 10-moat assessment |
| Stress Test | 10 | All core + moat | 10+ scenario simulations |
| Financial Intel | 11 | All core | Unit economics, projections, valuation |
| Investment Committee | 12 | All core + finance | VC review, term sheet, DD checklist |
| Product Execution | 13 | DNA, Features, Roadmap | PRDs, architecture, sprints |
| Global Expansion | 14 | DNA, Features, Roadmap, Cost | Multi-country expansion waves |

---

## Test Coverage

```
tests/
├── agents/          74 tests — agent mesh, tools, workflows, types
├── intelligence/    58 tests — all new modules
│   ├── test_evidence_types.py       (10 tests)
│   ├── test_multi_agent.py          (18 tests)
│   ├── test_competitive_moat.py     (5 tests)
│   ├── test_stress_test.py          (5 tests)
│   ├── test_financial_intelligence.py (6 tests)
│   ├── test_investment_committee.py  (4 tests)
│   ├── test_product_execution.py     (7 tests)
│   └── test_global_expansion.py      (6 tests)
```

**Total: 132 tests, all passing**
