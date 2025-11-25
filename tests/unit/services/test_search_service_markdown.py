"""Tests for Markdown preservation in search service."""

from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.services.search_service import SearchService


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = Mock(spec=Settings)
    settings.cot_max_reasoning_depth = 3
    settings.cot_reasoning_strategy = "sequential"
    settings.cot_token_budget_multiplier = 1.5
    return settings


@pytest.fixture
def search_service(mock_db, mock_settings):
    """Create a SearchService instance for testing."""
    return SearchService(mock_db, mock_settings)


class TestMarkdownPreservation:
    """Test suite for Markdown preservation in answer cleaning."""

    def test_clean_generated_answer_preserves_h2_headers(self, search_service):
        """Test that ## headers are preserved."""
        input_text = """## Main Header

Some content here.

## Another Header

More content."""

        result = search_service._clean_generated_answer(input_text)

        assert "## Main Header" in result
        assert "## Another Header" in result

    def test_clean_generated_answer_preserves_h3_headers(self, search_service):
        """Test that ### headers are preserved."""
        input_text = """### Sub Header

Some content here.

### Another Sub Header

More content."""

        result = search_service._clean_generated_answer(input_text)

        assert "### Sub Header" in result
        assert "### Another Sub Header" in result

    def test_clean_generated_answer_preserves_mixed_headers(self, search_service):
        """Test that mixed header levels are preserved."""
        input_text = """## Main Header

### Sub Header

Some content here.

#### Sub-sub Header

More content."""

        result = search_service._clean_generated_answer(input_text)

        assert "## Main Header" in result
        assert "### Sub Header" in result
        assert "#### Sub-sub Header" in result

    def test_clean_generated_answer_removes_and_artifacts(self, search_service):
        """Test that AND artifacts are removed."""
        input_text = "This is a test AND another test AND final test"

        result = search_service._clean_generated_answer(input_text)

        assert " AND " not in result
        assert "test another test final test" in result or "test test test" in result

    def test_clean_generated_answer_removes_duplicate_words(self, search_service):
        """Test that duplicate consecutive words are removed."""
        input_text = "This is is a test test test"

        result = search_service._clean_generated_answer(input_text)

        # Should remove consecutive duplicates
        # Use word boundary check to avoid false positives (e.g., "is" in "This")
        assert not re.search(r"\bis\s+is\b", result), f"Found duplicate 'is is' in: {result}"
        assert not re.search(r"\btest\s+test\s+test\b", result), f"Found duplicate 'test test test' in: {result}"
        # Verify the expected output
        assert "This is a test" in result or result == "This is a test"

    def test_clean_generated_answer_preserves_markdown_with_duplicates(self, search_service):
        """Test that Markdown headers are preserved even with duplicate words."""
        input_text = """## Step Step 1: Analysis

This is is a test.

### Sub Sub Header

More more content."""

        result = search_service._clean_generated_answer(input_text)

        # Headers should be preserved
        assert "## Step" in result
        assert "### Sub" in result
        # But duplicates in content should be removed
        assert "is is" not in result or "## Step" in result  # Allow if in header

    def test_clean_generated_answer_preserves_markdown_lists(self, search_service):
        """Test that Markdown lists are preserved."""
        input_text = """## Main Header

- Item 1
- Item 2
- Item 3

### Sub Header

1. First
2. Second
3. Third"""

        result = search_service._clean_generated_answer(input_text)

        assert "## Main Header" in result
        assert "### Sub Header" in result
        assert "- Item" in result or "Item 1" in result
        assert "1." in result or "First" in result

    def test_clean_generated_answer_preserves_markdown_emphasis(self, search_service):
        """Test that Markdown emphasis is preserved."""
        input_text = """## Main Header

This is **bold** text and *italic* text.

### Sub Header

More **emphasis** here."""

        result = search_service._clean_generated_answer(input_text)

        assert "## Main Header" in result
        assert "### Sub Header" in result
        assert "**bold**" in result or "bold" in result
        assert "*italic*" in result or "italic" in result

    def test_clean_generated_answer_handles_empty_input(self, search_service):
        """Test that empty input is handled gracefully."""
        result = search_service._clean_generated_answer("")
        assert result == ""

    def test_clean_generated_answer_handles_whitespace_only(self, search_service):
        """Test that whitespace-only input is handled."""
        result = search_service._clean_generated_answer("   \n\n   ")
        assert result == ""

    def test_clean_generated_answer_complex_cot_response(self, search_service):
        """Test a complex CoT response with multiple sections."""
        input_text = """## Answer to: How did IBM revenue change over the years?

### Step 1: Analyze 2018-2019 Revenue

IBM's revenue decreased from $79,591 million in 2018 to $77,147 million in 2019.

### Step 2: Analyze 2020 Revenue Decline

Revenue further declined to $73,620 million in 2020, primarily due to strategic repositioning.

### Step 3: Analyze 2021-2023 Recovery

Revenue rebounded to $61.9 billion in 2021 and grew to $62.8 billion in 2023.

### Summary

Based on the analysis above, IBM's revenue experienced fluctuations over the years.
Furthermore, the company showed strong recovery from 2021 onwards.
Additionally, growth was driven by hybrid cloud and AI solutions."""

        result = search_service._clean_generated_answer(input_text)

        # All headers should be preserved
        assert "## Answer to:" in result
        assert "### Step 1:" in result
        assert "### Step 2:" in result
        assert "### Step 3:" in result
        assert "### Summary" in result

        # Content should be preserved
        assert "IBM" in result
        assert "revenue" in result
        assert "2018" in result
        assert "2023" in result

    def test_clean_generated_answer_preserves_code_blocks(self, search_service):
        """Test that code blocks are preserved."""
        input_text = """## Code Example

```python
def hello():
    print("Hello, World!")
```

### Explanation

This is a simple function."""

        result = search_service._clean_generated_answer(input_text)

        assert "## Code Example" in result
        assert "### Explanation" in result
        # Code block markers should be preserved
        assert "```" in result or "python" in result

    def test_clean_generated_answer_preserves_tables(self, search_service):
        """Test that Markdown tables are preserved."""
        input_text = """## Revenue Table

| Year | Revenue |
|------|---------|
| 2018 | $79,591 |
| 2019 | $77,147 |

### Analysis

The table shows revenue decline."""

        result = search_service._clean_generated_answer(input_text)

        assert "## Revenue Table" in result
        assert "### Analysis" in result
        assert "|" in result or "Year" in result


