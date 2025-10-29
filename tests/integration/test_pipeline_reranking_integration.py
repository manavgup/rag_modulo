"""
Integration tests for Pipeline Reranking Order (Issue #543, PR #544).

Tests verify that reranking happens BEFORE LLM generation, not after.

Test Strategy:
- Use real PipelineService with real database
- Mock vector store to return controlled 20 documents
- Use SimpleReranker (no LLM needed) to rerank to top 5
- Track method calls to verify ordering
- Verify LLM receives exactly 5 reranked documents

Expected Flow:
  Retrieval (20 docs) → Reranking (top 5) → Context Format → LLM Generation (5 docs)

Buggy Flow (before fix):
  Retrieval (20 docs) → Context Format → LLM Generation (20 docs) → Reranking (too late)
"""

from datetime import UTC, datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from core.config import Settings, get_settings
from rag_solution.schemas.prompt_template_schema import PromptTemplateOutput, PromptTemplateType
from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.pipeline_service import PipelineService
from vectordbs.data_types import DocumentChunk, DocumentChunkMetadata, QueryResult, Source


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_vector_store_20_docs():
    """Mock vector store that returns 20 documents."""
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
            text=f"This is document {i} content with relevant information about the query topic.",
            metadata=metadata,
        )
        result = QueryResult(
            chunk=chunk,
            score=0.9 - (i * 0.01),  # Descending scores: 0.9, 0.89, 0.88, ...
            collection_id="test_collection",
        )
        mock_results.append(result)

    mock = Mock()
    mock.search = Mock(return_value=mock_results)
    return mock


