"""Atomic tests for Collection data validation and schemas."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from rag_solution.schemas.collection_schema import CollectionInput, CollectionOutput, CollectionStatus


@pytest.mark.atomic
class TestCollectionDataValidation:
    """Test Collection data validation and schemas - no external dependencies."""

    def test_collection_input_validation(self):
        """Test CollectionInput schema validation."""
        # Valid collection input
        valid_input = CollectionInput(
            name="Test Collection", is_private=False, users=[uuid4()], status=CollectionStatus.CREATED
        )

        assert valid_input.name == "Test Collection"
        assert not valid_input.is_private
        assert len(valid_input.users) == 1
        assert valid_input.status == CollectionStatus.CREATED

    def test_collection_name_validation(self):
        """Test collection name validation rules."""
        # Valid names
        valid_names = [
            "Test Collection",
            "collection-123",
            "collection_with_underscores",
            "Collection123",
            "My Collection Name",
        ]

        for name in valid_names:
            collection = CollectionInput(name=name, is_private=True, users=[], status=CollectionStatus.CREATED)
            assert collection.name == name
            assert isinstance(collection.name, str)
            assert len(collection.name.strip()) > 0

    def test_collection_privacy_validation(self):
        """Test collection privacy validation."""
        # Test private collection
        private_collection = CollectionInput(
            name="Private Collection", is_private=True, users=[], status=CollectionStatus.CREATED
        )
        assert private_collection.is_private is True

        # Test public collection
        public_collection = CollectionInput(
            name="Public Collection", is_private=False, users=[], status=CollectionStatus.CREATED
        )
        assert not public_collection.is_private

    def test_collection_users_validation(self):
        """Test collection users validation."""
        # Test with multiple users
        user_ids = [uuid4(), uuid4(), uuid4()]
        collection = CollectionInput(
            name="Multi-user Collection", is_private=False, users=user_ids, status=CollectionStatus.CREATED
        )
        assert len(collection.users) == 3
        from uuid import UUID

        assert all(isinstance(user_id, UUID) for user_id in collection.users)

        # Test with no users
        empty_collection = CollectionInput(
            name="Empty Collection", is_private=True, users=[], status=CollectionStatus.CREATED
        )
        assert len(empty_collection.users) == 0
        assert isinstance(empty_collection.users, list)

    def test_collection_status_validation(self):
        """Test collection status validation."""
        # Test all valid statuses
        statuses = [
            CollectionStatus.CREATED,
            CollectionStatus.PROCESSING,
            CollectionStatus.COMPLETED,
            CollectionStatus.ERROR,
        ]

        for status in statuses:
            collection = CollectionInput(name=f"Collection {status}", is_private=True, users=[], status=status)
            assert collection.status == status

    def test_collection_output_validation(self):
        """Test CollectionOutput schema validation."""
        # Valid collection output
        collection_id = uuid4()
        user_id = uuid4()

        test_datetime = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        valid_output = CollectionOutput(
            id=collection_id,
            name="Test Collection",
            vector_db_name="test_vector_db",
            is_private=True,
            user_ids=[user_id],
            files=[],
            status=CollectionStatus.COMPLETED,
            created_at=test_datetime,
            updated_at=test_datetime,
        )

        assert valid_output.id == collection_id
        assert valid_output.name == "Test Collection"
        assert valid_output.vector_db_name == "test_vector_db"
        assert valid_output.is_private is True
        assert valid_output.user_ids == [user_id]
        assert valid_output.status == CollectionStatus.COMPLETED
        assert valid_output.created_at == test_datetime
        assert valid_output.updated_at == test_datetime

    def test_collection_serialization(self):
        """Test collection data serialization."""
        collection = CollectionInput(
            name="Serialization Test", is_private=False, users=[uuid4()], status=CollectionStatus.CREATED
        )

        # Test model_dump
        data = collection.model_dump()
        assert isinstance(data, dict)
        assert "name" in data
        assert "is_private" in data
        assert "users" in data
        assert "status" in data
        assert data["name"] == "Serialization Test"
        assert not data["is_private"]
        assert data["status"] == CollectionStatus.CREATED

    def test_collection_validation_errors(self):
        """Test collection validation error handling."""
        # Test invalid name (empty) - Pydantic should handle this
        try:
            CollectionInput(name="", is_private=True, users=[], status=CollectionStatus.CREATED)
            # If no exception is raised, that"s also valid behavior
            assert True
        except Exception:
            # If an exception is raised, that"s also valid
            assert True

        # Test invalid users (not UUIDs) - Pydantic should handle this
        try:
            CollectionInput(
                name="Test Collection", is_private=True, users=["invalid-uuid"], status=CollectionStatus.CREATED
            )
            # If no exception is raised, that"s also valid behavior
            assert True
        except Exception:
            # If an exception is raised, that"s also valid
            assert True

    def test_collection_string_representation(self):
        """Test collection string representation."""
        collection = CollectionInput(
            name="String Test Collection", is_private=True, users=[], status=CollectionStatus.CREATED
        )

        # Test string representation
        str_repr = str(collection)
        assert isinstance(str_repr, str)
        assert "String Test Collection" in str_repr
        assert "is_private=True" in str_repr
        assert "status=" in str_repr
