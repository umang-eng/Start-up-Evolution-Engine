import os
import asyncio
import time
from typing import Type, TypeVar
from openai import AsyncOpenAI, APIError
from pydantic import BaseModel, ValidationError

from backend.ai.provider import LLMProvider
from backend.core.config import settings
from backend.core.exceptions import BaseBusinessException
from backend.core.logging import logger, performance_logger

T = TypeVar("T", bound=BaseModel)


class GeminiAdapter(LLMProvider):
    """Adapter executing non-blocking content generation using Hugging Face serverless router."""

    def __init__(self) -> None:
        self.model_name = "deepseek-ai/DeepSeek-V4-Pro:novita"
        self._client: AsyncOpenAI | None = None
        if settings.HF_TOKEN:
            self._client = AsyncOpenAI(
                base_url="https://router.huggingface.co/v1",
                api_key=settings.HF_TOKEN
            )

    @property
    def client(self) -> AsyncOpenAI:
        if not self._client:
            # Fallback to environment directly or re-load in case it was loaded late
            hf_token = settings.HF_TOKEN or os.getenv("HF_TOKEN")
            if hf_token:
                self._client = AsyncOpenAI(
                    base_url="https://router.huggingface.co/v1",
                    api_key=hf_token
                )
                return self._client
            raise BaseBusinessException(
                message="Hugging Face token is not configured. Set HF_TOKEN in your environment.",
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
        """Generates structured content conforming to the schema using DeepSeek on Hugging Face router."""
        max_validation_attempts = 2
        current_prompt = prompt
        last_error: Exception | None = None

        for attempt in range(max_validation_attempts):
            start_time = time.perf_counter()
            try:
                logger.info(
                    f"Hugging Face Request: model={self.model_name} attempt={attempt + 1}",
                    extra_data={"model": self.model_name, "attempt": attempt + 1, "prompt_len": len(current_prompt)}
                )

                messages = []
                if system_instruction:
                    messages.append({"role": "system", "content": system_instruction})
                
                # Instruct the model clearly to return valid JSON conforming to the schema
                messages.append({
                    "role": "user",
                    "content": f"{current_prompt}\n\nYou must return a valid JSON object matching this schema:\n{schema.model_json_schema()}"
                })

                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.3,
                    max_tokens=8192
                )

                latency_ms = int((time.perf_counter() - start_time) * 1000)
                
                # Extract tokens usage info if present
                prompt_tokens = response.usage.prompt_tokens if response.usage else 0
                completion_tokens = response.usage.completion_tokens if response.usage else 0

                performance_logger.info(
                    f"Hugging Face OK: {self.model_name} in {latency_ms}ms",
                    extra_data={
                        "model": self.model_name,
                        "latency_ms": latency_ms,
                        "prompt_tokens": prompt_tokens,
                        "candidates_tokens": completion_tokens
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
                        completion_tokens=completion_tokens,
                        latency_ms=latency_ms
                    ))

                response_text = response.choices[0].message.content
                if not response_text or not response_text.strip():
                    raise ValueError(f"Hugging Face returned an empty response on model {self.model_name}.")

                try:
                    return schema.model_validate_json(response_text)
                except ValidationError as ve:
                    logger.warning(
                        f"Validation error attempt {attempt + 1}/{max_validation_attempts} on {self.model_name}",
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
                    break

            except APIError as ae:
                error_str = str(ae)
                status_code = getattr(ae, 'status_code', 0)
                logger.error(f"Hugging Face APIError {status_code}: {error_str}", exc_info=ae)
                
                # Check for rate limit / 429
                if status_code == 429 or "rate limit" in error_str.lower():
                    logger.warning(f"Rate limit 429 on Hugging Face. Waiting 15s before retry.")
                    await asyncio.sleep(15)
                
                last_error = ae
            except Exception as e:
                logger.error(f"Unexpected Hugging Face error: {str(e)}", exc_info=e)
                last_error = e

        raise BaseBusinessException(
            message=f"Hugging Face DeepSeek API call failed: {str(last_error)}",
            code="AI_EXECUTION_ERROR",
            status_code=502
        )

    async def generate_text(self, prompt: str, system_instruction: str | None = None) -> str:
        """Generates a plain text response (non-structured) — used for idea enhancement."""
        try:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=512
            )

            response_text = response.choices[0].message.content
            if response_text and response_text.strip():
                return response_text.strip()
            raise ValueError("Hugging Face returned an empty response")
        except Exception as e:
            logger.error(f"Hugging Face generate_text failed: {str(e)}", exc_info=e)
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

            # Estimate cost for deepseek-ai/DeepSeek-V4-Pro
            cost = (prompt_tokens * 0.0000005) + (completion_tokens * 0.0000015)

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
        raise NotImplementedError("Streaming generate is handled inside specific module workflows.")


gemini_adapter = GeminiAdapter()
