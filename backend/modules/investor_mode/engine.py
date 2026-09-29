"""Investor Meeting Mode — investor-specific analysis and preparation.

When investor meetings are detected, generates investor questions,
strengths, weaknesses, objections, missing metrics, and follow-up plans.
"""

from datetime import datetime, timezone
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field

from backend.ai.gemini import gemini_adapter
from backend.core.logging import logger


class InvestorQuestion(BaseModel):
    """A likely investor question with suggested response."""
    question: str
    suggested_response: str
    confidence: float = Field(ge=0.0, le=1.0)
    category: str
    difficulty: Literal["easy", "moderate", "hard", "critical"]
    missing_data: list[str] = Field(default_factory=list)


class InvestorAnalysis(BaseModel):
    """Complete investor meeting analysis."""
    meeting_id: str
    is_investor_meeting: bool
    investor_type: str = Field(default="", description="Type of investor (VC, angel, accelerator)")
    likely_questions: list[InvestorQuestion]
    strengths: list[str]
    weaknesses: list[str]
    objections: list[str]
    missing_metrics: list[str]
    due_diligence_requests: list[str]
    funding_probability: float = Field(ge=0.0, le=1.0)
    follow_up_recommendations: list[str]
    investor_action_plan: list[str]
    summary: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


INVESTOR_ANALYSIS_PROMPT = """You are an Investment Analyst. Analyze this meeting for investor-related content.

## Meeting
- Title: {title}
- Participants: {participants}

## Startup Context
{startup_context}

## Transcript
{transcript}

## Analyze:

1. Is this an investor meeting? (check for investor-related language)
2. If yes, what type of investor? (VC, angel, accelerator, bank)

3. Likely investor questions (10-15):
   - question: what they'll ask
   - suggested_response: how to answer
   - confidence: how likely they'll ask this
   - category: market/product/financial/team/legal
   - difficulty: easy/moderate/hard/critical
   - missing_data: what info we don't have yet

4. Strengths to highlight
5. Weaknesses to address
6. Potential objections and how to handle
7. Missing metrics investors want to see
8. Due diligence requests to prepare for
9. Funding probability estimate (0-100%)
10. Follow-up recommendations
11. Action plan before next investor meeting

Return valid InvestorAnalysis JSON."""


class InvestorModeEngine:
    """Analyzes meetings for investor-related content."""

    def __init__(self):
        self.analyses: list[InvestorAnalysis] = []

    async def analyze(
        self,
        meeting_id: str,
        title: str,
        participants: list[str],
        transcript: str,
        startup_context: str = "",
    ) -> InvestorAnalysis:
        """Analyze a meeting for investor content."""
        prompt = INVESTOR_ANALYSIS_PROMPT.format(
            title=title,
            participants=", ".join(participants),
            startup_context=startup_context[:2000],
            transcript=transcript[:6000],
        )

        try:
            result = await gemini_adapter.generate(
                prompt=prompt,
                schema=InvestorAnalysis,
                system_instruction="You analyze meetings for investor-related content and provide strategic advice.",
            )

            if isinstance(result, InvestorAnalysis):
                result.meeting_id = meeting_id
                self.analyses.append(result)
                return result

        except Exception as e:
            logger.warning(f"Investor analysis failed: {e}")

        return InvestorAnalysis(
            meeting_id=meeting_id,
            is_investor_meeting=False,
            likely_questions=[],
            strengths=[],
            weaknesses=[],
            objections=[],
            missing_metrics=[],
            due_diligence_requests=[],
            funding_probability=0.0,
            follow_up_recommendations=[],
            investor_action_plan=[],
            summary="Investor analysis unavailable",
        )

    def get_investor_meetings(self) -> list[InvestorAnalysis]:
        """Get all identified investor meetings."""
        return [a for a in self.analyses if a.is_investor_meeting]

    def get_preparation_checklist(self) -> list[str]:
        """Generate a preparation checklist from all investor analyses."""
        checklist = []
        for analysis in self.get_investor_meetings():
            checklist.extend(analysis.investor_action_plan)
            checklist.extend(analysis.due_diligence_requests)
        return list(set(checklist))
