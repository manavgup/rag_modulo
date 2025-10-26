"""
Collections page object for managing document collections.

Based on our LightweightCollections and LightweightCollectionDetail components.
"""

from playwright.sync_api import Page

from .base_page import BasePage


class CollectionsPage(BasePage):
    """Page object for the collections management interface."""

    def __init__(self, page: Page):
        super().__init__(page)
        self.path = "/collections"

        # Selectors based on our frontend components
        self.selectors = {
            "page_title": "h1",
            "add_collection_btn": "button:has-text('Add a collection')",
            "collection_cards": "[data-testid='collection-card'], .card",
            "collection_title": ".card h3",
            "collection_description": ".card p",
            "collection_status": ".card .rounded-full",
            "chat_button": "button[title='Chat with collection']",
            "create_modal": "[data-testid='create-collection-modal']",
            "modal_name_input": "input[name='name'], input[placeholder*='name']",
            "modal_description_input": "textarea[name='description'], textarea[placeholder*='description']",
            "modal_create_btn": "button:has-text('Create')",
            "modal_cancel_btn": "button:has-text('Cancel')",
            "loading_spinner": ".animate-spin",
            "notification": "[data-testid*='notification']"
        }

    def navigate(self) -> None:
        """Navigate to collections page."""
        self.navigate_to(self.path)

    def wait_for_collections_to_load(self) -> None:
        """Wait for collections to finish loading."""
        # Wait for loading spinner to disappear
        self.wait_for_loading_to_finish(self.selectors["loading_spinner"])

        # Wait for page title to be visible
        self.wait_for_selector(self.selectors["page_title"])

    def get_page_title(self) -> str:
        """Get the page title text."""
        return self.get_text(self.selectors["page_title"])

    def click_add_collection(self) -> None:
        """Click the add collection button."""
        self.click_element(self.selectors["add_collection_btn"])
        # Wait for modal to appear
        self.wait_for_selector(self.selectors["create_modal"])

    def create_collection(self, name: str, description: str = "") -> None:
        """Create a new collection."""
        self.click_add_collection()

        # Fill in collection details
        self.fill_input(self.selectors["modal_name_input"], name)
        if description:
            self.fill_input(self.selectors["modal_description_input"], description)

        # Click create button
        self.click_element(self.selectors["modal_create_btn"])

        # Wait for modal to close and collection to be created
        self.page.wait_for_selector(self.selectors["create_modal"], state="hidden", timeout=10000)

    def get_collection_count(self) -> int:
        """Get the number of visible collections."""
        return len(self.page.locator(self.selectors["collection_cards"]).all())

    def get_collection_names(self) -> list[str]:
        """Get list of all collection names."""
        cards = self.page.locator(self.selectors["collection_cards"])
        names = []
        for i in range(cards.count()):
            title_element = cards.nth(i).locator(self.selectors["collection_title"])
            if title_element.count() > 0:
                names.append(title_element.text_content())
        return names

    def find_collection_by_name(self, name: str) -> int:
        """Find collection index by name. Returns -1 if not found."""
        names = self.get_collection_names()
        try:
            return names.index(name)
        except ValueError:
            return -1

    def click_collection_by_name(self, name: str) -> None:
        """Click on a collection by its name."""
        collection_index = self.find_collection_by_name(name)
        if collection_index == -1:
            raise Exception(f"Collection '{name}' not found")

        cards = self.page.locator(self.selectors["collection_cards"])
        cards.nth(collection_index).click()

    def click_chat_button_for_collection(self, name: str) -> None:
        """Click the chat button for a specific collection."""
        collection_index = self.find_collection_by_name(name)
        if collection_index == -1:
            raise Exception(f"Collection '{name}' not found")

        cards = self.page.locator(self.selectors["collection_cards"])
        chat_button = cards.nth(collection_index).locator(self.selectors["chat_button"])
        chat_button.click()

    def get_collection_status(self, name: str) -> str:
        """Get the status of a specific collection."""
        collection_index = self.find_collection_by_name(name)
        if collection_index == -1:
            raise Exception(f"Collection '{name}' not found")

        cards = self.page.locator(self.selectors["collection_cards"])
        status_element = cards.nth(collection_index).locator(self.selectors["collection_status"])
        return status_element.text_content().strip()

    def is_collection_ready(self, name: str) -> bool:
        """Check if collection status is 'ready'."""
        status = self.get_collection_status(name)
        return status.lower() == "ready"

    def wait_for_collection_ready(self, name: str, timeout: int = 30000) -> None:
        """Wait for collection to reach 'ready' status."""
        start_time = self.page.evaluate("Date.now()")

        while True:
            current_time = self.page.evaluate("Date.now()")
            if current_time - start_time > timeout:
                raise Exception(f"Collection '{name}' did not become ready within {timeout}ms")

            try:
                if self.is_collection_ready(name):
                    return
            except Exception:
                pass  # Collection might not exist yet

            self.page.wait_for_timeout(1000)  # Wait 1 second before checking again

    def assert_collection_exists(self, name: str) -> None:
        """Assert that a collection with the given name exists."""
        collection_index = self.find_collection_by_name(name)
        assert collection_index != -1, f"Collection '{name}' should exist but was not found"

    def assert_collection_not_exists(self, name: str) -> None:
        """Assert that a collection with the given name does not exist."""
        collection_index = self.find_collection_by_name(name)
        assert collection_index == -1, f"Collection '{name}' should not exist but was found"

    def assert_page_loaded(self) -> None:
        """Assert that the collections page is properly loaded."""
        self.assert_element_visible(self.selectors["page_title"])
        self.assert_element_text(self.selectors["page_title"], "Collections")