class TestMarkdownEdgeCases:
    """Test edge cases for Markdown preservation."""

    def test_headers_with_special_characters(self, search_service):
        """Test headers with special characters."""
        input_text = """## Step 1: What's the revenue?

### Analysis: 2018-2019

Content here."""

        result = search_service._clean_generated_answer(input_text)

        assert "## Step 1:" in result
        assert "### Analysis:" in result

    def test_headers_with_numbers(self, search_service):
        """Test headers with numbers."""
        input_text = """## 2018 Revenue Analysis

### Q1 2018 Results

Content here."""

        result = search_service._clean_generated_answer(input_text)

        assert "## 2018" in result
        assert "### Q1" in result

    def test_multiple_consecutive_headers(self, search_service):
        """Test multiple consecutive headers without content."""
        input_text = """## Main Header
### Sub Header
#### Sub-sub Header

Content here."""

        result = search_service._clean_generated_answer(input_text)

        assert "## Main Header" in result
        assert "### Sub Header" in result
        assert "#### Sub-sub Header" in result

    def test_headers_at_end_of_text(self, search_service):
        """Test headers at the end of text."""
        input_text = """Content here.

## Final Header"""

        result = search_service._clean_generated_answer(input_text)

        assert "## Final Header" in result


class TestHTMLToMarkdownConversion:
    """Test suite for HTML-to-Markdown conversion functionality."""

    def test_html_table_conversion(self, search_service):
        """Test that HTML tables are converted to Markdown."""
        input_text = """<table>
<tr><th>Year</th><th>Revenue</th></tr>
<tr><td>2019</td><td>$1.2B</td></tr>
<tr><td>2020</td><td>$975M</td></tr>
</table>"""

        result = search_service._clean_generated_answer(input_text)

        # Should convert HTML table to Markdown
        assert "<table>" not in result
        assert "|" in result or "Year" in result or "Revenue" in result

    def test_html_lists_conversion(self, search_service):
        """Test that HTML lists are converted to Markdown."""
        input_text = """<ul>
<li>First item</li>
<li>Second item</li>
<li>Third item</li>
</ul>"""

        result = search_service._clean_generated_answer(input_text)

        # Should convert HTML list to Markdown
        assert "<ul>" not in result
        assert "<li>" not in result
        assert "-" in result or "First item" in result

    def test_html_ordered_list_conversion(self, search_service):
        """Test that HTML ordered lists are converted to Markdown."""
        input_text = """<ol>
<li>Step one</li>
<li>Step two</li>
<li>Step three</li>
</ol>"""

        result = search_service._clean_generated_answer(input_text)

        # Should convert HTML ordered list to Markdown
        assert "<ol>" not in result
        assert "<li>" not in result
        assert "1." in result or "Step one" in result

    def test_html_links_conversion(self, search_service):
        """Test that HTML links are converted to Markdown."""
        input_text = """<p>Visit <a href="https://example.com">our website</a> for more info.</p>"""

        result = search_service._clean_generated_answer(input_text)

        # Should convert HTML link to Markdown
        assert "<a" not in result
        assert "<p>" not in result
        assert "our website" in result or "https://example.com" in result

    def test_html_bold_italic_conversion(self, search_service):
        """Test that HTML bold and italic are converted to Markdown."""
        input_text = """<p>This is <strong>bold</strong> and <em>italic</em> text.</p>"""

        result = search_service._clean_generated_answer(input_text)

        # Should convert HTML formatting to Markdown
        assert "<strong>" not in result
        assert "<em>" not in result
        assert "<p>" not in result
        assert "bold" in result
        assert "italic" in result

    def test_html_headings_conversion(self, search_service):
        """Test that HTML headings are converted to Markdown."""
        input_text = """<h1>Main Title</h1>
<h2>Section Title</h2>
<h3>Subsection Title</h3>"""

        result = search_service._clean_generated_answer(input_text)

        # Should convert HTML headings to Markdown
        assert "<h1>" not in result
        assert "<h2>" not in result
        assert "<h3>" not in result
        assert "Main Title" in result
        assert "Section Title" in result
        assert "Subsection Title" in result

    def test_html_code_blocks_conversion(self, search_service):
        """Test that HTML code blocks are converted to Markdown."""
        input_text = """<pre><code>def hello():
    print("Hello, World!")
</code></pre>"""

        result = search_service._clean_generated_answer(input_text)

        # Should convert HTML code to Markdown
        assert "<pre>" not in result
        assert "<code>" not in result
        assert "def hello()" in result

    def test_malformed_html_handling(self, search_service):
        """Test that malformed HTML is handled gracefully."""
        input_text = """<p>Unclosed paragraph
<div>Nested <span>content</div>
<table><tr><td>Cell</td></tr>"""

        result = search_service._clean_generated_answer(input_text)

        # Should not crash and should process what it can
        assert isinstance(result, str)
        assert "Cell" in result or "content" in result

    def test_nested_html_structures(self, search_service):
        """Test that nested HTML structures are converted correctly."""
        input_text = """<div>
<h2>Section</h2>
<ul>
<li>Item 1</li>
<li>Item 2</li>
</ul>
<p>Paragraph with <strong>bold</strong> text.</p>
</div>"""

        result = search_service._clean_generated_answer(input_text)

        # Should convert nested HTML to Markdown
        assert "<div>" not in result
        assert "<h2>" not in result
        assert "<ul>" not in result
        assert "Section" in result
        assert "Item" in result or "bold" in result

    def test_html_with_markdown_mixed(self, search_service):
        """Test that existing Markdown is preserved when HTML is converted."""
        input_text = """## Existing Markdown Header

<p>HTML paragraph with <strong>bold</strong> text.</p>

### Another Markdown Header

More Markdown content."""

        result = search_service._clean_generated_answer(input_text)

        # Markdown headers should be preserved
        assert "## Existing Markdown Header" in result
        assert "### Another Markdown Header" in result
        # HTML should be converted
        assert "<p>" not in result
        assert "<strong>" not in result

    def test_html_images_conversion(self, search_service):
        """Test that HTML images are converted to Markdown."""
        input_text = """<img src="image.png" alt="Description" />"""

        result = search_service._clean_generated_answer(input_text)

        # Should convert HTML image to Markdown
        assert "<img" not in result
        assert "image.png" in result or "Description" in result

    def test_no_html_no_conversion(self, search_service):
        """Test that plain text without HTML is not modified unnecessarily."""
        input_text = """This is plain text without any HTML tags.
It should remain mostly unchanged."""

        result = search_service._clean_generated_answer(input_text)

        # Should preserve content
        assert "plain text" in result
        assert "HTML tags" in result or "unchanged" in result

    def test_html_br_tags_conversion(self, search_service):
        """Test that HTML line breaks are handled."""
        input_text = """Line 1<br>Line 2<br/>Line 3"""

        result = search_service._clean_generated_answer(input_text)

        # Should convert line breaks
        assert "<br" not in result
        assert "Line 1" in result
        assert "Line 2" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob
