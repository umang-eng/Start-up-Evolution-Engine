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

# Ordered list of models to try — fastest/cheapest first, fallback to more capable
MODEL_PRIORITY = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]


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
                message="Gemini API key is not configured.",
                code="AI_CONFIGURATION_ERROR",
                status_code=500
            )
        return self._client

    async def generate(
        self, 
        prompt: str, 
        schema: Type[T], 
        system_instruction: str | None = None
    ) -> T:
        """Generates structured content conforming to the schema, with up to 3 repair attempts."""
        max_validation_attempts = 3
        current_prompt = prompt

        # Try models in priority order; skip to next on quota/rate-limit errors
        for model_name in MODEL_PRIORITY:
            for attempt in range(max_validation_attempts):
                start_time = time.perf_counter()
                try:
                    logger.info(
                        f"Initiating Gemini Request: {model_name}",
                        extra_data={"attempt": attempt + 1, "prompt_len": len(current_prompt)}
                    )

                    config = types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema,
                        temperature=0.2,
                        system_instruction=system_instruction,
                    )

                    response = await self.client.aio.models.generate_content(
                        model=model_name,
                        contents=current_prompt,
                        config=config,
                    )

                    latency_ms = int((time.perf_counter() - start_time) * 1000)

                    prompt_tokens = 0
                    candidates_tokens = 0
                    if response.usage_metadata:
                        prompt_tokens = response.usage_metadata.prompt_token_count or 0
                        candidates_tokens = response.usage_metadata.candidates_token_count or 0

                    performance_logger.info(
                        f"Gemini Request Succeeded in {latency_ms}ms",
                        extra_data={
                            "model": model_name,
                            "latency_ms": latency_ms,
                            "prompt_tokens": prompt_tokens,
                            "candidates_tokens": candidates_tokens
                        }
                    )

                    from backend.core.logging import active_project_id_ctx, active_module_name_ctx, correlation_id_ctx
                    proj_id = active_project_id_ctx.get()
                    mod_name = active_module_name_ctx.get() or "unknown"
                    corr_id = correlation_id_ctx.get() or "unknown"

                    if proj_id:
                        await self._log_analytics(
                            project_id=proj_id,
                            correlation_id=corr_id,
                            module_name=mod_name,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=candidates_tokens,
                            latency_ms=latency_ms
                        )

                    response_text = response.text
                    if not response_text:
                        raise ValueError("Gemini returned an empty response.")

                    return schema.model_validate_json(response_text)

                except ValidationError as ve:
                    logger.warning(
                        f"Pydantic Validation failed on LLM output JSON: attempt {attempt + 1}",
                        extra_data={"errors": ve.errors()}
                    )
                    if attempt == max_validation_attempts - 1:
                        break  # Move to next model
                    current_prompt = (
                        f"{prompt}\n\n"
                        f"ERROR ENCOUNTERED PREVIOUSLY: The response did not match the validation schema. "
                        f"Validation details: {ve.errors()}\n"
                        f"Please re-generate the JSON matching the required schema keys strictly."
                    )

                except ClientError as ce:
                    status_code = ce.status_code if hasattr(ce, 'status_code') else 0
                    if status_code == 429:
                        logger.warning(
                            f"Rate limit hit on model {model_name}, trying next fallback model.",
                            extra_data={"model": model_name}
                        )
                        break  # Move to next model in priority list
                    logger.error(f"Gemini Client API Error [{model_name}]: {str(ce)}", exc_info=ce)
                    raise BaseBusinessException(
                        message=f"LLM API execution failed: {str(ce)}",
                        code="AI_PROVIDER_ERROR",
                        status_code=502
                    )

                except BaseBusinessException:
                    raise

                except Exception as e:
                    logger.error(f"Gemini Client Error [{model_name}]: {str(e)}", exc_info=e)
                    raise BaseBusinessException(
                        message=f"LLM API execution failed: {str(e)}",
                        code="AI_PROVIDER_ERROR",
                        status_code=502
                    )

        raise BaseBusinessException(
            message="All Gemini model variants are currently rate-limited or unavailable. Please retry later.",
            code="AI_QUOTA_EXHAUSTED",
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
            # Input: $0.10 / million tokens -> $0.0000001 per token
            # Output: $0.40 / million tokens -> $0.0000004 per token
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
            logger.error("Failed to persist analytics log in database", exc_info=e)

    async def generate_stream(
        self, 
        prompt: str, 
        schema: Type[T], 
        system_instruction: str | None = None
    ):
        """Generates stream chunks (Placeholder endpoint wrapper)."""
        # Note: Streaming is implemented in the streaming layer context later.
        raise NotImplementedError("Streaming generate is handled inside specific module workflows.")


gemini_adapter = GeminiAdapter()
