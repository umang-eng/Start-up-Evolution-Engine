import uuid
from sqlalchemy import String, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.models.base import Base, UUIDMixin, TimestampMixin


class Meeting(Base, UUIDMixin, TimestampMixin):
    """A conversation/meeting session initiated by a user."""
    __tablename__ = "meetings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="RECORDING", nullable=False
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    speaker_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True, default="en")

    # Relationships
    transcript: Mapped["Transcript | None"] = relationship(
        "Transcript", back_populates="meeting", uselist=False, cascade="all, delete-orphan"
    )
    report: Mapped["MeetingReport | None"] = relationship(
        "MeetingReport", back_populates="meeting", uselist=False, cascade="all, delete-orphan"
    )
    segments: Mapped[list["MeetingSegment"]] = relationship(
        "MeetingSegment", back_populates="meeting", cascade="all, delete-orphan"
    )

    # Relationships to parent models (optional)
    owner: Mapped["User"] = relationship("User")
    project: Mapped["Project | None"] = relationship("Project")


class MeetingSegment(Base, UUIDMixin, TimestampMixin):
    """A timed segment of the meeting (used for streaming transcription)."""
    __tablename__ = "meeting_segments"

    meeting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    speaker: Mapped[str | None] = mapped_column(String(100), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    start_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    end_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    is_final: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relationships
    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="segments")


class Transcript(Base, UUIDMixin, TimestampMixin):
    """Full raw transcript of a meeting, stored exactly as captured."""
    __tablename__ = "transcripts"

    meeting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language_detected: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Relationships
    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="transcript")


class MeetingReport(Base, UUIDMixin, TimestampMixin):
    """AI-generated structured intelligence report from a meeting."""
    __tablename__ = "meeting_reports"

    meeting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), default="PENDING", nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_points: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    decisions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    action_items: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    questions_raised: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    risks_concerns: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    agreements: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    disagreements: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    technical_topics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    business_opportunities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    follow_up_needed: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    overall_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_report_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="report")


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from backend.models.user import User
    from backend.models.project import Project
