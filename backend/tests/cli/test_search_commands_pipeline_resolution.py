"""TDD Red Phase: Tests for CLI Search Commands with Pipeline Resolution.

This module tests the enhanced CLI search commands that work with the new
optional pipeline architecture, allowing users to search without specifying pipelines.
"""

from unittest.mock import Mock
from uuid import uuid4

import pytest

from rag_solution.cli.commands.search import SearchCommands


class TestSearchCommandsPipelineResolution:
    """Test suite for CLI SearchCommands with pipeline resolution."""

    @pytest.fixture
    def mock_api_client(self):
        """Create mock API client."""
        return Mock()

    @pytest.fixture
    def mock_config(self):
        """Create mock CLI config."""
        return Mock()

    @pytest.fixture
    def search_commands(self, mock_api_client, mock_config):
        """Create SearchCommands instance with mocks."""
        return SearchCommands(mock_api_client, mock_config)

    @pytest.fixture
    def sample_ids(self):
        """Generate sample UUIDs for testing."""
        return {
            "user_id": uuid4(),
            "collection_id": uuid4(),
            "pipeline_id": uuid4(),
        }

    def test_query_works_without_pipeline_id_using_backend_resolution(
        self, search_commands, mock_api_client, sample_ids
    ):
        """Test that CLI query works without pipeline_id by relying on backend resolution."""
        # Arrange
        collection_id = str(sample_ids["collection_id"])
        query_text = "What is machine learning?"

        # Mock authentication
        search_commands._require_authentication = Mock()

        # Mock user context
        mock_api_client.get.return_value = {"uuid": str(sample_ids["user_id"])}

        # Mock successful search response
        expected_response = {
            "answer": "Machine learning is a subset of AI that enables computers to learn.",
            "documents": [],
            "query_results": [],
            "execution_time": 1.2,
        }
        mock_api_client.post.return_value = expected_response

        # Act
        result = search_commands.query(
            collection_id=collection_id,
            query=query_text,
            pipeline_id=None,  # No pipeline specified
            max_chunks=5,
        )

        # Assert
        assert result.success is True
        assert result.data == expected_response
        assert result.message == "Search completed successfully"

        # Verify API was called with correct data (no pipeline_id in request)
        mock_api_client.post.assert_called_once_with(
            "/api/search",
            data={
                "question": query_text,
                "collection_id": collection_id,
                "user_id": str(sample_ids["user_id"]),
                "config_metadata": {"max_chunks": 5},
                # Note: No pipeline_id should be sent when None
            },
        )

    def test_query_includes_explicit_pipeline_id_when_provided(self, search_commands, mock_api_client, sample_ids):
        """Test that explicit pipeline_id is included in request when provided."""
        # Arrange
        collection_id = str(sample_ids["collection_id"])
        pipeline_id = str(sample_ids["pipeline_id"])
        query_text = "What is machine learning?"

        # Mock authentication
        search_commands._require_authentication = Mock()

        # Mock user context
        mock_api_client.get.return_value = {"uuid": str(sample_ids["user_id"])}

        # Mock successful search response
        expected_response = {
            "answer": "Machine learning is a subset of AI that enables computers to learn.",
            "documents": [],
            "query_results": [],
            "execution_time": 1.2,
        }
        mock_api_client.post.return_value = expected_response

        # Act
        result = search_commands.query(
            collection_id=collection_id,
            query=query_text,
            pipeline_id=pipeline_id,  # Explicit pipeline specified
            max_chunks=5,
        )

        # Assert
        assert result.success is True
        assert result.data == expected_response

        # Verify API was called with explicit pipeline_id
        mock_api_client.post.assert_called_once_with(
            "/api/search",
            data={
                "question": query_text,
                "collection_id": collection_id,
                "user_id": str(sample_ids["user_id"]),
                "pipeline_id": pipeline_id,  # Should include explicit pipeline_id
                "config_metadata": {"max_chunks": 5},
            },
        )

    def test_query_removes_deprecated_pipeline_resolution_logic(self, search_commands, mock_api_client, sample_ids):
        """Test that CLI no longer attempts to resolve pipelines itself."""
        # Arrange
        collection_id = str(sample_ids["collection_id"])
        query_text = "What is machine learning?"

        # Mock authentication
        search_commands._require_authentication = Mock()

        # Mock user context
        mock_api_client.get.return_value = {"uuid": str(sample_ids["user_id"])}

        # Mock successful search response
        expected_response = {
            "answer": "Machine learning is a subset of AI that enables computers to learn.",
            "documents": [],
            "query_results": [],
            "execution_time": 1.2,
        }
        mock_api_client.post.return_value = expected_response

        # Act
        result = search_commands.query(collection_id=collection_id, query=query_text, pipeline_id=None, max_chunks=5)

        # Assert
        assert result.success is True

        # Verify that CLI does NOT attempt to fetch user pipelines anymore
        # (This was the old behavior that we're removing)
        get_calls = [call for call in mock_api_client.get.call_args_list]
        pipeline_calls = [call for call in get_calls if "pipelines" in str(call)]
        assert len(pipeline_calls) == 0, "CLI should not fetch user pipelines - backend handles resolution"

    def test_query_handles_backend_pipeline_resolution_errors_gracefully(
        self, search_commands, mock_api_client, sample_ids
    ):
        """Test that CLI handles backend pipeline resolution errors gracefully."""
        # Arrange
        collection_id = str(sample_ids["collection_id"])
        query_text = "What is machine learning?"

        # Mock authentication
        search_commands._require_authentication = Mock()

        # Mock user context
        mock_api_client.get.return_value = {"uuid": str(sample_ids["user_id"])}

        # Mock backend error response for pipeline resolution failure
        mock_api_client.post.side_effect = Exception("No pipeline configuration could be resolved")

        # Act
        result = search_commands.query(collection_id=collection_id, query=query_text, pipeline_id=None, max_chunks=5)

        # Assert
        assert result.success is False
        assert "No pipeline configuration could be resolved" in str(result.message) or "error" in result.message.lower()

    def test_query_preserves_config_metadata_in_request(self, search_commands, mock_api_client, sample_ids):
        """Test that config_metadata is properly sent to backend."""
        # Arrange
        collection_id = str(sample_ids["collection_id"])
        query_text = "What is machine learning?"
        max_chunks = 15

        # Mock authentication
        search_commands._require_authentication = Mock()

        # Mock user context
        mock_api_client.get.return_value = {"uuid": str(sample_ids["user_id"])}

        # Mock successful search response
        mock_api_client.post.return_value = {"answer": "test", "documents": [], "query_results": []}

        # Act
        search_commands.query(collection_id=collection_id, query=query_text, pipeline_id=None, max_chunks=max_chunks)

        # Assert
        call_args = mock_api_client.post.call_args
        request_data = call_args[1]["data"]
        assert request_data["config_metadata"] == {"max_chunks": max_chunks}

    def test_query_maintains_backward_compatibility_with_explicit_pipeline(
        self, search_commands, mock_api_client, sample_ids
    ):
        """Test that existing code using explicit pipeline_id continues to work."""
        # This test ensures that our changes don't break existing CLI usage

        # Arrange
        collection_id = str(sample_ids["collection_id"])
        pipeline_id = str(sample_ids["pipeline_id"])
        query_text = "What is machine learning?"

        # Mock authentication
        search_commands._require_authentication = Mock()

        # Mock user context
        mock_api_client.get.return_value = {"uuid": str(sample_ids["user_id"])}

        # Mock successful search response
        expected_response = {"answer": "test", "documents": [], "query_results": []}
        mock_api_client.post.return_value = expected_response

        # Act - This should work exactly as before
        result = search_commands.query(collection_id=collection_id, query=query_text, pipeline_id=pipeline_id)

        # Assert
        assert result.success is True
        call_args = mock_api_client.post.call_args
        request_data = call_args[1]["data"]
        assert request_data["pipeline_id"] == pipeline_id
