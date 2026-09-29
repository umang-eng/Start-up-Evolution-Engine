"""Startup Memory Engine — persistent memory of all startup knowledge.

Extracts and stores decisions, assumptions, hypotheses, rejected ideas,
pivots, priorities, deadlines, owners, unresolved questions, risks,
and opportunities. Every new meeting references previous meetings.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    DECISION = "decision"
    ASSUMPTION = "assumption"
    HYPOTHESIS = "hypothesis"
    REJECTED_IDEA = "rejected_idea"
    PIVOT = "pivot"
    PRIORITY = "priority"
    DEADLINE = "deadline"
    ASSIGNED_OWNER = "assigned_owner"
    UNRESOLVED_QUESTION = "unresolved_question"
    RISK = "risk"
    OPPORTUNITY = "opportunity"
    FACT = "fact"
    COMMITMENT = "commitment"
    CONCERN = "concern"
    IDEA = "idea"
    LESSON = "lesson"


class MemoryEntry(BaseModel):
    """A single memory entry extracted from meetings."""
    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex[:12])
    memory_type: MemoryType
    content: str = Field(max_length=2000, description="The memory content")
    category: str = Field(default="general", description="Business category (pricing, features, hiring, etc.)")
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    source_meeting_id: str = Field(description="Which meeting this came from")
    source_transcript_refs: list[str] = Field(default_factory=list, description="Timestamps/segments referencing this")
    created_by: str = Field(default="system", description="Who/what created this memory")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    related_entries: list[str] = Field(default_factory=list, description="IDs of related memories")
    affected_modules: list[str] = Field(default_factory=list, description="Pipeline stages affected")
    contradictions: list[str] = Field(default_factory=list, description="IDs of contradicting memories")
    superseded_by: str | None = Field(default=None, description="If this was replaced by a newer memory")
    is_active: bool = Field(default=True, description="Whether this memory is still valid")
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryCluster(BaseModel):
    """A group of related memories about a topic."""
    topic: str
    entries: list[MemoryEntry]
    summary: str
    last_updated: str
    status: Literal["ACTIVE", "RESOLVED", "SUPERSEDED", "ABANDONED"]
    contradictions_count: int = 0


class StartupMemory(BaseModel):
    """Complete startup memory state."""
    project_id: str
    entries: list[MemoryEntry] = Field(default_factory=list)
    clusters: list[MemoryCluster] = Field(default_factory=list)
    total_meetings_processed: int = 0
    last_meeting_id: str | None = None
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    contradictions_detected: int = 0
    forgotten_decisions: list[str] = Field(default_factory=list)
    repeated_discussions: list[str] = Field(default_factory=list)
    changed_priorities: list[str] = Field(default_factory=list)


class MemoryDiff(BaseModel):
    """Changes detected between two memory states."""
    new_entries: list[MemoryEntry] = Field(default_factory=list)
    updated_entries: list[MemoryEntry] = Field(default_factory=list)
    removed_entries: list[MemoryEntry] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    repeated_discussions: list[str] = Field(default_factory=list)
    forgotten_decisions: list[str] = Field(default_factory=list)
    changed_priorities: list[str] = Field(default_factory=list)
    affected_modules: list[str] = Field(default_factory=list)
    summary: str = ""


class AffectedComponent(BaseModel):
    """A startup component affected by meeting discussions."""
    component_type: Literal["FEATURE", "ROADMAP", "TEAM", "COST", "SWOT", "BLUEPRINT", "DNA", "EXPANSION"]
    component_id: str | None = None
    change_type: Literal["ADDED", "MODIFIED", "REMOVED", "DEFERRED", "CANCELLED"]
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
