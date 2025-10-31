"""
Base stage interface for search pipeline.

This module defines the abstract base class for all pipeline stages,
providing a consistent interface for stage execution and error handling.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from core.logging_utils import get_logger

logger = get_logger("services.pipeline.base_stage")


@dataclass
class StageResult:
    """
    Result of a pipeline stage execution.

    Attributes:
        success: Whether the stage completed successfully
        context: Updated search context with stage results
        error: Error message if stage failed
        metadata: Additional metadata about stage execution
    """

    # pylint: disable=too-few-public-methods
    # Justification: Dataclass is a simple data container, no methods needed

    success: bool
    context: Any  # Type will be SearchContext, avoiding circular import
    error: str | None = None
    metadata: dict[str, Any] | None = None


class BaseStage(ABC):
    """
    Abstract base class for all pipeline stages.

    Each stage represents a discrete step in the search pipeline:
    - Pipeline resolution
    - Query enhancement
    - Retrieval
    - Reranking
    - Reasoning (Chain of Thought)
    - Generation

    Stages receive a SearchContext, execute their logic, and return
    an updated context with their results.
    """

    def __init__(self, stage_name: str) -> None:
        """
        Initialize the base stage.

        Args:
            stage_name: Human-readable name for this stage
        """
        self.stage_name = stage_name
        self.logger = get_logger(f"services.pipeline.{stage_name}")

    @abstractmethod
    async def execute(self, context: Any) -> StageResult:  # Context is SearchContext
        """
        Execute this pipeline stage.

        Args:
            context: Current search context with accumulated results

        Returns:
            StageResult with success status and updated context

        Raises:
            Exception: If stage encounters a critical error
        """

    async def _handle_error(self, context: Any, error: Exception) -> StageResult:
        """
        Handle errors during stage execution.

        Args:
            context: Current search context
            error: Exception that occurred

        Returns:
            StageResult with error information
        """
        error_msg = f"{self.stage_name} failed: {error!s}"
        self.logger.error(error_msg, exc_info=True)
        return StageResult(success=False, context=context, error=error_msg)

    def _log_stage_start(self, context: Any) -> None:
        """
        Log the start of stage execution.

        Args:
            context: Current search context
        """
        self.logger.info("Starting %s stage", self.stage_name)
        self.logger.debug("%s stage context: %s", self.stage_name, context)

    def _log_stage_complete(self, result: StageResult) -> None:
        """
        Log stage completion.

        Args:
            result: Stage execution result
        """
        if result.success:
            self.logger.info("%s stage completed successfully", self.stage_name)
        else:
            self.logger.error("%s stage failed: %s", self.stage_name, result.error)
