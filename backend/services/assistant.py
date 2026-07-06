"""
Dynamic Intake Router — Stateful Onboarding Conversation Engine.

Conducts a personalized Q&A session with a founder to refine their startup
concept *before* the 7-stage pipeline is ever triggered.

Flow:
1. Founder submits raw idea → Gemini extracts industry, audience, value prop
2. Based on detected vertical, Gemini generates 3-4 hyper-targeted follow-ups
3. Each answer is collected; once all questions are answered, the engine
   synthesizes everything into an enriched description
4. The enriched package populates the Project entity for pipeline consumption
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from backend.ai.gemini import gemini_adapter
from backend.core.exceptions import BaseBusinessException
from backend.core.logging import logger
from backend.schemas.intake import (
    ConceptExtraction,
    DynamicQuestionSet,
    IntakeAnswer,
    IntakePackage,
)


# ── In-memory session store (production: move to Redis) ─────────────

_intake_sessions: dict[str, dict[str, Any]] = {}


# ── Prompt Templates ────────────────────────────────────────────────

CONCEPT_EXTRACTION_SYSTEM = """You are an elite startup analyst and venture strategist.
Your task is to analyze a raw startup idea and extract structured metadata.

You must identify:
1. The specific industry vertical (be precise: HealthTech, FinTech, EdTech, etc.)
2. The primary target audience (who specifically would pay for this)
3. The core value proposition (one crisp sentence)
4. 2-4 keyword signals that hint at the industry sub-niche

Be specific and nuanced. Avoid generic labels like "Tech" or "Software".
If the idea spans multiple verticals, pick the PRIMARY one."""


CONCEPT_EXTRACTION_USER = """Analyze this startup idea and extract the structured metadata:

"{{ raw_idea }}"

Return ONLY a JSON object matching the required schema."""


FOLLOW_UP_QUESTIONS_SYSTEM = """You are an elite startup accelerator director and industry expert.

Given a startup idea with its detected industry vertical, generate exactly 3 to 4
hyper-targeted follow-up questions designed to uncover HIDDEN ASSUMPTIONS.

CRITICAL RULES:
- Questions must be INDUSTRY-SPECIFIC. Generic questions are forbidden.
- Each question should challenge a hidden assumption the founder likely hasn't considered.
- Questions must be open-ended (not yes/no).
- Questions should be specific enough that the answer directly feeds into business planning.
- Prioritize the most critical gaps in the founder's reasoning.

INDUSTRY-SPECIFIC QUESTION EXAMPLES:
- Hardware/IoT: manufacturing scale, supply chain, unit cost at volume, regulatory certifications
- FinTech: regulatory compliance, licensing requirements, fraud risk, banking partnerships
- HealthTech: HIPAA compliance, clinical validation, physician adoption, insurance integration
- SaaS: churn rates, sales cycle length, integration complexity, competitive moat
- Marketplace: supply/demand cold-start, take rate sensitivity, geographic expansion
- AI/ML: data moat, model accuracy benchmarks, compute costs, ethical concerns
- E-commerce: unit economics, logistics complexity, customer acquisition cost, seasonality
- BioTech: clinical trial timeline, IP protection, FDA pathway, manufacturing scalability
- CleanTech: government incentives, installation complexity, payback period, regulatory support

Return EXACTLY 3 to 4 questions. No more, no less."""


FOLLOW_UP_QUESTIONS_USER = """Startup Idea: {{ raw_idea }}
Detected Industry: {{ industry }}
Target Audience: {{ target_audience }}
Core Value Proposition: {{ core_value_proposition }}
Sub-niche Signals: {{ vertical_signals }}

Generate the 3-4 most critical follow-up questions for this specific startup.
Return ONLY a JSON object matching the required schema."""


SYNTHESIS_SYSTEM = """You are an elite startup strategist writing a comprehensive concept brief.

Given a founder's raw idea and their answers to targeted consultation questions,
synthesize everything into a rich, cohesive 2-3 paragraph description.

This description will be fed into an AI pipeline that generates:
- Business DNA analysis
- Feature architecture
- Development roadmap
- Team structure
- SWOT analysis
- Financial projections

Write the description to give the pipeline maximum context:
- Include specific industry details, regulatory landscape, and market dynamics
- Incorporate the founder's unique insights from their answers
- Highlight technical constraints and opportunities mentioned
- Preserve specific numbers, timelines, and targets the founder provided
- Be factual and precise — no marketing fluff

The output should read like a compact but thorough concept document."""


SYNTHESIS_USER = """Original Idea:
{{ raw_idea }}

Industry: {{ industry }}
Target Audience: {{ target_audience }}
Value Proposition: {{ core_value_proposition }}

Consultation Q&A:
{% for qa in qa_pairs %}
Q: {{ qa.question }}
A: {{ qa.answer }}
{% endfor %}

