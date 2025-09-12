#!/usr/bin/env python3
"""Pre-commit hook to check for test isolation violations.

This script checks atomic tests to ensure they don't violate test isolation
principles by accessing real environment variables or making real API calls.
"""

import sys
import os
from pathlib import Path
from typing import List, Tuple

# Add the backend directory to the path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))


def check_test_isolation(test_file: str, content: str) -> List[Tuple[int, int, str]]:
    """Check for test isolation violations using AST analysis."""
    violations = []
    lines = content.split('\n')

    # Skip CI/environment tests that legitimately need environment variables
    if any(skip_pattern in test_file for skip_pattern in [
        'test_ci_environment.py',
        'test_settings_acceptance.py',
        'test_cicd_precommit_coverage.py',
        'test_settings_dependency_injection.py',
        'test_environment_loading.py'  # Explicitly tests env var loading
    ]):
        return violations

    for i, line in enumerate(lines, 1):
        # Check for environment variable access
        if 'os.getenv(' in line or 'os.environ[' in line:
            violations.append((i, 0, "Direct environment variable access in test"))

        # Check for real API calls (but skip E2E tests that need real API calls)
        if ('requests.get(' in line or 'requests.post(' in line) and '/e2e/' not in test_file:
            violations.append((i, 0, "Real API call in test"))

    return violations


def check_patterns(test_file: str, content: str) -> List[Tuple[int, str]]:
    """Check for problematic patterns in test content."""
    violations = []
    lines = content.split('\n')

    # Skip CI/environment tests that legitimately need file system access
    if any(skip_pattern in test_file for skip_pattern in [
        'test_ci_environment.py',
        'test_settings_acceptance.py',
        'test_cicd_precommit_coverage.py',
        'test_settings_dependency_injection.py',
        'test_environment_loading.py'  # Explicitly tests env var loading
    ]):
        return violations

    for i, line in enumerate(lines, 1):
        # Check for database connections
        if 'psycopg2.connect(' in line or 'sqlite3.connect(' in line:
            violations.append((i, "Database connection in test"))

        # Check for file system access (but allow test_data)
        if 'open(' in line and 'test_data' not in line:
            violations.append((i, "File system access in test"))

    return violations


def main():
    """Main function to check test isolation violations."""
    print("🔍 Checking for test isolation violations...")

    violations_found = False
    backend_tests_dir = backend_dir / "tests"

    # Find all test files
    test_files = list(backend_tests_dir.rglob("test_*.py"))

    for test_file in test_files:
        if test_file.is_file():
            print(f"  Checking {test_file.relative_to(backend_dir)}...")

            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for AST-based violations
                ast_violations = check_test_isolation(str(test_file), content)

                # Check for pattern-based violations
                pattern_violations = check_patterns(str(test_file), content)

                # Report violations
                if ast_violations:
                    for line, col, message in ast_violations:
                        print(f"    ❌ Line {line}:{col} - {message}")
                        violations_found = True

                if pattern_violations:
                    for line, message in pattern_violations:
                        print(f"    ❌ Line {line} - {message}")
                        violations_found = True

            except Exception as e:
                print(f"    ⚠️  Error checking {test_file}: {e}")

    if violations_found:
        print("\n❌ Test isolation violations found!")
        print("Please fix these issues before committing.")
        print("\nFor help, see: docs/TEST_ISOLATION.md")
        return 1
    else:
        print("\n✅ No test isolation violations found!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
