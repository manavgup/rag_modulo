"""Integration fixtures - Real services via testcontainers."""

from collections.abc import Generator
from pathlib import Path

import pytest

try:
    import pymupdf
except ImportError:
    pymupdf = None


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
    page2.insert_text((100, 100), "Table Example", fontsize=12)
    # Add table content here

    # Page 3: Image placeholder
    page3 = doc.new_page()
    page3.insert_text((100, 100), "Image Example", fontsize=12)
    page3.insert_text((100, 150), "[Image would be here]", fontsize=10)

    doc.save(test_file)
    doc.close()

    yield test_file

    if test_file.exists():
        test_file.unlink()


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """Test database URL for integration tests."""
    return "postgresql://test:test@localhost:5432/test_db"


@pytest.fixture(scope="session")
def test_milvus_config() -> dict:
    """Test Milvus configuration for integration tests."""
    return {"host": "localhost", "port": 19530, "collection_name": "test_collection"}


@pytest.fixture(scope="session")
def test_minio_config() -> dict:
    """Test MinIO configuration for integration tests."""
    return {"endpoint": "localhost:9000", "access_key": "test", "secret_key": "test123", "bucket": "test-bucket"}
