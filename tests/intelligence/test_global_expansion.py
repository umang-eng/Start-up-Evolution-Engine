"""Tests for global expansion engine."""

import pytest
from backend.modules.global_expansion.schemas import (
    GlobalExpansionOutput, CountryExpansion, ExpansionWave
)
from backend.modules.evidence.types import ConfidenceScore


class TestCountryExpansion:
    def test_create_country(self):
        country = CountryExpansion(
            country="United Kingdom",
            country_code="GB",
            priority="TIER_1",
            market_size_usd=500000000,
            local_competitors=["UK Tech Co"],
            regulatory_requirements=["GDPR", "Companies House"],
            localization_needs=["British English", "GBP"],
            hiring_costs_monthly=6000,
            pricing_adjustment_percent=0,
            tax_considerations=["20% corp tax"],
            gtm_strategy="Direct sales",
            risks=["Post-Brexit regulations"],
            confidence=ConfidenceScore(score=70.0),
        )
        assert country.country == "United Kingdom"
        assert country.priority == "TIER_1"
        assert country.market_size_usd == 500000000

    def test_priority_tiers(self):
        for tier in ["TIER_1", "TIER_2", "TIER_3"]:
            country = CountryExpansion(
                country="Test", country_code="XX", priority=tier,
                market_size_usd=100000, local_competitors=[],
                regulatory_requirements=[], localization_needs=[],
                hiring_costs_monthly=3000, pricing_adjustment_percent=0,
                tax_considerations=[], gtm_strategy="Test",
                risks=[], confidence=ConfidenceScore(score=50.0),
            )
            assert country.priority == tier


class TestExpansionWave:
    def test_create_wave(self):
        country = CountryExpansion(
            country="UK", country_code="GB", priority="TIER_1",
            market_size_usd=500000000, local_competitors=[],
            regulatory_requirements=[], localization_needs=[],
            hiring_costs_monthly=6000, pricing_adjustment_percent=0,
            tax_considerations=[], gtm_strategy="Direct",
            risks=[], confidence=ConfidenceScore(score=70.0),
        )
        wave = ExpansionWave(
            wave_number=1,
            wave_name="Quick Wins",
            countries=[country],
            timeline_months=12,
            total_investment_usd=200000,
            expected_arr_contribution=300000,
        )
        assert wave.wave_number == 1
        assert len(wave.countries) == 1
        assert wave.total_investment_usd == 200000


class TestGlobalExpansionOutput:
    def test_create_output(self):
        country = CountryExpansion(
            country="Canada", country_code="CA", priority="TIER_1",
            market_size_usd=300000000, local_competitors=[],
            regulatory_requirements=[], localization_needs=[],
            hiring_costs_monthly=5500, pricing_adjustment_percent=-5,
            tax_considerations=[], gtm_strategy="Adjacent market",
            risks=[], confidence=ConfidenceScore(score=65.0),
        )
        wave = ExpansionWave(
            wave_number=1, wave_name="Phase 1",
            countries=[country], timeline_months=12,
            total_investment_usd=150000, expected_arr_contribution=200000,
        )
        output = GlobalExpansionOutput(
            waves=[wave],
            total_markets_assessed=1,
            recommended_first_market="Canada",
            total_expansion_investment=150000,
            expected_global_arr=200000,
            expansion_timeline_months=12,
            key_risks=["Currency fluctuation"],
            recommendations=["Start with English-speaking markets"],
            confidence=ConfidenceScore(score=60.0),
            explanation="Expansion plan generated",
        )
        assert output.recommended_first_market == "Canada"
        assert output.total_expansion_investment == 150000


class TestGlobalExpansionModule:
    @pytest.mark.asyncio
    async def test_module_initialization(self):
        from backend.modules.global_expansion.module import GlobalExpansionModule
        module = GlobalExpansionModule()
        assert module.stage_name == "global_expansion"
        assert "blueprint" in module.input_stages

    @pytest.mark.asyncio
    async def test_fallback_output(self):
        from backend.modules.global_expansion.module import GlobalExpansionModule
        module = GlobalExpansionModule()
        output = module._fallback_output([])
        assert isinstance(output, GlobalExpansionOutput)
        assert len(output.waves) == 1
