"""Pytest configuration for MCP server tests.

This module provides fixtures and configuration for MCP server tests.
Tests are skipped if the 'mcp' package is not available.

The collect_ignore list prevents pytest from importing test files
when the mcp module is not installed, avoiding ImportErrors during collection.
"""

# Check if mcp module is available BEFORE any test imports
try:
    import mcp  # noqa: F401

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

# If mcp is not available, ignore all test files in this directory
# This prevents ImportError during test collection
if not MCP_AVAILABLE:
    collect_ignore = [
        "test_auth.py",
        "test_main.py",
        "test_resources.py",
        "test_server.py",
        "test_tools.py",
        "test_types.py",
    ]
