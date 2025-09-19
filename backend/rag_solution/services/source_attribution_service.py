"""Source attribution service for Chain of Thought reasoning.

This service tracks source documents used in each reasoning step
and provides attribution information for transparency and verification.
"""

from rag_solution.schemas.chain_of_thought_schema import (
    ReasoningStep,
    SourceAttribution,
    SourceSummary,
)


class SourceAttributionService:
    """Service for tracking and managing source attributions in CoT reasoning."""

    def __init__(self) -> None:
        """Initialize the source attribution service."""
        self._source_cache: dict[str, SourceAttribution] = {}

    def create_source_attribution(
        self,
        document_id: str,
        relevance_score: float,
        document_title: str | None = None,
        excerpt: str | None = None,
        chunk_index: int | None = None,
        retrieval_rank: int | None = None,
    ) -> SourceAttribution:
        """Create a structured source attribution.

        Args:
            document_id: Unique identifier for the source document
            relevance_score: Relevance score for this source (0-1)
            document_title: Title or name of the source document
            excerpt: Relevant excerpt from the source
            chunk_index: Index of the chunk within the document
            retrieval_rank: Rank in the retrieval results

        Returns:
            SourceAttribution object
        """
        attribution = SourceAttribution(
            document_id=document_id,
            document_title=document_title,
            relevance_score=relevance_score,
            excerpt=excerpt,
            chunk_index=chunk_index,
            retrieval_rank=retrieval_rank,
        )

        # Cache for deduplication
        self._source_cache[document_id] = attribution
        return attribution

    def extract_sources_from_context(
        self,
        context_documents: list[str],
        search_results: list[dict[str, str | int | float]] | None = None,
    ) -> list[SourceAttribution]:
        """Extract source attributions from context documents.

        Args:
            context_documents: List of context document strings
            search_results: Optional structured search results with metadata

        Returns:
            List of SourceAttribution objects
        """
        attributions = []

        if search_results:
            # Use structured search results when available
            for i, result in enumerate(search_results):
                # Ensure proper typing for document_id
                doc_id = result.get("document_id", f"doc_{i}")
                if not isinstance(doc_id, str):
                    doc_id = str(doc_id)

                # Ensure proper typing for document_title
                title = result.get("title", result.get("document_title"))
                if title is not None and not isinstance(title, str):
                    title = str(title)

                # Ensure proper typing for relevance_score
                score = result.get("score", result.get("relevance_score", 0.5))
                if not isinstance(score, int | float):
                    score = 0.5
                relevance_score = float(score)

                # Ensure proper typing for excerpt
                content = result.get("content", result.get("text", ""))
                if not isinstance(content, str):
                    content = str(content)
                excerpt = content[:200]

                # Ensure proper typing for chunk_index
                chunk_idx = result.get("chunk_index")
                if chunk_idx is not None and not isinstance(chunk_idx, int):
                    try:
                        chunk_idx = int(chunk_idx)
                    except (ValueError, TypeError):
                        chunk_idx = None

                attribution = self.create_source_attribution(
                    document_id=doc_id,
                    document_title=title,
                    relevance_score=relevance_score,
                    excerpt=excerpt,
                    chunk_index=chunk_idx,
                    retrieval_rank=i + 1,
                )
                attributions.append(attribution)
        else:
            # Fallback: create attributions from raw context strings
            for i, context in enumerate(context_documents):
                if not context.strip():
                    continue

                # Extract document ID if present in context
                document_id = f"context_doc_{i}"
                if "id:" in context:
                    try:
                        doc_id_part = context.split("id:")[1].split()[0].strip()
                        document_id = doc_id_part
                    except (IndexError, AttributeError):
                        pass

                attribution = self.create_source_attribution(
                    document_id=document_id,
                    relevance_score=max(0.3, 1.0 - (i * 0.1)),  # Decreasing relevance by rank
                    excerpt=context[:200] if len(context) > 200 else context,
                    retrieval_rank=i + 1,
                )
                attributions.append(attribution)

        return attributions

    def aggregate_sources_across_steps(self, reasoning_steps: list[ReasoningStep]) -> SourceSummary:
        """Aggregate source attributions across all reasoning steps.

        Args:
            reasoning_steps: List of reasoning steps with source attributions

        Returns:
            SourceSummary with aggregated source information
        """
        all_sources: dict[str, SourceAttribution] = {}
        source_usage_by_step: dict[int, list[str]] = {}

        # Collect all sources and track usage by step
        for step in reasoning_steps:
            step_sources = []
            for attribution in step.source_attributions:
                # Track unique sources
                if attribution.document_id not in all_sources:
                    all_sources[attribution.document_id] = attribution
                else:
                    # Update with highest relevance score if seen multiple times
                    existing = all_sources[attribution.document_id]
                    if attribution.relevance_score > existing.relevance_score:
                        all_sources[attribution.document_id] = attribution

                step_sources.append(attribution.document_id)

            source_usage_by_step[step.step_number] = step_sources

        # Identify primary sources (highest relevance scores)
        all_sources_list = list(all_sources.values())
        all_sources_list.sort(key=lambda x: x.relevance_score, reverse=True)

        # Primary sources are top 3 or those with relevance > 0.7
        primary_sources = [source for source in all_sources_list if source.relevance_score > 0.7][:3]

        if not primary_sources and all_sources_list:
            # If no high-relevance sources, take top 3
            primary_sources = all_sources_list[:3]

        return SourceSummary(
            all_sources=all_sources_list,
            primary_sources=primary_sources,
            source_usage_by_step=source_usage_by_step,
        )

    def enhance_reasoning_step_with_sources(
        self,
        step: ReasoningStep,
        retrieved_documents: list[dict[str, str | int | float]] | None = None,
    ) -> ReasoningStep:
        """Enhance a reasoning step with source attributions.

        Args:
            step: The reasoning step to enhance
            retrieved_documents: Optional retrieved documents for this step

        Returns:
            Enhanced reasoning step with source attributions
        """
        if retrieved_documents:
            # Extract sources from structured retrieval results
            source_attributions = self.extract_sources_from_context(
                context_documents=[],
                search_results=retrieved_documents,
            )
        else:
            # Extract sources from existing context_used field
            source_attributions = self.extract_sources_from_context(
                context_documents=step.context_used,
                search_results=None,
            )

        # Update the step with source attributions
        step.source_attributions = source_attributions
        return step

    def format_sources_for_display(
        self, source_summary: SourceSummary, include_excerpts: bool = True
    ) -> dict[
        str, str | int | float | list[dict[str, str | int | float]] | dict[str, dict[str, str | int | list[str]]]
    ]:
        """Format sources for user-friendly display.

        Args:
            source_summary: SourceSummary to format
            include_excerpts: Whether to include document excerpts

        Returns:
            Formatted source information for display
        """
        primary_sources: list[dict[str, str | int | float]] = []
        all_sources: list[dict[str, str | int | float]] = []
        step_breakdown: dict[str, dict[str, str | int | list[str]]] = {}

        # Format primary sources
        for source in source_summary.primary_sources:
            primary_info: dict[str, str | int | float] = {
                "document_id": source.document_id,
                "title": source.document_title or source.document_id,
                "relevance": round(source.relevance_score, 2),
            }
            if source.retrieval_rank is not None:
                primary_info["rank"] = source.retrieval_rank
            if include_excerpts and source.excerpt:
                primary_info["excerpt"] = source.excerpt
            primary_sources.append(primary_info)

        # Format all sources
        for source in source_summary.all_sources:
            source_info: dict[str, str | int | float] = {
                "document_id": source.document_id,
                "title": source.document_title or source.document_id,
                "relevance": round(source.relevance_score, 2),
            }
            if include_excerpts and source.excerpt:
                source_info["excerpt"] = source.excerpt
            all_sources.append(source_info)

        # Format step breakdown
        for step_num, doc_ids in source_summary.source_usage_by_step.items():
            step_breakdown[f"step_{step_num}"] = {
                "step_number": step_num,
                "sources_used": len(doc_ids),
                "document_ids": doc_ids,
            }

        return {
            "total_sources": len(source_summary.all_sources),
            "primary_sources": primary_sources,
            "all_sources": all_sources,
            "step_breakdown": step_breakdown,
        }


__all__ = ["SourceAttributionService"]
