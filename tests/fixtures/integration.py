"""Integration fixtures - Real services via testcontainers."""

from collections.abc import Generator
from pathlib import Path

import pytest

from backend.core.config import get_settings

try:
    import pymupdf  # type: ignore[import-untyped]
except ImportError:
    pymupdf = None


@pytest.fixture(scope="function")
def integration_settings():
    """Integration test settings fixture."""
    return get_settings()


@pytest.fixture(scope="function")
def complex_test_pdf_path() -> Generator[Path, None, None]:
    """Fixture to create a robust PDF file with multiple pages, tables and images."""
    if pymupdf is None:
        pytest.skip("pymupdf not available")

    test_file = Path("/tmp/complex_test.pdf")

    doc = pymupdf.open()

    # Page 1: Text and Heading
    page1 = doc.new_page()
    page1.insert_text((100, 100), "This is a test document.")
    page1.insert_text((100, 150), "Heading 1", fontsize=14)
    page1.insert_text((100, 200), "This is some content under heading 1.")

    # Page 2: Table
    page2 = doc.new_page()
    page2.insert_text((100, 100), "Table Data")
    page2.insert_text((100, 120), "Row 1, Col 1")
    page2.insert_text((200, 120), "Row 1, Col 2")

    # Page 3: Image placeholder
    page3 = doc.new_page()
    page3.insert_text((100, 100), "Image placeholder")

    doc.save(test_file)
    doc.close()

    yield test_file

    # Cleanup
    if test_file.exists():
        test_file.unlink()
