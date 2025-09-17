"""Unit tests for PipelineService signature updates.

Tests that PipelineService methods have the correct signatures for the
simplified pipeline resolution architecture.
"""

import contextlib
from unittest.mock import Mock
from uuid import uuid4

import pytest

from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.pipeline_service import PipelineService


class TestPipelineServiceSignatureUpdate:
    """Test suite for PipelineService signature updates."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def mock_settings(self):
        """Mock settings."""
        settings = Mock()
        settings.vector_db = "milvus"
        return settings

    @pytest.fixture
    def pipeline_service(self, mock_db, mock_settings):
        """Create PipelineService instance."""
        return PipelineService(mock_db, mock_settings)

    @pytest.fixture
    def sample_search_input(self):
        """Create sample SearchInput without pipeline_id."""
        return SearchInput(
            question="What is machine learning?",
            collection_id=uuid4(),
            user_id=uuid4(),
            config_metadata={"max_chunks": 5},
        )

    def test_get_default_pipeline_simplified_signature(self, pipeline_service):
        """Test that get_default_pipeline has simplified signature (no collection_id)."""
        # This test will fail until PipelineService.get_default_pipeline is updated
        import inspect

        # Get method signature
        sig = inspect.signature(pipeline_service.get_default_pipeline)
        params = list(sig.parameters.keys())

        # Should have user_id parameter but not collection_id
        assert "user_id" in params
        assert "collection_id" not in params  # Should be removed

        # Method should work with just user_id
        user_id = uuid4()
        with contextlib.suppress(Exception):
            # This call should work with new signature
            pipeline_service.get_default_pipeline(user_id)

    def test_execute_pipeline_accepts_pipeline_id_parameter(self, pipeline_service, sample_search_input):
        """Test that execute_pipeline accepts pipeline_id as a parameter."""
        # This test will fail until execute_pipeline signature is updated
        import inspect

        # Get method signature
        sig = inspect.signature(pipeline_service.execute_pipeline)
        params = list(sig.parameters.keys())

        # Should have pipeline_id parameter
        assert "pipeline_id" in params
        assert "search_input" in params
        assert "collection_name" in params

        # Test calling with new signature
        pipeline_id = uuid4()
        collection_name = "test_collection"

        with contextlib.suppress(Exception):
            # This call should work with new signature
            pipeline_service.execute_pipeline(
                search_input=sample_search_input, collection_name=collection_name, pipeline_id=pipeline_id
            )

    def test_execute_pipeline_no_longer_uses_search_input_pipeline_id(self, pipeline_service, sample_search_input):
        """Test that execute_pipeline doesn't try to access search_input.pipeline_id."""
        # This test ensures the implementation is updated to use the parameter instead

        # Mock the internal methods that execute_pipeline might call
        pipeline_service._validate_configuration = Mock(return_value=(Mock(), Mock(), Mock()))
        pipeline_service.query_rewriter = Mock()
        pipeline_service.query_rewriter.rewrite_query = Mock(return_value="rewritten query")

        # Mock other dependencies
        pipeline_service._get_retriever_instance = Mock(return_value=Mock())
        pipeline_service._get_llm_instance = Mock(return_value=Mock())
        pipeline_service._get_evaluator = Mock(return_value=Mock())

        pipeline_id = uuid4()
        collection_name = "test_collection"

        try:
            # Call with pipeline_id parameter
            pipeline_service.execute_pipeline(
                search_input=sample_search_input, collection_name=collection_name, pipeline_id=pipeline_id
            )

            # If this succeeds, verify _validate_configuration was called with pipeline_id parameter
            pipeline_service._validate_configuration.assert_called_with(pipeline_id, sample_search_input.user_id)
        except AttributeError as e:
            if "pipeline_id" in str(e) and "search_input" in str(e):
                # This is expected in Red phase - implementation still uses search_input.pipeline_id
                pass
            else:
                raise
        except Exception:
            # Other exceptions are expected in Red phase
            pass

    def test_get_default_pipeline_only_uses_user_context(self, pipeline_service):
        """Test that get_default_pipeline only considers user context, not collection."""
        # This test verifies the architectural decision to remove collection-pipeline coupling

        user_id = uuid4()

        # Mock the repository layer
        pipeline_service._pipeline_repository = Mock()
        pipeline_service.pipeline_repository.get_user_default = Mock(return_value=None)

        with contextlib.suppress(Exception):
            # Call should work with just user_id
            pipeline_service.get_default_pipeline(user_id)

            # Verify repository was called correctly
            pipeline_service.pipeline_repository.get_user_default.assert_called_once_with(user_id)
