import uuid
from sqlalchemy import Numeric, String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.models.base import Base, UUIDMixin, TimestampMixin


class AnalyticsLog(Base, UUIDMixin, TimestampMixin):
    """Logs token consumption, costs, and response metrics for LLM operations."""
    __tablename__ = "analytics_logs"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    module_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost_usd: Mapped[float] = mapped_column(Numeric(10, 6), default=0.0, nullable=False)

    # Relationships
    project: Mapped["Project"] = relationship("Project")


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from backend.models.project import Project
