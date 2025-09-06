
from pydantic import UUID4, SecretStr
from sqlalchemy.orm import Session

from core.config import Settings
from core.custom_exceptions import LLMProviderError
from core.logging_utils import get_logger
from rag_solution.schemas.llm_model_schema import LLMModelInput, ModelType
from rag_solution.schemas.llm_provider_schema import (
    LLMProviderInput,
    LLMProviderOutput,
)
from rag_solution.services.llm_model_service import LLMModelService
from rag_solution.services.llm_provider_service import LLMProviderService

logger = get_logger("services.system_initialization")


class SystemInitializationService:
    def __init__(self, db: Session, settings: Settings) -> None:
        """Initialize service with dependency injection.

        Args:
            db: Database session
            settings: Configuration settings
        """
        self.db = db
        self.settings = settings
        self.llm_provider_service = LLMProviderService(db)
        self.llm_model_service = LLMModelService(db)

    def initialize_providers(self, raise_on_error: bool = False) -> list[LLMProviderOutput]:
        try:
            existing_providers = {p.name: p for p in self.llm_provider_service.get_all_providers()}
            logger.info(f"Found existing providers: {list(existing_providers.keys())}")
        except Exception as e:
            logger.error(f"Error getting existing providers: {e!s}")
            if raise_on_error:
                raise LLMProviderError("unknown", "initialization", str(e)) from e
            return []

        default_configs = self._get_provider_configs()
        if not default_configs:
            logger.warning("No provider configurations available")
            return []

        initialized_providers: list[LLMProviderOutput] = []

        for name, config in default_configs.items():
            try:
                provider = self._initialize_single_provider(name, config, existing_providers.get(name), raise_on_error)
                if provider:
                    initialized_providers.append(provider)
            except Exception as e:
                logger.error(f"Error initializing provider {name}: {e!s}")
                if raise_on_error:
                    raise LLMProviderError(name, "initialization", str(e)) from e

        logger.info(f"Completed provider initialization. Count: {len(initialized_providers)}")
        return initialized_providers

    def _get_provider_configs(self) -> dict[str, LLMProviderInput]:
        configs: dict[str, LLMProviderInput] = {}

        if self.settings.wx_api_key and self.settings.wx_project_id:
            configs["watsonx"] = LLMProviderInput.model_validate(
                {
                    "name": "watsonx",
                    "base_url": self.settings.wx_url or "https://us-south.ml.cloud.ibm.com",
                    "api_key": SecretStr(self.settings.wx_api_key),
                    "project_id": self.settings.wx_project_id,
                    "is_default": True,
                }
            )
            logger.info("Added WatsonX configuration")

        if self.settings.openai_api_key:
            configs["openai"] = LLMProviderInput.model_validate({"name": "openai", "base_url": "https://api.openai.com", "api_key": SecretStr(self.settings.openai_api_key)})
            logger.info("Added OpenAI configuration")

        if self.settings.anthropic_api_key:
            configs["anthropic"] = LLMProviderInput.model_validate(
                {
                    "name": "anthropic",
                    "base_url": "https://api.anthropic.com",
                    "api_key": SecretStr(self.settings.anthropic_api_key),
                }
            )
            logger.info("Added Anthropic configuration")

        return configs

    def _initialize_single_provider(self, name: str, config: LLMProviderInput, existing_provider: LLMProviderOutput | None, raise_on_error: bool) -> LLMProviderOutput | None:
        try:
            if existing_provider:
                logger.info(f"Updating provider: {name}")
                provider = self.llm_provider_service.update_provider(existing_provider.id, config.model_dump(exclude_unset=True))
                if not provider:
                    raise LLMProviderError(name, "update", f"Failed to update {name}")
            else:
                logger.info(f"Creating provider: {name}")
                provider = self.llm_provider_service.create_provider(config)

            if name == "watsonx":
                self._setup_watsonx_models(provider.id, raise_on_error)

            return provider
        except Exception as e:
            logger.error(f"Provider initialization error: {e!s}")
            if raise_on_error:
                raise
            return None

    def _setup_watsonx_models(self, provider_id: UUID4, raise_on_error: bool) -> None:
        try:
            generation_model = LLMModelInput.model_validate(
                {
                    "provider_id": provider_id,
                    "model_id": self.settings.rag_llm,
                    "default_model_id": "ibm/granite-3-8b-instruct",
                    "model_type": ModelType.GENERATION,
                    "timeout": 30,
                    "max_retries": 3,
                    "batch_size": 10,
                    "retry_delay": 1.0,
                    "concurrency_limit": 10,
                    "stream": False,
                    "rate_limit": 10,
                    "is_default": True,
                    "is_active": True,
                }
            )

            embedding_model = LLMModelInput.model_validate(
                {
                    "provider_id": provider_id,
                    "model_id": self.settings.embedding_model,
                    "default_model_id": self.settings.embedding_model,
                    "model_type": ModelType.EMBEDDING,
                    "timeout": 30,
                    "max_retries": 3,
                    "batch_size": 10,
                    "retry_delay": 1.0,
                    "concurrency_limit": 10,
                    "stream": False,
                    "rate_limit": 10,
                    "is_default": True,
                    "is_active": True,
                }
            )

            self.llm_model_service.create_model(generation_model)
            logger.info("Created WatsonX generation model")

            self.llm_model_service.create_model(embedding_model)
            logger.info("Created WatsonX embedding model")

        except Exception as e:
            logger.error(f"Error creating WatsonX models: {e!s}")
            if raise_on_error:
                raise
