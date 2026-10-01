"""Product Execution Engine Module — generates PRDs, architecture, sprints, and release plans.

All outputs are synchronized with roadmap and features from earlier pipeline stages.
"""

from __future__ import annotations

import logging
from typing import Any
from datetime import date, timedelta

from backend.ai.ollama import ollama_adapter
from backend.modules.product_execution.schemas import (
    ProductExecutionOutput, TechnicalArchitecture, ReleasePlan,
    SprintBacklog, UserStory,
)
from backend.modules.evidence.types import ConfidenceScore, EvidenceSource
from backend.modules.evidence.collector import search_evidence
from backend.core.config import settings
from backend.core.exceptions import BaseBusinessException

logger = logging.getLogger("app.product_execution")


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

        # Fast mode skips optional web research, not the execution plan itself.
        industry = context.get("industry", "technology")
        if not settings.PIPELINE_FAST_MODE:
            prod_evidence = await search_evidence(
                f"{industry} product management best practices agile sprint 2025", max_results=3
            )
            evidence.extend(prod_evidence)

        try:
            output = await self._generate_execution(context, evidence)
        except BaseBusinessException as exc:
            if exc.code.startswith("OLLAMA_"):
                raise
            logger.exception("Product execution generation failed; building a plan from available pipeline inputs.")
            output = self._fallback_output(evidence, context)
        except Exception:
            logger.exception("Product execution generation failed; building a plan from available pipeline inputs.")
            output = self._fallback_output(evidence, context)
        return output.model_dump()

    async def _generate_execution(
        self, context: dict[str, Any], evidence: list[EvidenceSource]
    ) -> ProductExecutionOutput:
        """Generate comprehensive product execution plan."""
        features = context.get("features_output") or context.get("features", {})
        feature_list = features.get("features", [])
        features_summary = "\n".join(
            f"- {f.get('id', 'F-XX')}: {f.get('name', 'Feature')} — {f.get('description', '')[:60]} "
            f"(effort: {f.get('effort_estimate', 'M')}, value: {f.get('business_value', 5)}/10)"
            for f in feature_list[:15] if isinstance(f, dict)
        ) or "No features defined"

        roadmap = context.get("roadmap_output") or context.get("roadmap", {})
        phases = roadmap.get("phases", [])
        roadmap_summary = "\n".join(
            f"- {p.get('name', 'Phase')}: "
            f"{p.get('duration_weeks', int(p.get('duration_months', 1) or 1) * 4)} weeks, "
            f"{len(p.get('tasks', []))} tasks"
            for p in phases[:6] if isinstance(p, dict)
        ) or "No roadmap phases defined"

        team = context.get("team_output") or context.get("team", {})
        roles = team.get("org_chart", team.get("roles", []))
        team_summary = "\n".join(
            f"- {r.get('title', r.get('role_title', 'Role'))}: "
            f"{r.get('responsibilities', [''])[0] if r.get('responsibilities') else 'TBD'}"
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

        result = await ollama_adapter.generate(
            prompt=prompt,
            schema=ProductExecutionOutput,
            system_instruction="You are a Senior Product Manager and Technical Lead creating an execution plan.",
        )

        if isinstance(result, ProductExecutionOutput):
            result.evidence = evidence[:10]
            fallback = self._fallback_output(evidence, context)
            return self._complete_output(result, fallback)

        return self._fallback_output(evidence, context)

    @staticmethod
    def _complete_output(
        output: ProductExecutionOutput,
        fallback: ProductExecutionOutput,
    ) -> ProductExecutionOutput:
        """Fill schema-valid but incomplete model responses from actual pipeline inputs."""
        data = output.model_dump()
        fallback_data = fallback.model_dump()
        for field in ("product_vision", "prd_summary", "qa_strategy", "deployment_strategy"):
            value = data.get(field)
            if not value or (isinstance(value, str) and value.strip().lower() in {"tbd", "to be defined", "to be designed"}):
                data[field] = fallback_data[field]

        for field in ("user_stories", "qa_strategy", "deployment_strategy"):
            if not data.get(field):
                data[field] = fallback_data[field]
        stories = list(data.get("user_stories") or [])
        fallback_stories = fallback_data["user_stories"]
        feature_story_counts: dict[str, int] = {}
        for story in stories:
            feature_id = story.get("feature_id", "")
            feature_story_counts[feature_id] = feature_story_counts.get(feature_id, 0) + 1
        next_story_number = len(stories) + 1
        existing_story_ids = {story.get("id") for story in stories}
        for story in fallback_stories:
            if len(stories) >= 15:
                break
            feature_id = story.get("feature_id", "")
            if feature_story_counts.get(feature_id, 0) >= 3:
                continue
            while f"US-{next_story_number:03d}" in existing_story_ids:
                next_story_number += 1
            story = {**story, "id": f"US-{next_story_number:03d}"}
            stories.append(story)
            existing_story_ids.add(story["id"])
            feature_story_counts[feature_id] = feature_story_counts.get(feature_id, 0) + 1
            next_story_number += 1
        data["user_stories"] = stories[:25]
        if len(data.get("sprints") or []) < 6:
            data["sprints"] = fallback_data["sprints"]

        architecture = data.get("technical_architecture") or {}
        fallback_architecture = fallback_data["technical_architecture"]
        for field in (
            "system_overview",
            "components",
            "data_flow",
            "api_endpoints",
            "database_schema",
            "infrastructure",
            "security_considerations",
        ):
            if not architecture.get(field):
                architecture[field] = fallback_architecture[field]
        data["technical_architecture"] = architecture

        release_plan = data.get("release_plan") or {}
        fallback_release = fallback_data["release_plan"]
        for field in ("release_name", "version", "target_date", "features", "milestones", "success_metrics", "rollback_plan"):
            if not release_plan.get(field) or str(release_plan.get(field, "")).strip().lower() in {"tbd", "to be defined"}:
                release_plan[field] = fallback_release[field]
        data["release_plan"] = release_plan
        if not data.get("explanation"):
            data["explanation"] = fallback_data["explanation"]
        return ProductExecutionOutput.model_validate(data)

    def _fallback_output(
        self,
        evidence: list[EvidenceSource],
        context: dict[str, Any],
    ) -> ProductExecutionOutput:
        """Build a useful, input-grounded plan when structured generation is unavailable."""
        features = context.get("features_output") or context.get("features", {})
        feature_list = [
            feature for feature in features.get("features", [])
            if isinstance(feature, dict)
        ][:20]
        roadmap = context.get("roadmap_output") or context.get("roadmap", {})
        phases = [
            phase for phase in roadmap.get("phases", [])
            if isinstance(phase, dict)
        ]
        team = context.get("team_output") or context.get("team", {})
        roles = team.get("org_chart", team.get("roles", []))
        stack = features.get("core_stack", [])
        product = context.get("product_description") or context.get("startup_idea") or "the proposed product"
        industry = context.get("industry", "the target market")
        target_users = context.get("target_market") or f"customers in {industry}"
        stories = []
        story_variants = [
            ("Deliver", "use"),
            ("Handle errors in", "recover from"),
            ("Manage", "review and manage"),
        ]
        for feature in feature_list:
            feature_name = feature.get("name", "product capability")
            for title_prefix, action_prefix in story_variants:
                if len(stories) == 25:
                    break
                stories.append(UserStory(
                    id=f"US-{len(stories) + 1:03d}",
                    title=f"{title_prefix} {feature_name}",
                    user_type=target_users,
                    action=f"{action_prefix} {feature_name}",
                    benefit=feature.get("business_value") or feature.get("description") or "solve a validated customer problem",
                    acceptance_criteria=[
                        f"{feature_name} is available to its intended user.",
                        "Input validation, error handling, and access controls are covered by automated tests.",
                        "The team can verify the feature against its stated success metric.",
                    ],
                    priority=(
                        "P0" if feature.get("priority") == "MUST_HAVE"
                        else "P1" if feature.get("priority") == "SHOULD_HAVE"
                        else "P2"
                    ),
                    effort_estimate=feature.get("effort_estimate", "M"),
                    feature_id=feature.get("id", ""),
                ))
            if len(stories) == 25:
                break
        sprint_names = [
            "Discovery and delivery foundations",
            "Core product capabilities",
            "Customer workflow and integrations",
            "Data, reliability, and security",
            "Acceptance testing and pilot",
            "Launch readiness",
        ]
        sprints = []
        for index, sprint_name in enumerate(sprint_names):
            sprint_stories = stories[index::len(sprint_names)]
            source_phase = phases[index % len(phases)] if phases else {}
            sprints.append(SprintBacklog(
                sprint_number=index + 1,
                sprint_name=sprint_name,
                duration_weeks=2,
                goal=(
                    source_phase.get("phase_objective")
                    or source_phase.get("name")
                    or f"Complete {sprint_name.lower()} and validate the result with target users."
                ),
                stories=sprint_stories,
                total_effort_points=sum(
                    {"XS": 1, "S": 2, "M": 5, "L": 8, "XL": 13}.get(
                        str(story.effort_estimate).upper(), 5
                    )
                    for story in sprint_stories
                ),
                risks=["Confirm acceptance criteria and dependencies before sprint commitment."],
            ))

        component_names = stack[:8] if isinstance(stack, list) else []
        components = [
            {"name": str(name), "description": f"Product platform component using the proposed {name} technology."}
            for name in component_names
        ]
        if not components:
            components = [
                {"name": "Web application", "description": "Customer-facing product interface."},
                {"name": "Application API", "description": "Validates requests and coordinates product workflows."},
                {"name": "Data store", "description": "Persists user, product, and audit records with access controls."},
            ]
        endpoint_slugs = [
            "".join(character.lower() if character.isalnum() else "-" for character in str(feature.get("name", ""))).strip("-")
            for feature in feature_list[:8]
        ]
        api_endpoints = [
            {"method": "POST", "path": f"/api/v1/{slug}", "description": f"Execute the {feature.get('name', 'product')} workflow."}
            for feature, slug in zip(feature_list[:8], endpoint_slugs)
            if slug
        ]
        database_schema = [
            {"table": table, "purpose": purpose}
            for table, purpose in [
                ("users", "Account identities and authentication references."),
                ("workspaces", "Startup or customer workspace ownership."),
                ("features", "Product capabilities and feature configuration."),
                ("projects", "Project lifecycle and generated artifacts."),
                ("audit_events", "Security-sensitive changes and operational traceability."),
            ]
        ]
        total_weeks = max(int(roadmap.get("total_estimated_weeks", len(phases) * 4) or 1), 1)
        role_names = [
            str(role.get("title", role.get("role_title", "delivery team")))
            for role in roles[:8] if isinstance(role, dict)
        ]
        target_date = (date.today() + timedelta(weeks=min(total_weeks, 52))).isoformat()
        feature_names = [str(feature.get("name", "Core capability")) for feature in feature_list]
        return ProductExecutionOutput(
            product_vision=(
                f"Deliver {product} as a dependable solution for {target_users}, "
                "validating customer value through measurable releases."
            )[:1000],
            prd_summary=(
                f"Build the defined product features for {industry} customers in sequenced, testable releases. "
                f"Prioritize {', '.join(feature_names[:5]) or 'the smallest validated customer workflow'}; "
                f"coordinate delivery across {', '.join(role_names[:4]) or 'the founding team'}. "
                "Confirm user research, acceptance criteria, security, and launch metrics before committing dates."
            )[:2000],
            user_stories=stories,
            technical_architecture=TechnicalArchitecture(
                system_overview=(
                    f"Start with a modular application architecture for {industry}; "
                    "separate the user interface, authenticated API, and persistent data layer."
                ),
                components=components,
                data_flow="Client requests pass through authenticated API validation, business logic, and persisted data; return only authorized results and record security-sensitive events.",
                api_endpoints=api_endpoints or [
                    {"method": "GET", "path": "/api/v1/projects", "description": "List projects the authenticated user may access."},
                    {"method": "POST", "path": "/api/v1/projects", "description": "Create a project after validating its required input."},
                ],
                database_schema=database_schema,
                infrastructure="Deploy separate development, staging, and production environments; use managed hosting, encrypted backups, secret management, health checks, and monitoring.",
                security_considerations=[
                    "Require authenticated, owner-scoped authorization for workspace data.",
                    "Encrypt network traffic and sensitive data at rest; store secrets outside source control.",
                    "Validate and rate-limit inputs; record security-sensitive actions and test recovery procedures.",
                ],
            ),
            sprints=sprints,
            release_plan=ReleasePlan(
                release_name="Validated MVP",
                version="0.1.0",
                target_date=target_date,
                features=feature_names[:12],
                milestones=[
                    {"name": phase.get("name", f"Phase {index + 1}"), "target": phase.get("phase_objective", "Complete phase acceptance criteria.")}
                    for index, phase in enumerate(phases[:8])
                ] or [{"name": "Pilot readiness", "target": "Validate the end-to-end core workflow with target users."}],
                success_metrics=[
                    "Track activation and completion of the primary user workflow.",
                    "Measure pilot retention, support issues, and willingness to pay against pre-launch targets.",
                ],
                rollback_plan="Use a staged rollout with health checks; disable the affected release, restore the last known-good build, and reconcile any data changes.",
            ),
            qa_strategy=[
                "Add unit tests for core business rules and input validation.",
                "Test API authorization, persistence, integrations, and failure handling.",
                "Run end-to-end acceptance tests for the primary user journeys before each release.",
            ],
            deployment_strategy=[
                "Build and test each change through CI before merging.",
                "Promote a verified build through staging, then release gradually with rollback readiness.",
                "Monitor availability, errors, latency, and security events after launch.",
            ],
            evidence=evidence[:5],
            confidence=ConfidenceScore(
                score=45.0,
                evidence=evidence[:3],
                missing_information=["Validated user research, detailed acceptance criteria, and confirmed delivery capacity."],
                assumptions=["Sprint and release dates are planning estimates and require team review."],
            ),
            explanation=(
                "This execution plan was assembled from the available feature, roadmap, team, and product inputs "
                "because structured AI output was unavailable. Validate the assumptions and sprint capacity with the delivery team."
            ),
        )
