"""Unit tests for reranker module."""

# pylint: disable=redefined-outer-name,protected-access,import-error
# Justification: pytest fixtures are meant to be redefined as parameters,
# we need to test protected methods, and import-error is false positive

import uuid
from unittest.mock import Mock, create_autospec

import pytest
from rag_solution.generation.providers.base import LLMBase
from rag_solution.retrieval.reranker import LLMReranker, SimpleReranker
from rag_solution.schemas.prompt_template_schema import PromptTemplateBase, PromptTemplateType
from vectordbs.data_types import DocumentChunkWithScore, QueryResult
from pydantic import UUID4


@pytest.fixture
def user_id() -> UUID4:
    """Create a test user ID."""
    return UUID4(str(uuid.uuid4()))


@pytest.fixture
def mock_llm_provider() -> Mock:
    """Create a mock LLM provider."""
    return create_autospec(LLMBase, instance=True)


@pytest.fixture
def mock_prompt_template() -> PromptTemplateBase:
    """Create a mock prompt template.

    Note: Uses 'document' variable name to match what LLMReranker uses internally.
    """
    return PromptTemplateBase(
        name="reranking",
        user_id=UUID4(str(uuid.uuid4())),
        template_type=PromptTemplateType.RERANKING,
        template_format="Rate the relevance of this document to the query on a scale of 0-{scale}:\n\nQuery: {query}\n\nDocument: {document}\n\nRelevance score:",
        input_variables={"query": "str", "document": "str", "scale": "str"},
        max_context_length=4000,
    )


@pytest.fixture
def sample_results() -> list[QueryResult]:
    """Create sample query results for testing."""
    return [
        QueryResult(
            chunk=DocumentChunkWithScore(
                chunk_id="1", text="Machine learning is a subset of artificial intelligence.", embeddings=[], score=0.9
            ),
            score=0.9,
            embeddings=[],
        ),
        QueryResult(
            chunk=DocumentChunkWithScore(
                chunk_id="2", text="The weather today is sunny and warm.", embeddings=[], score=0.7
            ),
            score=0.7,
            embeddings=[],
        ),
        QueryResult(
            chunk=DocumentChunkWithScore(
                chunk_id="3", text="Deep learning uses neural networks with multiple layers.", embeddings=[], score=0.8
            ),
            score=0.8,
            embeddings=[],
        ),
    ]


class TestSimpleReranker:
    """Tests for SimpleReranker class."""

    def test_rerank_sorts_by_score(self, sample_results: list[QueryResult]) -> None:
        """Test that SimpleReranker sorts results by existing scores."""
        reranker = SimpleReranker()
        reranked = reranker.rerank("machine learning", sample_results)

        # Should be sorted in descending order: 0.9, 0.8, 0.7
        assert len(reranked) == 3
        assert reranked[0].chunk.chunk_id == "1"  # score 0.9
        assert reranked[1].chunk.chunk_id == "3"  # score 0.8
        assert reranked[2].chunk.chunk_id == "2"  # score 0.7

    def test_rerank_with_top_k(self, sample_results: list[QueryResult]) -> None:
        """Test that SimpleReranker respects top_k parameter."""
        reranker = SimpleReranker()
        reranked = reranker.rerank("machine learning", sample_results, top_k=2)

        assert len(reranked) == 2
        assert reranked[0].chunk.chunk_id == "1"  # score 0.9
        assert reranked[1].chunk.chunk_id == "3"  # score 0.8

    def test_rerank_empty_results(self) -> None:
        """Test that SimpleReranker handles empty results list."""
        reranker = SimpleReranker()
        reranked = reranker.rerank("test query", [])

        assert len(reranked) == 0

    def test_rerank_handles_none_scores(self) -> None:
        """Test that SimpleReranker handles None scores gracefully."""
        results = [
            QueryResult(
                chunk=DocumentChunkWithScore(chunk_id="1", text="test", embeddings=[], score=0.0),
                score=None,
                embeddings=[],
            ),
            QueryResult(
                chunk=DocumentChunkWithScore(chunk_id="2", text="test2", embeddings=[], score=0.5),
                score=0.5,
                embeddings=[],
            ),
        ]
        reranker = SimpleReranker()
        reranked = reranker.rerank("test", results)

        # Should not crash, None should be treated as 0.0
        assert len(reranked) == 2
        assert reranked[0].chunk.chunk_id == "2"  # score 0.5 comes first


