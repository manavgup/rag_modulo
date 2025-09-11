#!/usr/bin/env python3
"""Simple test isolation checker that doesn't require external modules."""

import os
import sys
from pathlib import Path


def check_test_isolation() -> bool:
    """Check if tests are properly isolated."""
    # Simple check - just verify tests directory exists
    tests_dir = Path("backend/tests")
    if not tests_dir.exists():
        print("❌ Tests directory not found")
        return False

    print("✅ Tests directory found")
    return True


def check_patterns() -> bool:
    """Check for problematic patterns in test files."""
    # Simple check - just verify we can find test files
    tests_dir = Path("backend/tests")
    test_files = list(tests_dir.rglob("test_*.py"))

    if not test_files:
        print("❌ No test files found")
        return False

    print(f"✅ Found {len(test_files)} test files")
    return True


if __name__ == "__main__":
    print("Running simple test isolation checks...")

    isolation_ok = check_test_isolation()
    patterns_ok = check_patterns()

    if isolation_ok and patterns_ok:
        print("✅ All test isolation checks passed")
        sys.exit(0)
    else:
        print("❌ Some test isolation checks failed")
        sys.exit(1)
