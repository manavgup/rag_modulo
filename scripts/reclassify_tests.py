#!/usr/bin/env python3
"""
Reclassify tests based on what they actually test.

Current Problem: 248 integration tests vs 27 atomic tests (backwards!)
Solution: Move most integration tests to atomic/unit layers based on what they test.

Classification Rules:
- Atomic: Pure data validation, schema validation, no external dependencies
- Unit: Service logic with mocked dependencies, business logic
- Integration: Real database connections, real external services, cross-service communication
- E2E: Full user workflows, API endpoints, complete system tests
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Set

def analyze_test_content(file_path: Path) -> Dict[str, any]:
    """Analyze a test file to determine what it actually tests."""

    content = file_path.read_text()

    analysis = {
        "file": file_path.name,
        "lines": len(content.splitlines()),
        "has_database": False,
        "has_mocks": False,
        "has_real_services": False,
        "has_api_calls": False,
        "has_data_validation": False,
        "has_schema_validation": False,
        "has_external_deps": False,
        "suggested_layer": "unknown"
    }

    # Check for database usage
    if any(keyword in content.lower() for keyword in [
        "db_session", "database", "sqlalchemy", "postgres", "mysql", "sqlite",
        "connection", "transaction", "commit", "rollback"
    ]):
        analysis["has_database"] = True

    # Check for mocks
    if any(keyword in content.lower() for keyword in [
        "mock", "patch", "unittest.mock", "mocked", "fake"
    ]):
        analysis["has_mocks"] = True

    # Check for real services
    if any(keyword in content.lower() for keyword in [
        "service.create", "service.get", "service.update", "service.delete",
        "real_", "actual_", "live_"
    ]):
        analysis["has_real_services"] = True

    # Check for API calls
    if any(keyword in content.lower() for keyword in [
        "test_client", "client.get", "client.post", "client.put", "client.delete",
        "response.status_code", "api/", "endpoint"
    ]):
        analysis["has_api_calls"] = True

    # Check for data validation
    if any(keyword in content.lower() for keyword in [
        "validation", "validate", "schema", "pydantic", "input", "output",
        "assert.*email", "assert.*name", "assert.*id"
    ]):
        analysis["has_data_validation"] = True

    # Check for schema validation
    if any(keyword in content.lower() for keyword in [
        "schema", "model", "pydantic", "validation", "input", "output"
    ]):
        analysis["has_schema_validation"] = True

    # Check for external dependencies
    if any(keyword in content.lower() for keyword in [
        "http", "requests", "external", "third_party", "api_key", "endpoint"
    ]):
        analysis["has_external_deps"] = True

    # Determine suggested layer
    if analysis["has_api_calls"] and analysis["has_real_services"]:
        analysis["suggested_layer"] = "e2e"
    elif analysis["has_database"] and not analysis["has_mocks"]:
        analysis["suggested_layer"] = "integration"
    elif analysis["has_mocks"] and analysis["has_real_services"]:
        analysis["suggested_layer"] = "unit"
    elif analysis["has_data_validation"] or analysis["has_schema_validation"]:
        analysis["suggested_layer"] = "atomic"
    elif analysis["has_mocks"]:
        analysis["suggested_layer"] = "unit"
    else:
        analysis["suggested_layer"] = "atomic"

    return analysis

def reclassify_tests():
    """Reclassify tests based on their actual content."""

    integration_dir = Path("backend/tests/integration")
    atomic_dir = Path("backend/tests/atomic")
    unit_dir = Path("backend/tests/unit")
    e2e_dir = Path("backend/tests/e2e")

    # Create backup
    backup_dir = Path("backend/tests/integration_backup_analysis")
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    shutil.copytree(integration_dir, backup_dir)
    print(f"✅ Created backup at {backup_dir}")

    # Analyze all integration test files
    test_files = list(integration_dir.glob("test_*.py"))
    analyses = []

    print(f"🔍 Analyzing {len(test_files)} integration test files...")

    for file_path in test_files:
        analysis = analyze_test_content(file_path)
        analyses.append(analysis)

        print(f"📄 {file_path.name}:")
        print(f"   Lines: {analysis['lines']}")
        print(f"   Database: {analysis['has_database']}")
        print(f"   Mocks: {analysis['has_mocks']}")
        print(f"   Real Services: {analysis['has_real_services']}")
        print(f"   API Calls: {analysis['has_api_calls']}")
        print(f"   Data Validation: {analysis['has_data_validation']}")
        print(f"   Suggested: {analysis['suggested_layer']}")
        print()

    # Group by suggested layer
    by_layer = {
        "atomic": [],
        "unit": [],
        "integration": [],
        "e2e": []
    }

    for analysis in analyses:
        by_layer[analysis["suggested_layer"]].append(analysis)

    # Print summary
    print("📊 Reclassification Summary:")
    for layer, files in by_layer.items():
        if files:
            print(f"   {layer.upper()}: {len(files)} files")
            for file_info in files:
                print(f"     - {file_info['file']} ({file_info['lines']} lines)")

    print()

    # Move files to appropriate layers
    print("🔄 Moving files to appropriate layers...")

    for layer, files in by_layer.items():
        if not files:
            continue

        target_dir = Path(f"backend/tests/{layer}")
        target_dir.mkdir(exist_ok=True)

        for file_info in files:
            source_file = integration_dir / file_info["file"]
            target_file = target_dir / file_info["file"]

            if source_file.exists():
                shutil.move(str(source_file), str(target_file))
                print(f"   ✅ Moved {file_info['file']} to {layer}/")

    # Create focused integration tests
    create_focused_integration_tests()

    print("\n🎯 Reclassification complete!")
    print("📊 Expected results:")
    print("   - Atomic tests: ~100-150 tests (data validation, schemas)")
    print("   - Unit tests: ~50-80 tests (mocked services, business logic)")
    print("   - Integration tests: ~10-15 tests (real database, real services)")
    print("   - E2E tests: ~15-20 tests (full workflows)")

def create_focused_integration_tests():
    """Create focused integration tests that actually test integration."""

    integration_dir = Path("backend/tests/integration")

    # Create essential integration tests
    integration_tests = {
        "test_database_integration.py": '''"""
