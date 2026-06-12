from abc import ABC, abstractmethod
from typing import Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """Abstract interface defining required behaviors for AI LLM providers."""

    @abstractmethod
    async def generate(
        self, 
        prompt: str, 
        schema: Type[T], 
        system_instruction: str | None = None
    ) -> T:
        """Generates structured content conforming to the target Pydantic schema model."""
        pass

    @abstractmethod
    async def generate_stream(
        self, 
        prompt: str, 
        schema: Type[T], 
        system_instruction: str | None = None
    ):
        """Generates streams of structured content."""
        pass
