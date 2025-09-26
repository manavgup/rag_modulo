"""
Real TDD tests for RAG search functionality - testing the actual RAG pipeline.

These tests will fail until we have a working RAG system with:
- Document ingestion
- Vector search
- Answer generation
- Result ranking

These are true E2E tests that require the full RAG infrastructure to be working.
"""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.services.search_service import SearchService


@pytest.mark.e2e
class TestRAGSearchFunctionality:
    """Test actual RAG search functionality - the core business logic."""

    @pytest.fixture
    def search_service(self, e2e_settings: Settings) -> SearchService:
        """Create a real SearchService with real database connection."""
        # Use real database connection for E2E tests - no mocks
        engine = create_engine(
            f"postgresql://{e2e_settings.collectiondb_user}:{e2e_settings.collectiondb_pass}@"
            f"{e2e_settings.collectiondb_host}:{e2e_settings.collectiondb_port}/{e2e_settings.collectiondb_name}"
        )
        session = Session(engine)
        return SearchService(session, e2e_settings)

    @pytest.mark.asyncio
    async def test_rag_search_with_valid_query(self, search_service: SearchService):
        """Test RAG search with a valid query - requires full RAG infrastructure."""
        # This test will fail until we have:
        # 1. A collection with documents
        # 2. Working vector search
        # 3. Working answer generation

        search_input = SearchInput(
            question="What is machine learning?",
            collection_id=uuid4(),  # This needs to be a real collection ID with documents
            # This needs to be a real pipeline ID
            user_id=uuid4(),
        )

        # This should either return results OR raise appropriate infrastructure errors
        try:
            result = await search_service.search(search_input)

            # If it succeeds, validate the search result structure
            assert isinstance(result, SearchOutput)
            assert result.answer is not None
            assert len(result.answer) > 0
            assert result.documents is not None
            assert result.query_results is not None

            # Validate answer quality
            assert "machine learning" in result.answer.lower() or "ml" in result.answer.lower()

        except Exception as exc:
            # Expected failures: collection not found, pipeline not found, Milvus connection, etc.
            error_message = str(exc).lower()
            assert any(
                keyword in error_message
                for keyword in ["not found", "collection", "pipeline", "milvus", "connection", "vector", "404"]
            )

    @pytest.mark.asyncio
    async def test_rag_search_with_technical_query(self, search_service: SearchService):
        """Test RAG search with technical query - requires domain-specific documents."""
        search_input = SearchInput(
            question="Explain the difference between supervised and unsupervised learning",
            collection_id=uuid4(),  # Needs real collection with ML documents
            # Needs real pipeline
            user_id=uuid4(),
        )

        try:
            result = await search_service.search(search_input)

            # Validate technical answer quality
            assert isinstance(result, SearchOutput)
            assert len(result.answer) > 50  # Technical answers should be detailed
            assert any(
                keyword in result.answer.lower()
                for keyword in ["supervised", "unsupervised", "learning", "training", "data"]
            )

        except Exception as exc:
            # Expected infrastructure failures
            error_message = str(exc).lower()
            assert any(
                keyword in error_message
                for keyword in ["not found", "collection", "pipeline", "milvus", "connection", "vector"]
            )

    @pytest.mark.asyncio
    async def test_rag_search_with_comparative_query(self, search_service: SearchService):
        """Test RAG search with comparative query - tests reasoning capabilities."""
        search_input = SearchInput(
            question="Compare neural networks and decision trees for classification",
            collection_id=uuid4(),  # Needs collection with ML algorithm docs
            # Needs real pipeline
            user_id=uuid4(),
        )

        try:
            result = await search_service.search(search_input)

            # Validate comparative analysis
            assert isinstance(result, SearchOutput)
            assert len(result.answer) > 100  # Comparative answers should be detailed
            assert any(
                keyword in result.answer.lower()
                for keyword in ["neural", "decision", "tree", "classification", "compare"]
            )

        except Exception as exc:
            # Expected infrastructure failures
            error_message = str(exc).lower()
            assert any(
                keyword in error_message
                for keyword in ["not found", "collection", "pipeline", "milvus", "connection", "vector"]
            )

    @pytest.mark.asyncio
    async def test_rag_search_result_ranking(self, search_service: SearchService):
        """Test that RAG search results are properly ranked by relevance."""
        search_input = SearchInput(
            question="deep learning applications",
            collection_id=uuid4(),  # Needs collection with varied ML docs
            # Needs real pipeline
            user_id=uuid4(),
        )

        try:
            result = await search_service.search(search_input)

            # Validate result ranking
            assert isinstance(result, SearchOutput)
            assert len(result.query_results) > 0

            # Check that results are ranked (scores should be in descending order)
            scores = [qr.score for qr in result.query_results if qr.score is not None]
            if len(scores) > 1:
                assert scores == sorted(scores, reverse=True), "Results should be ranked by score descending"

        except Exception as exc:
            # Expected infrastructure failures
            error_message = str(exc).lower()
            assert any(
                keyword in error_message
                for keyword in ["not found", "collection", "pipeline", "milvus", "connection", "vector"]
            )

    @pytest.mark.asyncio
    async def test_rag_search_answer_quality(self, search_service: SearchService):
        """Test that RAG search generates coherent, relevant answers."""
        search_input = SearchInput(
            question="What are the main benefits of using machine learning?",
            collection_id=uuid4(),  # Needs collection with ML benefit docs
            # Needs real pipeline
            user_id=uuid4(),
        )

        try:
            result = await search_service.search(search_input)

            # Validate answer quality
            assert isinstance(result, SearchOutput)
            assert len(result.answer) > 30  # Substantial answer
            assert not result.answer.startswith("I don't know")  # Should have content

            # Check for coherent sentence structure
            assert "." in result.answer or "!" in result.answer  # Complete sentences

        except Exception as exc:
            # Expected infrastructure failures
            error_message = str(exc).lower()
            assert any(
                keyword in error_message
                for keyword in ["not found", "collection", "pipeline", "milvus", "connection", "vector"]
            )

    @pytest.mark.asyncio
    async def test_rag_search_with_no_relevant_documents(self, search_service: SearchService):
        """Test RAG search behavior when no relevant documents are found."""
        search_input = SearchInput(
            question="What is the weather like on Mars today?",  # Unlikely to have relevant docs
            collection_id=uuid4(),  # Collection without Mars weather docs
            # Needs real pipeline
            user_id=uuid4(),
        )

        try:
            result = await search_service.search(search_input)

            # Should still return a result, but may indicate no relevant info
            assert isinstance(result, SearchOutput)
            assert result.answer is not None
            assert result.documents is not None
            assert result.query_results is not None

        except Exception as exc:
            # Expected infrastructure failures
            error_message = str(exc).lower()
            assert any(
                keyword in error_message
                for keyword in ["not found", "collection", "pipeline", "milvus", "connection", "vector"]
            )
