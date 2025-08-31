"""Tests for CollectionRouter."""

import pytest
from uuid import uuid4
from sqlalchemy.orm import Session

from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.schemas.collection_schema import CollectionInput, CollectionStatus
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.question_schema import QuestionInput

# ----------------
# Fixtures
# ----------------

@pytest.fixture
def test_client(test_client):
    """Use the test client fixture that includes auth mocking."""
    return test_client

@pytest.fixture
def collection_service(db_session: Session) -> CollectionService:
    """Create a CollectionService instance."""
    return CollectionService(db_session)

@pytest.fixture
def file_management_service(db_session: Session) -> FileManagementService:
    """Create a FileManagementService instance."""
    return FileManagementService(db_session)

@pytest.fixture
def test_collection(base_user) -> CollectionInput:
    """Create a test collection input."""
    return CollectionInput(
        name="Test Collection",
        is_private=False,
        users=[base_user.id],
        status=CollectionStatus.CREATED
    )

@pytest.fixture
def test_llm_params() -> dict:
    """Create test LLM parameters input."""
    return {
        "name": "test-params",
        "description": "Test parameters",
        "max_new_tokens": 200,
        "temperature": 0.7,
        "top_k": 50,
        "top_p": 1.0,
        "repetition_penalty": 1.1,
        "is_default": True
    }

# ----------------
# Collection Tests
# ----------------

