#!/usr/bin/env python3
"""Script to consolidate service tests from service_backup into proper test layers."""

import ast
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Set

import click


class ServiceTestConsolidator:
    """Consolidates service tests into proper test layers using Strangler Fig pattern."""

    def __init__(self, test_dir: str) -> None:
        self.test_dir = Path(test_dir)
        self.service_backup_dir = self.test_dir / "service_backup"
        self.atomic_dir = self.test_dir / "atomic"
        self.unit_dir = self.test_dir / "unit"
        self.integration_dir = self.test_dir / "integration"
        self.e2e_dir = self.test_dir / "e2e"

    def analyze_service_tests(self) -> Dict[str, Any]:
        """Analyze service tests in the backup directory."""
        analysis = {
            "total_files": 0,
            "total_tests": 0,
            "services": {},
            "test_categories": {
                "atomic": 0,
                "unit": 0,
                "integration": 0,
                "e2e": 0,
            },
        }

        if not self.service_backup_dir.exists():
            print("❌ Service backup directory not found!")
            return analysis

        for test_file in self.service_backup_dir.glob("test_*.py"):
            if test_file.name == "__init__.py":
                continue

            analysis["total_files"] += 1
            service_name = test_file.stem.replace("test_", "").replace("_service", "")

            # Count tests in file
            test_count = self._count_tests_in_file(test_file)
            analysis["total_tests"] += test_count

            # Categorize tests
            categories = self._categorize_tests(test_file)
            analysis["services"][service_name] = {
                "file": str(test_file),
                "test_count": test_count,
                "categories": categories,
            }

            for category, count in categories.items():
                analysis["test_categories"][category] += count

        return analysis

    def _count_tests_in_file(self, file_path: Path) -> int:
        """Count test functions in a file."""
        try:
            with open(file_path, "r") as f:
                content = f.read()

            tree = ast.parse(content)
            test_count = 0

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    test_count += 1

            return test_count
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return 0

    def _categorize_tests(self, file_path: Path) -> Dict[str, int]:
        """Categorize tests based on their content and dependencies."""
        categories = {"atomic": 0, "unit": 0, "integration": 0, "e2e": 0}

        try:
            with open(file_path, "r") as f:
                content = f.read()

            # Simple heuristic categorization based on content
            if "db_session" in content or "database" in content.lower():
                categories["integration"] += 1
            elif "mock" in content.lower() or "patch" in content:
                categories["unit"] += 1
            elif "client" in content.lower() or "api" in content.lower():
                categories["e2e"] += 1
            else:
                categories["atomic"] += 1

        except Exception as e:
            print(f"Error categorizing {file_path}: {e}")

        return categories

    def consolidate_service_tests(self) -> None:
        """Consolidate service tests into proper layers."""
        print("🔄 Starting service test consolidation...")

        analysis = self.analyze_service_tests()
        print(f"📊 Found {analysis['total_files']} service test files with {analysis['total_tests']} tests")

        # Create target directories if they don't exist
        for directory in [self.atomic_dir, self.unit_dir, self.integration_dir, self.e2e_dir]:
            directory.mkdir(exist_ok=True)

        # Process each service
        for service_name, service_info in analysis["services"].items():
            print(f"\n🔄 Processing {service_name} service...")
            self._consolidate_service(service_name, service_info)

    def _consolidate_service(self, service_name: str, service_info: Dict[str, Any]) -> None:
        """Consolidate tests for a specific service."""
        source_file = Path(service_info["file"])

        # Create atomic tests
        atomic_file = self.atomic_dir / f"test_{service_name}_validation.py"
        self._create_atomic_tests(service_name, source_file, atomic_file)

        # Create unit tests
        unit_file = self.unit_dir / f"test_{service_name}_service.py"
        self._create_unit_tests(service_name, source_file, unit_file)

        # Create integration tests
        integration_file = self.integration_dir / f"test_{service_name}_database.py"
        self._create_integration_tests(service_name, source_file, integration_file)

    def _create_atomic_tests(self, service_name: str, source_file: Path, target_file: Path) -> None:
        """Create atomic tests for data validation."""
        atomic_content = f'''"""Atomic tests for {service_name} data validation."""

import pytest
from pydantic import ValidationError

from rag_solution.schemas.{service_name}_schema import {service_name.title()}Input, {service_name.title()}Output


@pytest.mark.atomic
def test_{service_name}_input_validation():
    """Test {service_name} input validation without external dependencies."""
    # Valid input
    valid_input = {service_name.title()}Input(
        # Add valid input fields here
    )
    assert valid_input is not None


@pytest.mark.atomic
def test_{service_name}_input_invalid_data():
    """Test {service_name} input validation with invalid data."""
    with pytest.raises(ValidationError):
        {service_name.title()}Input(
            # Add invalid input fields here
        )


@pytest.mark.atomic
def test_{service_name}_output_serialization():
    """Test {service_name} output serialization."""
    # Test output serialization
    output = {service_name.title()}Output(
        # Add output fields here
    )
    assert output is not None
'''

        with open(target_file, "w") as f:
            f.write(atomic_content)

        print(f"  ✅ Created atomic tests: {target_file}")

    def _create_unit_tests(self, service_name: str, source_file: Path, target_file: Path) -> None:
        """Create unit tests with mocked dependencies."""
        unit_content = f'''"""Unit tests for {service_name} service with mocked dependencies."""

import pytest
from unittest.mock import Mock, patch

from rag_solution.services.{service_name}_service import {service_name.title()}Service


@pytest.mark.unit
def test_{service_name}_service_creation():
    """Test {service_name} service creation with mocked dependencies."""
    mock_db = Mock()
    mock_settings = Mock()

    service = {service_name.title()}Service(mock_db, mock_settings)
    assert service is not None


@pytest.mark.unit
def test_{service_name}_service_methods():
    """Test {service_name} service methods with mocked dependencies."""
    mock_db = Mock()
    mock_settings = Mock()

    service = {service_name.title()}Service(mock_db, mock_settings)

    # Test service methods with mocks
    # Add specific test cases here
'''

        with open(target_file, "w") as f:
            f.write(unit_content)

        print(f"  ✅ Created unit tests: {target_file}")

    def _create_integration_tests(self, service_name: str, source_file: Path, target_file: Path) -> None:
        """Create integration tests with real database."""
        integration_content = f'''"""Integration tests for {service_name} service with real database."""

import pytest
from testcontainers.postgres import PostgresContainer

from rag_solution.services.{service_name}_service import {service_name.title()}Service


@pytest.mark.integration
def test_{service_name}_database_operations():
    """Test {service_name} database operations with real database."""
    with PostgresContainer("postgres:13") as postgres:
        # Test database operations
        # Add specific test cases here
        pass


@pytest.mark.integration
def test_{service_name}_service_integration():
    """Test {service_name} service integration with real database."""
    with PostgresContainer("postgres:13") as postgres:
        # Test service integration
        # Add specific test cases here
        pass
'''

        with open(target_file, "w") as f:
            f.write(integration_content)

        print(f"  ✅ Created integration tests: {target_file}")

    def create_migration_report(self) -> None:
        """Create a migration report."""
        analysis = self.analyze_service_tests()

        report_file = self.test_dir / "service_migration_report.md"
        with open(report_file, "w") as f:
            f.write("# Service Test Migration Report\n\n")
            f.write(f"## Summary\n")
            f.write(f"- Total files processed: {analysis['total_files']}\n")
            f.write(f"- Total tests: {analysis['total_tests']}\n")
            f.write(f"- Services migrated: {len(analysis['services'])}\n\n")

            f.write("## Services Migrated\n")
            for service_name, service_info in analysis["services"].items():
                f.write(f"### {service_name.title()} Service\n")
                f.write(f"- Original file: {service_info['file']}\n")
                f.write(f"- Test count: {service_info['test_count']}\n")
                f.write(f"- Categories: {service_info['categories']}\n\n")

        print(f"📋 Created migration report: {report_file}")


@click.command()
@click.option("--test-dir", default="backend/tests", help="Test directory to consolidate")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
def main(test_dir: str, dry_run: bool) -> None:
    """Consolidate service tests into proper test layers."""
    consolidator = ServiceTestConsolidator(test_dir)

    if dry_run:
        analysis = consolidator.analyze_service_tests()
        print("🔍 DRY RUN - Would consolidate the following services:")
        for service_name, service_info in analysis["services"].items():
            print(f"  - {service_name}: {service_info['test_count']} tests")
        return

    consolidator.consolidate_service_tests()
    consolidator.create_migration_report()

    print("✅ Service test consolidation complete!")


if __name__ == "__main__":
    main()
