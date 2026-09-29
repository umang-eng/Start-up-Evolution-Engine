import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    """Payload to create a new project workspace."""
    title: str = Field(min_length=3, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    industry: str | None = Field(default=None, max_length=100)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    """Project workspace metadata returned to client."""
    id: uuid.UUID
    title: str
    description: str | None
    industry: str | None
    created_at: datetime
