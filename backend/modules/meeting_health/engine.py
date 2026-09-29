"""Meeting Health Analysis — scores meetings on multiple dimensions.

Tracks focus, clarity, participation, decision quality, execution readiness,
innovation, strategic alignment, conflict resolution, and time efficiency.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field

from backend.ai.gemini import gemini_adapter
from backend.core.logging import logger


class HealthDimension(BaseModel):
    """A single health dimension score."""
    name: str
    score: float = Field(ge=0.0, le=10.0)
    weight: float = Field(ge=0.0, le=1.0, default=1.0)
    explanation: str = Field(default="")
    improvement: str = Field(default="", description="How to improve this dimension")


class MeetingHealthReport(BaseModel):
    """Complete health analysis for a meeting."""
    meeting_id: str
    overall_score: float = Field(ge=0.0, le=10.0)
    dimensions: list[HealthDimension]
    strengths: list[str]
    weaknesses: list[str]
    improvement_opportunities: list[str]
    trend: str = Field(default="stable", description="improving/stable/declining")
    benchmark_comparison: str = Field(default="", description="How this compares to average")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


HEALTH_ANALYSIS_PROMPT = """You are a Meeting Effectiveness Analyst. Analyze this meeting transcript and score it.

## Meeting
- Title: {title}
- Duration: {duration}
- Participants: {participants}

## Transcript
{transcript}

## Score each dimension (0-10):

1. **Focus** (0-10): How focused was the meeting? Were tangents avoided?
2. **Clarity** (0-10): How clear were discussions and outcomes?
3. **Participation** (0-10): Did all participants contribute equally?
4. **Decision Quality** (0-10): Were decisions well-reasoned and evidence-based?
5. **Execution Readiness** (0-10): Are action items clear with owners and deadlines?
6. **Innovation** (0-10): Were new ideas explored?
7. **Strategic Alignment** (0-10): Does this align with the startup's strategy?
8. **Conflict Resolution** (0-10): Were disagreements resolved constructively?
9. **Time Efficiency** (0-10): Was time used productively?

For EACH dimension provide:
- score: 0-10
- explanation: why this score
- improvement: specific suggestion to improve

Also provide:
- strengths: top 3 things done well
- weaknesses: top 3 areas for improvement
- improvement_opportunities: specific actionable suggestions

Return valid MeetingHealthReport JSON."""


class MeetingHealthEngine:
    """Analyzes meeting effectiveness across multiple dimensions."""

    def __init__(self):
        self.reports: list[MeetingHealthReport] = []

    async def analyze(
        self,
        meeting_id: str,
        title: str,
        duration: str,
        participants: list[str],
        transcript: str,
    ) -> MeetingHealthReport:
        """Analyze a meeting's health across all dimensions."""
        prompt = HEALTH_ANALYSIS_PROMPT.format(
            title=title,
            duration=duration,
            participants=", ".join(participants),
            transcript=transcript[:6000],
        )

        try:
            result = await gemini_adapter.generate(
                prompt=prompt,
                schema=MeetingHealthReport,
                system_instruction="You analyze meeting effectiveness and provide constructive feedback.",
            )

            if isinstance(result, MeetingHealthReport):
                result.meeting_id = meeting_id
                self.reports.append(result)
                return result

        except Exception as e:
            logger.warning(f"Meeting health analysis failed: {e}")

        return self._fallback_report(meeting_id)

    def _fallback_report(self, meeting_id: str) -> MeetingHealthReport:
        """Fallback when analysis fails."""
        return MeetingHealthReport(
            meeting_id=meeting_id,
            overall_score=5.0,
            dimensions=[
                HealthDimension(name="Focus", score=5.0, explanation="Unable to analyze"),
                HealthDimension(name="Clarity", score=5.0, explanation="Unable to analyze"),
                HealthDimension(name="Participation", score=5.0, explanation="Unable to analyze"),
                HealthDimension(name="Decision Quality", score=5.0, explanation="Unable to analyze"),
                HealthDimension(name="Execution Readiness", score=5.0, explanation="Unable to analyze"),
                HealthDimension(name="Innovation", score=5.0, explanation="Unable to analyze"),
                HealthDimension(name="Strategic Alignment", score=5.0, explanation="Unable to analyze"),
                HealthDimension(name="Conflict Resolution", score=5.0, explanation="Unable to analyze"),
                HealthDimension(name="Time Efficiency", score=5.0, explanation="Unable to analyze"),
            ],
            strengths=["Meeting occurred"],
            weaknesses=["Analysis unavailable"],
            improvement_opportunities=["Run analysis with more transcript data"],
        )

    def get_trend(self, limit: int = 10) -> dict[str, Any]:
        """Analyze health trend over recent meetings."""
        recent = self.reports[-limit:]
        if not recent:
            return {"trend": "no_data", "average": 0}

        scores = [r.overall_score for r in recent]
        avg = sum(scores) / len(scores)

        if len(scores) >= 2:
            first_half = scores[:len(scores)//2]
            second_half = scores[len(scores)//2:]
            first_avg = sum(first_half) / len(first_half)
            second_avg = sum(second_half) / len(second_half)

            if second_avg > first_avg + 0.5:
                trend = "improving"
            elif second_avg < first_avg - 0.5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "trend": trend,
            "average": round(avg, 1),
            "latest": scores[-1] if scores else 0,
            "meetings_analyzed": len(recent),
        }

    def get_dimension_trends(self) -> dict[str, list[float]]:
        """Get trend data for each dimension."""
        trends: dict[str, list[float]] = {}
        for report in self.reports:
            for dim in report.dimensions:
                if dim.name not in trends:
                    trends[dim.name] = []
                trends[dim.name].append(dim.score)
        return trends
