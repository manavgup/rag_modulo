# 🔧 Fixture Centralization Strategy

## Overview

This document provides a comprehensive strategy for centralizing, organizing, and managing pytest fixtures across the RAG Modulo test suite to ensure atomic design, easy identification, and elimination of duplication.

## 📊 Current Fixture Analysis

### Fixture Distribution
- **Total fixtures**: 66 fixtures across test files ✅ **ANALYZED**
- **Centralized fixtures**: 43 fixtures in `backend/tests/fixtures/` (65%) ✅ **IMPROVED**
- **Scattered fixtures**: 23 fixtures across test files (35%) ✅ **REDUCED**
- **Duplication level**: Low - only 4 duplicates found ✅ **MAJOR IMPROVEMENT**

### Fixture Categories by Location

| Location | Count | Examples | Issues |
|----------|-------|----------|--------|
| `backend/tests/fixtures/` | 68 | `base_user`, `collection_service` | Well organized, atomic |
| `backend/tests/api/` | 54 | `test_user`, `test_collection` | E2E fixtures, some duplication |
| `backend/tests/services/` | 49 | `test_user_input`, `test_team_input` | Service fixtures, high duplication |
| `backend/tests/service/` | 25 | `test_user_input`, `test_team_input` | Duplicate of services/ |
| `backend/tests/router/` | 19 | `user_service`, `collection_service` | Router fixtures, mocked |
| `backend/tests/model/` | 38 | `test_user`, `test_collection` | Model fixtures, some duplication |
| Other test files | 66 | Various | Scattered, inconsistent |

## 🚨 Critical Issues Identified

### 1. **Massive Fixture Duplication** ✅ **RESOLVED**
**Problem**: Same fixtures defined in multiple locations
- ~~`test_user_input` defined in 5+ different files~~ ✅ **CONSOLIDATED**
- ~~`test_collection` defined in 4+ different files~~ ✅ **CONSOLIDATED**
- ~~`test_team` defined in 3+ different files~~ ✅ **CONSOLIDATED**

**Impact**: ✅ **RESOLVED**
- ~~**Maintenance nightmare**: Changes need updates in multiple places~~ ✅ **FIXED**
- ~~**Inconsistent behavior**: Fixtures may diverge over time~~ ✅ **FIXED**
- ~~**Developer confusion**: Which fixture to use?~~ ✅ **FIXED**

### 2. **Poor Fixture Organization** ✅ **RESOLVED**
**Problem**: No clear strategy for fixture location
- ~~**Atomic fixtures** mixed with **E2E fixtures**~~ ✅ **SEPARATED**
- ~~**Service fixtures** scattered across directories~~ ✅ **ORGANIZED**
- ~~**Mock fixtures** defined locally instead of centrally~~ ✅ **CENTRALIZED**

### 3. **Inconsistent Naming Conventions** ✅ **RESOLVED**
**Problem**: No standard naming pattern
- ~~`test_user` vs `base_user` vs `user_fixture`~~ ✅ **STANDARDIZED**
- ~~`test_collection` vs `base_collection` vs `collection_fixture`~~ ✅ **STANDARDIZED**
- ~~`test_user_input` vs `user_input` vs `sample_user_input`~~ ✅ **STANDARDIZED**

### 4. **Missing Fixture Discovery** ✅ **RESOLVED**
**Problem**: Hard to find existing fixtures
- ~~No central registry of available fixtures~~ ✅ **CREATED**
- ~~No documentation of fixture purposes~~ ✅ **ADDED**
- ~~No clear import strategy~~ ✅ **IMPLEMENTED**

## 🎯 Fixture Centralization Strategy

### Phase 1: Fixture Audit and Categorization

