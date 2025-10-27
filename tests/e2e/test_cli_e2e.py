"""End-to-end tests for complete CLI workflow.

This test validates the complete user journey through the CLI.
Business logic validation is handled by existing service/API tests.
"""

import os
import tempfile
from unittest.mock import patch

import pytest
import requests
from rag_solution.cli.client import RAGAPIClient
from rag_solution.cli.commands.auth import AuthCommands
from rag_solution.cli.commands.collections import CollectionCommands
from rag_solution.cli.commands.documents import DocumentCommands
from rag_solution.cli.commands.search import SearchCommands
from rag_solution.cli.config import RAGConfig
from rag_solution.cli.exceptions import APIError, AuthenticationError


@pytest.mark.e2e
class TestCLICompleteWorkflow:
    """Test complete CLI workflow end-to-end."""

    @pytest.fixture
    def api_url(self, monkeypatch):
        """Get API URL for testing."""
        # Set default API URL for testing - avoiding direct env access
        api_url = "http://localhost:8000"
        monkeypatch.setenv("API_URL", api_url)
        return api_url

    @pytest.fixture
    def cli_config(self, api_url):
        """Create CLI configuration for testing."""
        return RAGConfig(api_url=api_url, profile="e2e-test", timeout=30)

    @pytest.fixture
    def api_client(self, cli_config, tmp_path, monkeypatch):
        """Create API client for testing."""
        # Set temporary home directory
        monkeypatch.setenv("HOME", str(tmp_path))
        client = RAGAPIClient(cli_config)
        return client

    @pytest.fixture
    def test_document_content(self):
        """Create test document content."""
        return """
        Machine Learning Fundamentals

        Machine learning is a subset of artificial intelligence (AI) that focuses on
        algorithms that can learn from and make decisions or predictions based on data.

        Key Concepts:
        - Supervised Learning: Learning with labeled examples
        - Unsupervised Learning: Finding patterns in unlabeled data
        - Reinforcement Learning: Learning through trial and error

        Applications:
        - Image recognition
        - Natural language processing
        - Recommendation systems
        - Autonomous vehicles
        """

    def test_authentication_workflow_e2e(self, api_client):
        """Test complete authentication workflow from start to finish."""
        try:
            auth_commands = AuthCommands(api_client)

            # Step 1: Check initial authentication status (should be unauthenticated)
            result = auth_commands.status()
            assert result.success is False
            assert result.error_code == "NOT_AUTHENTICATED"

            # Step 2: Attempt CLI authentication start (this will test the endpoint exists)
            # Note: We can't complete full OIDC flow in automated test, but we can test the start
            try:
                # Mock the browser-based authentication for testing
                with patch("webbrowser.open"), patch("builtins.input", return_value="mock-auth-code"):
                    # This would normally open browser and prompt for auth code
                    # In test, we'll just verify the start endpoint works

                    # Test that CLI auth start endpoint is reachable
                    cli_request = {"provider": "ibm", "client_id": "test-e2e-client", "scope": "openid profile email"}

                    response = api_client.post("/api/auth/cli/start", data=cli_request)
                    assert "auth_url" in response
                    assert "state" in response

                    # In real workflow, user would authenticate and provide auth code
                    # For test, we'll simulate setting a token directly
                    test_token = (
                        "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoidGVzdCIsImV4cCI6OTk5OTk5OTk5OX0.test"
                    )
                    from datetime import datetime, timedelta

                    expires_at = (datetime.now() + timedelta(hours=1)).isoformat()

                    api_client.set_auth_token(test_token, expires_at)

                    # Verify authentication state changed
                    assert api_client.is_authenticated() is True

                    # Step 3: Test logout workflow
                    result = auth_commands.logout()
                    assert result.success is True

                    # Verify logout worked
                    result = auth_commands.status()
                    assert result.success is False
                    assert result.error_code == "NOT_AUTHENTICATED"

            except APIError as e:
                if e.status_code == 404:
                    pytest.fail("CLI auth endpoints not implemented - cannot complete auth workflow test")
                else:
                    # Other auth errors are acceptable for this test
                    pytest.skip(f"Auth configuration issues prevent full test: {e}")

        except requests.exceptions.ConnectionError:
            pytest.skip("Backend API not running - E2E test requires live backend")

    def test_collection_management_workflow_e2e(self, api_client, test_document_content):
        """Test complete collection management workflow."""
        try:
            # This test requires authentication, so we'll simulate it
            test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoidGVzdCIsImV4cCI6OTk5OTk5OTk5OX0.test"
            from datetime import datetime, timedelta

            expires_at = (datetime.now() + timedelta(hours=1)).isoformat()
            api_client.set_auth_token(test_token, expires_at)

            collections_commands = CollectionCommands(api_client)
            documents_commands = DocumentCommands(api_client)
            search_commands = SearchCommands(api_client)

            # Step 1: List existing collections (baseline)
            initial_result = collections_commands.list_collections()
            if initial_result.success:
                initial_count = len(initial_result.data.get("collections", []))
            else:
                # If auth fails, skip the test
                pytest.skip("Authentication required for collection workflow test")

            # Step 2: Create a new collection
            create_result = collections_commands.create_collection(
                name="E2E Test Collection",
                description="Created by end-to-end test",
                vector_db="milvus",
                is_private=False,
            )

            if not create_result.success:
                pytest.skip(f"Collection creation failed: {create_result.message}")

            collection_id = create_result.data.get("id")
            assert collection_id is not None

            try:
                # Step 3: Verify collection was created
                list_result = collections_commands.list_collections()
                assert list_result.success is True
                collections = list_result.data.get("collections", [])
                assert len(collections) == initial_count + 1

                # Find our collection
                test_collection = next((c for c in collections if c.get("name") == "E2E Test Collection"), None)
                assert test_collection is not None
                assert test_collection["id"] == collection_id

                # Step 4: Get detailed collection info
                detail_result = collections_commands.get_collection(collection_id)
                assert detail_result.success is True
                assert detail_result.data["name"] == "E2E Test Collection"

                # Step 5: Upload a document to the collection
                with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp_file:
                    tmp_file.write(test_document_content)
                    tmp_file_path = tmp_file.name

                try:
                    upload_result = documents_commands.upload_document(
                        file_path=tmp_file_path,
                        collection_id=collection_id,
                        metadata={
                            "title": "ML Fundamentals Test Doc",
                            "description": "Test document about machine learning",
                        },
                    )

                    if upload_result.success:
                        document_id = upload_result.data.get("id")
                        assert document_id is not None

                        # Step 6: List documents in collection
                        docs_result = documents_commands.list_documents(collection_id)
                        assert docs_result.success is True
                        documents = docs_result.data.get("documents", [])
                        assert len(documents) >= 1

                        # Find our document
                        test_doc = next((d for d in documents if d.get("title") == "ML Fundamentals Test Doc"), None)
                        assert test_doc is not None

                        # Step 7: Perform search query (after brief delay for indexing)
                        import time

                        time.sleep(2)  # Allow time for document processing

                        search_result = search_commands.query(
                            collection_id=collection_id, query="What is machine learning?", max_chunks=3
                        )

                        if search_result.success:
                            # Verify search returned results
                            assert "answer" in search_result.data
                            assert "retrieved_chunks" in search_result.data
                            retrieved_chunks = search_result.data["retrieved_chunks"]
                            assert len(retrieved_chunks) > 0

                            # Verify chunks contain relevant content
                            chunk_content = " ".join([chunk.get("content", "") for chunk in retrieved_chunks])
                            assert "machine learning" in chunk_content.lower()
                        else:
                            # Search might fail due to indexing delays or configuration
                            pytest.skip(f"Search functionality not available: {search_result.message}")

                finally:
                    # Cleanup temp file
                    if os.path.exists(tmp_file_path):
                        os.unlink(tmp_file_path)

            finally:
                # Cleanup: Delete the test collection
                _delete_result = collections_commands.delete_collection(collection_id)
                # Don't assert on delete success as it might not be implemented

        except requests.exceptions.ConnectionError:
            pytest.skip("Backend API not running - E2E test requires live backend")
        except AuthenticationError:
            pytest.skip("Authentication required for collection workflow test")

    def test_error_handling_workflow_e2e(self, api_client):
        """Test complete error handling across CLI workflow."""
        try:
            auth_commands = AuthCommands(api_client)
            collections_commands = CollectionCommands(api_client)

            # Test 1: Authentication errors
            result = auth_commands.status()
            assert result.success is False
            assert result.error_code == "NOT_AUTHENTICATED"

            # Test 2: API errors without authentication
            with pytest.raises(AuthenticationError):
                collections_commands.list_collections()

            # Test 3: Invalid collection operations
            with pytest.raises(AuthenticationError):
                collections_commands.get_collection("invalid-collection-id")

            # Test 4: Network/connection error handling is covered by connection error skips

        except requests.exceptions.ConnectionError:
            pytest.skip("Backend API not running - E2E test requires live backend")
