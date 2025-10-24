"""Debug test for reranking functionality.

Tests if the reranker is actually calling the LLM and extracting scores correctly.
"""

import logging
import uuid

from pydantic import UUID4

from rag_solution.retrieval.reranker import LLMReranker
from rag_solution.schemas.prompt_template_schema import PromptTemplateBase, PromptTemplateType
from vectordbs.data_types import DocumentChunkMetadata, DocumentChunkWithScore, QueryResult, Source

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class MockLLMProvider:
    """Mock LLM provider for testing."""

    def generate_text(self, user_id, prompt, template=None, variables=None, **kwargs):
        """Mock generate_text that returns different scores."""
        logger.info(f"MockLLM called with prompt: {prompt[:100] if isinstance(prompt, str) else 'list'}")
        logger.info(f"Variables: {variables}")

        # If prompt is a list (batch), return list of scores
        if isinstance(prompt, list):
            scores = [f"Score: {i + 1}" for i in range(len(prompt))]
            logger.info(f"Returning batch scores: {scores}")
            return scores
        else:
            logger.info("Returning single score: Score: 5")
            return "Score: 5"


def create_mock_template(user_id: UUID4) -> PromptTemplateBase:
    """Create a mock prompt template for testing."""
    return PromptTemplateBase(
        name="test_reranking",
        user_id=user_id,
        template_type=PromptTemplateType.RERANKING,
        template_format="Relevance score for query: {query}\nDocument: {document}\nScale: {scale}",
        input_variables={"query": "The search query", "document": "The document text", "scale": "Score scale"},
        is_default=True,
    )


def test_reranker_score_extraction():
    """Test if reranker can extract scores from LLM responses."""
    logger.info("\n=== Testing Reranker Score Extraction ===\n")

    # Create mock LLM and reranker
    mock_llm = MockLLMProvider()
    test_user_id = uuid.uuid4()
    mock_template = create_mock_template(test_user_id)

    reranker = LLMReranker(
        llm_provider=mock_llm,
        user_id=test_user_id,
        prompt_template=mock_template,
        batch_size=3,
        score_scale=10,
    )

    # Test score extraction
    logger.info("\n--- Testing Score Extraction ---")
    test_responses = [
        "Score: 8",
        "The relevance score is 7",
        "8/10",
        "9.5",
        "This document is relevant with a score of 6",
    ]

    for response in test_responses:
        score = reranker._extract_score(response)
        logger.info(f"Response: '{response}' -> Score: {score}")

    # Create test query results
    logger.info("\n--- Testing Reranking with Mock LLM ---")
    test_results = [
        QueryResult(
            chunk=DocumentChunkWithScore(
                id="chunk1",
                text="IBM reported revenue of $60.5 billion in 2022.",
                source="test_doc.txt",
                page=1,
                score=0.5,
                metadata=DocumentChunkMetadata(source=Source.PDF),
            ),
            score=0.5,
            embeddings=None,
        ),
        QueryResult(
            chunk=DocumentChunkWithScore(
                id="chunk2",
                text="The weather was nice yesterday.",
                source="test_doc.txt",
                page=2,
                score=0.3,
                metadata=DocumentChunkMetadata(source=Source.PDF),
            ),
            score=0.3,
            embeddings=None,
        ),
        QueryResult(
            chunk=DocumentChunkWithScore(
                id="chunk3",
                text="Cloud computing services grew 15% year over year.",
                source="test_doc.txt",
                page=3,
                score=0.4,
                metadata=DocumentChunkMetadata(source=Source.PDF),
            ),
            score=0.4,
            embeddings=None,
        ),
    ]

    query = "What was IBM's revenue in 2022?"

    logger.info(f"\nQuery: {query}")
    logger.info(f"Input results ({len(test_results)}):")
    for i, result in enumerate(test_results):
        logger.info(f"  {i + 1}. Score: {result.score:.3f} - {result.chunk.text[:60]}")

    # Rerank
    reranked = reranker.rerank(query, test_results, top_k=None)

    logger.info(f"\nReranked results ({len(reranked)}):")
    for i, result in enumerate(reranked):
        logger.info(f"  {i + 1}. Score: {result.score:.3f} - {result.chunk.text[:60]}")

    # Check if scores were actually updated
    scores_updated = any(result.score != orig.score for result, orig in zip(reranked, test_results))
    logger.info(f"\nScores updated: {scores_updated}")

    if scores_updated:
        logger.info("✅ PASS: Reranker is working!")
        return True
    else:
        logger.error("❌ FAIL: Reranker scores not updated - LLM might not be called!")
        return False


if __name__ == "__main__":
    success = test_reranker_score_extraction()
    exit(0 if success else 1)
