import asyncio
import time
from typing import Type, TypeVar
from google import genai
from google.genai import types
from google.genai.errors import ClientError
from pydantic import BaseModel, ValidationError

from backend.ai.provider import LLMProvider
from backend.core.config import settings
from backend.core.exceptions import BaseBusinessException
from backend.core.logging import logger, performance_logger

T = TypeVar("T", bound=BaseModel)

# Ordered list of models to try — fastest/cheapest first
# NOTE: With google-genai SDK v2 (v1beta API), use exact model IDs from:
# https://ai.google.dev/gemini-api/docs/models/gemini
MODEL_PRIORITY = [
    "gemini-2.0-flash",           # Fastest, hits quota first on free tier
    "gemini-2.0-flash-lite",      # Lighter quota limits
    "gemini-1.5-flash",           # Universally supported fallback on free tier
]

# Backoff wait times (seconds) per model on quota exhaustion
MODEL_BACKOFF_SECONDS = [15, 45, 90]


class GeminiAdapter(LLMProvider):
    """Adapter executing non-blocking content generation using google-genai SDK (v2+)."""

    def __init__(self) -> None:
        self.default_model_name = MODEL_PRIORITY[0]
        self._client: genai.Client | None = None
        if settings.GEMINI_API_KEY:
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)

    @property
    def client(self) -> genai.Client:
        if not self._client:
            raise BaseBusinessException(
                message="Gemini API key is not configured. Set GEMINI_API_KEY in your environment.",
                code="AI_CONFIGURATION_ERROR",
                status_code=500
            )
        return self._client

    def _generate_json_template(self, model: Type[BaseModel]) -> dict:
        from typing import Union, get_origin, get_args
        try:
            from typing import Literal as TypLiteral
        except ImportError:
            TypLiteral = None
        try:
            from typing_extensions import Literal as ExtLiteral
        except ImportError:
            ExtLiteral = None

        template = {}
        for field_name, field_info in model.model_fields.items():
            annotation = field_info.annotation
            origin = get_origin(annotation)
            if origin is Union:
                args = get_args(annotation)
                non_none = [a for a in args if a is not type(None)]
                if non_none:
                    annotation = non_none[0]
                    origin = get_origin(annotation)
            
            # Check for Literal type
            is_literal = (origin is TypLiteral) or (ExtLiteral and origin is ExtLiteral)
            
            # Determine constraints if any
            min_v = None
            max_v = None
            for meta in field_info.metadata:
                for attr in ['ge', 'le', 'gt', 'lt']:
                    val = getattr(meta, attr, None)
                    if val is not None:
                        if attr == 'ge': min_v = f">= {val}"
                        elif attr == 'gt': min_v = f"> {val}"
                        elif attr == 'le': max_v = f"<= {val}"
                        elif attr == 'lt': max_v = f"< {val}"

            constraint_str = ""
            if min_v is not None and max_v is not None:
                constraint_str = f" ({min_v} and {max_v})"
            elif min_v is not None:
                constraint_str = f" ({min_v})"
            elif max_v is not None:
                constraint_str = f" ({max_v})"

            if is_literal:
                choices = get_args(annotation)
                desc = field_info.description or field_name
                choices_str = ", ".join(repr(c) for c in choices)
                template[field_name] = f"<string - {desc} (MUST be one of: {choices_str})>"
            elif isinstance(annotation, type) and issubclass(annotation, BaseModel):
                template[field_name] = self._generate_json_template(annotation)
            elif origin is list:
                args = get_args(annotation)
                if args:
                    item_type = args[0]
                    item_origin = get_origin(item_type)
                    item_is_literal = (item_origin is TypLiteral) or (ExtLiteral and item_origin is ExtLiteral)
                    if item_is_literal:
                        item_choices = get_args(item_type)
                        desc = field_info.description or "item"
                        choices_str = ", ".join(repr(c) for c in item_choices)
                        template[field_name] = [f"<string - {desc} (MUST be one of: {choices_str})>"]
                    elif isinstance(item_type, type) and issubclass(item_type, BaseModel):
                        template[field_name] = [self._generate_json_template(item_type)]
                    else:
                        desc = field_info.description or "item"
                        template[field_name] = [f"<string - {desc}>"]
                else:
                    desc = field_info.description or "item"
                    template[field_name] = [f"<string - {desc}>"]
            else:
                desc = field_info.description or field_name
                type_name = "string"
                if annotation is int:
                    type_name = "integer"
                elif annotation is float:
                    type_name = "float"
                elif annotation is bool:
                    type_name = "boolean (true/false)"
                template[field_name] = f"<{type_name} - {desc}{constraint_str}>"
        return template

    async def generate(
        self,
        prompt: str,
        schema: Type[T],
        system_instruction: str | None = None
    ) -> T:
        """Generates structured content conforming to the schema using local Ollama model gemma2:2b."""
        import httpx
        import json

        # Force local Ollama generation using gemma2:2b
        try:
            logger.info("Executing local structured generation workflow via Ollama gemma2:2b...")
            system_content = system_instruction or "You are a strategic startup assistant."
            template = self._generate_json_template(schema)
            system_content += (
                f"\n\nIMPORTANT: You must return ONLY a JSON object filled with information matching "
                f"this template structure exactly. Do NOT use placeholder values, return actual content. "
                f"For integer and float types, return a raw number without quotes. Example: 85, not '85'.\n\n"
                f"Template structure:\n{json.dumps(template, indent=2)}"
            )
            
            payload = {
                "model": "gemma2:2b",
                "messages": [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt}
                ],
                "format": "json",
                "stream": False,
                "options": {
                    "temperature": 0.3
                }
            }
            
            async with httpx.AsyncClient(timeout=120.0) as work_client:
                response = await work_client.post("http://localhost:11434/api/chat", json=payload)
                if response.status_code != 200:
                    raise BaseBusinessException(
                        message=f"Local Ollama API returned status code {response.status_code}: {response.text}",
                        code="OLLAMA_ERROR",
                        status_code=500
                    )
                
                res_data = response.json()
                content = res_data.get("message", {}).get("content", "")
                if not content:
                    raise BaseBusinessException(
                        message="Local Ollama model returned an empty response.",
                        code="OLLAMA_EMPTY_RESPONSE",
                        status_code=500
                    )
                
                try:
                    return schema.model_validate_json(content)
                except Exception as ve:
                    logger.error(f"Ollama output validation failed: {str(ve)}. Response content: {content}")
                    raise BaseBusinessException(
                        message=f"Ollama output failed schema validation: {str(ve)}",
                        code="OLLAMA_VALIDATION_ERROR",
                        status_code=422
                    )
        except BaseBusinessException:
            raise
        except Exception as e:
            logger.error(f"Ollama generation failed: {str(e)}")
            raise BaseBusinessException(
                message=f"Local Ollama generation failed. Make sure the Ollama app is running and gemma2:2b is pulled. Error: {str(e)}",
                code="OLLAMA_UNAVAILABLE",
                status_code=503
            )

    async def generate_text(self, prompt: str, system_instruction: str | None = None) -> str:
        """Generates a plain text response (non-structured) using local Ollama model gemma2:2b."""
        import httpx
        try:
            logger.info("Executing local text generation workflow via Ollama gemma2:2b...")
            payload = {
                "model": "gemma2:2b",
                "messages": [
                    {"role": "system", "content": system_instruction or "You are a startup compiler assistant."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.7
                }
            }
            
            async with httpx.AsyncClient(timeout=60.0) as work_client:
                response = await work_client.post("http://localhost:11434/api/chat", json=payload)
                if response.status_code != 200:
                    raise BaseBusinessException(
                        message=f"Local Ollama API returned status code {response.status_code}: {response.text}",
                        code="OLLAMA_ERROR",
                        status_code=500
                    )
                
                res_data = response.json()
                content = res_data.get("message", {}).get("content", "")
                if content and content.strip():
                    return content.strip()
                else:
                    raise BaseBusinessException(
                        message="Local Ollama model returned an empty text response.",
                        code="OLLAMA_EMPTY_RESPONSE",
                        status_code=500
                    )
        except BaseBusinessException:
            raise
        except Exception as e:
            logger.error(f"Ollama text generation failed: {str(e)}")
            raise BaseBusinessException(
                message=f"Local Ollama text generation failed. Make sure the Ollama app is running and gemma2:2b is pulled. Error: {str(e)}",
                code="OLLAMA_UNAVAILABLE",
                status_code=503
            )

    async def _log_analytics(
        self,
        project_id: str,
        correlation_id: str,
        module_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int
    ) -> None:
        """Persists LLM execution cost, token, and latency metrics to database."""
        try:
            import uuid
            from backend.database.session import AsyncSessionLocal
            from backend.models.analytics import AnalyticsLog

            # Costs for gemini-2.0-flash:
            # Input: $0.10/million tokens → $0.0000001 per token
            # Output: $0.40/million tokens → $0.0000004 per token
            cost = (prompt_tokens * 0.0000001) + (completion_tokens * 0.0000004)

            async with AsyncSessionLocal() as db:
                log_entry = AnalyticsLog(
                    project_id=uuid.UUID(project_id),
                    correlation_id=correlation_id,
                    module_name=module_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    latency_ms=latency_ms,
                    estimated_cost_usd=cost
                )
                db.add(log_entry)
                await db.commit()
        except Exception as e:
            logger.error("Failed to persist analytics log", exc_info=e)

    async def generate_stream(
        self,
        prompt: str,
        schema: Type[T],
        system_instruction: str | None = None
    ):
        """Placeholder — streaming handled at module level."""
        raise NotImplementedError("Streaming generate is handled inside specific module workflows.")


gemini_adapter = GeminiAdapter()
