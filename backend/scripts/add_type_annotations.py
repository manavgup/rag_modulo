#!/usr/bin/env python3
"""
Add Type Annotations to Test Files
Ensures all test functions have proper type annotations for mypy compliance.
"""

import re
from pathlib import Path


def add_function_type_annotations(content: str) -> str:
    """Add type annotations to test functions."""
    lines = content.split("\n")
    fixed_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this is a test function without type annotation
        if re.match(r"def test_.*\(.*\):", line) and "->" not in line:
            # Add -> None annotation
            line = re.sub(r"(def test_.*\(self[^)]*\)):", r"\1 -> None:", line) if "self" in line else re.sub(r"(def test_.*\([^)]*\)):", r"\1 -> None:", line)

        # Check for other functions without type annotations
        elif re.match(r"def [^_].*\(.*\):", line) and "->" not in line and "def test_" not in line:
            # Add -> None annotation for non-test functions
            line = re.sub(r"(def [^_].*\(self[^)]*\)):", r"\1 -> None:", line) if "self" in line else re.sub(r"(def [^_].*\([^)]*\)):", r"\1 -> None:", line)

        fixed_lines.append(line)
        i += 1

    return "\n".join(fixed_lines)


def fix_uuid_imports(content: str) -> str:
    """Fix UUID imports and usage."""
    # Add UUID import if not present
    if "from uuid import uuid4" in content and "from uuid import UUID" not in content:
        content = content.replace("from uuid import uuid4", "from uuid import uuid4, UUID")

    # Fix isinstance checks with UUID
    content = re.sub(r"isinstance\(([^,]+), uuid4\)", r"isinstance(\1, UUID)", content)

    return content


def fix_datetime_imports(content: str) -> str:
    """Fix datetime imports and usage."""
    # Add datetime import if not present
    if "from datetime import datetime" in content and "from datetime import timezone" not in content:
        content = content.replace("from datetime import datetime", "from datetime import datetime, timezone")

    return content


def fix_pydantic_usage(content: str) -> str:
    """Fix Pydantic 2.0 usage patterns."""
    # Fix datetime usage in Pydantic models
    content = re.sub(
        r"datetime\((\d+), (\d+), (\d+), (\d+), (\d+), (\d+)\)",
        r"datetime(\1, \2, \3, \4, \5, \6, tzinfo=timezone.utc)",
        content,
    )

    return content


def fix_type_annotations(content: str) -> str:
    """Fix type annotations to use modern Python syntax."""
    # Fix Union types
    content = re.sub(r"Union\[([^,]+), None\]", r"\1 | None", content)
    content = re.sub(r"Optional\[([^\]]+)\]", r"\1 | None", content)

    # Fix List/Dict types
    content = re.sub(r"List\[", "list[", content)
    content = re.sub(r"Dict\[", "dict[", content)
    content = re.sub(r"Tuple\[", "tuple[", content)
    content = re.sub(r"Set\[", "set[", content)

    return content


def fix_test_file(file_path: Path) -> None:
    """Fix a single test file."""
    print(f"🔧 Adding type annotations to {file_path}")

    try:
        content = file_path.read_text(encoding="utf-8")

        # Apply all fixes
        content = add_function_type_annotations(content)
        content = fix_uuid_imports(content)
        content = fix_datetime_imports(content)
        content = fix_pydantic_usage(content)
        content = fix_type_annotations(content)

        # Write back
        file_path.write_text(content, encoding="utf-8")
        print(f"✅ Fixed {file_path}")

    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")


def main():
    """Main function to fix all test files."""
    print("🚀 Adding type annotations to test files...")

    # Find all test files
    test_dirs = ["tests/atomic", "tests/unit", "tests/integration", "tests/e2e"]

    for test_dir in test_dirs:
        if Path(test_dir).exists():
            for test_file in Path(test_dir).glob("test_*.py"):
                fix_test_file(test_file)

    print("✅ Type annotations added!")


if __name__ == "__main__":
    main()
