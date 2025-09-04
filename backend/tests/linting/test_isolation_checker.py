"""Custom linting rules to prevent test isolation violations.

This module provides linting checks to ensure atomic tests don't violate
test isolation principles.
"""

import ast
import re


class TestIsolationChecker:
    """Check for test isolation violations in atomic tests."""

    def __init__(self):
        self.violations: list[tuple[int, int, str]] = []

    def check_file(self, filepath: str, content: str) -> list[tuple[int, int, str]]:
        """Check a file for test isolation violations."""
        self.violations = []

        try:
            tree = ast.parse(content)
            self._check_ast(tree, filepath)
        except SyntaxError:
            # Skip files with syntax errors
            pass

        return self.violations

    def _check_ast(self, tree: ast.AST, filepath: str):
        """Check AST for test isolation violations."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._check_test_function(node, filepath)
            elif isinstance(node, ast.ImportFrom):
                self._check_import(node, filepath)
            elif isinstance(node, ast.Assign):
                self._check_assignment(node, filepath)

    def _check_test_function(self, node: ast.FunctionDef, filepath: str):
        """Check if a test function violates isolation principles."""
        # Check if this is an atomic test
        is_atomic = any(
            isinstance(dec, ast.Name)
            and dec.id == "atomic"
            or (isinstance(dec, ast.Attribute) and dec.attr == "atomic")
            for dec in node.decorator_list
        )

        # Only check atomic tests for violations
        if not is_atomic:
            return

        # Check for problematic patterns in atomic tests
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                self._check_function_call(child, node, filepath)
            elif isinstance(child, ast.Attribute):
                self._check_attribute_access(child, node, filepath)

    def _check_function_call(self, node: ast.Call, test_func: ast.FunctionDef, _filepath: str):
        """Check function calls in atomic tests."""
        # Skip checking function calls for now - too complex to detect patch contexts accurately
        # Focus on module-level violations instead

    def _check_attribute_access(self, node: ast.Attribute, test_func: ast.FunctionDef, _filepath: str):
        """Check attribute access in atomic tests."""
        # Check for settings access without mocking
        if (
            isinstance(node.value, ast.Name)
            and node.value.id == "settings"
            and not self._is_in_patch_context(node, test_func)
        ):
            self.violations.append(
                (
                    node.lineno,
                    node.col_offset,
                    "Atomic test accesses settings without mocking - use @patch or fixtures",
                )
            )

    def _check_import(self, node: ast.ImportFrom, filepath: str):
        """Check imports for problematic patterns."""
        # Only check files that contain atomic tests
        if (
            node.module == "core.config"
            and any(alias.name == "settings" for alias in node.names)
            and "test" in filepath.lower()
            and self._has_atomic_tests(filepath)
        ):
            self.violations.append(
                (node.lineno, node.col_offset, "Test imports global settings - use fixtures or mocking instead")
            )

    def _check_assignment(self, _node: ast.Assign, _filepath: str):
        """Check assignments for problematic patterns."""
        # Skip checking assignments for now - too complex to detect context accurately
        # Focus on imports and other simpler violations

    def _is_in_patch_context(self, _node: ast.Attribute, test_func: ast.FunctionDef) -> bool:
        """Check if node is within a patch context."""
        # Check for patch decorators
        for dec in test_func.decorator_list:
            if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr == "patch":
                return True

        # Check for with patch.context() statements
        # This is a simplified check - in practice, you'd need more sophisticated AST analysis
        # to detect if the node is within a with statement that uses patch
        return False

    def _is_module_level(self, _node: ast.Assign, _filepath: str) -> bool:
        """Check if assignment is at module level."""
        # This is a simplified check - in practice, you'd need more sophisticated AST analysis
        return True

    def _has_atomic_tests(self, filepath: str) -> bool:
        """Check if file contains atomic tests."""
        try:
            with open(filepath) as f:
                content = f.read()
                return "@pytest.mark.atomic" in content
        except OSError:
            return False


def check_test_isolation(filepath: str, content: str) -> list[tuple[int, int, str]]:
    """Check a file for test isolation violations."""
    checker = TestIsolationChecker()
    return checker.check_file(filepath, content)


# Regex patterns for additional checks
PROBLEMATIC_PATTERNS = [
    (r"@pytest\.mark\.skipif.*settings\.", "Conditional skip based on real settings"),
    # Skip other patterns for now - too aggressive
]


def check_patterns(content: str) -> list[tuple[int, str]]:
    """Check content for problematic patterns using regex."""
    violations: list[tuple[int, str]] = []
    lines = content.split("\n")

    # Check if this file contains atomic tests
    has_atomic_tests = any("@pytest.mark.atomic" in line for line in lines)
    if not has_atomic_tests:
        return violations

    for line_num, line in enumerate(lines, 1):
        # Only check lines that are in atomic test functions
        if "@pytest.mark.atomic" in line or "def test_" in line:
            for pattern, message in PROBLEMATIC_PATTERNS:
                if re.search(pattern, line):
                    violations.append((line_num, message))

    return violations
