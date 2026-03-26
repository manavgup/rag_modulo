"""Tests that mcp_server is properly registered as a Poetry package.

Validates that mcp_server is installable via Poetry's packages config
the same way core, rag_solution, auth, and vectordbs are. This ensures
`from mcp_server.X` imports work in all contexts (CI, Docker, local).
"""

import subprocess
import sys

import pytest

pytestmark = pytest.mark.unit


class TestMCPServerPackageRegistration:
    """Verify mcp_server is registered as a Poetry package."""

    def test_mcp_server_importable_as_top_level_package(self):
        """mcp_server should be importable as a top-level package.

        Spawns a subprocess (no pytest pythonpath influence) to verify
        Poetry's package installation makes mcp_server importable,
        matching how core/rag_solution/auth/vectordbs work.
        """
        result = subprocess.run(
            [sys.executable, "-c", "import mcp_server; print('OK')"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, (
            f"mcp_server not importable as top-level package.\n"
            f"stderr: {result.stderr}\n"
            f"Ensure mcp_server is in pyproject.toml [tool.poetry] packages."
        )

    def test_mcp_server_permissions_importable(self):
        """from mcp_server.permissions should work (used by auth.py internally)."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from mcp_server.permissions import DefaultPermissionSets, MCPPermissions; "
                "print('OK')",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, (
            f"mcp_server.permissions not importable.\n"
            f"stderr: {result.stderr}"
        )

    def test_core_also_importable(self):
        """core should be importable the same way (sanity check for parity)."""
        result = subprocess.run(
            [sys.executable, "-c", "import core; print('OK')"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, (
            f"core not importable as top-level package.\n"
            f"stderr: {result.stderr}"
        )
