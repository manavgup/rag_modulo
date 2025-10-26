"""
Search page object for the chat/search interface.

Based on our LightweightSearchInterface component with WebSocket integration.
"""

from playwright.sync_api import Page

from .base_page import BasePage


class SearchPage(BasePage):
    """Page object for the search/chat interface."""

    def __init__(self, page: Page):
        super().__init__(page)
        self.path = "/search"

        # Selectors based on our search interface component
        self.selectors = {
            "page_title": "h1",
            "connection_status": "[data-testid='connection-status']",
            "collection_dropdown": "select",
            "chat_messages": "[data-testid='chat-message'], .max-w-3xl",
            "user_message": ".bg-blue-60",
            "assistant_message": ".bg-gray-20",
            "message_input": "input[placeholder*='Ask a question']",
            "send_button": "button[type='submit']",
            "typing_indicator": ":has-text('typing')",
            "loading_indicator": ":has-text('Searching')",
            "sources_button": "button:has-text('Show Sources')",
            "sources_container": ".mt-2.space-y-2",
            "source_item": ".bg-white.rounded-md",
            "source_title": ".font-medium",
            "source_content": ".text-xs.text-gray-70",
            "advanced_filters": "button:has-text('Advanced Filters')",
            "filters_panel": ".mt-4.space-y-3",
            "document_type_filter": "select",
            "date_filter_start": "input[type='date']:first",
            "date_filter_end": "input[type='date']:last"
        }

    def navigate(self) -> None:
        """Navigate to search page."""
        self.navigate_to(self.path)

    def navigate_with_collection(self, collection_id: str, collection_name: str) -> None:
        """Navigate to search page with collection context."""
        # Simulate navigation from collections page with state
        self.navigate_to(f"{self.path}?collection={collection_id}")
        # Wait for page to load with collection context
        self.wait_for_page_load()

    def wait_for_search_page_load(self) -> None:
        """Wait for search page to fully load."""
        self.wait_for_selector(self.selectors["page_title"])
        self.wait_for_selector(self.selectors["message_input"])

    def get_page_title(self) -> str:
        """Get the page title."""
        return self.get_text(self.selectors["page_title"])

    def get_connection_status(self) -> str:
        """Get WebSocket connection status."""
        try:
            return self.get_text(self.selectors["connection_status"])
        except Exception:
            return "unknown"

    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        status = self.get_connection_status()
        return "connected" in status.lower()

    def wait_for_connection(self, timeout: int = 10000) -> None:
        """Wait for WebSocket connection to be established."""
        self.page.wait_for_function(
            """() => {
                const statusElement = document.querySelector('[data-testid="connection-status"]');
                return statusElement && statusElement.textContent.toLowerCase().includes('connected');
            }""",
            timeout=timeout
        )

    def select_collection(self, collection_name: str) -> None:
        """Select a collection from dropdown."""
        self.page.select_option(self.selectors["collection_dropdown"], label=collection_name)

    def send_message(self, message: str) -> None:
        """Send a chat message."""
        self.fill_input(self.selectors["message_input"], message)
        self.click_element(self.selectors["send_button"])

    def wait_for_response(self, timeout: int = 30000) -> None:
        """Wait for assistant response to appear."""
        # Wait for loading indicator to appear and disappear
        try:
            self.page.wait_for_selector(self.selectors["loading_indicator"], timeout=5000)
            self.page.wait_for_selector(self.selectors["loading_indicator"], state="hidden", timeout=timeout)
        except Exception:
            pass  # Loading might be too fast to catch

        # Wait for new message to appear
        self.page.wait_for_timeout(1000)

    def get_message_count(self) -> int:
        """Get total number of messages in chat."""
        return len(self.page.locator(self.selectors["chat_messages"]).all())

    def get_last_message_text(self) -> str:
        """Get text of the last message."""
        messages = self.page.locator(self.selectors["chat_messages"])
        if messages.count() == 0:
            return ""
        return messages.last.text_content() or ""

    def get_last_user_message(self) -> str:
        """Get text of the last user message."""
        user_messages = self.page.locator(self.selectors["user_message"])
        if user_messages.count() == 0:
            return ""
        return user_messages.last.text_content() or ""

    def get_last_assistant_message(self) -> str:
        """Get text of the last assistant message."""
        assistant_messages = self.page.locator(self.selectors["assistant_message"])
        if assistant_messages.count() == 0:
            return ""
        return assistant_messages.last.text_content() or ""

    def has_sources_in_last_message(self) -> bool:
        """Check if last assistant message has sources."""
        assistant_messages = self.page.locator(self.selectors["assistant_message"])
        if assistant_messages.count() == 0:
            return False

        last_message = assistant_messages.last
        sources_button = last_message.locator(self.selectors["sources_button"])
        return sources_button.count() > 0

    def show_sources_for_last_message(self) -> None:
        """Show sources for the last assistant message."""
        assistant_messages = self.page.locator(self.selectors["assistant_message"])
        if assistant_messages.count() == 0:
            raise Exception("No assistant messages found")

        last_message = assistant_messages.last
        sources_button = last_message.locator(self.selectors["sources_button"])
        if sources_button.count() > 0:
            sources_button.click()

    def get_sources_count_for_last_message(self) -> int:
        """Get number of sources in last assistant message."""
        if not self.has_sources_in_last_message():
            return 0

        self.show_sources_for_last_message()
        assistant_messages = self.page.locator(self.selectors["assistant_message"])
        last_message = assistant_messages.last
        sources = last_message.locator(self.selectors["source_item"])
        return sources.count()

    def get_source_titles_for_last_message(self) -> list[str]:
        """Get list of source titles from last assistant message."""
        if not self.has_sources_in_last_message():
            return []

        self.show_sources_for_last_message()
        assistant_messages = self.page.locator(self.selectors["assistant_message"])
        last_message = assistant_messages.last
        source_titles = last_message.locator(self.selectors["source_title"])

        titles = []
        for i in range(source_titles.count()):
            titles.append(source_titles.nth(i).text_content() or "")
        return titles

    def is_typing_indicator_visible(self) -> bool:
        """Check if typing indicator is visible."""
        return self.is_visible(self.selectors["typing_indicator"])

    def wait_for_typing_to_finish(self, timeout: int = 10000) -> None:
        """Wait for typing indicator to disappear."""
        try:
            self.page.wait_for_selector(self.selectors["typing_indicator"], state="hidden", timeout=timeout)
        except Exception:
            pass  # Typing indicator might not appear

    def open_advanced_filters(self) -> None:
        """Open advanced filters panel."""
        self.click_element(self.selectors["advanced_filters"])
        self.wait_for_selector(self.selectors["filters_panel"])

    def set_document_type_filter(self, doc_type: str) -> None:
        """Set document type filter."""
        self.open_advanced_filters()
        self.page.select_option(self.selectors["document_type_filter"], label=doc_type)

    def set_date_range_filter(self, start_date: str, end_date: str) -> None:
        """Set date range filter (dates in YYYY-MM-DD format)."""
        self.open_advanced_filters()
        self.fill_input(self.selectors["date_filter_start"], start_date)
        self.fill_input(self.selectors["date_filter_end"], end_date)

    def send_message_and_wait_for_response(self, message: str, timeout: int = 30000) -> str:
        """Send message and wait for assistant response."""
        initial_message_count = self.get_message_count()
        self.send_message(message)

        # Wait for user message to appear
        self.page.wait_for_function(
            f"() => document.querySelectorAll('{self.selectors['chat_messages']}').length > {initial_message_count}",
            timeout=5000
        )

        # Wait for assistant response
        self.wait_for_response(timeout)
        return self.get_last_assistant_message()

    def assert_page_loaded(self) -> None:
        """Assert that search page is properly loaded."""
        self.assert_element_visible(self.selectors["page_title"])
        self.assert_element_visible(self.selectors["message_input"])

    def assert_message_sent(self, message: str) -> None:
        """Assert that a message was sent successfully."""
        last_user_message = self.get_last_user_message()
        assert message in last_user_message, f"Expected message '{message}' not found in '{last_user_message}'"

    def assert_response_received(self) -> None:
        """Assert that an assistant response was received."""
        last_assistant_message = self.get_last_assistant_message()
        assert len(last_assistant_message) > 0, "No assistant response received"

    def assert_has_sources(self) -> None:
        """Assert that the last response has sources."""
        assert self.has_sources_in_last_message(), "Last assistant message should have sources"

    def assert_connected(self) -> None:
        """Assert that WebSocket is connected."""
        assert self.is_connected(), "WebSocket should be connected"
