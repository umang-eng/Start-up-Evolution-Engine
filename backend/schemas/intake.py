"""
Intake Conversation Schemas — Structured I/O for the Dynamic Intake Router.

Defines the Pydantic models that the Gemini API must conform to when:
1. Extracting initial concept metadata from a raw startup idea
2. Generating hyper-targeted follow-up questions based on detected industry
3. Aggregating the final intake package for Project entity population
"""

from enum import Enum
from pydantic import BaseModel, Field


# ── Phase 1: Initial Concept Extraction ────────────────────────────

class ConceptExtraction(BaseModel):
    """Structured output from the first Gemini call on raw idea text.

    The model must identify the industry vertical, the primary audience,
    and distill the core value proposition into a single sentence.
    """
    industry: str = Field(
        description=(
            "The specific industry vertical this startup operates in. "
            "Be precise: 'HealthTech', 'FinTech', 'EdTech', 'CleanTech', 'SaaS', "
            "'Marketplace', 'Hardware/IoT', 'AI/ML', 'E-commerce', 'BioTech', etc."
        )
    )
    target_audience: str = Field(
        description=(
            "The primary customer or user persona. "
            "Example: 'busy urban professionals aged 25-40', "
            "'SMB e-commerce store owners', 'enterprise DevOps teams'."
        )
    )
    core_value_proposition: str = Field(
        description=(
            "A single, crisp sentence that captures the core value this startup delivers. "
            "Example: 'Automates bookkeeping for freelancers using AI-powered receipt scanning.'"
        )
    )
    detected_vertical_signals: list[str] = Field(
        default_factory=list,
        description=(
            "2-4 keyword signals that hint at the industry sub-niche. "
            "Used to tailor follow-up questions. "
            "Example: ['drone', 'regulation', 'last-mile'] for a drone delivery startup."
        )
    )


# ── Phase 2: Dynamic Follow-Up Questions ───────────────────────────

class QuestionCategory(str, Enum):
    """Taxonomy of follow-up question types for classification."""
    MANUFACTURING = "manufacturing"
    REGULATORY = "regulatory"
    MARKET_VALIDATION = "market_validation"
    TECHNICAL_FEASIBILITY = "technical_feasibility"
    COMPETITIVE_LANDSCAPE = "competitive_landscape"
    UNIT_ECONOMICS = "unit_economics"
    GO_TO_MARKET = "go_to_market"
    TEAM_COMPOSITION = "team_composition"
    SCALABILITY = "scalability"
    FUNDING_STRATEGY = "funding_strategy"
    CUSTOMER_DISCOVERY = "customer_discovery"
    RISK_ASSESSMENT = "risk_assessment"


class FollowUpQuestion(BaseModel):
    """A single hyper-targeted follow-up question.

    Each question is tagged with a category so the frontend can display
    contextual icons, and weighted by priority so the most critical
    questions appear first.
    """
    question_id: str = Field(
        description="Unique identifier for this question, e.g. 'q1', 'q2'."
    )
    question_text: str = Field(
        description=(
            "The complete question text to display to the founder. "
            "Must be specific, open-ended, and designed to uncover hidden assumptions."
        )
    )
    category: QuestionCategory = Field(
        description="The thematic category this question falls under."
    )
    rationale: str = Field(
        description=(
            "Internal note (not shown to user) explaining WHY this question matters "
            "for this specific industry. Helps the AI later if context is needed."
        )
    )
    priority: int = Field(
        ge=1,
        le=4,
        default=1,
        description="Display priority: 1 = most critical, 4 = nice-to-have."
    )


class DynamicQuestionSet(BaseModel):
    """Structured output from the Gemini call that generates follow-up questions.

    The model must produce exactly 3-4 questions tailored to the detected
    industry vertical and the founder's initial description.
    """
    questions: list[FollowUpQuestion] = Field(
        min_length=3,
        max_length=4,
        description=(
            "Exactly 3 to 4 hyper-targeted follow-up questions. "
            "Each must be unique, non-overlapping, and designed to expose "
            "hidden assumptions specific to the detected industry."
        )
    )


# ── Phase 3: Final Intake Package ──────────────────────────────────

class IntakeAnswer(BaseModel):
    """A single Q&A pair from the conversation."""
    question_id: str
    question_text: str
    category: QuestionCategory
    answer: str


class IntakePackage(BaseModel):
    """The complete intake package assembled after all questions are answered.

    This is sent to the backend to populate the Project entity and enrich
    the context for the 7-stage pipeline.
    """
    raw_idea: str = Field(description="The founder's original raw idea text.")
    industry: str = Field(description="Detected or confirmed industry vertical.")
    target_audience: str = Field(description="Primary customer persona.")
    core_value_proposition: str = Field(description="Core value proposition sentence.")
    enriched_description: str = Field(
        description=(
            "A 2-3 paragraph enriched description that synthesizes the raw idea "
            "with all follow-up answers. This becomes the Project.description field "
            "fed into the pipeline."
        )
    )
    answers: list[IntakeAnswer] = Field(
        description="All Q&A pairs from the consultation session."
    )


# ── API Request/Response Models ────────────────────────────────────

class IntakeStartRequest(BaseModel):
    """Payload to initiate an intake session."""
    raw_idea: str = Field(
        min_length=10,
        max_length=2000,
        description="The founder's raw startup idea text."
    )


class IntakeStartResponse(BaseModel):
    """Response after the first analysis — returns initial extraction + first question."""
    session_id: str = Field(description="Unique intake session identifier.")
    extraction: ConceptExtraction = Field(description="Initial concept extraction.")
    first_question: FollowUpQuestion = Field(description="The first follow-up question.")


class IntakeMessageRequest(BaseModel):
    """Payload to send a user's answer to a follow-up question."""
    session_id: str
    question_id: str
    answer: str = Field(min_length=1, max_length=2000)


class IntakeMessageResponse(BaseModel):
    """Response after processing an answer — returns next question or final package."""
    next_question: FollowUpQuestion | None = Field(
        description="The next follow-up question, or null if all questions are answered."
    )
    questions_remaining: int = Field(description="Number of questions still pending.")
    is_complete: bool = Field(description="True when all questions have been answered.")


class IntakeFinalizeRequest(BaseModel):
    """Payload to finalize the intake session and get the enriched package."""
    session_id: str


class IntakeFinalizeResponse(BaseModel):
    """Response with the complete intake package ready for pipeline consumption."""
    package: IntakePackage
    project_id: str | None = Field(
        default=None,
        description="If auto-project-creation is enabled, the created project ID."
    )
