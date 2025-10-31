"""
Pipeline resolution stage.

This stage resolves the user's default pipeline configuration.
Wraps the existing PipelineService for pipeline management.
"""

from pydantic import UUID4

from core.custom_exceptions import ConfigurationError
from core.logging_utils import get_logger
from rag_solution.services.pipeline.base_stage import BaseStage, StageResult
from rag_solution.services.pipeline.search_context import SearchContext

logger = get_logger("services.pipeline.stages.pipeline_resolution")


class PipelineResolutionStage(BaseStage):  # pylint: disable=too-few-public-methods
    """
    Resolves pipeline configuration.

    This stage:
    1. Resolves the user's default pipeline
    2. Creates a new pipeline if none exists
    3. Updates the context with pipeline_id

    Note: Single public method (execute) is by design for pipeline stage pattern.
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

        Raises:
            ConfigurationError: If pipeline resolution or creation fails
        """
        self._log_stage_start(context)

        try:
            # Resolve user's default pipeline (creates if doesn't exist)
            pipeline_id = await self._resolve_user_default_pipeline(context.user_id)

            # Update context
            context.pipeline_id = pipeline_id
            context.add_metadata(
                "pipeline_resolution", {"pipeline_id": str(pipeline_id), "success": True}
            )

            result = StageResult(success=True, context=context)
            self._log_stage_complete(result)
            return result

        except ConfigurationError as e:
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
            llm_service = self.pipeline_service.llm_provider_service
            default_provider = llm_service.get_user_provider(user_id)
            if not default_provider:
                raise ConfigurationError(
                    "No LLM provider available for pipeline creation"
                )

            # Create default pipeline for user
            created_pipeline = self.pipeline_service.initialize_user_pipeline(
                user_id, default_provider.id
            )
            logger.info("Created pipeline %s for user %s", created_pipeline.id, user_id)
            return created_pipeline.id

        except (AttributeError, ValueError, TypeError) as e:
            # Catch specific exceptions that indicate configuration issues
            logger.error("Failed to create pipeline for user %s: %s", user_id, e)
            raise ConfigurationError(
                f"Failed to create default pipeline for user {user_id}: {e}"
            ) from e
