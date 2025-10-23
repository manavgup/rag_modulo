"""Pipeline builder and executor for composing RAG techniques.

This module provides:
- TechniquePipelineBuilder: Fluent API for constructing technique pipelines
- TechniquePipeline: Executor for running technique pipelines
- TECHNIQUE_PRESETS: Pre-configured technique combinations
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from rag_solution.techniques.base import BaseTechnique, TechniqueConfig, TechniqueContext, TechniqueStage

if TYPE_CHECKING:
    from rag_solution.techniques.registry import TechniqueRegistry

logger = logging.getLogger(__name__)


class TechniquePipeline:
    """Executable pipeline of RAG techniques.

    The pipeline executes techniques in sequence, passing a shared context
    between them. Each technique can:
    - Transform the query
    - Retrieve documents
    - Filter/rerank results
    - Compress context
    - Generate answers

    The pipeline is resilient: if a technique fails, execution continues
    unless the technique is marked as critical.

    Usage:
        pipeline = TechniquePipeline(techniques)
        context = TechniqueContext(...)
        result_context = await pipeline.execute(context)
    """

    def __init__(self, techniques: list[tuple[BaseTechnique, dict[str, Any]]]) -> None:
        """Initialize the pipeline.

        Args:
            techniques: List of (technique, config) tuples to execute in order
        """
        self.techniques = techniques
        self.metrics: dict[str, Any] = {}

    async def execute(self, context: TechniqueContext) -> TechniqueContext:
        """Execute all techniques in sequence.

        Args:
            context: Shared context passed through the pipeline

        Returns:
            Updated context after all techniques have executed

        Note:
            The pipeline continues execution even if individual techniques fail,
            unless a technique is marked as critical. Failed techniques are logged
            and their errors are recorded in the metrics.
        """
        pipeline_start = time.time()

        logger.info(f"Starting technique pipeline with {len(self.techniques)} techniques")

        for technique, config in self.techniques:
            try:
                # Update context with technique-specific config
                technique_config = {**context.config, **config}

                # Log execution
                context.execution_trace.append(f"Executing: {technique.technique_id}")
                logger.debug(f"Executing technique: {technique.technique_id}", extra={"config": technique_config})

                # Create temporary context with merged config
                temp_context = TechniqueContext(
                    user_id=context.user_id,
                    collection_id=context.collection_id,
                    original_query=context.original_query,
                    current_query=context.current_query,
                    llm_provider=context.llm_provider,
                    vector_store=context.vector_store,
                    db_session=context.db_session,
                    retrieved_documents=context.retrieved_documents,
                    intermediate_results=context.intermediate_results,
                    metrics=context.metrics,
                    execution_trace=context.execution_trace,
                    config=technique_config,
                )

                # Execute technique with timing
                result = await technique.execute_with_timing(temp_context)

                # Update main context with changes from temp context
                context.current_query = temp_context.current_query
                context.retrieved_documents = temp_context.retrieved_documents
                context.intermediate_results = temp_context.intermediate_results

                # Track metrics
                self.metrics[technique.technique_id] = {
                    "execution_time_ms": result.execution_time_ms,
                    "tokens_used": result.tokens_used,
                    "llm_calls": result.llm_calls,
                    "success": result.success,
                    "fallback_used": result.fallback_used,
                }

                # Store result in context
                if result.success:
                    context.intermediate_results[technique.technique_id] = result.output
                    logger.info(
                        f"Technique {technique.technique_id} completed successfully",
                        extra={
                            "execution_time_ms": result.execution_time_ms,
                            "tokens_used": result.tokens_used,
                        },
                    )
                else:
                    logger.warning(
                        f"Technique {technique.technique_id} failed: {result.error}",
                        extra={"fallback_used": result.fallback_used},
                    )
                    # Continue pipeline execution (techniques should be resilient)

            except Exception as e:
                logger.error(f"Error executing technique {technique.technique_id}: {e}", exc_info=True)
                # Record error but continue pipeline
                self.metrics[technique.technique_id] = {
                    "execution_time_ms": 0,
                    "success": False,
                    "error": str(e),
                }
                context.execution_trace.append(f"Error in {technique.technique_id}: {e}")

        # Calculate total pipeline time
        pipeline_time = (time.time() - pipeline_start) * 1000

        # Add pipeline-level metrics to context
        context.metrics["pipeline_metrics"] = {
            **self.metrics,
            "total_execution_time_ms": pipeline_time,
            "techniques_executed": len(self.techniques),
            "techniques_succeeded": sum(1 for m in self.metrics.values() if m.get("success", False)),
            "techniques_failed": sum(1 for m in self.metrics.values() if not m.get("success", True)),
        }

        logger.info(
            f"Pipeline execution completed in {pipeline_time:.2f}ms",
            extra={
                "techniques_executed": len(self.techniques),
                "techniques_succeeded": context.metrics["pipeline_metrics"]["techniques_succeeded"],
                "techniques_failed": context.metrics["pipeline_metrics"]["techniques_failed"],
            },
        )

        return context

    def get_estimated_cost(self) -> dict[str, Any]:
        """Estimate pipeline execution cost.

        Returns:
            Dictionary with estimated latency and token costs
        """
        total_latency = sum(t.estimated_latency_ms for t, _ in self.techniques)

        total_token_multiplier = sum(t.token_cost_multiplier for t, _ in self.techniques)

        llm_techniques = sum(1 for t, _ in self.techniques if t.requires_llm)

        return {
            "estimated_latency_ms": total_latency,
            "token_cost_multiplier": total_token_multiplier,
            "technique_count": len(self.techniques),
            "llm_techniques": llm_techniques,
        }

    def get_technique_ids(self) -> list[str]:
        """Get list of technique IDs in this pipeline.

        Returns:
            List of technique IDs in execution order
        """
        return [t.technique_id for t, _ in self.techniques]


class TechniquePipelineBuilder:
    """Builder for constructing technique pipelines.

    Provides a fluent API for building technique pipelines:

    Usage:
        builder = TechniquePipelineBuilder(registry)
        pipeline = (
            builder
            .add_hyde()
            .add_fusion_retrieval(vector_weight=0.8)
            .add_reranking(top_k=10)
            .build()
        )
    """

    def __init__(self, registry: TechniqueRegistry) -> None:
        """Initialize the builder.

        Args:
            registry: Technique registry for resolving technique IDs
        """
        self.registry = registry
        self.techniques: list[tuple[str, dict[str, Any]]] = []

    def add_technique(
        self, technique_id: str, config: dict[str, Any] | None = None
    ) -> TechniquePipelineBuilder:
        """Add a technique to the pipeline.

        Args:
            technique_id: Unique identifier of the technique
            config: Optional configuration for the technique

        Returns:
            Self for method chaining
        """
        self.techniques.append((technique_id, config or {}))
        return self

    # Convenience methods for common techniques

    def add_query_transformation(self, method: str = "rewrite") -> TechniquePipelineBuilder:
        """Add query transformation technique.

        Args:
            method: Transformation method ("rewrite", "stepback", "decomposition")

        Returns:
            Self for method chaining
        """
        return self.add_technique("query_transformation", {"method": method})

    def add_hyde(self) -> TechniquePipelineBuilder:
        """Add HyDE (Hypothetical Document Embeddings) technique.

        Returns:
            Self for method chaining
        """
        return self.add_technique("hyde")

    def add_vector_retrieval(self, top_k: int = 10) -> TechniquePipelineBuilder:
        """Add vector retrieval technique.

        Args:
            top_k: Number of documents to retrieve

        Returns:
            Self for method chaining
        """
        return self.add_technique("vector_retrieval", {"top_k": top_k})

    def add_fusion_retrieval(
        self, vector_weight: float = 0.7, top_k: int = 10
    ) -> TechniquePipelineBuilder:
        """Add fusion retrieval (hybrid vector + keyword).

        Args:
            vector_weight: Weight for vector search (0-1), keyword weight is (1 - vector_weight)
            top_k: Number of documents to retrieve

        Returns:
            Self for method chaining
        """
        return self.add_technique("fusion_retrieval", {"vector_weight": vector_weight, "top_k": top_k})

    def add_reranking(self, top_k: int = 10) -> TechniquePipelineBuilder:
        """Add LLM-based reranking.

        Args:
            top_k: Number of top documents to keep after reranking

        Returns:
            Self for method chaining
        """
        return self.add_technique("reranking", {"top_k": top_k})

    def add_contextual_compression(self) -> TechniquePipelineBuilder:
        """Add contextual compression technique.

        Returns:
            Self for method chaining
        """
        return self.add_technique("contextual_compression")

    def add_multi_faceted_filtering(
        self,
        min_similarity: float = 0.7,
        ensure_diversity: bool = False,
        metadata_filters: dict[str, Any] | None = None,
    ) -> TechniquePipelineBuilder:
        """Add multi-faceted filtering.

        Args:
            min_similarity: Minimum similarity threshold
            ensure_diversity: Whether to filter near-duplicates
            metadata_filters: Optional metadata filters

        Returns:
            Self for method chaining
        """
        return self.add_technique(
            "multi_faceted_filtering",
            {
                "min_similarity": min_similarity,
                "ensure_diversity": ensure_diversity,
                "metadata_filters": metadata_filters or {},
            },
        )

    def add_adaptive_retrieval(self) -> TechniquePipelineBuilder:
        """Add adaptive retrieval (query-type based strategy selection).

        Returns:
            Self for method chaining
        """
        return self.add_technique("adaptive_retrieval")

    def validate(self) -> tuple[bool, str | None]:
        """Validate the pipeline configuration.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.techniques:
            return False, "Pipeline is empty"

        technique_ids = [tid for tid, _ in self.techniques]
        is_valid, error = self.registry.validate_pipeline(technique_ids)

        if not is_valid:
            return False, error

        # Validate individual technique configs
        for technique_id, config in self.techniques:
            try:
                technique = self.registry.get_technique(technique_id)
                if not technique.validate_config(config):
                    return False, f"Invalid config for {technique_id}: {config}"
            except ValueError as e:
                return False, str(e)

        return True, None

    def build(self) -> TechniquePipeline:
        """Build the pipeline.

        Returns:
            Configured TechniquePipeline ready for execution

        Raises:
            ValueError: If pipeline configuration is invalid
        """
        is_valid, error = self.validate()
        if not is_valid:
            raise ValueError(f"Invalid pipeline: {error}")

        # Instantiate techniques
        instances: list[tuple[BaseTechnique, dict[str, Any]]] = []
        for technique_id, config in self.techniques:
            try:
                technique = self.registry.get_technique(technique_id)
                instances.append((technique, config))
            except ValueError as e:
                logger.error(f"Failed to instantiate technique {technique_id}: {e}")
                raise

        logger.info(f"Built pipeline with {len(instances)} techniques: {[t.technique_id for t, _ in instances]}")

        return TechniquePipeline(instances)

    def clear(self) -> TechniquePipelineBuilder:
        """Clear all techniques from the builder.

        Returns:
            Self for method chaining
        """
        self.techniques.clear()
        return self


