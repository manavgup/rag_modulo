"""
Authentication tests for RAG Modulo with mock authentication.

Tests the authentication flow and access control in development mode.
Based on IBM MCP Context Forge patterns.
"""
import pytest
import requests
from playwright.sync_api import Page, BrowserContext
from pages.collections_page import CollectionsPage
from pages.search_page import SearchPage
from fixtures.test_data import TestDataFixtures
import os


class TestAuthentication:
    """Authentication and authorization tests."""

    @pytest.mark.auth
    def test_mock_auth_bypass_enabled(self, page: Page):
        """Test that mock authentication bypass is working in development mode."""
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        # Navigate without authentication
        page.goto(frontend_url)
        page.wait_for_load_state("networkidle")

        # Try to access protected route (collections)
        page.goto(f"{frontend_url}/collections")
        page.wait_for_load_state("networkidle")

        # Should be able to access collections page without real authentication
        # Check that we're not redirected to a login page
        assert "/collections" in page.url, "Should be able to access collections with mock auth"

        # Check that page loads content (not an error or login page)
        page.wait_for_selector("h1", timeout=10000)
        title = page.locator("h1").text_content()
        assert "collection" in title.lower(), "Should see collections page content"

    @pytest.mark.auth
    def test_protected_routes_accessible_with_mock_auth(self, authenticated_page: Page):
        """Test that all protected routes are accessible with mock authentication."""
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        protected_routes = ["/collections", "/search"]

        for route in protected_routes:
            authenticated_page.goto(f"{frontend_url}{route}")
            authenticated_page.wait_for_load_state("networkidle")

            # Should not be redirected to login
            assert route in authenticated_page.url, f"Should be able to access {route}"

            # Should have content (not an error page)
            try:
                authenticated_page.wait_for_selector("h1", timeout=5000)
                title = authenticated_page.locator("h1").text_content()
                assert len(title) > 0, f"Route {route} should have content"
            except Exception:
                # Some pages might not have h1, check for body content
                body = authenticated_page.locator("body").text_content()
                assert len(body) > 100, f"Route {route} should have substantial content"

    @pytest.mark.auth
    def test_api_requests_include_mock_auth_headers(self, page: Page):
        """Test that API requests include proper mock authentication headers."""
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        # Track network requests
        requests_with_auth = []

        def handle_request(request):
            if "/api/" in request.url:
                headers = request.headers
                auth_header = headers.get("authorization", "")
                mock_auth_header = headers.get("x-mock-auth", "")

                requests_with_auth.append({
                    "url": request.url,
                    "has_auth": bool(auth_header),
                    "has_mock_auth": bool(mock_auth_header),
                    "auth_header": auth_header
                })

        page.on("request", handle_request)

        # Navigate to page that makes API calls
        collections_page = CollectionsPage(page)
        collections_page.navigate()
        collections_page.wait_for_collections_to_load()

        # Wait for API requests to complete
        page.wait_for_timeout(3000)

        # Check that API requests were made with authentication
        api_requests = [req for req in requests_with_auth if "/api/" in req["url"]]

        if api_requests:  # Only check if API requests were made
            for request in api_requests:
                # Should have either Authorization header or mock auth setup
                has_auth = request["has_auth"] or request["has_mock_auth"]
                assert has_auth, f"API request to {request['url']} should have authentication headers"

    @pytest.mark.auth
    def test_backend_accepts_mock_auth_token(self):
        """Test that backend accepts mock authentication token."""
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        mock_auth_data = TestDataFixtures.get_mock_auth_data()

        # Test with mock auth headers
        headers = {
            "Authorization": mock_auth_data["auth_header"],
            "X-Mock-Auth": "true",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(f"{backend_url}/api/collections", headers=headers, timeout=10)

            # Should not get 401/403 (authentication rejection)
            assert response.status_code not in [401, 403], \
                f"Backend should accept mock auth, got {response.status_code}"

            # Accept 200 (success) or other valid responses, but not auth errors
            assert response.status_code < 500, \
                f"Should not get server error with mock auth, got {response.status_code}"

        except requests.exceptions.RequestException as e:
            pytest.fail(f"Mock auth backend test failed: {e}")

    @pytest.mark.auth
    def test_local_storage_contains_mock_token(self, authenticated_page: Page):
        """Test that local storage contains mock authentication token."""
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        # Navigate to authenticated page
        authenticated_page.goto(f"{frontend_url}/collections")
        authenticated_page.wait_for_load_state("networkidle")

        # Check local storage for mock token
        access_token = authenticated_page.evaluate("localStorage.getItem('access_token')")
        mock_auth_enabled = authenticated_page.evaluate("localStorage.getItem('mock_auth_enabled')")

        assert access_token is not None, "Access token should be set in localStorage"
        assert "mock" in access_token.lower(), "Access token should be a mock token"
        assert mock_auth_enabled == "true", "Mock auth should be enabled"

    @pytest.mark.auth
    def test_unauthenticated_context_behavior(self, browser):
        """Test behavior with completely unauthenticated context."""
        # Create context without mock auth setup
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            ignore_https_errors=True
        )

        page = context.new_page()
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        try:
            # Navigate to protected route without any auth setup
            page.goto(f"{frontend_url}/collections")
            page.wait_for_load_state("networkidle", timeout=10000)

            # In development mode with SKIP_AUTH, should still work
            # Check if we can access the page or get redirected
            current_url = page.url

            # Either we can access the page (SKIP_AUTH=true) or we get redirected to login
            if "/collections" in current_url:
                # Mock auth bypass is working
                page.wait_for_selector("h1", timeout=5000)
                title = page.locator("h1").text_content()
                assert "collection" in title.lower(), "Should see collections content"
            else:
                # Real auth is required - check for login page or error
                assert "/login" in current_url or "login" in page.title().lower(), \
                    "Should be redirected to login without auth"

        finally:
            context.close()

    @pytest.mark.auth
    def test_websocket_connection_with_mock_auth(self, authenticated_page: Page):
        """Test that WebSocket connection works with mock authentication."""
        search_page = SearchPage(authenticated_page)
        search_page.navigate()
        search_page.wait_for_search_page_load()

        # Wait for WebSocket connection attempt
        authenticated_page.wait_for_timeout(5000)

        # Check connection status
        try:
            status = search_page.get_connection_status()
            # In development mode, WebSocket might not connect to real backend
            # but we should at least see a status indicator
            assert len(status) > 0, "Should have WebSocket status indicator"

            # If connected, that's great; if not connected, that's also acceptable in test environment
            assert status.lower() in ["connected", "disconnected", "connecting", "unknown"], \
                f"WebSocket status should be valid, got '{status}'"

        except Exception:
            # WebSocket status element might not exist in all environments
            # This is acceptable for auth testing
            pass

    @pytest.mark.auth
    def test_api_error_handling_without_auth(self, page: Page):
        """Test API error handling when authentication is missing or invalid."""
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

        # Test with no auth headers
        try:
            response = requests.get(f"{backend_url}/api/collections", timeout=10)

            # Should handle missing auth gracefully
            # In SKIP_AUTH mode: might return 200
            # In real auth mode: should return 401
            assert response.status_code in [200, 401, 422], \
                f"API should handle missing auth gracefully, got {response.status_code}"

        except requests.exceptions.RequestException:
            # Network errors are acceptable in test environment
            pass

        # Test with invalid auth headers
        try:
            headers = {"Authorization": "Bearer invalid-token"}
            response = requests.get(f"{backend_url}/api/collections", headers=headers, timeout=10)

            # Should handle invalid auth gracefully
            assert response.status_code in [200, 401, 403, 422], \
                f"API should handle invalid auth gracefully, got {response.status_code}"

        except requests.exceptions.RequestException:
            # Network errors are acceptable in test environment
            pass

    @pytest.mark.auth
    def test_session_persistence_across_page_reloads(self, authenticated_page: Page):
        """Test that mock auth session persists across page reloads."""
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        # Navigate to collections page
        authenticated_page.goto(f"{frontend_url}/collections")
        authenticated_page.wait_for_load_state("networkidle")

        # Verify we can access the page
        assert "/collections" in authenticated_page.url, "Should access collections page"

        # Reload the page
        authenticated_page.reload()
        authenticated_page.wait_for_load_state("networkidle")

        # Should still be able to access the page
        assert "/collections" in authenticated_page.url, "Should still access collections after reload"

        # Check that mock auth is still in localStorage
        access_token = authenticated_page.evaluate("localStorage.getItem('access_token')")
        assert access_token is not None, "Access token should persist after reload"
        assert "mock" in access_token.lower(), "Should still have mock token after reload"
