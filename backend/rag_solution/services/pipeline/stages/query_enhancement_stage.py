"""
Query enhancement stage.

This stage enhances the user's query by rewriting it for better retrieval.
Wraps the query rewriting functionality from PipelineService.
"""

from core.logging_utils import get_logger
from rag_solution.services.pipeline.base_stage import BaseStage, StageResult
from rag_solution.services.pipeline.search_context import SearchContext

logger = get_logger("services.pipeline.stages.query_enhancement")


class QueryEnhancementStage(BaseStage):  # pylint: disable=too-few-public-methods
    """
    Enhances user queries for better retrieval.

    This stage:
    1. Cleans and prepares the raw query
    2. Rewrites the query for improved retrieval
    3. Updates the context with the rewritten query

    Note: Single public method (execute) is by design for pipeline stage pattern.
    """

    def __init__(self, pipeline_service: "PipelineService") -> None:  # type: ignore
        """
        Initialize the query enhancement stage.

        Args:
            pipeline_service: PipelineService instance for query operations
        """
        super().__init__("QueryEnhancement")
        self.pipeline_service = pipeline_service

    async def execute(self, context: SearchContext) -> StageResult:
        """
        Execute query enhancement.

        Args:
            context: Current search context

        Returns:
            StageResult with rewritten_query set in context

        Raises:
            ValueError: If query preparation or rewriting fails
            AttributeError: If required context attributes are missing
        """
        self._log_stage_start(context)

        try:
            # Get original query
            original_query = context.search_input.question

            # Prepare query (clean it)
            clean_query = self._prepare_query(original_query)
            logger.debug("Cleaned query: %s", clean_query)

            # Rewrite query for better retrieval
            rewritten_query = self._rewrite_query(clean_query)
            logger.info("Query rewritten: '%s' -> '%s'", clean_query, rewritten_query)

            # Update context
            context.rewritten_query = rewritten_query
            context.add_metadata(
                "query_enhancement",
                {
                    "original_query": original_query,
                    "clean_query": clean_query,
                    "rewritten_query": rewritten_query,
                },
            )

            result = StageResult(success=True, context=context)
            self._log_stage_complete(result)
            return result

        except (ValueError, AttributeError, TypeError) as e:
            return await self._handle_error(context, e)

    def _prepare_query(self, query: str) -> str:
        """
        Prepare and clean the query.

        Args:
            query: Raw user query

        Returns:
            Cleaned query
        """
        # Use PipelineService's _prepare_query method
        return self.pipeline_service._prepare_query(query)  # pylint: disable=protected-access

    def _rewrite_query(self, query: str) -> str:
        """
        Rewrite query for better retrieval.

        Args:
            query: Cleaned query

        Returns:
            Rewritten query
        """
        # Use PipelineService's query_rewriter
        return self.pipeline_service.query_rewriter.rewrite(query)
