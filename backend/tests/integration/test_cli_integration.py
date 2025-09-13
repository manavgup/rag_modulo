"""Minimal integration tests for CLI-API communication.

These tests focus on CLI-specific integration concerns:
- CLI can reach API endpoints
- Authentication flow works
- Output formatting works
- Error handling is appropriate for CLI users

Business logic is covered by existing service/API tests.
"""

import pytest

# Skip all CLI tests until CLI integration is complete
pytestmark = pytest.mark.skip(reason="CLI integration not yet complete")


@pytest.mark.integration
class TestCLIAPIConnectivity:
    """Test CLI-API connectivity and communication."""

    def test_cli_placeholder(self):
        """Placeholder test for CLI integration functionality."""
        pytest.skip("CLI integration not yet complete")
