#!/usr/bin/env python3
"""
Script to fix syntax errors in integration test files.
"""

import re
from pathlib import Path


def fix_syntax_errors(content: str) -> str:
    """Fix common syntax errors in test files."""

    # Fix broken import statements
    content = re.sub(
        r"from tests\.fixtures\.unit import mock_user_service, mock_collection_service\nfrom rag_solution\.data_ingestion\.chunking import \(",
        "from rag_solution.data_ingestion.chunking import (",
        content,
    )

    # Fix duplicate imports
    content = re.sub(r"from tests\.fixtures\.unit import mock_user_service, mock_collection_service\n", "", content)

    # Fix missing integration_settings import
    if "integration_settings" in content and "from tests.fixtures.integration import integration_settings" not in content:
        lines = content.split("\n")
        import_end = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(("import ", "from ")) and not line.strip().startswith("#"):
                import_end = i + 1

        lines.insert(import_end, "from tests.fixtures.integration import integration_settings")
        content = "\n".join(lines)

    return content


def fix_integration_test_syntax(file_path: str) -> bool:
    """Fix syntax errors in a single integration test file."""

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        original_content = content
        content = fix_syntax_errors(content)

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function to fix syntax errors in all integration tests."""

    integration_dir = Path("tests/integration")
    if not integration_dir.exists():
        print("Integration tests directory not found")
        return

    fixed_files = []

    # Process all integration test files
    for test_file in integration_dir.glob("test_*.py"):
        if fix_integration_test_syntax(str(test_file)):
            fixed_files.append(str(test_file))

    print(f"Fixed syntax errors in {len(fixed_files)} files:")
    for file_path in fixed_files:
        print(f"  {file_path}")


if __name__ == "__main__":
    main()
