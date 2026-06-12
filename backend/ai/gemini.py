import time
from typing import Type, TypeVar
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from pydantic import BaseModel, ValidationError

from backend.ai.provider import LLMProvider
from backend.core.config import settings
from backend.core.exceptions import BaseBusinessException
from backend.core.logging import logger, performance_logger

T = TypeVar("T", bound=BaseModel)


class GeminiAdapter(LLMProvider):
    """Adapter executing non-blocking content generation using google-generativeai."""

    def __init__(self) -> None:
        self.default_model_name = "gemini-1.5-pro"
        # Configure API Client
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)

    async def generate(
        self, 
        prompt: str, 
        schema: Type[T], 
        system_instruction: str | None = None
    ) -> T:
        """Generates structured content conforming to the schema, with up to 3 repair attempts."""
        model = genai.GenerativeModel(
            model_name=self.default_model_name,
            system_instruction=system_instruction
        )

        attempts = 3
        current_prompt = prompt

        for attempt in range(attempts):
            start_time = time.perf_counter()
            try:
                # Call async Gemini client
                logger.info(
                    f"Initiating Gemini Request: {self.default_model_name}", 
                    extra_data={"attempt": attempt + 1, "prompt_len": len(current_prompt)}
                )
                
                response = await model.generate_content_async(
                    contents=current_prompt,
                    generation_config=GenerationConfig(
                        response_mime_type="application/json",
                        response_schema=schema,
                        temperature=0.2
                    )
                )

                latency_ms = int((time.perf_counter() - start_time) * 1000)
                
                # Token Log Telemetry
                prompt_tokens = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
                candidates_tokens = response.usage_metadata.candidates_token_count if response.usage_metadata else 0
                
                performance_logger.info(
                    f"Gemini Request Succeeded in {latency_ms}ms",
                    extra_data={
                        "model": self.default_model_name,
                        "latency_ms": latency_ms,
                        "prompt_tokens": prompt_tokens,
                        "candidates_tokens": candidates_tokens
                    }
                )

                # Log database telemetry automatically using active ContextVars
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

                # Parse JSON string back to Pydantic Model
                return schema.model_validate_json(response.text)

            except ValidationError as ve:
                logger.warning(
                    f"Pydantic Validation failed on LLM output JSON: attempt {attempt + 1}",
                    extra_data={"errors": ve.errors(), "raw_text": response.text}
                )
                if attempt == attempts - 1:
                    raise BaseBusinessException(
                        message=f"Gemini response failed structural verification after {attempts} attempts.",
                        code="AI_VALIDATION_ERROR",
                        status_code=500
                    )
                # Append repair instructions and retry
                current_prompt = (
                    f"{prompt}\n\n"
                    f"ERROR ENCOUNTERED PREVIOUSLY: The response did not match the validation schema. "
                    f"Validation details: {ve.errors()}\n"
                    f"Please re-generate the JSON matching the required schema keys strictly."
                )

            except Exception as e:
                logger.error(
                    f"Gemini Client API Error: {str(e)}", 
                    exc_info=e
                )
                raise BaseBusinessException(
                    message=f"LLM API execution failed: {str(e)}",
                    code="AI_PROVIDER_ERROR",
                    status_code=502
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

            # Costs for gemini-1.5-pro:
            # Input: $1.25 / million tokens -> $0.00000125 per token
            # Output: $5.00 / million tokens -> $0.000005 per token
            cost = (prompt_tokens * 0.00000125) + (completion_tokens * 0.000005)

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