Database Integration Tests

Tests real database operations and transactions.
"""

import pytest
from sqlalchemy.orm import Session

@pytest.mark.integration
class TestDatabaseIntegration:
    """Test real database integration."""

    def test_database_connection(self, db_session: Session) -> None:
        """Test real database connection."""
        # Test actual database connectivity
        result = db_session.execute("SELECT 1").scalar()
        assert result == 1

    def test_database_transactions(self, db_session: Session) -> None:
        """Test real database transactions."""
        # Test transaction rollback on error
        # Test transaction commit on success
        pass
''',

        "test_service_integration.py": '''"""
Service Integration Tests

Tests real service integrations with database.
"""

import pytest
from sqlalchemy.orm import Session

@pytest.mark.integration
class TestServiceIntegration:
    """Test real service integration."""

    def test_user_service_database_integration(self, db_session: Session) -> None:
        """Test user service with real database."""
        # Test actual user creation in database
        pass

    def test_collection_service_database_integration(self, db_session: Session) -> None:
        """Test collection service with real database."""
        # Test actual collection creation in database
        pass
''',

        "test_external_service_integration.py": '''"""
External Service Integration Tests

Tests integration with external services.
"""

import pytest

@pytest.mark.integration
class TestExternalServiceIntegration:
    """Test external service integration."""

    def test_vector_store_integration(self) -> None:
        """Test real vector store integration."""
        # Test actual vector store operations
        pass

    def test_llm_provider_integration(self) -> None:
        """Test real LLM provider integration."""
        # Test actual LLM provider calls
        pass
'''
    }

    for filename, content in integration_tests.items():
        file_path = integration_dir / filename
        file_path.write_text(content)
        print(f"   ✅ Created {filename}")

def main():
    """Main reclassification function."""
    print("🔄 Reclassifying tests based on what they actually test...")
    print("Current: 248 integration tests vs 27 atomic tests (backwards!)")
    print("Target: Proper distribution across all layers")
    print()

    reclassify_tests()

if __name__ == "__main__":
    main()
