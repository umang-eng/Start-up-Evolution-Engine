# Pipeline Quality Improvement Analysis

## Critical Weaknesses Found

After analyzing every prompt, schema, context assembly, and search integration across all 8 stages, here are the structural issues dragging down output quality.

---

## Step 1: DNA Stage Has No Market Grounding

**Problem:** DNA is the foundation everything else builds on, yet it uses zero web search. Scores for `market_opportunity`, `competition`, and `risk_factor` are pure LLM guessing. The `notes` field is hardcoded to `"None"` — there's no way to pass founder-provided context.

**Impact:** Every downstream stage inherits fabricated market data. Features are designed for a non-existent market. Cost projections ignore real competitor pricing.

**Fix:**
- Add 2 search queries: `"{industry} market size 2026"` and `"{industry} competitive landscape top players"`
- Inject results as `[REAL-TIME_MARKET_DATA]` block (same pattern as SWOT/Cost)
- Replace hardcoded `"None"` notes with `project.description` as additional context
- Add a `market_size_estimate: str` field to `DNAOutput` for downstream use
- Add a `competitor_landscape: list[str]` field (top 3-5 competitors)

**Schema change:**
```python
class DNAOutput(BaseModel):
    # ... existing fields ...
    market_size_estimate: str          # NEW: "TAM ~$Xb, SAM ~$Yb"
    competitor_landscape: list[str]    # NEW: top 3-5 competitors
    key_risks: list[str]               # NEW: top 3 risks with brief rationale
```

---

## Step 2: Features Stage Is Too Rigid and Shallow

**Problem:** Exactly 5 features (2 Core, 1 Advanced, 1 Future, 1 Competitive) regardless of startup complexity. Features have no user stories, no acceptance criteria, no effort estimation beyond LOW/MEDIUM/HIGH. No non-functional requirements (performance, security, scalability).

**Impact:** A complex enterprise SaaS and a simple mobile app get the same 5-feature structure. Investors see toy-level planning.

**Fix:**
- Scale features by complexity: DNA `complexity` score determines feature count (5-12)
- Add `user_stories: list[str]` to `FeatureItem` (who + what + why)
- Add `effort_estimate: Literal["XS","S","M","L","XL"]` alongside complexity
- Add `nfr_requirements: list[str]` to `FeatureExtractorOutput` (non-functional requirements)
- Add `technical_risks: list[str]` to flag known implementation risks

**Schema change:**
```python
class FeatureItem(BaseModel):
    # ... existing fields ...
    user_stories: list[str]                    # NEW: "As a [user], I want [X] so that [Y]"
    effort_estimate: Literal["XS","S","M","L","XL"]  # NEW: engineering effort
    success_metrics: list[str]                 # NEW: how to measure this feature works

class FeatureExtractorOutput(BaseModel):
    # ... existing fields ...
    nfr_requirements: list[str]                # NEW: non-functional requirements
    technical_risks: list[str]                 # NEW: known implementation risks
```

---

## Step 3: Roadmap Tasks Are Too Sparse and Lack Risk Awareness

**Problem:** Only 2 tasks per phase (12 total). No risk assessment per task. No resource estimation. Phase names are hardcoded to 6 fixed names — inflexible for different project types. Tasks have no acceptance criteria.

**Impact:** A 12-task roadmap for a 6-month project is unrealistic. No way to identify critical path or bottleneck risks.

**Fix:**
- Scale tasks: 3-4 per phase (18-24 total) based on complexity
- Add `risk_level: Literal["LOW","MEDIUM","HIGH"]` to `RoadmapTask`
- Add `acceptance_criteria: list[str]` to `RoadmapTask`
- Add `resource_requirements: str` (e.g., "1 senior dev, 2 weeks")
- Add `critical_path: bool` flag to identify bottleneck tasks
- Allow phase names to be dynamic (keep the 6 as suggestions, not constraints)

**Schema change:**
```python
class RoadmapTask(BaseModel):
    # ... existing fields ...
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]   # NEW
    acceptance_criteria: list[str]                   # NEW
    resource_requirements: str                       # NEW: "1 senior dev, 2 weeks"
    is_critical_path: bool = False                   # NEW

class RoadmapOutput(BaseModel):
    # ... existing fields ...
    total_estimated_weeks: int                       # NEW
    critical_path: list[str]                         # NEW: task IDs on critical path
    key_dependencies: list[str]                      # NEW: cross-phase dependency risks
```

---

