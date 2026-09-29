"""Initial schema — all 15 tables

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="USER"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── audit_logs ───────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── projects ─────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("region", sa.String(10), nullable=True, server_default="US",
                   comment="ISO 3166-1 alpha-2 country code for regional compliance search"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── dna_results ──────────────────────────────────────────────
    op.create_table(
        "dna_results",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", sa.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("hash_checksum", sa.String(64), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── feature_results ──────────────────────────────────────────
    op.create_table(
        "feature_results",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", sa.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("hash_checksum", sa.String(64), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── roadmap_results ──────────────────────────────────────────
    op.create_table(
        "roadmap_results",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", sa.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("hash_checksum", sa.String(64), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── team_results ─────────────────────────────────────────────
    op.create_table(
        "team_results",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", sa.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("hash_checksum", sa.String(64), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── swot_results ─────────────────────────────────────────────
    op.create_table(
        "swot_results",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", sa.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("hash_checksum", sa.String(64), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── cost_results ─────────────────────────────────────────────
    op.create_table(
        "cost_results",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", sa.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("hash_checksum", sa.String(64), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── legal_compliance_results ─────────────────────────────────
    op.create_table(
        "legal_compliance_results",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", sa.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("hash_checksum", sa.String(64), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── blueprints ───────────────────────────────────────────────
    op.create_table(
        "blueprints",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", sa.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("health_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("version", sa.String(20), nullable=False, server_default="1.0.0"),
        sa.Column("hash_checksum", sa.String(64), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── project_versions ─────────────────────────────────────────
    op.create_table(
        "project_versions",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", sa.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("version_label", sa.String(50), nullable=False),
        sa.Column("message", sa.String(255), nullable=True),
        sa.Column("snapshot_data", postgresql.JSONB(), nullable=False),
        sa.Column("dna_result_id", sa.UUID(as_uuid=True), sa.ForeignKey("dna_results.id", ondelete="SET NULL"), nullable=True),
        sa.Column("feature_result_id", sa.UUID(as_uuid=True), sa.ForeignKey("feature_results.id", ondelete="SET NULL"), nullable=True),
        sa.Column("roadmap_result_id", sa.UUID(as_uuid=True), sa.ForeignKey("roadmap_results.id", ondelete="SET NULL"), nullable=True),
        sa.Column("team_result_id", sa.UUID(as_uuid=True), sa.ForeignKey("team_results.id", ondelete="SET NULL"), nullable=True),
        sa.Column("swot_result_id", sa.UUID(as_uuid=True), sa.ForeignKey("swot_results.id", ondelete="SET NULL"), nullable=True),
        sa.Column("cost_result_id", sa.UUID(as_uuid=True), sa.ForeignKey("cost_results.id", ondelete="SET NULL"), nullable=True),
        sa.Column("blueprint_result_id", sa.UUID(as_uuid=True), sa.ForeignKey("blueprints.id", ondelete="SET NULL"), nullable=True),
        sa.Column("checksum_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── generation_sessions ──────────────────────────────────────
    op.create_table(
        "generation_sessions",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", sa.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="CREATED"),
        sa.Column("correlation_id", sa.String(100), nullable=False, index=True),
        sa.Column("current_stage", sa.String(50), nullable=True),
        sa.Column("progress_percentage", sa.Numeric(5, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("error_message", sa.String(1000), nullable=True),
        sa.Column("stage_cache_map", postgresql.JSONB(), nullable=True),
        sa.Column("cache_hits", sa.Numeric(3, 0), nullable=False, server_default=sa.text("0")),
        sa.Column("cache_misses", sa.Numeric(3, 0), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── workflow_events ──────────────────────────────────────────
    op.create_table(
        "workflow_events",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.UUID(as_uuid=True), sa.ForeignKey("generation_sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("stage", sa.String(50), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── analytics_logs ───────────────────────────────────────────
    op.create_table(
        "analytics_logs",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", sa.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("correlation_id", sa.String(100), nullable=False, index=True),
        sa.Column("module_name", sa.String(100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("estimated_cost_usd", sa.Numeric(10, 6), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("analytics_logs")
    op.drop_table("workflow_events")
    op.drop_table("generation_sessions")
    op.drop_table("project_versions")
    op.drop_table("blueprints")
    op.drop_table("legal_compliance_results")
    op.drop_table("cost_results")
    op.drop_table("swot_results")
    op.drop_table("team_results")
    op.drop_table("roadmap_results")
    op.drop_table("feature_results")
    op.drop_table("dna_results")
    op.drop_table("projects")
    op.drop_table("audit_logs")
    op.drop_table("users")
