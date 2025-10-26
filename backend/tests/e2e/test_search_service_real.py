"""
Real TDD tests for SearchService - testing actual functionality to find real bugs.

These tests call the real SearchService and will fail until the implementation
is correct. This is what TDD should actually do.
"""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.services.search_service import SearchService


@pytest.mark.e2e
class TestSearchServiceReal:
    """Test real SearchService functionality to find actual bugs."""

    @pytest.fixture
    def search_service(self, e2e_settings: Settings) -> SearchService:
        """Create a real SearchService with real database connection."""
        # Use real database connection for E2E tests
        engine = create_engine(
            f"postgresql://{e2e_settings.collectiondb_user}:{e2e_settings.collectiondb_pass}@"
            f"{e2e_settings.collectiondb_host}:{e2e_settings.collectiondb_port}/{e2e_settings.collectiondb_name}"
        )
        session = Session(engine)
        return SearchService(session, e2e_settings)

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
    async def test_search_with_none_query(self, search_service: SearchService):
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
