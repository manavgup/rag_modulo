# 🗺️ Implementation Roadmap

## Overview

This document provides a detailed, step-by-step implementation roadmap for the test infrastructure refactoring, addressing both [Issue #187](https://github.com/manavgup/rag_modulo/issues/187) and [Issue #176](https://github.com/manavgup/rag_modulo/issues/176).

## 🎯 Success Criteria

### Performance Targets
- **Atomic tests**: < 30 seconds total
- **Unit tests**: < 2 minutes total
- **Integration tests**: < 5 minutes total
- **E2E tests**: < 3 minutes total
- **Full CI pipeline**: < 15 minutes (vs current 45-90 minutes)

### Quantitative Goals
- **Test files**: 114 → ~60 files (-47%)
- **Test functions**: 1,054 → ~600-700 functions (-33-40%)
- **Fixtures**: 68 → ~40 fixtures (-41%)
- **Duplicate test cases**: Remove ~200-300 duplicates

## 📅 Implementation Timeline

### Week 0: Immediate Relief (This Weekend - 3 hours)

#### Day 1: Configuration Setup (2 hours)

**Step 1.1: Create Atomic Test Configuration (30 minutes)**
```bash
# Create pytest-atomic.ini
cat > backend/pytest-atomic.ini << 'EOF'
[pytest]
testpaths = ["backend/tests"]
markers =
    atomic: Ultra-fast tests with no external dependencies
    unit: Fast unit tests with minimal setup
    integration: Database/service integration tests
    e2e: End-to-end workflow tests

# ATOMIC TESTS: No coverage, no reports, no database
addopts =
    --verbose
    --tb=short
    --disable-warnings
    -x
    --show-capture=no
    # NO --cov flags!
    # NO --html reports!
    # NO database overhead!

filterwarnings =
    ignore::DeprecationWarning
    ignore::UserWarning
EOF
```

**Step 1.2: Add Lightning-Fast Makefile Targets (30 minutes)**
```bash
# Add to Makefile
cat >> Makefile << 'EOF'

# LIGHTNING FAST: Atomic tests with no overhead (< 30 seconds)
test-atomic: venv
	@echo "⚡ Running atomic tests (no coverage, no database, no reports)..."
	cd backend && poetry run pytest -c pytest-atomic.ini tests/ -m atomic -v

# FAST: Unit tests with minimal setup (< 2 minutes)
test-unit-fast: venv
	@echo "🧪 Running unit tests (no coverage overhead)..."
	cd backend && poetry run pytest -c pytest-atomic.ini tests/ -m unit -v --no-cov

# DEVELOPMENT: Perfect for daily coding (< 1 minute)
test-dev: test-atomic
	@echo "✅ Development testing complete"

# PRE-COMMIT: Fast validation (< 3 minutes)
test-pre-commit: test-atomic test-unit-fast
	@echo "✅ Pre-commit validation complete"
EOF
```

**Step 1.3: Create First Atomic Tests (1 hour)**
```bash
# Create atomic test directory
mkdir -p backend/tests/atomic

# Create atomic conftest.py
cat > backend/tests/atomic/conftest.py << 'EOF'
"""Atomic test fixtures - Pure mocks, no external dependencies."""

import pytest
from unittest.mock import Mock, patch
import os

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
EOF

# Create first atomic test
cat > backend/tests/atomic/test_user_validation.py << 'EOF'
"""Atomic tests for user validation logic."""

import pytest
from rag_solution.schemas.user_schema import UserInput

@pytest.mark.atomic
def test_validate_user_email():
    """Test user email validation logic."""
    from rag_solution.services.user_service import validate_user_email

    # Valid emails
    assert validate_user_email("test@example.com") == True
    assert validate_user_email("user.name@domain.co.uk") == True
    assert validate_user_email("user+tag@example.org") == True

    # Invalid emails
    assert validate_user_email("invalid-email") == False
    assert validate_user_email("@example.com") == False
    assert validate_user_email("user@") == False
    assert validate_user_email("") == False

@pytest.mark.atomic
def test_validate_user_role():
    """Test user role validation logic."""
    from rag_solution.services.user_service import validate_user_role

    # Valid roles
    assert validate_user_role("user") == True
    assert validate_user_role("admin") == True
    assert validate_user_role("moderator") == True

    # Invalid roles
    assert validate_user_role("invalid") == False
    assert validate_user_role("") == False
    assert validate_user_role(None) == False

@pytest.mark.atomic
def test_user_input_validation():
    """Test user input validation."""
    # Valid user input
    valid_user = UserInput(
        email="test@example.com",
        ibm_id="test_user_123",
        name="Test User",
        role="user"
    )
    assert valid_user.email == "test@example.com"
    assert valid_user.role == "user"

    # Test validation errors
    with pytest.raises(ValueError):
        UserInput(
            email="invalid-email",
            ibm_id="test_user_123",
            name="Test User",
            role="user"
        )
EOF
```

**Validation Steps**:
```bash
# Test the new atomic configuration
make test-atomic

# Should complete in < 30 seconds
# Should show 3 atomic tests passing
```

#### Day 2: Test Existing Atomic Fixtures (1 hour)

**Step 2.1: Convert Existing Atomic Fixtures**
```bash
# Create atomic fixtures file
cat > backend/tests/fixtures/atomic.py << 'EOF'
"""Atomic fixtures - Pure data structures, no external dependencies."""

import pytest
from unittest.mock import Mock, patch
import os
from uuid import uuid4
from datetime import datetime

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

@pytest.fixture
def isolated_test_env():
    """Provide a completely isolated test environment with no real env vars."""
    with patch.dict(os.environ, {}, clear=True):
        yield
EOF
```

**Validation Steps**:
```bash
# Test atomic fixtures
make test-atomic

# Should complete in < 30 seconds
# Should show all atomic tests passing
```

### Week 1: Directory Restructuring & Integration Layer

#### Day 1-2: Create New Directory Structure

**Step 1.1: Create New Test Directories**
```bash
# Create new directory structure
mkdir -p backend/tests/{atomic,unit,integration,e2e}
mkdir -p backend/tests/unit/{services,models,utils}
mkdir -p backend/tests/integration/{database,vector_store,llm_provider}
mkdir -p backend/tests/e2e/{workflows,api}

# Create conftest.py files for each layer
touch backend/tests/atomic/conftest.py
touch backend/tests/unit/conftest.py
touch backend/tests/integration/conftest.py
touch backend/tests/e2e/conftest.py
```

**Step 1.2: Create Integration Fixtures**
```bash
# Create integration fixtures
cat > backend/tests/fixtures/integration.py << 'EOF'
"""Integration fixtures - Real services via testcontainers."""

import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.compose import DockerCompose

@pytest.fixture(scope="session")
def postgres_container():
    """Isolated PostgreSQL container for integration tests."""
    with PostgresContainer("postgres:13") as postgres:
        yield postgres

@pytest.fixture(scope="session")
def milvus_container():
    """Isolated Milvus container for vector store tests."""
    with DockerCompose(".", compose_file_name="docker-compose-test.yml") as compose:
        yield compose.get_service_host("milvus", 19530)

@pytest.fixture
def db_session_integration(postgres_container):
    """Create a database session for integration tests."""
    # Real database operations via testcontainers
    pass

@pytest.fixture
def user_service_integration(db_session_integration, mock_settings):
    """Initialize UserService with real database."""
    from rag_solution.services.user_service import UserService
    return UserService(db_session_integration, mock_settings)
EOF
```

**Step 1.3: Create E2E Fixtures**
```bash
# Create E2E fixtures
cat > backend/tests/fixtures/e2e.py << 'EOF'
"""E2E fixtures - Full stack for end-to-end tests."""

import pytest

@pytest.fixture(scope="session")
def full_database_setup():
    """Set up full database for E2E tests."""
    # Full database setup with all tables
    pass

@pytest.fixture(scope="session")
def full_vector_store_setup():
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
EOF
```

#### Day 3-4: Migrate First Service Tests

**Step 3.1: Migrate User Service Tests**
```bash
# Create consolidated user service test
cat > backend/tests/unit/services/test_user_service.py << 'EOF'
"""Unit tests for user service with mocked dependencies."""

import pytest
from unittest.mock import Mock, patch
from rag_solution.services.user_service import UserService
from rag_solution.schemas.user_schema import UserInput, UserOutput

@pytest.mark.unit
def test_create_user_success(mock_user_repository, mock_settings):
    """Test successful user creation."""
    # Arrange
    service = UserService(mock_user_repository, mock_settings)
    user_input = UserInput(
        email="test@example.com",
        ibm_id="test_user_123",
        name="Test User",
        role="user"
    )
    expected_user = UserOutput(
        id="user_123",
        email="test@example.com",
        ibm_id="test_user_123",
        name="Test User",
        role="user"
    )
    mock_user_repository.save.return_value = expected_user

    # Act
    result = service.create_user(user_input)

    # Assert
    assert result.email == "test@example.com"
    assert result.role == "user"
    mock_user_repository.save.assert_called_once()

@pytest.mark.unit
def test_create_user_validation_error(mock_user_repository, mock_settings):
    """Test user creation with validation error."""
    # Arrange
    service = UserService(mock_user_repository, mock_settings)
    invalid_user_input = UserInput(
        email="invalid-email",
        ibm_id="test_user_123",
        name="Test User",
        role="user"
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid email format"):
        service.create_user(invalid_user_input)

@pytest.mark.unit
def test_get_user_success(mock_user_repository, mock_settings):
    """Test successful user retrieval."""
    # Arrange
    service = UserService(mock_user_repository, mock_settings)
    user_id = "user_123"
    expected_user = UserOutput(
        id=user_id,
        email="test@example.com",
        ibm_id="test_user_123",
        name="Test User",
        role="user"
    )
    mock_user_repository.get_by_id.return_value = expected_user

    # Act
    result = service.get_user(user_id)

    # Assert
    assert result.id == user_id
    assert result.email == "test@example.com"
    mock_user_repository.get_by_id.assert_called_once_with(user_id)

@pytest.mark.unit
def test_get_user_not_found(mock_user_repository, mock_settings):
    """Test user retrieval when user not found."""
    # Arrange
    service = UserService(mock_user_repository, mock_settings)
    user_id = "nonexistent_user"
    mock_user_repository.get_by_id.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="User not found"):
        service.get_user(user_id)
EOF
```

**Step 3.2: Create Integration Tests**
```bash
# Create integration test for user database operations
cat > backend/tests/integration/database/test_user_database.py << 'EOF'
"""Integration tests for user database operations."""

import pytest
from rag_solution.schemas.user_schema import UserInput

@pytest.mark.integration
def test_user_database_operations(postgres_container):
    """Test user database operations with real database."""
    # Real database operations via testcontainers
    pass

@pytest.mark.integration
def test_user_persistence(postgres_container):
    """Test user persistence in database."""
    # Test user creation, retrieval, update, deletion
    pass
EOF
```

**Step 3.3: Create E2E Tests**
```bash
# Create E2E test for user workflow
cat > backend/tests/e2e/workflows/test_user_workflow.py << 'EOF'
"""E2E tests for user workflow."""

import pytest

@pytest.mark.e2e
def test_user_registration_workflow():
    """Test complete user registration workflow."""
    # Full stack test with real services
    pass

@pytest.mark.e2e
def test_user_authentication_workflow():
    """Test complete user authentication workflow."""
    # Full stack test with real services
    pass
EOF
```

### Week 2: Testcontainers Integration & Large File Refactoring

#### Day 1-2: Implement Testcontainers

**Step 1.1: Install Testcontainers Dependencies**
```bash
# Add testcontainers to backend dependencies
cd backend
poetry add testcontainers[postgres] testcontainers[compose]
```

**Step 1.2: Create Testcontainers Configuration**
```bash
# Create docker-compose-test.yml for testcontainers
cat > docker-compose-test.yml << 'EOF'
version: '3.8'

services:
  postgres-test:
    image: postgres:13
    environment:
      POSTGRES_DB: test_db
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_password
    ports:
      - "5433:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U test_user -d test_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  milvus-test:
    image: milvusdb/milvus:latest
    ports:
      - "19531:19530"
    environment:
      ETCD_ENDPOINTS: etcd:2379
    depends_on:
      - etcd

  etcd:
    image: quay.io/coreos/etcd:latest
    ports:
      - "2379:2379"
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
      - ETCD_QUOTA_BACKEND_BYTES=4294967296
      - ETCD_SNAPSHOT_COUNT=50000
EOF
```

**Step 1.3: Update Integration Fixtures**
```bash
# Update integration fixtures with testcontainers
cat > backend/tests/fixtures/integration.py << 'EOF'
"""Integration fixtures - Real services via testcontainers."""

import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.compose import DockerCompose
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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
EOF
```

#### Day 3-4: Refactor Large Test File

**Step 3.1: Split `test_search_debug_edge_cases.py`**
```bash
# Create atomic search validation tests
cat > backend/tests/atomic/test_search_validation.py << 'EOF'
"""Atomic tests for search validation logic."""

import pytest

@pytest.mark.atomic
def test_validate_search_query():
    """Test search query validation."""
    from rag_solution.services.search_service import validate_search_query

    # Valid queries
    assert validate_search_query("What is the main topic?") == True
    assert validate_search_query("How does this work?") == True

    # Invalid queries
    assert validate_search_query("") == False
    assert validate_search_query("   ") == False
    assert validate_search_query(None) == False

@pytest.mark.atomic
def test_validate_search_parameters():
    """Test search parameters validation."""
    from rag_solution.services.search_service import validate_search_parameters

    # Valid parameters
    valid_params = {
        "query": "test query",
        "collection_id": "col_123",
        "user_id": "user_123",
        "limit": 10
    }
    assert validate_search_parameters(valid_params) == True

    # Invalid parameters
    invalid_params = {
        "query": "",
        "collection_id": None,
        "user_id": "user_123"
    }
    assert validate_search_parameters(invalid_params) == False
EOF
```

**Step 3.2: Create Unit Search Service Tests**
```bash
# Create unit search service tests
cat > backend/tests/unit/services/test_search_service.py << 'EOF'
"""Unit tests for search service with mocked dependencies."""

import pytest
from unittest.mock import Mock, patch
from rag_solution.services.search_service import SearchService

@pytest.mark.unit
def test_search_service_initialization(mock_vector_store, mock_llm_provider, mock_settings):
    """Test search service initialization."""
    service = SearchService(mock_vector_store, mock_llm_provider, mock_settings)
    assert service.vector_store == mock_vector_store
    assert service.llm_provider == mock_llm_provider

@pytest.mark.unit
def test_search_with_valid_query(mock_vector_store, mock_llm_provider, mock_settings):
    """Test search with valid query."""
    # Arrange
    service = SearchService(mock_vector_store, mock_llm_provider, mock_settings)
    query = "What is the main topic?"
    mock_vector_store.search.return_value = [
        {"content": "Test content", "score": 0.95}
    ]
    mock_llm_provider.generate_answer.return_value = "Test answer"

    # Act
    result = service.search(query, collection_id="col_123", user_id="user_123")

    # Assert
    assert result["answer"] == "Test answer"
    assert len(result["documents"]) == 1
    mock_vector_store.search.assert_called_once()
    mock_llm_provider.generate_answer.assert_called_once()

@pytest.mark.unit
def test_search_with_empty_results(mock_vector_store, mock_llm_provider, mock_settings):
    """Test search with empty results."""
    # Arrange
    service = SearchService(mock_vector_store, mock_llm_provider, mock_settings)
    query = "What is the main topic?"
    mock_vector_store.search.return_value = []

    # Act
    result = service.search(query, collection_id="col_123", user_id="user_123")

    # Assert
    assert result["answer"] == "No relevant documents found."
    assert len(result["documents"]) == 0
EOF
```

**Step 3.3: Create Integration Search Tests**
```bash
# Create integration search tests
cat > backend/tests/integration/database/test_search_database.py << 'EOF'
"""Integration tests for search database operations."""

import pytest

@pytest.mark.integration
def test_search_database_operations(postgres_container, milvus_container):
    """Test search database operations with real services."""
    # Real database and vector store operations
    pass

@pytest.mark.integration
def test_vector_store_integration(milvus_container):
    """Test vector store integration."""
    # Real vector store operations
    pass
EOF
```

**Step 3.4: Create E2E Search Workflow Tests**
```bash
# Create E2E search workflow tests
cat > backend/tests/e2e/workflows/test_search_workflow.py << 'EOF'
"""E2E tests for search workflow."""

import pytest

@pytest.mark.e2e
def test_end_to_end_search_flow():
    """Test complete search workflow."""
    # Full stack search test
    pass

@pytest.mark.e2e
def test_search_performance():
    """Test search performance."""
    # Performance testing
    pass
EOF
```

### Week 3-4: Systematic Migration & Optimization

#### Day 1-2: Migrate Remaining Service Tests

**Step 1.1: Consolidate Team Service Tests**
```bash
# Create consolidated team service test
cat > backend/tests/unit/services/test_team_service.py << 'EOF'
"""Unit tests for team service with mocked dependencies."""

import pytest
from unittest.mock import Mock
from rag_solution.services.team_service import TeamService
from rag_solution.schemas.team_schema import TeamInput, TeamOutput

@pytest.mark.unit
def test_create_team_success(mock_team_repository, mock_settings):
    """Test successful team creation."""
    # Test implementation
    pass

@pytest.mark.unit
def test_get_team_success(mock_team_repository, mock_settings):
    """Test successful team retrieval."""
    # Test implementation
    pass

# ... other team service tests
EOF
```

**Step 1.2: Consolidate Collection Service Tests**
```bash
# Create consolidated collection service test
cat > backend/tests/unit/services/test_collection_service.py << 'EOF'
"""Unit tests for collection service with mocked dependencies."""

import pytest
from unittest.mock import Mock
from rag_solution.services.collection_service import CollectionService
from rag_solution.schemas.collection_schema import CollectionInput, CollectionOutput

@pytest.mark.unit
def test_create_collection_success(mock_collection_repository, mock_vector_store, mock_settings):
    """Test successful collection creation."""
    # Test implementation
    pass

@pytest.mark.unit
def test_get_collection_success(mock_collection_repository, mock_settings):
    """Test successful collection retrieval."""
    # Test implementation
    pass

# ... other collection service tests
EOF
```

#### Day 3-4: Update CI/CD Pipeline

**Step 3.1: Update GitHub Actions Workflow**
```bash
# Update .github/workflows/ci.yml
cat > .github/workflows/ci.yml << 'EOF'
name: Test Infrastructure

on: [push, pull_request]

env:
  PYTHON_VERSION: '3.12'
  POETRY_VERSION: '1.6.1'

jobs:
  atomic-tests:
    name: Atomic Tests
    runs-on: ubuntu-latest
    timeout-minutes: 2
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: ${{ env.POETRY_VERSION }}

      - name: Install dependencies
        run: |
          cd backend
          poetry install --with dev

      - name: Run atomic tests (30 seconds)
        run: make test-atomic

  unit-tests:
    name: Unit Tests
    needs: [atomic-tests]
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: ${{ env.POETRY_VERSION }}

      - name: Install dependencies
        run: |
          cd backend
          poetry install --with dev

      - name: Run unit tests (2 minutes)
        run: make test-unit-fast

  integration-tests:
    name: Integration Tests
    needs: [unit-tests]
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: ${{ env.POETRY_VERSION }}

      - name: Install dependencies
        run: |
          cd backend
          poetry install --with dev
          poetry add testcontainers[postgres] testcontainers[compose]

      - name: Run integration tests (5 minutes)
        run: make test-integration-coverage

  e2e-tests:
    name: E2E Tests
    needs: [integration-tests]
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          version: ${{ env.POETRY_VERSION }}

      - name: Install dependencies
        run: |
          cd backend
          poetry install --with dev

      - name: Run E2E tests (3 minutes)
        run: make test-e2e-coverage
EOF
```

### Week 5+: Ongoing Migration & Maintenance

#### Ongoing Tasks

**Daily Tasks**:
- [ ] Run `make test-dev` before committing
- [ ] Use `make test-pre-commit` for validation
- [ ] Monitor test performance metrics

**Weekly Tasks**:
- [ ] Migrate 2-3 test files to new structure
- [ ] Remove duplicate test cases
- [ ] Update fixture usage
- [ ] Monitor CI pipeline performance

**Monthly Tasks**:
- [ ] Review and optimize test performance
- [ ] Update documentation
- [ ] Gather developer feedback
- [ ] Plan next migration phase

## 🎯 Success Validation

### Performance Validation
```bash
# Test performance targets
make test-atomic    # Should complete in < 30 seconds
make test-unit-fast # Should complete in < 2 minutes
make test-integration-coverage # Should complete in < 5 minutes
make test-e2e-coverage # Should complete in < 3 minutes
```

### Quality Validation
```bash
# Run full test suite
make test-all

# Check test coverage
make coverage

# Run linting
make lint
```

### CI/CD Validation
```bash
# Test CI pipeline locally
act -j atomic-tests
act -j unit-tests
act -j integration-tests
act -j e2e-tests
```

## 📊 Progress Tracking

### Week 0 Progress
- [ ] Create atomic test configuration
- [ ] Add lightning-fast Makefile targets
- [ ] Create first atomic tests
- [ ] Validate atomic test performance

### Week 1 Progress
- [ ] Create new directory structure
- [ ] Implement testcontainers integration
- [ ] Migrate first service tests
- [ ] Create integration fixtures

### Week 2 Progress
- [ ] Refactor large test files
- [ ] Implement testcontainers configuration
- [ ] Create E2E test workflows
- [ ] Update CI/CD pipeline

### Week 3-4 Progress
- [ ] Migrate remaining service tests
- [ ] Consolidate duplicate tests
- [ ] Update all test imports
- [ ] Validate full test suite

### Week 5+ Progress
- [ ] Ongoing migration
- [ ] Performance optimization
- [ ] Documentation updates
- [ ] Developer feedback integration

## 🚨 Risk Mitigation

### Technical Risks
- **Breaking existing tests**: Run full test suite after each change
- **Fixture dependency issues**: Use incremental migration approach
- **Performance regressions**: Monitor test execution times

### Process Risks
- **Developer resistance**: Provide clear documentation and training
- **Timeline delays**: Use phased approach with clear milestones
- **Quality issues**: Implement comprehensive validation steps

### Mitigation Strategies
- **Backup strategy**: Keep original files until migration is complete
- **Rollback plan**: Maintain ability to revert changes
- **Communication**: Regular updates on progress and issues
- **Training**: Provide documentation and examples for new patterns

This comprehensive implementation roadmap provides a clear path to transform the test infrastructure from a 30-minute E2E-heavy approach to a 30-second layered testing strategy while addressing all the issues identified in both Issue #187 and Issue #176.
