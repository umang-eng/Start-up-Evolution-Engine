import asyncio
import time
from typing import Type, TypeVar, Any
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

    def _normalize_json_data(self, data: Any, model: Type[BaseModel]) -> Any:
        from typing import Union, get_origin, get_args
        try:
            from typing import Literal as TypLiteral
        except ImportError:
            TypLiteral = None
        try:
            from typing_extensions import Literal as ExtLiteral
        except ImportError:
            ExtLiteral = None

        if not isinstance(data, dict):
            return data

        normalized = {}
        for field_name, field_info in model.model_fields.items():
            if field_name not in data:
                continue
            
            val = data[field_name]
            annotation = field_info.annotation
            origin = get_origin(annotation)
            
            if origin is Union:
                args = get_args(annotation)
                non_none = [a for a in args if a is not type(None)]
                if non_none:
                    annotation = non_none[0]
                    origin = get_origin(annotation)

            is_literal = (origin is TypLiteral) or (ExtLiteral and origin is ExtLiteral)

            if is_literal and isinstance(val, str):
                choices = get_args(annotation)
                val_upper = val.strip().upper().replace(" ", "_").replace("-", "_")
                matched = False
                for choice in choices:
                    if isinstance(choice, str) and choice.upper() == val_upper:
                        normalized[field_name] = choice
                        matched = True
                        break
                
                if not matched:
                    # Synonym mapping for MoSCoW priorities
                    val_lower = val.lower()
                    if "critical" in val_lower or "urgent" in val_lower or "must" in val_lower:
                        for choice in choices:
                            if choice == "MUST_HAVE":
                                normalized[field_name] = "MUST_HAVE"
                                matched = True
                                break
                    elif "should" in val_lower:
                        for choice in choices:
                            if choice == "SHOULD_HAVE":
                                normalized[field_name] = "SHOULD_HAVE"
                                matched = True
                                break
                    elif "could" in val_lower:
                        for choice in choices:
                            if choice == "COULD_HAVE":
                                normalized[field_name] = "COULD_HAVE"
                                matched = True
                                break
                    elif "wont" in val_lower or "won't" in val_lower or "will not" in val_lower:
                        for choice in choices:
                            if choice == "WONT_HAVE":
                                normalized[field_name] = "WONT_HAVE"
                                matched = True
                                break
                
                if not matched:
                    normalized[field_name] = val
            elif isinstance(annotation, type) and issubclass(annotation, BaseModel):
                normalized[field_name] = self._normalize_json_data(val, annotation)
            elif origin is list and isinstance(val, list):
                args = get_args(annotation)
                if args:
                    item_type = args[0]
                    item_origin = get_origin(item_type)
                    item_is_literal = (item_origin is TypLiteral) or (ExtLiteral and item_origin is ExtLiteral)
                    
                    new_list = []
                    for item in val:
                        if item_is_literal and isinstance(item, str):
                            item_choices = get_args(item_type)
                            item_upper = item.strip().upper().replace(" ", "_").replace("-", "_")
                            matched = False
                            for choice in item_choices:
                                if isinstance(choice, str) and choice.upper() == item_upper:
                                    new_list.append(choice)
                                    matched = True
                                    break
                            
                            if not matched:
                                item_lower = item.lower()
                                if "critical" in item_lower or "urgent" in item_lower or "must" in item_lower:
                                    for choice in item_choices:
                                        if choice == "MUST_HAVE":
                                            new_list.append("MUST_HAVE")
                                            matched = True
                                            break
                                elif "should" in item_lower:
                                    for choice in item_choices:
                                        if choice == "SHOULD_HAVE":
                                            new_list.append("SHOULD_HAVE")
                                            matched = True
                                            break
                                elif "could" in item_lower:
                                    for choice in item_choices:
                                        if choice == "COULD_HAVE":
                                            new_list.append("COULD_HAVE")
                                            matched = True
                                            break
                                elif "wont" in item_lower or "won't" in item_lower or "will not" in item_lower:
                                    for choice in item_choices:
                                        if choice == "WONT_HAVE":
                                            new_list.append("WONT_HAVE")
                                            matched = True
                                            break
                            if not matched:
                                new_list.append(item)
                        elif isinstance(item_type, type) and issubclass(item_type, BaseModel):
                            new_list.append(self._normalize_json_data(item, item_type))
                        else:
                            new_list.append(item)
                    normalized[field_name] = new_list
                else:
                    normalized[field_name] = val
            else:
                normalized[field_name] = val
        
        # Add any other fields from data that weren't in model_fields just in case
        for k, v in data.items():
            if k not in normalized:
                normalized[k] = v
                
        return normalized

    def _extract_json(self, content: str) -> str:
        """Cleans and extracts JSON string from potential markdown wrappers or surrounding text."""
        text = content.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
            
        # If it still doesn't start with { or [, try to find it
        if not (text.startswith("{") or text.startswith("[")):
            start_idx = text.find("{")
            end_idx = text.rfind("}")
            if start_idx != -1 and end_idx != -1:
                text = text[start_idx:end_idx + 1]
                
        return text

    async def generate(
        self,
        prompt: str,
        schema: Type[T],
        system_instruction: str | None = None
    ) -> T:
        """Generates structured content conforming to the schema using local/cloud Ollama model."""
        import httpx
        import json

        # Build request headers — cloud models require Authorization header
        headers = {"Content-Type": "application/json"}
        if settings.OLLAMA_API_KEY:
            headers["Authorization"] = f"Bearer {settings.OLLAMA_API_KEY}"

        # Force Ollama generation using configured host and model settings
        try:
            logger.info(f"Executing Ollama structured generation workflow via model '{settings.OLLAMA_MODEL}'...")
            system_content = system_instruction or "You are a strategic startup assistant."
            template = self._generate_json_template(schema)
            system_content += (
                f"\n\nIMPORTANT: You must return ONLY a JSON object filled with information matching "
                f"this template structure exactly. Do NOT use placeholder values, return actual content. "
                f"For integer and float types, return a raw number without quotes. Example: 85, not '85'.\n\n"
                f"Template structure:\n{json.dumps(template, indent=2)}"
            )
            
            payload = {
                "model": settings.OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt}
                ],
                "format": "json",
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_ctx": 4096
                }
            }
            
            async with httpx.AsyncClient(timeout=120.0) as work_client:
                response = await work_client.post(f"{settings.OLLAMA_HOST}/api/chat", json=payload, headers=headers)
                if response.status_code != 200:
                    raise BaseBusinessException(
                        message=f"Ollama API ({settings.OLLAMA_MODEL}) returned status code {response.status_code}: {response.text}",
                        code="OLLAMA_ERROR",
                        status_code=500
                    )
                
                res_data = response.json()
                content = res_data.get("message", {}).get("content", "")
                if not content:
                    raise BaseBusinessException(
                        message=f"Ollama model '{settings.OLLAMA_MODEL}' returned an empty response.",
                        code="OLLAMA_EMPTY_RESPONSE",
                        status_code=500
                    )
                
                try:
                    # Clean and parse JSON data to handle case-insensitivity, markdown wrappers, and synonym matching
                    cleaned_content = self._extract_json(content)
                    parsed_data = json.loads(cleaned_content)
                    normalized_data = self._normalize_json_data(parsed_data, schema)
                    return schema.model_validate(normalized_data)
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
                message=f"Ollama generation failed. Make sure the Ollama host '{settings.OLLAMA_HOST}' is reachable and the model '{settings.OLLAMA_MODEL}' is active. Error: {str(e)}",
                code="OLLAMA_UNAVAILABLE",
                status_code=503
            )

    async def generate_text(self, prompt: str, system_instruction: str | None = None) -> str:
        """Generates a plain text response (non-structured) using Ollama model."""
        import httpx

        # Build request headers — cloud models require Authorization header
        headers = {"Content-Type": "application/json"}
        if settings.OLLAMA_API_KEY:
            headers["Authorization"] = f"Bearer {settings.OLLAMA_API_KEY}"

        try:
            logger.info(f"Executing Ollama text generation workflow via model '{settings.OLLAMA_MODEL}'...")
            payload = {
                "model": settings.OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system_instruction or "You are a startup compiler assistant."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_ctx": 4096
                }
            }
            
            async with httpx.AsyncClient(timeout=60.0) as work_client:
                response = await work_client.post(f"{settings.OLLAMA_HOST}/api/chat", json=payload, headers=headers)
                if response.status_code != 200:
                    raise BaseBusinessException(
                        message=f"Ollama API ({settings.OLLAMA_MODEL}) returned status code {response.status_code}: {response.text}",
                        code="OLLAMA_ERROR",
                        status_code=500
                    )
                
                res_data = response.json()
                content = res_data.get("message", {}).get("content", "")
                if content and content.strip():
                    return content.strip()
                else:
                    raise BaseBusinessException(
                        message=f"Ollama model '{settings.OLLAMA_MODEL}' returned an empty text response.",
                        code="OLLAMA_EMPTY_RESPONSE",
                        status_code=500
                    )
        except BaseBusinessException:
            raise
        except Exception as e:
            logger.error(f"Ollama text generation failed: {str(e)}")
            raise BaseBusinessException(
                message=f"Ollama text generation failed. Make sure the Ollama host '{settings.OLLAMA_HOST}' is reachable and the model '{settings.OLLAMA_MODEL}' is active. Error: {str(e)}",
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