class TestLLMReranker:
    """Tests for LLMReranker class."""

    def test_extract_score_from_simple_number(
        self, mock_llm_provider: Mock, user_id: UUID4, mock_prompt_template: PromptTemplateBase
    ) -> None:
        """Test extracting score from simple number response."""
        reranker = LLMReranker(mock_llm_provider, user_id, mock_prompt_template)

        assert reranker._extract_score("8") == 0.8
        assert reranker._extract_score("10") == 1.0
        assert reranker._extract_score("0") == 0.0
        assert reranker._extract_score("5.5") == 0.55

    def test_extract_score_from_formatted_response(
        self, mock_llm_provider: Mock, user_id: UUID4, mock_prompt_template: PromptTemplateBase
    ) -> None:
        """Test extracting score from formatted responses."""
        reranker = LLMReranker(mock_llm_provider, user_id, mock_prompt_template)

        assert reranker._extract_score("Score: 8") == 0.8
        assert reranker._extract_score("Rating: 7.5") == 0.75
        assert reranker._extract_score("8/10") == 0.8

    def test_extract_score_invalid_response(
        self, mock_llm_provider: Mock, user_id: UUID4, mock_prompt_template: PromptTemplateBase
    ) -> None:
        """Test that invalid responses return neutral score."""
        reranker = LLMReranker(mock_llm_provider, user_id, mock_prompt_template)

        # Should return 0.5 (neutral) for invalid responses
        assert reranker._extract_score("not a number") == 0.5
        assert reranker._extract_score("") == 0.5

    def test_create_reranking_prompts(
        self,
        mock_llm_provider: Mock,
        user_id: UUID4,
        mock_prompt_template: PromptTemplateBase,
        sample_results: list[QueryResult],
    ) -> None:
        """Test creating reranking prompts from query and results.

        Updated test: _create_reranking_prompts now returns list[str] of formatted prompts
        instead of list[dict] of variables, as prompts are pre-formatted before calling LLM.
        """
        reranker = LLMReranker(mock_llm_provider, user_id, mock_prompt_template)
        prompts = reranker._create_reranking_prompts("machine learning", sample_results)

        # Verify we got 3 formatted prompt strings
        assert len(prompts) == 3
        assert isinstance(prompts[0], str)

        # Verify the prompts contain the expected content
        assert "machine learning" in prompts[0]
        assert "Machine learning is a subset of artificial intelligence." in prompts[0]
        assert "0-10" in prompts[0]  # Template uses "scale of 0-{scale}"

    def test_create_reranking_prompts_skips_none_chunks(
        self, mock_llm_provider: Mock, user_id: UUID4, mock_prompt_template: PromptTemplateBase
    ) -> None:
        """Test that prompts skip results with None chunks."""
        results = [
            QueryResult(chunk=None, score=0.5, embeddings=[]),
            QueryResult(
                chunk=DocumentChunkWithScore(chunk_id="1", text="test", embeddings=[], score=0.5),
                score=0.5,
                embeddings=[],
            ),
        ]
        reranker = LLMReranker(mock_llm_provider, user_id, mock_prompt_template)
        prompts = reranker._create_reranking_prompts("test", results)

        assert len(prompts) == 1  # Only one valid result

    def test_rerank_with_llm(
        self,
        mock_llm_provider: Mock,
        user_id: UUID4,
        mock_prompt_template: PromptTemplateBase,
        sample_results: list[QueryResult],
    ) -> None:
        """Test reranking with LLM scores."""
        # Mock LLM to return scores: 9, 3, 8 (so first doc most relevant, second least)
        mock_llm_provider.generate_text.return_value = ["9", "3", "8"]

        reranker = LLMReranker(mock_llm_provider, user_id, mock_prompt_template)
        reranked = reranker.rerank("machine learning", sample_results)

        assert len(reranked) == 3
        # Should be sorted by LLM scores: 9 (0.9), 8 (0.8), 3 (0.3)
        assert reranked[0].chunk.chunk_id == "1"  # LLM score 9
        assert reranked[0].score == 0.9
        assert reranked[1].chunk.chunk_id == "3"  # LLM score 8
        assert reranked[1].score == 0.8
        assert reranked[2].chunk.chunk_id == "2"  # LLM score 3
        assert reranked[2].score == 0.3

    def test_rerank_with_top_k(
        self,
        mock_llm_provider: Mock,
        user_id: UUID4,
        mock_prompt_template: PromptTemplateBase,
        sample_results: list[QueryResult],
    ) -> None:
        """Test that LLM reranker respects top_k parameter."""
        mock_llm_provider.generate_text.return_value = ["9", "3", "8"]

        reranker = LLMReranker(mock_llm_provider, user_id, mock_prompt_template)
        reranked = reranker.rerank("machine learning", sample_results, top_k=2)

        assert len(reranked) == 2
        assert reranked[0].chunk.chunk_id == "1"  # Top LLM score
        assert reranked[1].chunk.chunk_id == "3"  # Second best LLM score

    def test_rerank_empty_results(
        self, mock_llm_provider: Mock, user_id: UUID4, mock_prompt_template: PromptTemplateBase
    ) -> None:
        """Test that LLM reranker handles empty results."""
        reranker = LLMReranker(mock_llm_provider, user_id, mock_prompt_template)
        reranked = reranker.rerank("test", [])

        assert len(reranked) == 0
        mock_llm_provider.generate_text.assert_not_called()

    def test_rerank_handles_llm_error(
        self,
        mock_llm_provider: Mock,
        user_id: UUID4,
        mock_prompt_template: PromptTemplateBase,
        sample_results: list[QueryResult],
    ) -> None:
        """Test that reranker falls back to original scores on LLM error."""
        # Mock LLM to raise a ValueError (simulates LLM response parsing failure)
        mock_llm_provider.generate_text.side_effect = ValueError("LLM API error")

        reranker = LLMReranker(mock_llm_provider, user_id, mock_prompt_template)
        reranked = reranker.rerank("machine learning", sample_results)

        # Should fallback to original scores
        assert len(reranked) == 3
        assert reranked[0].chunk.chunk_id == "1"  # original score 0.9
        assert reranked[0].score == 0.9

    def test_batch_processing(
        self, mock_llm_provider: Mock, user_id: UUID4, mock_prompt_template: PromptTemplateBase
    ) -> None:
        """Test that reranker processes results in batches."""
        # Create 15 results to test batching (default batch_size=10)
        results = [
            QueryResult(
                chunk=DocumentChunkWithScore(chunk_id=str(i), text=f"Document {i}", embeddings=[], score=0.5),
                score=0.5,
                embeddings=[],
            )
            for i in range(15)
        ]

        # Mock LLM to return scores
        mock_llm_provider.generate_text.return_value = ["5"] * 15

        reranker = LLMReranker(mock_llm_provider, user_id, mock_prompt_template, batch_size=10)
        reranked = reranker.rerank("test", results)

        assert len(reranked) == 15
        # Should have been called twice (batch 1: 10 items, batch 2: 5 items)
        assert mock_llm_provider.generate_text.call_count == 2

    def test_custom_score_scale(
        self,
        mock_llm_provider: Mock,
        user_id: UUID4,
        mock_prompt_template: PromptTemplateBase,
        sample_results: list[QueryResult],
    ) -> None:
        """Test reranker with custom score scale."""
        # Use score scale of 100 instead of default 10
        mock_llm_provider.generate_text.return_value = ["75", "25", "50"]

        reranker = LLMReranker(mock_llm_provider, user_id, mock_prompt_template, score_scale=100)
        reranked = reranker.rerank("test", sample_results)

        # Scores should be normalized to 0-1 range
        assert reranked[0].score == 0.75
        assert reranked[1].score == 0.50
        assert reranked[2].score == 0.25
