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

    async def generate(
        self,
        prompt: str,
        schema: Type[T],
        system_instruction: str | None = None
    ) -> T:
        """Generates structured content conforming to the schema with exponential backoff on rate limits."""
        max_validation_attempts = 2
        current_prompt = prompt
        last_error: Exception | None = None

        for model_idx, model_name in enumerate(MODEL_PRIORITY):
            for attempt in range(max_validation_attempts):
                start_time = time.perf_counter()
                try:
                    logger.info(
                        f"Gemini Request: model={model_name} attempt={attempt + 1}",
                        extra_data={"model": model_name, "attempt": attempt + 1, "prompt_len": len(current_prompt)}
                    )

                    config = types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema,
                        temperature=0.3,
                        system_instruction=system_instruction,
                        max_output_tokens=8192,
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
                        f"Gemini OK: {model_name} in {latency_ms}ms",
                        extra_data={
                            "model": model_name,
                            "latency_ms": latency_ms,
                            "prompt_tokens": prompt_tokens,
                            "candidates_tokens": candidates_tokens
                        }
                    )

                    # Fire-and-forget analytics logging
                    from backend.core.logging import active_project_id_ctx, active_module_name_ctx, correlation_id_ctx
                    proj_id = active_project_id_ctx.get()
                    if proj_id:
                        mod_name = active_module_name_ctx.get() or "unknown"
                        corr_id = correlation_id_ctx.get() or "unknown"
                        asyncio.create_task(self._log_analytics(
                            project_id=proj_id,
                            correlation_id=corr_id,
                            module_name=mod_name,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=candidates_tokens,
                            latency_ms=latency_ms
                        ))

                    response_text = response.text
                    if not response_text or not response_text.strip():
                        raise ValueError(f"Gemini returned an empty response on model {model_name}.")

                    try:
                        return schema.model_validate_json(response_text)
                    except ValidationError as ve:
                        logger.warning(
                            f"Validation error attempt {attempt + 1}/{max_validation_attempts} on {model_name}",
                            extra_data={"errors": ve.errors()[:3]}
                        )
                        if attempt < max_validation_attempts - 1:
                            current_prompt = (
                                f"{prompt}\n\n"
                                f"IMPORTANT: Your previous response failed schema validation. "
                                f"Errors: {ve.errors()[:3]}\n"
                                f"Return ONLY valid JSON matching the schema exactly. No extra text."
                            )
                            continue
                        last_error = ve
                        break  # Try next model

                except ClientError as ce:
                    error_str = str(ce)
                    status_code = getattr(ce, 'status_code', 0)

                    if status_code == 429 or "RESOURCE_EXHAUSTED" in error_str:
                        backoff = MODEL_BACKOFF_SECONDS[min(model_idx, len(MODEL_BACKOFF_SECONDS) - 1)]
                        logger.warning(
                            f"Rate limit 429 on {model_name}. Waiting {backoff}s before trying next model.",
                            extra_data={"model": model_name, "backoff_seconds": backoff}
                        )
                        await asyncio.sleep(backoff)
                    else:
                        # 404 (model not found), 400 (bad request), 5xx — try next model without waiting
                        logger.warning(
                            f"ClientError {status_code} on {model_name}, trying next model.",
                            extra_data={"model": model_name, "error": error_str[:100]}
                        )

                    last_error = ce
                    break  # Move to next model

                except BaseBusinessException:
                    raise

                except Exception as e:
                    logger.error(f"Unexpected Gemini error [{model_name}]: {str(e)}", exc_info=e)
                    last_error = e
                    break  # Try next model

        raise BaseBusinessException(
            message=(
                "All Gemini model variants are rate-limited or unavailable. "
                "The Gemini API free tier has per-minute/per-day limits. "
                "Please wait 1-2 minutes and try again, or upgrade your Gemini API quota."
            ),
            code="AI_QUOTA_EXHAUSTED",
            status_code=503
        )

    async def generate_text(self, prompt: str, system_instruction: str | None = None) -> str:
        """Generates a plain text response (non-structured) — used for idea enhancement.
        
        Treats ANY model-level error (404, 429, 5xx) as non-fatal and tries the next model.
        Only raises after ALL models are exhausted.
        """
        last_error: Exception | None = None

        for model_idx, model_name in enumerate(MODEL_PRIORITY):
            try:
                config = types.GenerateContentConfig(
                    temperature=0.7,
                    system_instruction=system_instruction,
                    max_output_tokens=512,
                )

                response = await self.client.aio.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config,
                )

                response_text = response.text
                if response_text and response_text.strip():
                    return response_text.strip()

                # Empty response — try next model
                last_error = ValueError(f"Empty response from {model_name}")
                continue

            except ClientError as ce:
                error_str = str(ce)
                status_code = getattr(ce, 'status_code', 0)
                
                if status_code == 429 or "RESOURCE_EXHAUSTED" in error_str:
                    backoff = MODEL_BACKOFF_SECONDS[min(model_idx, len(MODEL_BACKOFF_SECONDS) - 1)]
                    logger.warning(
                        f"Rate limit 429 on {model_name} (text). Waiting {backoff}s.",
                        extra_data={"model": model_name}
                    )
                    await asyncio.sleep(backoff)
                else:
                    # 404, 400, 5xx — model unavailable, try next without waiting
                    logger.warning(
                        f"ClientError {status_code} on {model_name} (text), trying next model.",
                        extra_data={"model": model_name, "error": error_str[:100]}
                    )
                
                last_error = ce
                continue  # Always try next model for any client error

            except Exception as e:
                logger.warning(f"Unexpected error on {model_name} (text): {str(e)[:100]}")
                last_error = e
                continue

        # All models failed — raise meaningful error
        raise BaseBusinessException(
            message="AI service is currently unavailable. Please try again in a moment.",
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
