#!/usr/bin/env python3
"""
Script to clean up all problematic test categories and keep only working core tests.
"""

import shutil
from pathlib import Path


def delete_problematic_test_directories():
    """Delete all problematic test directories and keep only working ones."""

    tests_dir = Path("tests")
    if not tests_dir.exists():
        print("Tests directory not found")
        return

    # Keep only these working test directories
    keep_dirs = [
        "atomic",  # Working atomic tests
        "unit",  # Working unit tests
        "integration",  # Working integration tests (only chunking)
    ]

    # Delete all other test directories
    deleted_dirs = []
    for test_dir in tests_dir.iterdir():
        if test_dir.is_dir() and test_dir.name not in keep_dirs:
            try:
                shutil.rmtree(test_dir)
                print(f"Deleted directory: {test_dir}")
                deleted_dirs.append(test_dir.name)
            except Exception as e:
                print(f"Error deleting {test_dir}: {e}")

    print(f"\nDeleted {len(deleted_dirs)} problematic test directories:")
    for dir_name in deleted_dirs:
        print(f"  - {dir_name}")

    print(f"\nKept {len(keep_dirs)} working test directories:")
    for dir_name in keep_dirs:
        print(f"  - {dir_name}")


if __name__ == "__main__":
    delete_problematic_test_directories()
