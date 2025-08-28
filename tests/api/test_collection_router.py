"""Tests for CollectionRouter."""

import pytest
from uuid import UUID, uuid4
from fastapi.testclient import TestClient

from main import app
from rag_solution.schemas.collection_schema import CollectionInput, CollectionStatus
from rag_solution.schemas.question_schema import QuestionInput
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateType


def test_create_collection(client, collection_service, base_user, auth_headers):
    """Test creating a collection."""
    collection_input = CollectionInput(
        name="Test Collection",
        is_private=False,
        users=[str(base_user.id)]  # Convert UUID to string
    )
    
    response = client.post("/api/collections", json=collection_input.model_dump(), headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == collection_input.name
    assert data["is_private"] == collection_input.is_private
    assert "id" in data


def test_create_collection_with_documents(
    test_client: TestClient,
    auth_headers: dict,
    base_user,
    test_documents
):
    """Test creating a collection with documents."""
    # Create a test file
    test_file_content = "Test document content"
    files = [("files", ("test.txt", test_file_content, "text/plain"))]
    
    response = test_client.post(
        "/api/collections/with-files",
        data={
            "collection_name": "Test Collection with Files",
            "is_private": "false",
            "user_id": str(base_user.id)
        },
        files=files,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Collection with Files"
    assert UUID(data["id"]) is not None


def test_get_collection(test_client, collection_service, test_collection, auth_headers):
    """Test getting a collection."""
    # Create the collection
    collection = collection_service.create_collection(test_collection)
    
    # Ensure the collection exists
    assert collection is not None, "Collection was not created"
    
    # Now try to get the collection
    response = test_client.get(
        f"/api/collections/{collection.id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(collection.id)
    assert data["name"] == collection.name


def test_delete_collection(
    test_client: TestClient,
    auth_headers: dict,
    base_collection
):
    """Test deleting a collection."""
    response = test_client.delete(
        f"/api/collections/{base_collection.id}",
        headers=auth_headers
    )
    
    assert response.status_code == 204


def test_create_collection_question(
    test_client: TestClient,
    auth_headers: dict,
    base_collection
):
    """Test creating a question for a collection."""
    question_input = {
        "question": "What is this collection about?"
    }
    
    response = test_client.post(
        f"/api/collections/{base_collection.id}/questions",
        json=question_input,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["question"] == question_input["question"]
    assert UUID(data["id"]) is not None


def test_get_collection_questions(
    test_client: TestClient,
    auth_headers: dict,
    base_collection,
    base_suggested_question
):
    """Test getting questions for a collection."""
    response = test_client.get(
        f"/api/collections/{base_collection.id}/questions",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    questions = response.json()
    assert len(questions) >= 1
    assert any(q["id"] == str(base_suggested_question.id) for q in questions)


def test_delete_collection_question(
    test_client: TestClient,
    auth_headers: dict,
    base_collection,
    base_suggested_question
):
    """Test deleting a question from a collection."""
    response = test_client.delete(
        f"/api/collections/{base_collection.id}/questions/{base_suggested_question.id}",
        headers=auth_headers
    )
    
    assert response.status_code == 204


def test_delete_all_collection_questions(
    test_client: TestClient,
    auth_headers: dict,
    base_collection
):
    """Test deleting all questions from a collection."""
    response = test_client.delete(
        f"/api/collections/{base_collection.id}/questions",
        headers=auth_headers
    )
    
    assert response.status_code == 204


def test_create_llm_parameters(
    test_client: TestClient,
    auth_headers: dict,
    base_collection
):
    """Test creating LLM parameters for a collection."""
    params_input = {
        "name": "test-params",
        "description": "Test parameters",
        "max_new_tokens": 200,
        "temperature": 0.7,
        "top_k": 50,
        "top_p": 1.0,
        "repetition_penalty": 1.1,
        "is_default": True
    }
    
    response = test_client.post(
        f"/api/collections/{base_collection.id}/llm-parameters",
        json=params_input,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["max_new_tokens"] == params_input["max_new_tokens"]
    assert data["temperature"] == params_input["temperature"]


def test_get_llm_parameters(
    test_client: TestClient,
    auth_headers: dict,
    base_collection,
    base_llm_parameters
):
    """Test getting LLM parameters for a collection."""
    response = test_client.get(
        f"/api/collections/{base_collection.id}/llm-parameters",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert UUID(data["id"]) is not None
    assert data["max_new_tokens"] == base_llm_parameters.max_new_tokens
    assert data["temperature"] == base_llm_parameters.temperature


def test_delete_llm_parameters(
    test_client: TestClient,
    auth_headers: dict,
    base_collection,
    base_llm_parameters
):
    """Test deleting LLM parameters for a collection."""
    response = test_client.delete(
        f"/api/collections/{base_collection.id}/llm-parameters",
        headers=auth_headers
    )
    
    assert response.status_code == 204


def test_create_prompt_template(
    test_client: TestClient,
    auth_headers: dict,
    base_collection
):
    """Test creating a prompt template for a collection."""
    template_input = {
        "name": "test-template",
        "provider": "watsonx",
        "template_type": PromptTemplateType.RAG_QUERY,
        "system_prompt": "You are a helpful assistant.",
        "template_format": "{context}\n\n{question}",
        "input_variables": {
            "context": "Context for the question",
            "question": "User's question"
        },
        "example_inputs": {
            "context": "Sample context",
            "question": "Sample question"
        },
        "is_default": True
    }
    
    response = test_client.post(
        f"/api/collections/{base_collection.id}/prompt-templates",
        json=template_input,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == template_input["name"]
    assert data["template_type"] == template_input["template_type"]


def test_get_prompt_template(
    test_client: TestClient,
    auth_headers: dict,
    base_collection,
    base_prompt_template
):
    """Test getting a prompt template for a collection."""
    response = test_client.get(
        f"/api/collections/{base_collection.id}/prompt-templates",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert UUID(data["id"]) is not None
    assert data["name"] == base_prompt_template.name
    assert data["template_type"] == base_prompt_template.template_type


def test_delete_prompt_template(
    test_client: TestClient,
    auth_headers: dict,
    base_collection,
    base_prompt_template
):
    """Test deleting a prompt template for a collection."""
    response = test_client.delete(
        f"/api/collections/{base_collection.id}/prompt-templates",
        headers=auth_headers
    )
    
    assert response.status_code == 204


def test_get_collection_files(
    test_client: TestClient,
    auth_headers: dict,
    base_collection
):
    """Test getting files for a collection."""
    response = test_client.get(
        f"/api/collections/{base_collection.id}/files",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_file_path(
    test_client: TestClient,
    auth_headers: dict,
    base_collection
):
    """Test getting file path for a collection."""
    # First upload a file
    test_file_content = "Test document content"
    files = [("files", ("test.txt", test_file_content, "text/plain"))]
    
    upload_response = test_client.post(
        f"/api/collections/{base_collection.id}/files",
        files=files,
        headers=auth_headers
    )
    
    assert upload_response.status_code == 200
    file_id = upload_response.json()[0]["id"]
    
    # Then get its path
    response = test_client.get(
        f"/api/collections/{base_collection.id}/files/{file_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "file_path" in data


def test_delete_files(
    test_client: TestClient,
    auth_headers: dict,
    base_collection
):
    """Test deleting files from a collection."""
    response = test_client.delete(
        f"/api/collections/{base_collection.id}/files",
        json={"filenames": ["test.txt"]},
        headers=auth_headers
    )
    
    assert response.status_code == 204


def test_update_file_metadata(
    test_client: TestClient,
    auth_headers: dict,
    base_collection
):
    """Test updating file metadata for a collection."""
    # First upload a file
    test_file_content = "Test document content"
    files = [("files", ("test.txt", test_file_content, "text/plain"))]
    
    upload_response = test_client.post(
        f"/api/collections/{base_collection.id}/files",
        files=files,
        headers=auth_headers
    )
    
    assert upload_response.status_code == 200
    file_id = upload_response.json()[0]["id"]
    
    # Then update its metadata
    new_metadata = {
        "name": "updated_test.txt"
    }
    
    response = test_client.put(
        f"/api/collections/{base_collection.id}/files/{file_id}/metadata",
        json=new_metadata,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == new_metadata["name"]


if __name__ == "__main__":
    pytest.main([__file__])