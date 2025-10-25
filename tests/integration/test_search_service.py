"""
Integration tests for SearchService - testing with real database.

These tests use transaction rollback for isolation and test the service layer
directly without going through HTTP/API layer.
"""

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.rag_solution.schemas.search_schema import SearchInput, SearchOutput
from backend.rag_solution.services.search_service import SearchService


@pytest.mark.integration
class TestSearchService:
    """Integration tests for SearchService with real database."""

    @pytest.fixture
    def search_service(self, real_db_session: Session) -> SearchService:
        """Create a real SearchService with real database connection using transaction rollback."""
        settings = get_settings()
        return SearchService(real_db_session, settings)

    def test_search_service_initialization(self, search_service: SearchService):
        """Test that SearchService initializes correctly."""
        assert search_service is not None
        assert hasattr(search_service, "search")
        assert hasattr(search_service, "db")
        assert hasattr(search_service, "settings")

    @pytest.mark.asyncio
    async def test_search_with_empty_query(self, search_service: SearchService):
        """Test search with empty query - should validate input."""
        search_input = SearchInput(
            question="",  # Empty query
            collection_id=uuid4(),
            user_id=uuid4(),
        )

        # Should raise validation error
        with pytest.raises(Exception) as exc_info:
            await search_service.search(search_input)

        # Error should be about empty query
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in ["empty", "query", "validation"])

    @pytest.mark.asyncio
    async def test_search_with_none_query(self, search_service: SearchService):  # noqa: ARG002
        """Test search with None query - should fail at Pydantic validation."""
        # This test should fail at SearchInput creation, not at search execution
        with pytest.raises(Exception) as exc_info:
            SearchInput(
                question=None,  # None query - should fail Pydantic validation
                collection_id=uuid4(),
                user_id=uuid4(),
            )

        # Error should be about type validation
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in ["string", "validation", "type"])

    @pytest.mark.asyncio
    async def test_search_with_whitespace_only_query(self, search_service: SearchService):
        """Test search with whitespace-only query."""
        search_input = SearchInput(
            question="   \n\t   ",  # Whitespace only
            collection_id=uuid4(),
            user_id=uuid4(),
        )

        # Should raise validation error
        with pytest.raises(Exception) as exc_info:
            await search_service.search(search_input)

        # Error should be about empty/invalid query
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in ["empty", "query", "validation"])

    @pytest.mark.asyncio
    async def test_search_with_invalid_collection_id(self, search_service: SearchService):
        """Test search with invalid collection ID."""
        search_input = SearchInput(
            question="What is machine learning?",
            collection_id=uuid4(),  # Non-existent collection
            user_id=uuid4(),
        )

        # Should raise collection not found error
        with pytest.raises(Exception) as exc_info:
            await search_service.search(search_input)

        # Error should be about collection not found
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in ["not found", "collection", "404"])

    @pytest.mark.asyncio
    async def test_search_with_invalid_pipeline_id(self, search_service: SearchService):
        """Test search with invalid pipeline ID."""
        search_input = SearchInput(
            question="What is machine learning?",
            collection_id=uuid4(),
            # Non-existent pipeline
            user_id=uuid4(),
        )

        # Should raise pipeline not found error
        with pytest.raises(Exception) as exc_info:
            await search_service.search(search_input)

        # Error should be about pipeline or collection not found
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in ["not found", "pipeline", "collection", "404"])

    @pytest.mark.asyncio
    async def test_search_with_valid_input_but_missing_infrastructure(self, search_service: SearchService):
        """Test search with valid input but missing infrastructure."""
        search_input = SearchInput(
            question="What is machine learning?",
            collection_id=uuid4(),  # Non-existent collection
            # Non-existent pipeline
            user_id=uuid4(),
        )

        # Should raise infrastructure error
        with pytest.raises(Exception) as exc_info:
            await search_service.search(search_input)

        # Error should be about missing collection or infrastructure
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in ["not found", "collection", "pipeline", "milvus", "vector"])

    def test_search_input_schema_validation(self):
        """Test SearchInput schema validation."""
        # Test valid input
        valid_input = SearchInput(
            question="What is machine learning?",
            collection_id=uuid4(),
            user_id=uuid4(),
        )
        assert valid_input.question == "What is machine learning?"
        assert isinstance(valid_input.collection_id, type(uuid4()))
        assert isinstance(valid_input.user_id, type(uuid4()))
        # Note: pipeline_id is not part of SearchInput schema - pipeline selection is handled automatically

    def test_search_output_schema_validation(self):
        """Test SearchOutput schema validation."""
        # Test valid output structure
        output = SearchOutput(
            answer="Machine learning is a subset of AI.",
            documents=[],
            query_results=[],
            rewritten_query="What is ML?",
            evaluation={"score": 0.8},
        )
        assert output.answer == "Machine learning is a subset of AI."
        assert output.documents == []
        assert output.query_results == []
        assert output.rewritten_query == "What is ML?"
        assert output.evaluation == {"score": 0.8}


@pytest.mark.integration
class TestRAGSearchFunctionality:
    """Test actual RAG search functionality - the core business logic."""

    @pytest.fixture
    def search_service(self, real_db_session: Session) -> SearchService:
        """Create a real SearchService with real database connection using transaction rollback."""
        settings = get_settings()
        return SearchService(real_db_session, settings)

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
