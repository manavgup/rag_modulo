"""Test to simulate the exact CI test-isolation failure.

This test simulates what happens in the CI pipeline's test-isolation job.
"""

import subprocess
import sys
import os


def test_module_import_without_env_vars():
    """Test that importing core.config works without environment variables (AFTER FIX).

    This simulates the CI test-isolation scenario:
    - No environment variables set
    - Trying to import a module that uses Settings
    - Should now SUCCESS with defaults after fix
    """
    # Create a subprocess with no environment variables
    env = os.environ.copy()
    # Remove all the required variables (CI test-isolation scenario)
    for var in ["JWT_SECRET_KEY", "RAG_LLM", "WATSONX_INSTANCE_ID", "WATSONX_APIKEY", "WATSONX_URL"]:
        env.pop(var, None)

    # Try to import the config module
    result = subprocess.run(
        [sys.executable, "-c", "from core.config import settings; print('✓ Import success with defaults:', settings.rag_llm)"],
        env=env,
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # backend dir
    )

    # After fix this SHOULD succeed
    assert result.returncode == 0, f"Import should succeed with defaults after fix. Error: {result.stderr}"
    assert "✓ Import success" in result.stdout, "Should show success message"

    print("✓ Fixed: Module import works without env vars (fixed behavior)")
    print(f"Success message: {result.stdout.strip()}")


def test_pytest_atomic_marker_without_env_vars():
    """Test that config import works in atomic test context (AFTER FIX).

    This tests the core functionality that was failing in CI test-isolation job.
    """
    env = os.environ.copy()
    # Remove all the required variables (CI test-isolation scenario)
    for var in ["JWT_SECRET_KEY", "RAG_LLM", "WATSONX_INSTANCE_ID", "WATSONX_APIKEY", "WATSONX_URL"]:
        env.pop(var, None)

    # Test the core functionality that was breaking (config import, not full pytest)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
sys.path.insert(0, '.')
# This is what was failing in CI - importing config in an atomic test context
try:
    from core.config import settings, get_settings
    # Validate defaults work
    assert settings.jwt_secret_key.startswith('dev-secret-key')
    assert settings.rag_llm == 'openai'
    print('✓ Config import works in atomic context')
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

    # After fix this should succeed
    assert result.returncode == 0, f"Config should work in atomic context after fix. Error: {result.stderr}"
    assert "✓ Config import works" in result.stdout

    print("✓ Fixed: Config import works in atomic test context (fixed behavior)")


if __name__ == "__main__":
    # Run tests directly
    print("Testing current broken behavior (these should show failures):")
    print("-" * 60)

    try:
        test_module_import_without_env_vars()
    except AssertionError as e:
        print(f"✗ Test failed unexpectedly: {e}")

    try:
        test_pytest_atomic_marker_without_env_vars()
    except AssertionError as e:
        print(f"✗ Test failed unexpectedly: {e}")
