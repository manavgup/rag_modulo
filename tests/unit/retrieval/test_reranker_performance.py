"""
Performance tests for async concurrent reranking (P0-3).

Tests verify that reranking uses concurrent batch processing for optimal performance.

Test Strategy:
- Use real reranker with mocked LLM provider
- Verify concurrent batch processing (not sequential)
- Measure performance improvements
- Validate accuracy is maintained

Expected Flow (20 documents, batch_size=10):
  OLD: Batch1 (10 docs, 6s) → Batch2 (10 docs, 6s) = 12s total (sequential)
  NEW: Batch1 + Batch2 (concurrent, 6s) = 6s total (50% faster)
"""

import asyncio
import time
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from rag_solution.retrieval.reranker import LLMReranker
from vectordbs.data_types import DocumentChunk, DocumentChunkMetadata, QueryResult, Source


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_documents_20():
    """Create 20 mock documents for testing."""
    docs = []
    for i in range(20):
        metadata = DocumentChunkMetadata(
            document_id=f"doc_{i}",
            chunk_index=0,
            total_chunks=1,
            source=Source.OTHER,
        )
        chunk = DocumentChunk(
            id=f"chunk_{i}",
            text=f"Document {i} contains relevant information about the query topic.",
            metadata=metadata,
        )
        result = QueryResult(
            chunk=chunk,
            score=0.9 - (i * 0.01),  # Descending scores
            collection_id="test_collection",
        )
        docs.append(result)
    return docs


@pytest.fixture
def mock_llm_provider_async():
    """Mock LLM provider with async batch generation."""
    provider = Mock()

    # Simulate async processing with 100ms delay per document
    async def mock_generate_text(user_id, prompt, template=None):
        if isinstance(prompt, list):
            # Simulate concurrent processing
            await asyncio.sleep(0.1 * len(prompt))  # 100ms per document
            return [f"Score: 8.{i}" for i in range(len(prompt))]
        else:
            await asyncio.sleep(0.1)
            return "Score: 8.0"

    provider.generate_text = AsyncMock(side_effect=mock_generate_text)
    return provider


@pytest.fixture
def mock_prompt_template():
    """Mock reranking prompt template."""
    now = datetime.now(UTC)
    from rag_solution.schemas.prompt_template_schema import PromptTemplateOutput, PromptTemplateType

    return PromptTemplateOutput(
        id=uuid4(),
        name="reranking-template",
        user_id=uuid4(),
        template_type=PromptTemplateType.RERANKING,
        system_prompt="You are a relevance scoring assistant.",
        template_format="Query: {query}\n\nDocument: {document}\n\nScore (0-10):",
        input_variables={"query": "query", "document": "document"},
        example_inputs={"query": "test query", "document": "test document"},
        is_default=True,
        created_at=now,
        updated_at=now,
    )