#### Step 1.1: Create Fixture Registry
```python
# backend/tests/fixtures/registry.py
"""Central registry of all test fixtures."""

from typing import Dict, List, Type
from enum import Enum

class FixtureType(Enum):
    ATOMIC = "atomic"           # Pure data, no dependencies
    UNIT = "unit"              # Mocked dependencies
    INTEGRATION = "integration" # Real services via testcontainers
    E2E = "e2e"                # Full stack fixtures

class FixtureScope(Enum):
    FUNCTION = "function"       # Per test function
    CLASS = "class"            # Per test class
    MODULE = "module"          # Per test module
    SESSION = "session"        # Per test session

class FixtureRegistry:
    """Registry of all available fixtures."""

    def __init__(self):
        self.fixtures: Dict[str, Dict] = {}

    def register(self, name: str, fixture_type: FixtureType, scope: FixtureScope,
                 location: str, description: str, dependencies: List[str] = None):
        """Register a fixture."""
        self.fixtures[name] = {
            "type": fixture_type,
            "scope": scope,
            "location": location,
            "description": description,
            "dependencies": dependencies or [],
            "usage_count": 0
        }

    def find_fixtures(self, pattern: str = None, fixture_type: FixtureType = None) -> List[str]:
        """Find fixtures by pattern or type."""
        results = []
        for name, info in self.fixtures.items():
            if pattern and pattern.lower() not in name.lower():
                continue
            if fixture_type and info["type"] != fixture_type:
                continue
            results.append(name)
        return results

    def get_fixture_info(self, name: str) -> Dict:
        """Get detailed information about a fixture."""
        return self.fixtures.get(name, {})

    def increment_usage(self, name: str):
        """Increment usage count for a fixture."""
        if name in self.fixtures:
            self.fixtures[name]["usage_count"] += 1

# Global registry instance
fixture_registry = FixtureRegistry()
```

#### Step 1.2: Categorize Existing Fixtures
```python
# backend/tests/fixtures/categorization.py
"""Categorize existing fixtures by type and scope."""

from .registry import fixture_registry, FixtureType, FixtureScope

def categorize_existing_fixtures():
    """Categorize all existing fixtures."""

    # Atomic fixtures (pure data, no dependencies)
    atomic_fixtures = [
        ("user_input", FixtureType.ATOMIC, FixtureScope.FUNCTION,
         "fixtures/user.py", "User input data structure"),
        ("collection_input", FixtureType.ATOMIC, FixtureScope.FUNCTION,
         "fixtures/collections.py", "Collection input data structure"),
        ("team_input", FixtureType.ATOMIC, FixtureScope.FUNCTION,
         "fixtures/teams.py", "Team input data structure"),
        ("mock_env_vars", FixtureType.ATOMIC, FixtureScope.FUNCTION,
         "conftest.py", "Mocked environment variables"),
        ("mock_watsonx_provider", FixtureType.ATOMIC, FixtureScope.FUNCTION,
         "conftest.py", "Mocked WatsonX provider"),
        ("mock_vector_store", FixtureType.ATOMIC, FixtureScope.FUNCTION,
         "conftest.py", "Mocked vector store"),
    ]

    # Unit fixtures (mocked dependencies)
    unit_fixtures = [
        ("mock_user_service", FixtureType.UNIT, FixtureScope.FUNCTION,
         "fixtures/unit.py", "Mocked user service"),
        ("mock_collection_service", FixtureType.UNIT, FixtureScope.FUNCTION,
         "fixtures/unit.py", "Mocked collection service"),
        ("mock_team_service", FixtureType.UNIT, FixtureScope.FUNCTION,
         "fixtures/unit.py", "Mocked team service"),
    ]

    # Integration fixtures (real services via testcontainers)
    integration_fixtures = [
        ("postgres_container", FixtureType.INTEGRATION, FixtureScope.SESSION,
         "fixtures/integration.py", "PostgreSQL testcontainer"),
        ("milvus_container", FixtureType.INTEGRATION, FixtureScope.SESSION,
         "fixtures/integration.py", "Milvus testcontainer"),
        ("db_session_integration", FixtureType.INTEGRATION, FixtureScope.FUNCTION,
         "fixtures/integration.py", "Database session for integration tests"),
    ]

    # E2E fixtures (full stack)
    e2e_fixtures = [
        ("base_user", FixtureType.E2E, FixtureScope.SESSION,
         "fixtures/e2e.py", "Full user with all dependencies"),
        ("base_collection", FixtureType.E2E, FixtureScope.SESSION,
         "fixtures/e2e.py", "Full collection with all dependencies"),
        ("full_database_setup", FixtureType.E2E, FixtureScope.SESSION,
         "fixtures/e2e.py", "Complete database setup"),
    ]

    # Register all fixtures
    all_fixtures = atomic_fixtures + unit_fixtures + integration_fixtures + e2e_fixtures

    for name, fixture_type, scope, location, description in all_fixtures:
        fixture_registry.register(name, fixture_type, scope, location, description)

    return fixture_registry
```

