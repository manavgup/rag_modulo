"""Tests for SQLAlchemy import issues discovered in CI.

These tests reproduce the datetime import failures that cause CI to fail
when collecting atomic tests.
"""

import subprocess
import sys
from pathlib import Path


class TestSQLAlchemyImports:
    """Test SQLAlchemy model import issues."""

    def test_collection_model_imports_without_error(self):
        """Test that Collection model can be imported without datetime resolution errors.

        Expected: Should be able to import Collection model successfully
        Current: Fails with 'Could not resolve all types within mapped annotation: "Mapped[datetime]"'
        """
        # Test importing Collection model in isolation
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import sys
sys.path.insert(0, '.')
try:
    from rag_solution.models.collection import Collection
    print('SUCCESS: Collection model imported')
    exit(0)
except Exception as e:
    print(f'FAILED: {e}')
    exit(1)
            """,
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        # This should succeed but currently fails
        assert result.returncode == 0, f"Collection model import should work: {result.stderr}"
        assert "SUCCESS" in result.stdout

    def test_all_models_can_be_imported(self):
        """Test that all models with datetime annotations can be imported.

        Expected: All models should import without SQLAlchemy annotation errors
        Current: Multiple models fail with datetime resolution errors
        """
        models_to_test = ["collection", "file", "user", "llm_parameters", "llm_provider", "pipeline", "question"]

        for model_name in models_to_test:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    f"""
import sys
sys.path.insert(0, '.')
try:
    from rag_solution.models.{model_name} import {model_name.title().replace('_', '')}
    print('SUCCESS: {model_name} imported')
    exit(0)
except Exception as e:
    print(f'FAILED: {{e}}')
    exit(1)
                """,
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            # This should succeed but currently fails for models with datetime issues
            assert result.returncode == 0, f"{model_name} model should import: {result.stderr}"

    def test_models_with_type_checking_imports(self):
        """Test that models using TYPE_CHECKING for datetime imports work correctly.

        Expected: datetime should be available for annotation resolution
        Current: datetime only available during type checking, not runtime
        """
        # Test that datetime is available for SQLAlchemy at runtime
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
from __future__ import annotations
import sys
sys.path.insert(0, '.')
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

# This simulates what SQLAlchemy tries to do
try:
    # SQLAlchemy needs datetime at runtime, not just type checking
    datetime_type = eval('datetime')  # This is what fails
    print('SUCCESS: datetime available at runtime')
    exit(0)
except NameError:
    print('FAILED: datetime not available at runtime')
    exit(1)
            """,
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        # This should fail currently (demonstrating the issue)
        assert result.returncode != 0, "This should fail to demonstrate the TYPE_CHECKING issue"
        assert "FAILED: datetime not available at runtime" in result.stdout
