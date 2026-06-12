from typing import Generic, TypeVar
from backend.repositories.base import BaseRepository
from backend.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)
RepoType = TypeVar("RepoType", bound=BaseRepository)


class BaseService(Generic[ModelType, RepoType]):
    """Base business service coordinator executing domain validation logic."""
    
    def __init__(self, repository: RepoType) -> None:
        self.repository = repository