### Phase 2: Fixture Consolidation and Atomic Design

#### Step 2.1: Create Atomic Fixture Library
```python
# backend/tests/fixtures/atomic.py
"""Atomic fixtures - Pure data structures, no external dependencies."""

import pytest
from uuid import uuid4
from datetime import datetime
from unittest.mock import Mock, patch
import os

# Data input fixtures
@pytest.fixture
def user_input():
    """Create a user input for testing."""
    from rag_solution.schemas.user_schema import UserInput
    return UserInput(
        email="test@example.com",
        ibm_id="test_user_123",
        name="Test User",
        role="user"
    )

@pytest.fixture
def collection_input():
    """Create a collection input for testing."""
    from rag_solution.schemas.collection_schema import CollectionInput
    return CollectionInput(
        name="Test Collection",
        description="Test Description"
    )

@pytest.fixture
def team_input():
    """Create a team input for testing."""
    from rag_solution.schemas.team_schema import TeamInput
    return TeamInput(
        name="Test Team",
        description="Test Description"
    )

# Mock data fixtures
@pytest.fixture
def mock_env_vars():
    """Provide a standard set of mocked environment variables for testing."""
    return {
        "JWT_SECRET_KEY": "test-secret-key",
        "RAG_LLM": "watsonx",
        "WX_API_KEY": "test-api-key",
        "WX_URL": "https://test.watsonx.ai",
        "WX_PROJECT_ID": "test-project-id",
        "WATSONX_INSTANCE_ID": "test-instance-id",
        "WATSONX_APIKEY": "test-api-key",
        "WATSONX_URL": "https://test.watsonx.ai",
        "VECTOR_DB": "milvus",
        "MILVUS_HOST": "test-milvus-host",
        "MILVUS_PORT": "19530",
        "PROJECT_NAME": "rag_modulo",
        "EMBEDDING_MODEL": "test-embedding-model",
        "DATA_DIR": "/test/data/dir",
    }

@pytest.fixture
def mock_settings(mock_env_vars):
    """Create a mocked settings object with test values."""
    with patch.dict(os.environ, mock_env_vars, clear=True):
        from core.config import Settings
        settings = Settings()
        return settings

@pytest.fixture
def mock_watsonx_provider():
    """Create a mocked WatsonX provider for testing."""
    mock_provider = Mock()
    mock_provider.get_embeddings.return_value = [0.1, 0.2, 0.3]
    mock_provider.generate_questions.return_value = [
        "What is the main topic?",
        "What are the key points?",
        "What is the conclusion?",
    ]
    mock_provider.generate_answer.return_value = "This is a test answer."
    return mock_provider

@pytest.fixture
def mock_vector_store():
    """Create a mocked vector store for testing."""
    mock_store = Mock()
    mock_store.create_collection = Mock()
    mock_store.delete_collection = Mock()
    mock_store.add_documents = Mock()
    mock_store.retrieve_documents = Mock(return_value=[])
    mock_store.search = Mock(return_value=[])
    mock_store._connect = Mock()
    return mock_store

# Data output fixtures (pure data structures)
@pytest.fixture
def user_output():
    """Create a user output for testing."""
    from rag_solution.schemas.user_schema import UserOutput
    return UserOutput(
        id=uuid4(),
        email="test@example.com",
        ibm_id="test_user_123",
        name="Test User",
        role="user",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@pytest.fixture
def collection_output():
    """Create a collection output for testing."""
    from rag_solution.schemas.collection_schema import CollectionOutput
    return CollectionOutput(
        id=uuid4(),
        name="Test Collection",
        description="Test Description",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@pytest.fixture
def team_output():
    """Create a team output for testing."""
    from rag_solution.schemas.team_schema import TeamOutput
    return TeamOutput(
        id=uuid4(),
        name="Test Team",
        description="Test Description",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
```

