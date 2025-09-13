"""Atomic tests for CLI core functionality - command parsing, config, and authentication logic."""

import pytest

# Skip all CLI tests until CLI integration is complete
pytestmark = pytest.mark.skip(reason="CLI integration not yet complete")


@pytest.mark.atomic
class TestCLICommandParsing:
    """Test CLI command parsing and configuration."""

    def test_cli_placeholder(self):
        """Placeholder test for CLI core functionality."""
        pytest.skip("CLI integration not yet complete")
