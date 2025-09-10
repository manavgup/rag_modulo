# 🔧 Fixture Migration Mapping

## Overview

This document provides detailed file-level mapping for migrating fixtures from the current structure to the new layered testing architecture.

## Current Fixture Analysis

### `backend/tests/fixtures/services.py` (359 lines, 25 fixtures)

#### Fixtures to Keep in Atomic Layer
```python
@pytest.fixture
def llm_provider() -> str:
    """hard coded watsonx provider name for now."""
    return "watsonx"
```
**Action**: Move to `fixtures/atomic.py`
**Reason**: Pure string value, no dependencies

#### Fixtures to Move to Integration Layer
```python
@pytest.fixture
def user_service(db_session: Session, mock_settings) -> UserService:
    """Initialize UserService."""
    return UserService(db_session, mock_settings)

@pytest.fixture
def user_team_service(db_session: Session, mock_settings) -> UserTeamService:
    """Initialize UserTeamService."""
    return UserTeamService(db_session, mock_settings)

@pytest.fixture
def llm_provider_service(db_session: Session, mock_settings) -> LLMProviderService:
    """Initialize LLMProviderService."""
    return LLMProviderService(db_session, mock_settings)

@pytest.fixture
def llm_model_service(db_session: Session, mock_settings) -> LLMModelService:
    """Initialize LLMModelService."""
    return LLMModelService(db_session, mock_settings)

@pytest.fixture
def llm_parameters_service(db_session: Session, mock_settings) -> LLMParametersService:
    """Initialize LLMParametersService."""
    return LLMParametersService(db_session, mock_settings)

@pytest.fixture
def prompt_template_service(db_session: Session, mock_settings) -> PromptTemplateService:
    """Initialize PromptTemplateService."""
    return PromptTemplateService(db_session, mock_settings)

@pytest.fixture
def pipeline_service(db_session: Session, mock_settings) -> PipelineService:
    """Initialize PipelineService."""
    return PipelineService(db_session, mock_settings)
```
**Action**: Move to `fixtures/integration.py` with testcontainers
**Reason**: Require database session, should use real database in integration tests

#### Fixtures to Move to E2E Layer
```python
@pytest.fixture(scope="session")
def session_mock_settings() -> Settings:
    """Create a session-scoped mocked settings object."""
    # ... complex settings setup

@pytest.fixture(scope="session")
def collection_service(session_db: Session) -> CollectionService:
    """Initialize CollectionService with mocked vector store."""
    # ... complex service setup with mocks

@pytest.fixture(scope="session")
def mock_pipeline_service():
    """Mock PipelineService to avoid Milvus connection during user initialization."""
    # ... complex mock setup

@pytest.fixture(scope="session")
def base_user(db_engine: Engine, ensure_watsonx_provider: LLMProviderOutput, mock_pipeline_service) -> UserOutput:
    """Create a test user once for the entire test session."""
    # ... complex user creation with full stack

@pytest.fixture(scope="session", autouse=True)
def init_providers(...):
    """Initialize test providers and related configurations."""
    # ... complex provider initialization
```
**Action**: Move to `fixtures/e2e.py`
**Reason**: Session-scoped, complex setup, full stack dependencies

### `backend/tests/fixtures/db.py` (58 lines, 2 fixtures)

#### Fixtures to Move to Integration Layer
```python
@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine, None, None]:
    """Initialize the database engine for the test session."""
    # ... database engine setup

@pytest.fixture(scope="function")
def db_session(db_engine: Engine) -> Generator[Session, None, None]:
    """Provide a clean database session for each test."""
    # ... database session setup
```
**Action**: Move to `fixtures/integration.py` with testcontainers
**Reason**: Database operations should use real database in integration tests

### `backend/tests/fixtures/collections.py` (103 lines, 4 fixtures)

#### Current Fixtures
```python
@pytest.fixture
def collection_input():
    """Create a collection input for testing."""
    return CollectionInput(name="Test Collection", description="Test Description")

@pytest.fixture
def collection_output(collection_input):
    """Create a collection output for testing."""
    return CollectionOutput(
        id=uuid4(),
        name=collection_input.name,
        description=collection_input.description,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@pytest.fixture
def collection_with_user(base_user, collection_output):
    """Create a collection with user association."""
    return UserCollectionOutput(
        user_id=base_user.id,
        collection_id=collection_output.id,
        collection=collection_output
    )

@pytest.fixture
def collection_list(collection_output):
    """Create a list of collections for testing."""
    return [collection_output]
```

