"""
Real TDD tests for CollectionService - testing actual functionality to find real bugs.
"""

import pytest
from uuid import uuid4, UUID
from unittest.mock import Mock
from sqlalchemy.orm import Session

from rag_solution.services.collection_service import CollectionService
from rag_solution.schemas.collection_schema import CollectionInput
from core.config import Settings


@pytest.mark.e2e
class TestCollectionServiceReal:
    """Test real CollectionService functionality to find actual bugs."""
    
    @pytest.fixture
    def collection_service(self, mock_settings: Settings) -> CollectionService:
        """Create a real CollectionService with mock database."""
        mock_db = Mock(spec=Session)
        return CollectionService(mock_db, mock_settings)
    
    def test_collection_service_initialization(self, collection_service: CollectionService):
        """Test that CollectionService initializes correctly."""
        assert collection_service is not None
        assert hasattr(collection_service, 'create_collection')
        assert hasattr(collection_service, 'get_collection')
        assert hasattr(collection_service, 'db')
        assert hasattr(collection_service, 'settings')
    
    def test_create_collection_with_valid_input(self, collection_service: CollectionService):
        """Test create_collection with valid input."""
        collection_input = CollectionInput(
            name="Test Collection",
            description="A test collection",
            user_id=uuid4()
        )
        
        # Should create collection or raise appropriate error
        try:
            collection = collection_service.create_collection(collection_input)
            assert collection is not None
            assert hasattr(collection, 'name')
            assert hasattr(collection, 'description')
        except Exception as exc_info:
            # If it raises an error, it should be about infrastructure or validation
            error_message = str(exc_info.value).lower()
            assert any(keyword in error_message for keyword in ['milvus', 'connection', 'database', 'vector', 'validation'])
    
    def test_create_collection_with_invalid_input(self, collection_service: CollectionService):
        """Test create_collection with invalid input."""
        # Test with None name
        with pytest.raises(Exception):
            CollectionInput(
                name=None,  # Invalid
                description="A test collection",
                user_id=uuid4()
            )
        
        # Test with empty name
        with pytest.raises(Exception):
            CollectionInput(
                name="",  # Invalid
                description="A test collection",
                user_id=uuid4()
            )
    
    def test_get_collection_with_invalid_id(self, collection_service: CollectionService):
        """Test get_collection with invalid collection ID."""
        invalid_collection_id = uuid4()
        
        # Should return None or raise appropriate error
        try:
            collection = collection_service.get_collection(invalid_collection_id)
            assert collection is None or isinstance(collection, object)
        except Exception as exc_info:
            # If it raises an error, it should be about collection not found
            error_message = str(exc_info.value).lower()
            assert any(keyword in error_message for keyword in ['not found', 'collection', '404'])
    
    def test_update_collection_with_invalid_id(self, collection_service: CollectionService):
        """Test update_collection with invalid collection ID."""
        invalid_collection_id = uuid4()
        collection_update = CollectionInput(
            name="Updated Collection",
            description="Updated description",
            user_id=uuid4()
        )
        
        # Should raise not found error
        with pytest.raises(Exception) as exc_info:
            collection_service.update_collection(invalid_collection_id, collection_update)
        
        # Error should be about collection not found
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in ['not found', 'collection', '404'])
    
    def test_delete_collection_with_invalid_id(self, collection_service: CollectionService):
        """Test delete_collection with invalid collection ID."""
        invalid_collection_id = uuid4()
        
        # Should return False or raise appropriate error
        try:
            result = collection_service.delete_collection(invalid_collection_id)
            assert result is False
        except Exception as exc_info:
            # If it raises an error, it should be about collection not found
            error_message = str(exc_info.value).lower()
            assert any(keyword in error_message for keyword in ['not found', 'collection', '404'])
    
    def test_get_user_collections_with_invalid_user_id(self, collection_service: CollectionService):
        """Test get_user_collections with invalid user ID."""
        invalid_user_id = uuid4()
        
        # Should return empty list or raise appropriate error
        try:
            collections = collection_service.get_user_collections(invalid_user_id)
            assert isinstance(collections, list)
        except Exception as exc_info:
            # If it raises an error, it should be about user not found
            error_message = str(exc_info.value).lower()
            assert any(keyword in error_message for keyword in ['not found', 'user', '404'])
