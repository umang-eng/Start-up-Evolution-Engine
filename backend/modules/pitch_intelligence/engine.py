"""Pitch Intelligence — analyzes presentations and provides coaching.

Measures speaking pace, filler words, confidence, engagement,
interruptions, clarity, storytelling, and technical complexity.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field

from backend.ai.gemini import gemini_adapter
from backend.core.logging import logger


class PitchMetric(BaseModel):
    """A single pitch metric."""
    name: str
    score: float = Field(ge=0.0, le=10.0)
    value: str = Field(default="", description="Actual measured value")
    benchmark: str = Field(default="", description="Target value")
    explanation: str = Field(default="")
    coaching_tip: str = Field(default="")


class PitchAnalysis(BaseModel):
    """Complete pitch analysis."""
    meeting_id: str
    overall_score: float = Field(ge=0.0, le=10.0)
    metrics: list[PitchMetric]
    strengths: list[str]
    areas_for_improvement: list[str]
    specific_feedback: list[str]
    practice_exercises: list[str]
    improvement_plan: list[str]
    confidence_level: str = Field(default="", description="estimated/confident/nervous")
    audience_engagement: str = Field(default="", description="low/medium/high")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


PITCH_ANALYSIS_PROMPT = """You are a Pitch Coach. Analyze this presentation/meeting for pitch effectiveness.

## Meeting
- Title: {title}
- Duration: {duration}
- Participants: {participants}

## Transcript
{transcript}

## Analyze pitch metrics (0-10 each):

1. **Speaking Pace**: Was it appropriate? (target: 130-150 words/minute)
2. **Filler Word Usage**: How many "um", "uh", "like", "so"?
3. **Confidence Level**: How confident did the speaker sound?
4. **Audience Engagement**: Was the audience engaged?
5. **Interruptions**: How many interruptions occurred?
6. **Clarity**: How clear was the message?
7. **Storytelling**: Was there a compelling narrative?
8. **Technical Complexity**: Was technical depth appropriate?
9. **Call to Action**: Was there a clear ask/CTA?
10. **Handling Objections**: How well were questions handled?

For EACH metric:
- score: 0-10
- value: actual measurement (e.g., "15 fillers", "160 wpm")
- benchmark: target value
- coaching_tip: specific improvement suggestion

Also provide:
- strengths: top 3 things done well
- areas_for_improvement: top 3 areas to work on
- specific_feedback: actionable feedback
- practice_exercises: exercises to improve
- improvement_plan: 30-day improvement plan

Return valid PitchAnalysis JSON."""


class PitchIntelligenceEngine:
    """Analyzes pitch effectiveness and provides coaching."""

    def __init__(self):
        self.analyses: list[PitchAnalysis] = []

    async def analyze(
        self,
        meeting_id: str,
        title: str,
        duration: str,
        participants: list[str],
        transcript: str,
    ) -> PitchAnalysis:
        """Analyze a presentation's pitch effectiveness."""
        prompt = PITCH_ANALYSIS_PROMPT.format(
            title=title,
            duration=duration,
            participants=", ".join(participants),
            transcript=transcript[:6000],
        )

        try:
            result = await gemini_adapter.generate(
                prompt=prompt,
                schema=PitchAnalysis,
                system_instruction="You are an expert pitch coach analyzing presentations.",
            )

            if isinstance(result, PitchAnalysis):
                result.meeting_id = meeting_id
                self.analyses.append(result)
                return result

        except Exception as e:
            logger.warning(f"Pitch analysis failed: {e}")

        return PitchAnalysis(
            meeting_id=meeting_id,
            overall_score=5.0,
            metrics=[],
            strengths=["Pitch occurred"],
            areas_for_improvement=["Analysis unavailable"],
            specific_feedback=[],
            practice_exercises=[],
            improvement_plan=[],
        )

    def get_improvement_trend(self) -> dict[str, Any]:
        """Track improvement over multiple pitches."""
        if len(self.analyses) < 2:
            return {"trend": "insufficient_data"}

        scores = [a.overall_score for a in self.analyses]
        first = scores[0]
        last = scores[-1]
        avg = sum(scores) / len(scores)

        return {
            "trend": "improving" if last > first else "declining" if last < first else "stable",
            "first_score": first,
            "latest_score": last,
            "average": round(avg, 1),
            "pitches_analyzed": len(self.analyses),
        }
