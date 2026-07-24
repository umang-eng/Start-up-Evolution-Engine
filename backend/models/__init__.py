# Database Models Layer Package
#
# Import every ORM model here so that SQLAlchemy's mapper registry contains
# all classes before configure_mappers() runs. Without these imports,
# string-based relationship() references (e.g. "AuditLog" in User) fail
# to resolve at runtime.

from backend.models.base import Base, UUIDMixin, TimestampMixin  # noqa: F401
from backend.models.user import User  # noqa: F401
from backend.models.audit import AuditLog  # noqa: F401
from backend.models.project import Project, ProjectVersion  # noqa: F401
from backend.models.blueprint import Blueprint  # noqa: F401
from backend.models.results import (  # noqa: F401
    DNAResult,
    FeatureResult,
    RoadmapResult,
    TeamResult,
    SWOTResult,
    CostResult,
    LegalComplianceResult,
)
from backend.models.workflow import GenerationSession, WorkflowEvent  # noqa: F401
from backend.models.analytics import AnalyticsLog  # noqa: F401
from backend.models.meeting import Meeting, MeetingSegment, Transcript, MeetingReport  # noqa: F401
