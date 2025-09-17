"""TDD Red Phase: Tests for Collection model with default_pipeline_id.

This module tests the enhancement to the Collection model to support
collection-level default pipeline assignment.
"""

from datetime import datetime
from uuid import uuid4

import pytest

from rag_solution.models.collection import Collection
from rag_solution.schemas.collection_schema import CollectionInput, CollectionOutput


class TestCollectionDefaultPipeline:
    """Test suite for Collection model default pipeline functionality."""

    def test_collection_model_has_default_pipeline_id_field(self):
        """Test that Collection model includes default_pipeline_id field."""
        # Arrange
        collection_id = uuid4()
        pipeline_id = uuid4()
        user_id = uuid4()

        # Act
        collection = Collection(
            id=collection_id,
            name="Test Collection",
            description="Test collection with default pipeline",
            user_id=user_id,
            is_private=False,
            status="CREATED",
            vector_db_name="test_collection_db",
            default_pipeline_id=pipeline_id,  # This field should exist
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Assert
        assert hasattr(collection, "default_pipeline_id")
        assert collection.default_pipeline_id == pipeline_id

    def test_collection_model_allows_null_default_pipeline_id(self):
        """Test that default_pipeline_id can be None."""
        # Arrange
        collection_id = uuid4()
        user_id = uuid4()

        # Act
        collection = Collection(
            id=collection_id,
            name="Test Collection",
            description="Test collection without default pipeline",
            user_id=user_id,
            is_private=False,
            status="CREATED",
            vector_db_name="test_collection_db",
            default_pipeline_id=None,  # Should allow None
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Assert
        assert collection.default_pipeline_id is None

    def test_collection_input_schema_includes_optional_default_pipeline_id(self):
        """Test that CollectionInput schema includes optional default_pipeline_id."""
        # Test with default_pipeline_id
        pipeline_id = uuid4()
        collection_input_with_pipeline = CollectionInput(
            name="Test Collection",
            description="Test collection",
            is_private=False,
            default_pipeline_id=pipeline_id,
        )
        assert collection_input_with_pipeline.default_pipeline_id == pipeline_id

        # Test without default_pipeline_id
        collection_input_without_pipeline = CollectionInput(
            name="Test Collection",
            description="Test collection",
            is_private=False,
        )
        assert collection_input_without_pipeline.default_pipeline_id is None

    def test_collection_output_schema_includes_default_pipeline_id(self):
        """Test that CollectionOutput schema includes default_pipeline_id."""
        # Arrange
        collection_id = uuid4()
        pipeline_id = uuid4()
        user_id = uuid4()
        current_time = datetime.utcnow()

        # Act
        collection_output = CollectionOutput(
            id=collection_id,
            name="Test Collection",
            description="Test collection",
            user_id=user_id,
            is_private=False,
            status="COMPLETED",
            created_at=current_time,
            updated_at=current_time,
            default_pipeline_id=pipeline_id,
        )

        # Assert
        assert collection_output.default_pipeline_id == pipeline_id

    def test_collection_can_be_updated_with_default_pipeline_id(self):
        """Test that existing collections can be updated with default pipeline."""
        # Arrange
        collection_id = uuid4()
        user_id = uuid4()
        pipeline_id = uuid4()

        # Create collection without default pipeline
        collection = Collection(
            id=collection_id,
            name="Test Collection",
            description="Test collection",
            user_id=user_id,
            is_private=False,
            status="CREATED",
            vector_db_name="test_collection_db",
            default_pipeline_id=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        assert collection.default_pipeline_id is None

        # Act - Update with default pipeline
        collection.default_pipeline_id = pipeline_id
        collection.updated_at = datetime.utcnow()

        # Assert
        assert collection.default_pipeline_id == pipeline_id

    def test_collection_default_pipeline_id_foreign_key_constraint(self):
        """Test that default_pipeline_id references pipeline_configs table."""
        # This test verifies that the database relationship is properly defined
        # We'll test this by checking the model's relationship definitions

        # Check that Collection model has proper relationship definition
        assert hasattr(Collection, "__table__")

        # The actual foreign key constraint will be tested in integration tests
        # Here we just verify the field exists and can hold UUID values
        pipeline_id = uuid4()
        collection = Collection(
            id=uuid4(),
            name="Test Collection",
            user_id=uuid4(),
            is_private=False,
            status="CREATED",
            vector_db_name="test_db",
            default_pipeline_id=pipeline_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        assert collection.default_pipeline_id == pipeline_id

    def test_collection_schema_validation_with_invalid_pipeline_id(self):
        """Test schema validation with invalid pipeline ID format."""
        # This should be handled by UUID4 type validation

        with pytest.raises((ValueError, TypeError)):
            CollectionInput(
                name="Test Collection",
                description="Test collection",
                is_private=False,
                default_pipeline_id="invalid-uuid-format",
            )

    def test_multiple_collections_can_share_same_default_pipeline(self):
        """Test that multiple collections can reference the same default pipeline."""
        # Arrange
        shared_pipeline_id = uuid4()
        user_id = uuid4()

        # Act
        collection1 = Collection(
            id=uuid4(),
            name="Collection 1",
            user_id=user_id,
            is_private=False,
            status="CREATED",
            vector_db_name="collection1_db",
            default_pipeline_id=shared_pipeline_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        collection2 = Collection(
            id=uuid4(),
            name="Collection 2",
            user_id=user_id,
            is_private=False,
            status="CREATED",
            vector_db_name="collection2_db",
            default_pipeline_id=shared_pipeline_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Assert
        assert collection1.default_pipeline_id == shared_pipeline_id
        assert collection2.default_pipeline_id == shared_pipeline_id
        assert collection1.default_pipeline_id == collection2.default_pipeline_id
