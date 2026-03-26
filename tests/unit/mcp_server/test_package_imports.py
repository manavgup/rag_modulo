"""Tests that mcp_server is properly registered as a Poetry package.

Validates that all backend packages listed in pyproject.toml [tool.poetry]
packages are importable as top-level modules. Uses subprocess to spawn a
clean Python interpreter without pytest's pythonpath influence, ensuring
the test validates Poetry's package installation rather than test-runner
path manipulation.
"""

import subprocess
import sys

import pytest

pytestmark = pytest.mark.unit

SUBPROCESS_TIMEOUT = 30


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
            timeout=SUBPROCESS_TIMEOUT,
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
            timeout=SUBPROCESS_TIMEOUT,
        )
        assert result.returncode == 0, (
            f"mcp_server.permissions not importable.\n"
            f"stderr: {result.stderr}"
        )


class TestAllRegisteredPackages:
    """Guard against package-mode regression for all registered packages.

    Every package in pyproject.toml [tool.poetry] packages must be
    importable as a top-level module via Poetry's venv. This test
    catches accidental removal or misconfiguration of any package.
    """

    @pytest.mark.parametrize(
        "package_name",
        ["core", "rag_solution", "auth", "vectordbs", "mcp_server"],
    )
    def test_registered_package_importable(self, package_name: str):
        """Each registered package should be importable outside of pytest."""
        result = subprocess.run(
            [sys.executable, "-c", f"import {package_name}; print('OK')"],
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT,
        )
        assert result.returncode == 0, (
            f"Package '{package_name}' not importable as top-level module.\n"
            f"stderr: {result.stderr}\n"
            f"Check pyproject.toml [tool.poetry] packages config."
        )
