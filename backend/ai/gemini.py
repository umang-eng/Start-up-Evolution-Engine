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