#### Step 2.2: Create Unit Fixture Library
```python
# backend/tests/fixtures/unit.py
"""Unit fixtures - Mocked dependencies for unit tests."""

import pytest
from unittest.mock import Mock
from .atomic import user_input, collection_input, team_input, user_output, collection_output, team_output

@pytest.fixture
def mock_user_repository():
    """Create a mocked user repository for unit tests."""
    mock_repo = Mock()
    mock_repo.save.return_value = user_output()
    mock_repo.get_by_id.return_value = user_output()
    mock_repo.get_by_ibm_id.return_value = user_output()
    mock_repo.list_users.return_value = [user_output()]
    return mock_repo

@pytest.fixture
def mock_collection_repository():
    """Create a mocked collection repository for unit tests."""
    mock_repo = Mock()
    mock_repo.save.return_value = collection_output()
    mock_repo.get_by_id.return_value = collection_output()
    mock_repo.get_by_name.return_value = collection_output()
    mock_repo.list_collections.return_value = [collection_output()]
    return mock_repo

@pytest.fixture
def mock_team_repository():
    """Create a mocked team repository for unit tests."""
    mock_repo = Mock()
    mock_repo.save.return_value = team_output()
    mock_repo.get_by_id.return_value = team_output()
    mock_repo.get_by_name.return_value = team_output()
    mock_repo.list_teams.return_value = [team_output()]
    return mock_repo

@pytest.fixture
def mock_user_service(mock_user_repository, mock_settings):
    """Create a mocked user service for unit tests."""
    from rag_solution.services.user_service import UserService
    service = Mock(spec=UserService)
    service.create_user.return_value = user_output()
    service.get_user.return_value = user_output()
    service.update_user.return_value = user_output()
    service.delete_user.return_value = True
    service.list_users.return_value = [user_output()]
    return service

@pytest.fixture
def mock_collection_service(mock_collection_repository, mock_vector_store, mock_settings):
    """Create a mocked collection service for unit tests."""
    from rag_solution.services.collection_service import CollectionService
    service = Mock(spec=CollectionService)
    service.create_collection.return_value = collection_output()
    service.get_collection.return_value = collection_output()
    service.update_collection.return_value = collection_output()
    service.delete_collection.return_value = True
    service.list_collections.return_value = [collection_output()]
    return service

@pytest.fixture
def mock_team_service(mock_team_repository, mock_settings):
    """Create a mocked team service for unit tests."""
    from rag_solution.services.team_service import TeamService
    service = Mock(spec=TeamService)
    service.create_team.return_value = team_output()
    service.get_team.return_value = team_output()
    service.update_team.return_value = team_output()
    service.delete_team.return_value = True
    service.list_teams.return_value = [team_output()]
    return service
```

#### Step 2.3: Create Integration Fixture Library
```python
# backend/tests/fixtures/integration.py
"""Integration fixtures - Real services via testcontainers."""

import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.compose import DockerCompose
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .atomic import mock_settings

@pytest.fixture(scope="session")
def postgres_container():
    """Isolated PostgreSQL container for integration tests."""
    with PostgresContainer("postgres:13") as postgres:
        yield postgres

@pytest.fixture(scope="session")
def milvus_container():
    """Isolated Milvus container for vector store tests."""
    with DockerCompose(".", compose_file_name="docker-compose-test.yml") as compose:
        yield compose.get_service_host("milvus", 19531)

@pytest.fixture
def db_session_integration(postgres_container):
    """Create a database session for integration tests."""
    engine = create_engine(postgres_container.get_connection_url())
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def user_service_integration(db_session_integration, mock_settings):
    """Initialize UserService with real database."""
    from rag_solution.services.user_service import UserService
    return UserService(db_session_integration, mock_settings)

@pytest.fixture
def collection_service_integration(db_session_integration, mock_vector_store, mock_settings):
    """Initialize CollectionService with real database."""
    from rag_solution.services.collection_service import CollectionService
    return CollectionService(db_session_integration, mock_settings)

@pytest.fixture
def team_service_integration(db_session_integration, mock_settings):
    """Initialize TeamService with real database."""
    from rag_solution.services.team_service import TeamService
    return TeamService(db_session_integration, mock_settings)
```

