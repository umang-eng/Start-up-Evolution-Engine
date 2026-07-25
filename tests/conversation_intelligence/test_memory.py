"""Tests for startup memory engine."""

import pytest
from backend.modules.memory.types import (
    MemoryEntry, MemoryType, StartupMemory, MemoryCluster, MemoryDiff, AffectedComponent
)


class TestMemoryEntry:
    def test_create_entry(self):
        entry = MemoryEntry(
            memory_type=MemoryType.DECISION,
            content="We decided to use React for the frontend",
            category="technical",
            confidence=0.9,
            source_meeting_id="meeting-001",
            affected_modules=["features", "roadmap"],
        )
        assert entry.memory_type == MemoryType.DECISION
        assert entry.confidence == 0.9
        assert "features" in entry.affected_modules
        assert entry.is_active is True

    def test_memory_types(self):
        for mt in MemoryType:
            entry = MemoryEntry(
                memory_type=mt,
                content=f"Test {mt.value}",
                source_meeting_id="test",
            )
            assert entry.memory_type == mt


class TestStartupMemory:
    def test_create_memory(self):
        memory = StartupMemory(project_id="proj-001")
        assert memory.project_id == "proj-001"
        assert memory.total_meetings_processed == 0
        assert len(memory.entries) == 0

    def test_add_entries(self):
        memory = StartupMemory(project_id="proj-001")
        entry = MemoryEntry(
            memory_type=MemoryType.FACT,
            content="Market size is $50B",
            source_meeting_id="meeting-001",
        )
        memory.entries.append(entry)
        assert len(memory.entries) == 1


class TestMemoryDiff:
    def test_create_diff(self):
        diff = MemoryDiff(
            new_entries=[],
            summary="No changes",
        )
        assert diff.summary == "No changes"
        assert len(diff.new_entries) == 0


class TestMemoryEngine:
    @pytest.mark.asyncio
    async def test_engine_initialization(self):
        from backend.modules.memory.engine import MemoryEngine
        engine = MemoryEngine(project_id="proj-001")
        assert engine.project_id == "proj-001"
        assert engine.memory.project_id == "proj-001"

    def test_get_active_entries(self):
        from backend.modules.memory.engine import MemoryEngine
        engine = MemoryEngine(project_id="proj-001")
        engine.memory.entries.append(MemoryEntry(
            memory_type=MemoryType.DECISION,
            content="Test decision",
            source_meeting_id="m1",
        ))
        entries = engine.get_active_entries(MemoryType.DECISION)
        assert len(entries) == 1

    def test_search(self):
        from backend.modules.memory.engine import MemoryEngine
        engine = MemoryEngine(project_id="proj-001")
        engine.memory.entries.append(MemoryEntry(
            memory_type=MemoryType.FACT,
            content="Market size is $50B",
            source_meeting_id="m1",
        ))
        results = engine.search("market size")
        assert len(results) == 1

    def test_get_recent_entries(self):
        from backend.modules.memory.engine import MemoryEngine
        engine = MemoryEngine(project_id="proj-001")
        for i in range(5):
            engine.memory.entries.append(MemoryEntry(
                memory_type=MemoryType.FACT,
                content=f"Fact {i}",
                source_meeting_id="m1",
            ))
        recent = engine.get_recent_entries(limit=3)
        assert len(recent) == 3