@pytest.fixture
def mock_rag_template():
    """Mock RAG template for testing."""
    now = datetime.now(UTC)
    return PromptTemplateOutput(
        id=uuid4(),
        name="test-rag-template",
        user_id=uuid4(),
        template_type=PromptTemplateType.RAG_QUERY,
        system_prompt="You are a helpful assistant.",
        template_format="{context}\n\n{question}",
        input_variables={"context": "context", "question": "question"},
        example_inputs={"context": "example context", "question": "example question"},
        is_default=True,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def settings_with_reranking():
    """Settings with reranking enabled."""
    settings = get_settings()
    settings.enable_reranking = True
    settings.reranker_type = "simple"  # Use SimpleReranker (no LLM needed)
    settings.reranker_top_k = 5  # Rerank to top 5
    settings.number_of_results = 20  # Retrieve 20 initially
    return settings


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


@pytest.mark.integration
class TestPipelineRerankingOrder:
    """Integration tests verifying reranking happens BEFORE LLM generation."""

    @pytest.fixture
    def pipeline_service(self, real_db_session: Session, settings_with_reranking: Settings) -> PipelineService:
        """Create PipelineService with real database and reranking enabled."""
        return PipelineService(real_db_session, settings_with_reranking)

    @pytest.mark.asyncio
    async def test_reranking_happens_before_llm_generation_integration(
        self,
        pipeline_service: PipelineService,
        mock_vector_store_20_docs,
        mock_rag_template,
    ):
        """
        Integration Test: Verify reranking reduces 20 docs to 5 BEFORE LLM sees them.

        Flow:
          1. Vector store returns 20 documents
          2. Reranking reduces to 5 documents
          3. Context formatter receives 5 documents
          4. LLM generation receives 5 documents

        This test verifies the P0-2 fix is working end-to-end.
        """
        # Arrange
        search_input = SearchInput(
            question="What is machine learning and how does it work?",
            collection_id=uuid4(),
            user_id=uuid4(),
        )

        # Track what _format_context receives
        format_context_docs_count = None

        def track_format_context(template_id, query_results):
            nonlocal format_context_docs_count
            format_context_docs_count = len(query_results)
            return "Formatted context with relevant information"

        with (
            patch.object(PipelineService, "_validate_configuration") as mock_validate,
            patch.object(PipelineService, "_get_templates") as mock_get_templates,
            patch.object(PipelineService, "_prepare_query") as mock_prepare,
            patch.object(PipelineService, "_retrieve_documents") as mock_retrieve,
            patch.object(PipelineService, "_format_context") as mock_format_context,
            patch.object(PipelineService, "_generate_answer") as mock_generate,
        ):
            # Setup mocks
            mock_validate.return_value = (Mock(), Mock(), Mock())
            mock_get_templates.return_value = (mock_rag_template, None)
            mock_prepare.return_value = "prepared query"
            mock_retrieve.return_value = mock_vector_store_20_docs.search.return_value  # Return 20 docs
            mock_format_context.side_effect = track_format_context
            mock_generate.return_value = "Generated answer based on relevant documents"

            # Act
            result = await pipeline_service.execute_pipeline(
                search_input=search_input,
                collection_name="test_collection",
                pipeline_id=uuid4(),
            )

            # Assert: _retrieve_documents was called and returned 20 docs
            mock_retrieve.assert_called_once()

            # Assert: Context formatter received exactly 5 reranked documents (not 20)
            assert format_context_docs_count == 5, (
                f"Context formatter should receive 5 reranked docs, got {format_context_docs_count}"
            )

            # Assert: Result contains 5 reranked documents (not 20)
            assert len(result.query_results) == 5, (
                f"Pipeline result should have 5 reranked docs, got {len(result.query_results)}"
            )

            # Assert: Documents are the top-scored ones (SimpleReranker keeps highest scores)
            assert all(r.score >= 0.85 for r in result.query_results), (
                "Reranked results should have high scores (top 5)"
            )

    @pytest.mark.asyncio
    async def test_reranking_called_exactly_once_integration(
        self,
        pipeline_service: PipelineService,
        mock_vector_store_20_docs,
        mock_rag_template,
    ):
        """
        Integration Test: Verify reranking is called exactly ONCE (no double-reranking).

        Before P0-2 fix: Reranking happened in both PipelineService AND SearchService.
        After P0-2 fix: Reranking happens ONLY in PipelineService.

        This test ensures we don't have double-reranking bugs.
        """
        # Arrange
        search_input = SearchInput(
            question="Explain neural networks",
            collection_id=uuid4(),
            user_id=uuid4(),
        )

        rerank_call_count = 0

        def track_rerank_calls(query, results, top_k=None):
            nonlocal rerank_call_count
            rerank_call_count += 1
            # SimpleReranker just returns top results by score
            return results[:5]

        with (
            patch.object(PipelineService, "_validate_configuration") as mock_validate,
            patch.object(PipelineService, "_get_templates") as mock_get_templates,
            patch.object(PipelineService, "_prepare_query") as mock_prepare,
            patch.object(PipelineService, "_retrieve_documents") as mock_retrieve,
            patch.object(PipelineService, "_format_context") as mock_format_context,
            patch.object(PipelineService, "_generate_answer") as mock_generate,
            patch("rag_solution.retrieval.reranker.SimpleReranker.rerank") as mock_rerank,
        ):
            # Setup mocks
            mock_validate.return_value = (Mock(), Mock(), Mock())
            mock_get_templates.return_value = (mock_rag_template, None)
            mock_prepare.return_value = "prepared query"
            mock_retrieve.return_value = mock_vector_store_20_docs.search.return_value  # Return 20 docs
            mock_format_context.return_value = "formatted context"
            mock_generate.return_value = "generated answer"
            mock_rerank.side_effect = track_rerank_calls

            # Act
            await pipeline_service.execute_pipeline(
                search_input=search_input,
                collection_name="test_collection",
                pipeline_id=uuid4(),
            )

            # Assert: Reranker.rerank was called exactly ONCE
            assert rerank_call_count == 1, (
                f"Reranker.rerank should be called exactly once, got {rerank_call_count} calls"
            )

            # Assert: Reranker was called with all 20 documents
            call_args = mock_rerank.call_args
            assert call_args is not None, "Reranker was not called"
            # Access results from keyword arguments
            results_arg = call_args.kwargs.get("results") or call_args[0][1]  # Try kwargs first, then positional
            assert len(results_arg) == 20, (
                f"Reranker should receive 20 retrieved docs, got {len(results_arg)}"
            )

    @pytest.mark.asyncio
    async def test_reranking_disabled_skips_reranking_integration(
        self,
        real_db_session: Session,
        mock_vector_store_20_docs,
        mock_rag_template,
    ):
        """
        Integration Test: When reranking is disabled, all 20 docs pass through.

        Verifies that the reranking pipeline stage can be disabled cleanly.
        """
        # Arrange: Settings with reranking DISABLED
        settings = get_settings()
        settings.enable_reranking = False
        settings.number_of_results = 20

        pipeline_service = PipelineService(real_db_session, settings)

        search_input = SearchInput(
            question="What is deep learning?",
            collection_id=uuid4(),
            user_id=uuid4(),
        )

        format_context_docs_count = None

        def track_format_context(template_id, query_results):
            nonlocal format_context_docs_count
            format_context_docs_count = len(query_results)
            return "Formatted context"

        with (
            patch.object(PipelineService, "_validate_configuration") as mock_validate,
            patch.object(PipelineService, "_get_templates") as mock_get_templates,
            patch.object(PipelineService, "_prepare_query") as mock_prepare,
            patch.object(PipelineService, "_retrieve_documents") as mock_retrieve,
            patch.object(PipelineService, "_format_context") as mock_format_context,
            patch.object(PipelineService, "_generate_answer") as mock_generate,
        ):
            # Setup mocks
            mock_validate.return_value = (Mock(), Mock(), Mock())
            mock_get_templates.return_value = (mock_rag_template, None)
            mock_prepare.return_value = "prepared query"
            mock_retrieve.return_value = mock_vector_store_20_docs.search.return_value  # Return 20 docs
            mock_format_context.side_effect = track_format_context
            mock_generate.return_value = "generated answer"

            # Act
            result = await pipeline_service.execute_pipeline(
                search_input=search_input,
                collection_name="test_collection",
                pipeline_id=uuid4(),
            )

            # Assert: Context formatter received all 20 documents (no reranking)
            assert format_context_docs_count == 20, (
                f"When reranking disabled, should pass all 20 docs, got {format_context_docs_count}"
            )

            # Assert: Result contains all 20 documents
            assert len(result.query_results) == 20, (
                f"When reranking disabled, should return all 20 docs, got {len(result.query_results)}"
            )