class CollectionDetailPage(BasePage):
    """Page object for individual collection detail view."""

    def __init__(self, page: Page):
        super().__init__(page)

        # Selectors for collection detail page
        self.selectors = {
            "page_title": "h1",
            "collection_description": "p",
            "back_button": "button:has([data-testid='arrow-left'])",
            "chat_button": "button:has-text('Chat')",
            "add_documents_btn": "button:has-text('Add Documents')",
            "documents_table": "table",
            "document_rows": "tbody tr",
            "upload_modal": "[data-testid='upload-modal']",
            "file_input": "input[type='file']",
            "upload_btn": "button:has-text('Upload')",
            "search_input": "input[placeholder*='Search documents']",
            "delete_selected_btn": "button:has-text('Delete')",
            "document_checkbox": "input[type='checkbox']",
            "loading_spinner": ".animate-spin"
        }

    def navigate_to_collection(self, collection_id: str) -> None:
        """Navigate to specific collection detail page."""
        self.navigate_to(f"/collections/{collection_id}")

    def wait_for_collection_to_load(self) -> None:
        """Wait for collection details to load."""
        self.wait_for_loading_to_finish(self.selectors["loading_spinner"])
        self.wait_for_selector(self.selectors["page_title"])

    def get_collection_name(self) -> str:
        """Get the collection name from the page."""
        return self.get_text(self.selectors["page_title"])

    def click_add_documents(self) -> None:
        """Click the add documents button."""
        self.click_element(self.selectors["add_documents_btn"])
        self.wait_for_selector(self.selectors["upload_modal"])

    def upload_file(self, file_path: str) -> None:
        """Upload a file to the collection."""
        self.click_add_documents()
        self.upload_file(self.selectors["file_input"], file_path)
        self.click_element(self.selectors["upload_btn"])
        # Wait for upload to complete
        self.page.wait_for_selector(self.selectors["upload_modal"], state="hidden", timeout=30000)

    def get_document_count(self) -> int:
        """Get the number of documents in the collection."""
        return len(self.page.locator(self.selectors["document_rows"]).all())

    def search_documents(self, query: str) -> None:
        """Search for documents in the collection."""
        self.fill_input(self.selectors["search_input"], query)
        # Wait a moment for search to filter results
        self.page.wait_for_timeout(1000)

    def click_chat_button(self) -> None:
        """Click the chat button to start chatting with collection."""
        self.click_element(self.selectors["chat_button"])

    def select_all_documents(self) -> None:
        """Select all documents using the header checkbox."""
        header_checkbox = self.page.locator("thead").locator(self.selectors["document_checkbox"])
        header_checkbox.click()

    def delete_selected_documents(self) -> None:
        """Delete selected documents."""
        self.click_element(self.selectors["delete_selected_btn"])
        # Wait for deletion to complete
        self.page.wait_for_timeout(2000)

    def assert_collection_loaded(self, expected_name: str) -> None:
        """Assert that the collection detail page is loaded."""
        self.assert_element_visible(self.selectors["page_title"])
        self.assert_element_text(self.selectors["page_title"], expected_name)
