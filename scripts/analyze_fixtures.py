#!/usr/bin/env python3
"""Script to analyze and discover fixtures across the test suite."""

import ast
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import click


class FixtureAnalyzer:
    """Analyzes pytest fixtures across the test suite."""

    def __init__(self, test_dir: str) -> None:
        self.test_dir = Path(test_dir)
        self.fixtures: Dict[str, Dict[str, Any]] = {}
        self.duplicates: Dict[str, List[str]] = defaultdict(list)
        self.usage_count: Dict[str, int] = defaultdict(int)

    def analyze_file(self, file_path: Path) -> None:
        """Analyze a single Python file for fixtures."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if self._is_fixture(node):
                        self._extract_fixture_info(node, file_path)

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")

    def _is_fixture(self, node: ast.FunctionDef) -> bool:
        """Check if a function is a pytest fixture."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "fixture":
                return True
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name) and decorator.func.id == "fixture":
                    return True
                if isinstance(decorator.func, ast.Attribute) and decorator.func.attr == "fixture":
                    return True
        return False

    def _extract_fixture_info(self, node: ast.FunctionDef, file_path: Path) -> None:
        """Extract information about a fixture."""
        fixture_name = node.name

        # Determine fixture type based on file location
        fixture_type = self._determine_fixture_type(file_path)

        # Extract scope from decorators
        scope = self._extract_scope(node)

        # Extract dependencies from function parameters
        dependencies = [arg.arg for arg in node.args.args if arg.arg != "self"]

        # Store fixture information
        self.fixtures[fixture_name] = {
            "file": str(file_path.relative_to(self.test_dir)),
            "type": fixture_type,
            "scope": scope,
            "dependencies": dependencies,
            "line_number": node.lineno,
            "docstring": ast.get_docstring(node) or "",
        }

        # Track duplicates
        self.duplicates[fixture_name].append(str(file_path.relative_to(self.test_dir)))

    def _determine_fixture_type(self, file_path: Path) -> str:
        """Determine fixture type based on file location."""
        path_parts = file_path.parts

        if "atomic" in path_parts:
            return "atomic"
        elif "unit" in path_parts:
            return "unit"
        elif "integration" in path_parts:
            return "integration"
        elif "e2e" in path_parts:
            return "e2e"
        elif "fixtures" in path_parts:
            return "centralized"
        else:
            return "scattered"

    def _extract_scope(self, node: ast.FunctionDef) -> str:
        """Extract fixture scope from decorators."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                for keyword in decorator.keywords:
                    if keyword.arg == "scope":
                        if isinstance(keyword.value, ast.Constant):
                            return keyword.value.value
        return "function"  # Default scope

    def analyze_directory(self) -> None:
        """Analyze all Python files in the test directory."""
        for py_file in self.test_dir.rglob("*.py"):
            if py_file.name != "__init__.py":
                self.analyze_file(py_file)

    def find_duplicates(self) -> Dict[str, List[str]]:
        """Find duplicate fixtures."""
        return {name: files for name, files in self.duplicates.items() if len(files) > 1}

    def generate_report(self) -> str:
        """Generate a comprehensive fixture analysis report."""
        report = []
        report.append("# Fixture Analysis Report")
        report.append("=" * 50)
        report.append("")

        # Summary statistics
        total_fixtures = len(self.fixtures)
        duplicates = self.find_duplicates()

        report.append(f"## Summary")
        report.append(f"- Total fixtures: {total_fixtures}")
        report.append(f"- Duplicate fixtures: {len(duplicates)}")
        report.append("")

        # Fixture distribution by type
        type_distribution = defaultdict(int)
        for fixture_info in self.fixtures.values():
            type_distribution[fixture_info["type"]] += 1

        report.append("## Fixture Distribution by Type")
        for fixture_type, count in sorted(type_distribution.items()):
            report.append(f"- {fixture_type}: {count}")
        report.append("")

        # Duplicate fixtures
        if duplicates:
            report.append("## Duplicate Fixtures")
            for fixture_name, files in duplicates.items():
                report.append(f"### {fixture_name}")
                report.append(f"Found in {len(files)} files:")
                for file_path in files:
                    report.append(f"- {file_path}")
                report.append("")

        # Fixtures by file
        file_fixtures = defaultdict(list)
        for fixture_name, fixture_info in self.fixtures.items():
            file_fixtures[fixture_info["file"]].append(fixture_name)

        report.append("## Fixtures by File")
        for file_path, fixtures in sorted(file_fixtures.items()):
            report.append(f"### {file_path}")
            report.append(f"Fixtures ({len(fixtures)}): {', '.join(fixtures)}")
            report.append("")

        return "\n".join(report)

    def export_fixture_mapping(self) -> Dict[str, Any]:
        """Export fixture mapping for migration planning."""
        duplicates = self.find_duplicates()

        # Fixture distribution by type
        type_distribution = defaultdict(int)
        for fixture_info in self.fixtures.values():
            type_distribution[fixture_info["type"]] += 1

        # Fixtures by file
        file_fixtures = defaultdict(list)
        for fixture_name, fixture_info in self.fixtures.items():
            file_fixtures[fixture_info["file"]].append(fixture_name)

        return {
            "total_fixtures": len(self.fixtures),
            "duplicates": dict(duplicates),
            "fixtures_by_type": dict(type_distribution),
            "fixtures_by_file": dict(file_fixtures),
        }


@click.command()
@click.option("--test-dir", default="backend/tests", help="Test directory to analyze")
@click.option("--output", help="Output file for the report")
@click.option("--export-json", help="Export JSON mapping file")
def main(test_dir: str, output: str, export_json: str) -> None:
    """Analyze pytest fixtures across the test suite."""
    analyzer = FixtureAnalyzer(test_dir)
    analyzer.analyze_directory()

    report = analyzer.generate_report()

    if output:
        with open(output, "w") as f:
            f.write(report)
        print(f"Report written to {output}")
    else:
        print(report)

    if export_json:
        mapping = analyzer.export_fixture_mapping()
        import json
        with open(export_json, "w") as f:
            json.dump(mapping, f, indent=2)
        print(f"JSON mapping written to {export_json}")


if __name__ == "__main__":
    main()