#### Migration Plan
- **Move to atomic.py**: `collection_input()` - Pure data structure
- **Move to integration.py**: `collection_output()`, `collection_with_user()` - Database operations
- **Move to e2e.py**: `collection_list()` - Full workflow data

### `backend/tests/fixtures/user.py` (1 fixture)

#### Current Fixture
```python
@pytest.fixture
def user_input():
    """Create a user input for testing."""
    return UserInput(
        email="test@example.com",
        ibm_id="test_user_123",
        name="Test User",
        role="user"
    )
```

#### Migration Plan
- **Move to atomic.py**: Pure data structure, no dependencies

### `backend/tests/fixtures/teams.py` (3 fixtures)

#### Current Fixtures
```python
@pytest.fixture
def team_input():
    """Create a team input for testing."""
    return TeamInput(name="Test Team", description="Test Description")

@pytest.fixture
def team_output(team_input):
    """Create a team output for testing."""
    return TeamOutput(
        id=uuid4(),
        name=team_input.name,
        description=team_input.description,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@pytest.fixture
def team_with_user(base_user, team_output):
    """Create a team with user association."""
    return UserTeamOutput(
        user_id=base_user.id,
        team_id=team_output.id,
        team=team_output
    )
```

#### Migration Plan
- **Move to atomic.py**: `team_input()` - Pure data structure
- **Move to integration.py**: `team_output()`, `team_with_user()` - Database operations

### `backend/tests/fixtures/files.py` (2 fixtures)

#### Current Fixtures
```python
@pytest.fixture
def file_input():
    """Create a file input for testing."""
    return FileInput(
        name="test.pdf",
        content=b"test content",
        content_type="application/pdf"
    )

@pytest.fixture
def file_output(file_input):
    """Create a file output for testing."""
    return FileOutput(
        id=uuid4(),
        name=file_input.name,
        content=file_input.content,
        content_type=file_input.content_type,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
```

#### Migration Plan
- **Move to atomic.py**: `file_input()` - Pure data structure
- **Move to integration.py**: `file_output()` - Database operations

### `backend/tests/fixtures/llm.py` (3 fixtures)

#### Current Fixtures
```python
@pytest.fixture
def llm_parameters_input():
    """Create LLM parameters input for testing."""
    return LLMParametersInput(
        temperature=0.7,
        max_tokens=100,
        top_k=5
    )

@pytest.fixture
def llm_parameters_output(llm_parameters_input):
    """Create LLM parameters output for testing."""
    return LLMParametersOutput(
        id=uuid4(),
        temperature=llm_parameters_input.temperature,
        max_tokens=llm_parameters_input.max_tokens,
        top_k=llm_parameters_input.top_k,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@pytest.fixture
def base_llm_parameters(llm_parameters_output):
    """Create base LLM parameters for testing."""
    return llm_parameters_output
```

#### Migration Plan
- **Move to atomic.py**: `llm_parameters_input()` - Pure data structure
- **Move to integration.py**: `llm_parameters_output()` - Database operations
- **Move to e2e.py**: `base_llm_parameters()` - Full stack setup

### `backend/tests/fixtures/llm_provider.py` (2 fixtures)

#### Current Fixtures
```python
@pytest.fixture
def llm_provider_input():
    """Create LLM provider input for testing."""
    return LLMProviderInput(
        name="test_provider",
        base_url="https://test.example.com",
        api_key=SecretStr("test_key"),
        project_id="test_project"
    )

@pytest.fixture
def llm_provider_output(llm_provider_input):
    """Create LLM provider output for testing."""
    return LLMProviderOutput(
        id=uuid4(),
        name=llm_provider_input.name,
        base_url=llm_provider_input.base_url,
        project_id=llm_provider_input.project_id,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
```

#### Migration Plan
- **Move to atomic.py**: `llm_provider_input()` - Pure data structure
- **Move to integration.py**: `llm_provider_output()` - Database operations

### `backend/tests/fixtures/llm_model.py` (2 fixtures)

#### Current Fixtures
```python
@pytest.fixture
def llm_model_input():
    """Create LLM model input for testing."""
    return LLMModelInput(
        provider_id=uuid4(),
        model_id="test_model",
        model_type=ModelType.GENERATION
    )

@pytest.fixture
def llm_model_output(llm_model_input):
    """Create LLM model output for testing."""
    return LLMModelOutput(
        id=uuid4(),
        provider_id=llm_model_input.provider_id,
        model_id=llm_model_input.model_id,
        model_type=llm_model_input.model_type,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
```

