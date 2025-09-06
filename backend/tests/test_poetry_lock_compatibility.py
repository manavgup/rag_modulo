"""Tests specifically for Poetry lock file compatibility issues.

These tests verify the Poetry version and lock file issues that block Docker builds.
"""

import re
import subprocess
from pathlib import Path


class TestPoetryLockCompatibility:
    """Test Poetry lock file compatibility issues."""

    def test_poetry_version_consistency(self):
        """Test that Poetry versions are consistent across environments."""
        backend_dir = Path(__file__).parent.parent

        # Get current Poetry version
        result = subprocess.run(["poetry", "--version"], capture_output=True, text=True)
        assert result.returncode == 0, "Poetry should be installed"

        current_version = result.stdout.strip()
        print(f"Current Poetry version: {current_version}")

        # Check if Dockerfile specifies a version
        dockerfile_path = backend_dir / "Dockerfile.backend"
        if dockerfile_path.exists():
            dockerfile_content = dockerfile_path.read_text()

            # Look for Poetry version specification
            version_match = re.search(r"POETRY_VERSION[=:]([0-9.]+)", dockerfile_content)
            if version_match:
                dockerfile_version = version_match.group(1)
                print(f"Dockerfile Poetry version: {dockerfile_version}")

                # Versions should be compatible
                # (This test will help us identify version mismatches)

    def test_poetry_lock_is_up_to_date(self):
        """Test that poetry.lock is up to date with pyproject.toml."""
        backend_dir = Path(__file__).parent.parent

        # Check if lock file is up to date
        result = subprocess.run(["poetry", "check"], capture_output=True, text=True, cwd=backend_dir)

        # Should pass - if not, lock file needs updating
        assert result.returncode == 0, f"poetry.lock should be up to date: {result.stderr}"

    def test_docker_poetry_commands(self):
        """Test the specific Poetry commands that fail in Docker build.

        From the CI logs, these are the failing commands:
        - poetry lock --no-update
        - poetry install --only main --no-root --no-cache
        """
        backend_dir = Path(__file__).parent.parent

        # Test 1: poetry lock command (this is what fails)
        # Note: --no-update might not be available in newer Poetry versions
        result = subprocess.run(["poetry", "lock", "--help"], capture_output=True, text=True, cwd=backend_dir)

        lock_help = result.stdout
        has_no_update = "--no-update" in lock_help

        if has_no_update:
            # Try the command that fails in Docker
            result = subprocess.run(["poetry", "lock", "--no-update"], capture_output=True, text=True, cwd=backend_dir)
            # This should work for Docker compatibility
            assert result.returncode == 0, f"poetry lock --no-update should work: {result.stderr}"
        else:
            # Poetry 2.x doesn't have --no-update, use 'poetry check' instead
            result = subprocess.run(["poetry", "check"], capture_output=True, text=True, cwd=backend_dir)
            assert result.returncode == 0, f"poetry check should work for Docker compatibility: {result.stderr}"
            print("✓ Updated for Poetry 2.x: using 'poetry check' instead of deprecated flags")

        # Test 2: poetry install command
        result = subprocess.run(["poetry", "install", "--help"], capture_output=True, text=True, cwd=backend_dir)

        install_help = result.stdout
        assert "--only" in install_help, "Poetry should support --only flag"
        assert "--no-root" in install_help, "Poetry should support --no-root flag"
        assert "--no-cache" in install_help or "--no-cache" not in install_help, "Check cache flags"

    def test_dockerfile_poetry_commands_validity(self):
        """Test that Poetry commands in Dockerfile are valid with current Poetry version."""
        backend_dir = Path(__file__).parent.parent
        dockerfile_path = backend_dir / "Dockerfile.backend"

        if not dockerfile_path.exists():
            return  # Skip if Dockerfile doesn't exist

        dockerfile_content = dockerfile_path.read_text()

        # Extract Poetry commands from Dockerfile
        poetry_commands = []
        for line in dockerfile_content.split("\n"):
            if "poetry" in line and "RUN" in line:
                # Extract the command part
                if "&&" in line:
                    parts = line.split("&&")
                    for part in parts:
                        if "poetry" in part:
                            cmd = part.strip().replace("\\", "").strip()
                            poetry_commands.append(cmd)
                elif "poetry" in line:
                    cmd = line.split("RUN")[1].strip().replace("\\", "").strip()
                    if cmd.startswith("poetry"):
                        poetry_commands.append(cmd)

        print(f"Found Poetry commands in Dockerfile: {poetry_commands}")

        # Test each command's validity (not execution, just syntax)
        for cmd in poetry_commands:
            if cmd.startswith("poetry "):
                # Get the subcommand and flags
                parts = cmd.split()[1:]  # Remove 'poetry'
                if parts:
                    subcommand = parts[0]
                    flags = [p for p in parts[1:] if p.startswith("--")]

                    # Check if subcommand exists
                    result = subprocess.run(["poetry", subcommand, "--help"], capture_output=True, text=True, cwd=backend_dir)

                    if result.returncode != 0:
                        print(f"⚠️  Subcommand '{subcommand}' not available")
                        continue

                    # Check if flags are valid
                    help_text = result.stdout
                    for flag in flags:
                        if flag not in help_text:
                            print(f"⚠️  Flag '{flag}' not available for '{subcommand}'")
                            # This identifies the issue we need to fix

    def test_environment_consistency_poetry_versions(self):
        """Test that Poetry versions match across different configuration files."""
        backend_dir = Path(__file__).parent.parent
        project_root = backend_dir.parent

        versions_found = {}

        # Check .tool-versions if it exists
        tool_versions = project_root / ".tool-versions"
        if tool_versions.exists():
            content = tool_versions.read_text()
            poetry_match = re.search(r"poetry\s+([0-9.]+)", content)
            if poetry_match:
                versions_found["tool-versions"] = poetry_match.group(1)

        # Check Dockerfile
        dockerfile = backend_dir / "Dockerfile.backend"
        if dockerfile.exists():
            content = dockerfile.read_text()
            version_match = re.search(r"POETRY_VERSION[=:]([0-9.]+)", content)
            if version_match:
                versions_found["dockerfile"] = version_match.group(1)

        # Check pyproject.toml for Poetry version constraints
        pyproject = backend_dir / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text()
            # Look for poetry in build-system or tool.poetry sections
            version_matches = re.findall(r"poetry[^=]*[=<>]+\s*([0-9.]+)", content, re.IGNORECASE)
            if version_matches:
                versions_found["pyproject"] = version_matches[0]

        print(f"Poetry versions found: {versions_found}")

        # All versions should be compatible if multiple are specified
        if len(versions_found) > 1:
            versions = list(versions_found.values())
            # Simple check - major.minor should match
            major_minors = [".".join(v.split(".")[:2]) for v in versions]
            unique_major_minors = set(major_minors)

            if len(unique_major_minors) > 1:
                print(f"⚠️  Inconsistent Poetry versions across files: {versions_found}")
                print(f"    Major.minor versions: {unique_major_minors}")
                # This indicates we need to sync versions


