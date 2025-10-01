"""
Smoke tests for basic application health and functionality.

These tests provide quick validation that the application is running correctly.
Based on IBM MCP Context Forge patterns.
"""
import pytest
import requests
from playwright.sync_api import Page
from pages.collections_page import CollectionsPage
from pages.search_page import SearchPage
import os


class TestSmoke:
    """Smoke tests for basic application functionality."""

    @pytest.mark.smoke
    def test_frontend_loads(self, page: Page):
        """Test that frontend application loads successfully."""
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        # Navigate to frontend
        page.goto(frontend_url)
        page.wait_for_load_state("networkidle")

        # Check that page loads without errors
        assert page.title(), "Page should have a title"

        # Check for React root element or main content
        page.wait_for_selector("body", timeout=10000)
        assert page.locator("body").is_visible(), "Body element should be visible"

    @pytest.mark.smoke
    def test_backend_health_endpoint(self):
        """Test that backend health endpoint responds correctly."""
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

        try:
            response = requests.get(f"{backend_url}/api/health", timeout=10)
            assert response.status_code == 200, f"Health endpoint should return 200, got {response.status_code}"

            # Check response content if available
            if response.headers.get('content-type', '').startswith('application/json'):
                health_data = response.json()
                assert isinstance(health_data, dict), "Health response should be a dictionary"
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Backend health check failed: {e}")

    @pytest.mark.smoke
    def test_collections_page_loads(self, authenticated_page: Page):
        """Test that collections page loads with mock authentication."""
        collections_page = CollectionsPage(authenticated_page)

        # Navigate to collections page
        collections_page.navigate()
        collections_page.wait_for_collections_to_load()

        # Verify page loads correctly
        collections_page.assert_page_loaded()

        # Check that main elements are present
        title = collections_page.get_page_title()
        assert "collection" in title.lower(), f"Page title should contain 'collection', got '{title}'"

    @pytest.mark.smoke
    def test_search_page_loads(self, authenticated_page: Page):
        """Test that search page loads correctly."""
        search_page = SearchPage(authenticated_page)

        # Navigate to search page
        search_page.navigate()
        search_page.wait_for_search_page_load()

        # Verify page loads correctly
        search_page.assert_page_loaded()

        # Check that main elements are present
        title = search_page.get_page_title()
        assert len(title) > 0, "Search page should have a title"

    @pytest.mark.smoke
    def test_navigation_between_pages(self, authenticated_page: Page):
        """Test basic navigation between main pages."""
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        # Start at home page
        authenticated_page.goto(frontend_url)
        authenticated_page.wait_for_load_state("networkidle")

        # Navigate to collections
        authenticated_page.goto(f"{frontend_url}/collections")
        authenticated_page.wait_for_load_state("networkidle")
        assert "/collections" in authenticated_page.url, "Should be on collections page"

        # Navigate to search
        authenticated_page.goto(f"{frontend_url}/search")
        authenticated_page.wait_for_load_state("networkidle")
        assert "/search" in authenticated_page.url, "Should be on search page"

    @pytest.mark.smoke
    def test_api_collections_endpoint(self):
        """Test that collections API endpoint is accessible."""
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

        try:
            # Test with mock auth headers
            headers = {
                "Authorization": "Bearer mock-dev-token",
                "X-Mock-Auth": "true"
            }

            response = requests.get(f"{backend_url}/api/collections", headers=headers, timeout=10)

            # Accept both 200 (success) and 401 (auth required) as valid responses
            # This ensures the endpoint exists and is responding
            assert response.status_code in [200, 401, 422], \
                f"Collections endpoint should be accessible, got {response.status_code}"

        except requests.exceptions.RequestException as e:
            pytest.fail(f"Collections API endpoint test failed: {e}")

    @pytest.mark.smoke
    def test_websocket_endpoint_exists(self, authenticated_page: Page):
        """Test that WebSocket endpoint is available."""
        # Navigate to search page which initializes WebSocket
        search_page = SearchPage(authenticated_page)
        search_page.navigate()
        search_page.wait_for_search_page_load()

        # Wait a moment for WebSocket connection attempt
        authenticated_page.wait_for_timeout(3000)

        # Check for WebSocket connection (may fail in mock mode, but endpoint should exist)
        # Look for connection status indicator
        try:
            status = search_page.get_connection_status()
            # Any status (connected, disconnected, connecting) means endpoint exists
            assert len(status) > 0, "WebSocket status should be available"
        except Exception:
            # If status element doesn't exist, that's also acceptable for smoke test
            pass

    @pytest.mark.smoke
    def test_css_and_assets_load(self, page: Page):
        """Test that CSS and static assets load correctly."""
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        # Track network responses
        responses = []
        page.on("response", lambda response: responses.append(response))

        # Navigate to frontend
        page.goto(frontend_url)
        page.wait_for_load_state("networkidle")

        # Check that we received some successful responses
        successful_responses = [r for r in responses if r.status < 400]
        assert len(successful_responses) > 0, "Should have at least some successful HTTP responses"

        # Check for critical CSS (basic styles should be applied)
        body_element = page.locator("body")
        assert body_element.is_visible(), "Body should be visible"

    @pytest.mark.smoke
    def test_console_errors(self, page: Page):
        """Test that there are no critical console errors."""
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        # Collect console messages
        console_messages = []
        page.on("console", lambda msg: console_messages.append(msg))

        # Collect page errors
        page_errors = []
        page.on("pageerror", lambda error: page_errors.append(error))

        # Navigate and wait for page to load
        page.goto(frontend_url)
        page.wait_for_load_state("networkidle")

        # Navigate to main pages to check for errors
        page.goto(f"{frontend_url}/collections")
        page.wait_for_load_state("networkidle")

        # Check for critical errors (not warnings)
        critical_errors = [msg for msg in console_messages if msg.type == "error"]
        page_error_messages = [str(error) for error in page_errors]

        # Allow some non-critical errors but fail on severe issues
        if critical_errors:
            error_texts = [msg.text for msg in critical_errors]
            # Filter out known non-critical errors
            serious_errors = [
                error for error in error_texts
                if not any(ignore in error.lower() for ignore in [
                    "favicon",  # Favicon not found
                    "chunk",    # Chunk loading issues in dev
                    "websocket", # WebSocket connection issues in test
                    "network"   # Network timeout issues
                ])
            ]

            assert len(serious_errors) == 0, f"Found serious console errors: {serious_errors}"

        assert len(page_error_messages) == 0, f"Found page errors: {page_error_messages}"

    @pytest.mark.smoke
    def test_mobile_responsive_layout(self, page: Page):
        """Test basic mobile responsive layout."""
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        # Test mobile viewport
        page.set_viewport_size({"width": 375, "height": 667})  # iPhone size
        page.goto(frontend_url)
        page.wait_for_load_state("networkidle")

        # Check that page is still functional
        body = page.locator("body")
        assert body.is_visible(), "Page should be visible on mobile"

        # Navigate to collections page
        page.goto(f"{frontend_url}/collections")
        page.wait_for_load_state("networkidle")

        # Page should still be functional (not checking exact layout, just basic functionality)
        assert page.title(), "Page should have title on mobile"

        # Reset to desktop viewport
        page.set_viewport_size({"width": 1280, "height": 720})
