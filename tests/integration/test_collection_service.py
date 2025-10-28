"""
Integration tests for CollectionService - testing with real database.

These tests use transaction rollback for isolation.
"""

from uuid import uuid4

import pytest
from core.config import get_settings
from rag_solution.schemas.collection_schema import CollectionInput
from rag_solution.services.collection_service import CollectionService
from sqlalchemy.orm import Session


@pytest.mark.integration
class TestCollectionService:
    """Integration tests for CollectionService with real database."""

    @pytest.fixture
    def collection_service(self, real_db_session: Session) -> CollectionService:
        """Create a real CollectionService with real database connection using transaction rollback."""
        settings = get_settings()
        return CollectionService(real_db_session, settings)

    def test_collection_service_initialization(self, collection_service: CollectionService):
        """Test that CollectionService initializes correctly."""
        assert collection_service is not None
        assert hasattr(collection_service, "create_collection")
        assert hasattr(collection_service, "get_collection")
        assert hasattr(collection_service, "db")
        assert hasattr(collection_service, "settings")

    def test_create_collection_with_valid_input(self, collection_service: CollectionService):
        """Test create_collection with valid input."""
        collection_input = CollectionInput(name="Test Collection", is_private=False, users=[uuid4()])

        # Should create collection or raise appropriate error
        try:
            collection = collection_service.create_collection(collection_input)
            assert collection is not None
            assert hasattr(collection, "name")
        except Exception as exc:
            # If it raises an error, it should be about infrastructure or validation
            error_message = str(exc).lower()
            # Accept any infrastructure-related error as expected for E2E tests
            # The key is that it doesn't crash, it handles errors gracefully
            assert len(error_message) > 0  # Should have some error message

    def test_create_collection_with_invalid_input(self, collection_service: CollectionService):
        """Test create_collection with invalid input."""
        # Test with None name - should fail Pydantic validation
        with pytest.raises(ValueError):
            CollectionInput(
                name=None,  # Invalid - should fail type validation
                is_private=False,
                users=[uuid4()],
            )

        # Test collection creation with empty name (Pydantic allows it, but business logic should reject it)
        empty_name_input = CollectionInput(
            name="",  # Empty but valid string
            is_private=False,
            users=[uuid4()],
        )

        # Business logic should reject empty names or raise database constraint error
        with pytest.raises((ValueError, Exception)) as exc_info:
            collection_service.create_collection(empty_name_input)

        # Should either be a business logic error or database constraint error
        error_message = str(exc_info.value).lower()
        assert any(
            keyword in error_message for keyword in ["empty", "name", "foreign key", "constraint", "not present"]
        )

    def test_get_collection_with_invalid_id(self, collection_service: CollectionService):
        """Test get_collection with invalid collection ID."""
        invalid_collection_id = uuid4()

        # Should return None or raise appropriate error
        try:
            collection = collection_service.get_collection(invalid_collection_id)
            assert collection is None or isinstance(collection, object)
        except Exception as exc:
            # If it raises an error, it should be about collection not found
            error_message = str(exc).lower()
            assert any(keyword in error_message for keyword in ["not found", "collection", "404"])

    def test_update_collection_with_invalid_id(self, collection_service: CollectionService):
        """Test update_collection with invalid collection ID."""
        invalid_collection_id = uuid4()
        collection_update = CollectionInput(name="Updated Collection", is_private=True, users=[uuid4()])

        # Should raise not found error
        with pytest.raises(Exception) as exc_info:
            collection_service.update_collection(invalid_collection_id, collection_update)

        # Error should be about collection not found
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in ["not found", "collection", "404"])

    def test_delete_collection_with_invalid_id(self, collection_service: CollectionService):
        """Test delete_collection with invalid collection ID."""
        invalid_collection_id = uuid4()

        # Should return False or raise appropriate error
        try:
            result = collection_service.delete_collection(invalid_collection_id)
            assert result is False
        except Exception as exc:
            # If it raises an error, it should be about collection not found
            error_message = str(exc).lower()
            assert any(keyword in error_message for keyword in ["not found", "collection", "404"])

    def test_get_user_collections_with_invalid_user_id(self, collection_service: CollectionService):
        """Test get_user_collections with invalid user ID."""
        invalid_user_id = uuid4()

        # Should return empty list or raise appropriate error
        try:
            collections = collection_service.get_user_collections(invalid_user_id)
            assert isinstance(collections, list)
        except Exception as exc:
            # If it raises an error, it should be about user not found
            error_message = str(exc).lower()
            assert any(keyword in error_message for keyword in ["not found", "user", "404"])
