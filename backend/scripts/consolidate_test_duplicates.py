#!/usr/bin/env python3
"""
Consolidate Test Duplicates and Fix Pre-commit Issues
"""

import shutil
from pathlib import Path


def move_core_tests():
    """Move core tests to appropriate layers."""
    print("🔄 Moving core tests to appropriate layers...")

    # Move core/test_settings_dependency_injection.py to unit/
    core_file = Path("tests/core/test_settings_dependency_injection.py")
    unit_file = Path("tests/unit/test_settings_dependency_injection.py")

    if core_file.exists() and not unit_file.exists():
        shutil.move(str(core_file), str(unit_file))
        print(f"✅ Moved {core_file} to {unit_file}")

        # Add unit marker to the file
        content = unit_file.read_text(encoding="utf-8")
        if "@pytest.mark.unit" not in content:
            content = content.replace("import pytest", "import pytest\n\n@pytest.mark.unit")
            unit_file.write_text(content, encoding="utf-8")
            print(f"✅ Added @pytest.mark.unit marker to {unit_file}")

    # Remove empty core directory
    if core_file.parent.exists() and not any(core_file.parent.iterdir()):
        core_file.parent.rmdir()
        print(f"✅ Removed empty {core_file.parent} directory")


def consolidate_integration_tests():
    """Consolidate integration test duplicates."""
    print("🔄 Consolidating integration test duplicates...")

    # Priority order: integration/ > integration_backup/ > integration_backup_analysis/ > service_backup/
    priority_dirs = ["tests/integration", "tests/integration_backup", "tests/integration_backup_analysis", "tests/service_backup"]

    # Find all test files
    all_tests = {}
    for test_dir in priority_dirs:
        if Path(test_dir).exists():
            for file_path in Path(test_dir).rglob("test_*.py"):
                if file_path.is_file():
                    filename = file_path.name
                    if filename not in all_tests:
                        all_tests[filename] = []
                    all_tests[filename].append(file_path)

    # Process duplicates
    for filename, file_paths in all_tests.items():
        if len(file_paths) > 1:
            print(f"\n📁 Processing {filename} ({len(file_paths)} duplicates)")

            # Find the best version (largest file with most tests)
            best_file = None
            best_score = 0

            for file_path in file_paths:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    test_count = content.count("def test_")
                    size = len(content)
                    score = test_count * 100 + size  # Weight test count more

                    if score > best_score:
                        best_score = score
                        best_file = file_path
                except Exception as e:
                    print(f"  ⚠️  Error reading {file_path}: {e}")

            if best_file:
                print(f"  🏆 Best version: {best_file} (score: {best_score})")

                # Move to integration/ if not already there
                target_file = Path("tests/integration") / filename
                if best_file != target_file:
                    if target_file.exists():
                        target_file.unlink()
                    shutil.move(str(best_file), str(target_file))
                    print(f"  ✅ Moved to {target_file}")

                # Delete other duplicates
                for file_path in file_paths:
                    if file_path != target_file and file_path.exists():
                        file_path.unlink()
                        print(f"  🗑️  Deleted {file_path}")


def consolidate_e2e_tests():
    """Consolidate E2E test duplicates."""
    print("🔄 Consolidating E2E test duplicates...")

    # Priority order: e2e/ > e2e_backup/
    priority_dirs = ["tests/e2e", "tests/e2e_backup"]

    # Find all E2E test files
    all_tests = {}
    for test_dir in priority_dirs:
        if Path(test_dir).exists():
            for file_path in Path(test_dir).rglob("test_*.py"):
                if file_path.is_file():
                    filename = file_path.name
                    if filename not in all_tests:
                        all_tests[filename] = []
                    all_tests[filename].append(file_path)

    # Process duplicates
    for filename, file_paths in all_tests.items():
        if len(file_paths) > 1:
            print(f"\n📁 Processing {filename} ({len(file_paths)} duplicates)")

            # Find the best version
            best_file = None
            best_score = 0

            for file_path in file_paths:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    test_count = content.count("def test_")
                    size = len(content)
                    score = test_count * 100 + size

                    if score > best_score:
                        best_score = score
                        best_file = file_path
                except Exception as e:
                    print(f"  ⚠️  Error reading {file_path}: {e}")

            if best_file:
                print(f"  🏆 Best version: {best_file} (score: {best_score})")

                # Move to e2e/ if not already there
                target_file = Path("tests/e2e") / filename
                if best_file != target_file:
                    if target_file.exists():
                        target_file.unlink()
                    shutil.move(str(best_file), str(target_file))
                    print(f"  ✅ Moved to {target_file}")

                # Delete other duplicates
                for file_path in file_paths:
                    if file_path != target_file and file_path.exists():
                        file_path.unlink()
                        print(f"  🗑️  Deleted {file_path}")


