"""
Retrieval stage.

This stage retrieves relevant documents from the vector database.
Wraps the document retrieval functionality from PipelineService.
"""

from core.logging_utils import get_logger
from rag_solution.services.pipeline.base_stage import BaseStage, StageResult
from rag_solution.services.pipeline.search_context import SearchContext

logger = get_logger("services.pipeline.stages.retrieval")


class RetrievalStage(BaseStage):
    """
    Retrieves relevant documents from vector database.

    This stage:
    1. Extracts top_k parameter from config
    2. Retrieves documents using the rewritten query
    3. Updates the context with query results
    """

    def __init__(self, pipeline_service: "PipelineService") -> None:  # type: ignore
        """
        Initialize the retrieval stage.

        Args:
            pipeline_service: PipelineService instance for retrieval operations
        """
        super().__init__("Retrieval")
        self.pipeline_service = pipeline_service

    async def execute(self, context: SearchContext) -> StageResult:
        """
        Execute document retrieval.

        Args:
            context: Current search context

        Returns:
            StageResult with query_results set in context

        Raises:
            ValueError: If required context attributes are missing
            AttributeError: If context attributes are not accessible
        """
        self._log_stage_start(context)

        try:
            # Ensure we have a collection name
            if not context.collection_name:
                raise ValueError("Collection name not set in context")

            # Ensure we have a rewritten query
            if not context.rewritten_query:
                raise ValueError("Rewritten query not set in context")

            # Extract top_k from config_metadata
            top_k = self._get_top_k(context)

            # Retrieve documents
            query_results = self._retrieve_documents(context.rewritten_query, context.collection_name, top_k)

            logger.info("Retrieved %d documents with top_k=%d", len(query_results), top_k)

            # Update context
            context.query_results = query_results
            context.add_metadata(
                "retrieval",
                {"top_k": top_k, "results_count": len(query_results), "collection": context.collection_name},
            )

            result = StageResult(success=True, context=context)
            self._log_stage_complete(result)
            return result

        except (ValueError, AttributeError, TypeError, KeyError) as e:
            return await self._handle_error(context, e)

    def _get_top_k(self, context: SearchContext) -> int:
        """
        Get top_k parameter from config or use default.

        Args:
            context: Search context

        Returns:
            Number of documents to retrieve
        """
        # Default from settings
        top_k = self.pipeline_service.settings.number_of_results

        # Override from config_metadata if provided
        if context.search_input.config_metadata and "top_k" in context.search_input.config_metadata:
            top_k = context.search_input.config_metadata["top_k"]
            logger.debug("Using top_k=%d from config_metadata", top_k)

        return top_k

    def _retrieve_documents(self, query: str, collection_name: str, top_k: int) -> list:
        """
        Retrieve documents from vector database.

        Args:
            query: Query to search for
            collection_name: Name of the collection
            top_k: Number of documents to retrieve

        Returns:
            List of query results
        """
        # Use PipelineService's _retrieve_documents method
        return self.pipeline_service._retrieve_documents(  # pylint: disable=protected-access
            query, collection_name, top_k
        )