#### Migration Plan
- **Move to atomic.py**: `llm_model_input()` - Pure data structure
- **Move to integration.py**: `llm_model_output()` - Database operations

### `backend/tests/fixtures/llm_parameter.py` (5 fixtures)

#### Current Fixtures
```python
@pytest.fixture
def llm_parameters_input():
    """Create LLM parameters input for testing."""
    return LLMParametersInput(
        temperature=0.7,
        max_tokens=100,
        top_k=5
    )

@pytest.fixture
def llm_parameters_output(llm_parameters_input):
    """Create LLM parameters output for testing."""
    return LLMParametersOutput(
        id=uuid4(),
        temperature=llm_parameters_input.temperature,
        max_tokens=llm_parameters_input.max_tokens,
        top_k=llm_parameters_input.top_k,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@pytest.fixture
def base_llm_parameters(llm_parameters_output):
    """Create base LLM parameters for testing."""
    return llm_parameters_output

@pytest.fixture
def llm_parameters_list(base_llm_parameters):
    """Create a list of LLM parameters for testing."""
    return [base_llm_parameters]

@pytest.fixture
def llm_parameters_with_provider(base_llm_parameters, llm_provider_output):
    """Create LLM parameters with provider association."""
    return LLMParametersWithProvider(
        parameters=base_llm_parameters,
        provider=llm_provider_output
    )
```

#### Migration Plan
- **Move to atomic.py**: `llm_parameters_input()` - Pure data structure
- **Move to integration.py**: `llm_parameters_output()`, `llm_parameters_with_provider()` - Database operations
- **Move to e2e.py**: `base_llm_parameters()`, `llm_parameters_list()` - Full stack setup

### `backend/tests/fixtures/prompt_template.py` (7 fixtures)

#### Current Fixtures
```python
@pytest.fixture
def prompt_template_input():
    """Create prompt template input for testing."""
    return PromptTemplateInput(
        name="test_template",
        content="Test prompt: {input}",
        template_type="generation"
    )

@pytest.fixture
def prompt_template_output(prompt_template_input):
    """Create prompt template output for testing."""
    return PromptTemplateOutput(
        id=uuid4(),
        name=prompt_template_input.name,
        content=prompt_template_input.content,
        template_type=prompt_template_input.template_type,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@pytest.fixture
def base_prompt_template(prompt_template_output):
    """Create base prompt template for testing."""
    return prompt_template_output

@pytest.fixture
def rag_prompt_template():
    """Create RAG prompt template for testing."""
    return PromptTemplateOutput(
        id=uuid4(),
        name="rag_template",
        content="Answer based on context: {context}\nQuestion: {question}",
        template_type="rag"
    )

@pytest.fixture
def question_gen_template():
    """Create question generation template for testing."""
    return PromptTemplateOutput(
        id=uuid4(),
        name="question_gen_template",
        content="Generate questions for: {content}",
        template_type="question_generation"
    )

@pytest.fixture
def prompt_template_list(base_prompt_template, rag_prompt_template, question_gen_template):
    """Create a list of prompt templates for testing."""
    return [base_prompt_template, rag_prompt_template, question_gen_template]

@pytest.fixture
def prompt_template_with_parameters(base_prompt_template, llm_parameters_output):
    """Create prompt template with parameters association."""
    return PromptTemplateWithParameters(
        template=base_prompt_template,
        parameters=llm_parameters_output
    )
```

#### Migration Plan
- **Move to atomic.py**: `prompt_template_input()` - Pure data structure
- **Move to integration.py**: `prompt_template_output()`, `prompt_template_with_parameters()` - Database operations
- **Move to e2e.py**: `base_prompt_template()`, `rag_prompt_template()`, `question_gen_template()`, `prompt_template_list()` - Full stack setup

### `backend/tests/fixtures/pipelines.py` (2 fixtures)

#### Current Fixtures
```python
@pytest.fixture
def pipeline_config_input():
    """Create pipeline config input for testing."""
    return PipelineConfigInput(
        name="test_pipeline",
        description="Test pipeline",
        steps=["ingestion", "chunking", "embedding"]
    )

@pytest.fixture
def pipeline_config_output(pipeline_config_input):
    """Create pipeline config output for testing."""
    return PipelineConfigOutput(
        id=uuid4(),
        name=pipeline_config_input.name,
        description=pipeline_config_input.description,
        steps=pipeline_config_input.steps,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
```

#### Migration Plan
- **Move to atomic.py**: `pipeline_config_input()` - Pure data structure
- **Move to integration.py**: `pipeline_config_output()` - Database operations

### `backend/tests/fixtures/data.py` (5 fixtures)

