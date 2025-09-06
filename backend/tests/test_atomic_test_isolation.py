"""Tests for atomic test isolation issues discovered in CI.

These tests reproduce the database connection failures that cause atomic tests
to fail when they shouldn't need database infrastructure.
"""

import subprocess
import sys
from pathlib import Path


class TestAtomicTestIsolation:
    """Test that atomic tests are properly isolated from infrastructure dependencies."""

    def test_atomic_tests_should_not_need_database(self):
        """Test that tests marked as atomic don't try to connect to database.

        Expected: Atomic tests should run without database infrastructure
        Current: Many atomic tests fail with PostgreSQL connection errors
        """
        # This simulates what happens in CI test-isolation job
        env_without_db = {
            "PATH": "/usr/bin:/bin",  # Minimal PATH
            "PYTHONPATH": ".",
            # No database environment variables
        }

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import sys
sys.path.insert(0, '.')
# Test that we can import core modules without triggering database connections
try:
    # This should work without database
    from core.config import get_settings
    print('SUCCESS: Core config imported without database')
    exit(0)
except Exception as e:
    if 'connection' in str(e).lower() or 'database' in str(e).lower():
        print(f'FAILED: Unexpected database connection attempt: {e}')
        exit(1)
    else:
        print(f'FAILED: Other error: {e}')
        exit(1)
            """,
            ],
            env=env_without_db,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        # This should succeed (our Settings fix should handle this)
        assert result.returncode == 0, f"Core imports should work without database: {result.stderr}"

    def test_main_app_import_triggers_database_connection(self):
        """Test that importing main app triggers database connection (current issue).

        Expected: Should be able to import app modules without database in atomic context
        Current: Importing main.py triggers database connection via SQLAlchemy
        """
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import sys
sys.path.insert(0, '.')
try:
    from main import app
    print('SUCCESS: Main app imported')
    exit(0)
except Exception as e:
    if 'connection' in str(e).lower() and 'refused' in str(e).lower():
        print('EXPECTED_FAILURE: Database connection required for main app')
        exit(42)  # Special exit code to indicate expected failure
    else:
        print(f'FAILED: Unexpected error: {e}')
        exit(1)
            """,
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        # This should fail with database connection error (demonstrating the issue)
        assert result.returncode == 42, f"Should fail with expected database error: {result.stderr}"
        assert "EXPECTED_FAILURE" in result.stdout

    def test_api_tests_should_not_be_marked_atomic(self):
        """Test that API tests requiring database are not marked as atomic.

        Expected: Tests that need database should not have @pytest.mark.atomic
        Current: Many API tests are incorrectly marked as atomic
        """
        # Check for API tests marked as atomic
        api_test_files = list(Path("tests/api").glob("test_*.py"))

        atomic_api_tests = []
        for test_file in api_test_files:
            content = test_file.read_text()
            if "@pytest.mark.atomic" in content and "from main import app" in content:
                atomic_api_tests.append(test_file.name)

        # This should fail initially (showing the problem)
        assert len(atomic_api_tests) == 0, f"These API tests are incorrectly marked as atomic: {atomic_api_tests}"

    def test_model_tests_should_not_be_marked_atomic_if_they_need_db(self):
        """Test that model tests requiring database are not marked as atomic.

        Expected: Tests that instantiate models needing DB should not be atomic
        Current: Some model tests are marked atomic but need database
        """
        # Look for model tests that are atomic but import models that need DB
        model_test_files = list(Path("tests").glob("**/test_*model*.py")) + list(Path("tests").glob("**/test_*repository*.py"))

        problematic_tests = []
        for test_file in model_test_files:
            if test_file.exists():
                content = test_file.read_text()
                if (
                    "@pytest.mark.atomic" in content
                    and ("from rag_solution.models" in content or "import" in content)
                    and any(model in content for model in ["Collection", "User", "File", "Base.metadata.create_all"])
                ):
                    problematic_tests.append(test_file.name)

        # This should initially show problems
        assert len(problematic_tests) == 0, f"These model tests are atomic but may need DB: {problematic_tests}"
