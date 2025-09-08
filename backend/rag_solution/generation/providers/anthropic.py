"""Anthropic provider implementation for text generation."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from core.custom_exceptions import LLMProviderError, NotFoundError, ValidationError
from core.logging_utils import get_logger
from rag_solution.schemas.llm_model_schema import ModelType

from .base import LLMBase

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

    from pydantic import UUID4

    from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
    from rag_solution.schemas.prompt_template_schema import PromptTemplateBase
    from vectordbs.data_types import EmbeddingsList

logger = get_logger("llm.providers.anthropic")


class AnthropicLLM(LLMBase):
    """Anthropic provider implementation using Claude API."""

    def initialize_client(self) -> None:
        """Initialize Anthropic client."""
        try:
            provider = self._get_provider_config("anthropic")
            self._provider = provider

            self.client = anthropic.Anthropic(api_key=str(provider.api_key), base_url=provider.base_url)

            self._models = self.llm_model_service.get_models_by_provider(provider.id)
            self._initialize_default_model()

        except Exception as e:
            raise LLMProviderError(
                provider="anthropic",
                error_type="initialization_failed",
                message=f"Failed to initialize client: {e!s}",
            ) from e

    def _initialize_default_model(self) -> None:
        """Initialize default model for generation."""
        self._default_model = next((m for m in self._models if m.is_default and m.model_type == ModelType.GENERATION), None)

        if not self._default_model:
            logger.warning("No default model configured, using claude-3-opus-20240229")
            self._default_model_id = "claude-3-opus-20240229"
        else:
            self._default_model_id = self._default_model.model_id

    def _get_generation_params(self, user_id: UUID4, model_parameters: LLMParametersInput | None = None) -> dict[str, Any]:
        """Get validated generation parameters."""
        params = model_parameters or self.llm_parameters_service.get_latest_or_default_parameters(user_id)
        return {
            "max_tokens": params.max_new_tokens if params else 150,
            "temperature": params.temperature if params else 0.7,
            "top_p": params.top_p if params else 1.0,
        }

    def generate_text(
        self,
        user_id: UUID4,
        prompt: str | Sequence[str],
        model_parameters: LLMParametersInput | None = None,
        template: PromptTemplateBase | None = None,
        variables: dict[str, Any] | None = None,
    ) -> str | list[str]:
        """Generate text using Anthropic model."""
        try:
            self._ensure_client()
            model_id = self._model_id or self._default_model_id
            generation_params = self._get_generation_params(user_id, model_parameters)

            # Handle batch generation
            if isinstance(prompt, list):
                formatted_prompts = [self._format_prompt(str(p), template, variables) for p in prompt]
                # Use asyncio for concurrent processing
                result = asyncio.run(self._generate_batch(model_id, formatted_prompts, generation_params))
                return result
            else:
                formatted_prompt = self._format_prompt(str(prompt), template, variables)
                response = self.client.messages.create(  # type: ignore[union-attr]
                    model=model_id, messages=[{"role": "user", "content": formatted_prompt}], **generation_params
                )
                content: str | None = response.content[0].text
                if content is None:
                    raise LLMProviderError(provider="anthropic", error_type="generation_failed", message="Anthropic returned empty content")
                return content.strip()

        except (ValidationError, NotFoundError) as e:
            raise LLMProviderError(
                provider="anthropic",
                error_type="invalid_template" if isinstance(e, ValidationError) else "template_not_found",
                message=str(e),
            ) from e
        except Exception as e:
            raise LLMProviderError(provider="anthropic", error_type="generation_failed", message=f"Failed to generate text: {e!s}") from e

    def _format_prompt(self, prompt: str, template: PromptTemplateBase | None = None, variables: dict[str, Any] | None = None) -> str:
        """Format a prompt using a template and variables."""
        if template:
            vars_dict = dict(variables or {})
            vars_dict["prompt"] = prompt
            return self.prompt_template_service.format_prompt_with_template(template, vars_dict)
        return prompt

    async def _generate_batch(self, model_id: str, prompts: list[str], generation_params: dict[str, Any]) -> list[str]:
        """Generate text for multiple prompts concurrently."""

        async def generate_single(prompt: str) -> str:
            # Create a new client for each request to avoid session conflicts
            async with anthropic.AsyncAnthropic(api_key=str(self._provider.api_key), base_url=self._provider.base_url) as client:
                response = await client.messages.create(model=model_id, messages=[{"role": "user", "content": prompt}], **generation_params)
                content: str | None = response.content[0].text
                if content is None:
                    raise LLMProviderError(provider="anthropic", error_type="generation_failed", message="Anthropic returned empty content")
                return content.strip()

        # Process prompts concurrently with a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(10)  # Limit concurrent requests

        async def bounded_generate(prompt: str) -> str:
            async with semaphore:
                return await generate_single(prompt)

        tasks = [bounded_generate(prompt) for prompt in prompts]
        result = await asyncio.gather(*tasks)
        return result

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(3),
    )
    def generate_text_stream(
        self,
        user_id: UUID4,
        prompt: str,
        model_parameters: LLMParametersInput | None = None,
        template: PromptTemplateBase | None = None,
        variables: dict[str, Any] | None = None,
    ) -> Generator[str, None, None]:
        """Generate text in streaming mode."""
        try:
            self._ensure_client()
            model_id = self._model_id or self._default_model_id
            generation_params = self._get_generation_params(user_id, model_parameters)
            generation_params["stream"] = True

            formatted_prompt = self._format_prompt(prompt, template, variables)
            stream = self.client.messages.create(  # type: ignore[union-attr]
                model=model_id, messages=[{"role": "user", "content": formatted_prompt}], **generation_params
            )

            for chunk in stream:
                if chunk.type == "content_block_delta" and chunk.delta.text:
                    yield chunk.delta.text

        except (ValidationError, NotFoundError) as e:
            raise LLMProviderError(
                provider="anthropic",
                error_type="invalid_template" if isinstance(e, ValidationError) else "template_not_found",
                message=str(e),
            ) from e
        except Exception as e:
            raise LLMProviderError(
                provider="anthropic",
                error_type="streaming_failed",
                message=f"Failed to generate streaming text: {e!s}",
            ) from e

    def get_embeddings(self, texts: str | Sequence[str]) -> EmbeddingsList:  # noqa: ARG002
        """Generate embeddings for texts.

        Raises:
            LLMProviderError: Anthropic does not provide embeddings
        """
        raise LLMProviderError(provider="anthropic", error_type="not_supported", message="Anthropic does not provide embeddings")

    def close(self) -> None:
        """Clean up provider resources."""
        if hasattr(self, "client") and self.client:
            self.client.close()
        super().close()
