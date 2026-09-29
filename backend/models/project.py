import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.models.base import Base, UUIDMixin, TimestampMixin


class Project(Base, UUIDMixin, TimestampMixin):
    """Core workspace mapping projects created by founders."""
    __tablename__ = "projects"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    region: Mapped[str | None] = mapped_column(String(10), nullable=True, default="US",
        comment="ISO 3166-1 alpha-2 country code for regional compliance search (e.g. IN, US, GB)")

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="projects")
    
    # 1-to-1 result tables
    blueprint: Mapped["Blueprint"] = relationship("Blueprint", back_populates="project", cascade="all, delete-orphan", uselist=False)
    dna_result: Mapped["DNAResult"] = relationship("DNAResult", back_populates="project", cascade="all, delete-orphan", uselist=False)
    feature_result: Mapped["FeatureResult"] = relationship("FeatureResult", back_populates="project", cascade="all, delete-orphan", uselist=False)
    roadmap_result: Mapped["RoadmapResult"] = relationship("RoadmapResult", back_populates="project", cascade="all, delete-orphan", uselist=False)
    team_result: Mapped["TeamResult"] = relationship("TeamResult", back_populates="project", cascade="all, delete-orphan", uselist=False)
    swot_result: Mapped["SWOTResult"] = relationship("SWOTResult", back_populates="project", cascade="all, delete-orphan", uselist=False)
    cost_result: Mapped["CostResult"] = relationship("CostResult", back_populates="project", cascade="all, delete-orphan", uselist=False)
    legal_compliance_result: Mapped["LegalComplianceResult"] = relationship("LegalComplianceResult", back_populates="project", cascade="all, delete-orphan", uselist=False)

    # 1-to-many relationship mappings
    versions: Mapped[list["ProjectVersion"]] = relationship("ProjectVersion", back_populates="project", cascade="all, delete-orphan")
    sessions: Mapped[list["GenerationSession"]] = relationship("GenerationSession", back_populates="project", cascade="all, delete-orphan")


class ProjectVersion(Base, UUIDMixin, TimestampMixin):
    """Immutable Git-like version snapshots for projects.

    Each version links to the exact stage result row IDs and their checksums,
    enabling precise reconstruction of any historical pipeline state.
    """
    __tablename__ = "project_versions"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    version_label: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., '1.0.0'
    message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    snapshot_data: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # ── Stage snapshot foreign keys ──────────────────────────────
    # Each FK points to the specific result row ID for that stage at snapshot time.
    # This allows reconstructing any historical version without relying on the
    # mutable JSON snapshot_data alone.
    dna_result_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("dna_results.id", ondelete="SET NULL"), nullable=True)
    feature_result_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("feature_results.id", ondelete="SET NULL"), nullable=True)
    roadmap_result_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("roadmap_results.id", ondelete="SET NULL"), nullable=True)
    team_result_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("team_results.id", ondelete="SET NULL"), nullable=True)
    swot_result_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("swot_results.id", ondelete="SET NULL"), nullable=True)
    cost_result_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cost_results.id", ondelete="SET NULL"), nullable=True)
    blueprint_result_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("blueprints.id", ondelete="SET NULL"), nullable=True)

    # Checksum snapshot: maps stage name → hash_checksum at version time
    checksum_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="versions")


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from backend.models.user import User
    from backend.models.blueprint import Blueprint
    from backend.models.results import DNAResult, FeatureResult, RoadmapResult, TeamResult, SWOTResult, CostResult, LegalComplianceResult
    from backend.models.workflow import GenerationSession
