"""
Retrieval stage.

This stage retrieves relevant documents from the vector database.
Wraps the document retrieval functionality from PipelineService.
"""

from core.logging_utils import get_logger
from rag_solution.services.pipeline.base_stage import BaseStage, StageResult
from rag_solution.services.pipeline.search_context import SearchContext

logger = get_logger("services.pipeline.stages.retrieval")


class RetrievalStage(BaseStage):  # pylint: disable=too-few-public-methods
    """
    Retrieves relevant documents from vector database.

    This stage:
    1. Extracts top_k parameter from config
    2. Retrieves documents using the rewritten query
    3. Updates the context with query results

    Note: Single public method (execute) is by design for pipeline stage pattern.
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
            # Ensure we have a collection_id
            if not context.collection_id:
                raise ValueError("Collection ID not set in context")

            # Ensure we have a rewritten query
            if not context.rewritten_query:
                raise ValueError("Rewritten query not set in context")

            # Extract top_k from config_metadata
            top_k = self._get_top_k(context)

            # COMPREHENSIVE DEBUG LOGGING - Log retrieval parameters BEFORE retrieval
            self._log_retrieval_params(context.rewritten_query, str(context.collection_id), top_k)

            # Retrieve documents using collection_id (PipelineService handles the lookup)
            query_results = self.pipeline_service.retrieve_documents_by_id(
                query=context.rewritten_query, collection_id=context.collection_id, top_k=top_k
            )

            logger.info("Retrieved %d documents with top_k=%d", len(query_results), top_k)

            # Generate document metadata for UI display (sources)
            document_metadata = self.pipeline_service.generate_document_metadata(query_results, context.collection_id)
            logger.debug("Generated metadata for %d documents", len(document_metadata))

            # Update context
            context.query_results = query_results
            context.document_metadata = document_metadata
            context.add_metadata(
                "retrieval",
                {
                    "top_k": top_k,
                    "results_count": len(query_results),
                    "documents_count": len(document_metadata),
                    "collection_id": str(context.collection_id),
                },
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

    def _log_retrieval_params(self, query: str, collection_id: str, top_k: int) -> None:
        """
        Log retrieval parameters for debugging.

        Args:
            query: The query being searched
            collection_id: Collection UUID
            top_k: Number of results to retrieve
        """
        try:
            import os
            from datetime import datetime

            debug_dir = "/tmp/rag_debug"
            os.makedirs(debug_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = f"{debug_dir}/retrieval_params_{timestamp}.txt"

            # Get settings from pipeline_service
            settings = self.pipeline_service.settings

            with open(debug_file, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write("RETRIEVAL STAGE - PARAMETERS\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write("=" * 80 + "\n\n")

                f.write("QUERY:\n")
                f.write("-" * 80 + "\n")
                f.write(f"{query}\n\n")

                f.write("COLLECTION:\n")
                f.write("-" * 80 + "\n")
                f.write(f"Collection ID: {collection_id}\n")
                f.write(f"Top K: {top_k}\n\n")

                f.write("EMBEDDING CONFIGURATION:\n")
                f.write("-" * 80 + "\n")
                f.write(f"Embedding Model: {getattr(settings, 'embedding_model', 'N/A')}\n")
                f.write(f"Embedding Dimension: {getattr(settings, 'embedding_dim', 'N/A')}\n")
                f.write(f"Embedding Field: {getattr(settings, 'embedding_field', 'N/A')}\n\n")

                f.write("MILVUS CONFIGURATION:\n")
                f.write("-" * 80 + "\n")
                f.write(f"Milvus Host: {getattr(settings, 'milvus_host', 'N/A')}\n")
                f.write(f"Milvus Port: {getattr(settings, 'milvus_port', 'N/A')}\n\n")

                # Log search parameters from MilvusStore
                if hasattr(self.pipeline_service, 'retriever'):
                    retriever = self.pipeline_service.retriever
                    if hasattr(retriever, 'search_params'):
                        f.write("MILVUS SEARCH PARAMETERS:\n")
                        f.write("-" * 80 + "\n")
                        f.write(f"Metric Type: {retriever.search_params.get('metric_type', 'N/A')}\n")
                        f.write(f"Search Params: {retriever.search_params.get('params', 'N/A')}\n\n")

                f.write("=" * 80 + "\n")
                f.write("END OF RETRIEVAL PARAMETERS LOG\n")
                f.write("=" * 80 + "\n")

            logger.info("📝 Retrieval parameters logged to: %s", debug_file)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("Failed to log retrieval parameters: %s", e)
