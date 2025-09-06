"""Acceptance tests for Settings configuration fix.

When these tests pass, we know the Settings configuration is fixed.
"""

import os
import subprocess
import sys


def test_acceptance_settings_with_defaults():
    """ACCEPTANCE TEST: Settings should work without any env vars."""
    test_script = """
import os
# Clear all env vars
for key in list(os.environ.keys()):
    if key.startswith(('JWT', 'RAG', 'WATSON', 'WX')):
        del os.environ[key]

from core.config import settings

# Should not crash and should have values
assert settings.jwt_secret_key is not None
assert settings.rag_llm is not None
assert settings.wx_project_id is not None
assert settings.wx_api_key is not None
assert settings.wx_url is not None

print("✓ Settings works without environment variables")
"""

    result = subprocess.run([sys.executable, "-c", test_script], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    assert result.returncode == 0, f"Settings should work without env vars. Error: {result.stderr}"
    assert "✓ Settings works" in result.stdout


def test_acceptance_lazy_initialization():
    """ACCEPTANCE TEST: Settings should support lazy initialization."""
    test_script = """
from core.config import get_settings

# Should have get_settings function
settings1 = get_settings()
settings2 = get_settings()

# Should be the same instance (cached)
assert settings1 is settings2

print("✓ Lazy initialization works")
"""

    result = subprocess.run([sys.executable, "-c", test_script], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    assert result.returncode == 0, f"Lazy initialization should work. Error: {result.stderr}"
    assert "✓ Lazy initialization" in result.stdout


def test_acceptance_backwards_compatible():
    """ACCEPTANCE TEST: Old import patterns should still work."""
    test_script = """
# Old pattern should still work
from core.config import settings
assert settings is not None

# Direct access should work
import core.config
assert core.config.settings is not None

print("✓ Backwards compatible")
"""

    result = subprocess.run([sys.executable, "-c", test_script], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    assert result.returncode == 0, f"Should be backwards compatible. Error: {result.stderr}"
    assert "✓ Backwards compatible" in result.stdout


def test_acceptance_env_vars_override():
    """ACCEPTANCE TEST: Environment variables should override defaults."""
    test_script = """
import os
os.environ["JWT_SECRET_KEY"] = "production-secret"
os.environ["RAG_LLM"] = "anthropic"

from core.config import settings

assert settings.jwt_secret_key == "production-secret"
assert settings.rag_llm == "anthropic"

print("✓ Environment variables override defaults")
"""

    result = subprocess.run([sys.executable, "-c", test_script], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    assert result.returncode == 0, f"Env vars should override. Error: {result.stderr}"
    assert "✓ Environment variables" in result.stdout


def test_acceptance_pytest_atomic_works():
    """ACCEPTANCE TEST: Settings can be imported in atomic test context."""
    env = os.environ.copy()
    # Remove all the potentially required variables (CI test-isolation scenario)
    for var in ["JWT_SECRET_KEY", "RAG_LLM", "WATSONX_INSTANCE_ID", "WATSONX_APIKEY", "WATSONX_URL"]:
        env.pop(var, None)

    # Test that config can be imported without ValidationError (the core CI issue)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
sys.path.insert(0, '.')
try:
    from core.config import settings, get_settings
    # Test that defaults work
    assert settings.jwt_secret_key.startswith('dev-secret-key')
    assert settings.rag_llm == 'openai'
    assert get_settings() is not None
    print('✓ Settings work in atomic test context')
    exit(0)
except Exception as e:
    print(f'✗ Settings failed: {e}')
    exit(1)
        """,
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )

    # Should succeed after fix
    assert result.returncode == 0, f"Settings should work in atomic context. Error: {result.stderr}"


def test_acceptance_docker_context():
    """ACCEPTANCE TEST: Settings should work in Docker-like environment."""
    test_script = """
import os
# Simulate Docker environment
os.environ["CONTAINER_ENV"] = "1"
# Clear other vars
for key in list(os.environ.keys()):
    if key.startswith(('JWT', 'RAG', 'WATSON', 'WX')):
        del os.environ[key]

from core.config import settings

# Should work with defaults
assert settings is not None
assert hasattr(settings, 'jwt_secret_key')

print("✓ Works in Docker context")
"""

    result = subprocess.run([sys.executable, "-c", test_script], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    assert result.returncode == 0, f"Should work in Docker context. Error: {result.stderr}"
    assert "✓ Works in Docker" in result.stdout


if __name__ == "__main__":
    print("=" * 70)
    print("ACCEPTANCE TESTS - These should all FAIL before the fix")
    print("=" * 70)

    tests = [
        ("Settings with defaults", test_acceptance_settings_with_defaults),
        ("Lazy initialization", test_acceptance_lazy_initialization),
        ("Backwards compatibility", test_acceptance_backwards_compatible),
        ("Environment variable override", test_acceptance_env_vars_override),
        ("Pytest atomic marker", test_acceptance_pytest_atomic_works),
        ("Docker context", test_acceptance_docker_context),
    ]

    failed = []
    passed = []

    for name, test_func in tests:
        try:
            print(f"\nTesting: {name}")
            test_func()
            passed.append(name)
            print("  ✓ PASSED (unexpected - fix might already be in place?)")
        except AssertionError as e:
            failed.append(name)
            print(f"  ✗ FAILED (expected before fix): {str(e)[:100]}...")

    print("\n" + "=" * 70)
    print(f"Summary: {len(failed)} failed (expected), {len(passed)} passed (unexpected)")
    print("=" * 70)

    if failed:
        print("\n✓ Good! These tests are failing as expected.")
        print("  Once we implement the fix, all these should pass.")
