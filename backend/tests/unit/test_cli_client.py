"""Unit tests for CLI HTTP client wrapper - focuses on API communication, not business logic."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from uuid import uuid4

from rag_solution.cli.client import RAGAPIClient
from rag_solution.cli.config import RAGConfig
from rag_solution.cli.exceptions import RAGCLIError, AuthenticationError


@pytest.mark.unit
class TestRAGAPIClient:
    """Test CLI HTTP client wrapper with mocked HTTP calls.
    
    Note: Business logic is tested in existing service tests.
    This focuses on HTTP communication and CLI-specific concerns.
    """
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return RAGConfig(
            api_url='http://localhost:8000',
            profile='test',
            auth_token='test-token'
        )
        
    @pytest.fixture
    def api_client(self, config):
        """Create API client with test config."""
        return RAGAPIClient(config)
        
    @pytest.fixture
    def mock_response(self):
        """Create mock HTTP response."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {'success': True}
        response.raise_for_status.return_value = None
        return response
        
    @patch('requests.get')
    def test_get_request_success(self, mock_get, api_client, mock_response):
        """Test successful GET request."""
        mock_get.return_value = mock_response
        
        result = api_client.get('/api/collections')
        
        # Verify request was made correctly
        mock_get.assert_called_once_with(
            'http://localhost:8000/api/collections',
            headers={
                'Authorization': 'Bearer test-token',
                'Content-Type': 'application/json'
            },
            params=None,
            timeout=30
        )
        
        # Verify response handling
        assert result == {'success': True}
        
    @patch('requests.post')
    def test_post_request_success(self, mock_post, api_client, mock_response):
        """Test successful POST request."""
        mock_post.return_value = mock_response
        
        data = {'name': 'Test Collection'}
        result = api_client.post('/api/collections', data=data)
        
        # Verify request
        mock_post.assert_called_once_with(
            'http://localhost:8000/api/collections',
            headers={
                'Authorization': 'Bearer test-token',
                'Content-Type': 'application/json'
            },
            json=data,
            timeout=30
        )
        
        assert result == {'success': True}
        
    @patch('requests.put')
    def test_put_request_success(self, mock_put, api_client, mock_response):
        """Test successful PUT request."""
        mock_put.return_value = mock_response
        
        data = {'name': 'Updated Collection'}
        result = api_client.put('/api/collections/123', data=data)
        
        # Verify request
        mock_put.assert_called_once_with(
            'http://localhost:8000/api/collections/123',
            headers={
                'Authorization': 'Bearer test-token',
                'Content-Type': 'application/json'
            },
            json=data,
            timeout=30
        )
        
        assert result == {'success': True}
        
    @patch('requests.delete')
    def test_delete_request_success(self, mock_delete, api_client, mock_response):
        """Test successful DELETE request."""
        mock_delete.return_value = mock_response
        
        result = api_client.delete('/api/collections/123')
        
        # Verify request
        mock_delete.assert_called_once_with(
            'http://localhost:8000/api/collections/123',
            headers={
                'Authorization': 'Bearer test-token',
                'Content-Type': 'application/json'
            },
            timeout=30
        )
        
        assert result == {'success': True}
        
    @patch('requests.get')
    def test_authentication_error_handling(self, mock_get, api_client):
        """Test handling of authentication errors."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {'error': 'Unauthorized'}
        mock_get.return_value = mock_response
        
        with pytest.raises(AuthenticationError) as exc_info:
            api_client.get('/api/collections')
            
        assert "Unauthorized" in str(exc_info.value)
        
    @patch('requests.post')
    def test_file_upload_request(self, mock_post, api_client, mock_response, tmp_path):
        """Test file upload functionality."""
        mock_post.return_value = mock_response
        
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")
        
        result = api_client.post_file(
            '/api/documents/upload',
            file_path=str(test_file),
            data={'collection_id': '123'}
        )
        
        # Verify file upload call was made
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        assert 'http://localhost:8000/api/documents/upload' in call_args[0]
        assert 'files' in call_args[1]
        assert 'data' in call_args[1]
        assert call_args[1]['data']['collection_id'] == '123'
        
        assert result == {'success': True}
        
    @patch('requests.get')
    def test_query_parameters(self, mock_get, api_client, mock_response):
        """Test request with query parameters."""
        mock_get.return_value = mock_response
        
        params = {'status': 'active', 'limit': 10}
        result = api_client.get('/api/collections', params=params)
        
        # Verify params were passed
        mock_get.assert_called_once_with(
            'http://localhost:8000/api/collections',
            headers={
                'Authorization': 'Bearer test-token',
                'Content-Type': 'application/json'
            },
            params=params,
            timeout=30
        )
        
    def test_is_authenticated_with_token(self, api_client):
        """Test authentication check with valid token."""
        assert api_client.is_authenticated() is True
        
    def test_is_authenticated_without_token(self, config):
        """Test authentication check without token."""
        config.auth_token = None
        api_client = RAGAPIClient(config)
        
        assert api_client.is_authenticated() is False
        
    @patch('requests.get')
    def test_timeout_configuration(self, mock_get, mock_response):
        """Test timeout configuration is respected."""
        config = RAGConfig(timeout=60, auth_token='test-token')
        api_client = RAGAPIClient(config)
        mock_get.return_value = mock_response
        
        api_client.get('/api/test')
        
        # Verify timeout was set
        mock_get.assert_called_once()
        assert mock_get.call_args[1]['timeout'] == 60


@pytest.mark.unit
class TestCLICommandWrapper:
    """Test CLI command wrapper classes that use the API client.
    
    These tests focus on CLI-specific logic, not business logic.
    Business logic is covered by existing service tests.
    """
    
    @pytest.fixture
    def mock_api_client(self):
        """Mock API client for command testing."""
        client = Mock(spec=RAGAPIClient)
        client.is_authenticated.return_value = True
        return client
        
    def test_collections_list_command(self, mock_api_client):
        """Test collections list command wrapper."""
        from rag_solution.cli.commands.collections import CollectionCommands
        
        # Mock API response (reuses existing test data patterns)
        mock_api_client.get.return_value = {
            'collections': [
                {'id': '123', 'name': 'Test Collection', 'status': 'active'},
                {'id': '456', 'name': 'Another Collection', 'status': 'active'}
            ],
            'total': 2
        }
        
        commands = CollectionCommands(api_client=mock_api_client)
        result = commands.list_collections()
        
        # Verify API was called correctly
        mock_api_client.get.assert_called_once_with('/api/collections')
        
        # Verify result structure (CLI-specific concern)
        assert result.success is True
        assert len(result.data['collections']) == 2
        assert result.data['total'] == 2
        
    def test_users_create_command(self, mock_api_client):
        """Test users create command wrapper."""
        from rag_solution.cli.commands.users import UserCommands
        
        # Mock API response
        mock_api_client.post.return_value = {
            'id': str(uuid4()),
            'email': 'test@example.com',
            'name': 'Test User',
            'role': 'user'
        }
        
        commands = UserCommands(api_client=mock_api_client)
        result = commands.create_user(
            email='test@example.com',
            name='Test User',
            role='user'
        )
        
        # Verify API call
        mock_api_client.post.assert_called_once_with('/api/users', data={
            'email': 'test@example.com',
            'name': 'Test User',
            'role': 'user'
        })
        
        # Verify CLI result structure
        assert result.success is True
        assert result.data['email'] == 'test@example.com'
        
    def test_search_query_command(self, mock_api_client):
        """Test search query command wrapper."""
        from rag_solution.cli.commands.search import SearchCommands
        
        # Mock API response
        mock_api_client.post.return_value = {
            'answer': 'Test answer',
            'retrieved_chunks': [
                {'content': 'Chunk 1', 'score': 0.95},
                {'content': 'Chunk 2', 'score': 0.87}
            ],
            'confidence_score': 0.91
        }
        
        commands = SearchCommands(api_client=mock_api_client)
        result = commands.query(
            collection_id='collection123',
            query='What is machine learning?'
        )
        
        # Verify API call
        mock_api_client.post.assert_called_once_with('/api/search/query', data={
            'collection_id': 'collection123',
            'query': 'What is machine learning?'
        })
        
        # Verify CLI result
        assert result.success is True
        assert result.data['answer'] == 'Test answer'
        assert len(result.data['retrieved_chunks']) == 2
        
    def test_command_authentication_check(self, mock_api_client):
        """Test that commands check authentication status."""
        from rag_solution.cli.commands.collections import CollectionCommands
        
        # Mock unauthenticated state
        mock_api_client.is_authenticated.return_value = False
        
        commands = CollectionCommands(api_client=mock_api_client)
        
        with pytest.raises(AuthenticationError):
            commands.list_collections()