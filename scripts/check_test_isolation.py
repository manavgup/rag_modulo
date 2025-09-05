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

from tests.linting.test_isolation_checker import check_test_isolation, check_patterns


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
                pattern_violations = check_patterns(content)

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
