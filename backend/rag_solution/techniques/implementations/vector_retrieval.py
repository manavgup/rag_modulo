"""Vector retrieval technique implementation.

This technique performs vector-based document retrieval using the configured
vector store (Milvus, Elasticsearch, etc.).
"""

from __future__ import annotations

import logging
from typing import Any

from rag_solution.techniques.base import BaseTechnique, TechniqueContext, TechniqueResult, TechniqueStage
from rag_solution.techniques.registry import register_technique
from vectordbs.data_types import QueryResult, VectorQuery

logger = logging.getLogger(__name__)


@register_technique()
class VectorRetrievalTechnique(BaseTechnique[str, list[QueryResult]]):
    """Vector-based document retrieval technique.

    This technique retrieves documents from a vector store based on semantic
    similarity to the query. It uses the current query from the context
    (which may have been transformed by earlier techniques) and stores
    the retrieved documents in the context for later stages.

    Configuration:
        top_k: Number of documents to retrieve (default: 10)
        collection_name: Optional collection name override
        min_score: Optional minimum similarity score threshold
    """

    technique_id = "vector_retrieval"
    name = "Vector Retrieval"
    description = "Retrieve documents using vector similarity search"
    stage = TechniqueStage.RETRIEVAL

    requires_vector_store = True
    requires_embeddings = True
    estimated_latency_ms = 100
    token_cost_multiplier = 0.0  # No LLM calls, only embeddings

    async def execute(self, context: TechniqueContext) -> TechniqueResult[list[QueryResult]]:
        """Execute vector retrieval.

        Args:
            context: Pipeline context containing query and vector store

        Returns:
            TechniqueResult with retrieved documents
        """
        try:
            # Get configuration
            top_k = context.config.get("top_k", 10)
            collection_name = context.config.get("collection_name")
            min_score = context.config.get("min_score")

            # Validate dependencies
            if context.vector_store is None:
                return TechniqueResult(
                    success=False,
                    output=[],
                    metadata={},
                    technique_id=self.technique_id,
                    execution_time_ms=0,
                    error="Vector store not available in context",
                )

            # Determine collection name
            if collection_name is None:
                # Use collection_id from context to derive collection name
                collection_name = str(context.collection_id)

            # Create query object
            query = VectorQuery(text=context.current_query, number_of_results=top_k)

            # Execute retrieval
            logger.debug(
                f"Retrieving {top_k} documents for query: {context.current_query[:100]}",
                extra={"collection": collection_name},
            )

            results: list[QueryResult] = context.vector_store.retrieve_documents(
                context.current_query, collection_name, top_k
            )

            # Apply minimum score filter if configured
            if min_score is not None:
                original_count = len(results)
                results = [r for r in results if r.score >= min_score]
                filtered_count = original_count - len(results)
                if filtered_count > 0:
                    logger.info(f"Filtered {filtered_count} results below min_score {min_score}")

            # Update context with retrieved documents
            context.retrieved_documents = results

            logger.info(
                f"Retrieved {len(results)} documents",
                extra={
                    "top_k": top_k,
                    "min_score": min_score,
                    "collection": collection_name,
                },
            )

            return TechniqueResult(
                success=True,
                output=results,
                metadata={
                    "documents_retrieved": len(results),
                    "top_k": top_k,
                    "collection": collection_name,
                    "query_used": context.current_query,
                },
                technique_id=self.technique_id,
                execution_time_ms=0,  # Set by wrapper
            )

        except Exception as e:
            logger.error(f"Vector retrieval failed: {e}", exc_info=True)
            return TechniqueResult(
                success=False,
                output=[],
                metadata={},
                technique_id=self.technique_id,
                execution_time_ms=0,
                error=str(e),
            )

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration.

        Args:
            config: Configuration to validate

        Returns:
            True if configuration is valid
        """
        # Validate top_k
        top_k = config.get("top_k")
        if top_k is not None:
            if not isinstance(top_k, int) or top_k <= 0:
                logger.warning(f"Invalid top_k value: {top_k}, must be positive integer")
                return False

        # Validate min_score
        min_score = config.get("min_score")
        if min_score is not None:
            if not isinstance(min_score, (int, float)) or not (0 <= min_score <= 1):
                logger.warning(f"Invalid min_score value: {min_score}, must be between 0 and 1")
                return False

        return True

    def get_default_config(self) -> dict[str, Any]:
        """Get default configuration.

        Returns:
            Default configuration dictionary
        """
        return {"top_k": 10, "min_score": None, "collection_name": None}

    def get_config_schema(self) -> dict[str, Any]:
        """Get JSON schema for configuration.

        Returns:
            JSON schema dictionary
        """
        return {
            "type": "object",
            "properties": {
                "top_k": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Number of documents to retrieve",
                    "default": 10,
                },
                "min_score": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Minimum similarity score threshold",
                    "default": None,
                },
                "collection_name": {
                    "type": "string",
                    "description": "Collection name override (optional)",
                    "default": None,
                },
            },
            "additionalProperties": False,
        }