## Step 4: Team Stage Ignores Market Reality and Has Dead Variables

**Problem:** Only 3-4 roles regardless of startup stage. No equity structure. No remote/onsite cost adjustment. The `features` variable is passed to the prompt but never used (dead code). No consideration for cofounder vs hire decisions.

**Impact:** Team recommendations feel generic. Salary estimates don't reflect actual market rates for the region.

**Fix:**
- Scale roles: 4-8 based on DNA complexity and roadmap phases
- Add `compensation_structure: Literal["CASH_ONLY","EQUITY_HEAVY","BALANCED"]` to team output
- Add `equity_pool_percent: float` field for equity allocation
- Add `remote_friendly: bool` flag affecting salary estimates
- Remove unused `features` variable from context assembly
- Add `cofounder_recommendation: str` field (when to seek cofounders)

**Schema change:**
```python
class TeamOutput(BaseModel):
    # ... existing fields ...
    compensation_structure: Literal["CASH_ONLY", "EQUITY_HEAVY", "BALANCED"]  # NEW
    equity_pool_percent: float                                                  # NEW
    cofounder_recommendation: str                                               # NEW
    key_hiring_risks: list[str]                                                 # NEW
    total_monthly_payroll_usd: float                                            # NEW: for cross-validation with Cost
```

---

## Step 5: SWOT Threats Lack Quantified Impact and Search Results Are Raw

**Problem:** `ThreatMitigation.severity` validator is a no-op (just returns `v`). Threats are vague strings, not structured risk items. Search results are injected raw — the LLM has to parse formatted text, leading to inconsistent引用. No competitor-specific threats.

**Impact:** SWOT reads like a generic textbook, not a data-driven analysis. Mitigations are hand-wavy.

**Fix:**
- Fix severity validator: `severity = impact * probability` (actual computation)
- Structure threats as `ThreatItem` with: description, affected_stage, financial_impact_estimate
- Pre-process search results into structured bullet points (not raw blocks)
- Add competitor-specific SWOT entries
- Add `market_validation_required: list[str]` — actions the founder must take to validate assumptions

**Schema change:**
```python
class ThreatItem(BaseModel):
    description: str
    affected_area: Literal["MARKET", "TECHNICAL", "FINANCIAL", "REGULATORY", "COMPETITIVE"]
    financial_impact_estimate: str           # NEW: "could delay runway by 3-6 months"
    severity: int = Field(computed=True)     # FIXED: impact * probability

class SWOTOutput(BaseModel):
    # ... existing fields ...
    competitor_positioning: str              # NEW: where we stand vs competitors
    market_validation_required: list[str]    # NEW: founder must-validate items
    biggest_assumption: str                  # NEW: the single riskiest assumption
```

---

## Step 6: Cost Estimates Are Disconnected from Features and Roadmap

**Problem:** Cost module receives compressed SWOT (only 4 list fields) but doesn't use feature count or roadmap timeline for estimation. Budget scenarios are fixed names (LEAN/BALANCED/AGGRESSIVE) with no startup-specific context. MVP cost estimate is a single number with no breakdown.

**Impact:** Financial projections feel arbitrary. No connection between "we need 12 tasks" and "this costs $X."

**Fix:**
- Add `feature_cost_breakdown: dict[str, float]` — cost per feature (estimated from complexity)
- Add `phase_cost_breakdown: dict[str, float]` — cost per roadmap phase
- Add `hire_cost_impact: float` — monthly cost impact of each team hire
- Add `contingency_percent: float` (10-30% buffer)
- Add `revenue_projections: RevenueProjection` — simple revenue model based on DNA business model
- Make budget scenarios contextual: add `assumptions: list[str]` to each scenario

**Schema change:**
```python
class BudgetScenario(BaseModel):
    # ... existing fields ...
    assumptions: list[str]                  # NEW: "assumes 2 engineers, no marketing spend"
    monthly_burn_breakdown: dict[str, float]  # NEW: category-level breakdown

class CostOutput(BaseModel):
    # ... existing fields ...
    contingency_percent: float              # NEW
    break_even_month: int | None            # NEW: estimated month to break even
    key_cost_risks: list[str]               # NEW
```

---

## Step 7: Blueprint Is a Passive Aggregator, Not an Active Analyst

**Problem:** Blueprint just concatenates previous outputs. Health indicators use hardcoded formulas that don't adapt to startup type. Conflict resolution only checks salary vs budget — misses feature vs roadmap mismatches, team vs hiring timeline gaps. Executive summary is generic "strong opportunity" language.

