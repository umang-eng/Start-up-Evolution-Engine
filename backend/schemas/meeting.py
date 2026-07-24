import uuid
from datetime import datetime
from pydantic import BaseModel, Field


# ── Meeting Schemas ───────────────────────────────────────────────

class MeetingCreate(BaseModel):
    """Payload to start a new meeting recording."""
    project_id: uuid.UUID | None = None
    title: str | None = Field(default=None, max_length=500)
    language: str | None = Field(default="en", max_length=10)


class MeetingUpdate(BaseModel):
    """Payload to update meeting metadata after recording stops."""
    title: str | None = Field(default=None, max_length=500)
    duration_seconds: int | None = None
    speaker_count: int | None = None
    status: str | None = None


class MeetingResponse(BaseModel):
    """Meeting metadata returned to client."""
    id: uuid.UUID
    user_id: uuid.UUID
    project_id: uuid.UUID | None
    title: str | None
    status: str
    duration_seconds: int | None
    speaker_count: int | None
    language: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Transcript Schemas ────────────────────────────────────────────

class TranscriptCreate(BaseModel):
    """Payload to upload a completed transcript."""
    raw_text: str = Field(min_length=1)
    language_detected: str | None = None


class TranscriptResponse(BaseModel):
    """Transcript returned to client."""
    id: uuid.UUID
    meeting_id: uuid.UUID
    raw_text: str
    word_count: int | None
    language_detected: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class TranscriptSegment(BaseModel):
    """A single segment for streaming upload."""
    speaker: str | None = None
    text: str
    start_time_ms: int = 0
    end_time_ms: int = 0
    confidence: float | None = None
    is_final: bool = True


class TranscriptBulkCreate(BaseModel):
    """Bulk upload segments for streaming transcription."""
    segments: list[TranscriptSegment]


# ── Meeting Report Schemas ────────────────────────────────────────

class ActionItem(BaseModel):
    task: str
    owner: str | None = None
    priority: str | None = None
    deadline: str | None = None
    status: str = "Pending"


class MeetingReportResponse(BaseModel):
    """Full AI-generated meeting report."""
    id: uuid.UUID
    meeting_id: uuid.UUID
    status: str
    title: str | None
    executive_summary: str | None
    key_points: list[str] | None
    decisions: list[str] | None
    action_items: list[ActionItem] | None
    questions_raised: list[str] | None
    risks_concerns: list[str] | None
    agreements: list[str] | None
    disagreements: list[str] | None
    technical_topics: list[str] | None
    business_opportunities: list[str] | None
    follow_up_needed: list[str] | None
    overall_outcome: str | None
    full_report_markdown: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportGenerateRequest(BaseModel):
    """Request to generate a report from an existing transcript."""
    meeting_id: uuid.UUID
