"""Adapter techniques that wrap existing retrieval infrastructure.

This module provides technique implementations that leverage the existing
retrieval components (VectorRetriever, HybridRetriever, LLMReranker) rather
than reimplementing them.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from rag_solution.retrieval.reranker import LLMReranker
from rag_solution.retrieval.retriever import HybridRetriever, VectorRetriever
from rag_solution.techniques.base import BaseTechnique, TechniqueContext, TechniqueResult, TechniqueStage
from rag_solution.techniques.registry import register_technique
from vectordbs.data_types import QueryResult, VectorQuery

logger = logging.getLogger(__name__)


@register_technique()
class VectorRetrievalTechnique(BaseTechnique[str, list[QueryResult]]):
    """Vector retrieval technique using existing VectorRetriever.

    This technique wraps the existing VectorRetriever implementation,
    leveraging the proven vector search infrastructure.
    """

    technique_id = "vector_retrieval"
    name = "Vector Retrieval"
    description = "Retrieve documents using vector similarity (wraps existing VectorRetriever)"
    stage = TechniqueStage.RETRIEVAL

    requires_vector_store = True
    requires_embeddings = True
    estimated_latency_ms = 100
    token_cost_multiplier = 0.0

    def __init__(self) -> None:
        """Initialize technique."""
        super().__init__()
        self._retriever: VectorRetriever | None = None

    async def execute(self, context: TechniqueContext) -> TechniqueResult[list[QueryResult]]:
        """Execute vector retrieval using existing VectorRetriever.

        Args:
            context: Pipeline context

        Returns:
            TechniqueResult with retrieved documents
        """
        try:
            # Get configuration
            top_k = context.config.get("top_k", 10)
            collection_name = context.config.get("collection_name", str(context.collection_id))

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

            # Get or create retriever (reuse existing implementation)
            if self._retriever is None:
                from rag_solution.data_ingestion.ingestion import DocumentStore

                document_store = DocumentStore(context.vector_store, collection_name)
                self._retriever = VectorRetriever(document_store)

            # Create query
            query = VectorQuery(text=context.current_query, number_of_results=top_k)

            # Execute using existing VectorRetriever
            logger.debug(
                f"Executing VectorRetriever for query: {context.current_query[:100]}",
                extra={"top_k": top_k, "collection": collection_name},
            )

            results = self._retriever.retrieve(collection_name, query)

            # Update context
            context.retrieved_documents = results

            logger.info(f"VectorRetriever returned {len(results)} documents")

            return TechniqueResult(
                success=True,
                output=results,
                metadata={
                    "documents_retrieved": len(results),
                    "top_k": top_k,
                    "collection": collection_name,
                    "retriever": "VectorRetriever",
                },
                technique_id=self.technique_id,
                execution_time_ms=0,
            )

        except Exception as e:
            logger.error(f"VectorRetriever execution failed: {e}", exc_info=True)
            return TechniqueResult(
                success=False,
                output=[],
                metadata={},
                technique_id=self.technique_id,
                execution_time_ms=0,
                error=str(e),
            )

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        top_k = config.get("top_k")
        return not (top_k is not None and (not isinstance(top_k, int) or top_k <= 0))

    def get_default_config(self) -> dict[str, Any]:
        """Get default configuration."""
        return {"top_k": 10, "collection_name": None}


@register_technique()
class HybridRetrievalTechnique(BaseTechnique[str, list[QueryResult]]):
    """Hybrid retrieval technique using existing HybridRetriever.

    This technique wraps the existing HybridRetriever which combines
    vector and keyword (TF-IDF) retrieval.
    """

    technique_id = "hybrid_retrieval"
    name = "Hybrid Retrieval (Vector + Keyword)"
    description = "Combine vector and keyword retrieval (wraps existing HybridRetriever)"
    stage = TechniqueStage.RETRIEVAL

    requires_vector_store = True
    requires_embeddings = True
    estimated_latency_ms = 150
    token_cost_multiplier = 0.0

    # Alternative names for discovery
    compatible_with: ClassVar[list[str]] = ["fusion_retrieval"]  # Alias

    def __init__(self) -> None:
        """Initialize technique."""
        super().__init__()
        self._retriever: HybridRetriever | None = None

    async def execute(self, context: TechniqueContext) -> TechniqueResult[list[QueryResult]]:
        """Execute hybrid retrieval using existing HybridRetriever.

        Args:
            context: Pipeline context

        Returns:
            TechniqueResult with retrieved documents
        """
        try:
            # Get configuration
            top_k = context.config.get("top_k", 10)
            vector_weight = context.config.get("vector_weight", 0.7)
            collection_name = context.config.get("collection_name", str(context.collection_id))

            # Validate dependencies
            if context.vector_store is None:
                return TechniqueResult(
                    success=False,
                    output=[],
                    metadata={},
                    technique_id=self.technique_id,
                    execution_time_ms=0,
                    error="Vector store not available",
                )

            # Get or create retriever
            if self._retriever is None or self._retriever.vector_weight != vector_weight:
                from rag_solution.data_ingestion.ingestion import DocumentStore

                document_store = DocumentStore(context.vector_store, collection_name)
                self._retriever = HybridRetriever(document_store, vector_weight=vector_weight)

            # Create query
            query = VectorQuery(text=context.current_query, number_of_results=top_k)

            # Execute using existing HybridRetriever
            logger.debug(
                f"Executing HybridRetriever (vector_weight={vector_weight})",
                extra={"top_k": top_k, "collection": collection_name},
            )

            results = self._retriever.retrieve(collection_name, query)

            # Update context
            context.retrieved_documents = results

            logger.info(
                f"HybridRetriever returned {len(results)} documents",
                extra={"vector_weight": vector_weight},
            )

            return TechniqueResult(
                success=True,
                output=results,
                metadata={
                    "documents_retrieved": len(results),
                    "top_k": top_k,
                    "vector_weight": vector_weight,
                    "collection": collection_name,
                    "retriever": "HybridRetriever",
                },
                technique_id=self.technique_id,
                execution_time_ms=0,
            )

        except Exception as e:
            logger.error(f"HybridRetriever execution failed: {e}", exc_info=True)
            return TechniqueResult(
                success=False,
                output=[],
                metadata={},
                technique_id=self.technique_id,
                execution_time_ms=0,
                error=str(e),
            )

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        top_k = config.get("top_k")
        if top_k is not None and (not isinstance(top_k, int) or top_k <= 0):
            return False

        vector_weight = config.get("vector_weight")
        return not (vector_weight is not None and (not isinstance(vector_weight, (int, float)) or not (0 <= vector_weight <= 1)))

    def get_default_config(self) -> dict[str, Any]:
        """Get default configuration."""
        return {"top_k": 10, "vector_weight": 0.7, "collection_name": None}


@register_technique()
class LLMRerankingTechnique(BaseTechnique[list[QueryResult], list[QueryResult]]):
    """LLM-based reranking technique using existing LLMReranker.

    This technique wraps the existing LLMReranker implementation,
    leveraging the proven LLM-based relevance scoring.
    """

    technique_id = "llm_reranking"
    name = "LLM-Based Reranking"
    description = "Rerank results using LLM relevance scoring (wraps existing LLMReranker)"
    stage = TechniqueStage.RERANKING

    requires_llm = True
    estimated_latency_ms = 500
    token_cost_multiplier = 2.0  # LLM calls for each document

    # Alternative names
    compatible_with: ClassVar[list[str]] = ["reranking"]

    def __init__(self) -> None:
        """Initialize technique."""
        super().__init__()
        self._reranker: LLMReranker | None = None

    async def execute(self, context: TechniqueContext) -> TechniqueResult[list[QueryResult]]:
        """Execute LLM reranking using existing LLMReranker.

        Args:
            context: Pipeline context

        Returns:
            TechniqueResult with reranked documents
        """
        try:
            # Get configuration
            top_k = context.config.get("top_k", 10)
            batch_size = context.config.get("batch_size", 10)
            score_scale = context.config.get("score_scale", 10)

            # Get documents from context
            documents = context.retrieved_documents
            if not documents:
                logger.warning("No documents to rerank")
                return TechniqueResult(
                    success=True,
                    output=[],
                    metadata={"documents_reranked": 0},
                    technique_id=self.technique_id,
                    execution_time_ms=0,
                )

            # Validate dependencies
            if context.llm_provider is None:
                logger.warning("LLM provider not available, skipping reranking")
                return TechniqueResult(
                    success=False,
                    output=documents,  # Return original documents
                    metadata={},
                    technique_id=self.technique_id,
                    execution_time_ms=0,
                    error="LLM provider not available",
                    fallback_used=True,
                )

            # Get or create reranker using existing LLMReranker
            if self._reranker is None:
                # Get reranking prompt template from context or use default
                from rag_solution.schemas.prompt_template_schema import PromptTemplateBase

                # Create a simple reranking template (or get from config)
                prompt_template = context.config.get("prompt_template")
                if prompt_template is None:
                    # Use a default template
                    prompt_template = PromptTemplateBase(
                        template_id="reranking_default",
                        name="Default Reranking",
                        template_text="Rate the relevance of this document to the query on a scale of 0-{scale}.\n\nQuery: {query}\n\nDocument: {document}\n\nRelevance score:",
                    )

                self._reranker = LLMReranker(
                    llm_provider=context.llm_provider,
                    user_id=context.user_id,
                    prompt_template=prompt_template,
                    batch_size=batch_size,
                    score_scale=score_scale,
                )

            # Execute using existing LLMReranker
            logger.debug(
                f"Executing LLMReranker on {len(documents)} documents",
                extra={"top_k": top_k, "batch_size": batch_size},
            )

            reranked = self._reranker.rerank(context.current_query, documents, top_k=top_k)

            # Update context
            context.retrieved_documents = reranked

            # Estimate token usage (rough estimate)
            avg_doc_length = (
                sum(len(d.chunk.text) for d in documents if d.chunk and d.chunk.text) // len(documents)
                if documents
                else 0
            )
            tokens_used = len(documents) * (avg_doc_length // 4 + 50)  # Rough token estimate

            logger.info(
                f"LLMReranker reranked to {len(reranked)} documents",
                extra={"original_count": len(documents), "top_k": top_k},
            )

            return TechniqueResult(
                success=True,
                output=reranked,
                metadata={
                    "documents_reranked": len(documents),
                    "documents_returned": len(reranked),
                    "top_k": top_k,
                    "reranker": "LLMReranker",
                },
                technique_id=self.technique_id,
                execution_time_ms=0,
                tokens_used=tokens_used,
                llm_calls=len(documents),
            )

        except Exception as e:
            logger.error(f"LLMReranker execution failed: {e}", exc_info=True)
            # Fallback: return original documents
            return TechniqueResult(
                success=False,
                output=context.retrieved_documents,
                metadata={},
                technique_id=self.technique_id,
                execution_time_ms=0,
                error=str(e),
                fallback_used=True,
            )

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        top_k = config.get("top_k")
        if top_k is not None and (not isinstance(top_k, int) or top_k <= 0):
            return False

        batch_size = config.get("batch_size")
        if batch_size is not None and (not isinstance(batch_size, int) or batch_size <= 0):
            return False

        score_scale = config.get("score_scale")
        return not (score_scale is not None and (not isinstance(score_scale, int) or score_scale <= 0))

    def get_default_config(self) -> dict[str, Any]:
        """Get default configuration."""
        return {"top_k": 10, "batch_size": 10, "score_scale": 10, "prompt_template": None}


# Register alias for common naming conventions
@register_technique()
class FusionRetrievalTechnique(HybridRetrievalTechnique):
    """Alias for HybridRetrievalTechnique.

    Many users expect 'fusion_retrieval' as the name for hybrid search.
    This is just an alias to the same implementation.
    """

    technique_id = "fusion_retrieval"
    name = "Fusion Retrieval"
    description = "Alias for hybrid_retrieval - combines vector and keyword search"


@register_technique()
class RerankingTechnique(LLMRerankingTechnique):
    """Alias for LLMRerankingTechnique.

    Shorter, more common name for LLM-based reranking.
    """

    technique_id = "reranking"
    name = "Reranking"
    description = "Alias for llm_reranking - LLM-based relevance scoring"
