import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Payload to create a new project workspace."""
    title: str = Field(min_length=3, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    industry: str | None = Field(default=None, max_length=100)


class ProjectUpdate(BaseModel):
    """Payload to update an existing project workspace."""
    title: str | None = Field(default=None, min_length=1, max_length=255)



class ProjectResponse(BaseModel):
    """Project workspace metadata returned to client."""
    id: uuid.UUID
    title: str
    description: str | None
    industry: str | None
    created_at: datetime

    class Config:
        from_attributes = True
