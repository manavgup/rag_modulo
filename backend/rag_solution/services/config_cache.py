"""Request-scoped configuration cache.

Caches read-mostly config data (providers, models, templates, parameters)
within a single request. No cross-request state.
"""

from typing import Any

from pydantic import UUID4
from sqlalchemy.orm import Session

from core.logging_utils import get_logger

logger = get_logger(__name__)


class ConfigCache:
    """Per-request cache for read-mostly configuration."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._cache: dict[str, Any] = {}

    def _get_or_set(self, key: str, loader: Any) -> Any:
        if key not in self._cache:
            self._cache[key] = loader()
            logger.debug("ConfigCache MISS: %s", key)
        else:
            logger.debug("ConfigCache HIT: %s", key)
        return self._cache[key]

    def get_default_provider(self) -> Any:
        from rag_solution.services.llm_provider_service import LLMProviderService

        return self._get_or_set("default_provider", lambda: LLMProviderService(self._db).get_default_provider())

    def get_user_provider(self, user_id: UUID4) -> Any:
        from rag_solution.services.llm_provider_service import LLMProviderService

        return self._get_or_set(f"provider:{user_id}", lambda: LLMProviderService(self._db).get_user_provider(user_id))

    def get_pipeline_config(self, user_id: UUID4) -> Any:
        from rag_solution.repository.pipeline_repository import PipelineConfigRepository

        return self._get_or_set(
            f"pipeline:{user_id}", lambda: PipelineConfigRepository(self._db).get_user_default(user_id)
        )

    def get_rag_template(self, user_id: UUID4) -> Any:
        from rag_solution.services.prompt_template_service import PromptTemplateService

        return self._get_or_set(
            f"template:rag:{user_id}", lambda: PromptTemplateService(self._db).get_rag_template(user_id)
        )

    def get_llm_parameters(self, user_id: UUID4) -> Any:
        from core.config import get_settings
        from rag_solution.services.llm_parameters_service import LLMParametersService

        return self._get_or_set(
            f"params:{user_id}", lambda: LLMParametersService(self._db, get_settings()).get_user_parameters(user_id)
        )

    def get_models_by_provider(self, provider_id: UUID4) -> Any:
        from rag_solution.services.llm_model_service import LLMModelService

        return self._get_or_set(
            f"models:{provider_id}", lambda: LLMModelService(self._db).get_models_by_provider(provider_id)
        )

    def invalidate(self, key: str | None = None) -> None:
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()
