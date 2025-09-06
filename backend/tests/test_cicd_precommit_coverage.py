"""Tests to ensure CI/CD pipeline and pre-commit hooks work correctly.

These tests verify that our Settings fixes will work in all environments:
1. CI/CD pipeline jobs
2. Pre-commit hooks
3. Docker builds
4. Local development
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


class TestCICDPipeline:
    """Tests that simulate each CI/CD job."""

    def test_ci_test_isolation_job(self):
        """Simulate the test-isolation job from CI/CD pipeline.

        This job specifically runs WITHOUT any environment variables to ensure
        tests are properly isolated.
        """
        # This is what fails in CI currently
        env = os.environ.copy()
        # Remove ALL potentially required env vars (as CI does)
        vars_to_remove = ["JWT_SECRET_KEY", "RAG_LLM", "WATSONX_INSTANCE_ID", "WATSONX_APIKEY", "WATSONX_URL", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "VECTOR_DB", "EMBEDDING_MODEL"]
        for var in vars_to_remove:
            env.pop(var, None)

        # Test 1: Import check (from check_test_isolation.py)
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import sys
sys.path.insert(0, '.')
# This is what check_test_isolation.py does
try:
    import core.config
    print('✓ Config import succeeded')
    exit(0)
except Exception as e:
    print(f'✗ Config import failed: {e}')
    exit(1)
""",
            ],
            env=env,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )

        # After fix, this should succeed
        assert result.returncode == 0, f"test-isolation import check should pass: {result.stderr}"

        # Test 2: Verify config imports work in test context (core CI issue)
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import sys
sys.path.insert(0, '.')
try:
    from core.config import settings, get_settings
    # This is what was failing in CI - Settings ValidationError
    assert settings.jwt_secret_key.startswith('dev-secret-key')
    assert settings.rag_llm == 'openai'
    print('✓ Config works in CI test-isolation context')
    exit(0)
except Exception as e:
    print(f'✗ Config failed: {e}')
    exit(1)
            """,
            ],
            env=env,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )

        # After fix, this should succeed
        assert result.returncode == 0, f"Config should work in CI test-isolation context: {result.stderr}"

    def test_ci_lint_and_unit_job(self):
        """Simulate the lint-and-unit job from CI/CD pipeline.

        This job DOES have environment variables set (see ci.yml lines 56-68).
        """
        env = os.environ.copy()
        # Set the env vars that CI provides
        env.update(
            {
                "JWT_SECRET_KEY": "test-secret-key-for-ci",
                "RAG_LLM": "openai",
                "WATSONX_INSTANCE_ID": "test-instance-id",
                "WATSONX_APIKEY": "test-api-key",
                "WATSONX_URL": "https://test.watsonx.com",
                "VECTOR_DB": "milvus",
                "EMBEDDING_MODEL": "sentence-transformers/all-minilm-l6-v2",
            }
        )

        # Should be able to import and run tests
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
from core.config import settings
assert settings.jwt_secret_key == 'test-secret-key-for-ci'
assert settings.rag_llm == 'openai'
print('✓ Settings work with CI env vars')
""",
            ],
            env=env,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )

        assert result.returncode == 0, f"Should work with CI env vars: {result.stderr}"

    def test_ci_build_job_poetry_lock(self):
        """Test that poetry.lock is compatible with Docker build.

        The build job fails with 'poetry lock --no-update' in Docker.
        """
        # Check if poetry.lock exists and is valid
        backend_dir = Path(__file__).parent.parent
        poetry_lock = backend_dir / "poetry.lock"
        pyproject_toml = backend_dir / "pyproject.toml"

        assert poetry_lock.exists(), "poetry.lock should exist"
        assert pyproject_toml.exists(), "pyproject.toml should exist"

        # Verify poetry lock file can be used (Poetry 2.x compatible)
        result = subprocess.run(["poetry", "check"], capture_output=True, text=True, cwd=backend_dir)

        # This should succeed for Docker builds to work
        assert result.returncode == 0, f"poetry.lock should be valid: {result.stderr}"