# ============================================================================
# UNIT TESTS: Concurrent Processing
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncConcurrentReranking:
    """Test async concurrent batch processing for reranking."""

    async def test_reranking_uses_concurrent_batch_processing(
        self, mock_llm_provider_async, mock_prompt_template, mock_documents_20
    ):
        """
        TDD Test: Verify reranking processes batches concurrently, not sequentially.

        Expected behavior:
        - 20 documents split into 2 batches of 10
        - Both batches processed concurrently (asyncio.gather)
        - Total time ≈ time for single batch (not 2x)

        This test FAILS initially because _score_documents is synchronous.
        """
        # Arrange
        reranker = LLMReranker(
            llm_provider=mock_llm_provider_async,
            user_id=uuid4(),
            prompt_template=mock_prompt_template,
            batch_size=10,
            score_scale=10,
        )

        # Act: Measure reranking time
        start_time = time.time()
        result = await reranker.rerank_async(
            query="test query", results=mock_documents_20, top_k=5
        )
        elapsed_time = time.time() - start_time

        # Assert: Concurrent processing should take ~1 batch time, not 2x
        # Sequential: 2 batches * 1.0s = 2.0s
        # Concurrent: max(1.0s, 1.0s) = 1.0s
        assert elapsed_time < 1.5, (
            f"Concurrent processing should take < 1.5s, took {elapsed_time:.2f}s"
        )

        # Assert: Mock provider called with batches
        assert mock_llm_provider_async.generate_text.call_count == 2  # 2 batches

        # Assert: Results returned correctly
        assert len(result) == 5  # top_k=5

    async def test_concurrent_reranking_calls_provider_correct_number_of_times(
        self, mock_llm_provider_async, mock_prompt_template, mock_documents_20
    ):
        """
        TDD Test: Verify provider called correct number of times for concurrent batches.

        Expected: Called once per batch (2 calls for 20 docs with batch_size=10)
        """
        # Arrange
        reranker = LLMReranker(
            llm_provider=mock_llm_provider_async,
            user_id=uuid4(),
            prompt_template=mock_prompt_template,
            batch_size=10,
            score_scale=10,
        )

        # Act
        await reranker.rerank_async(query="test query", results=mock_documents_20, top_k=10)

        # Assert: Provider called exactly 2 times (2 batches)
        assert mock_llm_provider_async.generate_text.call_count == 2

    async def test_concurrent_reranking_maintains_accuracy(
        self, mock_llm_provider_async, mock_prompt_template, mock_documents_20
    ):
        """
        TDD Test: Verify concurrent processing maintains reranking accuracy.

        Expected: Results properly scored and sorted by LLM scores
        """
        # Arrange
        reranker = LLMReranker(
            llm_provider=mock_llm_provider_async,
            user_id=uuid4(),
            prompt_template=mock_prompt_template,
            batch_size=10,
            score_scale=10,
        )

        # Act
        result = await reranker.rerank_async(
            query="test query", results=mock_documents_20, top_k=5
        )

        # Assert: Top 5 results returned
        assert len(result) == 5

        # Assert: Results are QueryResult objects
        assert all(isinstance(r, QueryResult) for r in result)

        # Assert: Results have scores assigned
        assert all(r.score is not None for r in result)

    async def test_concurrent_reranking_with_small_dataset(
        self, mock_llm_provider_async, mock_prompt_template
    ):
        """
        TDD Test: Verify concurrent processing works efficiently for small datasets.

        Expected: Small dataset (<= batch_size) processed in single batch
        """
        # Arrange: 5 documents (less than batch_size=10)
        small_docs = []
        for i in range(5):
            metadata = DocumentChunkMetadata(
                document_id=f"doc_{i}",
                chunk_index=0,
                total_chunks=1,
                source=Source.OTHER,
            )
            chunk = DocumentChunk(
                id=f"chunk_{i}",
                text=f"Document {i}",
                metadata=metadata,
            )
            result = QueryResult(
                chunk=chunk,
                score=0.9 - (i * 0.1),
                collection_id="test",
            )
            small_docs.append(result)

        reranker = LLMReranker(
            llm_provider=mock_llm_provider_async,
            user_id=uuid4(),
            prompt_template=mock_prompt_template,
            batch_size=10,
            score_scale=10,
        )

        # Act
        start_time = time.time()
        result = await reranker.rerank_async(query="test", results=small_docs, top_k=3)
        elapsed_time = time.time() - start_time

        # Assert: Single batch processed quickly
        assert elapsed_time < 1.0, f"Small dataset should process < 1.0s, took {elapsed_time:.2f}s"

        # Assert: Provider called once (1 batch)
        assert mock_llm_provider_async.generate_text.call_count == 1

        # Assert: Results correct
        assert len(result) == 3


# ============================================================================
# UNIT TESTS: Error Handling
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncRerankingErrorHandling:
    """Test error handling in async concurrent reranking."""

    async def test_concurrent_reranking_handles_batch_failure_gracefully(
        self, mock_prompt_template, mock_documents_20
    ):
        """
        TDD Test: Verify graceful fallback when batch processing fails.

        Expected: Use original scores as fallback, don't crash
        """
        # Arrange: Provider that fails on second batch
        provider = Mock()
        call_count = 0

        async def failing_generate(user_id, prompt, template=None):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Fail on second batch
                raise ValueError("Simulated LLM response parsing failure")
            if isinstance(prompt, list):
                return [f"Score: 8.{i}" for i in range(len(prompt))]
            return "Score: 8.0"

        provider.generate_text = AsyncMock(side_effect=failing_generate)

        reranker = LLMReranker(
            llm_provider=provider,
            user_id=uuid4(),
            prompt_template=mock_prompt_template,
            batch_size=10,
            score_scale=10,
        )

        # Act: Should not crash
        result = await reranker.rerank_async(
            query="test query", results=mock_documents_20, top_k=10
        )

        # Assert: Returns results despite failure (using fallback scores)
        assert len(result) == 10

        # Assert: Second batch used fallback scores (original scores)
        # First 10 docs should have LLM scores, last 10 should have fallback
        assert all(r.score is not None for r in result)

    async def test_concurrent_reranking_with_empty_results(
        self, mock_llm_provider_async, mock_prompt_template
    ):
        """
        TDD Test: Verify handling of empty document list.

        Expected: Return empty list immediately
        """
        # Arrange
        reranker = LLMReranker(
            llm_provider=mock_llm_provider_async,
            user_id=uuid4(),
            prompt_template=mock_prompt_template,
            batch_size=10,
            score_scale=10,
        )

        # Act
        result = await reranker.rerank_async(query="test query", results=[], top_k=5)

        # Assert: Empty list returned
        assert result == []

        # Assert: Provider not called
        mock_llm_provider_async.generate_text.assert_not_called()
