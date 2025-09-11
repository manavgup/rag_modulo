"""
Real TDD tests for SearchService - testing actual functionality to find real bugs.

These tests call the real SearchService and will fail until the implementation
is correct. This is what TDD should actually do.
"""

import pytest
from uuid import uuid4, UUID
from unittest.mock import Mock
from sqlalchemy.orm import Session

from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.services.search_service import SearchService
from core.config import Settings


@pytest.mark.e2e
class TestSearchServiceReal:
    """Test real SearchService functionality to find actual bugs."""
    
    @pytest.fixture
    def search_service(self, mock_settings: Settings) -> SearchService:
        """Create a real SearchService with mock database."""
        mock_db = Mock(spec=Session)
        return SearchService(mock_db, mock_settings)
    
    def test_search_service_initialization(self, search_service: SearchService):
        """Test that SearchService initializes correctly."""
        assert search_service is not None
        assert hasattr(search_service, 'search')
        assert hasattr(search_service, 'db')
        assert hasattr(search_service, 'settings')
    
    @pytest.mark.asyncio
    async def test_search_with_empty_query(self, search_service: SearchService):
        """Test search with empty query - should validate input."""
        search_input = SearchInput(
            question="",  # Empty query
            collection_id=uuid4(),
            pipeline_id=uuid4(),
            user_id=uuid4()
        )
        
        # Should raise validation error
        with pytest.raises(Exception) as exc_info:
            await search_service.search(search_input)
        
        # Error should be about empty query
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in ['empty', 'query', 'validation'])
    
    @pytest.mark.asyncio
    async def test_search_with_none_query(self, search_service: SearchService):
        """Test search with None query - should validate input."""
        search_input = SearchInput(
            question=None,  # None query
            collection_id=uuid4(),
            pipeline_id=uuid4(),
            user_id=uuid4()
        )
        
        # Should raise validation error
        with pytest.raises(Exception) as exc_info:
            await search_service.search(search_input)
        
        # Error should be about invalid query
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in ['none', 'null', 'validation'])
    
    @pytest.mark.asyncio
    async def test_search_with_whitespace_only_query(self, search_service: SearchService):
        """Test search with whitespace-only query - should validate input."""
        search_input = SearchInput(
            question="   \n\t   ",  # Whitespace only
            collection_id=uuid4(),
            pipeline_id=uuid4(),
            user_id=uuid4()
        )
        
        # Should raise validation error
        with pytest.raises(Exception) as exc_info:
            await search_service.search(search_input)
        
        # Error should be about empty query
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in ['empty', 'query', 'validation'])
    
    @pytest.mark.asyncio
    async def test_search_with_invalid_collection_id(self, search_service: SearchService):
        """Test search with invalid collection ID - should handle gracefully."""
        search_input = SearchInput(
            question="What is machine learning?",
            collection_id=uuid4(),  # Random UUID that doesn't exist
            pipeline_id=uuid4(),
            user_id=uuid4()
        )
        
        # Should raise not found error
        with pytest.raises(Exception) as exc_info:
            await search_service.search(search_input)
        
        # Error should be about collection not found
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in ['not found', 'collection', '404'])
    
    @pytest.mark.asyncio
    async def test_search_with_invalid_pipeline_id(self, search_service: SearchService):
        """Test search with invalid pipeline ID - should handle gracefully."""
        search_input = SearchInput(
            question="What is machine learning?",
            collection_id=uuid4(),
            pipeline_id=uuid4(),  # Random UUID that doesn't exist
            user_id=uuid4()
        )
        
        # Should raise not found error
        with pytest.raises(Exception) as exc_info:
            await search_service.search(search_input)
        
        # Error should be about pipeline not found
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in ['not found', 'pipeline', '404'])
    
    @pytest.mark.asyncio
    async def test_search_with_valid_input_but_missing_infrastructure(self, search_service: SearchService):
        """Test search with valid input but missing infrastructure (Milvus, etc.)."""
        search_input = SearchInput(
            question="What is machine learning?",
            collection_id=uuid4(),
            pipeline_id=uuid4(),
            user_id=uuid4()
        )
        
        # Should fail due to infrastructure (Milvus connection, etc.)
        with pytest.raises(Exception) as exc_info:
            await search_service.search(search_input)
        
        # Error should be about infrastructure
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in ['milvus', 'connection', 'database', 'vector'])
    
    def test_search_input_schema_validation(self):
        """Test SearchInput schema validation."""
        # Valid input should work
        valid_input = SearchInput(
            question="What is machine learning?",
            collection_id=uuid4(),
            pipeline_id=uuid4(),
            user_id=uuid4()
        )
        assert valid_input.question == "What is machine learning?"
        
        # Invalid input should raise validation error
        with pytest.raises(Exception):
            SearchInput(
                question=None,  # Invalid
                collection_id=uuid4(),
                pipeline_id=uuid4(),
                user_id=uuid4()
            )
    
    def test_search_output_schema_validation(self):
        """Test SearchOutput schema validation."""
        # Valid output should work
        output = SearchOutput(
            answer="Machine learning is a subset of AI",
            documents=[],
            query_results=[],
            rewritten_query="What is machine learning?",
            evaluation={"score": 0.9}
        )
        
        assert output.answer == "Machine learning is a subset of AI"
        assert output.documents == []
        assert output.query_results == []
        assert output.rewritten_query == "What is machine learning?"
        assert output.evaluation == {"score": 0.9}
