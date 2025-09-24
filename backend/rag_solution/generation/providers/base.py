from abc import ABC, abstractmethod
from collections.abc import Generator, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from core.custom_exceptions import LLMProviderError
from core.logging_utils import get_logger, setup_logging
from pydantic import UUID4
from vectordbs.data_types import EmbeddingsList

from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.llm_provider_schema import LLMProviderConfig
from rag_solution.schemas.llm_usage_schema import LLMUsage, ServiceType, TokenUsageStats
from rag_solution.schemas.prompt_template_schema import PromptTemplateBase
from rag_solution.services.llm_model_service import LLMModelService
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.prompt_template_service import PromptTemplateService

setup_logging(Path("logs"))
logger = get_logger("llm.providers")


class LLMBase(ABC):
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

        # Token tracking storage
        self._usage_history: list[LLMUsage] = []

        # Initialize client during provider creation
        self.initialize_client()

    @classmethod
    def register(cls) -> None:
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
            ) from e

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
        return self.prompt_template_service.format_prompt_with_template(template, variables or {})

    def track_usage(
        self,
        usage: LLMUsage,
        user_id: UUID4 | None = None,
        session_id: str | None = None,
    ) -> None:
        """Track token usage for this provider instance."""
        # Update user_id and session_id if provided
        if user_id is not None:
            usage.user_id = str(user_id)
        if session_id is not None:
            usage.session_id = session_id

        self._usage_history.append(usage)
        self.logger.debug(f"Tracked usage: {usage.total_tokens} tokens for model {usage.model_name}")

    def get_recent_usage(self, limit: int = 10) -> list[LLMUsage]:
        """Get recent token usage records."""
        return self._usage_history[-limit:] if self._usage_history else []

    def get_total_usage(self) -> TokenUsageStats:
        """Get aggregated token usage statistics."""
        if not self._usage_history:
            return TokenUsageStats()

        total_prompt = sum(usage.prompt_tokens for usage in self._usage_history)
        total_completion = sum(usage.completion_tokens for usage in self._usage_history)
        total_tokens = sum(usage.total_tokens for usage in self._usage_history)
        total_calls = len(self._usage_history)
        avg_tokens = total_tokens / total_calls if total_calls > 0 else 0.0

        # Group by service type
        by_service: dict[ServiceType | str, int] = {}
        for usage in self._usage_history:
            service_key = usage.service_type
            by_service[service_key] = by_service.get(service_key, 0) + usage.total_tokens

        # Group by model
        by_model: dict[str, int] = {}
        for usage in self._usage_history:
            model_key = usage.model_name
            by_model[model_key] = by_model.get(model_key, 0) + usage.total_tokens

        return TokenUsageStats(
            total_prompt_tokens=total_prompt,
            total_completion_tokens=total_completion,
            total_tokens=total_tokens,
            total_calls=total_calls,
            average_tokens_per_call=avg_tokens,
            by_service=by_service,
            by_model=by_model,
        )

    @abstractmethod
    def generate_text(
        self,
        user_id: UUID4,
        prompt: str | Sequence[str],
        model_parameters: LLMParametersInput | None = None,
        template: PromptTemplateBase | None = None,
        variables: dict[str, Any] | None = None,
    ) -> str | list[str]:
        """Generate text using the model."""

    @abstractmethod
    def generate_text_stream(
        self,
        user_id: UUID4,
        prompt: str,
        model_parameters: LLMParametersInput | None = None,
        template: PromptTemplateBase | None = None,
        variables: dict[str, Any] | None = None,
    ) -> Generator[str, None, None]:
        """Generate text in streaming mode."""

    @abstractmethod
    def get_embeddings(self, texts: str | Sequence[str]) -> EmbeddingsList:
        """Generate embeddings for texts."""

    def generate_text_with_usage(
        self,
        user_id: UUID4,
        prompt: str | Sequence[str],
        service_type: ServiceType,
        model_parameters: LLMParametersInput | None = None,
        template: PromptTemplateBase | None = None,
        variables: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> tuple[str | list[str], LLMUsage]:
        """Generate text and return both result and usage information.

        Default implementation that wraps generate_text. Providers can override
        for more accurate token tracking when API returns usage data.
        """
        # Get actual result using the provider's implementation
        result = self.generate_text(user_id, prompt, model_parameters, template, variables)

        # Create a placeholder usage record since we don't have actual token counts
        # Providers should override this method to get real usage from their APIs
        model_id = self._model_id or "unknown"
        usage = LLMUsage(
            prompt_tokens=0,  # Placeholder - actual providers should provide real counts
            completion_tokens=0,  # Placeholder - actual providers should provide real counts
            total_tokens=0,  # Placeholder - actual providers should provide real counts
            model_name=model_id,
            service_type=service_type,
            timestamp=datetime.now(),
            user_id=str(user_id),
            session_id=session_id,
        )

        self.track_usage(usage)
        return result, usage

    def close(self) -> None:
        """Clean up provider resources."""
        self.client = None
