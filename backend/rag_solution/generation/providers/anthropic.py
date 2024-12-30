"""Anthropic provider implementation for text generation."""

from typing import Dict, List, Optional, Union, Generator, Any
from core.logging_utils import get_logger
from tenacity import retry, stop_after_attempt, wait_exponential

from anthropic import Anthropic
from core.custom_exceptions import LLMProviderError

from .base import LLMProvider, ProviderConfig
from vectordbs.data_types import EmbeddingsList
from rag_solution.schemas.llm_parameters_schema import LLMParametersBase
from rag_solution.schemas.prompt_template_schema import PromptTemplateBase

logger = get_logger("llm.providers.anthropic")
class AnthropicProvider(LLMProvider):
    """Anthropic implementation using Anthropic API."""

    def __init__(self, provider_config_service) -> None:
        """Initialize Anthropic provider with cached client."""
        super().__init__()
        self.provider_config_service = provider_config_service
        self.provider_config = self.provider_config_service.get_provider_config("anthropic")
        if not self.provider_config:
            raise LLMProviderError(
                provider="anthropic",
                error_type="config_invalid",
                message="No configuration found for Anthropic provider"
            )
    
    def initialize_client(self) -> None:
        """Initialize Anthropic client."""
        try:
            self.client = Anthropic(api_key=self.provider_config.api_key)
            self.default_model = "claude-3-opus-20240229"
            self._model_cache = {}
            self.rate_limit = 10
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {str(e)}")
            raise LLMProviderError(f"Initialization failed: {str(e)}")

    def get_embeddings(
        self,
        texts: Union[str, List[str]],
        provider_config: Optional[ProviderConfig] = None
    ) -> EmbeddingsList:
        """Embeddings not supported by Anthropic."""
        raise NotImplementedError("Anthropic does not support embeddings")

    def generate_text(
    self,
    prompt: Union[str, List[str]],
    model_parameters: LLMParametersBase,
    template: Optional[PromptTemplateBase] = None,
    provider_config: Optional[ProviderConfig] = None
) -> Union[str, List[str]]:
        """Generate text using the Anthropic model."""
        try:
            self._ensure_client()
            # Prepare the prompt using the template if provided
            prompt = self._prepare_prompts(prompt, template)

            if isinstance(prompt, list):
                responses = []
                for p in prompt:
                    response = self.client.messages.create(
                        model=self.default_model,
                        max_tokens=model_parameters.max_new_tokens,
                        temperature=model_parameters.temperature,
                        messages=[{"role": "user", "content": p}]
                    )
                    responses.append(response.content[0].text)

                logger.info(f"***** Response type: {type(responses)}")
                logger.info(f"***** Response content: {responses}")
                return responses
            else:
                response = self.client.messages.create(
                    model=self.default_model,
                    max_tokens=model_parameters.max_new_tokens,
                    temperature=model_parameters.temperature,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
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

            # Create the stream object
            with self.client.messages.stream(
                model=self.default_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=model_parameters.max_new_tokens,
                temperature=model_parameters.temperature,
            ) as stream:
                # Log the stream object for debugging
                logger.debug(f"Stream object: {stream}")

                # Process the stream events
                for event in stream:
                    logger.debug(f"Received event: {event}")

                    if hasattr(event, 'type') and event.type == 'content_block_delta':
                        if hasattr(event.delta, 'text'):
                            yield event.delta.text
                    # Alternative check for text events
                    elif hasattr(event, 'type') and event.type == 'text':
                        if hasattr(event, 'text'):
                            yield event.text
                    else:
                        logger.debug(f"Skipping non-text event: {event}")
                        continue
        except Exception as e:
            logger.error(f"Streaming generation failed: {str(e)}")
            raise LLMProviderError(f"Failed to generate streaming text: {str(e)}")

    def close(self) -> None:
        """Clean up provider resources."""
        if hasattr(self, 'client') and self.client:
            self.client.close()
        self.client = None