#### Current Fixtures
```python
@pytest.fixture
def sample_document():
    """Create a sample document for testing."""
    return Document(
        id="doc_1",
        content="This is a test document",
        metadata={"source": "test", "type": "text"}
    )

@pytest.fixture
def sample_chunk():
    """Create a sample chunk for testing."""
    return Chunk(
        id="chunk_1",
        content="This is a test chunk",
        document_id="doc_1",
        metadata={"chunk_index": 0}
    )

@pytest.fixture
def sample_embedding():
    """Create a sample embedding for testing."""
    return [0.1, 0.2, 0.3, 0.4, 0.5]

@pytest.fixture
def sample_query():
    """Create a sample query for testing."""
    return Query(
        text="What is the main topic?",
        filters={"collection_id": "col_1"}
    )

@pytest.fixture
def sample_search_result():
    """Create a sample search result for testing."""
    return SearchResult(
        document_id="doc_1",
        content="This is a test document",
        score=0.95,
        metadata={"source": "test"}
    )
```

#### Migration Plan
- **Move to atomic.py**: All fixtures - Pure data structures, no dependencies

### `backend/tests/fixtures/auth.py` (5 fixtures)

#### Current Fixtures
```python
@pytest.fixture
def auth_headers():
    """Create auth headers for testing."""
    return {"Authorization": "Bearer test_token"}

@pytest.fixture
def mock_jwt_token():
    """Create a mock JWT token for testing."""
    return "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test.signature"

@pytest.fixture
def mock_user_claims():
    """Create mock user claims for testing."""
    return {
        "sub": "user_123",
        "email": "test@example.com",
        "role": "user"
    }

@pytest.fixture
def mock_admin_claims():
    """Create mock admin claims for testing."""
    return {
        "sub": "admin_123",
        "email": "admin@example.com",
        "role": "admin"
    }

@pytest.fixture
def mock_auth_service():
    """Create a mock auth service for testing."""
    mock_service = Mock()
    mock_service.verify_token.return_value = True
    mock_service.get_user_claims.return_value = mock_user_claims()
    return mock_service
```

#### Migration Plan
- **Move to atomic.py**: `auth_headers()`, `mock_jwt_token()`, `mock_user_claims()`, `mock_admin_claims()` - Pure data structures
- **Move to unit.py**: `mock_auth_service()` - Mock service for unit tests

## New Fixture Structure

### `backend/tests/fixtures/atomic.py`
```python
"""Atomic fixtures - Pure data structures, no external dependencies."""

# Data input fixtures
@pytest.fixture
def user_input():
    """Create a user input for testing."""
    return UserInput(
        email="test@example.com",
        ibm_id="test_user_123",
        name="Test User",
        role="user"
    )

@pytest.fixture
def collection_input():
    """Create a collection input for testing."""
    return CollectionInput(
        name="Test Collection",
        description="Test Description"
    )

# ... other input fixtures

# Mock data fixtures
@pytest.fixture
def mock_env_vars():
    """Provide a standard set of mocked environment variables for testing."""
    return {
        "JWT_SECRET_KEY": "test-secret-key",
        "RAG_LLM": "watsonx",
        "WATSONX_APIKEY": "test-api-key",
        # ... other env vars
    }

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
```

### `backend/tests/fixtures/integration.py`
```python
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
    return UserService(db_session_integration, mock_settings)

# ... other integration service fixtures
```

### `backend/tests/fixtures/e2e.py`
```python
"""E2E fixtures - Full stack for end-to-end tests."""

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

# ... other E2E fixtures
```

## Migration Checklist

### Phase 1: Atomic Fixtures
- [ ] Create `fixtures/atomic.py`
- [ ] Move pure data structure fixtures
- [ ] Move mock fixtures from `conftest.py`
- [ ] Update imports in atomic test files

### Phase 2: Integration Fixtures
- [ ] Create `fixtures/integration.py`
- [ ] Implement testcontainers setup
- [ ] Move database-dependent service fixtures
- [ ] Update imports in integration test files

### Phase 3: E2E Fixtures
- [ ] Create `fixtures/e2e.py`
- [ ] Move session-scoped complex fixtures
- [ ] Move full-stack setup fixtures
- [ ] Update imports in E2E test files

### Phase 4: Cleanup
- [ ] Remove old fixture files
- [ ] Update `conftest.py` imports
- [ ] Update all test file imports
- [ ] Run full test suite validation

This detailed mapping ensures a smooth migration from the current fixture structure to the new layered testing architecture while maintaining all existing functionality.
