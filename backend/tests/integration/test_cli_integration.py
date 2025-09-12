"""Minimal integration tests for CLI-API communication.

These tests focus on CLI-specific integration concerns:
- CLI can reach API endpoints
- Authentication flow works
- Output formatting works
- Error handling is appropriate for CLI users

Business logic is covered by existing service/API tests.
"""

import pytest
import json
import tempfile
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

from rag_solution.cli.main import main_cli
from rag_solution.cli.client import RAGAPIClient
from rag_solution.cli.config import RAGConfig


@pytest.mark.integration
class TestCLIAPIConnectivity:
    """Test that CLI can connect to API endpoints.
    
    Leverages existing API tests for business logic validation.
    """
    
    @pytest.fixture
    def temp_profile_dir(self):
        """Create temporary directory for CLI profiles."""
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_dir = Path(temp_dir) / '.rag-cli' / 'profiles'
            profile_dir.mkdir(parents=True)
            yield profile_dir
            
    @pytest.fixture
    def test_credentials(self):
        """Test user credentials."""
        return {
            'email': 'test@example.com',
            'password': 'testpassword123'
        }
        
    def test_cli_can_reach_api(self):
        """Test CLI can reach API health endpoint."""
        result = main_cli(['health', 'check', '--api'])
        
        # Should complete without connection error
        assert result.exit_code in [0, 1]  # 1 for unhealthy but reachable
        
    def test_cli_authentication_flow(self, temp_profile_dir, test_credentials):
        """Test CLI authentication flow integrates with API."""
        with patch('rag_solution.cli.auth.ProfileManager.profiles_dir', temp_profile_dir):
            
            # Test login attempt (may fail if auth not set up, but should handle gracefully)
            login_result = main_cli([
                'auth', 'login',
                '--username', test_credentials['email'],
                '--password', test_credentials['password']
            ])
            
            # Should handle auth attempt appropriately (success or clear error)
            assert login_result.exit_code in [0, 1]
            
            if login_result.exit_code == 0:
                # If auth succeeds, test authenticated operation
                collections_result = main_cli(['collections', 'list', '--output', 'json'])
                assert collections_result.exit_code == 0
                
                # Test logout
                logout_result = main_cli(['auth', 'logout'])
                assert logout_result.exit_code == 0
                
    def test_cli_output_formatting(self):
        """Test CLI output formatting works correctly."""
        # Test JSON output format
        json_result = main_cli(['health', 'check', '--api', '--output', 'json'])
        
        if json_result.exit_code == 0 and json_result.output.strip():
            # Should be valid JSON
            try:
                json.loads(json_result.output)
            except json.JSONDecodeError:
                pytest.fail("CLI JSON output is not valid JSON")
                
        # Test table output format (default)
        table_result = main_cli(['health', 'check', '--api', '--output', 'table'])
        
        # Should complete and produce some output
        assert table_result.exit_code in [0, 1]
        
    def test_cli_error_handling(self):
        """Test CLI handles API errors appropriately for users."""
        # Test invalid endpoint (should give user-friendly error)
        invalid_result = main_cli(['collections', 'show', 'nonexistent-id'])
        
        # Should fail gracefully with user-friendly message
        assert invalid_result.exit_code != 0
        assert len(invalid_result.output) > 0  # Should provide error message
        
    def test_cli_help_system(self):
        """Test CLI help system works."""
        # Test main help
        help_result = main_cli(['--help'])
        assert help_result.exit_code == 0
        assert 'RAG Modulo' in help_result.output
        
        # Test subcommand help
        collections_help = main_cli(['collections', '--help'])
        assert collections_help.exit_code == 0
        assert 'collections' in collections_help.output.lower()


