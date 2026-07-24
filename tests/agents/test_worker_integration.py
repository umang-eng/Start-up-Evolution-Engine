"""Unit tests for worker tasks.py AgentModule integration.

Tests verify feature flag routing without live DB or LLM calls.
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.agents.types import AgentRole, AgentBudget, StageAgentConfig


class TestOrchestratorRegistration:
    """Test that _get_orchestrator routes correctly based on feature flags."""

    def test_feature_flag_disabled_by_default(self):
        """All stages should be disabled by default in AGENT_MESH_CONFIG."""
        from backend.agents.config import AGENT_MESH_CONFIG

        for stage_name, cfg in AGENT_MESH_CONFIG.items():
            assert cfg.enabled is False, f"Stage {stage_name} should be disabled by default"

    @patch("backend.worker.tasks._orchestrator", None)
    def test_all_disabled_registers_original_modules(self):
        """When all stages disabled, only original modules are registered."""
        import backend.worker.tasks as tasks_mod
        tasks_mod._orchestrator = None

        with patch("backend.orchestrator.engine.WorkflowOrchestrator") as MockOrch:
            mock_orch = MagicMock()
            MockOrch.return_value = mock_orch

            # Mock all original modules
            mocks = {}
            for mod_path in [
                "backend.modules.dna.module.DNAModule",
                "backend.modules.features.module.FeatureModule",
                "backend.modules.roadmap.module.RoadmapModule",
                "backend.modules.team.module.TeamModule",
                "backend.modules.swot.module.SWOTModule",
                "backend.modules.cost.module.CostModule",
                "backend.modules.blueprint.module.BlueprintModule",
                "backend.modules.legal_compliance.module.LegalComplianceModule",
            ]:
                mocks[mod_path] = patch(mod_path)
                mocks[mod_path].start()
                mocks[mod_path].return_value = MagicMock()

            try:
                tasks_mod._get_orchestrator()
            except Exception:
                pass

            # All 8 original modules should be registered
            assert mock_orch.register_module.call_count == 8

            for m in mocks.values():
                m.stop()

    @patch("backend.worker.tasks._orchestrator", None)
    def test_enabled_stage_registers_agent_module(self):
        """When a stage is enabled, AgentModule should be registered for it."""
        import backend.worker.tasks as tasks_mod
        tasks_mod._orchestrator = None

        # Temporarily enable dna stage
        from backend.agents.config import AGENT_MESH_CONFIG
        original_enabled = AGENT_MESH_CONFIG["dna"].enabled
        AGENT_MESH_CONFIG["dna"].enabled = True

        try:
            with patch("backend.orchestrator.engine.WorkflowOrchestrator") as MockOrch:
                mock_orch = MagicMock()
                MockOrch.return_value = mock_orch

                # Mock AgentModule
                with patch("backend.agents.module.AgentModule") as MockAgentModule:
                    MockAgentModule.return_value = MagicMock()

                    # Mock all original modules
                    mocks = {}
                    for mod_path in [
                        "backend.modules.dna.module.DNAModule",
                        "backend.modules.features.module.FeatureModule",
                        "backend.modules.roadmap.module.RoadmapModule",
                        "backend.modules.team.module.TeamModule",
                        "backend.modules.swot.module.SWOTModule",
                        "backend.modules.cost.module.CostModule",
                        "backend.modules.blueprint.module.BlueprintModule",
                        "backend.modules.legal_compliance.module.LegalComplianceModule",
                    ]:
                        mocks[mod_path] = patch(mod_path)
                        mocks[mod_path].start()
                        mocks[mod_path].return_value = MagicMock()

                    try:
                        tasks_mod._get_orchestrator()
                    except Exception:
                        pass

                    # AgentModule created for dna (the only enabled stage)
                    MockAgentModule.assert_called_with("dna")

                    for m in mocks.values():
                        m.stop()
        finally:
            AGENT_MESH_CONFIG["dna"].enabled = original_enabled
