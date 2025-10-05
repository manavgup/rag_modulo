import re
from playwright.sync_api import sync_playwright, expect

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Navigate to the collection detail page
    page.goto("http://localhost:3000/lightweight-collections/8f60c52e-9d68-4a49-82a9-c8a46356a59b")

    # Wait for the page to load
    expect(page.get_by_role("heading", name=re.compile(r"Financial Reports Q2 2024", i))).to_be_visible()

    # Find the first download button
    download_button = page.get_by_title("Download document").first
    expect(download_button).to_be_visible()

    # Click the download button
    download_button.click()

    # Wait for the "Download Started" notification to appear
    notification = page.get_by_text("Download Started")
    expect(notification).to_be_visible()

    # Take a screenshot
    page.screenshot(path="jules-scratch/verification/verification.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)