# Pre-configured technique combinations for common use cases
TECHNIQUE_PRESETS: dict[str, list[TechniqueConfig]] = {
    "default": [
        TechniqueConfig(technique_id="vector_retrieval", config={"top_k": 10}),
        TechniqueConfig(technique_id="reranking", config={"top_k": 5}),
    ],
    "fast": [
        TechniqueConfig(technique_id="vector_retrieval", config={"top_k": 5}),
    ],
    "accurate": [
        TechniqueConfig(technique_id="query_transformation", config={"method": "rewrite"}),
        TechniqueConfig(technique_id="hyde"),
        TechniqueConfig(technique_id="fusion_retrieval", config={"vector_weight": 0.7, "top_k": 20}),
        TechniqueConfig(technique_id="reranking", config={"top_k": 10}),
        TechniqueConfig(technique_id="contextual_compression"),
    ],
    "cost_optimized": [
        TechniqueConfig(technique_id="vector_retrieval", config={"top_k": 5}),
        TechniqueConfig(
            technique_id="multi_faceted_filtering",
            config={"min_similarity": 0.7, "ensure_diversity": True},
        ),
    ],
    "comprehensive": [
        TechniqueConfig(technique_id="query_transformation", config={"method": "decomposition"}),
        TechniqueConfig(technique_id="adaptive_retrieval"),
        TechniqueConfig(technique_id="fusion_retrieval", config={"vector_weight": 0.8, "top_k": 20}),
        TechniqueConfig(technique_id="reranking", config={"top_k": 15}),
        TechniqueConfig(technique_id="contextual_compression"),
        TechniqueConfig(
            technique_id="multi_faceted_filtering",
            config={"min_similarity": 0.75, "ensure_diversity": True},
        ),
    ],
}


def create_preset_pipeline(preset_name: str, registry: TechniqueRegistry) -> TechniquePipeline:
    """Create a pipeline from a preset configuration.

    Args:
        preset_name: Name of the preset ("default", "fast", "accurate", etc.)
        registry: Technique registry

    Returns:
        Configured TechniquePipeline

    Raises:
        ValueError: If preset_name is unknown
    """
    if preset_name not in TECHNIQUE_PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}. Available: {list(TECHNIQUE_PRESETS.keys())}")

    builder = TechniquePipelineBuilder(registry)

    for technique_config in TECHNIQUE_PRESETS[preset_name]:
        if technique_config.enabled:
            builder.add_technique(technique_config.technique_id, technique_config.config)

    return builder.build()
