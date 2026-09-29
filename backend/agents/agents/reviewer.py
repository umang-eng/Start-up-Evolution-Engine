"""ReviewerAgent — Reviews synthesized output, catches errors, suggests improvements.

This agent reviews the output from the SynthesizerAgent and returns a
ReviewCritique indicating whether the output is approved or needs revision.
"""

from __future__ import annotations

from typing import Any

from backend.agents.base import BaseAgent
from backend.agents.context_bus import AgentContextBus
from backend.agents.types import AgentRole, ReviewCritique


class ReviewerAgent(BaseAgent):
    """Reviews synthesized output for quality, accuracy, and completeness."""

    role = AgentRole.REVIEWER
    tools = []

    SYSTEM_INSTRUCTION = (
        "You are a senior quality reviewer for startup analysis documents. "
        "Review the synthesized output for:\n"
        "1. Logical consistency between scores and narrative\n"
        "2. Missing critical analysis dimensions\n"
        "3. Overly optimistic or pessimistic assessments\n"
        "4. Actionability of recommendations\n"
        "5. Schema compliance (all required fields present and valid)\n\n"
        "Be rigorous but fair. Only flag genuine issues, not stylistic preferences."
    )

    async def run(
        self,
        context: dict[str, Any],
        bus: AgentContextBus,
    ) -> ReviewCritique:
        """Review the synthesis output from the bus."""
        # Get the synthesis output to review
        synthesis_data = {}
        try:
            obs = await self.wait_for_observation(bus, "synthesis_complete", timeout_s=10.0)
            if hasattr(obs.data, "data"):
                synthesis_data = obs.data.data
            elif hasattr(obs.data, "model_dump"):
                synthesis_data = obs.data.model_dump()
            elif isinstance(obs.data, dict):
                synthesis_data = obs.data
        except Exception as e:
            return ReviewCritique(
                approved=False,
                issues=[f"Could not retrieve synthesis output: {e}"],
                severity="blocking",
                revision_notes="Synthesis output not found on bus",
            )

        if not synthesis_data:
            return ReviewCritique(
                approved=False,
                issues=["Synthesis output is empty"],
                severity="blocking",
                revision_notes="No synthesis data to review",
            )

        issues: list[str] = []
        severity = "none"

        # Check for required fields based on common patterns
        if "scores" in synthesis_data:
            scores = synthesis_data["scores"]
            if isinstance(scores, dict):
                for key, val in scores.items():
                    if isinstance(val, (int, float)):
                        if val < 0 or val > 100:
                            issues.append(f"Score '{key}' out of range: {val}")
                            severity = "blocking"

        if "executive_summary" in synthesis_data:
            summary = synthesis_data["executive_summary"]
            if isinstance(summary, str) and len(summary) < 50:
                issues.append("Executive summary is too short (< 50 chars)")
                severity = "minor" if severity != "blocking" else severity

        if "confidence_score" in synthesis_data:
            cs = synthesis_data["confidence_score"]
            if isinstance(cs, (int, float)) and cs < 0.2:
                issues.append(f"Confidence score is very low: {cs}")
                severity = "minor" if severity != "blocking" else severity

        # Check for empty required lists
        for field_name in ["revenue_streams", "target_segments", "strategic_recommendations"]:
            if field_name in synthesis_data:
                val = synthesis_data[field_name]
                if isinstance(val, list) and len(val) == 0:
                    issues.append(f"Required list '{field_name}' is empty")
                    severity = "blocking"

        # Determine approval
        approved = severity != "blocking"

        revision_notes = None
        if not approved:
            revision_notes = (
                "Please address the blocking issues: "
                + "; ".join(issues)
            )

        return ReviewCritique(
            approved=approved,
            issues=issues,
            severity=severity,
            revision_notes=revision_notes,
        )
