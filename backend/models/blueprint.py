import uuid
from sqlalchemy import Numeric, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.models.base import Base, UUIDMixin, TimestampMixin


class Blueprint(Base, UUIDMixin, TimestampMixin):
    """Aggregated strategic compiled startup blueprint data store."""
    __tablename__ = "blueprints"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    health_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    # Nullable: set by orchestrator after module completes (cache checksum)
    hash_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="blueprint")


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from backend.models.project import Project
