import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.models.base import Base, UUIDMixin, TimestampMixin


class DNAResult(Base, UUIDMixin, TimestampMixin):
    """Stores intermediate structured JSON output from the DNA Analyzer."""
    __tablename__ = "dna_results"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Nullable: set by orchestrator after module completes (cache checksum)
    hash_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="dna_result")


class FeatureResult(Base, UUIDMixin, TimestampMixin):
    """Stores intermediate structured JSON output from the Feature Extractor."""
    __tablename__ = "feature_results"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    hash_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="feature_result")


class RoadmapResult(Base, UUIDMixin, TimestampMixin):
    """Stores intermediate structured JSON output from the Roadmap Generator."""
    __tablename__ = "roadmap_results"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    hash_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="roadmap_result")


class TeamResult(Base, UUIDMixin, TimestampMixin):
    """Stores intermediate structured JSON output from the Team Generator."""
    __tablename__ = "team_results"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    hash_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="team_result")


class SWOTResult(Base, UUIDMixin, TimestampMixin):
    """Stores intermediate structured JSON output from the SWOT Builder."""
    __tablename__ = "swot_results"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    hash_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="swot_result")


class CostResult(Base, UUIDMixin, TimestampMixin):
    """Stores intermediate structured JSON output from the Cost Estimator."""
    __tablename__ = "cost_results"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    hash_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="cost_result")


class LegalComplianceResult(Base, UUIDMixin, TimestampMixin):
    """Stores structured JSON output from the Legal & Compliance Doc Generator."""
    __tablename__ = "legal_compliance_results"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    hash_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="legal_compliance_result")


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from backend.models.project import Project
