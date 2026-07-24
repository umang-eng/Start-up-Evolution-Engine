"""
Meeting Intelligence Service — AI-powered conversation analysis and report generation.

Handles the full pipeline: transcript cleanup → LLM analysis → structured report.
"""

import json
import uuid
from datetime import datetime, timezone

from backend.ai.gemini import gemini_adapter
from backend.core.logging import logger
from backend.database.session import AsyncSessionLocal
from backend.models.meeting import Meeting, MeetingReport, Transcript, MeetingSegment
from backend.repositories.meeting import (
    meeting_repository,
    transcript_repository,
    meeting_report_repository,
)


# ── Transcript Cleanup ────────────────────────────────────────────

FILLER_WORDS = {
    "um", "uh", "hmm", "hmmm", "like", "you know", "i mean",
    "so", "basically", "actually", "right", "ok", "okay", "yeah",
    "yes", "no", "well", "uhh", "umm", "err", "ah", "eh",
}

REPEATED_PATTERNS = [
    "i think that", "the thing is", "what i mean is",
    "at the end of the day", "to be honest", "if that makes sense",
]


def clean_transcript(raw_text: str) -> str:
    """Remove filler words, merge duplicate sentences, clean formatting."""
    lines = raw_text.split("\n")
    cleaned = []
    seen = set()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Remove filler words from line
        words = line.split()
        filtered = [w for w in words if w.lower().strip(".,!?;:") not in FILLER_WORDS]
        cleaned_line = " ".join(filtered).strip()

        if not cleaned_line or len(cleaned_line) < 5:
            continue

        # Deduplicate lines
        normalized = cleaned_line.lower().strip(".,!?;:")
        if normalized in seen:
            continue
        seen.add(normalized)

        cleaned.append(cleaned_line)

    return "\n".join(cleaned)


# ── Report Generation Prompt ──────────────────────────────────────

REPORT_SYSTEM_PROMPT = """You are an elite business analyst and meeting intelligence specialist.

Your task is to analyze a meeting transcript and produce a comprehensive, structured intelligence report.

Rules:
- Remove all filler words ("um", "hmm", "like", etc.)
- Ignore repeated sentences and merge duplicate ideas
- Identify speakers if possible (Speaker A, Speaker B, etc.)
- Detect action items, deadlines, priorities, commitments, tasks
- Detect open questions, decisions, important numbers
- Preserve critical technical details
- Infer the meeting title
- The report should read as if written by a professional business analyst
- Be concise but thorough
- For action items, use the exact format: task, owner (if mentioned), priority (if detectable), deadline (if mentioned), status = "Pending"

Return ONLY a JSON object with this exact structure:
{
    "title": "Auto-inferred meeting title",
    "executive_summary": "2-4 concise paragraphs explaining the discussion",
    "key_points": ["bullet list of major topics discussed"],
    "decisions": ["list every decision finalized"],
    "action_items": [
        {
            "task": "description of the task",
            "owner": "person responsible or null",
            "priority": "HIGH/MEDIUM/LOW or null",
            "deadline": "date/time if mentioned or null",
            "status": "Pending"
        }
    ],
    "questions_raised": ["important questions that were asked"],
    "risks_concerns": ["risks or concerns mentioned"],
    "agreements": ["things everyone agreed on"],
    "disagreements": ["points of disagreement"],
    "technical_topics": ["technical subjects discussed"],
    "business_opportunities": ["business opportunities mentioned"],
    "follow_up_needed": ["items requiring follow-up"],
    "overall_outcome": "1-2 sentence summary of the meeting outcome"
}

IMPORTANT: Return ONLY the JSON object. No markdown, no explanation, no preamble."""


# ── Service Functions ─────────────────────────────────────────────

async def create_meeting(
    db: AsyncSessionLocal,
    *,
    user_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
    title: str | None = None,
    language: str = "en",
) -> Meeting:
    """Create a new meeting session."""
    meeting = Meeting(
        user_id=user_id,
        project_id=project_id,
        title=title,
        status="RECORDING",
        language=language,
    )
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)
    return meeting