def test_create_collection(test_client, test_collection, base_user, auth_headers):
    """Test creating a collection."""
    # Add user_id to collection input
    collection_data = test_collection.model_dump(mode="json")
    collection_data["users"] = [str(base_user.id)]
    
    response = test_client.post(
        "/api/collections", 
        json=collection_data,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == test_collection.name
    assert data["is_private"] == test_collection.is_private
    assert "id" in data

def test_get_collection(test_client, collection_service, test_collection, auth_headers):
    """Test getting a collection."""
    collection = collection_service.create_collection(test_collection)
    
    response = test_client.get(
        f"/api/collections/{collection.id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(collection.id)
    assert data["name"] == collection.name

def test_delete_collection(test_client, collection_service, test_collection, auth_headers):
    """Test deleting a collection."""
    collection = collection_service.create_collection(test_collection)
    
    response = test_client.delete(
        f"/api/collections/{collection.id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    
    # Verify deletion
    get_response = test_client.get(
        f"/api/collections/{collection.id}",
        headers=auth_headers
    )
    assert get_response.status_code == 404

# ----------------
# LLM Parameters Tests
# ----------------

def test_llm_parameters_crud(test_client, collection_service, test_collection, test_llm_params, base_user, auth_headers):
    """Test LLM parameters CRUD operations."""
    # First create a collection
    collection_data = test_collection.model_dump(mode="json")
    collection_data["users"] = [str(base_user.id)]
    collection_service.create_collection(CollectionInput(**collection_data))
    
    # Create LLM parameters
    params_input = LLMParametersInput(
        name=test_llm_params["name"],
        description=test_llm_params["description"],
        max_new_tokens=test_llm_params["max_new_tokens"],
        temperature=test_llm_params["temperature"],
        top_k=test_llm_params["top_k"],
        top_p=test_llm_params["top_p"],
        repetition_penalty=test_llm_params["repetition_penalty"],
        is_default=test_llm_params["is_default"]
    )
    
    create_response = test_client.post(
        f"/api/users/{base_user.id}/llm-parameters",
        json=params_input.model_dump(mode="json"),
        headers=auth_headers
    )
    assert create_response.status_code == 200
    data = create_response.json()
    assert data["name"] == test_llm_params["name"]
    
    # Get LLM parameters
    get_response = test_client.get(
        f"/api/users/{base_user.id}/llm-parameters",
        headers=auth_headers
    )
    assert get_response.status_code == 200
    parameters = get_response.json()
    assert len(parameters) > 0
    get_data = parameters[0]  # Get first parameter
    assert get_data["name"] == test_llm_params["name"]
    
    # Delete LLM parameters
    delete_response = test_client.delete(
        f"/api/users/{base_user.id}/llm-parameters/{get_data['id']}",
        headers=auth_headers
    )
    assert delete_response.status_code == 200
    
    # Verify deletion
    get_response = test_client.get(
        f"/api/users/{base_user.id}/llm-parameters",
        headers=auth_headers
    )
    assert get_response.status_code == 200
    assert len(get_response.json()) == 0

# ----------------
# File Operations Tests
# ----------------

def test_file_operations(test_client, collection_service, test_collection, base_user, auth_headers):
    """Test file operations."""
    # Create collection with user
    collection_data = test_collection.model_dump(mode="json")
    collection_data["users"] = [str(base_user.id)]
    collection_service.create_collection(CollectionInput(**collection_data))
    
    # Test file deletion
    # First create a file to delete
    file_id = uuid4()  # In a real test, you'd create a file first
    delete_response = test_client.delete(
        f"/api/users/{base_user.id}/files/{file_id}",
        headers=auth_headers
    )
    assert delete_response.status_code == 404  # Expect 404 since file doesn't exist

# ----------------
# Question Operations Tests
# ----------------

def test_question_operations(test_client, collection_service, test_collection, base_user, auth_headers):
    """Test question operations."""
    # Create collection with user
    collection_data = test_collection.model_dump(mode="json")
    collection_data["users"] = [str(base_user.id)]
    collection = collection_service.create_collection(CollectionInput(**collection_data))
    
    # Create question with proper schema
    question_input = QuestionInput(
        question="What are the key features and benefits of using Python in modern software development?",
        collection_id=collection.id,
        question_metadata=None
    )
    
    # Create question with proper schema
    create_response = test_client.post(
        f"/api/collections/{collection.id}/questions", 
        json=question_input.model_dump(exclude_unset=True, mode="json"),
        headers=auth_headers
    )
    assert create_response.status_code == 200, f"Expected 200, got {create_response.status_code}. Response: {create_response.json()}"
    create_response.json()["id"]
    
    # Get questions
    get_response = test_client.get(
        f"/api/collections/{collection.id}/questions",
        headers=auth_headers
    )
    assert get_response.status_code == 200
    questions = get_response.json()
    assert len(questions) == 1
    assert questions[0]["question"] == question_input.question
    
    # Delete questions
    delete_response = test_client.delete(
        f"/api/collections/{collection.id}/questions",
        headers=auth_headers
    )
    assert delete_response.status_code == 204
    
    # Verify deletion
    get_response = test_client.get(
        f"/api/collections/{collection.id}/questions",
        headers=auth_headers
    )
    assert get_response.status_code == 200
    assert len(get_response.json()) == 0

# ----------------
# Error Case Tests
# ----------------

def test_validation_errors(test_client, auth_headers):
    """Test API validation error cases."""
    # Test invalid collection creation
    # Test invalid collection creation (empty name)
    response = test_client.post(
        "/api/collections",
        json={
            "name": "",  # Empty name should trigger validation error
            "is_private": False,
            "users": [],
            "status": "CREATED"  # Use string enum value
        },
        headers=auth_headers
    )
    assert response.status_code == 422
    
    # Test invalid UUID format
    response = test_client.get(
        "/api/collections/not-a-valid-uuid",
        headers=auth_headers
    )
    assert response.status_code == 422
    
    # Test missing required fields
    response = test_client.post(
        f"/api/collections/{uuid4()}/questions",
        json={},  # Missing required fields
        headers=auth_headers
    )
    assert response.status_code == 422

def test_not_found_errors(test_client, auth_headers):
    """Test not found error cases."""
    non_existent_id = uuid4()
    
    # Test non-existent collection
    response = test_client.get(
        f"/api/collections/{non_existent_id}",
        headers=auth_headers
    )
    assert response.status_code == 404, f"Expected 404, got {response.status_code}. Response: {response.json()}"
    
    # Test non-existent LLM parameters
    response = test_client.get(
        f"/api/collections/{non_existent_id}/llm-parameters",
        headers=auth_headers
    )
    assert response.status_code == 404, f"Expected 404, got {response.status_code}. Response: {response.json()}"
    
    # Test non-existent questions
    response = test_client.get(
        f"/api/collections/{non_existent_id}/questions",
        headers=auth_headers
    )
    assert response.status_code == 404, f"Expected 404, got {response.status_code}. Response: {response.json()}"

if __name__ == "__main__":
    pytest.main([__file__])
