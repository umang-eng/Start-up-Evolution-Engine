"""Blueprint Synchronization — meetings automatically update the Venture Studio.

Detects changes to business model, pricing, features, roadmap, hiring,
financial assumptions, GTM, expansion, and investment strategy.
Suggests regeneration only for impacted stages.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field

from backend.modules.memory.types import AffectedComponent, MemoryEntry
from backend.ai.gemini import gemini_adapter
from backend.core.logging import logger


class ChangeType(str, Enum):
    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"
    DEFERRED = "deferred"
    CANCELLED = "cancelled"


class PipelineChange(BaseModel):
    """A change to a pipeline stage detected from meeting discussions."""
    stage_name: str = Field(description="Pipeline stage affected")
    change_type: ChangeType
    description: str = Field(max_length=1000)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    requires_regeneration: bool = Field(default=True)
    priority: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = Field(default="MEDIUM")
    estimated_impact: str = Field(default="", description="Expected impact on output")


class BlueprintSyncResult(BaseModel):
    """Result of syncing meetings to blueprint."""
    changes: list[PipelineChange]
    stages_affected: list[str]
    stages_to_regenerate: list[str]
    change_summary: str
    visual_diff: dict[str, Any] = Field(default_factory=dict)
    version_increment: str = Field(default="minor")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


SYNC_ANALYSIS_PROMPT = """You are a Blueprint Synchronization Analyst. Analyze meeting discussions for changes that affect the startup blueprint.

## Current Blueprint State
{blueprint_summary}

## Meeting Memory Entries
{memory_entries}

## Detected Changes

Analyze each memory entry and determine if it requires blueprint updates:

For EACH change detected:
1. stage_name: which pipeline stage is affected (dna, features, roadmap, team, swot, cost, blueprint, competitive_moat, stress_test, financial_intelligence, investment_committee, product_execution, global_expansion)
2. change_type: added/modified/removed/deferred/cancelled
3. description: what specifically changed
4. confidence: 0.0-1.0 (how certain is this change)
5. evidence: which memory entries support this change
6. requires_regeneration: should this stage be re-run?
7. priority: CRITICAL/HIGH/MEDIUM/LOW
8. estimated_impact: what will change in the output

## Pipeline Stage Dependencies
- DNA changes → all downstream stages affected
- Features changes → roadmap, team, cost, blueprint affected
- Roadmap changes → team, cost, blueprint affected
- Team changes → cost, blueprint affected
- Cost changes → blueprint, financial_intelligence affected
- SWOT changes → blueprint, competitive_moat affected

## Rules:
- Only flag changes that are material (not trivial wording changes)
- Consider cascading effects (DNA change affects everything)
- Estimate whether re-running a stage would produce meaningfully different output
- Prioritize changes that affect investor-facing outputs

