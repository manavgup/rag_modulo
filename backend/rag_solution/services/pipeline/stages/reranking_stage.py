"""
Reranking stage.

This stage reranks retrieved documents using cross-encoder for relevance optimization.
Wraps the CrossEncoderReranker functionality from PipelineService.
"""

import os

from core.logging_utils import get_logger
from rag_solution.services.pipeline.base_stage import BaseStage, StageResult
from rag_solution.services.pipeline.search_context import SearchContext

logger = get_logger("services.pipeline.stages.reranking")


class RerankingStage(BaseStage):  # pylint: disable=too-few-public-methods
    """
    Reranks retrieved documents using cross-encoder.

    This stage:
    1. Checks if reranking is enabled (config + env var)
    2. Applies cross-encoder to score relevance
    3. Reduces results to top-k documents
    4. Updates context with reranked results

    Note: Single public method (execute) is by design for pipeline stage pattern.
    """

    def __init__(self, pipeline_service: "PipelineService") -> None:  # type: ignore
        """
        Initialize the reranking stage.

        Args:
            pipeline_service: PipelineService instance for reranking operations
        """
        super().__init__("Reranking")
        self.pipeline_service = pipeline_service

    async def execute(self, context: SearchContext) -> StageResult:
        """
        Execute document reranking.

        Args:
            context: Current search context

        Returns:
            StageResult with reranked results in context

        Raises:
            ValueError: If required context attributes are missing
            AttributeError: If context attributes are not accessible
        """
        self._log_stage_start(context)

        try:
            # Check if reranking is enabled
            if not self._should_rerank(context):
                logger.info("Reranking disabled, skipping stage")
                result = StageResult(success=True, context=context)
                self._log_stage_complete(result)
                return result

            # Ensure we have query results
            if context.query_results is None:
                raise ValueError("Query results not set in context")

            # Ensure we have a rewritten query
            if not context.rewritten_query:
                raise ValueError("Rewritten query not set in context")

            original_count = len(context.query_results)

            # Get reranker instance
            reranker = self.pipeline_service.get_reranker(context.user_id)
            if not reranker:
                logger.warning("Reranker not available, skipping reranking")
                result = StageResult(success=True, context=context)
                self._log_stage_complete(result)
                return result

            # Get top_k for reranking
            top_k = self._get_reranking_top_k(context)

            # Rerank results
            reranked_results = await reranker.rerank_async(
                query=context.rewritten_query, results=context.query_results, top_k=top_k
            )

            logger.info("Reranked %d documents to top %d", original_count, len(reranked_results))

            # COMPREHENSIVE DEBUG LOGGING - Log reranked chunks
            if hasattr(self.pipeline_service, "_log_retrieved_chunks_to_file"):
                self.pipeline_service._log_retrieved_chunks_to_file(
                    context.rewritten_query, str(context.collection_id), reranked_results, "reranking"
                )

            # Update context
            context.query_results = reranked_results
            context.add_metadata(
                "reranking",
                {"original_count": original_count, "reranked_count": len(reranked_results), "method": "cross_encoder"},
            )

            result = StageResult(success=True, context=context)
            self._log_stage_complete(result)
            return result

        except (ValueError, AttributeError, TypeError, KeyError) as e:
            return await self._handle_error(context, e)

    def _should_rerank(self, context: SearchContext) -> bool:
        """
        Check if reranking should be performed.

        Args:
            context: Search context

        Returns:
            True if reranking is enabled, False otherwise
        """
        # Check environment variable
        enable_reranking_env = os.getenv("ENABLE_RERANKING", "true").lower() in ["true", "1", "yes"]
        if not enable_reranking_env:
            return False

        # Check config_metadata override
        if context.search_input.config_metadata:
            disable_rerank = context.search_input.config_metadata.get("disable_rerank", False)
            if disable_rerank:
                logger.debug("Reranking disabled via config_metadata")
                return False

        return True

    def _get_reranking_top_k(self, context: SearchContext) -> int | None:
        """
        Get top_k parameter for reranking.

        Args:
            context: Search context

        Returns:
            Top_k value or None (let reranker use default)
        """
        if context.search_input.config_metadata and "top_k_rerank" in context.search_input.config_metadata:
            top_k = context.search_input.config_metadata["top_k_rerank"]
            logger.debug("Using top_k_rerank=%s from config_metadata", top_k)
            return top_k

        # Use None to let reranker decide (default behavior)
        return None
