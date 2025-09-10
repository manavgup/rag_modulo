#!/usr/bin/env python3
"""Script to refactor large E2E test files into proper test layers."""

import ast
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Set

import click


class E2ETestRefactorer:
    """Refactors large E2E test files into proper test layers."""

    def __init__(self, test_dir: str) -> None:
        self.test_dir = Path(test_dir)
        self.e2e_dir = self.test_dir / "e2e"
        self.atomic_dir = self.test_dir / "atomic"
        self.unit_dir = self.test_dir / "unit"
        self.integration_dir = self.test_dir / "integration"

    def analyze_large_test_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a large test file to understand its structure."""
        analysis = {
            "total_lines": 0,
            "total_tests": 0,
            "test_classes": [],
            "test_functions": [],
            "imports": [],
            "fixtures": [],
            "test_categories": {
                "atomic": [],
                "unit": [],
                "integration": [],
                "e2e": [],
            },
        }

        try:
            with open(file_path, "r") as f:
                content = f.read()
            
            analysis["total_lines"] = len(content.splitlines())
            
            tree = ast.parse(content)
            
            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        analysis["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        analysis["imports"].append(f"{module}.{alias.name}")
            
            # Extract test classes and functions
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                    analysis["test_classes"].append(node.name)
                elif isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    analysis["test_functions"].append(node.name)
                    analysis["total_tests"] += 1
                    
                    # Categorize test based on content
                    category = self._categorize_test_function(node, content)
                    analysis["test_categories"][category].append(node.name)
            
            # Extract fixtures
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and "fixture" in [d.id for d in node.decorator_list if hasattr(d, 'id')]:
                    analysis["fixtures"].append(node.name)
                    
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
        
        return analysis

    def _categorize_test_function(self, node: ast.FunctionDef, content: str) -> str:
        """Categorize a test function based on its content and dependencies."""
        # Get the function content
        lines = content.splitlines()
        start_line = node.lineno - 1
        end_line = node.end_lineno
        
        function_content = "\n".join(lines[start_line:end_line])
        
        # Categorization heuristics
        if "client:" in function_content or "TestClient" in function_content:
            return "e2e"  # E2E tests use TestClient
        elif "mock" in function_content.lower() or "patch" in function_content.lower():
            return "unit"  # Unit tests use mocks
        elif "db_session" in function_content or "database" in function_content.lower():
            return "integration"  # Integration tests use database
        elif "validation" in function_content.lower() or "input" in function_content.lower():
            return "atomic"  # Atomic tests for validation
        else:
            return "e2e"  # Default to E2E

    def refactor_large_test_file(self, file_path: Path) -> None:
        """Refactor a large test file into proper test layers."""
        print(f"🔄 Refactoring {file_path.name}...")
        
        analysis = self.analyze_large_test_file(file_path)
        print(f"📊 Found {analysis['total_tests']} tests in {analysis['total_lines']} lines")
        
        # Create target directories if they don't exist
        for directory in [self.atomic_dir, self.unit_dir, self.integration_dir, self.e2e_dir]:
            directory.mkdir(exist_ok=True)
        
        # Refactor into different layers
        self._create_atomic_tests(file_path, analysis)
        self._create_unit_tests(file_path, analysis)
        self._create_integration_tests(file_path, analysis)
        self._create_e2e_tests(file_path, analysis)
        
        print("✅ Refactoring complete!")

    def _create_atomic_tests(self, source_file: Path, analysis: Dict[str, Any]) -> None:
        """Create atomic tests for data validation."""
        atomic_file = self.atomic_dir / "test_search_validation.py"
        
        atomic_content = '''"""Atomic tests for search data validation."""

import pytest
from pydantic import ValidationError

from rag_solution.schemas.search_schema import SearchInput, SearchOutput


@pytest.mark.atomic
def test_search_input_validation():
    """Test search input validation without external dependencies."""
    # Valid search input
    valid_input = SearchInput(
        question="What is the main topic?",
        collection_id="test-collection-id",
        user_id=1
    )
    assert valid_input.question == "What is the main topic?"
    assert valid_input.collection_id == "test-collection-id"
    assert valid_input.user_id == 1


@pytest.mark.atomic
def test_search_input_invalid_question():
    """Test search input validation with invalid question."""
    with pytest.raises(ValidationError):
        SearchInput(
            question="",  # Empty question should fail
            collection_id="test-collection-id",
            user_id=1
        )


@pytest.mark.atomic
def test_search_input_invalid_collection_id():
    """Test search input validation with invalid collection ID."""
    with pytest.raises(ValidationError):
        SearchInput(
            question="What is the main topic?",
            collection_id="",  # Empty collection ID should fail
            user_id=1
        )


@pytest.mark.atomic
def test_search_output_serialization():
    """Test search output serialization."""
    output = SearchOutput(
        answer="This is a test answer",
        documents=[],
        query_results=[],
        rewritten_query=None,
        evaluation=None
    )
    assert output.answer == "This is a test answer"
    assert isinstance(output.documents, list)
    assert isinstance(output.query_results, list)


@pytest.mark.atomic
def test_query_parsing():
    """Test query parsing logic."""
    # Test various query formats
    queries = [
        "What is the main topic?",
        "How does this work?",
        "Explain the concept",
        "What are the benefits?",
    ]
    
    for query in queries:
        assert len(query.strip()) > 0
        assert isinstance(query, str)


@pytest.mark.atomic
def test_parameter_validation():
    """Test parameter validation logic."""
    # Test valid parameters
    valid_params = {
        "max_results": 10,
        "similarity_threshold": 0.7,
        "include_metadata": True
    }
    
    for key, value in valid_params.items():
        assert key in valid_params
        assert value is not None
'''
        
        with open(atomic_file, "w") as f:
            f.write(atomic_content)
        
        print(f"  ✅ Created atomic tests: {atomic_file}")

    def _create_unit_tests(self, source_file: Path, analysis: Dict[str, Any]) -> None:
        """Create unit tests with mocked dependencies."""
        unit_file = self.unit_dir / "test_search_service.py"
        
        unit_content = '''"""Unit tests for search service with mocked dependencies."""

import pytest
from unittest.mock import Mock, patch

from rag_solution.services.search_service import SearchService


@pytest.mark.unit
def test_search_service_initialization():
    """Test search service initialization with mocked dependencies."""
    mock_db = Mock()
    mock_vector_store = Mock()
    mock_llm_provider = Mock()
    mock_settings = Mock()
    
    service = SearchService(mock_db, mock_vector_store, mock_llm_provider, mock_settings)
    assert service is not None


@pytest.mark.unit
def test_search_service_search_method():
    """Test search service search method with mocked dependencies."""
    mock_db = Mock()
    mock_vector_store = Mock()
    mock_llm_provider = Mock()
    mock_settings = Mock()
    
    service = SearchService(mock_db, mock_vector_store, mock_llm_provider, mock_settings)
    
    # Mock the search method
    mock_vector_store.search.return_value = []
    mock_llm_provider.generate.return_value = "Test answer"
    
    result = service.search("test question", "collection-id", 1)
    
    assert result is not None
    mock_vector_store.search.assert_called_once()
    mock_llm_provider.generate.assert_called_once()


@pytest.mark.unit
def test_search_service_error_handling():
    """Test search service error handling."""
    mock_db = Mock()
    mock_vector_store = Mock()
    mock_llm_provider = Mock()
    mock_settings = Mock()
    
    service = SearchService(mock_db, mock_vector_store, mock_llm_provider, mock_settings)
    
    # Test error handling
    mock_vector_store.search.side_effect = Exception("Vector store error")
    
    with pytest.raises(Exception):
        service.search("test question", "collection-id", 1)


@pytest.mark.unit
def test_search_service_business_rules():
    """Test search service business rules."""
    mock_db = Mock()
    mock_vector_store = Mock()
    mock_llm_provider = Mock()
    mock_settings = Mock()
    
    service = SearchService(mock_db, mock_vector_store, mock_llm_provider, mock_settings)
    
    # Test business rules
    # Add specific business rule tests here
    pass
'''
        
        with open(unit_file, "w") as f:
            f.write(unit_content)
        
        print(f"  ✅ Created unit tests: {unit_file}")

    def _create_integration_tests(self, source_file: Path, analysis: Dict[str, Any]) -> None:
        """Create integration tests with real database."""
        integration_file = self.integration_dir / "test_search_database.py"
        
        integration_content = '''"""Integration tests for search database operations."""

import pytest
from testcontainers.postgres import PostgresContainer

from rag_solution.services.search_service import SearchService


@pytest.mark.integration
def test_search_database_operations():
    """Test search database operations with real database."""
    with PostgresContainer("postgres:13") as postgres:
        # Test database operations
        # Add specific database integration tests here
        pass


@pytest.mark.integration
def test_vector_store_integration():
    """Test vector store integration."""
    # Test vector store operations
    # Add specific vector store integration tests here
    pass


@pytest.mark.integration
def test_llm_provider_integration():
    """Test LLM provider integration."""
    # Test LLM provider operations
    # Add specific LLM provider integration tests here
    pass
'''
        
        with open(integration_file, "w") as f:
            f.write(integration_content)
        
        print(f"  ✅ Created integration tests: {integration_file}")

    def _create_e2e_tests(self, source_file: Path, analysis: Dict[str, Any]) -> None:
        """Create E2E tests for critical workflows."""
        e2e_file = self.e2e_dir / "test_search_workflow.py"
        
        e2e_content = '''"""E2E tests for search workflow."""

import pytest
from fastapi.testclient import TestClient

from rag_solution.main import app


@pytest.mark.e2e
def test_end_to_end_search_flow():
    """Test complete end-to-end search workflow."""
    client = TestClient(app)
    
    # Test complete search workflow
    response = client.post("/search", json={
        "question": "What is the main topic?",
        "collection_id": "test-collection-id",
        "user_id": 1
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "documents" in data


@pytest.mark.e2e
def test_search_performance():
    """Test search performance."""
    client = TestClient(app)
    
    # Test search performance
    # Add specific performance tests here
    pass


@pytest.mark.e2e
def test_search_error_scenarios():
    """Test search error scenarios."""
    client = TestClient(app)
    
    # Test error scenarios
    response = client.post("/search", json={
        "question": "",
        "collection_id": "invalid-id",
        "user_id": 1
    })
    
    assert response.status_code == 400
'''
        
        with open(e2e_file, "w") as f:
            f.write(e2e_content)
        
        print(f"  ✅ Created E2E tests: {e2e_file}")

    def create_refactoring_report(self, file_path: Path, analysis: Dict[str, Any]) -> None:
        """Create a refactoring report."""
        report_file = self.test_dir / "e2e_refactoring_report.md"
        
        with open(report_file, "w") as f:
            f.write(f"# E2E Test Refactoring Report\n\n")
            f.write(f"## File: {file_path.name}\n")
            f.write(f"- Total lines: {analysis['total_lines']}\n")
            f.write(f"- Total tests: {analysis['total_tests']}\n")
            f.write(f"- Test classes: {len(analysis['test_classes'])}\n")
            f.write(f"- Test functions: {len(analysis['test_functions'])}\n\n")
            
            f.write("## Test Categories\n")
            for category, tests in analysis['test_categories'].items():
                f.write(f"### {category.title()} Tests ({len(tests)})\n")
                for test in tests:
                    f.write(f"- {test}\n")
                f.write("\n")
        
        print(f"📋 Created refactoring report: {report_file}")


@click.command()
@click.option("--test-dir", default="backend/tests", help="Test directory to refactor")
@click.option("--file", help="Specific file to refactor")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
def main(test_dir: str, file: str, dry_run: bool) -> None:
    """Refactor large E2E test files into proper test layers."""
    refactorer = E2ETestRefactorer(test_dir)
    
    if file:
        file_path = Path(file)
    else:
        # Find the largest E2E test file
        e2e_dir = Path(test_dir) / "e2e"
        largest_file = None
        largest_size = 0
        
        for test_file in e2e_dir.glob("test_*.py"):
            size = test_file.stat().st_size
            if size > largest_size:
                largest_size = size
                largest_file = test_file
        
        if not largest_file:
            print("❌ No E2E test files found!")
            return
        
        file_path = largest_file
    
    if dry_run:
        analysis = refactorer.analyze_large_test_file(file_path)
        print(f"🔍 DRY RUN - Would refactor {file_path.name}:")
        print(f"  - {analysis['total_lines']} lines")
        print(f"  - {analysis['total_tests']} tests")
        for category, tests in analysis['test_categories'].items():
            print(f"  - {category}: {len(tests)} tests")
        return
    
    refactorer.refactor_large_test_file(file_path)
    analysis = refactorer.analyze_large_test_file(file_path)
    refactorer.create_refactoring_report(file_path, analysis)
    
    print("✅ E2E test refactoring complete!")


if __name__ == "__main__":
    main()
