"""OpenAI provider implementation for text generation and embeddings."""

from typing import Dict, List, Optional, Union, Generator, Any
from core.logging_utils import get_logger
from tenacity import retry, stop_after_attempt, wait_exponential

from openai import OpenAI

from .base import LLMProvider, ProviderConfig
from core.config import settings
from vectordbs.data_types import EmbeddingsList
from core.custom_exceptions import LLMProviderError
from rag_solution.schemas.llm_parameters_schema import LLMParametersBase
from rag_solution.schemas.prompt_template_schema import PromptTemplateBase

logger = get_logger("llm.providers.openai")

class OpenAIProvider(LLMProvider):
    """OpenAI implementation using OpenAI API."""

    def __init__(self, provider_config_service) -> None:
        """Initialize OpenAI provider with cached client."""
        super().__init__()
        self.provider_config_service = provider_config_service
        self.provider_config = self.provider_config_service.get_provider_config("openai")
        if not self.provider_config:
            raise LLMProviderError(
                provider="openai",
                error_type="config_invalid",
                message="No configuration found for OpenAI provider"
            )
    
    def initialize_client(self) -> None:
        """Initialize OpenAI client."""
        try:
            self.client = OpenAI(
                api_key=self.provider_config.api_key,
                organization=self.provider_config.org_id
            )
            self.default_model = "gpt-3.5-turbo"
            self.default_embedding_model = "text-embedding-ada-002"
            self._model_cache = {}
            self.rate_limit = 10
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            raise LLMProviderError(f"Initialization failed: {str(e)}")

    async def get_embeddings(
        self,
        texts: Union[str, List[str]],
        provider_config: Optional[ProviderConfig] = None
    ) -> EmbeddingsList:
        """Generate embeddings for texts."""
        try:
            self._ensure_client()
            if isinstance(texts, str):
                texts = [texts]

            response = await self.client.embeddings.create(
                model=self.default_embedding_model,
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise LLMProviderError(f"Failed to generate embeddings: {str(e)}")

    def generate_text(
    self,
    prompt: Union[str, List[str]],
    model_parameters: LLMParametersBase,
    template: Optional[PromptTemplateBase] = None,
    provider_config: Optional[ProviderConfig] = None
) -> Union[str, List[str]]:
        """Generate text using the OpenAI model."""
        try:
            self._ensure_client()
            # Prepare the prompt using the template if provided
            prompt = self._prepare_prompts(prompt, template)

            if isinstance(prompt, list):
                responses = []
                for p in prompt:
                    response = self.client.chat.completions.create(
                        model=self.default_model,
                        messages=[{"role": "user", "content": p}],
                        max_tokens=model_parameters.max_new_tokens,
                        temperature=model_parameters.temperature,
                        top_p=model_parameters.top_p,
                        seed=model_parameters.random_seed
                    )
                    responses.append(response.choices[0].message.content.strip())

                return responses
            else:
                response = self.client.chat.completions.create(
                    model=self.default_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=model_parameters.max_new_tokens,
                    temperature=model_parameters.temperature,
                    top_p=model_parameters.top_p,
                    seed=model_parameters.random_seed
                )
                return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Text generation failed: {str(e)}")
            raise LLMProviderError(f"Failed to generate text: {str(e)}")

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(3),
    )
    def generate_text_stream(
        self,
        prompt: str,
    model_parameters: LLMParametersBase,
    template: Optional[PromptTemplateBase] = None,
        provider_config: Optional[ProviderConfig] = None
    ) -> Generator[str, None, None]:
        """Generate text in streaming mode."""
        try:
            self._ensure_client()
            # Prepare the prompt using the template if provided
            prompt = self._prepare_prompts(prompt, template)

            stream = self.client.chat.completions.create(
                model=self.default_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=model_parameters.max_new_tokens,
                temperature=model_parameters.temperature,
                stream=True,
                seed=model_parameters.random_seed
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Streaming generation failed: {str(e)}")
            raise LLMProviderError(f"Failed to generate streaming text: {str(e)}")

    def close(self) -> None:
        """Clean up provider resources."""
        if hasattr(self, 'client') and self.client:
            self.client.close()
        self.client = None
