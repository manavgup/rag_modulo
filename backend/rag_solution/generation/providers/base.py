from abc import ABC, ABCMeta, abstractmethod
from collections.abc import Generator, Sequence
from pathlib import Path
from typing import Any
from uuid import UUID

from core.custom_exceptions import LLMProviderError
from core.logging_utils import get_logger, setup_logging
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.llm_provider_schema import LLMProviderConfig
from rag_solution.schemas.prompt_template_schema import PromptTemplateBase
from rag_solution.services.llm_model_service import LLMModelService
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.prompt_template_service import PromptTemplateService
from vectordbs.data_types import EmbeddingsList

setup_logging(Path("logs"))
logger = get_logger("llm.providers")


class LLMMeta(ABCMeta):
    """
    Metaclass for automatically registering provider classes with the factory.
    """

    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        # Automatically register the provider class if it's not the base class
        if name != "LLMBase" and not cls.__module__.startswith("abc"):
            logger.debug(f"Registering provider class: {name}")
            cls.register()


class LLMBase(ABC, metaclass=LLMMeta):
    """
    Base class for language model integrations.

    Subclasses must implement methods for text generation, streaming, and embedding generation.
    """

    def __init__(
        self,
        llm_provider_service: LLMProviderService,
        llm_parameters_service: LLMParametersService,
        prompt_template_service: PromptTemplateService,
        llm_model_service: LLMModelService,
    ) -> None:
        """Initialize provider with required services."""
        self.logger: Any = get_logger(f"llm.providers.{self.__class__.__name__}")
        self.logger.info(f"Initializing {self.__class__.__name__}")

        self.llm_provider_service: LLMProviderService = llm_provider_service
        self.llm_parameters_service: LLMParametersService = llm_parameters_service
        self.prompt_template_service: PromptTemplateService = prompt_template_service
        self.llm_model_service: LLMModelService = llm_model_service

        self._model_id: str | None = None
        self._provider_name: str = self.__class__.__name__.lower()
        self.client: Any | None = None

        # Initialize client during provider creation
        self.initialize_client()

    @classmethod
    def register(cls):
        """
        Automatically register the provider with the factory using the module name.
        """
        # Import the factory here to avoid circular imports
        from rag_solution.generation.providers.factory import LLMProviderFactory

        provider_name = cls.__module__.split(".")[-1].lower()  # Extract the module name
        logger.debug(f"Attempting to register provider: {provider_name}")
        LLMProviderFactory.register_provider(provider_name, cls)
        logger.info(f"Registered provider: {provider_name}")

    def _get_provider_config(self, provider_name: str) -> LLMProviderConfig:
        """Get provider configuration from service."""
        provider = self.llm_provider_service.get_provider_by_name(provider_name)
        if not provider or not provider.is_active:
            raise LLMProviderError(
                provider=provider_name,
                error_type="provider_not_found",
                message=f"Active {provider_name} provider not found",
            )
        return provider

    @property
    def model_id(self) -> str | None:
        """Get current model ID."""
        return self._model_id

    @model_id.setter
    def model_id(self, value: str) -> None:
        """Set model ID and reinitialize if needed."""
        if value != self._model_id:
            self._model_id = value
            self.initialize_client()

    @abstractmethod
    def initialize_client(self) -> None:
        """Initialize or reinitialize the provider client."""

    def _ensure_client(self) -> None:
        """Ensure client is initialized and valid."""
        try:
            if self.client is None:
                self.logger.warning("Client not initialized, attempting to initialize")
                self.initialize_client()
            self.validate_client()
        except Exception as e:
            raise LLMProviderError(
                provider=self._provider_name, error_type="client_error", message=f"Client error: {e!s}"
            )

    def validate_client(self) -> None:
        """Validate OpenAI client state."""
        if self.client is None:
            raise ValueError("OpenAI client is not initialized")

    def _format_prompt(
        self, prompt: str, template: PromptTemplateBase | None = None, variables: dict[str, Any] | None = None
    ) -> str:
        """Format prompt using template service."""
        if not template:
            return prompt
        return self.prompt_template_service.format_prompt(template_or_id=template, variables=variables or {})

    @abstractmethod
    def generate_text(
        self,
        user_id: UUID,
        prompt: str | Sequence[str],
        model_parameters: LLMParametersInput | None = None,
        template: PromptTemplateBase | None = None,
        variables: dict[str, Any] | None = None,
    ) -> str | list[str]:
        """Generate text using the model."""

    @abstractmethod
    def generate_text_stream(
        self,
        user_id: UUID,
        prompt: str,
        model_parameters: LLMParametersInput | None = None,
        template: PromptTemplateBase | None = None,
        variables: dict[str, Any] | None = None,
    ) -> Generator[str, None, None]:
        """Generate text in streaming mode."""

    @abstractmethod
    def get_embeddings(self, texts: str | Sequence[str]) -> EmbeddingsList:
        """Generate embeddings for texts."""

    def close(self) -> None:
        """Clean up provider resources."""
        self.client = None
