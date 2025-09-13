"""Unit tests for CLI HTTP client wrapper - focuses on API communication, not business logic."""

import pytest

# Skip all CLI tests until CLI integration is complete
pytestmark = pytest.mark.skip(reason="CLI integration not yet complete")


@pytest.mark.unit
class TestRAGAPIClient:
    """Test RAG API client wrapper functionality."""

    def test_cli_placeholder(self):
        """Placeholder test for CLI client functionality."""
        pytest.skip("CLI integration not yet complete")