def clean_empty_directories():
    """Remove empty directories."""
    print("🔄 Cleaning empty directories...")

    directories_to_remove = ["tests/services", "tests/integration_backup", "tests/integration_backup_analysis", "tests/service_backup", "tests/e2e_backup"]

    for dir_path in directories_to_remove:
        if Path(dir_path).exists():
            try:
                shutil.rmtree(dir_path)
                print(f"✅ Removed {dir_path}")
            except Exception as e:
                print(f"⚠️  Error removing {dir_path}: {e}")


def fix_schema_issues():
    """Fix schema validation issues in test files."""
    print("🔄 Fixing schema validation issues...")

    # Fix UserInput schema issues
    user_validation_file = Path("tests/atomic/test_user_validation.py")
    if user_validation_file.exists():
        content = user_validation_file.read_text(encoding="utf-8")

        # Fix the test that uses wrong schema
        if "class TestUserInput" in content:
            # Replace the custom TestUserInput with proper UserInput usage
            content = content.replace('class TestUserInput(BaseModel):\n    name: str\n    description: str = ""', "# Using actual UserInput schema from rag_solution.schemas.user_schema")
            content = content.replace("from pydantic import BaseModel", "from pydantic import ValidationError\nfrom rag_solution.schemas.user_schema import UserInput")

            user_validation_file.write_text(content, encoding="utf-8")
            print(f"✅ Fixed UserInput schema in {user_validation_file}")

    # Fix SearchInput schema issues
    search_validation_file = Path("tests/atomic/test_search_validation.py")
    if search_validation_file.exists():
        content = search_validation_file.read_text(encoding="utf-8")

        # Fix the test that uses wrong schema
        if "class TestSearchInput" in content:
            content = content.replace('class TestSearchInput(BaseModel):\n    name: str\n    description: str = ""', "# Using actual SearchInput schema from rag_solution.schemas.search_schema")
            content = content.replace("from pydantic import BaseModel", "from pydantic import ValidationError\nfrom rag_solution.schemas.search_schema import SearchInput")

            search_validation_file.write_text(content, encoding="utf-8")
            print(f"✅ Fixed SearchInput schema in {search_validation_file}")

    # Fix CollectionInput schema issues
    collection_validation_file = Path("tests/atomic/test_collection_validation.py")
    if collection_validation_file.exists():
        content = collection_validation_file.read_text(encoding="utf-8")

        # Fix the test that uses wrong schema
        if "class TestCollectionInput" in content:
            content = content.replace(
                'class TestCollectionInput(BaseModel):\n    name: str\n    description: str = ""', "# Using actual CollectionInput schema from rag_solution.schemas.collection_schema"
            )
            content = content.replace("from pydantic import BaseModel", "from pydantic import ValidationError\nfrom rag_solution.schemas.collection_schema import CollectionInput")

            collection_validation_file.write_text(content, encoding="utf-8")
            print(f"✅ Fixed CollectionInput schema in {collection_validation_file}")


def main():
    """Main consolidation function."""
    print("🚀 Starting Test Consolidation and Pre-commit Fixes")
    print("=" * 60)

    # Step 1: Move core tests
    move_core_tests()

    # Step 2: Fix schema issues
    fix_schema_issues()

    # Step 3: Consolidate integration tests
    consolidate_integration_tests()

    # Step 4: Consolidate E2E tests
    consolidate_e2e_tests()

    # Step 5: Clean empty directories
    clean_empty_directories()

    print("\n✅ Test consolidation completed!")
    print("\n📊 Summary:")
    print("- Moved core tests to unit/ layer")
    print("- Fixed schema validation issues")
    print("- Consolidated duplicate test files")
    print("- Removed empty directories")
    print("\n🎯 Next steps:")
    print("1. Run 'make pre-commit-run' to check remaining issues")
    print("2. Fix any remaining linting/type issues")
    print("3. Run tests to ensure everything works")


if __name__ == "__main__":
    main()