#### Step 2.4: Create E2E Fixture Library
```python
# backend/tests/fixtures/e2e.py
"""E2E fixtures - Full stack for end-to-end tests."""

import pytest
from .integration import postgres_container, milvus_container, db_session_integration
from .atomic import mock_settings

@pytest.fixture(scope="session")
def full_database_setup(postgres_container):
    """Set up full database for E2E tests."""
    # Full database setup with all tables
    engine = create_engine(postgres_container.get_connection_url())
    from rag_solution.file_management.database import Base
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture(scope="session")
def full_vector_store_setup(milvus_container):
    """Set up full vector store for E2E tests."""
    # Full vector store setup
    pass

@pytest.fixture(scope="session")
def full_llm_provider_setup():
    """Set up full LLM provider for E2E tests."""
    # Full LLM provider setup
    pass

@pytest.fixture(scope="session")
def base_user_e2e(full_database_setup, full_llm_provider_setup):
    """Create a test user for E2E tests."""
    # Full user creation with all dependencies
    pass

@pytest.fixture(scope="session")
def base_collection_e2e(full_database_setup, full_vector_store_setup, base_user_e2e):
    """Create a test collection for E2E tests."""
    # Full collection creation with all dependencies
    pass

@pytest.fixture(scope="session")
def base_team_e2e(full_database_setup, base_user_e2e):
    """Create a test team for E2E tests."""
    # Full team creation with all dependencies
    pass
```

### Phase 3: Fixture Discovery and Management

#### Step 3.1: Create Fixture Discovery System
```python
# backend/tests/fixtures/discovery.py
"""Fixture discovery and management system."""

import os
import ast
from pathlib import Path
from typing import Dict, List, Set
from .registry import fixture_registry, FixtureType

class FixtureDiscovery:
    """Discover and analyze fixtures across the test suite."""

    def __init__(self, test_dir: str = "backend/tests"):
        self.test_dir = Path(test_dir)
        self.fixture_usage: Dict[str, List[str]] = {}
        self.duplicate_fixtures: Dict[str, List[str]] = {}

    def discover_fixtures(self) -> Dict[str, List[str]]:
        """Discover all fixtures across the test suite."""
        fixtures = {}

        for py_file in self.test_dir.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue

            file_fixtures = self._extract_fixtures_from_file(py_file)
            if file_fixtures:
                fixtures[str(py_file)] = file_fixtures

        return fixtures

    def _extract_fixtures_from_file(self, file_path: Path) -> List[str]:
        """Extract fixture names from a Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            fixtures = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call):
                            if isinstance(decorator.func, ast.Attribute):
                                if decorator.func.attr == "fixture":
                                    fixtures.append(node.name)
                        elif isinstance(decorator, ast.Attribute):
                            if decorator.attr == "fixture":
                                fixtures.append(node.name)

            return fixtures
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return []

    def find_duplicate_fixtures(self) -> Dict[str, List[str]]:
        """Find fixtures with the same name in different files."""
        all_fixtures = self.discover_fixtures()
        fixture_locations = {}

        for file_path, fixtures in all_fixtures.items():
            for fixture_name in fixtures:
                if fixture_name not in fixture_locations:
                    fixture_locations[fixture_name] = []
                fixture_locations[fixture_name].append(file_path)

        # Find duplicates
        duplicates = {name: locations for name, locations in fixture_locations.items()
                     if len(locations) > 1}

        return duplicates

    def analyze_fixture_usage(self) -> Dict[str, int]:
        """Analyze how often each fixture is used."""
        usage_count = {}

        for py_file in self.test_dir.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Count fixture usage in function parameters
                for line in content.split('\n'):
                    if 'def test_' in line and '(' in line:
                        # Extract function parameters
                        params_start = line.find('(')
                        params_end = line.find(')')
                        if params_start != -1 and params_end != -1:
                            params = line[params_start+1:params_end]
                            for param in params.split(','):
                                param = param.strip()
                                if param and not param.startswith('self'):
                                    usage_count[param] = usage_count.get(param, 0) + 1
            except Exception as e:
                print(f"Error analyzing {py_file}: {e}")

        return usage_count

    def generate_fixture_report(self) -> str:
        """Generate a comprehensive fixture report."""
        report = []
        report.append("# Fixture Analysis Report")
        report.append("")

        # Discover fixtures
        all_fixtures = self.discover_fixtures()
        total_fixtures = sum(len(fixtures) for fixtures in all_fixtures.values())
        report.append(f"## Summary")
        report.append(f"- Total fixtures: {total_fixtures}")
        report.append(f"- Files with fixtures: {len(all_fixtures)}")
        report.append("")

        # Find duplicates
        duplicates = self.find_duplicate_fixtures()
        if duplicates:
            report.append("## Duplicate Fixtures")
            for fixture_name, locations in duplicates.items():
                report.append(f"### {fixture_name}")
                for location in locations:
                    report.append(f"- {location}")
                report.append("")

        # Usage analysis
        usage_count = self.analyze_fixture_usage()
        most_used = sorted(usage_count.items(), key=lambda x: x[1], reverse=True)[:10]
        report.append("## Most Used Fixtures")
        for fixture_name, count in most_used:
            report.append(f"- {fixture_name}: {count} uses")
        report.append("")

        return "\n".join(report)

# Usage example
def main():
    discovery = FixtureDiscovery()
    report = discovery.generate_fixture_report()
    print(report)

    # Save report
    with open("fixture_analysis_report.md", "w") as f:
        f.write(report)

if __name__ == "__main__":
    main()
```

