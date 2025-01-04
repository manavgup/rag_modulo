"""Base provider interface for LLM interactions using established schemas."""

from abc import ABC, abstractmethod
from typing import Generator, List, Optional, Union, Dict, Any
from pathlib import Path

from core.logging_utils import setup_logging, get_logger
from core.custom_exceptions import LLMProviderError
from rag_solution.schemas.llm_parameters_schema import LLMParametersBase
from rag_solution.schemas.prompt_template_schema import PromptTemplateBase
from rag_solution.schemas.provider_config_schema import ProviderRuntimeSettings, ProviderExtendedSettings
from vectordbs.data_types import EmbeddingsList

# Setup logging
setup_logging(Path("logs"))
logger = get_logger("llm.providers")

# Error types for consistent error reporting
PROVIDER_ERROR_TYPES = {
    # Initialization errors
    "INIT_FAILED": "initialization_failed",
    "AUTH_FAILED": "authentication_failed",
    "CONFIG_INVALID": "configuration_invalid",
    
    # Runtime errors
    "RATE_LIMIT": "rate_limit_exceeded",
    "TIMEOUT": "request_timeout",
    "API_ERROR": "api_error",
    
    # Generation errors
    "PROMPT_ERROR": "prompt_preparation_failed",
    "TEMPLATE_ERROR": "template_formatting_failed",
    "PARAM_ERROR": "invalid_parameters",
    
    # Resource errors
    "MODEL_ERROR": "model_not_available",
    "RESOURCE_ERROR": "resource_exhausted",
    
    # Response errors
    "RESPONSE_ERROR": "invalid_response",
    "PARSING_ERROR": "response_parsing_failed"
}

class ProviderConfig(ProviderExtendedSettings):
    """Runtime configuration for LLM providers.
    
    This class inherits from ProviderExtendedSettings which provides:
    - Base runtime settings (timeout, max_retries, batch_size, retry_delay) from ProviderRuntimeSettings
    - Extended runtime settings (concurrency_limit, stream, rate_limit)
    
    The separation of ProviderRuntimeSettings and ProviderExtendedSettings allows for:
    - Common settings to be shared across different types of configurations
    - Provider-specific settings to be added without affecting the base settings
    - Consistent runtime behavior across all providers
    
    See ProviderRuntimeSettings and ProviderExtendedSettings for full documentation.
    """
    pass

class LLMProvider(ABC):
    """Abstract base class for language model providers."""

    def __init__(self) -> None:
        """Initialize provider with logging."""
        self.logger = get_logger(f"llm.providers.{self.__class__.__name__}")
        self.logger.info(f"Initializing {self.__class__.__name__}")
        self.client = None
        self._model_id: Optional[str] = None
        self._parameters: Optional[Dict[str, Any]] = None
        self.initialize_client()

    @property
    def model_id(self) -> Optional[str]:
        """Get the current model ID."""
        return self._model_id

    @model_id.setter
    def model_id(self, value: str) -> None:
        """Set the model ID and reinitialize client if needed."""
        if value != self._model_id:
            self._model_id = value
            self.initialize_client()

    @property
    def parameters(self) -> Optional[Dict[str, Any]]:
        """Get the current parameters."""
        return self._parameters

    @parameters.setter
    def parameters(self, value: Dict[str, Any]) -> None:
        """Set the parameters and reinitialize client if needed."""
        if value != self._parameters:
            self._parameters = value
            self.initialize_client()
    
    @abstractmethod
    def initialize_client(self) -> None:
        """Initialize the provider client. Must be implemented by subclasses."""
        pass

    def _ensure_client(self) -> None:
        """Ensure client is initialized."""
        if self.client is None:
            self.logger.warning("Client not initialized, attempting to initialize")
            self.initialize_client()
            if self.client is None:
                raise LLMProviderError(
                    provider=self.__class__.__name__.lower(),
                    error_type=PROVIDER_ERROR_TYPES["INIT_FAILED"],
                    message="Failed to initialize client"
                )

    def _prepare_prompts(
        self,
        prompt: Union[str, List[str]],
        template: Optional[PromptTemplateBase] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> Union[str, List[str]]:
        """Prepare prompts using template components.

        Args:
            prompt: The input prompt or list of prompts
            template: Optional template to format the prompt
            variables: Optional variables to substitute in the template

        Returns:
            The prepared prompt or list of prompts

        Raises:
            LLMProviderError: If prompt preparation fails
        """
        if template is None:
            return prompt

        try:
            if isinstance(prompt, str):
                # Ensure variables is a dict and include the prompt
                vars_dict = dict(variables or {})
                vars_dict['prompt'] = prompt
                return template.format_prompt(**vars_dict)

            if isinstance(prompt, list):
                return [self._prepare_prompts(p, template, variables) for p in prompt]

            raise LLMProviderError(
                provider=self.__class__.__name__.lower(),
                error_type=PROVIDER_ERROR_TYPES["PROMPT_ERROR"],
                message=f"Unsupported prompt type: {type(prompt)}"
            )

        except Exception as e:
            raise LLMProviderError(
                provider=self.__class__.__name__.lower(),
                error_type=PROVIDER_ERROR_TYPES["TEMPLATE_ERROR"],
                message=f"Failed to prepare prompt: {str(e)}"
            )

    @abstractmethod
    def generate_text(
        self,
        prompt: Union[str, List[str]],
        model_parameters: LLMParametersBase,
        template: Optional[PromptTemplateBase] = None,
        provider_config: Optional[ProviderConfig] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> Union[str, List[str]]:
        """Generate text using the model.

        Args:
            prompt: Input text prompt or list of prompts
            model_parameters: Generation parameters from model config
            template: Optional prompt template
            provider_config: Optional provider-specific settings
            variables: Optional variables to substitute in template

        Returns:
            Generated text response or list of responses
        """
        pass

    @abstractmethod
    def generate_text_stream(
        self,
        prompt: str,
        model_parameters: LLMParametersBase,
        template: Optional[PromptTemplateBase] = None,
        provider_config: Optional[ProviderConfig] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> Generator[str, None, None]:
        """Generate text in streaming mode.

        Args:
            prompt: Input text prompt
            model_parameters: Generation parameters from model config
            template: Optional prompt template
            provider_config: Optional provider-specific settings
            variables: Optional variables to substitute in template

        Yields:
            Generated text chunks
        """
        pass

    @abstractmethod
    def get_embeddings(
        self,
        texts: Union[str, List[str]],
        provider_config: Optional[ProviderConfig] = None
    ) -> EmbeddingsList:
        """Generate embeddings for texts.

        Args:
            texts: Text or list of texts to embed
            provider_config: Optional provider-specific settings

        Returns:
            List of embedding vectors
        """
        pass

    def close(self) -> None:
        """Clean up provider resources."""
        pass
