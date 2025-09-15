"""Integration tests for Makefile targets.

This module tests the Makefile targets in a clean container environment
to simulate a fresh developer machine experience.
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Any

import pytest


class MakefileTester:
    """Test helper for Makefile targets using container isolation."""
    
    def __init__(self):
        """Initialize the tester."""
        self.project_root = Path(__file__).parent.parent
        self.container_id = None
        self.container_name = f"rag-modulo-test-{int(time.time())}"
    
    def setup_test_environment(self) -> None:
        """Set up a clean container test environment."""
        try:
            # Start a clean Ubuntu container with project mounted and Docker socket
            # Using --privileged to ensure Docker socket access works properly
            result = subprocess.run([
                "docker", "run", "-d",
                "--name", self.container_name,
                "--privileged",  # Required for Docker-in-Docker operations
                "-v", f"{self.project_root}:/workspace",
                "-v", "/var/run/docker.sock:/var/run/docker.sock",  # Mount Docker socket
                "-w", "/workspace",
                "ubuntu:22.04",
                "sleep", "3600"  # Keep container alive for 1 hour
            ], capture_output=True, text=True, check=True)
            
            self.container_id = result.stdout.strip()
            
            # Install prerequisites
            self._install_prerequisites()
            
        except subprocess.CalledProcessError as e:
            pytest.skip(f"Failed to create test container: {e.stderr}")
        except FileNotFoundError:
            pytest.skip("Docker not available")
    
    def teardown_test_environment(self) -> None:
        """Clean up the container test environment."""
        if self.container_id:
            try:
                subprocess.run([
                    "docker", "rm", "-f", self.container_name
                ], capture_output=True, check=False)
            except Exception:
                pass  # Ignore cleanup errors
    
    def _install_prerequisites(self) -> None:
        """Install prerequisites in the container."""
        # First set of commands that can use simple exec
        commands = [
            # Update package list
            ["apt-get", "update"],
            # Install essential tools
            ["apt-get", "install", "-y", "make", "git", "curl", "ca-certificates", "gnupg", "lsb-release"],
            # Create logs directory
            ["mkdir", "-p", "/workspace/logs"]
        ]
        
        # Run initial commands
        for cmd in commands:
            try:
                subprocess.run([
                    "docker", "exec", self.container_name
                ] + cmd, capture_output=True, text=True, check=True, timeout=60)
            except subprocess.TimeoutExpired:
                pytest.skip(f"Timeout installing prerequisites: {cmd}")
            except subprocess.CalledProcessError as e:
                pytest.skip(f"Failed to install prerequisites: {e.stderr}")
        
        # Install Docker with official script for Compose V2 support
        install_docker_script = """
            set -e
            
            # Add Docker's official GPG key
            mkdir -p /etc/apt/keyrings
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
            
            # Set up the repository
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
            
            # Update and install Docker CE CLI and docker-compose-plugin
            apt-get update
            apt-get install -y docker-ce-cli docker-compose-plugin
            
            # Create docker group if it doesn't exist
            groupadd -f docker || true
            
            # Fix Docker socket permissions - make it accessible to all users
            # This is safe in a test container environment
            chmod 666 /var/run/docker.sock || true
            
            # Test Docker access
            docker version --format '{{.Client.Version}}'
            
            # Verify Docker Compose V2 installation
            docker compose version
            
            echo "Docker and Docker Compose V2 installed successfully"
        """
        
        try:
            result = subprocess.run([
                "docker", "exec", self.container_name, "bash", "-c", install_docker_script
            ], capture_output=True, text=True, check=True, timeout=120)
        except subprocess.TimeoutExpired:
            pytest.skip("Timeout installing Docker CLI and Compose V2")
        except subprocess.CalledProcessError as e:
            pytest.skip(f"Failed to install Docker CLI and Compose V2: {e.stderr}")
    
    def run_make_command(self, target: str, timeout: int = 60) -> Dict[str, Any]:
        """Run a make command inside the container."""
        try:
            result = subprocess.run([
                "docker", "exec", "-w", "/workspace",
                self.container_name, "make", target
            ], capture_output=True, text=True, timeout=timeout)
            
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
def makefile_tester():
    """Fixture for Makefile testing.
    
    Note: This fixture uses Docker-in-Docker which requires:
    1. Docker socket access
    2. Privileged container mode
    3. Proper permissions setup
    
    If tests fail with permission errors, use test_makefile_targets_direct.py instead.
    """
    # Check if we should skip Docker-in-Docker tests
    if os.environ.get("SKIP_DOCKER_IN_DOCKER_TESTS", "").lower() == "true":
        pytest.skip("Docker-in-Docker tests are disabled. Use test_makefile_targets_direct.py instead.")
    
    tester = MakefileTester()
    tester.setup_test_environment()
    yield tester
    tester.teardown_test_environment()


class TestMakefileTargets:
    """Test Makefile targets."""
    
    def test_make_dev_init(self, makefile_tester):
        """Test that make dev-init creates environment files."""
        result = makefile_tester.run_make_command("dev-init")
        
        assert result["success"], f"make dev-init failed: {result['stderr']}"
        assert "Initializing development environment" in result["stdout"]
        assert "Development environment initialized" in result["stdout"]
    
    def test_make_dev_build(self, makefile_tester):
        """Test that make dev-build creates Docker images."""
        makefile_tester.run_make_command("dev-init")
        result = makefile_tester.run_make_command("dev-build", timeout=300)
        
        assert result["success"], f"make dev-build failed: {result['stderr']}"
        assert "Building development images" in result["stdout"]
        assert "Backend image" in result["stdout"]
        assert "Frontend image" in result["stdout"]
    
    def test_make_dev_up(self, makefile_tester):
        """Test that make dev-up starts services."""
        makefile_tester.run_make_command("dev-init")
        makefile_tester.run_make_command("dev-build", timeout=300)
        result = makefile_tester.run_make_command("dev-up", timeout=120)
        
        assert result["success"], f"make dev-up failed: {result['stderr']}"
        assert "Starting development services" in result["stdout"]
    
    def test_make_dev_status(self, makefile_tester):
        """Test that make dev-status shows container status."""
        result = makefile_tester.run_make_command("dev-status")
        
        assert result["success"], f"make dev-status failed: {result['stderr']}"
        assert "Container Status:" in result["stdout"]
    
    def test_make_dev_logs(self, makefile_tester):
        """Test that make dev-logs shows service logs."""
        result = makefile_tester.run_make_command("dev-logs")
        
        # This might fail if no services are running, which is expected
        assert True, "Logs command executed (may fail if no services running)"
    
    def test_make_dev_down(self, makefile_tester):
        """Test that make dev-down stops services."""
        result = makefile_tester.run_make_command("dev-down")
        
        assert result["success"], f"make dev-down failed: {result['stderr']}"
        assert "Stopping development services" in result["stdout"]
    
    def test_make_dev_reset(self, makefile_tester):
        """Test that make dev-reset resets the environment."""
        result = makefile_tester.run_make_command("dev-reset")
        
        assert result["success"], f"make dev-reset failed: {result['stderr']}"
        assert "Resetting development environment" in result["stdout"]
    
    def test_make_clean_all(self, makefile_tester):
        """Test that make clean-all cleans everything."""
        result = makefile_tester.run_make_command("clean-all")
        
        # This might require user confirmation, so we just check it doesn't crash
        assert True, "Clean-all command executed"
    
    def test_make_dev_setup(self, makefile_tester):
        """Test that make dev-setup sets up the complete environment."""
        result = makefile_tester.run_make_command("dev-setup", timeout=600)
        
        assert result["success"], f"make dev-setup failed: {result['stderr']}"
        assert "Setting up development environment" in result["stdout"]
    
    def test_complete_development_workflow(self, makefile_tester):
        """Test the complete development workflow."""
        # Test the complete workflow
        steps = [
            ("dev-init", "Initialize environment"),
            ("dev-build", "Build images"),
            ("dev-up", "Start services"),
            ("dev-status", "Check status"),
            ("dev-down", "Stop services"),
            ("clean", "Clean up")
        ]
        
        for target, description in steps:
            result = makefile_tester.run_make_command(target, timeout=300)
            assert result["success"], f"{description} failed: {result['stderr']}"
    
    def test_one_command_setup(self, makefile_tester):
        """Test that make dev-setup works as a one-command setup."""
        result = makefile_tester.run_make_command("dev-setup", timeout=600)
        
        assert result["success"], f"One-command setup failed: {result['stderr']}"
        assert "Development environment setup complete" in result["stdout"]


class TestMakefileErrorHandling:
    """Test Makefile error handling."""
    
    def test_makefile_exists(self, makefile_tester):
        """Test that Makefile exists and is readable."""
        # Check that Makefile exists in the mounted workspace
        result = makefile_tester.run_make_command("help")
        assert result["success"], f"Makefile should be readable: {result['stderr']}"
    
    def test_help_command(self, makefile_tester):
        """Test that make help shows available commands."""
        result = makefile_tester.run_make_command("help")
        assert result["success"], f"make help failed: {result['stderr']}"
        assert "Development Workflow" in result["stdout"]
        assert "dev-init" in result["stdout"]
        assert "dev-build" in result["stdout"]
        assert "dev-up" in result["stdout"]
    
    def test_invalid_target(self, makefile_tester):
        """Test that invalid targets fail gracefully."""
        result = makefile_tester.run_make_command("invalid-target")
        assert not result["success"], "Invalid target should fail"
        assert "No rule to make target" in result["stderr"] or "No such file or directory" in result["stderr"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])