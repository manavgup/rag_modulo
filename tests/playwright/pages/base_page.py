"""
Base page class for Page Object Model implementation.

Following IBM MCP Context Forge patterns for maintainable test code.
"""
import os

from playwright.sync_api import Locator, Page


class BasePage:
    """Base page class with common functionality for all pages."""

    def __init__(self, page: Page):
        self.page = page
        self.base_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        self.timeout = 10000  # 10 seconds default timeout

    def navigate_to(self, path: str = "") -> None:
        """Navigate to a specific path."""
        url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.base_url}/{path}"
        self.page.goto(url)
        self.wait_for_page_load()

    def wait_for_page_load(self) -> None:
        """Wait for page to fully load."""
        self.page.wait_for_load_state("networkidle", timeout=self.timeout)

    def wait_for_selector(self, selector: str, timeout: int | None = None) -> Locator:
        """Wait for selector and return locator."""
        timeout = timeout or self.timeout
        return self.page.wait_for_selector(selector, timeout=timeout)

    def click_element(self, selector: str, timeout: int | None = None) -> None:
        """Click an element after waiting for it."""
        element = self.wait_for_selector(selector, timeout)
        element.click()

    def fill_input(self, selector: str, value: str, timeout: int | None = None) -> None:
        """Fill an input field after waiting for it."""
        element = self.wait_for_selector(selector, timeout)
        element.fill(value)

    def get_text(self, selector: str, timeout: int | None = None) -> str:
        """Get text content of an element."""
        element = self.wait_for_selector(selector, timeout)
        return element.text_content() or ""

    def is_visible(self, selector: str, timeout: int = 5000) -> bool:
        """Check if element is visible."""
        try:
            element = self.page.wait_for_selector(selector, timeout=timeout)
            return element.is_visible()
        except Exception:
            return False

    def wait_for_url_contains(self, url_part: str, timeout: int | None = None) -> None:
        """Wait for URL to contain specific text."""
        timeout = timeout or self.timeout
        self.page.wait_for_url(lambda url: url_part in str(url), timeout=timeout)

    def wait_for_api_response(self, url_pattern: str, timeout: int | None = None):
        """Wait for specific API response."""
        timeout = timeout or self.timeout
        with self.page.expect_response(
            lambda response: url_pattern in response.url,
            timeout=timeout
        ) as response_info:
            pass
        return response_info.value

    def check_notification(self, message: str, notification_type: str = "success") -> bool:
        """Check if notification with specific message appears."""
        try:
            # Look for notification elements (adjust selector based on your notification system)
            notification_selector = f"[data-testid='notification-{notification_type}']"
            notification = self.page.wait_for_selector(notification_selector, timeout=5000)
            return message.lower() in notification.text_content().lower()
        except Exception:
            return False

    def upload_file(self, file_input_selector: str, file_path: str) -> None:
        """Upload a file through file input."""
        self.page.set_input_files(file_input_selector, file_path)

    def scroll_to_element(self, selector: str) -> None:
        """Scroll to make element visible."""
        element = self.wait_for_selector(selector)
        element.scroll_into_view_if_needed()

    def get_current_url(self) -> str:
        """Get current page URL."""
        return self.page.url

    def refresh_page(self) -> None:
        """Refresh the current page."""
        self.page.reload()
        self.wait_for_page_load()

    def take_screenshot(self, name: str) -> str:
        """Take a screenshot and return the path."""
        screenshot_dir = "tests/screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)
        screenshot_path = f"{screenshot_dir}/{name}.png"
        self.page.screenshot(path=screenshot_path)
        return screenshot_path

    def wait_for_loading_to_finish(self, loading_selector: str = "[data-testid='loading']") -> None:
        """Wait for loading indicator to disappear."""
        try:
            # Wait for loading indicator to appear first (optional)
            self.page.wait_for_selector(loading_selector, timeout=2000)
        except Exception:
            pass  # Loading might not appear if request is fast

        # Wait for loading indicator to disappear
        try:
            self.page.wait_for_selector(loading_selector, state="hidden", timeout=30000)
        except Exception:
            pass  # Loading indicator might not be present

    def assert_page_title(self, expected_title: str) -> None:
        """Assert page title matches expected value."""
        actual_title = self.page.title()
        assert expected_title.lower() in actual_title.lower(), \
            f"Expected title to contain '{expected_title}', got '{actual_title}'"

    def assert_element_text(self, selector: str, expected_text: str) -> None:
        """Assert element contains expected text."""
        actual_text = self.get_text(selector)
        assert expected_text.lower() in actual_text.lower(), \
            f"Expected '{expected_text}' in '{actual_text}'"

    def assert_element_visible(self, selector: str) -> None:
        """Assert element is visible."""
        assert self.is_visible(selector), f"Element '{selector}' is not visible"

    def assert_element_not_visible(self, selector: str) -> None:
        """Assert element is not visible."""
        assert not self.is_visible(selector), f"Element '{selector}' should not be visible"