async def update_meeting_status(
    db: AsyncSessionLocal,
    *,
    meeting_id: uuid.UUID,
    status: str,
    duration_seconds: int | None = None,
    speaker_count: int | None = None,
    title: str | None = None,
) -> Meeting:
    """Update meeting metadata after recording stops."""
    meeting = await meeting_repository.get(db, meeting_id)
    if not meeting:
        raise ValueError("Meeting not found")

    update_data = {"status": status}
    if duration_seconds is not None:
        update_data["duration_seconds"] = duration_seconds
    if speaker_count is not None:
        update_data["speaker_count"] = speaker_count
    if title is not None:
        update_data["title"] = title

    return await meeting_repository.update(db, db_obj=meeting, obj_in=update_data)


async def add_transcript_segments(
    db: AsyncSessionLocal,
    *,
    meeting_id: uuid.UUID,
    segments: list[dict],
) -> None:
    """Add transcription segments to a meeting."""
    for seg in segments:
        segment = MeetingSegment(
            meeting_id=meeting_id,
            speaker=seg.get("speaker"),
            text=seg["text"],
            start_time_ms=seg.get("start_time_ms", 0),
            end_time_ms=seg.get("end_time_ms", 0),
            confidence=seg.get("confidence"),
            is_final=seg.get("is_final", True),
        )
        db.add(segment)
    await db.commit()


async def finalize_transcript(
    db: AsyncSessionLocal,
    *,
    meeting_id: uuid.UUID,
    raw_text: str,
    language_detected: str | None = None,
) -> Transcript:
    """Store the complete raw transcript for a meeting."""
    # Check if transcript already exists
    existing = await transcript_repository.get_by_meeting(db, meeting_id)
    if existing:
        return existing

    word_count = len(raw_text.split())
    transcript = Transcript(
        meeting_id=meeting_id,
        raw_text=raw_text,
        word_count=word_count,
        language_detected=language_detected,
    )
    db.add(transcript)
    await db.commit()
    await db.refresh(transcript)
    return transcript


