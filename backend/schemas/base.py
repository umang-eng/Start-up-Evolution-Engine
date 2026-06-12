from datetime import datetime, timezone
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponseMetadata(BaseModel):
    """Common metadata fields returned in all API responses."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    execution_time_ms: int = 0
    api_version: str = "1.0.0"


class PaginationMetadata(BaseModel):
    """Metadata block returned in paginated lists."""
    total_records: int
    limit: int
    offset: int
    has_more: bool


class BaseResponse(BaseModel, Generic[T]):
    """Standard success API envelope."""
    success: bool = True
    data: T
    metadata: APIResponseMetadata = Field(default_factory=APIResponseMetadata)
    pagination: PaginationMetadata | None = None


class APIError(BaseModel):
    """Structured error context payload."""
    code: str
    message: str
    details: Any | None = None


class BaseErrorResponse(BaseModel):
    """Standard error API envelope."""
    success: bool = False
    error: APIError
    metadata: APIResponseMetadata = Field(default_factory=APIResponseMetadata)
