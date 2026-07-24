"""Add Conversation Intelligence tables (meetings, transcripts, reports)

Revision ID: 0002_add_meetings
Revises: 0001_initial
Create Date: 2026-07-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_add_meetings"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    """Check if a table already exists in the database."""
    bind = op.get_bind()
    return sa.inspect(bind).has_table(table_name)


def upgrade() -> None:
    # ── meetings ──────────────────────────────────────────────────
    if not _table_exists("meetings"):
        op.create_table(
            "meetings",
            sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("project_id", sa.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True),
            sa.Column("title", sa.String(500), nullable=True),
            sa.Column("status", sa.String(50), nullable=False, server_default="RECORDING"),
            sa.Column("duration_seconds", sa.Integer(), nullable=True),
            sa.Column("speaker_count", sa.Integer(), nullable=True),
            sa.Column("language", sa.String(10), nullable=True, server_default="en"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )

    # ── meeting_segments ──────────────────────────────────────────
    if not _table_exists("meeting_segments"):
        op.create_table(
            "meeting_segments",
            sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
            sa.Column("meeting_id", sa.UUID(as_uuid=True), sa.ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("speaker", sa.String(100), nullable=True),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("start_time_ms", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("end_time_ms", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("is_final", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )

    # ── transcripts ───────────────────────────────────────────────
    if not _table_exists("transcripts"):
        op.create_table(
            "transcripts",
            sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
            sa.Column("meeting_id", sa.UUID(as_uuid=True), sa.ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
            sa.Column("raw_text", sa.Text(), nullable=False),
            sa.Column("word_count", sa.Integer(), nullable=True),
            sa.Column("language_detected", sa.String(10), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )

    # ── meeting_reports ───────────────────────────────────────────
    if not _table_exists("meeting_reports"):
        op.create_table(
            "meeting_reports",
            sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
            sa.Column("meeting_id", sa.UUID(as_uuid=True), sa.ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
            sa.Column("status", sa.String(50), nullable=False, server_default="PENDING"),
            sa.Column("title", sa.String(500), nullable=True),
            sa.Column("executive_summary", sa.Text(), nullable=True),
            sa.Column("key_points", postgresql.JSONB(), nullable=True),
            sa.Column("decisions", postgresql.JSONB(), nullable=True),
            sa.Column("action_items", postgresql.JSONB(), nullable=True),
            sa.Column("questions_raised", postgresql.JSONB(), nullable=True),
            sa.Column("risks_concerns", postgresql.JSONB(), nullable=True),
            sa.Column("agreements", postgresql.JSONB(), nullable=True),
            sa.Column("disagreements", postgresql.JSONB(), nullable=True),
            sa.Column("technical_topics", postgresql.JSONB(), nullable=True),
            sa.Column("business_opportunities", postgresql.JSONB(), nullable=True),
            sa.Column("follow_up_needed", postgresql.JSONB(), nullable=True),
            sa.Column("overall_outcome", sa.Text(), nullable=True),
            sa.Column("full_report_markdown", sa.Text(), nullable=True),
            sa.Column("report_metadata", postgresql.JSONB(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )


def downgrade() -> None:
    if _table_exists("meeting_reports"):
        op.drop_table("meeting_reports")
    if _table_exists("transcripts"):
        op.drop_table("transcripts")
    if _table_exists("meeting_segments"):
        op.drop_table("meeting_segments")
    if _table_exists("meetings"):
        op.drop_table("meetings")
