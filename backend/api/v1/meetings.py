import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_token_payload
from backend.database.session import get_db
from backend.schemas.base import BaseResponse, APIResponseMetadata
from backend.schemas.meeting import (
    MeetingCreate, MeetingUpdate, MeetingResponse,
    TranscriptCreate, TranscriptResponse, TranscriptBulkCreate,
    MeetingReportResponse, ReportGenerateRequest,
)
from backend.services.meeting import (
    create_meeting, update_meeting_status, finalize_transcript,
    generate_meeting_report,
)
from backend.services.transcription import transcribe_audio
from backend.repositories.meeting import (
    meeting_repository, transcript_repository, meeting_report_repository,
)

router = APIRouter(prefix="/meetings", tags=["Conversation Intelligence"])


# ── Meeting Endpoints ─────────────────────────────────────────────

@router.post("", response_model=BaseResponse[MeetingResponse], status_code=status.HTTP_201_CREATED)
async def start_meeting(
    payload: MeetingCreate,
    claims: dict[str, Any] = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Start a new meeting recording session."""
    user_id = uuid.UUID(claims["sub"])
    meeting = await create_meeting(
        db,
        user_id=user_id,
        project_id=payload.project_id,
        title=payload.title,
        language=payload.language or "en",
    )
    return {
        "success": True,
        "data": MeetingResponse.model_validate(meeting),
        "metadata": APIResponseMetadata(),
    }


@router.get("", response_model=BaseResponse[list[MeetingResponse]])
async def list_my_meetings(
    claims: dict[str, Any] = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
    offset: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    """List all meetings for the authenticated user."""
    user_id = uuid.UUID(claims["sub"])
    meetings = await meeting_repository.get_user_meetings(
        db, user_id=user_id, offset=offset, limit=limit,
    )
    return {
        "success": True,
        "data": [MeetingResponse.model_validate(m) for m in meetings],
        "metadata": APIResponseMetadata(),
    }


@router.get("/{meeting_id}", response_model=BaseResponse[MeetingResponse])
async def get_meeting(
    meeting_id: uuid.UUID,
    claims: dict[str, Any] = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get a single meeting by ID (with transcript and report)."""
    user_id = uuid.UUID(claims["sub"])
    meeting = await meeting_repository.get_by_meeting_and_user(db, meeting_id, user_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    return {
        "success": True,
        "data": MeetingResponse.model_validate(meeting),
        "metadata": APIResponseMetadata(),
    }


@router.patch("/{meeting_id}", response_model=BaseResponse[MeetingResponse])
async def update_meeting(
    meeting_id: uuid.UUID,
    payload: MeetingUpdate,
    claims: dict[str, Any] = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update meeting metadata (title, status, duration, speakers)."""
    user_id = uuid.UUID(claims["sub"])
    meeting = await meeting_repository.get_by_meeting_and_user(db, meeting_id, user_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    update_data = payload.model_dump(exclude_unset=True)
    updated = await update_meeting_status(db, meeting_id=meeting_id, **update_data)
    return {
        "success": True,
        "data": MeetingResponse.model_validate(updated),
        "metadata": APIResponseMetadata(),
    }


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting(
    meeting_id: uuid.UUID,
    claims: dict[str, Any] = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a meeting and all associated transcripts/reports."""
    user_id = uuid.UUID(claims["sub"])
    meeting = await meeting_repository.get_by_meeting_and_user(db, meeting_id, user_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    await meeting_repository.remove(db, id=meeting_id)


# ── Transcript Endpoints ──────────────────────────────────────────

@router.post("/{meeting_id}/transcript", response_model=BaseResponse[TranscriptResponse])
async def upload_transcript(
    meeting_id: uuid.UUID,
    payload: TranscriptCreate,
    claims: dict[str, Any] = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Upload a complete transcript for a meeting."""
    user_id = uuid.UUID(claims["sub"])
    meeting = await meeting_repository.get_by_meeting_and_user(db, meeting_id, user_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    transcript = await finalize_transcript(
        db,
        meeting_id=meeting_id,
        raw_text=payload.raw_text,
        language_detected=payload.language_detected,
    )
    # Update meeting status
    await update_meeting_status(db, meeting_id=meeting_id, status="TRANSCRIBED")
    return {
        "success": True,
        "data": TranscriptResponse.model_validate(transcript),
        "metadata": APIResponseMetadata(),
    }


@router.post("/{meeting_id}/transcript/segments")
async def upload_transcript_segments(
    meeting_id: uuid.UUID,
    payload: TranscriptBulkCreate,
    claims: dict[str, Any] = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Upload transcription segments (streaming speech-to-text)."""
    user_id = uuid.UUID(claims["sub"])
    meeting = await meeting_repository.get_by_meeting_and_user(db, meeting_id, user_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    from backend.services.meeting import add_transcript_segments
    segments_data = [s.model_dump() for s in payload.segments]
    await add_transcript_segments(db, meeting_id=meeting_id, segments=segments_data)
    return {
        "success": True,
        "data": {"segments_added": len(segments_data)},
        "metadata": APIResponseMetadata(),
    }


@router.post("/{meeting_id}/transcript/audio", response_model=BaseResponse[TranscriptResponse])
async def upload_audio_for_transcription(
    meeting_id: uuid.UUID,
    file: UploadFile = File(...),
    language: str | None = Form(default=None),
    claims: dict[str, Any] = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Upload audio file → Whisper.cpp transcribes → saves transcript."""
    user_id = uuid.UUID(claims["sub"])
    meeting = await meeting_repository.get_by_meeting_and_user(db, meeting_id, user_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    # Read audio bytes
    audio_bytes = await file.read()
    if len(audio_bytes) < 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio file is too small or empty")

    # Transcribe via Whisper
    try:
        result = await transcribe_audio(
            audio_bytes=audio_bytes,
            filename=file.filename or "audio.webm",
            language=language,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    raw_text = result.get("text", "").strip()
    if not raw_text:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No speech detected in audio")

    # Save transcript
    transcript = await finalize_transcript(
        db,
        meeting_id=meeting_id,
        raw_text=raw_text,
        language_detected=result.get("language"),
    )
    await update_meeting_status(
        db, meeting_id=meeting_id, status="TRANSCRIBED",
        duration_seconds=int(result.get("duration", 0)),
    )

    return {
        "success": True,
        "data": TranscriptResponse.model_validate(transcript),
        "metadata": APIResponseMetadata(),
    }


@router.get("/{meeting_id}/transcript", response_model=BaseResponse[TranscriptResponse])
async def get_transcript(
    meeting_id: uuid.UUID,
    claims: dict[str, Any] = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Fetch the transcript for a meeting."""
    user_id = uuid.UUID(claims["sub"])
    meeting = await meeting_repository.get_by_meeting_and_user(db, meeting_id, user_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    transcript = await transcript_repository.get_by_meeting(db, meeting_id)
    if not transcript:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found")
    return {
        "success": True,
        "data": TranscriptResponse.model_validate(transcript),
        "metadata": APIResponseMetadata(),
    }


# ── Report Endpoints ──────────────────────────────────────────────

@router.post("/{meeting_id}/report/generate", response_model=BaseResponse[MeetingReportResponse])
async def generate_report(
    meeting_id: uuid.UUID,
    claims: dict[str, Any] = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate an AI intelligence report from a meeting transcript."""
    user_id = uuid.UUID(claims["sub"])
    meeting = await meeting_repository.get_by_meeting_and_user(db, meeting_id, user_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    report = await generate_meeting_report(db, meeting_id=meeting_id)
    return {
        "success": True,
        "data": MeetingReportResponse.model_validate(report),
        "metadata": APIResponseMetadata(),
    }


@router.get("/{meeting_id}/report", response_model=BaseResponse[MeetingReportResponse])
async def get_report(
    meeting_id: uuid.UUID,
    claims: dict[str, Any] = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Fetch the AI-generated report for a meeting."""
    user_id = uuid.UUID(claims["sub"])
    meeting = await meeting_repository.get_by_meeting_and_user(db, meeting_id, user_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    report = await meeting_report_repository.get_by_meeting(db, meeting_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found. Generate one first.")
    return {
        "success": True,
        "data": MeetingReportResponse.model_validate(report),
        "metadata": APIResponseMetadata(),
    }


# ── Intelligence Engine Endpoints ────────────────────────────────

@router.get("/{meeting_id}/health")
async def get_meeting_health(
    meeting_id: uuid.UUID,
    claims: dict[str, Any] = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Run health analysis on a meeting's transcript across 9 dimensions."""
    user_id = uuid.UUID(claims["sub"])
    meeting = await meeting_repository.get_by_meeting_and_user(db, meeting_id, user_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    transcript = await transcript_repository.get_by_meeting(db, meeting_id)
    if not transcript:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found")

    from backend.modules.meeting_health.engine import MeetingHealthEngine
    engine = MeetingHealthEngine()

    participants = [f"Speaker {meeting.speaker_count or i}" for i in range(1, (meeting.speaker_count or 2) + 1)]
    duration_str = f"{meeting.duration_seconds // 60}m {meeting.duration_seconds % 60}s" if meeting.duration_seconds else "unknown"

    health_report = await engine.analyze(
        meeting_id=str(meeting_id),
        title=meeting.title or "Untitled Meeting",
        duration=duration_str,
        participants=participants,
        transcript=transcript.raw_text,
    )
    return {
        "success": True,
        "data": health_report.model_dump(),
        "metadata": APIResponseMetadata(),
    }


@router.get("/{meeting_id}/timeline")
async def get_meeting_timeline(
    meeting_id: uuid.UUID,
    claims: dict[str, Any] = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Extract timeline-worthy events from a meeting transcript."""
    user_id = uuid.UUID(claims["sub"])
    meeting = await meeting_repository.get_by_meeting_and_user(db, meeting_id, user_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    transcript = await transcript_repository.get_by_meeting(db, meeting_id)
    if not transcript:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found")

    from backend.modules.meeting_timeline.engine import TimelineEngine
    project_id = str(meeting.project_id) if meeting.project_id else str(meeting_id)
    engine = TimelineEngine(project_id=project_id)

    participants = [f"Speaker {meeting.speaker_count or i}" for i in range(1, (meeting.speaker_count or 2) + 1)]

    events = await engine.extract_events(
        meeting_id=str(meeting_id),
        title=meeting.title or "Untitled Meeting",
        date=meeting.created_at.isoformat(),
        participants=participants,
        transcript=transcript.raw_text,
    )
    return {
        "success": True,
        "data": {
            "events": [e.model_dump() for e in events],
            "total_events": len(events),
            "meeting_id": str(meeting_id),
        },
        "metadata": APIResponseMetadata(),
    }


@router.post("/{meeting_id}/analyze")
async def analyze_meeting(
    meeting_id: uuid.UUID,
    claims: dict[str, Any] = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Run all intelligence engines on a meeting: health analysis + timeline extraction."""
    user_id = uuid.UUID(claims["sub"])
    meeting = await meeting_repository.get_by_meeting_and_user(db, meeting_id, user_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    transcript = await transcript_repository.get_by_meeting(db, meeting_id)
    if not transcript:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found")

    participants = [f"Speaker {meeting.speaker_count or i}" for i in range(1, (meeting.speaker_count or 2) + 1)]
    duration_str = f"{meeting.duration_seconds // 60}m {meeting.duration_seconds % 60}s" if meeting.duration_seconds else "unknown"

    # Run health analysis
    from backend.modules.meeting_health.engine import MeetingHealthEngine
    health_engine = MeetingHealthEngine()
    health_report = await health_engine.analyze(
        meeting_id=str(meeting_id),
        title=meeting.title or "Untitled Meeting",
        duration=duration_str,
        participants=participants,
        transcript=transcript.raw_text,
    )

    # Run timeline extraction
    from backend.modules.meeting_timeline.engine import TimelineEngine
    project_id = str(meeting.project_id) if meeting.project_id else str(meeting_id)
    timeline_engine = TimelineEngine(project_id=project_id)
    events = await timeline_engine.extract_events(
        meeting_id=str(meeting_id),
        title=meeting.title or "Untitled Meeting",
        date=meeting.created_at.isoformat(),
        participants=participants,
        transcript=transcript.raw_text,
    )

    return {
        "success": True,
        "data": {
            "health": health_report.model_dump(),
            "timeline": {
                "events": [e.model_dump() for e in events],
                "total_events": len(events),
            },
            "meeting_id": str(meeting_id),
        },
        "metadata": APIResponseMetadata(),
    }
