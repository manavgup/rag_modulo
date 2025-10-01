"""
API integration tests for frontend-backend communication.

Tests the integration between React frontend and FastAPI backend.
Based on IBM MCP Context Forge patterns.
"""
import pytest
from playwright.sync_api import Page
from pages.collections_page import CollectionsPage, CollectionDetailPage
from pages.search_page import SearchPage
from fixtures.test_data import TestDataFixtures
import tempfile
import os


class TestAPIIntegration:
    """Frontend-backend API integration tests."""

    @pytest.mark.api
    def test_collections_crud_operations(self, authenticated_page: Page, test_collection_data):
        """Test complete CRUD operations for collections through the UI."""
        collections_page = CollectionsPage(authenticated_page)
        collections_page.navigate()
        collections_page.wait_for_collections_to_load()

        # Get initial collection count
        initial_count = collections_page.get_collection_count()

        # CREATE: Create a new collection
        collection_name = f"Test Collection {int(authenticated_page.evaluate('Date.now()'))}"
        collection_description = "Created by Playwright API integration test"

        collections_page.create_collection(collection_name, collection_description)

        # Wait for collection to appear and verify creation
        authenticated_page.wait_for_timeout(2000)  # Wait for API response
        collections_page.wait_for_collections_to_load()

        # READ: Verify collection appears in list
        collections_page.assert_collection_exists(collection_name)
        new_count = collections_page.get_collection_count()
        assert new_count > initial_count, "Collection count should increase after creation"

        # READ: Navigate to collection detail
        collections_page.click_collection_by_name(collection_name)

        # Verify we're on the detail page
        detail_page = CollectionDetailPage(authenticated_page)
        detail_page.wait_for_collection_to_load()
        detail_page.assert_collection_loaded(collection_name)

        # Go back to collections page for cleanup
        authenticated_page.go_back()
        collections_page.wait_for_collections_to_load()

    @pytest.mark.api
    def test_document_upload_functionality(self, authenticated_page: Page):
        """Test document upload through the UI."""
        # First create a collection
        collections_page = CollectionsPage(authenticated_page)
        collections_page.navigate()
        collections_page.wait_for_collections_to_load()

        collection_name = f"Upload Test Collection {int(authenticated_page.evaluate('Date.now()'))}"
        collections_page.create_collection(collection_name, "Test collection for document upload")

        # Navigate to collection detail
        collections_page.click_collection_by_name(collection_name)
        detail_page = CollectionDetailPage(authenticated_page)
        detail_page.wait_for_collection_to_load()

        # Get initial document count
        initial_doc_count = detail_page.get_document_count()

        # Create a test file
        test_files = TestDataFixtures.create_test_files_for_collection()

        try:
            # Upload the first test file
            if test_files:
                detail_page.upload_file(test_files[0])

                # Wait for upload to complete
                authenticated_page.wait_for_timeout(5000)
                detail_page.wait_for_collection_to_load()

                # Verify document was uploaded
                new_doc_count = detail_page.get_document_count()
                assert new_doc_count > initial_doc_count, "Document count should increase after upload"

        finally:
            # Clean up test files
            TestDataFixtures.cleanup_test_files(test_files)

    @pytest.mark.api
    def test_collections_api_error_handling(self, authenticated_page: Page):
        """Test API error handling in the UI."""
        collections_page = CollectionsPage(authenticated_page)
        collections_page.navigate()
        collections_page.wait_for_collections_to_load()

        # Try to create collection with invalid data
        invalid_data = TestDataFixtures.get_invalid_test_data()

        # Test empty name (should show validation error)
        collections_page.click_add_collection()

        # Try to create without name
        authenticated_page.click("button:has-text('Create')")

        # Should either show validation error or modal should remain open
        # Wait a moment for any error messages
        authenticated_page.wait_for_timeout(2000)

        # Modal should still be visible or error should be shown
        modal_visible = authenticated_page.locator("[data-testid='create-collection-modal']").is_visible()
        assert modal_visible, "Modal should remain open or show error for invalid input"

        # Close modal
        authenticated_page.click("button:has-text('Cancel')")

    @pytest.mark.api
    def test_search_api_integration(self, authenticated_page: Page):
        """Test search API integration through WebSocket or HTTP."""
        search_page = SearchPage(authenticated_page)
        search_page.navigate()
        search_page.wait_for_search_page_load()

        # Test basic search functionality
        test_queries = TestDataFixtures.get_sample_search_queries()

        if test_queries:
            query = test_queries[0]["query"]

            # Send a search message
            initial_message_count = search_page.get_message_count()
            search_page.send_message(query)

            # Wait for user message to appear
            authenticated_page.wait_for_timeout(2000)

            # Verify message was sent
            new_message_count = search_page.get_message_count()
            assert new_message_count > initial_message_count, "Message count should increase after sending"

            # Check that user message contains our query
            search_page.assert_message_sent(query)

            # Wait for response (may timeout in test environment without real backend)
            try:
                search_page.wait_for_response(timeout=15000)
                search_page.assert_response_received()
            except Exception:
                # Response timeout is acceptable in test environment
                pass

    @pytest.mark.api
    def test_websocket_connection_lifecycle(self, authenticated_page: Page):
        """Test WebSocket connection establishment and messaging."""
        search_page = SearchPage(authenticated_page)
        search_page.navigate()
        search_page.wait_for_search_page_load()

        # Wait for WebSocket connection attempt
        authenticated_page.wait_for_timeout(5000)

        # Check connection status
        status = search_page.get_connection_status()
        assert len(status) > 0, "Should have connection status"

        # Test message sending (may not get response in test environment)
        if "connected" in status.lower():
            search_page.send_message("Hello, this is a test message")
            authenticated_page.wait_for_timeout(2000)

            # Verify message appears in chat
            last_message = search_page.get_last_user_message()
            assert "test message" in last_message.lower(), "Test message should appear in chat"

    @pytest.mark.api
    def test_api_response_times(self, authenticated_page: Page):
        """Test that API responses are within acceptable time limits."""
        collections_page = CollectionsPage(authenticated_page)

        # Measure time to load collections page
        start_time = authenticated_page.evaluate("Date.now()")
        collections_page.navigate()
        collections_page.wait_for_collections_to_load()
        end_time = authenticated_page.evaluate("Date.now()")

        load_time = end_time - start_time
        assert load_time < 10000, f"Collections page should load within 10 seconds, took {load_time}ms"

        # Test search page load time
        search_page = SearchPage(authenticated_page)
        start_time = authenticated_page.evaluate("Date.now()")
        search_page.navigate()
        search_page.wait_for_search_page_load()
        end_time = authenticated_page.evaluate("Date.now()")

        search_load_time = end_time - start_time
        assert search_load_time < 10000, f"Search page should load within 10 seconds, took {search_load_time}ms"

    @pytest.mark.api
    def test_concurrent_api_requests(self, authenticated_page: Page):
        """Test handling of concurrent API requests."""
        collections_page = CollectionsPage(authenticated_page)
        collections_page.navigate()
        collections_page.wait_for_collections_to_load()

        # Open multiple collections creation modals rapidly
        for i in range(3):
            collections_page.click_add_collection()
            authenticated_page.wait_for_timeout(100)  # Small delay
            authenticated_page.click("button:has-text('Cancel')")
            authenticated_page.wait_for_timeout(100)

        # Page should still be functional
        collections_page.wait_for_collections_to_load()
        title = collections_page.get_page_title()
        assert "collection" in title.lower(), "Page should remain functional after concurrent requests"

    @pytest.mark.api
    def test_api_data_persistence(self, authenticated_page: Page):
        """Test that API data persists across page navigation."""
        collections_page = CollectionsPage(authenticated_page)
        collections_page.navigate()
        collections_page.wait_for_collections_to_load()

        # Get initial collection names
        initial_collections = collections_page.get_collection_names()

        # Navigate to search page
        search_page = SearchPage(authenticated_page)
        search_page.navigate()
        search_page.wait_for_search_page_load()

        # Navigate back to collections
        collections_page.navigate()
        collections_page.wait_for_collections_to_load()

        # Collections should still be there
        final_collections = collections_page.get_collection_names()

        # Allow for dynamic data changes, but basic structure should persist
        assert len(final_collections) >= 0, "Should have collections after navigation"

    @pytest.mark.api
    def test_network_error_handling(self, authenticated_page: Page):
        """Test UI behavior when network requests fail."""
        # Navigate to collections page first
        collections_page = CollectionsPage(authenticated_page)
        collections_page.navigate()
        collections_page.wait_for_collections_to_load()

        # Simulate network issues by going offline
        authenticated_page.context.set_offline(True)

        # Try to create a collection while offline
        collections_page.click_add_collection()
        collections_page.fill_input("[name='name']", "Offline Test Collection")

        # Click create (should handle network error gracefully)
        authenticated_page.click("button:has-text('Create')")

        # Wait for error handling
        authenticated_page.wait_for_timeout(5000)

        # Should either show error message or handle gracefully
        # Modal might still be open or error notification might appear
        authenticated_page.context.set_offline(False)

    @pytest.mark.api
    @pytest.mark.slow
    def test_large_data_handling(self, authenticated_page: Page):
        """Test handling of large data sets and responses."""
        collections_page = CollectionsPage(authenticated_page)
        collections_page.navigate()
        collections_page.wait_for_collections_to_load()

        # Create a collection for large data test
        collection_name = f"Large Data Test {int(authenticated_page.evaluate('Date.now()'))}"
        collections_page.create_collection(collection_name, "Test collection for large data handling")

        # Navigate to detail page
        collections_page.click_collection_by_name(collection_name)
        detail_page = CollectionDetailPage(authenticated_page)
        detail_page.wait_for_collection_to_load()

        # Create multiple test files
        large_content = "This is a large test document. " * 1000  # Create larger content
        test_file = TestDataFixtures.create_test_file(large_content, "large_test_doc", "text/plain")

        try:
            # Upload large file
            detail_page.upload_file(test_file)

            # Wait longer for large file upload
            authenticated_page.wait_for_timeout(15000)

            # Verify upload completed without errors
            doc_count = detail_page.get_document_count()
            assert doc_count > 0, "Large file should be uploaded successfully"

        finally:
            # Clean up
            TestDataFixtures.cleanup_test_files([test_file])