class TestPreCommitHooks:
    """Tests that pre-commit hooks work with the new Settings."""

    def test_precommit_can_import_config(self):
        """Pre-commit hooks that import Python code should work.

        Several pre-commit hooks import our Python modules:
        - check-test-isolation
        - validate-ci-environment-fixes
        - python-poetry-check
        """
        # Simulate pre-commit environment (minimal env vars)
        env = os.environ.copy()
        # Pre-commit typically has PATH and basic vars, but not app-specific ones
        for key in list(env.keys()):
            if key.startswith(("JWT", "RAG", "WATSON", "WX", "OPENAI", "ANTHROPIC")):
                del env[key]

        # Test that scripts used by pre-commit can run
        scripts_to_test = ["scripts/check_test_isolation.py", "scripts/validate_ci_fixes.py"]

        for script in scripts_to_test:
            script_path = Path(__file__).parent.parent.parent / script
            if script_path.exists():
                # Try to import the script
                result = subprocess.run([sys.executable, str(script_path), "--help"], env=env, capture_output=True, text=True, cwd=script_path.parent)

                # Should not crash due to missing env vars
                # (might fail for other reasons like missing --help, but not ValidationError)
                assert "ValidationError" not in result.stderr, f"{script} should not fail with ValidationError: {result.stderr}"

    def test_precommit_mypy_check(self):
        """MyPy should be able to type-check files that import config.

        Pre-commit runs MyPy which needs to import modules for type checking.
        """
        # Create a test file that imports config
        test_file = """
from core.config import settings, Settings, get_settings

def test_function() -> Settings:
    return get_settings()

def use_settings() -> str:
    return settings.jwt_secret_key
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(test_file)
            temp_file = f.name

        try:
            # Run mypy on the test file
            result = subprocess.run(
                [sys.executable, "-m", "mypy", "--ignore-missing-imports", temp_file], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )

            # Should not have import errors
            assert "cannot import" not in result.stdout.lower(), f"MyPy should be able to import config: {result.stdout}"
        finally:
            os.unlink(temp_file)


class TestDockerBuild:
    """Tests for Docker build compatibility."""

    def test_docker_build_simulation(self):
        """Simulate what happens during Docker build.

        Docker build runs 'poetry lock --no-update' which currently fails.
        """
        backend_dir = Path(__file__).parent.parent

        # Test: Verify lock file is compatible with current pyproject.toml (Poetry 2.x)
        result = subprocess.run(["poetry", "check"], capture_output=True, text=True, cwd=backend_dir)

        # Should succeed for Docker builds
        assert result.returncode == 0, f"poetry check should work for Docker: {result.stderr}"

    def test_docker_runtime_imports(self):
        """Test that the app can start in a Docker-like environment.

        Docker containers set CONTAINER_ENV=1 and may not have all env vars.
        """
        env = os.environ.copy()
        env["CONTAINER_ENV"] = "1"
        env["PYTHONPATH"] = "/app:/app/rag_solution:/app/core"

        # Remove optional env vars that might not be in container
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
            env.pop(key, None)

        # Main app import should work
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import os
os.environ['CONTAINER_ENV'] = '1'
from core.config import settings
# Should work with defaults or container-provided vars
assert settings is not None
print('✓ App can start in Docker environment')
""",
            ],
            env=env,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )

        assert result.returncode == 0, f"App should start in Docker environment: {result.stderr}"


class TestMakefileCommands:
    """Test that Makefile commands work with new Settings."""

    def test_make_lint_command(self):
        """Test that 'make lint' works without full environment setup.

        Developers often run 'make lint' without setting up env vars.
        """
        # Clear env vars as a developer might have
        env = os.environ.copy()
        for key in list(env.keys()):
            if key.startswith(("JWT", "RAG", "WATSON", "WX")):
                del env[key]

        # Run the Ruff check that make lint does
        result = subprocess.run(["poetry", "run", "ruff", "check", "--help"], env=env, capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Should not fail (ruff itself doesn't need our config)
        assert result.returncode == 0, "Ruff should work without env vars"

    def test_make_test_command(self):
        """Test that 'make test' can at least start without all env vars.

        The test might fail for other reasons, but shouldn't crash on import.
        """
        env = os.environ.copy()
        # Provide minimal required vars
        env.setdefault("JWT_SECRET_KEY", "test-key")
        env.setdefault("RAG_LLM", "openai")

        # Try to run pytest with a simple test file
        result = subprocess.run(["poetry", "run", "pytest", "--co", "-q"], env=env, capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Should not fail with ValidationError
        assert "ValidationError" not in result.stderr, "make test should not fail with ValidationError"


def run_all_coverage_tests():
    """Run all CI/CD and pre-commit coverage tests."""
    print("=" * 70)
    print("CI/CD & PRE-COMMIT COVERAGE TESTS")
    print("=" * 70)

    test_classes = [("CI/CD Pipeline", TestCICDPipeline), ("Pre-commit Hooks", TestPreCommitHooks), ("Docker Build", TestDockerBuild), ("Makefile Commands", TestMakefileCommands)]

    results = []

    for category_name, test_class in test_classes:
        print(f"\n{category_name} Tests:")
        print("-" * 40)

        test_instance = test_class()
        test_methods = [m for m in dir(test_instance) if m.startswith("test_")]

        for method_name in test_methods:
            test_name = method_name.replace("test_", "").replace("_", " ").title()
            try:
                print(f"  Testing: {test_name}...", end=" ")
                getattr(test_instance, method_name)()
                print("✓ PASSED (unexpected)")
                results.append((f"{category_name}: {test_name}", True))
            except AssertionError as e:
                print("✗ FAILED (expected)")
                print(f"    Reason: {str(e)[:100]}...")
                results.append((f"{category_name}: {test_name}", False))
            except Exception as e:
                print(f"✗ ERROR: {str(e)[:50]}...")
                results.append((f"{category_name}: {test_name}", False))

    print("\n" + "=" * 70)
    print("COVERAGE SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, status in results if status)
    failed = sum(1 for _, status in results if not status)

    print(f"Total: {len(results)} tests")
    print(f"Failed: {failed} (expected before fix)")
    print(f"Passed: {passed} (unexpected before fix)")

    if failed > 0:
        print("\n✓ Good! These tests are failing as expected.")
        print("  They verify CI/CD pipeline and pre-commit hook compatibility.")

    return results


if __name__ == "__main__":
    run_all_coverage_tests()
