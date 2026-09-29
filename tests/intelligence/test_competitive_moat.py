"""Tests for competitive moat analysis module."""

import pytest
from backend.modules.competitive_moat.schemas import (
    CompetitiveMoatOutput, MoatDimension, MoatType
)
from backend.modules.evidence.types import ConfidenceScore, EvidenceBackedScore, EvidenceSource


class TestMoatDimension:
    def test_create_dimension(self):
        dim = MoatDimension(
            moat_type=MoatType.NETWORK_EFFECTS,
            strength=8.0,
            difficulty_to_copy="HARD",
            time_to_copy_months=18,
            cost_to_copy_usd=5000000,
            explanation="Strong network effects from user base",
            is_active=True,
        )
        assert dim.moat_type == MoatType.NETWORK_EFFECTS
        assert dim.strength == 8.0
        assert dim.difficulty_to_copy == "HARD"
        assert dim.is_active is True

    def test_moat_types(self):
        assert MoatType.NETWORK_EFFECTS == "network_effects"
        assert MoatType.DATA_MOAT == "data_moat"
        assert MoatType.TECHNOLOGY_MOAT == "technology_moat"
        assert MoatType.AI_DATA_FLYWHEEL == "ai_data_flywheel"


class TestCompetitiveMoatOutput:
    def test_create_output(self):
        dim = MoatDimension(
            moat_type=MoatType.NETWORK_EFFECTS,
            strength=7.0,
            difficulty_to_copy="MODERATE",
            time_to_copy_months=12,
            cost_to_copy_usd=2000000,
            explanation="Moderate network effects",
        )
        output = CompetitiveMoatOutput(
            overall_moat_score=EvidenceBackedScore(
                value=70.0,
                label="Overall Moat Strength",
                confidence=ConfidenceScore(score=75.0),
            ),
            moat_dimensions=[dim],
            strongest_moat="network_effects",
            weakest_moat="network_effects",
            moat_gap_analysis=["Technology moat needs improvement"],
            build_recommendations=["Invest in proprietary data"],
            competitive_position="Moderate competitive position",
            time_to_defensible="18 months",
            explanation="Moat analysis complete",
        )
        assert output.overall_moat_score.value == 70.0
        assert len(output.moat_dimensions) == 1
        assert output.strongest_moat == "network_effects"


class TestCompetitiveMoatModule:
    @pytest.mark.asyncio
    async def test_module_initialization(self):
        from backend.modules.competitive_moat.module import CompetitiveMoatModule
        module = CompetitiveMoatModule()
        assert module.stage_name == "competitive_moat"
        assert "dna" in module.input_stages

    @pytest.mark.asyncio
    async def test_fallback_dimensions(self):
        from backend.modules.competitive_moat.module import CompetitiveMoatModule
        module = CompetitiveMoatModule()
        dims = module._fallback_dimensions([])
        assert len(dims) == 1
        assert dims[0].moat_type == MoatType.NETWORK_EFFECTS