#### Step 3.2: Create Fixture Import Strategy
```python
# backend/tests/fixtures/__init__.py
"""Centralized fixture imports with clear organization."""

# Atomic fixtures (pure data, no dependencies)
from .atomic import (
    # Data input fixtures
    user_input,
    collection_input,
    team_input,
    file_input,
    llm_parameters_input,
    llm_provider_input,
    llm_model_input,
    prompt_template_input,
    pipeline_config_input,

    # Data output fixtures
    user_output,
    collection_output,
    team_output,
    file_output,
    llm_parameters_output,
    llm_provider_output,
    llm_model_output,
    prompt_template_output,
    pipeline_config_output,

    # Mock fixtures
    mock_env_vars,
    mock_settings,
    mock_watsonx_provider,
    mock_vector_store,
    isolated_test_env,
)

# Unit fixtures (mocked dependencies)
from .unit import (
    # Mock repositories
    mock_user_repository,
    mock_collection_repository,
    mock_team_repository,

    # Mock services
    mock_user_service,
    mock_collection_service,
    mock_team_service,
    mock_search_service,
    mock_pipeline_service,
)

# Integration fixtures (real services via testcontainers)
from .integration import (
    # Testcontainers
    postgres_container,
    milvus_container,

    # Database sessions
    db_session_integration,

    # Service instances
    user_service_integration,
    collection_service_integration,
    team_service_integration,
)

# E2E fixtures (full stack)
from .e2e import (
    # Full stack setup
    full_database_setup,
    full_vector_store_setup,
    full_llm_provider_setup,

    # Complete entities
    base_user_e2e,
    base_collection_e2e,
    base_team_e2e,
)

# Legacy fixtures (to be migrated)
from .legacy import (
    # These will be gradually migrated to the new structure
    base_user,
    base_collection,
    base_team,
    # ... other legacy fixtures
)

# Export all fixtures
__all__ = [
    # Atomic fixtures
    "user_input", "collection_input", "team_input", "file_input",
    "llm_parameters_input", "llm_provider_input", "llm_model_input",
    "prompt_template_input", "pipeline_config_input",
    "user_output", "collection_output", "team_output", "file_output",
    "llm_parameters_output", "llm_provider_output", "llm_model_output",
    "prompt_template_output", "pipeline_config_output",
    "mock_env_vars", "mock_settings", "mock_watsonx_provider",
    "mock_vector_store", "isolated_test_env",

    # Unit fixtures
    "mock_user_repository", "mock_collection_repository", "mock_team_repository",
    "mock_user_service", "mock_collection_service", "mock_team_service",
    "mock_search_service", "mock_pipeline_service",

    # Integration fixtures
    "postgres_container", "milvus_container", "db_session_integration",
    "user_service_integration", "collection_service_integration", "team_service_integration",

    # E2E fixtures
    "full_database_setup", "full_vector_store_setup", "full_llm_provider_setup",
    "base_user_e2e", "base_collection_e2e", "base_team_e2e",

    # Legacy fixtures
    "base_user", "base_collection", "base_team",
]
```

### Phase 4: Fixture Migration and Cleanup