Synthesize all of the above into a comprehensive 2-3 paragraph startup concept brief.
Return ONLY the text, no JSON wrapping."""


# ── Core Service Functions ──────────────────────────────────────────

async def start_intake_session(raw_idea: str) -> dict[str, Any]:
    """Initiate a new intake session.

    1. Run concept extraction on the raw idea
    2. Generate industry-specific follow-up questions
    3. Store session state
    4. Return the extraction + first question
    """
    session_id = str(uuid.uuid4())

    logger.info(f"Starting intake session {session_id} for idea: {raw_idea[:80]}...")

    # Phase 1: Extract concept metadata
    extraction = await gemini_adapter.generate(
        prompt=_render(CONCEPT_EXTRACTION_USER, {"raw_idea": raw_idea}),
        schema=ConceptExtraction,
        system_instruction=CONCEPT_EXTRACTION_SYSTEM,
    )

    logger.info(
        f"Concept extracted | session={session_id} "
        f"industry={extraction.industry} audience={extraction.target_audience[:40]}"
    )

    # Phase 2: Generate follow-up questions
    follow_ups = await _generate_follow_up_questions(
        raw_idea=raw_idea,
        extraction=extraction,
    )

    # Store session state
    _intake_sessions[session_id] = {
        "raw_idea": raw_idea,
        "extraction": extraction,
        "questions": follow_ups.questions,
        "answers": [],
        "current_index": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    first_question = follow_ups.questions[0] if follow_ups.questions else None

    return {
        "session_id": session_id,
        "extraction": extraction,
        "first_question": first_question,
        "total_questions": len(follow_ups.questions),
    }


async def submit_answer(
    session_id: str,
    question_id: str,
    answer: str,
) -> dict[str, Any]:
    """Process a user's answer and return the next question.

    Validates the session exists, matches the question_id to the current
    question, stores the answer, and advances to the next question.
    """
    session = _get_session(session_id)

    questions = session["questions"]
    current_index = session["current_index"]

    # Validate question_id matches the current question
    if current_index >= len(questions):
        raise BaseBusinessException(
            message="All questions have already been answered. Please finalize the session.",
            code="INTAKE_COMPLETE",
            status_code=400,
        )

    current_question = questions[current_index]
    if current_question.question_id != question_id:
        raise BaseBusinessException(
            message=f"Expected answer for question '{current_question.question_id}', got '{question_id}'.",
            code="QUESTION_MISMATCH",
            status_code=400,
        )

    # Store the answer
    session["answers"].append({
        "question_id": question_id,
        "question_text": current_question.question_text,
        "category": current_question.category,
        "answer": answer,
    })
    session["current_index"] = current_index + 1

    # Determine next question
    next_index = session["current_index"]
    questions_remaining = len(questions) - next_index
    is_complete = questions_remaining == 0

    next_question = questions[next_index] if not is_complete else None

    logger.info(
        f"Answer recorded | session={session_id} "
        f"question={question_id} remaining={questions_remaining}"
    )

    return {
        "next_question": next_question,
        "questions_remaining": questions_remaining,
        "is_complete": is_complete,
    }


async def finalize_session(session_id: str) -> IntakePackage:
    """Synthesize all Q&A into a comprehensive enriched description.

    This is the final step before the Project entity is populated and
    the 7-stage pipeline is triggered.
    """
    session = _get_session(session_id)

    if session["current_index"] < len(session["questions"]):
        remaining = len(session["questions"]) - session["current_index"]
        raise BaseBusinessException(
            message=f"{remaining} questions remain unanswered. Complete all questions first.",
            code="INTAKE_INCOMPLETE",
            status_code=400,
        )

    extraction = session["extraction"]
    answers = session["answers"]

    # Synthesize enriched description via Gemini
    from jinja2 import Template

    synthesis_prompt = Template(SYNTHESIS_USER).render(
        raw_idea=session["raw_idea"],
        industry=extraction.industry,
        target_audience=extraction.target_audience,
        core_value_proposition=extraction.core_value_proposition,
        qa_pairs=answers,
    )

    enriched_description = await gemini_adapter.generate_text(
        prompt=synthesis_prompt,
        system_instruction=SYNTHESIS_SYSTEM,
    )

    # Build the intake package
    intake_answers = [
        IntakeAnswer(
            question_id=a["question_id"],
            question_text=a["question_text"],
            category=a["category"],
            answer=a["answer"],
        )
        for a in answers
    ]

    package = IntakePackage(
        raw_idea=session["raw_idea"],
        industry=extraction.industry,
        target_audience=extraction.target_audience,
        core_value_proposition=extraction.core_value_proposition,
        enriched_description=enriched_description,
        answers=intake_answers,
    )

    # Clean up session
    del _intake_sessions[session_id]

    logger.info(f"Intake session finalized | session={session_id} answers={len(answers)}")

    return package


# ── Helper Functions ────────────────────────────────────────────────

async def _generate_follow_up_questions(
    raw_idea: str,
    extraction: ConceptExtraction,
) -> DynamicQuestionSet:
    """Generate industry-specific follow-up questions via Gemini."""
    variables = {
        "raw_idea": raw_idea,
        "industry": extraction.industry,
        "target_audience": extraction.target_audience,
        "core_value_proposition": extraction.core_value_proposition,
        "vertical_signals": ", ".join(extraction.detected_vertical_signals),
    }

    result = await gemini_adapter.generate(
        prompt=_render(FOLLOW_UP_QUESTIONS_USER, variables),
        schema=DynamicQuestionSet,
        system_instruction=FOLLOW_UP_QUESTIONS_SYSTEM,
    )

    # Assign sequential question IDs
    for idx, q in enumerate(result.questions):
        q.question_id = f"q{idx + 1}"

    return result


def _get_session(session_id: str) -> dict[str, Any]:
    """Retrieve an intake session or raise if not found."""
    session = _intake_sessions.get(session_id)
    if not session:
        raise BaseBusinessException(
            message=f"Intake session '{session_id}' not found or has expired.",
            code="SESSION_NOT_FOUND",
            status_code=404,
        )
    return session


def _render(template_str: str, variables: dict[str, Any]) -> str:
    """Render a Jinja2 template string with variables."""
    from jinja2 import Template
    return Template(template_str).render(**variables)
