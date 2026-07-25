"""Product Execution Engine Module — generates PRDs, architecture, sprints, and release plans.

All outputs are synchronized with roadmap and features from earlier pipeline stages.
"""

from __future__ import annotations

from typing import Any

from backend.ai.gemini import gemini_adapter
from backend.modules.product_execution.schemas import (
    ProductExecutionOutput, TechnicalArchitecture, ReleasePlan
)
from backend.modules.evidence.types import ConfidenceScore, EvidenceSource
from backend.modules.evidence.collector import search_evidence


PRODUCT_EXEC_PROMPT = """You are a Senior Product Manager and Technical Lead creating an execution plan.

## Startup Context
- Industry: {industry}
- Product: {product_description}
- Target Market: {target_market}
- Stage: {stage}

## Features from Pipeline
{features_summary}

## Roadmap from Pipeline
{roadmap_summary}

## Team from Pipeline
{team_summary}

## Evidence
{evidence_text}

## Required Outputs

### 1. Product Vision (2-3 sentences)
Clear, inspiring product vision statement.

### 2. PRD Executive Summary
- Problem statement
- Proposed solution
- Target users
- Success metrics
- Key dependencies

### 3. User Stories (15-25 stories)
For EACH major feature, create 2-4 user stories in format:
- US-XXX: As a [user type], I want [action] so that [benefit]
- Include acceptance criteria (3-5 per story)
- Priority: P0 (must-have), P1 (should-have), P2 (nice-to-have), P3 (future)
- Effort: XS/S/M/L/XL

### 4. Technical Architecture
- System overview (microservices? monolith? serverless?)
- Key components
- Data flow
- API endpoints (5-10 key endpoints)
- Database schema (5-8 tables)
- Infrastructure requirements
- Security considerations

### 5. Sprint Plan (6-8 sprints, 2 weeks each)
For each sprint:
- Sprint goal
- Stories included
- Total effort points
- Risks

### 6. Release Plan
- Version 1.0 scope
- Target date
- Features included
- Milestones
- Success metrics
- Rollback plan

### 7. QA Strategy
- Testing approach
- Key test scenarios
- Automation strategy

### 8. Deployment Strategy
- CI/CD approach
- Environment strategy
- Monitoring

Return valid ProductExecutionOutput JSON."""


class ProductExecutionModule:
    """Generates comprehensive product execution assets."""

    stage_name = "product_execution"
    input_stages = ["dna", "features", "roadmap", "team", "blueprint"]

    async def run(self, context: dict[str, Any], evidence: list[EvidenceSource] | None = None) -> dict[str, Any]:
        evidence = evidence or []

        # Gather product execution evidence
        industry = context.get("industry", "technology")
        prod_evidence = await search_evidence(
            f"{industry} product management best practices agile sprint 2025", max_results=3
        )
        evidence.extend(prod_evidence)

        # Generate product execution plan
        output = await self._generate_execution(context, evidence)
        return output.model_dump()

    async def _generate_execution(
        self, context: dict[str, Any], evidence: list[EvidenceSource]
    ) -> ProductExecutionOutput:
        """Generate comprehensive product execution plan."""
        features = context.get("features_output", {})
        feature_list = features.get("features", [])
        features_summary = "\n".join(
            f"- {f.get('id', 'F-XX')}: {f.get('name', 'Feature')} — {f.get('description', '')[:60]} "
            f"(effort: {f.get('effort_estimate', 'M')}, value: {f.get('business_value', 5)}/10)"
            for f in feature_list[:15] if isinstance(f, dict)
        ) or "No features defined"

        roadmap = context.get("roadmap_output", {})
        phases = roadmap.get("phases", [])
        roadmap_summary = "\n".join(
            f"- Phase {p.get('phase_number', '?')}: {p.get('name', 'Phase')} — "
            f"{p.get('duration_weeks', '?')} weeks, {len(p.get('tasks', []))} tasks"
            for p in phases[:6] if isinstance(p, dict)
        ) or "No roadmap phases defined"

        team = context.get("team_output", {})
        roles = team.get("roles", [])
        team_summary = "\n".join(
            f"- {r.get('title', 'Role')}: {r.get('responsibilities', [''])[0] if r.get('responsibilities') else 'TBD'}"
            for r in roles[:8] if isinstance(r, dict)
        ) or "No team defined"

        evidence_text = "\n".join(
            f"- [{e.source_name}] {e.snippet[:100]}"
            for e in evidence[:10]
        ) or "No evidence available"

        prompt = PRODUCT_EXEC_PROMPT.format(
            industry=context.get("industry", "technology"),
            product_description=context.get("product_description", ""),
            target_market=context.get("target_market", ""),
            stage=context.get("stage", "pre-seed"),
            features_summary=features_summary,
            roadmap_summary=roadmap_summary,
            team_summary=team_summary,
            evidence_text=evidence_text,
        )

        result = await gemini_adapter.generate(
            prompt=prompt,
            schema=ProductExecutionOutput,
            system_instruction="You are a Senior Product Manager and Technical Lead creating an execution plan.",
        )

        if isinstance(result, ProductExecutionOutput):
            result.evidence = evidence[:10]
            return result

        return self._fallback_output(evidence, features_summary)

    def _fallback_output(self, evidence: list[EvidenceSource], features_summary: str) -> ProductExecutionOutput:
        """Fallback product execution plan."""
        return ProductExecutionOutput(
            product_vision="Build a market-leading product that solves core customer pain points.",
            prd_summary="Execution plan requires detailed feature specifications for full generation.",
            user_stories=[],
            technical_architecture=TechnicalArchitecture(
                system_overview="Architecture to be defined based on specific requirements.",
                components=[],
                data_flow="To be designed",
                api_endpoints=[],
                database_schema=[],
                infrastructure="Cloud-based (AWS/GCP)",
                security_considerations=["Authentication", "Data encryption", "Access control"],
            ),
            sprints=[],
            release_plan=ReleasePlan(
                release_name="MVP", version="0.1.0", target_date="TBD",
                features=[], milestones=[], success_metrics=[],
                rollback_plan="Redeploy previous version",
            ),
            qa_strategy=["Unit testing", "Integration testing", "E2E testing"],
            deployment_strategy=["CI/CD pipeline", "Staging environment", "Production deployment"],
            evidence=evidence[:5],
            confidence=ConfidenceScore(score=25.0, evidence=evidence[:3]),
            explanation="Fallback execution plan — requires detailed feature and roadmap inputs.",
        )
