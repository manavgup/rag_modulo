"""
Playwright test configuration and fixtures for RAG Modulo.

Based on IBM MCP Context Forge testing patterns.
"""
import os
import pytest
from playwright.sync_api import Playwright, Browser, Page, BrowserContext
from typing import Generator


# Test configuration
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
TEST_TIMEOUT = int(os.getenv("TEST_TIMEOUT", "30000"))  # 30 seconds
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"


@pytest.fixture(scope="session")
def browser_type_launch_args():
    """Browser launch arguments for consistent testing."""
    return {
        "headless": HEADLESS,
        "slow_mo": 50 if not HEADLESS else 0,  # Slow down for debugging
        "timeout": TEST_TIMEOUT,
        "args": [
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--no-sandbox",
            "--disable-dev-shm-usage"
        ]
    }


@pytest.fixture(scope="session")
def browser(playwright: Playwright, browser_type_launch_args) -> Generator[Browser, None, None]:
    """Browser instance for the test session."""
    browser = playwright.chromium.launch(**browser_type_launch_args)
    yield browser
    browser.close()


@pytest.fixture
def context(browser: Browser) -> Generator[BrowserContext, None, None]:
    """Browser context with mock authentication setup."""
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        ignore_https_errors=True,
        extra_http_headers={
            # Mock authentication headers for development mode
            "Authorization": "Bearer mock-dev-token",
            "X-Mock-Auth": "true"
        }
    )

    # Set local storage for mock authentication
    context.add_init_script("""
        localStorage.setItem('access_token', 'mock-dev-token');
        localStorage.setItem('mock_auth_enabled', 'true');
    """)

    yield context
    context.close()


@pytest.fixture
def page(context: BrowserContext) -> Generator[Page, None, None]:
    """Page instance with common setup."""
    page = context.new_page()

    # Set default timeout
    page.set_default_timeout(TEST_TIMEOUT)

    # Add console and error logging for debugging
    page.on("console", lambda msg: print(f"Console {msg.type}: {msg.text}"))
    page.on("pageerror", lambda err: print(f"Page error: {err}"))

    yield page
    page.close()


@pytest.fixture
def authenticated_page(page: Page) -> Page:
    """Page with authenticated session."""
    # Navigate to frontend and ensure mock auth is active
    page.goto(FRONTEND_URL)

    # Wait for page to load and check if authentication bypass is working
    page.wait_for_load_state("networkidle")

    # Verify we can access protected routes
    try:
        page.goto(f"{FRONTEND_URL}/collections")
        page.wait_for_selector("h1", timeout=5000)
    except Exception as e:
        pytest.fail(f"Failed to access protected route with mock auth: {e}")

    return page


@pytest.fixture
def test_collection_data():
    """Sample collection data for testing."""
    return {
        "name": "Test Collection",
        "description": "A test collection for Playwright tests",
        "documents": [
            {
                "name": "test-document.pdf",
                "content": "This is a test document for RAG testing.",
                "type": "PDF"
            }
        ]
    }


@pytest.fixture
def test_search_queries():
    """Sample search queries for testing."""
    return [
        "What is machine learning?",
        "Explain neural networks",
        "How does RAG work?",
        "What are the benefits of vector databases?"
    ]


# Pytest markers configuration
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "smoke: Quick validation tests (< 30s)"
    )
    config.addinivalue_line(
        "markers", "auth: Authentication and authorization tests"
    )
    config.addinivalue_line(
        "markers", "api: Frontend-backend integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end workflow tests"
    )
    config.addinivalue_line(
        "markers", "slow: Long-running tests (> 2min)"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Add smoke marker to smoke tests
        if "smoke" in item.name or "test_smoke" in item.nodeid:
            item.add_marker(pytest.mark.smoke)

        # Add auth marker to auth tests
        if "auth" in item.name or "test_auth" in item.nodeid:
            item.add_marker(pytest.mark.auth)

        # Add api marker to API tests
        if "api" in item.name or "test_api" in item.nodeid:
            item.add_marker(pytest.mark.api)

        # Add e2e marker to workflow tests
        if "workflow" in item.name or "e2e" in item.name:
            item.add_marker(pytest.mark.e2e)


# Helper functions for tests
def wait_for_api_response(page: Page, url_pattern: str, timeout: int = 10000):
    """Wait for specific API response."""
    with page.expect_response(lambda response: url_pattern in response.url, timeout=timeout) as response_info:
        pass
    return response_info.value


def check_element_text(page: Page, selector: str, expected_text: str, timeout: int = 5000):
    """Check if element contains expected text."""
    try:
        element = page.wait_for_selector(selector, timeout=timeout)
        actual_text = element.text_content()
        assert expected_text.lower() in actual_text.lower(), f"Expected '{expected_text}' in '{actual_text}'"
        return True
    except Exception:
        return False


def upload_test_file(page: Page, file_selector: str, file_content: str, file_name: str):
    """Upload a test file through file input."""
    # Create a temporary file for upload
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(file_content)
        temp_file_path = f.name

    try:
        # Upload the file
        page.set_input_files(file_selector, temp_file_path)
    finally:
        # Clean up
        os.unlink(temp_file_path)