Return as JSON array of PipelineChange objects."""


class BlueprintSyncEngine:
    """Synchronizes meeting insights with the Venture Studio pipeline."""

    def __init__(self, project_id: str):
        self.project_id = project_id

    async def analyze_changes(
        self,
        memory_entries: list[MemoryEntry],
        blueprint_summary: str,
    ) -> BlueprintSyncResult:
        """Analyze memory entries for blueprint-affecting changes."""
        if not memory_entries:
            return BlueprintSyncResult(
                changes=[],
                stages_affected=[],
                stages_to_regenerate=[],
                change_summary="No changes detected",
            )

        entries_text = "\n".join(
            f"- [{e.memory_type.value}] [{', '.join(e.affected_modules)}] {e.content[:150]}"
            for e in memory_entries[:30]
        )

        prompt = SYNC_ANALYSIS_PROMPT.format(
            blueprint_summary=blueprint_summary[:3000],
            memory_entries=entries_text,
        )

        try:
            result = await gemini_adapter.generate(
                prompt=prompt,
                schema=list[dict[str, Any]],
                system_instruction="You detect blueprint-affecting changes from meeting discussions.",
            )

            changes = []
            stages_affected: set[str] = set()
            stages_to_regenerate: set[str] = set()

            if isinstance(result, list):
                for item in result:
                    if isinstance(item, dict):
                        change = PipelineChange(
                            stage_name=item.get("stage_name", ""),
                            change_type=ChangeType(item.get("change_type", "modified")),
                            description=item.get("description", ""),
                            confidence=float(item.get("confidence", 0.7)),
                            evidence=item.get("evidence", []),
                            requires_regeneration=item.get("requires_regeneration", True),
                            priority=item.get("priority", "MEDIUM"),
                            estimated_impact=item.get("estimated_impact", ""),
                        )
                        changes.append(change)
                        stages_affected.add(change.stage_name)
                        if change.requires_regeneration:
                            stages_to_regenerate.add(change.stage_name)

            # Add cascading dependencies
            cascading = self._compute_cascading_changes(stages_to_regenerate)
            stages_to_regenerate.update(cascading)

            return BlueprintSyncResult(
                changes=changes,
                stages_affected=list(stages_affected),
                stages_to_regenerate=sorted(stages_to_regenerate),
                change_summary=f"Detected {len(changes)} changes affecting {len(stages_affected)} stages, {len(stages_to_regenerate)} need regeneration",
                visual_diff=self._build_visual_diff(changes),
                version_increment=self._determine_version_increment(changes),
            )

        except Exception as e:
            logger.warning(f"Blueprint sync analysis failed: {e}")
            return BlueprintSyncResult(
                changes=[],
                stages_affected=[],
                stages_to_regenerate=[],
                change_summary=f"Analysis failed: {str(e)[:100]}",
            )

    def _compute_cascading_changes(self, stages: set[str]) -> set[str]:
        """Compute cascading stage changes based on dependencies."""
        cascading: set[str] = set()
        dependency_map = {
            "dna": ["features", "roadmap", "team", "swot", "cost", "blueprint",
                    "competitive_moat", "stress_test", "financial_intelligence",
                    "investment_committee", "product_execution", "global_expansion"],
            "features": ["roadmap", "team", "cost", "blueprint", "product_execution"],
            "roadmap": ["team", "cost", "blueprint", "product_execution"],
            "team": ["cost", "blueprint"],
            "cost": ["blueprint", "financial_intelligence", "investment_committee"],
            "swot": ["blueprint", "competitive_moat"],
        }
        for stage in stages:
            for dep in dependency_map.get(stage, []):
                if dep not in stages:
                    cascading.add(dep)
        return cascading

    def _build_visual_diff(self, changes: list[PipelineChange]) -> dict[str, Any]:
        """Build a visual diff summary."""
        by_stage: dict[str, list[dict]] = {}
        for change in changes:
            if change.stage_name not in by_stage:
                by_stage[change.stage_name] = []
            by_stage[change.stage_name].append({
                "type": change.change_type.value,
                "description": change.description[:100],
                "priority": change.priority,
            })
        return by_stage

    def _determine_version_increment(self, changes: list[PipelineChange]) -> str:
        """Determine if this is a major, minor, or patch version increment."""
        has_critical = any(c.priority == "CRITICAL" for c in changes)
        has_high = any(c.priority == "HIGH" for c in changes)
        if has_critical:
            return "major"
        elif has_high:
            return "minor"
        return "patch"

    def generate_change_summary(self, result: BlueprintSyncResult) -> str:
        """Generate a human-readable change summary."""
        if not result.changes:
            return "No blueprint changes detected from this meeting."

        lines = [f"## Blueprint Changes ({len(result.changes)} detected)\n"]
        for change in result.changes:
            emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(change.priority, "⚪")
            lines.append(f"{emoji} **{change.stage_name.upper()}** ({change.change_type.value})")
            lines.append(f"   {change.description[:100]}")
            lines.append(f"   Confidence: {change.confidence:.0%} | Priority: {change.priority}")
            if change.requires_regeneration:
                lines.append(f"   ⚠️ Requires regeneration")
            lines.append("")

        if result.stages_to_regenerate:
            lines.append(f"\n**Stages to regenerate:** {', '.join(result.stages_to_regenerate)}")

        return "\n".join(lines)
