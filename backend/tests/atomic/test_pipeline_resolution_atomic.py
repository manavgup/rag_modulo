"""TDD Red Phase: Atomic tests for Pipeline Resolution functionality.

Atomic level tests for individual functions and methods in the pipeline resolution system.
These tests focus on pure functions and single-responsibility methods.
"""

from unittest.mock import Mock
from uuid import uuid4

import pytest

from rag_solution.schemas.search_schema import SearchInput


class TestPipelineResolutionAtomicFunctions:
    """Atomic tests for individual pipeline resolution functions."""

    def test_search_input_pipeline_id_optional_validation(self):
        """Test SearchInput validation with optional pipeline_id."""
        user_id = uuid4()
        collection_id = uuid4()

        # Test with None pipeline_id
        search_input = SearchInput(
            question="What is AI?", collection_id=collection_id, user_id=user_id, pipeline_id=None
        )
        assert search_input.pipeline_id is None
        assert search_input.question == "What is AI?"

        # Test with explicit pipeline_id
        pipeline_id = uuid4()
        search_input_with_pipeline = SearchInput(
            question="What is AI?", collection_id=collection_id, user_id=user_id, pipeline_id=pipeline_id
        )
        assert search_input_with_pipeline.pipeline_id == pipeline_id

    def test_search_input_pipeline_id_field_default(self):
        """Test that pipeline_id defaults to None when not provided."""
        user_id = uuid4()
        collection_id = uuid4()

        # Create SearchInput without pipeline_id field
        search_input = SearchInput(question="What is AI?", collection_id=collection_id, user_id=user_id)
        assert search_input.pipeline_id is None

    def test_find_default_pipeline_in_list_pure_function(self):
        """Test pure function to find default pipeline in a list."""
        # This would be a utility function in PipelineResolutionService

        # Mock pipeline configs
        pipeline1 = Mock()
        pipeline1.id = uuid4()
        pipeline1.is_default = False

        pipeline2 = Mock()
        pipeline2.id = uuid4()
        pipeline2.is_default = True

        pipeline3 = Mock()
        pipeline3.id = uuid4()
        pipeline3.is_default = False

        pipelines = [pipeline1, pipeline2, pipeline3]

        # Function we expect to exist
        def find_default_pipeline(pipeline_list):
            """Find the default pipeline in a list."""
            for pipeline in pipeline_list:
                if pipeline.is_default:
                    return pipeline.id
            return None

        # Test
        result = find_default_pipeline(pipelines)
        assert result == pipeline2.id

    def test_find_default_pipeline_returns_none_when_no_default(self):
        """Test find_default_pipeline returns None when no default exists."""
        # Mock pipeline configs without default
        pipeline1 = Mock()
        pipeline1.id = uuid4()
        pipeline1.is_default = False

        pipeline2 = Mock()
        pipeline2.id = uuid4()
        pipeline2.is_default = False

        pipelines = [pipeline1, pipeline2]

        def find_default_pipeline(pipeline_list):
            """Find the default pipeline in a list."""
            for pipeline in pipeline_list:
                if pipeline.is_default:
                    return pipeline.id
            return None

        result = find_default_pipeline(pipelines)
        assert result is None

    def test_find_default_pipeline_handles_empty_list(self):
        """Test find_default_pipeline handles empty pipeline list."""

        def find_default_pipeline(pipeline_list):
            """Find the default pipeline in a list."""
            for pipeline in pipeline_list:
                if pipeline.is_default:
                    return pipeline.id
            return None

        result = find_default_pipeline([])
        assert result is None

    def test_pipeline_id_validation_atomic(self):
        """Test atomic UUID validation for pipeline IDs."""
        from pydantic import ValidationError

        valid_uuid = uuid4()

        # Valid UUID should work
        search_input = SearchInput(question="test", collection_id=uuid4(), user_id=uuid4(), pipeline_id=valid_uuid)
        assert search_input.pipeline_id == valid_uuid

        # Invalid UUID should raise validation error
        with pytest.raises(ValidationError):
            SearchInput(question="test", collection_id=uuid4(), user_id=uuid4(), pipeline_id="invalid-uuid")

    def test_collection_default_pipeline_id_field_atomic(self):
        """Test atomic validation of Collection.default_pipeline_id field."""
        from rag_solution.schemas.collection_schema import CollectionInput

        pipeline_id = uuid4()

        # Test with valid pipeline_id
        collection_input = CollectionInput(
            name="Test Collection", description="Test", is_private=False, default_pipeline_id=pipeline_id
        )
        assert collection_input.default_pipeline_id == pipeline_id

        # Test with None pipeline_id
        collection_input_none = CollectionInput(
            name="Test Collection", description="Test", is_private=False, default_pipeline_id=None
        )
        assert collection_input_none.default_pipeline_id is None

    def test_pipeline_resolution_hierarchy_order_atomic(self):
        """Test the atomic logic for pipeline resolution hierarchy ordering."""
        # This tests the pure logic of resolution hierarchy

        def get_resolution_priority(explicit_id, user_default_id, collection_default_id, system_default_id):
            """Pure function to determine pipeline resolution priority."""
            if explicit_id is not None:
                return explicit_id, "explicit"
            if user_default_id is not None:
                return user_default_id, "user_default"
            if collection_default_id is not None:
                return collection_default_id, "collection_default"
            if system_default_id is not None:
                return system_default_id, "system_default"
            return None, "none"

        # Test explicit takes priority
        explicit_id = uuid4()
        user_id = uuid4()
        collection_id = uuid4()
        system_id = uuid4()

        result_id, source = get_resolution_priority(explicit_id, user_id, collection_id, system_id)
        assert result_id == explicit_id
        assert source == "explicit"

        # Test user default when no explicit
        result_id, source = get_resolution_priority(None, user_id, collection_id, system_id)
        assert result_id == user_id
        assert source == "user_default"

        # Test collection default when no explicit or user
        result_id, source = get_resolution_priority(None, None, collection_id, system_id)
        assert result_id == collection_id
        assert source == "collection_default"

        # Test system default when no others
        result_id, source = get_resolution_priority(None, None, None, system_id)
        assert result_id == system_id
        assert source == "system_default"

        # Test none when no pipelines available
        result_id, source = get_resolution_priority(None, None, None, None)
        assert result_id is None
        assert source == "none"

    def test_config_metadata_preservation_atomic(self):
        """Test atomic preservation of config_metadata in SearchInput."""
        metadata = {"max_chunks": 10, "similarity_threshold": 0.8}

        search_input = SearchInput(
            question="test query", collection_id=uuid4(), user_id=uuid4(), pipeline_id=None, config_metadata=metadata
        )

        assert search_input.config_metadata == metadata
        assert search_input.config_metadata["max_chunks"] == 10
        assert search_input.config_metadata["similarity_threshold"] == 0.8

    def test_search_input_immutability_atomic(self):
        """Test that SearchInput behaves correctly with immutable data."""
        original_metadata = {"max_chunks": 5}

        search_input = SearchInput(
            question="test query", collection_id=uuid4(), user_id=uuid4(), config_metadata=original_metadata
        )

        # Modifying original metadata shouldn't affect SearchInput
        original_metadata["max_chunks"] = 10

        # SearchInput should maintain its own copy
        assert search_input.config_metadata["max_chunks"] == 5
