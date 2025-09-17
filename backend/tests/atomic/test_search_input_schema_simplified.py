"""Atomic tests for simplified SearchInput schema without pipeline_id.

These tests verify that SearchInput schema works correctly without pipeline_id field
and that pipeline resolution is handled by the backend service layer.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from rag_solution.schemas.search_schema import SearchInput


class TestSearchInputSchemaSimplified:
    """Test suite for simplified SearchInput schema (no pipeline_id)."""

    def test_search_input_creation_without_pipeline_id_success(self):
        """Test that SearchInput can be created without pipeline_id field."""
        # Arrange
        question = "What is machine learning?"
        collection_id = uuid4()
        user_id = uuid4()
        config_metadata = {"max_chunks": 5}

        # Act
        search_input = SearchInput(
            question=question, collection_id=collection_id, user_id=user_id, config_metadata=config_metadata
        )

        # Assert
        assert search_input.question == question
        assert search_input.collection_id == collection_id
        assert search_input.user_id == user_id
        assert search_input.config_metadata == config_metadata
        # Verify pipeline_id is not in the schema
        assert not hasattr(search_input, "pipeline_id")

    def test_search_input_pipeline_id_field_does_not_exist(self):
        """Test that pipeline_id field is not accepted in SearchInput."""
        # Arrange
        data = {
            "question": "What is machine learning?",
            "collection_id": str(uuid4()),
            "user_id": str(uuid4()),
            "pipeline_id": str(uuid4()),  # Should be rejected
        }

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            SearchInput(**data)

        # Verify error is related to pipeline_id field
        error_message = str(exc_info.value)
        assert "pipeline_id" in error_message

    def test_search_input_minimal_valid_creation(self):
        """Test SearchInput creation with minimal required fields."""
        # Arrange
        question = "Test question"
        collection_id = uuid4()
        user_id = uuid4()

        # Act
        search_input = SearchInput(question=question, collection_id=collection_id, user_id=user_id)

        # Assert
        assert search_input.question == question
        assert search_input.collection_id == collection_id
        assert search_input.user_id == user_id
        assert search_input.config_metadata is None

    def test_search_input_config_metadata_optional(self):
        """Test that config_metadata is optional and can be None."""
        # Arrange & Act
        search_input = SearchInput(
            question="Test question", collection_id=uuid4(), user_id=uuid4(), config_metadata=None
        )

        # Assert
        assert search_input.config_metadata is None

    def test_search_input_config_metadata_dictionary(self):
        """Test that config_metadata accepts various dictionary structures."""
        # Arrange
        test_metadata = {
            "max_chunks": 10,
            "similarity_threshold": 0.8,
            "custom_parameter": "value",
            "nested": {"key": "value"},
        }

        # Act
        search_input = SearchInput(
            question="Test question", collection_id=uuid4(), user_id=uuid4(), config_metadata=test_metadata
        )

        # Assert
        assert search_input.config_metadata == test_metadata

    def test_search_input_serialization_without_pipeline_id(self):
        """Test that SearchInput serializes correctly without pipeline_id."""
        # Arrange
        search_input = SearchInput(
            question="Test question", collection_id=uuid4(), user_id=uuid4(), config_metadata={"max_chunks": 5}
        )

        # Act
        serialized = search_input.model_dump()

        # Assert
        assert "question" in serialized
        assert "collection_id" in serialized
        assert "user_id" in serialized
        assert "config_metadata" in serialized
        assert "pipeline_id" not in serialized  # Key assertion
