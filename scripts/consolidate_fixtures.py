#!/usr/bin/env python3
"""Script to consolidate duplicate fixtures and centralize fixture management."""

import ast
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Set

import click


class FixtureConsolidator:
    """Consolidates duplicate fixtures and centralizes fixture management."""

    def __init__(self, test_dir: str) -> None:
        self.test_dir = Path(test_dir)
        self.fixtures_dir = self.test_dir / "fixtures"
        self.duplicates = {
            "complex_test_pdf_path": [
                "integration/test_document_processors.py",
                "data_ingestion/test_pdf_processor.py"
            ],
            "mock_watsonx_imports": [
                "evaluation/test_evaluator.py",
                "evaluation/test_evaluation.py"
            ],
            "base_llm_parameters": [
                "fixtures/llm_parameter.py",
                "fixtures/llm.py"
            ],
            "mock_jwt_verification": [
                "e2e/test_auth_router.py",
                "e2e/test_health_router.py"
            ]
        }

    def consolidate_duplicates(self) -> None:
        """Consolidate duplicate fixtures into centralized locations."""
        print("🔧 Consolidating duplicate fixtures...")

        # Create centralized fixture files for each layer
        self._create_layer_fixture_files()

        # Consolidate each duplicate fixture
        for fixture_name, files in self.duplicates.items():
            self._consolidate_fixture(fixture_name, files)

    def _create_layer_fixture_files(self) -> None:
        """Create centralized fixture files for each testing layer."""
        layer_files = {
            "atomic.py": "# Atomic fixtures - Pure data, no dependencies",
            "unit.py": "# Unit fixtures - Mocked dependencies",
            "integration.py": "# Integration fixtures - Real services via testcontainers",
            "e2e.py": "# E2E fixtures - Full stack fixtures",
        }

        for filename, header in layer_files.items():
            file_path = self.fixtures_dir / filename
            if not file_path.exists():
                with open(file_path, "w") as f:
                    f.write(f'"""{header}"""\n\n')
                print(f"✅ Created {file_path}")

    def _consolidate_fixture(self, fixture_name: str, files: List[str]) -> None:
        """Consolidate a specific duplicate fixture."""
        print(f"🔄 Consolidating {fixture_name}...")

        # Determine the best location for the fixture
        target_layer = self._determine_fixture_layer(fixture_name)
        target_file = self.fixtures_dir / f"{target_layer}.py"

        # Extract the fixture definition from the first file
        fixture_def = self._extract_fixture_definition(fixture_name, files[0])
        if not fixture_def:
            print(f"❌ Could not extract fixture definition for {fixture_name}")
            return

        # Add the fixture to the target file
        self._add_fixture_to_file(fixture_def, target_file)

        # Remove the fixture from all source files
        for file_path in files:
            self._remove_fixture_from_file(fixture_name, file_path)

        print(f"✅ Consolidated {fixture_name} into {target_file}")

    def _determine_fixture_layer(self, fixture_name: str) -> str:
        """Determine which layer a fixture belongs to."""
        if "mock" in fixture_name.lower():
            return "unit"
        elif "base_" in fixture_name.lower():
            return "atomic"
        elif "complex" in fixture_name.lower():
            return "integration"
        else:
            return "unit"  # Default to unit

    def _extract_fixture_definition(self, fixture_name: str, file_path: str) -> str:
        """Extract fixture definition from a file."""
        full_path = self.test_dir / file_path
        try:
            with open(full_path, "r") as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == fixture_name:
                    # Extract the function definition
                    lines = content.split('\n')
                    start_line = node.lineno - 1
                    end_line = node.end_lineno

                    # Include decorators
                    decorator_lines = []
                    for decorator in node.decorator_list:
                        if hasattr(decorator, 'lineno'):
                            decorator_lines.append(decorator.lineno - 1)

                    if decorator_lines:
                        start_line = min(decorator_lines)

                    fixture_code = '\n'.join(lines[start_line:end_line])
                    return fixture_code

        except Exception as e:
            print(f"Error extracting fixture from {file_path}: {e}")

        return None

    def _add_fixture_to_file(self, fixture_def: str, target_file: Path) -> None:
        """Add a fixture definition to a target file."""
        with open(target_file, "a") as f:
            f.write(f"\n{fixture_def}\n")

    def _remove_fixture_from_file(self, fixture_name: str, file_path: str) -> None:
        """Remove a fixture definition from a file."""
        full_path = self.test_dir / file_path
        try:
            with open(full_path, "r") as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == fixture_name:
                    # Remove the function definition
                    lines = content.split('\n')
                    start_line = node.lineno - 1
                    end_line = node.end_lineno

                    # Include decorators
                    decorator_lines = []
                    for decorator in node.decorator_list:
                        if hasattr(decorator, 'lineno'):
                            decorator_lines.append(decorator.lineno - 1)

                    if decorator_lines:
                        start_line = min(decorator_lines)

                    # Remove the fixture
                    new_lines = lines[:start_line] + lines[end_line:]
                    new_content = '\n'.join(new_lines)

                    with open(full_path, "w") as f:
                        f.write(new_content)

                    print(f"✅ Removed {fixture_name} from {file_path}")
                    break

        except Exception as e:
            print(f"Error removing fixture from {file_path}: {e}")

    def create_fixture_imports(self) -> None:
        """Create import statements for centralized fixtures."""
        print("📦 Creating fixture import statements...")

        # Create __init__.py for fixtures
        init_file = self.fixtures_dir / "__init__.py"
        with open(init_file, "w") as f:
            f.write('"""Centralized test fixtures."""\n\n')
            f.write("# Import all fixtures for easy access\n")
            f.write("from .atomic import *\n")
            f.write("from .unit import *\n")
            f.write("from .integration import *\n")
            f.write("from .e2e import *\n")

        print("✅ Created fixture imports")

    def update_test_files(self) -> None:
        """Update test files to use centralized fixtures."""
        print("🔄 Updating test files to use centralized fixtures...")

        # This would update import statements in test files
        # For now, just create a mapping file
        mapping_file = self.test_dir / "fixture_migration_mapping.txt"
        with open(mapping_file, "w") as f:
            f.write("# Fixture Migration Mapping\n")
            f.write("# Update these imports in your test files:\n\n")

            for fixture_name, files in self.duplicates.items():
                f.write(f"# {fixture_name}\n")
                f.write(f"# Old: from {files[0].replace('/', '.').replace('.py', '')} import {fixture_name}\n")
                f.write(f"# New: from tests.fixtures import {fixture_name}\n\n")

        print(f"✅ Created migration mapping at {mapping_file}")


@click.command()
@click.option("--test-dir", default="backend/tests", help="Test directory to consolidate")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
def main(test_dir: str, dry_run: bool) -> None:
    """Consolidate duplicate fixtures and centralize fixture management."""
    consolidator = FixtureConsolidator(test_dir)

    if dry_run:
        print("🔍 DRY RUN - Would consolidate the following fixtures:")
        for fixture_name, files in consolidator.duplicates.items():
            print(f"  - {fixture_name}: {files}")
        return

    consolidator.consolidate_duplicates()
    consolidator.create_fixture_imports()
    consolidator.update_test_files()

    print("✅ Fixture consolidation complete!")


if __name__ == "__main__":
    main()
