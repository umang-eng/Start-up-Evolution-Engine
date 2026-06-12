import uuid
from sqlalchemy import Numeric, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.models.base import Base, UUIDMixin, TimestampMixin


class GenerationSession(Base, UUIDMixin, TimestampMixin):
    """Tracks active pipeline workflow runs, statuses, and steps."""
    __tablename__ = "generation_sessions"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="CREATED", nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    current_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    progress_percentage: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="sessions")
    events: Mapped[list["WorkflowEvent"]] = relationship("WorkflowEvent", back_populates="session", cascade="all, delete-orphan")


class WorkflowEvent(Base, UUIDMixin, TimestampMixin):
    """Persists historical event logs for active generator runs."""
    __tablename__ = "workflow_events"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("generation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Relationships
    session: Mapped["GenerationSession"] = relationship("GenerationSession", back_populates="events")


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from backend.models.project import Project
