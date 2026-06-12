from backend.orchestrator.engine import orchestrator
from backend.modules.dna.module import DNAModule
from backend.modules.features.module import FeatureModule
from backend.modules.roadmap.module import RoadmapModule
from backend.modules.team.module import TeamModule
from backend.modules.swot.module import SWOTModule
from backend.modules.cost.module import CostModule
from backend.modules.blueprint.module import BlueprintModule

# Register active compiler module instances
orchestrator.register_module("dna", DNAModule())
orchestrator.register_module("features", FeatureModule())
orchestrator.register_module("roadmap", RoadmapModule())
orchestrator.register_module("team", TeamModule())
orchestrator.register_module("swot", SWOTModule())
orchestrator.register_module("cost", CostModule())
orchestrator.register_module("blueprint", BlueprintModule())
