"""Atomic tests for search data validation.

These tests validate data structures, schemas, and data consistency
without any external dependencies (no database, no HTTP, no services).
"""

from datetime import datetime
from uuid import uuid4

import pytest

from rag_solution.schemas.collection_schema import CollectionOutput, CollectionStatus
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.schemas.user_schema import UserOutput


class TestSearchDataValidation:
    """Test search-related data validation and consistency."""

    def test_search_input_validation(self):
        """Test that SearchInput validates correctly."""
        valid_input = SearchInput(question="What is the main topic?", collection_id=uuid4(), pipeline_id=uuid4(), user_id=uuid4())

        assert valid_input.question == "What is the main topic?"
        assert valid_input.collection_id is not None
        assert valid_input.pipeline_id is not None
        assert valid_input.user_id is not None

    def test_search_input_invalid_data(self):
        """Test that SearchInput rejects invalid data."""
        from pydantic import ValidationError

        # Test with invalid UUID (should raise ValidationError)
        with pytest.raises(ValidationError):
            SearchInput(
                question="What is the main topic?",
                collection_id="invalid-uuid",  # Invalid UUID should fail
                pipeline_id=uuid4(),
                user_id=uuid4(),
            )

    def test_collection_data_consistency(self):
        """Test that collection data maintains consistency."""
        collection_id = uuid4()
        user_id = uuid4()

        collection = CollectionOutput(
            id=collection_id,
            name="Test Collection",
            vector_db_name="test_collection",
            is_private=True,
            user_ids=[user_id],
            files=[],
            status=CollectionStatus.CREATED,
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
        )

        # Verify data consistency
        assert collection.id == collection_id
        assert collection.name == "Test Collection"
        assert collection.vector_db_name == "test_collection"
        assert collection.is_private is True
        assert user_id in collection.user_ids
        assert collection.status == CollectionStatus.CREATED

    def test_user_data_consistency(self):
        """Test that user data maintains consistency."""
        user_id = uuid4()

        user = UserOutput(
            id=user_id,
            email="test@example.com",
            ibm_id="test_user_123",
            name="Test User",
            role="user",
            preferred_provider_id=None,
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
        )

        # Verify data consistency
        assert user.id == user_id
        assert user.email == "test@example.com"
        assert user.ibm_id == "test_user_123"
        assert user.name == "Test User"
        assert user.role == "user"

    def test_search_output_structure(self):
        """Test that SearchOutput has correct structure."""
        search_output = SearchOutput(answer="Test answer", documents=[], query_results=[], rewritten_query="Test query", evaluation={})

        # Verify required fields exist
        assert hasattr(search_output, "answer")
        assert hasattr(search_output, "documents")
        assert hasattr(search_output, "query_results")
        assert hasattr(search_output, "rewritten_query")
        assert hasattr(search_output, "evaluation")

    def test_document_id_validation(self):
        """Test that document IDs are properly validated."""
        doc_id = uuid4()

        # Test valid UUID
        assert str(doc_id) is not None
        assert len(str(doc_id)) == 36  # UUID string length

        # Test UUID format
        uuid_str = str(doc_id)
        assert uuid_str.count("-") == 4  # UUID has 4 hyphens

    def test_collection_status_enum_validation(self):
        """Test that collection status enum values are valid."""
        valid_statuses = [CollectionStatus.CREATED, CollectionStatus.PROCESSING, CollectionStatus.COMPLETED, CollectionStatus.ERROR]

        for status in valid_statuses:
            assert status in CollectionStatus
            assert isinstance(status.value, str)

    def test_data_serialization(self):
        """Test that data structures serialize correctly."""
        collection = CollectionOutput(
            id=uuid4(),
            name="Test Collection",
            vector_db_name="test_collection",
            is_private=True,
            user_ids=[],
            files=[],
            status=CollectionStatus.CREATED,
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            updated_at=datetime(2024, 1, 1, 0, 0, 0),
        )

        # Test JSON serialization
        json_data = collection.model_dump()
        assert json_data["name"] == "Test Collection"
        assert json_data["is_private"] is True
        assert json_data["status"] == "created"
