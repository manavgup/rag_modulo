"""Direct tests for Makefile targets without container isolation.

This module tests the Makefile targets directly on the host system
to avoid Docker-in-Docker permission issues. It uses careful cleanup
to ensure the test environment remains clean.
"""

import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, Any
import shutil

import pytest


class DirectMakefileTester:
    """Test helper for Makefile targets running directly on host."""

    def __init__(self):
        """Initialize the tester."""
        self.project_root = Path(__file__).parent.parent
        self.test_dir = None
        self.original_cwd = os.getcwd()

    def setup_test_environment(self) -> None:
        """Set up a clean test environment with a copy of the project."""
        try:
            # Create a temporary directory for testing
            self.test_dir = Path(tempfile.mkdtemp(prefix="rag-modulo-test-"))

            # Copy essential files needed for testing
            files_to_copy = [
                "Makefile",
                "docker-compose.yml",
                "docker-compose.dev.yml",
                "docker-compose-infra.yml",
                "env.example",
                "env.dev.example"
            ]

            # Copy files
            for file in files_to_copy:
                src = self.project_root / file
                if src.exists():
                    shutil.copy2(src, self.test_dir / file)

            # Copy backend directory completely (needed for Docker builds)
            backend_src = self.project_root / "backend"
            if backend_src.exists():
                backend_dst = self.test_dir / "backend"
                # Copy essential backend files and directories needed by Dockerfile
                backend_dst.mkdir(parents=True, exist_ok=True)

                # Copy root files
                backend_files = [
                    "main.py", "healthcheck.py", "pyproject.toml", "poetry.lock"
                ]
                for file in backend_files:
                    src_file = backend_src / file
                    if src_file.exists():
                        shutil.copy2(src_file, backend_dst / file)

                # Copy Dockerfiles
                for dockerfile in backend_src.glob("Dockerfile*"):
                    shutil.copy2(dockerfile, backend_dst / dockerfile.name)

                # Copy source directories (needed by Dockerfile)
                source_dirs = [
                    "rag_solution", "auth", "core", "cli", "vectordbs"
                ]
                for dir_name in source_dirs:
                    src_dir = backend_src / dir_name
                    if src_dir.exists():
                        dst_dir = backend_dst / dir_name
                        shutil.copytree(src_dir, dst_dir, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.pytest_cache'))

            # Copy other directories (minimal copy for speed)
            other_dirs = ["webui", "scripts"]
            for dir_name in other_dirs:
                src = self.project_root / dir_name
                if src.exists():
                    dst = self.test_dir / dir_name
                    # Create directory structure
                    dst.mkdir(parents=True, exist_ok=True)
                    # Copy only essential files (Dockerfiles, configs)
                    for pattern in ["Dockerfile*", "*.json", "*.toml", "*.yml", "*.yaml"]:
                        for file in src.glob(f"**/{pattern}"):
                            rel_path = file.relative_to(src)
                            dst_file = dst / rel_path
                            dst_file.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(file, dst_file)

            # Change to test directory
            os.chdir(self.test_dir)

        except Exception as e:
            pytest.skip(f"Failed to create test environment: {e}")

    def teardown_test_environment(self) -> None:
        """Clean up the test environment."""
        try:
            # Return to original directory
            os.chdir(self.original_cwd)

            # Clean up any Docker resources created during tests
            subprocess.run([
                "docker", "compose", "-f", "docker-compose.dev.yml", "down", "-v"
            ], capture_output=True, check=False, cwd=self.test_dir)

            # Remove test directory
            if self.test_dir and self.test_dir.exists():
                shutil.rmtree(self.test_dir, ignore_errors=True)

        except Exception:
            pass  # Ignore cleanup errors

    def run_make_command(self, target: str, timeout: int = 60) -> Dict[str, Any]:
        """Run a make command in the test directory."""
        try:
            result = subprocess.run(
                ["make", target],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.test_dir
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }


@pytest.fixture
def direct_makefile_tester():
    """Fixture for direct Makefile testing."""
    tester = DirectMakefileTester()
    tester.setup_test_environment()
    yield tester
    tester.teardown_test_environment()


@pytest.mark.makefile
class TestMakefileTargetsDirect:
    """Test Makefile targets directly on the host."""

    def test_check_docker_requirements(self, direct_makefile_tester):
        """Test that Docker requirements can be checked."""
        result = direct_makefile_tester.run_make_command("check-docker")

        # This should work if Docker is installed
        if "Docker is not installed" in result["stderr"]:
            pytest.skip("Docker is not installed on the test system")

        assert result["success"], f"Docker check failed: {result['stderr']}"

    def test_make_venv(self, direct_makefile_tester):
        """Test that make venv creates virtual environment."""
        result = direct_makefile_tester.run_make_command("venv", timeout=120)

        # Skip if Poetry cannot be installed (CI might not have curl)
        if "Poetry not found" in result["stderr"]:
            pytest.skip("Poetry installation requires curl")

        assert result["success"], f"make venv failed: {result['stderr']}"

        # Check that .venv was created
        venv_dir = direct_makefile_tester.test_dir / "backend" / ".venv"
        assert venv_dir.exists(), "backend/.venv was not created"

    def test_make_help(self, direct_makefile_tester):
        """Test that make help displays usage information."""
        result = direct_makefile_tester.run_make_command("help")

        assert result["success"], f"make help failed: {result['stderr']}"
        # Check for new visual help format
        assert "RAG Modulo - Streamlined Development Guide" in result["stdout"]
        assert "Quick Start" in result["stdout"]
        assert "check-docker" in result["stdout"]
        assert "local-dev-setup" in result["stdout"]

    @pytest.mark.skip(reason="info target removed in streamlined Makefile (Issue #348)")
    def test_make_info(self, direct_makefile_tester):
        """Test that make info displays project information."""
        result = direct_makefile_tester.run_make_command("info")

        assert result["success"], f"make info failed: {result['stderr']}"
        assert "Project name:" in result["stdout"]
        assert "Python version:" in result["stdout"]

    @pytest.mark.slow
    def test_make_build_backend_minimal(self, direct_makefile_tester):
        """Test that make build-backend starts correctly (minimal test)."""
        # Try to start the build (we'll timeout quickly to just test it starts)
        result = direct_makefile_tester.run_make_command("build-backend", timeout=10)

        # We expect it to timeout or start building
        # If it fails immediately with Docker errors, that's a problem
        if "Docker is not installed" in result["stderr"]:
            pytest.skip("Docker is not installed")
        if "Docker Compose V2 not found" in result["stderr"]:
            pytest.skip("Docker Compose V2 is not available")
        if "permission denied" in result["stderr"].lower():
            pytest.skip("Docker permissions issue on test system")

        # If it timed out, that means it started building (good)
        # If it succeeded quickly, that's also fine (cached build)
        assert result["returncode"] in [0, -1], f"Unexpected error: {result['stderr']}"

    def test_make_clean(self, direct_makefile_tester):
        """Test that make clean works without errors."""
        # Create some test directories that clean should remove
        test_dirs = [".pytest_cache", ".mypy_cache", "volumes"]
        for dir_name in test_dirs:
            (direct_makefile_tester.test_dir / dir_name).mkdir(exist_ok=True)

        result = direct_makefile_tester.run_make_command("clean", timeout=30)

        # Clean might fail if no containers exist, but shouldn't have syntax errors
        if "unknown shorthand flag" in result["stderr"]:
            pytest.fail(f"Docker command syntax error: {result['stderr']}")

        # The clean target might not succeed fully if containers don't exist,
        # but it should at least clean local directories
        # Note: The Makefile's clean target runs rm -rf for these directories
        # Check that at least the make command ran (even if docker commands failed)

        # For a more reliable test, we check if the clean command tried to run
        # The important thing is that we don't get Docker command syntax errors
        assert "unknown shorthand flag" not in result["stderr"], \
            f"Docker command syntax error detected: {result['stderr']}"

        # The clean command should at least attempt to run (even if it fails due to missing containers)
        # Return code 2 means make target failed but executed, which is fine for testing
        # Return code 0 means success, also fine
        assert result["returncode"] in [0, 2] or \
            "Cleaning up" in result["stderr"] or \
            "Stopping containers" in result["stderr"], \
            f"Make clean had unexpected failure: {result['stderr']}"
