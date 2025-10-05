import re
from playwright.sync_api import sync_playwright, Page, expect

def verify_agents_section(page: Page):
    """
    This script verifies that the 'Available Agents' section is visible
    on the collection detail page.
    """
    # 1. Arrange: Go to the collections page.
    # The frontend is running on localhost:3000
    page.goto("http://localhost:3000/lightweight-collections")

    # 2. Act: Find the first collection link and click it.
    # We wait for the page to load and collections to be listed.
    # We'll click the first link that goes to a collection detail page.
    collection_link = page.locator('a[href^="/lightweight-collections/"]').first
    expect(collection_link).to_be_visible()
    collection_link.click()

    # 3. Assert: Confirm the "Available Agents" section is visible.
    # We expect to find a heading with the text "Available Agents".
    agents_heading = page.get_by_role("heading", name="Available Agents")
    expect(agents_heading).to_be_visible()

    # 4. Screenshot: Capture the final result for visual verification.
    page.screenshot(path="jules-scratch/verification/verification.png")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        verify_agents_section(page)
        browser.close()

if __name__ == "__main__":
    main()