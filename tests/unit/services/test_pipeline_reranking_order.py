"""
Unit tests for P0-2: Pipeline Reranking Order Bug

Testing: Issue #543 - Reranking should happen BEFORE LLM generation, not after

Test Cases:
1. Reranking happens before context formatting
2. Reranking happens before LLM generation
3. LLM receives reranked documents, not raw retrieval results
4. Reranking is skipped when disabled
5. Reranking respects top_k configuration

Expected Flow:
  Retrieval (20 docs) → Reranking (top 5) → Context Format → LLM Generation (5 docs)

Current (Buggy) Flow:
  Retrieval (20 docs) → Context Format → LLM Generation (20 docs) → Reranking (too late)
"""

from datetime import UTC, datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.schemas.prompt_template_schema import PromptTemplateOutput, PromptTemplateType
from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.pipeline_service import PipelineService
from vectordbs.data_types import DocumentChunk, DocumentChunkMetadata, QueryResult, Source

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def mock_settings():
    """Mock settings with reranking enabled."""
    settings = Mock(spec=Settings)
    settings.vector_db = "milvus"
    settings.number_of_results = 20  # Retrieve 20 docs initially
    settings.enable_reranking = True  # ENABLED
    settings.reranker_top_k = 5  # Rerank to top 5
    settings.reranker_type = "llm"
    settings.runtime_eval = False
    settings.retrieval_type = "vector"
    settings.max_context_length = 2048
    settings.hierarchical_retrieval_mode = "child_only"
    return settings


@pytest.fixture
def mock_settings_reranking_disabled():
    """Mock settings with reranking disabled."""
    settings = Mock(spec=Settings)
    settings.vector_db = "milvus"
    settings.number_of_results = 20
    settings.enable_reranking = False  # DISABLED
    settings.reranker_top_k = None
    settings.runtime_eval = False
    settings.retrieval_type = "vector"
    settings.max_context_length = 2048
    settings.hierarchical_retrieval_mode = "child_only"
    return settings


@pytest.fixture
def mock_vector_store():
    """Mock vector store that returns 20 documents."""
    # Create 20 mock documents
    mock_results = []
    for i in range(20):
        metadata = DocumentChunkMetadata(
            document_id=f"doc_{i}",
            chunk_index=0,
            total_chunks=1,
            source=Source.OTHER,
        )
        chunk = DocumentChunk(
            id=f"chunk_{i}",
            text=f"This is document {i} content with relevant information.",
            metadata=metadata,
        )
        result = QueryResult(
            chunk=chunk,
            score=0.9 - (i * 0.01),  # Descending scores
            collection_id="test_collection",
        )
        mock_results.append(result)

    mock = Mock()
    mock.search = Mock(return_value=mock_results)
    return mock


