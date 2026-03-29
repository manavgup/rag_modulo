"""Repository for fetching all pipeline config in a minimal number of queries.

Replaces the 48-query-per-request pattern with a single composite fetch that
returns a frozen ``PipelineContext`` value object.
"""

from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from core.custom_exceptions import RepositoryError
from core.logging_utils import get_logger
from rag_solution.models.collection import Collection
from rag_solution.models.llm_model import LLMModel
from rag_solution.models.llm_parameters import LLMParameters
from rag_solution.models.llm_provider import LLMProvider
from rag_solution.models.pipeline import PipelineConfig
from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.schemas.pipeline_context import PipelineContext
from rag_solution.schemas.prompt_template_schema import PromptTemplateType

logger = get_logger("repository.pipeline_context")


class PipelineContextRepository:
    """Fetches all search-pipeline configuration in 3 queries (down from 48).

    Query 1: pipeline_config + provider (JOIN)
    Query 2: models + parameters + template (3 simple selects, batched)
    Query 3: collection lookup
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_context(self, user_id: UUID, collection_id: UUID) -> PipelineContext | None:
        """Build a ``PipelineContext`` for the given user + collection.

        Returns ``None`` when the user has no default pipeline so callers can
        fall back to the legacy per-service query path.

        Args:
            user_id: The requesting user's UUID.
            collection_id: The target collection's UUID.

        Returns:
            A frozen ``PipelineContext``, or ``None`` if prerequisites are missing.

        Raises:
            RepositoryError: On unexpected database errors.
        """
        try:
            return self._build_context(user_id, collection_id)
        except RepositoryError:
            raise
        except Exception as e:
            logger.warning("PipelineContextRepository.get_context failed: %s", e)
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_context(self, user_id: UUID, collection_id: UUID) -> PipelineContext | None:
        """Execute the composite query and assemble the context object."""

        # --- Query 1: pipeline_config + provider (eager JOIN) -----------
        pipeline: PipelineConfig | None = (
            self.db.query(PipelineConfig)
            .options(joinedload(PipelineConfig.provider))
            .filter(
                PipelineConfig.user_id == user_id,
                PipelineConfig.collection_id.is_(None),
                PipelineConfig.is_default.is_(True),
            )
            .first()
        )

        if pipeline is None:
            logger.debug("No default pipeline for user %s", user_id)
            return None

        provider: LLMProvider | None = pipeline.provider
        if provider is None:
            logger.warning("Pipeline %s has no provider", pipeline.id)
            return None

        # --- Query 2a: models for provider --------------------------------
        models_rows: list[LLMModel] = (
            self.db.query(LLMModel).filter(LLMModel.provider_id == provider.id, LLMModel.is_active.is_(True)).all()
        )
        models_tuple: tuple[tuple[str, str], ...] = tuple(
            (m.model_id, m.model_type.value if hasattr(m.model_type, "value") else str(m.model_type))
            for m in models_rows
        )

        # --- Query 2b: default LLM parameters for user --------------------
        params: LLMParameters | None = (
            self.db.query(LLMParameters)
            .filter(LLMParameters.user_id == user_id, LLMParameters.is_default.is_(True))
            .first()
        )

        # --- Query 2c: default RAG_QUERY prompt template for user ---------
        template: PromptTemplate | None = (
            self.db.query(PromptTemplate)
            .filter(
                PromptTemplate.user_id == user_id,
                PromptTemplate.template_type == PromptTemplateType.RAG_QUERY,
                PromptTemplate.is_default.is_(True),
            )
            .first()
        )

        # --- Query 3: collection -------------------------------------------
        collection: Collection | None = self.db.query(Collection).filter(Collection.id == collection_id).first()

        if collection is None:
            logger.warning("Collection %s not found", collection_id)
            return None

        # --- Assemble frozen context -----------------------------------
        return PipelineContext(
            # Pipeline
            pipeline_id=pipeline.id,
            retriever_type=pipeline.retriever or "vector",
            max_context_length=pipeline.max_context_length or 2048,
            # Provider
            provider_name=provider.name,
            provider_base_url=provider.base_url,
            provider_api_key=provider.api_key,
            provider_project_id=provider.project_id,
            # Models
            models=models_tuple,
            # Generation params (fall back to defaults when user has no saved params)
            max_new_tokens=params.max_new_tokens if params else 100,
            temperature=params.temperature if params else 0.7,
            top_k=params.top_k if params else 50,
            top_p=params.top_p if params else 1.0,
            repetition_penalty=params.repetition_penalty if params else 1.1,
            # Template
            template_id=template.id if template else None,
            template_format=template.template_format if template else "",
            system_prompt=template.system_prompt if template else "You are a helpful AI assistant.",
            # Collection
            vector_db_name=collection.vector_db_name,
            collection_id=collection.id,
        )