**Impact:** The final document doesn't feel like an investor wrote it. Health scores don't reflect real readiness.

**Fix:**
- Add `competitive_analysis: CompetitiveAnalysis` — where we win, where we lose
- Add `market_positioning: str` — positioning statement
- Add `investment_readiness_checklist: list[ChecklistItem]` — what's missing for fundraise
- Improve health indicator formulas with startup-type-specific weights
- Add cross-module validation: feature count vs team size vs budget alignment
- Add `key_assumptions: list[str]` — the 3-5 assumptions that must be true
- Add `next_steps: list[ActionItem]` — concrete 30-day actions for the founder

**Schema change:**
```python
class CompetitiveAnalysis(BaseModel):
    direct_competitors: list[str]
    indirect_competitors: list[str]
    competitive_advantages: list[str]
    competitive_gaps: list[str]
    differentiation_strategy: str

class ActionItem(BaseModel):
    action: str
    owner: Literal["FOUNDER", "CTO", "TEAM", "ADVISOR"]
    deadline: str
    priority: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    depends_on: list[str]

class BlueprintOutput(BaseModel):
    # ... existing fields ...
    competitive_analysis: CompetitiveAnalysis          # NEW
    market_positioning: str                             # NEW
    investment_readiness_checklist: list[ChecklistItem]  # NEW
    key_assumptions: list[str]                          # NEW
    next_steps: list[ActionItem]                        # NEW
```

---

## Step 8: Context Compression Is Destroying Signal

**Problem:** The orchestrator aggressively compresses context before passing it downstream. DNA loses `scores` and `executive_summary`. Features lose `description`, `dependencies`, `priority`. Roadmap loses task descriptions. Team loses `responsibilities` and `required_skills`. SWOT loses `founder_actions` detail.

**Impact:** Downstream modules receive hollow summaries. Blueprint gets dicts with 4 fields per feature instead of full context. The LLM can't make nuanced connections when it only sees truncated data.

**Fix:**
- Increase compression limits: features from 15 → 25 items, descriptions from 4 → full
- Pass `scores` through from DNA (downstream needs to know innovation level)
- Pass `executive_summary` through (gives strategic context)
- Add a `context_summary: str` field — a 200-char executive summary of each stage, always passed through
- For Blueprint (stage 7), pass full uncompressed context (it's the final stage, token budget is less constrained)

**Implementation in `engine.py`:**
```python
# BEFORE compression, extract a context_summary from each stage
context_summary = {
    "dna": output.get("executive_summary", "")[:200],
    "features": f"{len(output.get('features', []))} features, MVP: {output.get('mvp_scope_rationale', '')[:100]}",
    "roadmap": f"{len(output.get('phases', []))} phases, readiness: {output.get('launch_readiness_plan', {}).get('readiness_score', 'N/A')}",
    # ...
}
# Pass context_summary alongside compressed data
```

---

## Summary: Before vs After

| Dimension | Current | After Improvements |
|-----------|---------|-------------------|
| Market grounding | 3/8 stages use search | 5/8 stages use search (DNA + Features added) |
| Feature count | Fixed 5 | 5-12 (complexity-scaled) |
| Roadmap tasks | Fixed 12 | 18-24 (complexity-scaled) |
| Team roles | Fixed 3-4 | 4-8 (complexity-scaled) |
| SWOT severity | No-op validator | Computed: impact × probability |
| Cost connection | Disconnected from features | Feature-level cost breakdown |
| Blueprint depth | Passive aggregator | Active analyst with competitive analysis |
| Context passed | 4-8 fields per stage | 8-12 fields + context summaries |
| Search coverage | 14 queries/run | 18 queries/run (+4 for DNA) |

---

## Implementation Priority

| Priority | Step | Effort | Impact |
|----------|------|--------|--------|
| 1 | Fix context compression (Step 8) | Low | High — immediately improves all downstream quality |
| 2 | Add search to DNA (Step 1) | Medium | High — grounds the entire pipeline in real data |
| 3 | Fix SWOT severity validator (Step 5) | Low | Medium — quick fix, real data quality improvement |
| 4 | Scale features/roadmap/team (Steps 2-4) | Medium | Medium — more realistic output |
| 5 | Connect cost to features (Step 6) | Medium | High — makes financial projections believable |
| 6 | Enhance blueprint (Step 7) | High | High — final output quality |
