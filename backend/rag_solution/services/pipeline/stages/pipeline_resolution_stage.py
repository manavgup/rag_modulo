"""
Pipeline resolution stage.

This stage resolves the user's default pipeline configuration and validates it.
Wraps the existing PipelineService for pipeline management.
"""

from pydantic import UUID4

from core.custom_exceptions import ConfigurationError, NotFoundError
from core.logging_utils import get_logger
from rag_solution.services.pipeline.base_stage import BaseStage, StageResult
from rag_solution.services.pipeline.search_context import SearchContext

logger = get_logger("services.pipeline.stages.pipeline_resolution")


class PipelineResolutionStage(BaseStage):
    """
    Resolves and validates pipeline configuration.

    This stage:
    1. Resolves the user's default pipeline
    2. Creates a new pipeline if none exists
    3. Validates the pipeline configuration
    4. Updates the context with pipeline_id
    """

    def __init__(self, pipeline_service: "PipelineService") -> None:  # type: ignore
        """
        Initialize the pipeline resolution stage.

        Args:
            pipeline_service: PipelineService instance for pipeline operations
        """
        super().__init__("PipelineResolution")
        self.pipeline_service = pipeline_service

    async def execute(self, context: SearchContext) -> StageResult:
        """
        Execute pipeline resolution.

        Args:
            context: Current search context

        Returns:
            StageResult with pipeline_id set in context
        """
        self._log_stage_start(context)

        try:
            # Resolve user's default pipeline
            pipeline_id = await self._resolve_user_default_pipeline(context.user_id)

            # Validate pipeline configuration
            self._validate_pipeline(pipeline_id)

            # Update context
            context.pipeline_id = pipeline_id
            context.add_metadata("pipeline_resolution", {"pipeline_id": str(pipeline_id), "success": True})

            result = StageResult(success=True, context=context)
            self._log_stage_complete(result)
            return result

        except Exception as e:
            return await self._handle_error(context, e)

    async def _resolve_user_default_pipeline(self, user_id: UUID4) -> UUID4:
        """
        Resolve user's default pipeline, creating one if none exists.

        Args:
            user_id: User UUID

        Returns:
            Pipeline ID

        Raises:
            ConfigurationError: If pipeline resolution fails
        """
        # Try to get user's existing default pipeline
        default_pipeline = self.pipeline_service.get_default_pipeline(user_id)

        if default_pipeline:
            logger.info("Found default pipeline %s for user %s", default_pipeline.id, user_id)
            return default_pipeline.id

        # No default pipeline exists, create one
        logger.info("Creating default pipeline for user %s", user_id)

        # Get user's LLM provider (or system default)
        try:
            default_provider = self.pipeline_service.llm_provider_service.get_user_provider(user_id)
            if not default_provider:
                raise ConfigurationError("No LLM provider available for pipeline creation")

            # Create default pipeline for user
            created_pipeline = self.pipeline_service.initialize_user_pipeline(user_id, default_provider.id)
            logger.info("Created pipeline %s for user %s", created_pipeline.id, user_id)
            return created_pipeline.id

        except Exception as e:
            logger.error("Failed to create pipeline for user %s: %s", user_id, e)
            raise ConfigurationError(f"Failed to create default pipeline for user {user_id}: {e}") from e

    def _validate_pipeline(self, pipeline_id: UUID4) -> None:
        """
        Validate pipeline configuration.

        Args:
            pipeline_id: Pipeline ID to validate

        Raises:
            NotFoundError: If pipeline not found
        """
        pipeline_config = self.pipeline_service.get_pipeline_config(pipeline_id)
        if not pipeline_config:
            raise NotFoundError(
                resource_type="Pipeline",
                resource_id=str(pipeline_id),
                message=f"Pipeline configuration not found for ID {pipeline_id}",
            )
        logger.debug("Pipeline %s validated successfully", pipeline_id)