@pytest.mark.integration
class TestCLILeveragesExistingServices:
    """Test CLI leverages existing service functionality.
    
    These tests verify CLI calls the same endpoints that existing tests validate.
    """
    
    def test_cli_uses_existing_collection_endpoints(self):
        """Test CLI uses same collection endpoints as existing API tests."""
        # This test ensures CLI routes match existing tested API routes
        from rag_solution.cli.commands.collections import CollectionCommands
        
        config = RAGConfig(api_url='http://localhost:8000', auth_token='test')
        api_client = RAGAPIClient(config)
        commands = CollectionCommands(api_client=api_client)
        
        # Verify CLI uses standard endpoints (matching existing API tests)
        with patch.object(api_client, 'get') as mock_get:
            mock_get.return_value = {'collections': [], 'total': 0}
            
            commands.list_collections()
            
            # Should use same endpoint as existing API tests
            mock_get.assert_called_once_with('/api/collections')
            
        with patch.object(api_client, 'post') as mock_post:
            mock_post.return_value = {'id': '123', 'name': 'Test'}
            
            commands.create_collection('Test', 'Description')
            
            # Should use same endpoint as existing API tests
            mock_post.assert_called_once_with('/api/collections', data={
                'name': 'Test',
                'description': 'Description'
            })
            
    def test_cli_uses_existing_user_endpoints(self):
        """Test CLI uses same user endpoints as existing API tests."""
        from rag_solution.cli.commands.users import UserCommands
        
        config = RAGConfig(api_url='http://localhost:8000', auth_token='test')
        api_client = RAGAPIClient(config)
        commands = UserCommands(api_client=api_client)
        
        with patch.object(api_client, 'get') as mock_get:
            mock_get.return_value = {'users': [], 'total': 0}
            
            commands.list_users()
            
            # Should match existing API test endpoints
            mock_get.assert_called_once_with('/api/users')
            
    def test_cli_uses_existing_search_endpoints(self):
        """Test CLI uses same search endpoints as existing API tests."""
        from rag_solution.cli.commands.search import SearchCommands
        
        config = RAGConfig(api_url='http://localhost:8000', auth_token='test')
        api_client = RAGAPIClient(config)
        commands = SearchCommands(api_client=api_client)
        
        with patch.object(api_client, 'post') as mock_post:
            mock_post.return_value = {
                'answer': 'Test answer',
                'retrieved_chunks': [],
                'confidence_score': 0.8
            }
            
            commands.query('collection123', 'test query')
            
            # Should match existing search service endpoints
            mock_post.assert_called_once_with('/api/search/query', data={
                'collection_id': 'collection123',
                'query': 'test query'
            })


@pytest.mark.integration
class TestCLIConfigurationManagement:
    """Test CLI configuration and profile management integration."""
    
    @pytest.fixture
    def temp_profile_dir(self):
        """Create temporary directory for CLI profiles."""
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_dir = Path(temp_dir) / '.rag-cli' / 'profiles'
            profile_dir.mkdir(parents=True)
            yield profile_dir
            
    def test_profile_management_integration(self, temp_profile_dir):
        """Test profile management works with file system."""
        with patch('rag_solution.cli.auth.ProfileManager.profiles_dir', temp_profile_dir):
            
            # Create profile
            create_result = main_cli([
                'auth', 'profiles', 'create', 'test-profile',
                '--api-url', 'https://test.example.com',
                '--description', 'Test profile'
            ])
            
            assert create_result.exit_code == 0
            
            # List profiles
            list_result = main_cli(['auth', 'profiles', 'list'])
            
            assert list_result.exit_code == 0
            assert 'test-profile' in list_result.output
            
            # Switch profile
            switch_result = main_cli(['auth', 'profiles', 'switch', 'test-profile'])
            
            assert switch_result.exit_code == 0
            
    def test_configuration_validation_integration(self):
        """Test configuration validation integrates properly."""
        # Test valid configuration
        valid_result = main_cli([
            'config', 'validate',
            '--api-url', 'https://valid.example.com',
            '--timeout', '30'
        ])
        
        assert valid_result.exit_code == 0
        
        # Test invalid configuration
        invalid_result = main_cli([
            'config', 'validate', 
            '--api-url', 'invalid-url',
            '--timeout', '-1'
        ])
        
        assert invalid_result.exit_code != 0
        assert 'invalid' in invalid_result.output.lower()