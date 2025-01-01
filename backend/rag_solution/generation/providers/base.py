"""Base provider interface for LLM interactions using established schemas."""

from abc import ABC, abstractmethod
from typing import Generator, List, Optional, Union, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict

from core.logging_utils import setup_logging, get_logger
from core.custom_exceptions import LLMProviderError
from rag_solution.schemas.llm_parameters_schema import LLMParametersBase
from rag_solution.schemas.prompt_template_schema import PromptTemplateBase
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

class ProviderConfig(BaseModel):
    """Runtime configuration for LLM providers.
    
    This configuration class handles runtime behavior settings only.
    Startup configuration (API keys, endpoints, etc.) is managed by
    provider_config_service.
    
    Attributes:
        concurrency_limit: Maximum concurrent requests
        timeout: Request timeout in seconds
        batch_size: Size of batches for bulk operations
        stream: Whether to use streaming mode
        rate_limit: Maximum requests per second
        retry_attempts: Number of retry attempts
        retry_delay: Delay between retries in seconds
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "concurrency_limit": 5,
                "timeout": 60,
                "batch_size": 20,
                "stream": True,
                "rate_limit": 20,
                "retry_attempts": 3,
                "retry_delay": 1.0
            }]
        }
    )

    concurrency_limit: int = Field(
        default=10,
        ge=1,
        description="Maximum concurrent requests"
    )
    timeout: int = Field(
        default=30,
        ge=1,
        description="Request timeout in seconds"
    )
    batch_size: int = Field(
        default=10,
        ge=1,
        description="Size of batches for bulk operations"
    )
    stream: bool = Field(
        default=False,
        description="Whether to use streaming mode"
    )
    rate_limit: int = Field(
        default=10,
        ge=1,
        description="Maximum requests per second"
    )
    retry_attempts: int = Field(
        default=3,
        ge=0,
        description="Number of retry attempts"
    )
    retry_delay: float = Field(
        default=1.0,
        ge=0.0,
        description="Delay between retries in seconds"
    )

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

    def format_prompt(self, template: PromptTemplateBase, variables: Dict[str, Any]) -> str:
        """Format prompt template with variables.

        Args:
            template: The prompt template to format
            variables: The variables to substitute in the template

        Returns:
            str: The formatted prompt string

        Raises:
            LLMProviderError: If template formatting fails
        """
        try:
            # Build prompt parts
            formatted_parts: List[str] = []

            # Add system prompt
            if template.system_prompt:
                formatted_parts.append(template.system_prompt)

            # Add context if present
            if template.context_prefix and 'context' in variables:
                formatted_parts.append(f"{template.context_prefix}{variables['context']}")

            # Add query/question if present
            if template.query_prefix and 'question' in variables:
                formatted_parts.append(f"{template.query_prefix}{variables['question']}")

            # Add output prefix with specific template handling
            if template.output_prefix:
                if 'num_questions' in variables:
                    formatted_parts.append(f"{template.output_prefix}Generate {variables['num_questions']} questions.")
                else:
                    formatted_parts.append(template.output_prefix)

            return "\n\n".join(part.strip() for part in formatted_parts if part)

        except Exception as e:
            raise LLMProviderError(
                provider=self.__class__.__name__.lower(),
                error_type=PROVIDER_ERROR_TYPES["TEMPLATE_ERROR"],
                message=f"Failed to format prompt template: {str(e)}"
            )

    def _prepare_prompts(
        self,
        prompt: Union[str, List[str]],
        template: Optional[PromptTemplateBase] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> Union[str, List[str]]:
        """Prepare prompts using template if provided.

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

        if isinstance(prompt, str):
            vars_dict = variables or {"input": prompt}
            return self.format_prompt(template, vars_dict)

        if isinstance(prompt, list):
            vars_list = variables or [{"input": p} for p in prompt]
            return [
                self.format_prompt(template, vars)
                for vars in vars_list
            ]

        raise LLMProviderError(
            provider=self.__class__.__name__.lower(),
            error_type=PROVIDER_ERROR_TYPES["PROMPT_ERROR"],
            message=f"Unsupported prompt type: {type(prompt)}"
        )

    @abstractmethod
    def generate_text(
        self,
        prompt: Union[str, List[str]],
        model_parameters: LLMParametersBase,
        template: Optional[PromptTemplateBase] = None,
        provider_config: Optional[ProviderConfig] = None
    ) -> Union[str, List[str]]:
        """Generate text using the model.

        Args:
            prompt: Input text prompt or list of prompts
            model_parameters: Generation parameters from model config
            template: Optional prompt template
            provider_config: Optional provider-specific settings

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
        provider_config: Optional[ProviderConfig] = None
    ) -> Generator[str, None, None]:
        """Generate text in streaming mode.

        Args:
            prompt: Input text prompt
            model_parameters: Generation parameters from model config
            template: Optional prompt template
            provider_config: Optional provider-specific settings

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
