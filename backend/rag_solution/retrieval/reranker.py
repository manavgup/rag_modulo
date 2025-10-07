"""Reranking module for improving retrieval quality using LLM-based scoring.

This module provides reranking capabilities to improve the quality of retrieved documents
by using language models to score query-document relevance.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod

from pydantic import UUID4

from rag_solution.generation.providers.base import LLMBase
from rag_solution.schemas.prompt_template_schema import PromptTemplateBase
from vectordbs.data_types import QueryResult

logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
# Justification: Abstract base class defining interface
class BaseReranker(ABC):
    """Abstract base class for reranking implementations."""

    @abstractmethod
    def rerank(
        self,
        query: str,
        results: list[QueryResult],
        top_k: int | None = None,
    ) -> list[QueryResult]:
        """
        Rerank search results based on query relevance.

        Args:
            query: The search query string.
            results: List of QueryResult objects to rerank.
            top_k: Optional number of top results to return. If None, returns all reranked results.

        Returns:
            List of QueryResult objects sorted by relevance score.
        """


class LLMReranker(BaseReranker):
    """LLM-based reranker using WatsonX or other LLM providers.

    This reranker uses a language model to score the relevance of each document
    to the query, providing more sophisticated relevance scoring than simple
    vector similarity.

    The LLM is prompted to score each query-document pair on a scale, and
    results are sorted by these scores.
    """

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    # Justification: Reranker configuration requires these parameters for flexibility
    def __init__(
        self,
        llm_provider: LLMBase,
        user_id: UUID4,
        prompt_template: PromptTemplateBase,
        *,
        batch_size: int = 10,
        score_scale: int = 10,
    ) -> None:
        """
        Initialize LLM-based reranker.

        Args:
            llm_provider: The LLM provider instance (e.g., WatsonXLLM).
            user_id: User UUID for LLM requests.
            prompt_template: Template for reranking prompts.
            batch_size: Number of documents to score in parallel.
            score_scale: Maximum score value (e.g., 10 for 0-10 scale).
        """
        self.llm_provider = llm_provider
        self.user_id = user_id
        self.prompt_template = prompt_template
        self.batch_size = batch_size
        self.score_scale = score_scale

    def _extract_score(self, llm_response: str) -> float:
        """
        Extract numerical score from LLM response.

        Args:
            llm_response: Raw text response from LLM.

        Returns:
            Extracted score normalized to 0-1 range.
        """
        try:
            # Try to extract a number from the response
            # Look for patterns like "Score: 8", "8/10", "8.5", etc.
            patterns = [
                r"(?:score|rating)?\s*[:=]?\s*(\d+(?:\.\d+)?)",  # "Score: 8.5" or "8.5"
                r"(\d+(?:\.\d+)?)\s*/\s*\d+",  # "8/10"
                r"^(\d+(?:\.\d+)?)",  # Just a number at the start
            ]

            for pattern in patterns:
                match = re.search(pattern, llm_response.strip().lower())
                if match:
                    score = float(match.group(1))
                    # Normalize to 0-1 range
                    return min(max(score / self.score_scale, 0.0), 1.0)

            # If no score found, log warning and return neutral score
            logger.warning("Could not extract score from LLM response: %s", llm_response[:100])
            return 0.5

        except (ValueError, AttributeError) as e:
            logger.warning("Error extracting score from '%s': %s", llm_response[:100], e)
            return 0.5

    def _create_reranking_prompts(self, query: str, results: list[QueryResult]) -> list[dict[str, str]]:
        """
        Create reranking prompts for each query-document pair.

        Args:
            query: The search query.
            results: List of QueryResult objects.

        Returns:
            List of variable dictionaries for prompt formatting.
        """
        prompts = []
        for result in results:
            if result.chunk is None or result.chunk.text is None:
                continue
            prompt_vars = {
                "query": query,
                "document": result.chunk.text,
                "scale": str(self.score_scale),
            }
            prompts.append(prompt_vars)
        return prompts

    def _score_documents(self, query: str, results: list[QueryResult]) -> list[tuple[QueryResult, float]]:
        """
        Score documents using LLM.

        Args:
            query: The search query.
            results: List of QueryResult objects to score.

        Returns:
            List of tuples (QueryResult, score).
        """
        if not results:
            return []

        scored_results = []

        # Process in batches to avoid overwhelming the LLM
        for i in range(0, len(results), self.batch_size):
            batch = results[i : i + self.batch_size]
            batch_prompts = self._create_reranking_prompts(query, batch)

            try:
                # Generate scores using LLM
                # For each document, format the prompt with the template
                formatted_prompts = []
                for prompt_vars in batch_prompts:
                    # The template formatting is handled by the LLM provider
                    # We'll pass the document text as the "context" for the template
                    formatted_prompts.append(prompt_vars["document"])

                # Call LLM with batch of prompts
                responses = self.llm_provider.generate_text(
                    user_id=self.user_id,
                    prompt=formatted_prompts,
                    template=self.prompt_template,
                    variables={"query": query, "scale": str(self.score_scale)},
                )

                # Extract scores from responses
                if isinstance(responses, list):
                    for result, response in zip(batch, responses, strict=False):
                        score = self._extract_score(response)
                        scored_results.append((result, score))
                else:
                    # Single response case
                    score = self._extract_score(responses)
                    scored_results.append((batch[0], score))

            except Exception as e:  # pylint: disable=broad-exception-caught
                # Justification: Need to catch all exceptions to ensure fallback to original scores
                logger.error("Error scoring batch %d: %s", i // self.batch_size + 1, e)
                # Fallback: use original scores for this batch
                for result in batch:
                    fallback_score = result.score if result.score is not None else 0.5
                    scored_results.append((result, fallback_score))

        return scored_results

    def rerank(
        self,
        query: str,
        results: list[QueryResult],
        top_k: int | None = None,
    ) -> list[QueryResult]:
        """
        Rerank search results using LLM-based scoring.

        Args:
            query: The search query string.
            results: List of QueryResult objects to rerank.
            top_k: Optional number of top results to return.

        Returns:
            List of QueryResult objects sorted by LLM relevance scores.
        """
        if not results:
            logger.info("No results to rerank")
            return []

        logger.info("Reranking %d results for query: %s", len(results), query[:100])

        # Score all documents with LLM
        scored_results = self._score_documents(query, results)

        # Sort by LLM scores (descending)
        sorted_results = sorted(scored_results, key=lambda x: x[1], reverse=True)

        # Update QueryResult scores with LLM scores
        reranked_results = []
        for result, llm_score in sorted_results:
            # Create new QueryResult with updated score
            new_result = QueryResult(
                chunk=result.chunk,
                score=llm_score,  # Use LLM score instead of original vector similarity score
                embeddings=result.embeddings,
            )
            reranked_results.append(new_result)

        # Return top_k if specified
        if top_k is not None:
            reranked_results = reranked_results[:top_k]

        logger.info("Reranking complete. Returning %d results", len(reranked_results))
        return reranked_results


class SimpleReranker(BaseReranker):
    """Simple reranker that just sorts by existing scores.

    This is a fallback reranker that doesn't use LLM, useful for
    testing or when LLM-based reranking is not needed.
    """

    def rerank(
        self,
        query: str,  # noqa: ARG002
        results: list[QueryResult],
        top_k: int | None = None,
    ) -> list[QueryResult]:
        """
        Rerank by sorting on existing scores.

        Args:
            query: The search query string (unused).
            results: List of QueryResult objects to rerank.
            top_k: Optional number of top results to return.

        Returns:
            List of QueryResult objects sorted by existing scores.
        """
        sorted_results = sorted(results, key=lambda x: x.score if x.score is not None else 0.0, reverse=True)
        if top_k is not None:
            return sorted_results[:top_k]
        return sorted_results
