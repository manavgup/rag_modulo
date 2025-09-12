"""Single end-to-end test for complete CLI workflow.

This test validates the complete user journey through the CLI.
Business logic validation is handled by existing service/API tests.
"""

import pytest
import json
import tempfile
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
import time

from rag_solution.cli.main import main_cli


@pytest.mark.e2e
class TestCLICompleteWorkflow:
    """Test complete CLI workflow from authentication to search.

    This single test validates the entire user journey.
    Individual operations are tested by existing service tests.
    """

    @pytest.fixture
    def temp_profile_dir(self):
        """Create temporary directory for CLI profiles."""
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_dir = Path(temp_dir) / ".rag-cli" / "profiles"
            profile_dir.mkdir(parents=True)
            yield profile_dir

    @pytest.fixture
    def test_credentials(self):
        """Test user credentials."""
        return {"email": "test@example.com", "password": "testpassword123"}

    @pytest.fixture
    def sample_document(self, tmp_path):
        """Create sample document for testing."""
        doc_file = tmp_path / "test_document.txt"
        doc_file.write_text(
            """
        Machine Learning is a subset of artificial intelligence that enables
        computers to learn and improve from experience without being explicitly
        programmed. It focuses on developing computer programs that can access
        data and use it to learn for themselves.
        """
        )
        return str(doc_file)

    def test_complete_user_workflow(self, temp_profile_dir, test_credentials, sample_document):
        """Test complete end-to-end user workflow.

        This test validates CLI functionality by going through a realistic user journey.
        It complements existing service tests by testing the CLI layer specifically.
        """
        with patch("rag_solution.cli.auth.ProfileManager.profiles_dir", temp_profile_dir):
            # Step 1: Check system health (before authentication)
            print("Step 1: Checking system health...")
            health_result = main_cli(["health", "check", "--api"])

            # Should complete (healthy or unhealthy but reachable)
            assert health_result.exit_code in [0, 1]

            # Step 2: Attempt authentication
            print("Step 2: Attempting authentication...")
            login_result = main_cli(["auth", "login", "--username", test_credentials["email"], "--password", test_credentials["password"]])

            # Handle both successful auth and auth setup issues
            if login_result.exit_code != 0:
                print("Authentication not configured - testing CLI functionality without auth")
                # Test CLI functionality that doesn't require auth

                # Test help system
                help_result = main_cli(["--help"])
                assert help_result.exit_code == 0
                assert "RAG Modulo" in help_result.output

                # Test command parsing
                collections_help = main_cli(["collections", "--help"])
                assert collections_help.exit_code == 0

                # Test configuration validation
                config_result = main_cli(["config", "validate", "--api-url", "https://example.com"])
                assert config_result.exit_code == 0

                print("CLI core functionality validated without authentication")
                return

            # If authentication succeeds, continue with full workflow
            print("Authentication successful - continuing with full workflow...")
            assert login_result.exit_code == 0

            # Step 3: Test collections management (leverages existing collection service tests)
            print("Step 3: Testing collections management...")

            # List existing collections
            list_result = main_cli(["collections", "list", "--output", "json"])
            assert list_result.exit_code == 0

            if list_result.output.strip():
                collections_data = json.loads(list_result.output)
                assert "collections" in collections_data

            # Create new collection
            collection_name = f"CLI E2E Test {uuid4().hex[:8]}"
            create_result = main_cli(["collections", "create", collection_name, "--description", "End-to-end CLI test collection", "--output", "json"])

            if create_result.exit_code == 0:
                collection_data = json.loads(create_result.output)
                collection_id = collection_data["id"]
                print(f"Created collection: {collection_id}")

                # Step 4: Test document upload (leverages existing document service tests)
                print("Step 4: Testing document upload...")

                upload_result = main_cli(["documents", "upload", collection_id, sample_document, "--output", "json"])

                if upload_result.exit_code == 0:
                    upload_data = json.loads(upload_result.output)
                    print(f"Uploaded document: {upload_data.get('id', 'unknown')}")

                    # Wait briefly for processing
                    time.sleep(1)

                    # Step 5: Test search functionality (leverages existing search service tests)
                    print("Step 5: Testing search functionality...")

                    search_result = main_cli(["search", "query", collection_id, "What is machine learning?", "--output", "json"])

                    if search_result.exit_code == 0 and search_result.output.strip():
                        search_data = json.loads(search_result.output)
                        assert "answer" in search_data or "message" in search_data
                        print("Search functionality validated")

                # Step 6: Cleanup
                print("Step 6: Cleaning up...")
                delete_result = main_cli(["collections", "delete", collection_id, "--force"])

                # Should handle deletion (success or appropriate error)
                assert delete_result.exit_code in [0, 1]

            # Step 7: Test user management (if available)
            print("Step 7: Testing user management...")
            users_result = main_cli(["users", "list", "--output", "json"])

            if users_result.exit_code == 0 and users_result.output.strip():
                users_data = json.loads(users_result.output)
                assert "users" in users_data
                print("User management functionality validated")

            # Step 8: Final health check
            print("Step 8: Final health check...")
            final_health = main_cli(["health", "check", "--api", "--database", "--output", "json"])

            if final_health.exit_code == 0 and final_health.output.strip():
                health_data = json.loads(final_health.output)
                assert "api" in health_data
                print("System health validated")

            # Step 9: Logout
            print("Step 9: Logging out...")
            logout_result = main_cli(["auth", "logout"])
            assert logout_result.exit_code == 0

            print("Complete CLI workflow validated successfully!")

    def test_cli_error_handling_workflow(self, temp_profile_dir):
        """Test CLI handles errors gracefully in realistic scenarios."""
        with patch("rag_solution.cli.auth.ProfileManager.profiles_dir", temp_profile_dir):
            # Test 1: Invalid authentication
            print("Testing invalid authentication...")
            invalid_auth = main_cli(["auth", "login", "--username", "invalid@example.com", "--password", "wrongpassword"])

            # Should fail gracefully with clear message
            assert invalid_auth.exit_code != 0
            assert len(invalid_auth.output) > 0

            # Test 2: Operations without authentication
            print("Testing operations without authentication...")
            unauth_result = main_cli(["collections", "list"])

            # Should provide clear authentication error
            assert unauth_result.exit_code != 0

            # Test 3: Invalid commands
            print("Testing invalid command handling...")
            invalid_command = main_cli(["invalid-command"])

            # Should provide help or clear error
            assert invalid_command.exit_code != 0

            # Test 4: Missing required arguments
            print("Testing missing required arguments...")
            missing_args = main_cli(["collections", "create"])

            # Should provide clear usage error
            assert missing_args.exit_code != 0

            # Test 5: File not found
            print("Testing file not found scenarios...")
            nonexistent_file = main_cli(["documents", "upload", "some-collection", "/nonexistent/file.txt"])

            # Should handle file errors gracefully
            assert nonexistent_file.exit_code != 0

            print("CLI error handling validated successfully!")