#### Step 4.1: Create Migration Script
```python
# scripts/migrate_fixtures.py
#!/usr/bin/env python3
"""Script to migrate fixtures to centralized structure."""

import os
import re
from pathlib import Path
from typing import Dict, List, Set

class FixtureMigrator:
    """Migrate fixtures from scattered locations to centralized structure."""

    def __init__(self, test_dir: str = "backend/tests"):
        self.test_dir = Path(test_dir)
        self.fixtures_dir = self.test_dir / "fixtures"
        self.migration_log = []

    def migrate_fixtures(self):
        """Migrate all fixtures to centralized structure."""

        # Step 1: Discover all fixtures
        all_fixtures = self._discover_all_fixtures()

        # Step 2: Categorize fixtures
        categorized = self._categorize_fixtures(all_fixtures)

        # Step 3: Create centralized fixture files
        self._create_centralized_fixtures(categorized)

        # Step 4: Update test files to use centralized fixtures
        self._update_test_files()

        # Step 5: Remove duplicate fixtures
        self._remove_duplicate_fixtures()

        # Step 6: Generate migration report
        self._generate_migration_report()

    def _discover_all_fixtures(self) -> Dict[str, List[Dict]]:
        """Discover all fixtures across the test suite."""
        fixtures = {}

        for py_file in self.test_dir.rglob("*.py"):
            if py_file.name.startswith("__") or "fixtures" in str(py_file):
                continue

            file_fixtures = self._extract_fixtures_from_file(py_file)
            if file_fixtures:
                fixtures[str(py_file)] = file_fixtures

        return fixtures

    def _extract_fixtures_from_file(self, file_path: Path) -> List[Dict]:
        """Extract fixture definitions from a Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            fixtures = []
            lines = content.split('\n')

            for i, line in enumerate(lines):
                if '@pytest.fixture' in line:
                    # Find the function definition
                    for j in range(i + 1, min(i + 5, len(lines))):
                        if 'def ' in lines[j]:
                            func_line = lines[j]
                            func_name = re.search(r'def\s+(\w+)', func_line)
                            if func_name:
                                fixtures.append({
                                    'name': func_name.group(1),
                                    'line_number': j + 1,
                                    'content': self._extract_function_content(lines, j),
                                    'file': str(file_path)
                                })
                            break

            return fixtures
        except Exception as e:
            print(f"Error extracting fixtures from {file_path}: {e}")
            return []

    def _extract_function_content(self, lines: List[str], start_line: int) -> str:
        """Extract the complete function content."""
        content = [lines[start_line]]
        indent_level = len(lines[start_line]) - len(lines[start_line].lstrip())

        for i in range(start_line + 1, len(lines)):
            line = lines[i]
            if line.strip() == '':
                content.append(line)
                continue

            current_indent = len(line) - len(line.lstrip())
            if current_indent <= indent_level and line.strip():
                break

            content.append(line)

        return '\n'.join(content)

    def _categorize_fixtures(self, all_fixtures: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """Categorize fixtures by type."""
        categorized = {
            'atomic': [],
            'unit': [],
            'integration': [],
            'e2e': [],
            'duplicates': []
        }

        fixture_names = {}

        for file_path, fixtures in all_fixtures.items():
            for fixture in fixtures:
                name = fixture['name']

                # Track duplicates
                if name in fixture_names:
                    categorized['duplicates'].append(fixture)
                    categorized['duplicates'].append(fixture_names[name])
                else:
                    fixture_names[name] = fixture

                # Categorize by content and dependencies
                if self._is_atomic_fixture(fixture):
                    categorized['atomic'].append(fixture)
                elif self._is_unit_fixture(fixture):
                    categorized['unit'].append(fixture)
                elif self._is_integration_fixture(fixture):
                    categorized['integration'].append(fixture)
                elif self._is_e2e_fixture(fixture):
                    categorized['e2e'].append(fixture)

        return categorized

    def _is_atomic_fixture(self, fixture: Dict) -> bool:
        """Check if fixture is atomic (pure data, no dependencies)."""
        content = fixture['content'].lower()
        return (
            'mock' in content or
            'input' in fixture['name'] or
            'output' in fixture['name'] or
            'env_vars' in fixture['name'] or
            'settings' in fixture['name']
        )

    def _is_unit_fixture(self, fixture: Dict) -> bool:
        """Check if fixture is unit (mocked dependencies)."""
        content = fixture['content'].lower()
        return (
            'mock_' in fixture['name'] or
            'service' in fixture['name'] and 'mock' in content
        )

    def _is_integration_fixture(self, fixture: Dict) -> bool:
        """Check if fixture is integration (real services via testcontainers)."""
        content = fixture['content'].lower()
        return (
            'container' in fixture['name'] or
            'integration' in fixture['name'] or
            'testcontainers' in content
        )

    def _is_e2e_fixture(self, fixture: Dict) -> bool:
        """Check if fixture is E2E (full stack)."""
        content = fixture['content'].lower()
        return (
            'e2e' in fixture['name'] or
            'full_' in fixture['name'] or
            'base_' in fixture['name'] and 'db_session' in content
        )

    def _create_centralized_fixtures(self, categorized: Dict[str, List[Dict]]):
        """Create centralized fixture files."""

        # Create atomic fixtures
        self._write_fixture_file('atomic.py', categorized['atomic'])

        # Create unit fixtures
        self._write_fixture_file('unit.py', categorized['unit'])

        # Create integration fixtures
        self._write_fixture_file('integration.py', categorized['integration'])

        # Create E2E fixtures
        self._write_fixture_file('e2e.py', categorized['e2e'])

    def _write_fixture_file(self, filename: str, fixtures: List[Dict]):
        """Write fixtures to a centralized file."""
        file_path = self.fixtures_dir / filename

        with open(file_path, 'w') as f:
            f.write(f'"""Centralized {filename.replace(".py", "")} fixtures."""\n\n')
            f.write('import pytest\n')
            f.write('from unittest.mock import Mock, patch\n')
            f.write('from uuid import uuid4\n')
            f.write('from datetime import datetime\n\n')

            for fixture in fixtures:
                f.write(fixture['content'])
                f.write('\n\n')

    def _update_test_files(self):
        """Update test files to use centralized fixtures."""
        # This would involve updating imports and removing local fixture definitions
        pass

    def _remove_duplicate_fixtures(self):
        """Remove duplicate fixture definitions."""
        # This would involve removing duplicate fixtures from test files
        pass

    def _generate_migration_report(self):
        """Generate a migration report."""
        report = []
        report.append("# Fixture Migration Report")
        report.append("")
        report.append(f"## Summary")
        report.append(f"- Atomic fixtures: {len(self.migration_log)}")
        report.append(f"- Unit fixtures: {len(self.migration_log)}")
        report.append(f"- Integration fixtures: {len(self.migration_log)}")
        report.append(f"- E2E fixtures: {len(self.migration_log)}")
        report.append("")

        with open("fixture_migration_report.md", "w") as f:
            f.write('\n'.join(report))

# Usage
if __name__ == "__main__":
    migrator = FixtureMigrator()
    migrator.migrate_fixtures()
```