async def generate_meeting_report(
    db: AsyncSessionLocal,
    *,
    meeting_id: uuid.UUID,
) -> MeetingReport:
    """
    Generate an AI-powered intelligence report from a meeting's transcript.

    Pipeline:
    1. Fetch transcript
    2. Clean transcript (remove fillers, deduplicate)
    3. Send to LLM for analysis
    4. Parse structured response
    5. Store report in database
    """
    # 1. Fetch meeting and transcript
    meeting = await meeting_repository.get_with_relations(db, meeting_id)
    if not meeting:
        raise ValueError("Meeting not found")

    transcript = await transcript_repository.get_by_meeting(db, meeting_id)
    if not transcript:
        raise ValueError("Transcript not found. Upload a transcript before generating a report.")

    # 2. Create or update report record as PENDING
    report = await meeting_report_repository.get_by_meeting(db, meeting_id)
    if not report:
        report = MeetingReport(meeting_id=meeting_id, status="PROCESSING")
        db.add(report)
        await db.commit()
        await db.refresh(report)
    else:
        await meeting_report_repository.update(
            db, db_obj=report, obj_in={"status": "PROCESSING", "error_message": None}
        )

    # 3. Clean transcript
    cleaned_text = clean_transcript(transcript.raw_text)

    # 4. Generate report via LLM
    user_prompt = f"Analyze this meeting transcript and generate a structured intelligence report:\n\n{cleaned_text}"

    try:
        raw_response = await gemini_adapter.generate_text(
            prompt=user_prompt,
            system_instruction=REPORT_SYSTEM_PROMPT,
        )

        # 5. Parse JSON response
        # Strip markdown code fences if present
        text = raw_response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]  # remove opening ```json
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        report_data = json.loads(text)

        # 6. Update report with structured data
        update_fields = {
            "status": "COMPLETED",
            "title": report_data.get("title", meeting.title or "Untitled Meeting"),
            "executive_summary": report_data.get("executive_summary"),
            "key_points": report_data.get("key_points"),
            "decisions": report_data.get("decisions"),
            "action_items": report_data.get("action_items"),
            "questions_raised": report_data.get("questions_raised"),
            "risks_concerns": report_data.get("risks_concerns"),
            "agreements": report_data.get("agreements"),
            "disagreements": report_data.get("disagreements"),
            "technical_topics": report_data.get("technical_topics"),
            "business_opportunities": report_data.get("business_opportunities"),
            "follow_up_needed": report_data.get("follow_up_needed"),
            "overall_outcome": report_data.get("overall_outcome"),
            "full_report_markdown": _build_markdown(report_data),
            "report_metadata": {
                "word_count": transcript.word_count,
                "cleaned_word_count": len(cleaned_text.split()),
                "model": "gemini",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        report = await meeting_report_repository.update(
            db, db_obj=report, obj_in=update_fields
        )

        # 7. Update meeting title if inferred
        if report.title and not meeting.title:
            await meeting_repository.update(
                db, db_obj=meeting, obj_in={"title": report.title, "status": "ANALYZED"}
            )
        else:
            await meeting_repository.update(
                db, db_obj=meeting, obj_in={"status": "ANALYZED"}
            )

        logger.info(f"Report generated for meeting {meeting_id}")
        return report

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        await meeting_report_repository.update(
            db, db_obj=report, obj_in={
                "status": "FAILED",
                "error_message": f"Failed to parse AI response: {str(e)}",
            }
        )
        raise
    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=e)
        await meeting_report_repository.update(
            db, db_obj=report, obj_in={
                "status": "FAILED",
                "error_message": str(e),
            }
        )
        raise


def _build_markdown(data: dict) -> str:
    """Build a clean markdown report from structured data."""
    sections = []

    if data.get("title"):
        sections.append(f"# {data['title']}\n")

    if data.get("executive_summary"):
        sections.append(f"## Executive Summary\n\n{data['executive_summary']}\n")

    if data.get("key_points"):
        sections.append("## Key Discussion Points\n")
        for p in data["key_points"]:
            sections.append(f"- {p}")
        sections.append("")

    if data.get("decisions"):
        sections.append("## Decisions Made\n")
        for d in data["decisions"]:
            sections.append(f"- {d}")
        sections.append("")

    if data.get("action_items"):
        sections.append("## Action Items\n")
        sections.append("| Task | Owner | Priority | Deadline | Status |")
        sections.append("|------|-------|----------|----------|--------|")
        for item in data["action_items"]:
            if isinstance(item, dict):
                task = item.get("task", "")
                owner = item.get("owner", "-")
                priority = item.get("priority", "-")
                deadline = item.get("deadline", "-")
                status = item.get("status", "Pending")
                sections.append(f"| {task} | {owner} | {priority} | {deadline} | {status} |")
            else:
                sections.append(f"| {item} | - | - | - | Pending |")
        sections.append("")

    if data.get("questions_raised"):
        sections.append("## Important Questions Raised\n")
        for q in data["questions_raised"]:
            sections.append(f"- {q}")
        sections.append("")

    if data.get("risks_concerns"):
        sections.append("## Risks / Concerns\n")
        for r in data["risks_concerns"]:
            sections.append(f"- {r}")
        sections.append("")

    if data.get("agreements"):
        sections.append("## Agreements\n")
        for a in data["agreements"]:
            sections.append(f"- {a}")
        sections.append("")

    if data.get("disagreements"):
        sections.append("## Disagreements\n")
        for d in data["disagreements"]:
            sections.append(f"- {d}")
        sections.append("")

    if data.get("technical_topics"):
        sections.append("## Technical Topics Discussed\n")
        for t in data["technical_topics"]:
            sections.append(f"- {t}")
        sections.append("")

    if data.get("business_opportunities"):
        sections.append("## Business Opportunities Mentioned\n")
        for b in data["business_opportunities"]:
            sections.append(f"- {b}")
        sections.append("")

    if data.get("follow_up_needed"):
        sections.append("## Follow-up Needed\n")
        for f in data["follow_up_needed"]:
            sections.append(f"- {f}")
        sections.append("")

    if data.get("overall_outcome"):
        sections.append(f"## Overall Outcome\n\n{data['overall_outcome']}\n")

    return "\n".join(sections)
