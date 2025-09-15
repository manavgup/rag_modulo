#!/usr/bin/env python3
"""
Fix Remaining Lint Issues - Python Best Practices
"""

import re
from pathlib import Path


def fix_boolean_comparisons(content: str) -> str:
    """Fix boolean comparison issues."""
    # Fix == True patterns
    content = re.sub(r"(\w+) == True\b", r"\1 is True", content)
    content = re.sub(r"(\w+) == False\b", r"not \1", content)

    # Fix dictionary access patterns
    content = re.sub(r'(\w+\["[^"]+"\]) == True\b', r"\1 is True", content)
    content = re.sub(r'(\w+\["[^"]+"\]) == False\b', r"not \1", content)

    return content


def fix_isinstance_patterns(content: str) -> str:
    """Fix isinstance patterns to use modern syntax."""
    # Fix (X, Y) patterns
    content = re.sub(r"isinstance\(([^,]+), \(([^,]+), ([^)]+)\)\)", r"isinstance(\1, \2 | \3)", content)

    return content


def fix_ternary_operators(content: str) -> str:
    """Fix ternary operator patterns."""
    # Fix if-else blocks that can be ternary
    content = re.sub(
        r'if hasattr\(([^,]+), "item"\):\s*\n\s*([^=]+) = ([^;]+)\s*\n\s*else:\s*\n\s*([^=]+) = ([^;]+)',
        r'\2 = \3 if hasattr(\1, "item") else \5',
        content,
        flags=re.MULTILINE,
    )

    return content


def fix_unused_variables(content: str) -> str:
    """Remove unused variable assignments."""
    lines = content.split("\n")
    fixed_lines: list[str] = []

    for line in lines:
        # Check for unused variable patterns
        if re.match(r"\s*params = LLMParametersInput\(", line):
            # Look ahead to see if params is used
            next_lines = content[content.find(line) :].split("\n")[:10]
            if not any("params." in next_line for next_line in next_lines):
                # Remove the line
                continue
        elif re.match(r"\s*client = TestClient\(", line):
            # Look ahead to see if client is used
            next_lines = content[content.find(line) :].split("\n")[:10]
            if not any("client." in next_line for next_line in next_lines):
                # Remove the line
                continue
        else:
            fixed_lines.append(line)

    return "\n".join(fixed_lines)


def fix_pytest_raises(content: str) -> str:
    """Fix pytest.raises patterns."""
    # Replace generic Exception with specific exceptions
    content = re.sub(r"with pytest\.raises\(Exception\):", "with pytest.raises(ValueError):", content)

    return content


def fix_trailing_whitespace(content: str) -> str:
    """Fix trailing whitespace."""
    lines = content.split("\n")
    fixed_lines = []

    for line in lines:
        # Remove trailing whitespace
        line = line.rstrip()
        fixed_lines.append(line)

    return "\n".join(fixed_lines)


def fix_test_file(file_path: Path) -> None:
    """Fix a single test file."""
    print(f"🔧 Fixing {file_path}")

    try:
        content = file_path.read_text(encoding="utf-8")

        # Apply all fixes
        content = fix_boolean_comparisons(content)
        content = fix_isinstance_patterns(content)
        content = fix_ternary_operators(content)
        content = fix_unused_variables(content)
        content = fix_pytest_raises(content)
        content = fix_trailing_whitespace(content)

        # Write back
        file_path.write_text(content, encoding="utf-8")
        print(f"✅ Fixed {file_path}")

    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")


def main():
    """Main function to fix all test files."""
    print("🚀 Starting remaining lint fixes...")

    # Find all test files
    test_dirs = ["tests/atomic", "tests/unit", "tests/integration", "tests/e2e"]

    for test_dir in test_dirs:
        if Path(test_dir).exists():
            for test_file in Path(test_dir).glob("test_*.py"):
                fix_test_file(test_file)

    print("✅ Remaining lint fixes completed!")


if __name__ == "__main__":
    main()
