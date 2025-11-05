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

            # COMPREHENSIVE DEBUG LOGGING - Log query enhancement details
            self._log_query_enhancement(original_query, clean_query, rewritten_query)

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

    def _log_query_enhancement(self, original_query: str, clean_query: str, rewritten_query: str) -> None:
        """
        Log query enhancement details for debugging.

        Args:
            original_query: The original user query
            clean_query: The cleaned query
            rewritten_query: The rewritten query
        """
        try:
            import os
            from datetime import datetime

            debug_dir = "/tmp/rag_debug"
            os.makedirs(debug_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = f"{debug_dir}/query_enhancement_{timestamp}.txt"

            with open(debug_file, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write("QUERY ENHANCEMENT STAGE\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write("=" * 80 + "\n\n")

                f.write("ORIGINAL QUERY:\n")
                f.write("-" * 80 + "\n")
                f.write(f"{original_query}\n\n")

                f.write("CLEANED QUERY:\n")
                f.write("-" * 80 + "\n")
                f.write(f"{clean_query}\n\n")

                f.write("REWRITTEN QUERY (sent to Milvus):\n")
                f.write("-" * 80 + "\n")
                f.write(f"{rewritten_query}\n\n")

                f.write("SEMANTIC COMPARISON:\n")
                f.write("-" * 80 + "\n")
                f.write(f"Query changed: {original_query != rewritten_query}\n")
                f.write(f"Original length: {len(original_query)} chars\n")
                f.write(f"Rewritten length: {len(rewritten_query)} chars\n\n")

                f.write("=" * 80 + "\n")
                f.write("END OF QUERY ENHANCEMENT LOG\n")
                f.write("=" * 80 + "\n")

            logger.info("📝 Query enhancement logged to: %s", debug_file)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("Failed to log query enhancement: %s", e)
