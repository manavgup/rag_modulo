"""Reranking module for improving retrieval quality using LLM-based scoring."""

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
        """


# -----------------------------------------------------------
# The LLM Reranker with Bug Fixes and Improved Scoring Logic
# -----------------------------------------------------------


class LLMReranker(BaseReranker):
    """LLM-based reranker using WatsonX or other LLM providers."""

    # pylint: disable=too-many-arguments,too-many-positional-arguments
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

        Raises:
            ValueError: If prompt_template is None.
        """
        if prompt_template is None:
            raise ValueError("prompt_template cannot be None for LLMReranker")

        self.llm_provider = llm_provider
        self.user_id = user_id
        self.prompt_template = prompt_template
        self.batch_size = batch_size
        self.score_scale = score_scale
        # Define the keys required by the template: 'query', 'document', 'scale'
        self.required_template_vars = self.prompt_template.input_variables

    def _extract_score(self, llm_response: str) -> float:
        """
        Extract numerical score from LLM response.
        (Simplified for robustness, ideally use structured JSON output)
        """
        try:
            # Look for a number followed by the scale, or just a number
            patterns = [
                r"(\d+(?:\.\d+)?)\s*/\s*\d+",  # "8.5/10"
                r"(?:score|rating|relevance)\s*[:=]?\s*(\d+(?:\.\d+)?)",  # "Score: 8.5"
                r"^(\d+(?:\.\d+)?)",  # Just a number at the start
            ]

            for pattern in patterns:
                match = re.search(pattern, llm_response.strip().lower())
                if match:
                    score = float(match.group(1))
                    # Normalize to 0-1 range
                    return min(max(score / self.score_scale, 0.0), 1.0)

            # Fallback: log and return neutral score
            logger.warning("Could not extract score from LLM response: %s", llm_response[:100].replace("\n", " "))
            return 0.5

        except (ValueError, AttributeError) as e:
            logger.error(
                "Error extracting score from response: %s | Error: %s", llm_response[:50].replace("\n", " "), e
            )
            return 0.5

    def _create_reranking_prompts(self, query: str, results: list[QueryResult]) -> list[str]:
        """
        Create list of formatted prompt strings for batch reranking.

        Formats each prompt using the template before passing to LLM provider.
        Returns list of ready-to-use prompt strings.
        """
        formatted_prompts = []
        for result in results:
            if result.chunk is None or result.chunk.text is None:
                continue

            # Prepare variables for the template
            prompt_vars = {
                "query": query,
                "document": result.chunk.text,
                "scale": str(self.score_scale),
            }

            # Only include valid variables based on the template's input_variables
            final_vars = {k: v for k, v in prompt_vars.items() if k in self.required_template_vars}

            # Format the prompt using the template's format_prompt method
            # PromptTemplateBase.format_prompt() returns a formatted string
            formatted_prompt = self.prompt_template.format_prompt(**final_vars)
            formatted_prompts.append(formatted_prompt)

        return formatted_prompts

    def _score_documents(self, query: str, results: list[QueryResult]) -> list[tuple[QueryResult, float]]:
        """
        Score documents using LLM.

        Formats prompts with template variables and passes formatted strings
        to LLM provider for batch generation.
        """
        if not results:
            return []

        scored_results = []

        # Process in batches
        for i in range(0, len(results), self.batch_size):
            batch = results[i : i + self.batch_size]

            # Format prompts with template variables - returns list[str]
            formatted_prompts = self._create_reranking_prompts(query, batch)

            try:
                # Call LLM with batch of formatted prompt strings
                # No template needed - prompts are already formatted
                responses = self.llm_provider.generate_text(
                    user_id=self.user_id,
                    prompt=formatted_prompts,  # list[str] of pre-formatted prompts
                    template=None,  # Not needed - prompts already formatted
                )

                # Extract scores from responses
                if isinstance(responses, list) and len(responses) == len(batch):
                    for result, response in zip(batch, responses, strict=False):
                        score = self._extract_score(response)
                        scored_results.append((result, score))
                else:
                    # Log unexpected response format but proceed with fallback
                    logger.error(
                        "LLM returned unexpected response format for batch %d. Fallbacking to original scores.",
                        i // self.batch_size + 1,
                    )
                    raise ValueError("Unexpected LLM response format.")

            except Exception as e:  # pylint: disable=broad-exception-caught
                # Justification: Fallback to original scores to ensure search continues
                # Fallback: use original scores for this batch, preserving relative order
                logger.error(
                    "Error scoring batch %d: %s. Using original scores as fallback.", i // self.batch_size + 1, e
                )
                for result in batch:
                    fallback_score = result.score if result.score is not None else 0.0
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
        """
        if not results:
            logger.info("No results to rerank")
            return []

        logger.info("=" * 80)
        logger.info("RERANKING: Starting LLM-based reranking")
        logger.info("Query: %s", query[:150])
        logger.info("Number of results: %d", len(results))
        logger.info("=" * 80)

        # Log original results with their vector similarity scores
        logger.info("\n📊 BEFORE RERANKING (Vector Similarity Scores):")
        for i, result in enumerate(results, 1):
            original_score = result.score if result.score is not None else 0.0
            chunk_text = result.chunk.text[:200] if result.chunk and result.chunk.text else "N/A"
            logger.info(
                "  %d. Score: %.4f | Text: %s...",
                i,
                original_score,
                chunk_text.replace("\n", " "),
            )

        # Score all documents with LLM
        scored_results = self._score_documents(query, results)

        # Sort by LLM scores (descending)
        sorted_results = sorted(scored_results, key=lambda x: x[1], reverse=True)

        # Update QueryResult scores with LLM scores
        reranked_results = []
        for result, llm_score in sorted_results:
            new_result = QueryResult(
                chunk=result.chunk,
                score=llm_score,
                embeddings=result.embeddings,
            )
            reranked_results.append(new_result)

        # Log reranked results with LLM scores
        logger.info("\n📊 AFTER RERANKING (LLM Relevance Scores):")
        for i, (result, llm_score) in enumerate(sorted_results, 1):
            chunk_text = result.chunk.text[:200] if result.chunk and result.chunk.text else "N/A"
            original_score = result.score if result.score is not None else 0.0
            logger.info(
                "  %d. LLM Score: %.4f (was %.4f) | Text: %s...",
                i,
                llm_score,
                original_score,
                chunk_text.replace("\n", " "),
            )

        # Return top_k if specified
        if top_k is not None:
            reranked_results = reranked_results[:top_k]
            logger.info("\n✂️  Returning top %d results", top_k)

        logger.info("=" * 80)
        logger.info("RERANKING: Complete. Returned %d results", len(reranked_results))
        logger.info("=" * 80)
        return reranked_results


class SimpleReranker(BaseReranker):
    """Simple reranker that just sorts by existing scores."""

    def rerank(
        self,
        query: str,  # noqa: ARG002
        results: list[QueryResult],
        top_k: int | None = None,
    ) -> list[QueryResult]:
        """
        Rerank by sorting on existing scores.
        """
        sorted_results = sorted(results, key=lambda x: x.score if x.score is not None else 0.0, reverse=True)
        if top_k is not None:
            return sorted_results[:top_k]
        return sorted_results
