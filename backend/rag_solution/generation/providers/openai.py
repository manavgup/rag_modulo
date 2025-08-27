"""OpenAI provider implementation for text generation and embeddings."""

from typing import Dict, List, Optional, Union, Generator, Any, Sequence
from uuid import UUID
from core.logging_utils import get_logger
from tenacity import retry, stop_after_attempt, wait_exponential
import asyncio

from openai import OpenAI, AsyncOpenAI
from core.custom_exceptions import LLMProviderError, ValidationError, NotFoundError
from .base import LLMBase
from vectordbs.data_types import EmbeddingsList
from rag_solution.schemas.prompt_template_schema import PromptTemplateBase
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.llm_model_schema import ModelType

logger = get_logger("llm.providers.openai")

class OpenAILLM(LLMBase):
    """OpenAI provider implementation using OpenAI API."""

    def initialize_client(self) -> None:
        """Initialize OpenAI client."""
        try:
            provider = self._get_provider_config("openai")
            self._provider = provider

            self.client = OpenAI(
                api_key=provider.api_key,
                organization=provider.org_id,
                base_url=provider.base_url
            )
            self.async_client = AsyncOpenAI(
                api_key=provider.api_key,
                organization=provider.org_id,
                base_url=provider.base_url
            )

            self._models = self.llm_model_service.get_models_by_provider(provider.id)
            self._initialize_default_models()

        except Exception as e:
            raise LLMProviderError(
                provider="openai",
                error_type="initialization_failed",
                message=f"Failed to initialize client: {str(e)}"
            )

    def _initialize_default_models(self) -> None:
        """Initialize default models for generation and embeddings."""
        self._default_model = next(
            (m for m in self._models if m.is_default and m.model_type == ModelType.GENERATION),
            None
        )
        self._default_embedding_model = next(
            (m for m in self._models if m.is_default and m.model_type == ModelType.EMBEDDING),
            None
        )

        if not self._default_model:
            logger.warning("No default model configured, using gpt-3.5-turbo")
            self._default_model_id = "gpt-3.5-turbo"
        else:
            self._default_model_id = self._default_model.model_id

        if not self._default_embedding_model:
            logger.warning("No default embedding model configured, using text-embedding-ada-002")
            self._default_embedding_model_id = "text-embedding-ada-002"
        else:
            self._default_embedding_model_id = self._default_embedding_model.model_id

    def _get_generation_params(self, user_id: UUID, model_parameters: Optional[LLMParametersInput] = None) -> Dict[str, Any]:
        """Get validated generation parameters."""
        params = model_parameters or self.llm_parameters_service.get_latest_or_default_parameters(user_id)

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
        """Generate text using OpenAI model."""
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
                response = self.client.chat.completions.create(
                    model=model_id,
                    messages=[{"role": "user", "content": formatted_prompt}],
                    **generation_params
                )
                return response.choices[0].message.content.strip()

        except (ValidationError, NotFoundError) as e:
            raise LLMProviderError(
                provider="openai",
                error_type="invalid_template" if isinstance(e, ValidationError) else "template_not_found",
                message=str(e)
            )
        except Exception as e:
            raise LLMProviderError(
                provider="openai",
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
            response = await self.async_client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                **generation_params
            )
            return response.choices[0].message.content.strip()

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
            stream = self.client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": formatted_prompt}],
                **generation_params
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except (ValidationError, NotFoundError) as e:
            raise LLMProviderError(
                provider="openai",
                error_type="invalid_template" if isinstance(e, ValidationError) else "template_not_found",
                message=str(e)
            )
        except Exception as e:
            raise LLMProviderError(
                provider="openai",
                error_type="streaming_failed",
                message=f"Failed to generate streaming text: {str(e)}"
            )

    def get_embeddings(
        self,
        texts: Union[str, List[str]]
    ) -> EmbeddingsList:
        """Generate embeddings for texts."""
        try:
            self._ensure_client()

            if isinstance(texts, str):
                texts = [texts]

            # OpenAI embeddings API already handles batching efficiently
            response = self.client.embeddings.create(
                model=self._default_embedding_model_id,
                input=texts
            )
            return [data.embedding for data in response.data]

        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(
                provider="openai",
                error_type="embeddings_failed",
                message=f"Failed to generate embeddings: {str(e)}"
            )

    def close(self) -> None:
        """Clean up provider resources."""
        if hasattr(self, 'client') and self.client:
            self.client.close()
        if hasattr(self, 'async_client') and self.async_client:
            self.async_client.close()
        super().close()