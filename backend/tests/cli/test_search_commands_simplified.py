"""CLI tests for simplified search commands without pipeline_id.

Tests that CLI search commands work without requiring pipeline_id parameter
and rely on backend pipeline resolution.
"""

from unittest.mock import Mock
from uuid import uuid4

import pytest

from rag_solution.cli.commands.search import SearchCommands


class TestSearchCommandsSimplified:
    """Test suite for simplified CLI search commands."""

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
    def sample_user_response(self):
        """Sample user response from auth endpoint."""
        return {"uuid": str(uuid4()), "email": "test@example.com", "name": "Test User"}

    def test_query_method_signature_simplified(self, search_commands):
        """Test that query method has simplified signature without pipeline_id."""
        # This test will fail until CLI is updated
        import inspect

        # Get method signature
        sig = inspect.signature(search_commands.query)
        params = list(sig.parameters.keys())

        # Assert expected parameters (no pipeline_id)
        expected_params = ["collection_id", "query", "max_chunks"]
        for param in expected_params:
            assert param in params

        # Assert pipeline_id is NOT in parameters
        assert "pipeline_id" not in params

    def test_query_without_pipeline_id_succeeds(self, search_commands, mock_api_client, sample_user_response):
        """Test that query works without pipeline_id by relying on backend resolution."""
        # Arrange
        collection_id = str(uuid4())
        query_text = "What is machine learning?"

        # Mock authentication
        search_commands._require_authentication = Mock()

        # Mock user context
        mock_api_client.get.return_value = sample_user_response

        # Mock successful search response
        expected_response = {
            "answer": "Machine learning is a subset of AI that enables computers to learn.",
            "documents": [],
            "query_results": [],
            "execution_time": 1.2,
        }
        mock_api_client.post.return_value = expected_response

        # Act
        result = search_commands.query(collection_id=collection_id, query=query_text, max_chunks=5)

        # Assert
        assert result.success is True
        assert result.data == expected_response
        assert result.message == "Search completed successfully"

        # Verify API was called without pipeline_id
        mock_api_client.post.assert_called_once_with(
            "/api/search",
            data={
                "question": query_text,
                "collection_id": collection_id,
                "user_id": sample_user_response["uuid"],
                "config_metadata": {"max_chunks": 5},
                # NO pipeline_id in request data
            },
        )

    def test_query_request_data_excludes_pipeline_id(self, search_commands, mock_api_client, sample_user_response):
        """Test that query request data does not include pipeline_id."""
        # Arrange
        collection_id = str(uuid4())
        query_text = "Test query"

        search_commands._require_authentication = Mock()
        mock_api_client.get.return_value = sample_user_response
        mock_api_client.post.return_value = {"answer": "test", "documents": [], "query_results": []}

        # Act
        search_commands.query(collection_id=collection_id, query=query_text)

        # Assert
        call_args = mock_api_client.post.call_args
        request_data = call_args[1]["data"]

        # Verify required fields exist
        assert "question" in request_data
        assert "collection_id" in request_data
        assert "user_id" in request_data
        assert "config_metadata" in request_data

        # Verify pipeline_id is NOT included
        assert "pipeline_id" not in request_data

    def test_query_no_longer_fetches_user_pipelines(self, search_commands, mock_api_client, sample_user_response):
        """Test that query method no longer fetches user pipelines from API."""
        # Arrange
        collection_id = str(uuid4())
        query_text = "Test query"

        search_commands._require_authentication = Mock()
        mock_api_client.get.return_value = sample_user_response
        mock_api_client.post.return_value = {"answer": "test", "documents": [], "query_results": []}

        # Act
        search_commands.query(collection_id=collection_id, query=query_text)

        # Assert
        get_calls = list(mock_api_client.get.call_args_list)

        # Should only call /api/auth/me, not /api/users/{user_id}/pipelines
        pipeline_calls = [call for call in get_calls if "pipelines" in str(call)]
        assert len(pipeline_calls) == 0, "CLI should not fetch user pipelines - backend handles resolution"

    def test_query_uses_simplified_api_request(self, search_commands, mock_api_client, sample_user_response):
        """Test that query uses simplified API request structure."""
        # Arrange
        collection_id = str(uuid4())
        query_text = "What are the benefits of automation?"
        max_chunks = 15

        search_commands._require_authentication = Mock()
        mock_api_client.get.return_value = sample_user_response
        mock_api_client.post.return_value = {"answer": "test", "documents": [], "query_results": []}

        # Act
        search_commands.query(collection_id=collection_id, query=query_text, max_chunks=max_chunks)

        # Assert
        call_args = mock_api_client.post.call_args
        assert call_args[0][0] == "/api/search"  # Correct endpoint

        request_data = call_args[1]["data"]
        expected_data = {
            "question": query_text,
            "collection_id": collection_id,
            "user_id": sample_user_response["uuid"],
            "config_metadata": {"max_chunks": max_chunks},
        }
        assert request_data == expected_data

    def test_query_handles_backend_error_gracefully(self, search_commands, mock_api_client, sample_user_response):
        """Test that query handles backend pipeline resolution errors gracefully."""
        # Arrange
        collection_id = str(uuid4())
        query_text = "Test query"

        search_commands._require_authentication = Mock()
        mock_api_client.get.return_value = sample_user_response

        # Mock backend error response
        mock_api_client.post.side_effect = Exception("No default pipeline found for user")

        # Act
        result = search_commands.query(collection_id=collection_id, query=query_text)

        # Assert
        assert result.success is False
        assert "No default pipeline found for user" in str(result.message) or "error" in result.message.lower()

    def test_batch_search_method_signature_update(self, search_commands):
        """Test that batch_search method signature is updated to remove pipeline_id."""
        # This test will fail until batch_search is updated
        import inspect

        sig = inspect.signature(search_commands.batch_search)
        params = list(sig.parameters.keys())

        # Should have collection_id and queries, but not pipeline_id
        assert "collection_id" in params
        assert "queries" in params
        assert "pipeline_id" not in params

    def test_query_maintains_config_metadata_support(self, search_commands, mock_api_client, sample_user_response):
        """Test that config_metadata is properly passed to backend."""
        # Arrange
        collection_id = str(uuid4())
        query_text = "Test query"
        max_chunks = 20

        search_commands._require_authentication = Mock()
        mock_api_client.get.return_value = sample_user_response
        mock_api_client.post.return_value = {"answer": "test", "documents": [], "query_results": []}

        # Act
        search_commands.query(collection_id=collection_id, query=query_text, max_chunks=max_chunks)

        # Assert
        call_args = mock_api_client.post.call_args
        request_data = call_args[1]["data"]
        assert request_data["config_metadata"] == {"max_chunks": max_chunks}
