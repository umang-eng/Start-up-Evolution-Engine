# Base target import registry for Alembic migrations auto-generation
from backend.models.base import Base # noqa
from backend.models.user import User # noqa
from backend.models.project import Project, ProjectVersion # noqa
from backend.models.blueprint import Blueprint # noqa
from backend.models.results import DNAResult, FeatureResult, RoadmapResult, TeamResult, SWOTResult, CostResult # noqa
from backend.models.workflow import GenerationSession, WorkflowEvent # noqa
from backend.models.audit import AuditLog # noqa
from backend.models.analytics import AnalyticsLog # noqa