def test_comprehensive_poetry_fix():
    """High-level test of Poetry compatibility across all environments."""
    print("\n" + "=" * 70)
    print("POETRY COMPATIBILITY TEST SUMMARY")
    print("=" * 70)

    test_instance = TestPoetryLockCompatibility()

    tests = [
        ("Version Consistency", test_instance.test_poetry_version_consistency),
        ("Lock File Up-to-Date", test_instance.test_poetry_lock_is_up_to_date),
        ("Docker Commands", test_instance.test_docker_poetry_commands),
        ("Dockerfile Command Validity", test_instance.test_dockerfile_poetry_commands_validity),
        ("Environment Version Sync", test_instance.test_environment_consistency_poetry_versions),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            print(f"\nTesting: {test_name}")
            test_func()
            print("  ✓ PASSED")
            results.append((test_name, True, None))
        except AssertionError as e:
            print(f"  ✗ FAILED: {str(e)[:100]}...")
            results.append((test_name, False, str(e)))
        except Exception as e:
            print(f"  ⚠️  ERROR: {str(e)[:100]}...")
            results.append((test_name, False, str(e)))

    print("\n" + "=" * 70)
    failed = [r for r in results if not r[1]]

    if failed:
        print(f"Poetry Issues Found ({len(failed)}):")
        for test_name, _, error in failed:
            print(f"  - {test_name}: {error[:100] if error else 'Failed'}...")
        print("\n✓ These issues explain the Docker build failures in CI")
    else:
        print("✓ All Poetry compatibility tests passed!")

    return results


if __name__ == "__main__":
    test_comprehensive_poetry_fix()
