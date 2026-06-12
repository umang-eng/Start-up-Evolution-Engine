import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.models.base import Base, UUIDMixin, TimestampMixin


class AuditLog(Base, UUIDMixin, TimestampMixin):
    """Compliance log storing append-only history of system mutations."""
    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    actor: Mapped["User | None"] = relationship("User", back_populates="audit_logs")


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from backend.models.user import User