@pytest.fixture
def mock_rag_template():
    """Mock RAG template."""
    now = datetime.now(UTC)
    return PromptTemplateOutput(
        id=uuid4(),
        name="test-template",
        user_id=uuid4(),
        template_type=PromptTemplateType.RAG_QUERY,
        system_prompt="You are a helpful assistant.",
        template_format="{context}\n\n{question}",
        input_variables={"context": "context", "question": "question"},
        example_inputs={"context": "example", "question": "example"},
        is_default=True,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def search_input():
    """Mock search input."""
    return SearchInput(
        question="What is machine learning?",
        collection_id=uuid4(),
        user_id=uuid4(),
    )


# ============================================================================
# TEST: Reranking Order Verification
# ============================================================================


@pytest.mark.unit
class TestRerankingOrder:
    """Test that reranking happens BEFORE LLM generation."""

    async def test_reranking_called_before_llm_generation(
        self, mock_db, mock_settings, mock_vector_store, mock_rag_template, search_input
    ):
        """
        TDD Test: Verify reranking happens BEFORE LLM generation.

        Expected Order:
          1. _retrieve_documents() -> 20 docs
          2. _apply_reranking() -> 5 docs (top-k)
          3. _format_context() -> uses 5 reranked docs
          4. _generate_answer() -> generates from 5 reranked docs

        This test FAILS initially because reranking doesn't happen in execute_pipeline.
        """
        # Arrange: Mock reranker that returns top 5
        mock_reranker = Mock()
        mock_reranker.rerank = Mock(side_effect=lambda query, results, top_k: results[:5])  # noqa: ARG005

        with (
            patch("rag_solution.services.pipeline_service.VectorStoreFactory.get_datastore") as mock_factory,
            patch.object(PipelineService, "_validate_configuration") as mock_validate,
            patch.object(PipelineService, "_get_templates") as mock_get_templates,
            patch.object(PipelineService, "_prepare_query") as mock_prepare,
            patch.object(PipelineService, "_retrieve_documents") as mock_retrieve,
            patch.object(PipelineService, "_format_context") as mock_format_context,
            patch.object(PipelineService, "_generate_answer") as mock_generate,
        ):
            # Setup mocks
            mock_factory.return_value = mock_vector_store
            mock_validate.return_value = (Mock(), Mock(), Mock())
            mock_get_templates.return_value = (mock_rag_template, None)
            mock_prepare.return_value = "cleaned query"
            # Return 20 documents from vector store
            mock_retrieve.return_value = mock_vector_store.search.return_value
            mock_format_context.return_value = "formatted context"
            mock_generate.return_value = "Generated answer"

            # Create service
            service = PipelineService(mock_db, mock_settings)
            service.query_rewriter = Mock()
            service.query_rewriter.rewrite = Mock(return_value="rewritten query")

            # Patch instance method AFTER service creation
            service.get_reranker = Mock(return_value=mock_reranker)

            # Act
            result = await service.execute_pipeline(
                search_input=search_input,
                collection_name="test_collection",
                pipeline_id=uuid4(),
            )

            # Assert: Reranker was called
            mock_reranker.rerank.assert_called_once()

            # Assert: _format_context received 5 reranked results, not 20 raw results
            mock_format_context.assert_called_once()
            call_args = mock_format_context.call_args
            results_passed_to_format = call_args[0][1]  # Second positional arg

            assert len(results_passed_to_format) == 5, (
                f"_format_context should receive 5 reranked docs, got {len(results_passed_to_format)}"
            )

            # Assert: Result contains reranked query results (5, not 20)
            assert len(result.query_results) == 5, "Should have 5 reranked results, not 20"

    async def test_llm_receives_reranked_documents(
        self, mock_db, mock_settings, mock_vector_store, mock_rag_template, search_input
    ):
        """
        TDD Test: Verify LLM generation receives context from reranked docs, not raw retrieval.

        Expected: _format_context should receive 3 reranked docs, not 20 raw docs.

        This test FAILS initially because _format_context gets all 20 retrieved docs.
        """
        # Arrange: Mock reranker that returns top 3 with distinct IDs
        mock_reranker = Mock()

        def rerank_to_top_3(query: str, results: list[QueryResult], top_k: int | None = None) -> list[QueryResult]:
            # Return only top 3 documents (don't modify chunk IDs - just return subset)
            return results[:3]

        mock_reranker.rerank = Mock(side_effect=rerank_to_top_3)

        with (
            patch("rag_solution.services.pipeline_service.VectorStoreFactory.get_datastore") as mock_factory,
            patch.object(PipelineService, "_validate_configuration") as mock_validate,
            patch.object(PipelineService, "_get_templates") as mock_get_templates,
            patch.object(PipelineService, "_prepare_query") as mock_prepare,
            patch.object(PipelineService, "_retrieve_documents") as mock_retrieve,
            patch.object(PipelineService, "_format_context") as mock_format_context,
            patch.object(PipelineService, "_generate_answer") as mock_generate,
        ):
            # Setup mocks
            mock_factory.return_value = mock_vector_store
            mock_validate.return_value = (Mock(), Mock(), Mock())
            mock_get_templates.return_value = (mock_rag_template, None)
            mock_prepare.return_value = "cleaned query"
            mock_retrieve.return_value = mock_vector_store.search.return_value
            mock_format_context.return_value = "formatted context"
            mock_generate.return_value = "Generated answer"

            # Create service
            service = PipelineService(mock_db, mock_settings)
            service.query_rewriter = Mock()
            service.query_rewriter.rewrite = Mock(return_value="rewritten query")

            # Patch instance method AFTER service creation
            service.get_reranker = Mock(return_value=mock_reranker)

            # Act
            await service.execute_pipeline(
                search_input=search_input,
                collection_name="test_collection",
                pipeline_id=uuid4(),
            )

            # Assert: Reranker was called
            mock_reranker.rerank.assert_called_once()

            # Assert: _format_context received exactly 3 reranked results
            mock_format_context.assert_called_once()
            call_args = mock_format_context.call_args
            results_passed_to_format = call_args[0][1]  # Second positional arg is query_results

            assert len(results_passed_to_format) == 3, (
                f"_format_context should receive 3 reranked docs, got {len(results_passed_to_format)}"
            )

    async def test_reranking_respects_top_k_config(
        self, mock_db, mock_settings, mock_vector_store, mock_rag_template, search_input
    ):
        """
        TDD Test: Verify reranking uses the configured top_k value.

        Expected: If settings.reranker_top_k = 5, reranker should be called with top_k=5.

        This test FAILS initially because reranking doesn't use top_k from settings.
        """
        # Arrange
        reranker_top_k_used = None
        mock_reranker = Mock()

        def track_top_k(query: str, results: list[QueryResult], top_k: int | None = None) -> list[QueryResult]:
            nonlocal reranker_top_k_used
            reranker_top_k_used = top_k
            return results[: (top_k if top_k else len(results))]

        mock_reranker.rerank = Mock(side_effect=track_top_k)

        with (
            patch("rag_solution.services.pipeline_service.VectorStoreFactory.get_datastore") as mock_factory,
            patch.object(PipelineService, "_validate_configuration") as mock_validate,
            patch.object(PipelineService, "_get_templates") as mock_get_templates,
            patch.object(PipelineService, "_prepare_query") as mock_prepare,
            patch.object(PipelineService, "_retrieve_documents") as mock_retrieve,
            patch.object(PipelineService, "_format_context") as mock_format_context,
            patch.object(PipelineService, "_generate_answer") as mock_generate,
        ):
            # Setup mocks
            mock_factory.return_value = mock_vector_store
            mock_validate.return_value = (Mock(), Mock(), Mock())
            mock_get_templates.return_value = (mock_rag_template, None)
            mock_prepare.return_value = "cleaned query"
            mock_retrieve.return_value = mock_vector_store.search.return_value
            mock_format_context.return_value = "formatted context"
            mock_generate.return_value = "Generated answer"

            # Create service with top_k = 5
            mock_settings.reranker_top_k = 5
            service = PipelineService(mock_db, mock_settings)
            service.query_rewriter = Mock()
            service.query_rewriter.rewrite = Mock(return_value="rewritten query")

            # Patch instance method AFTER service creation
            service.get_reranker = Mock(return_value=mock_reranker)

            # Act
            await service.execute_pipeline(
                search_input=search_input,
                collection_name="test_collection",
                pipeline_id=uuid4(),
            )

            # Assert: Reranker was called with top_k=5
            assert reranker_top_k_used == 5, f"Reranker should use top_k=5, got {reranker_top_k_used}"


    async def test_reranking_skipped_when_disabled(
        self, mock_db, mock_settings_reranking_disabled, mock_vector_store, mock_rag_template, search_input
    ):
        """
        TDD Test: Verify reranking is skipped when enable_reranking=False.

        Expected: If settings.enable_reranking = False, reranker should not be called.

        This test should PASS even before the fix (validates skip logic).
        """
        # Arrange
        mock_reranker = Mock()
        mock_reranker.rerank = Mock(return_value=[])

        with (
            patch("rag_solution.services.pipeline_service.VectorStoreFactory.get_datastore") as mock_factory,
            patch.object(PipelineService, "_validate_configuration") as mock_validate,
            patch.object(PipelineService, "_get_templates") as mock_get_templates,
            patch.object(PipelineService, "_prepare_query") as mock_prepare,
            patch.object(PipelineService, "_retrieve_documents") as mock_retrieve,
            patch.object(PipelineService, "_format_context") as mock_format_context,
            patch.object(PipelineService, "_generate_answer") as mock_generate,
        ):
            # Setup mocks
            mock_factory.return_value = mock_vector_store
            mock_validate.return_value = (Mock(), Mock(), Mock())
            mock_get_templates.return_value = (mock_rag_template, None)
            mock_prepare.return_value = "cleaned query"
            mock_retrieve.return_value = mock_vector_store.search.return_value
            mock_format_context.return_value = "formatted context"
            mock_generate.return_value = "Generated answer"

            # Create service with reranking DISABLED
            service = PipelineService(mock_db, mock_settings_reranking_disabled)
            service.query_rewriter = Mock()
            service.query_rewriter.rewrite = Mock(return_value="rewritten query")

            # Patch instance method AFTER service creation to verify it's NOT called
            mock_get_reranker = Mock(return_value=None)
            service.get_reranker = mock_get_reranker

            # Act
            await service.execute_pipeline(
                search_input=search_input,
                collection_name="test_collection",
                pipeline_id=uuid4(),
            )

            # Assert: get_reranker was NOT called (early return when enable_reranking=False)
            mock_get_reranker.assert_not_called()

            # Assert: Reranker.rerank was NOT called
            mock_reranker.rerank.assert_not_called()

            # Assert: _format_context received all 20 raw results (no reranking)
            mock_format_context.assert_called_once()
            call_args = mock_format_context.call_args
            results_passed = call_args[0][1]
            assert len(results_passed) == 20, "Should have all 20 raw results when reranking disabled"