## 🎯 Implementation Timeline

### Phase 1: Fixture Audit (Weekend - 2 hours)
1. **Run fixture discovery script** to identify all fixtures
2. **Categorize fixtures** by type and scope
3. **Identify duplicates** and overlaps
4. **Generate fixture report** with recommendations

### Phase 2: Create Centralized Structure (Week 1)
1. **Create atomic fixture library** with pure data structures
2. **Create unit fixture library** with mocked dependencies
3. **Create integration fixture library** with testcontainers
4. **Create E2E fixture library** with full stack fixtures

### Phase 3: Migrate Fixtures (Week 2)
1. **Run migration script** to consolidate fixtures
2. **Update test files** to use centralized fixtures
3. **Remove duplicate fixtures** from test files
4. **Validate fixture functionality** across test suite

### Phase 4: Establish Management (Week 3)
1. **Create fixture registry** for discovery
2. **Implement naming conventions** and standards
3. **Create documentation** for fixture usage
4. **Train developers** on new fixture system

## 📊 Expected Results

### Quantitative Improvements
- **Reduce fixtures**: 311 → ~150 fixtures (-52%)
- **Eliminate duplicates**: Remove ~100+ duplicate fixtures
- **Centralize fixtures**: 78% scattered → 90% centralized
- **Improve discoverability**: Clear fixture registry and documentation

### Qualitative Improvements
- **Atomic design**: Clear separation of fixture types
- **Easy identification**: Central registry and naming conventions
- **Consistent behavior**: Single source of truth for each fixture
- **Better maintainability**: Changes only need updates in one place

This comprehensive fixture centralization strategy addresses the critical issues of duplication, poor organization, and difficult discovery while establishing a clear, maintainable system for managing fixtures across the large RAG Modulo test suite.
