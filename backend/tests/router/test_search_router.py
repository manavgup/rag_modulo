"""Tests for search router endpoints."""

import pytest
from uuid import uuid4
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from rag_solution.router.search_router import router
from rag_solution.models.collection import Collection
from rag_solution.models.file import File, FileMetadata
from rag_solution.models.provider_config import ProviderModelConfig
from rag_solution.models.llm_parameters import LLMParameters
from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.schemas.search_schema import SearchInput
from rag_solution.file_management.database import get_db

# Create test app
app = FastAPI()
app.include_router(router)

@pytest.fixture
def test_db(db: Session):
    """Get test database session."""
    return db

@pytest.fixture
def client(test_db: Session):
    """Create test client with database override."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass  # Don't close since it's handled by the db fixture
            
    app.dependency_overrides[get_db] = override_get_db
    
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()

@pytest.fixture
def test_collection(test_db: Session):
    """Create test collection."""
    collection = Collection(
        name="test-collection",
        description="Test collection",
        vector_db_name="test_collection"
    )
    test_db.add(collection)
    test_db.commit()
    return collection

@pytest.fixture
def test_file(test_db: Session, test_collection: Collection):
    """Create test file."""
    file = File(
        filename="test.txt",
        document_id="doc1",
        collection_id=test_collection.id,
        metadata=FileMetadata(
            total_pages=1,
            total_chunks=1,
            keywords=["test"]
        )
    )
    test_db.add(file)
    test_db.commit()
    return file

@pytest.fixture
def test_config(test_db: Session):
    """Create test configurations."""
    # Create LLM parameters
    params = LLMParameters(
        name="test-params",
        max_new_tokens=100,
        temperature=0.7,
        top_k=50,
        top_p=1.0,
        is_default=True
    )
    test_db.add(params)
    test_db.commit()
    
    # Create provider config
    provider = ProviderModelConfig(
        model_id="test-model",
        provider_name="test-provider",
        api_key="test-key",
        default_model_id="default-model",
        parameters_id=params.id,
        is_default=True,
        is_active=True
    )
    test_db.add(provider)
    
    # Create prompt template
    template = PromptTemplate(
        name="test-template",
        provider="test-provider",
        system_prompt="You are a helpful assistant",
        context_prefix="Context:",
        query_prefix="Question:",
        answer_prefix="Answer:",
        is_default=True
    )
    test_db.add(template)
    test_db.commit()
    
    return {
        'parameters': params,
        'provider': provider,
        'template': template
    }

@pytest.mark.asyncio
async def test_search_endpoint_success(
    client: TestClient,
    test_collection: Collection,
    test_file: File,
    test_config: dict
):
    """Test successful search request."""
    # Create search input
    search_input = {
        "question": "What is the capital of France?",
        "collection_id": str(test_collection.id)
    }
    
    # Make request
    response = client.post("/api/search", json=search_input)
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "documents" in data
    assert "query_results" in data
    assert "rewritten_query" in data
    assert len(data["documents"]) > 0
    assert data["documents"][0]["document_name"] == test_file.filename

@pytest.mark.asyncio
async def test_search_endpoint_collection_not_found(client: TestClient):
    """Test search with non-existent collection."""
    search_input = {
        "question": "test query",
        "collection_id": str(uuid4())
    }
    
    response = client.post("/api/search", json=search_input)
    assert response.status_code == 404
    assert "Collection not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_search_endpoint_invalid_input(client: TestClient):
    """Test search with invalid input."""
    # Missing required field
    search_input = {
        "collection_id": str(uuid4())
        # Missing question field
    }
    
    response = client.post("/api/search", json=search_input)
    assert response.status_code == 422  # Validation error

@pytest.mark.asyncio
async def test_search_endpoint_empty_query(
    client: TestClient,
    test_collection: Collection
):
    """Test search with empty query."""
    search_input = {
        "question": "   ",  # Empty after stripping
        "collection_id": str(test_collection.id)
    }
    
    response = client.post("/api/search", json=search_input)
    assert response.status_code == 400
    assert "Query cannot be empty" in response.json()["detail"]

@pytest.mark.asyncio
async def test_search_endpoint_with_context(
    client: TestClient,
    test_collection: Collection,
    test_file: File,
    test_config: dict
):
    """Test search with additional context."""
    search_input = {
        "question": "What is the capital of France?",
        "collection_id": str(test_collection.id)
    }
    
    # Add context in query params
    context = {
        "user_role": "student",
        "language": "en",
        "detail_level": "high"
    }
    
    response = client.post("/api/search", json=search_input, params=context)
    assert response.status_code == 200
    data = response.json()
    assert data["rewritten_query"] != search_input["question"]
    assert isinstance(data["rewritten_query"], str)
    assert len(data["rewritten_query"]) > 0

@pytest.mark.asyncio
async def test_search_endpoint_no_config(
    client: TestClient,
    test_collection: Collection
):
    """Test search with no provider configuration."""
    search_input = {
        "question": "test query",
        "collection_id": str(test_collection.id)
    }
    
    response = client.post("/api/search", json=search_input)
    assert response.status_code == 500
    assert "No valid provider configuration found" in response.json()["detail"]
