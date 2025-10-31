"""
Pipeline executor for orchestrating search stages.

This module provides the PipelineExecutor class that orchestrates
the execution of pipeline stages in sequence.
"""

from core.logging_utils import get_logger

from .base_stage import BaseStage, StageResult
from .search_context import SearchContext

logger = get_logger("services.pipeline.executor")


class PipelineExecutor:
    """
    Executes a sequence of pipeline stages.

    The executor orchestrates the flow of SearchContext through
    multiple stages, handling errors and collecting results.
    """

    def __init__(self, stages: list[BaseStage]) -> None:
        """
        Initialize the pipeline executor.

        Args:
            stages: Ordered list of pipeline stages to execute
        """
        self.stages = stages
        logger.info("Pipeline executor initialized with %d stages", len(stages))

    async def execute(self, context: SearchContext) -> SearchContext:
        """
        Execute all pipeline stages in sequence.

        Args:
            context: Initial search context

        Returns:
            Updated search context with results from all stages

        Raises:
            Exception: If a critical stage fails
        """
        logger.info("Starting pipeline execution with %d stages", len(self.stages))

        for i, stage in enumerate(self.stages, 1):
            logger.info("Executing stage %d/%d: %s", i, len(self.stages), stage.stage_name)

            try:
                result: StageResult = await stage.execute(context)

                if not result.success:
                    error_msg = f"Stage {stage.stage_name} failed: {result.error}"
                    logger.error(error_msg)
                    context.add_error(error_msg)
                    # Continue to next stage even if this one failed
                    continue

                # Update context with stage results
                context = result.context

                # Add stage metadata
                if result.metadata:
                    context.add_metadata(f"{stage.stage_name}_metadata", result.metadata)

                logger.info("Stage %s completed successfully", stage.stage_name)

            except Exception as e:  # pylint: disable=broad-exception-caught
                # Justification: Catch all exceptions to prevent pipeline failure
                error_msg = f"Critical error in stage {stage.stage_name}: {e!s}"
                logger.exception(error_msg)
                context.add_error(error_msg)
                # For critical errors, we might want to stop the pipeline
                # For now, we'll continue but this can be configurable
                continue

        # Update final execution time
        context.update_execution_time()
        logger.info("Pipeline execution completed in %.2f seconds", context.execution_time)

        return context

    def add_stage(self, stage: BaseStage) -> None:
        """
        Add a stage to the pipeline.

        Args:
            stage: Stage to add
        """
        self.stages.append(stage)
        logger.debug("Added stage %s to pipeline", stage.stage_name)

    def remove_stage(self, stage_name: str) -> None:
        """
        Remove a stage from the pipeline by name.

        Args:
            stage_name: Name of stage to remove
        """
        self.stages = [s for s in self.stages if s.stage_name != stage_name]
        logger.debug("Removed stage %s from pipeline", stage_name)

    def get_stage_names(self) -> list[str]:
        """
        Get names of all stages in the pipeline.

        Returns:
            List of stage names
        """
        return [stage.stage_name for stage in self.stages]
