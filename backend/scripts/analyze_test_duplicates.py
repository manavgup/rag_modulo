#!/usr/bin/env python3
"""
Analyze Test Duplicates and Consolidation Strategy
"""

import re
from pathlib import Path
from typing import Any


def analyze_test_directory(directory: Path) -> dict[str, list[Path]]:
    """Analyze a test directory and categorize files."""
    categories: dict[str, list[Path]] = {
        "atomic": [],
        "unit": [],
        "integration": [],
        "e2e": [],
        "fixtures": [],
        "other": [],
    }

    if not directory.exists():
        return categories

    for file_path in directory.rglob("test_*.py"):
        if file_path.is_file():
            # Determine category based on directory name
            if "atomic" in str(file_path):
                categories["atomic"].append(file_path)
            elif "unit" in str(file_path):
                categories["unit"].append(file_path)
            elif "integration" in str(file_path):
                categories["integration"].append(file_path)
            elif "e2e" in str(file_path):
                categories["e2e"].append(file_path)
            elif "fixture" in str(file_path):
                categories["fixtures"].append(file_path)
            else:
                categories["other"].append(file_path)

    return categories


def find_duplicate_tests() -> dict[str, list[Path]]:
    """Find duplicate test files across directories."""
    duplicates = {}

    # Directories to check for duplicates
    test_dirs = [
        "tests/integration",
        "tests/integration_backup",
        "tests/integration_backup_analysis",
        "tests/service_backup",
        "tests/services",
        "tests/e2e",
        "tests/e2e_backup",
    ]

    all_files: dict[str, list[Path]] = {}

    for test_dir in test_dirs:
        if Path(test_dir).exists():
            for file_path in Path(test_dir).rglob("test_*.py"):
                if file_path.is_file():
                    filename = file_path.name
                    if filename not in all_files:
                        all_files[filename] = []
                    all_files[filename].append(file_path)

    # Find duplicates
    for filename, file_paths in all_files.items():
        if len(file_paths) > 1:
            duplicates[filename] = file_paths

    return duplicates


def analyze_file_content(file_path: Path) -> dict[str, Any]:
    """Analyze the content of a test file."""
    try:
        content = file_path.read_text(encoding="utf-8")

        # Count test functions
        test_functions = len(re.findall(r"def test_\w+", content))

        # Count classes
        test_classes = len(re.findall(r"class Test\w+", content))

        # Check for imports
        has_pytest = "import pytest" in content or "from pytest" in content
        has_unittest = "import unittest" in content or "from unittest" in content
        has_fastapi = "from fastapi" in content or "import fastapi" in content

        # Check for markers
        has_atomic = "@pytest.mark.atomic" in content
        has_unit = "@pytest.mark.unit" in content
        has_integration = "@pytest.mark.integration" in content
        has_e2e = "@pytest.mark.e2e" in content

        # Check for external dependencies
        has_database = "database" in content.lower() or "db" in content.lower()
        has_http = "requests" in content or "httpx" in content or "TestClient" in content
        has_mock = "Mock" in content or "mock" in content or "patch" in content

        return {
            "test_functions": test_functions,
            "test_classes": test_classes,
            "has_pytest": has_pytest,
            "has_unittest": has_unittest,
            "has_fastapi": has_fastapi,
            "has_atomic": has_atomic,
            "has_unit": has_unit,
            "has_integration": has_integration,
            "has_e2e": has_e2e,
            "has_database": has_database,
            "has_http": has_http,
            "has_mock": has_mock,
            "size": len(content),
            "lines": len(content.split("\n")),
        }
    except Exception as e:
        return {"error": str(e)}


def main():
    """Main analysis function."""
    print("🔍 Analyzing Test Duplicates and Consolidation Strategy")
    print("=" * 60)

    # Find duplicates
    duplicates = find_duplicate_tests()

    print(f"\n📊 Found {len(duplicates)} duplicate test files:")
    for filename, file_paths in duplicates.items():
        print(f"\n📁 {filename}:")
        for file_path in file_paths:
            print(f"  - {file_path}")

    # Analyze each duplicate
    print("\n🔬 Analyzing duplicate files:")
    for filename, file_paths in duplicates.items():
        print(f"\n📁 {filename}:")

        for file_path in file_paths:
            analysis = analyze_file_content(file_path)
            print(f"  📄 {file_path}:")
            if "error" in analysis:
                print(f"    ❌ Error: {analysis['error']}")
            else:
                print(f"    📊 {analysis['test_functions']} test functions, {analysis['test_classes']} classes")
                print(f"    📏 {analysis['lines']} lines, {analysis['size']} bytes")
                print(f"    🏷️  Markers: atomic={analysis['has_atomic']}, unit={analysis['has_unit']}, integration={analysis['has_integration']}, e2e={analysis['has_e2e']}")
                print(f"    🔧 Dependencies: pytest={analysis['has_pytest']}, fastapi={analysis['has_fastapi']}, mock={analysis['has_mock']}")
                print(f"    🌐 External: database={analysis['has_database']}, http={analysis['has_http']}")

    # Analyze core tests
    print("\n🔬 Analyzing core tests:")
    core_file = Path("tests/core/test_settings_dependency_injection.py")
    if core_file.exists():
        analysis = analyze_file_content(core_file)
        print(f"📄 {core_file}:")
        if "error" in analysis:
            print(f"    ❌ Error: {analysis['error']}")
        else:
            print(f"    📊 {analysis['test_functions']} test functions, {analysis['test_classes']} classes")
            print(f"    📏 {analysis['lines']} lines, {analysis['size']} bytes")
            print(f"    🏷️  Markers: atomic={analysis['has_atomic']}, unit={analysis['has_unit']}, integration={analysis['has_integration']}, e2e={analysis['has_e2e']}")
            print(f"    🔧 Dependencies: pytest={analysis['has_pytest']}, fastapi={analysis['has_fastapi']}, mock={analysis['has_mock']}")
            print(f"    🌐 External: database={analysis['has_database']}, http={analysis['has_http']}")

    # Recommendations
    print("\n💡 Recommendations:")
    print("1. Move core/test_settings_dependency_injection.py to unit/ (it's a unit test)")
    print("2. Consolidate integration_backup, integration_backup_analysis, service_backup into integration/")
    print("3. Consolidate e2e_backup into e2e/")
    print("4. Delete services/ directory (empty)")
    print("5. Review each duplicate and keep the most comprehensive version")

    # Count total files
    total_files = sum(len(files) for files in duplicates.values())
    print("\n📈 Summary:")
    print(f"  - {len(duplicates)} duplicate filenames")
    print(f"  - {total_files} total duplicate files")
    print(f"  - Potential reduction: {total_files - len(duplicates)} files")


if __name__ == "__main__":
    main()
