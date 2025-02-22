"""Anthropic provider implementation for text generation."""

from typing import Dict, List, Optional, Union, Generator, Any, Sequence
from uuid import UUID
from core.logging_utils import get_logger
from tenacity import retry, stop_after_attempt, wait_exponential
import asyncio

import anthropic
from core.custom_exceptions import LLMProviderError, ValidationError, NotFoundError
from .base import LLMBase
from vectordbs.data_types import EmbeddingsList
from rag_solution.schemas.prompt_template_schema import PromptTemplateBase
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.llm_provider_schema import ModelType

logger = get_logger("llm.providers.anthropic")

class AnthropicLLM(LLMBase):
    """Anthropic provider implementation using Claude API."""

    def initialize_client(self) -> None:
        """Initialize Anthropic client."""
        try:
            provider = self._get_provider_config("anthropic")
            self._provider = provider

            self.client = anthropic.Anthropic(
                api_key=provider.api_key,
                base_url=provider.base_url
            )

            self._models = self.llm_provider_service.get_models_by_provider(provider.id)
            self._initialize_default_model()

        except Exception as e:
            raise LLMProviderError(
                provider="anthropic",
                error_type="initialization_failed",
                message=f"Failed to initialize client: {str(e)}"
            )

    def _initialize_default_model(self) -> None:
        """Initialize default model for generation."""
        self._default_model = next(
            (m for m in self._models if m.is_default and m.model_type == ModelType.GENERATION),
            None
        )

        if not self._default_model:
            logger.warning("No default model configured, using claude-3-opus-20240229")
            self._default_model_id = "claude-3-opus-20240229"
        else:
            self._default_model_id = self._default_model.model_id

    def _get_generation_params(self, user_id: UUID, model_parameters: Optional[LLMParametersInput] = None) -> Dict[str, Any]:
        """Get validated generation parameters."""
        params = self.llm_parameters_service.get_parameters(user_id) if not model_parameters else \
            self.llm_parameters_service.create_or_update_parameters(user_id, model_parameters)

        return {
            "max_tokens": params.max_new_tokens if params else 150,
            "temperature": params.temperature if params else 0.7,
            "top_p": params.top_p if params else 1.0
        }

    def generate_text(
        self,
        user_id: UUID,
        prompt: Union[str, Sequence[str]],
        model_parameters: Optional[LLMParametersInput] = None,
        template: Optional[PromptTemplateBase] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> Union[str, list[str]]:
        """Generate text using Anthropic model."""
        try:
            self._ensure_client()
            model_id = self._model_id or self._default_model_id
            generation_params = self._get_generation_params(user_id, model_parameters)

            # Handle batch generation
            if isinstance(prompt, list):
                formatted_prompts = [
                    self._format_prompt(p, template, variables) for p in prompt
                ]
                # Use asyncio for concurrent processing
                return asyncio.run(self._generate_batch(model_id, formatted_prompts, generation_params))
            else:
                formatted_prompt = self._format_prompt(prompt, template, variables)
                response = self.client.messages.create(
                    model=model_id,
                    messages=[{"role": "user", "content": formatted_prompt}],
                    **generation_params
                )
                return response.content[0].text.strip()

        except (ValidationError, NotFoundError) as e:
            raise LLMProviderError(
                provider="anthropic",
                error_type="invalid_template" if isinstance(e, ValidationError) else "template_not_found",
                message=str(e)
            )
        except Exception as e:
            raise LLMProviderError(
                provider="anthropic",
                error_type="generation_failed",
                message=f"Failed to generate text: {str(e)}"
            )

    def _format_prompt(
        self,
        prompt: str,
        template: Optional[PromptTemplateBase] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format a prompt using a template and variables."""
        if template:
            vars_dict = dict(variables or {})
            vars_dict['prompt'] = prompt
            return self.prompt_template_service.format_prompt(template.id, vars_dict)
        return prompt

    async def _generate_batch(
        self,
        model_id: str,
        prompts: List[str],
        generation_params: Dict[str, Any]
    ) -> List[str]:
        """Generate text for multiple prompts concurrently."""
        async def generate_single(prompt: str) -> str:
            # Create a new client for each request to avoid session conflicts
            async with anthropic.AsyncAnthropic(
                api_key=self._provider.api_key,
                base_url=self._provider.base_url
            ) as client:
                response = await client.messages.create(
                    model=model_id,
                    messages=[{"role": "user", "content": prompt}],
                    **generation_params
                )
                return response.content[0].text.strip()

        # Process prompts concurrently with a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(10)  # Limit concurrent requests
        async def bounded_generate(prompt: str) -> str:
            async with semaphore:
                return await generate_single(prompt)

        tasks = [bounded_generate(prompt) for prompt in prompts]
        return await asyncio.gather(*tasks)

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(3),
    )
    def generate_text_stream(
        self,
        user_id: UUID,
        prompt: str,
        model_parameters: Optional[LLMParametersInput] = None,
        template: Optional[PromptTemplateBase] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> Generator[str, None, None]:
        """Generate text in streaming mode."""
        try:
            self._ensure_client()
            model_id = self._model_id or self._default_model_id
            generation_params = self._get_generation_params(user_id, model_parameters)
            generation_params["stream"] = True

            formatted_prompt = self._format_prompt(prompt, template, variables)
            stream = self.client.messages.create(
                model=model_id,
                messages=[{"role": "user", "content": formatted_prompt}],
                **generation_params
            )

            for chunk in stream:
                if chunk.type == "content_block_delta" and chunk.delta.text:
                    yield chunk.delta.text

        except (ValidationError, NotFoundError) as e:
            raise LLMProviderError(
                provider="anthropic",
                error_type="invalid_template" if isinstance(e, ValidationError) else "template_not_found",
                message=str(e)
            )
        except Exception as e:
            raise LLMProviderError(
                provider="anthropic",
                error_type="streaming_failed",
                message=f"Failed to generate streaming text: {str(e)}"
            )

    def get_embeddings(
        self,
        texts: Union[str, List[str]]
    ) -> EmbeddingsList:
        """Generate embeddings for texts.
        
        Raises:
            LLMProviderError: Anthropic does not provide embeddings
        """
        raise LLMProviderError(
            provider="anthropic",
            error_type="not_supported",
            message="Anthropic does not provide embeddings"
        )

    def close(self) -> None:
        """Clean up provider resources."""
        if hasattr(self, 'client') and self.client:
            self.client.close()
        super().close()
