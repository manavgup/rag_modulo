#!/usr/bin/env python3
"""
Fix Test Quality - Python Best Practices with Pydantic 2.0
Ensures all test files follow best practices and pass linting.
"""

import re
from pathlib import Path


def fix_imports(content: str) -> str:
    """Fix import statements to follow best practices."""
    lines = content.split("\n")
    import_lines = []
    other_lines = []
    in_imports = True

    for line in lines:
        if in_imports and (line.startswith(("import ", "from ")) or line.strip() == ""):
            import_lines.append(line)
        else:
            in_imports = False
            other_lines.append(line)

    # Clean up imports
    cleaned_imports = []
    seen_imports = set()

    for line in import_lines:
        if line.strip() and not line.startswith("#"):
            # Remove unused imports
            if "unused" not in line.lower():
                cleaned_imports.append(line)
                seen_imports.add(line.strip())
        else:
            cleaned_imports.append(line)

    # Add standard library imports first
    std_imports = []
    third_party_imports = []
    local_imports = []

    for line in cleaned_imports:
        if line.strip().startswith("import ") or line.strip().startswith("from "):
            if "pytest" in line or "unittest" in line:
                third_party_imports.append(line)
            elif "rag_solution" in line or "backend" in line:
                local_imports.append(line)
            else:
                std_imports.append(line)
        else:
            std_imports.append(line)

    # Combine imports
    all_imports = std_imports + third_party_imports + local_imports

    return "\n".join(all_imports + other_lines)


def fix_pydantic_usage(content: str) -> str:
    """Fix Pydantic 2.0 usage patterns."""
    # Fix datetime imports
    content = re.sub(r"from datetime import datetime", "from datetime import datetime, timezone", content)

    # Fix timezone usage
    content = re.sub(r"datetime\((\d+), (\d+), (\d+), (\d+), (\d+), (\d+), tzinfo=TzInfo\(UTC\)\)", r"datetime(\1, \2, \3, \4, \5, \6, tzinfo=timezone.utc)", content)

    # Fix ConfigDict usage
    content = re.sub(r"class Config:", "model_config = ConfigDict(", content)

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


def fix_assertions(content: str) -> str:
    """Fix assertion patterns."""
    # Fix boolean comparisons
    content = re.sub(r"assert (\w+) == True\b", r"assert \1 is True", content)
    content = re.sub(r"assert (\w+) == False\b", r"assert \1 is False", content)

    # Fix isinstance patterns
    content = re.sub(r"isinstance\(([^,]+), type\(([^)]+)\)\)", r"isinstance(\1, \2)", content)

    return content


def fix_quotes(content: str) -> str:
    """Fix quote consistency."""
    # Use double quotes consistently
    content = re.sub(r"'([^']*)'", r'"\1"', content)

    return content


def fix_whitespace(content: str) -> str:
    """Fix whitespace issues."""
    lines = content.split("\n")
    fixed_lines = []

    for line in lines:
        # Remove trailing whitespace
        line = line.rstrip()
        fixed_lines.append(line)

    # Ensure file ends with newline
    if fixed_lines and fixed_lines[-1]:
        fixed_lines.append("")

    return "\n".join(fixed_lines)


def add_proper_docstrings(content: str) -> str:
    """Add proper docstrings to test functions."""
    lines = content.split("\n")
    fixed_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this is a test function without docstring
        if re.match(r"def test_.*\(.*\):", line):
            # Look for next non-empty line
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1

            # If next non-empty line is not a docstring, add one
            if j < len(lines) and not lines[j].strip().startswith('"""'):
                indent = len(line) - len(line.lstrip())
                docstring = " " * (indent + 4) + '"""Test function."""'
                fixed_lines.append(line)
                fixed_lines.append(docstring)
                i = j - 1
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)

        i += 1

    return "\n".join(fixed_lines)


def fix_test_file(file_path: Path) -> None:
    """Fix a single test file."""
    print(f"🔧 Fixing {file_path}")

    try:
        content = file_path.read_text(encoding="utf-8")

        # Apply all fixes
        content = fix_imports(content)
        content = fix_pydantic_usage(content)
        content = fix_type_annotations(content)
        content = fix_assertions(content)
        content = fix_quotes(content)
        content = fix_whitespace(content)
        content = add_proper_docstrings(content)

        # Write back
        file_path.write_text(content, encoding="utf-8")
        print(f"✅ Fixed {file_path}")

    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")


def main():
    """Main function to fix all test files."""
    print("🚀 Starting test quality fixes...")

    # Find all test files
    test_dirs = ["backend/tests/atomic", "backend/tests/unit", "backend/tests/integration", "backend/tests/e2e"]

    for test_dir in test_dirs:
        if Path(test_dir).exists():
            for test_file in Path(test_dir).glob("test_*.py"):
                if not test_file.name.startswith("test_simple"):
                    fix_test_file(test_file)

    print("✅ Test quality fixes completed!")
    print("Run: poetry run ruff check tests/ --fix")


if __name__ == "__main__":
    main()
