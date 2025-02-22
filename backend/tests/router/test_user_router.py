"""Tests for UserRouter."""

import pytest
from uuid import UUID, uuid4
from unittest.mock import Mock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from rag_solution.services.user_service import UserService
from rag_solution.services.user_collection_service import UserCollectionService
from rag_solution.services.user_collection_interaction_service import UserCollectionInteractionService
from rag_solution.services.user_team_service import UserTeamService
from rag_solution.services.pipeline_service import PipelineService
from rag_solution.schemas.user_schema import UserInput, UserOutput
from rag_solution.schemas.user_collection_schema import UserCollectionsOutput
from rag_solution.schemas.pipeline_schema import PipelineConfigInput, PipelineConfigOutput

@pytest.fixture
def db_session():
    """Create a mock database session."""
    return Mock(spec=Session)

@pytest.fixture
def user_service(db_session):
    """Create a mock UserService instance."""
    return Mock(spec=UserService)

@pytest.fixture
def user_collection_service(db_session):
    """Create a mock UserCollectionService instance."""
    return Mock(spec=UserCollectionService)

@pytest.fixture
def user_collection_interaction_service(db_session):
    """Create a mock UserCollectionInteractionService instance."""
    return Mock(spec=UserCollectionInteractionService)

@pytest.fixture
def user_team_service(db_session):
    """Create a mock UserTeamService instance."""
    return Mock(spec=UserTeamService)

@pytest.fixture
def pipeline_service(db_session):
    """Create a mock PipelineService instance."""
    return Mock(spec=PipelineService)

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture
def sample_user_id():
    """Create a sample user ID."""
    return uuid4()

@pytest.fixture
def sample_user_input():
    """Create a sample user input."""
    return UserInput(
        ibm_id="test-ibm-id",
        email="test@example.com",
        name="Test User"
    )

@pytest.fixture
def sample_user_output(sample_user_input):
    """Create a sample user output."""
    return UserOutput(
        id=uuid4(),
        ibm_id=sample_user_input.ibm_id,
        email=sample_user_input.email,
        name=sample_user_input.name
    )

@pytest.fixture
def sample_pipeline_config_input():
    """Create a sample pipeline configuration input."""
    return PipelineConfigInput(
        name="Test Pipeline",
        description="This is a test pipeline",
        provider="watsonx",
        model_id="test-model",
        query_rewriter_id="test-rewriter",
        retriever_id="test-retriever",
        generator_id="test-generator",
        evaluator_id="test-evaluator"
    )

@pytest.fixture
def sample_pipeline_config_output(sample_pipeline_config_input):
    """Create a sample pipeline configuration output."""
    return PipelineConfigOutput(
        id=uuid4(),
        user_id=uuid4(),
        name=sample_pipeline_config_input.name,
        description=sample_pipeline_config_input.description,
        provider=sample_pipeline_config_input.provider,
        model_id=sample_pipeline_config_input.model_id,
        query_rewriter_id=sample_pipeline_config_input.query_rewriter_id,
        retriever_id=sample_pipeline_config_input.retriever_id,
        generator_id=sample_pipeline_config_input.generator_id,
        evaluator_id=sample_pipeline_config_input.evaluator_id,
        is_default=False
    )

def test_list_users(client, user_service, sample_user_output):
    """Test listing users."""
    user_service.list_users.return_value = [sample_user_output]
    
    response = client.get("/api/users")
    
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == str(sample_user_output.id)

def test_create_user(client, user_service, sample_user_input, sample_user_output):
    """Test creating a user."""
    user_service.create_user.return_value = sample_user_output
    
    response = client.post("/api/users", json=sample_user_input.dict())
    
    assert response.status_code == 201
    assert response.json()["id"] == str(sample_user_output.id)

def test_get_user(client, user_service, sample_user_output):
    """Test getting a user."""
    user_service.get_user_by_id.return_value = sample_user_output
    
    response = client.get(f"/api/users/{sample_user_output.id}")
    
    assert response.status_code == 200
    assert response.json()["id"] == str(sample_user_output.id)

def test_update_user(client, user_service, sample_user_input, sample_user_output):
    """Test updating a user."""
    user_service.update_user.return_value = sample_user_output
    
    response = client.put(f"/api/users/{sample_user_output.id}", json=sample_user_input.dict())
    
    assert response.status_code == 200
    assert response.json()["id"] == str(sample_user_output.id)

def test_delete_user(client, user_service, sample_user_output):
    """Test deleting a user."""
    user_service.delete_user.return_value = True
    
    response = client.delete(f"/api/users/{sample_user_output.id}")
    
    assert response.status_code == 200
    assert response.json() is True

def test_get_user_collections(client, user_collection_interaction_service, sample_user_id, sample_user_output):
    """Test getting user collections."""
    user_collection_interaction_service.get_user_collections_with_files.return_value = UserCollectionsOutput(
        user_id=sample_user_id,
        collections=[]
    )
    
    response = client.get(f"/api/users/{sample_user_id}/collections")
    
    assert response.status_code == 200
    assert response.json()["user_id"] == str(sample_user_id)

def test_add_user_to_collection(client, user_collection_service, sample_user_id, sample_collection_id):
    """Test adding user to collection."""
    user_collection_service.add_user_to_collection.return_value = True
    
    response = client.post(f"/api/users/{sample_user_id}/collections/{sample_collection_id}")
    
    assert response.status_code == 200
    assert response.json() is True

def test_remove_user_from_collection(client, user_collection_service, sample_user_id, sample_collection_id):
    """Test removing user from collection."""
    user_collection_service.remove_user_from_collection.return_value = True
    
    response = client.delete(f"/api/users/{sample_user_id}/collections/{sample_collection_id}")
    
    assert response.status_code == 200
    assert response.json() is True

def test_get_user_teams(client, user_team_service, sample_user_id, sample_user_output):
    """Test getting user teams."""
    user_team_service.get_user_teams.return_value = []
    
    response = client.get(f"/api/users/{sample_user_id}/teams")
    
    assert response.status_code == 200
    assert len(response.json()) == 0

def test_add_user_to_team(client, user_team_service, sample_user_id, sample_team_id):
    """Test adding user to team."""
    user_team_service.add_user_to_team.return_value = True
    
    response = client.post(f"/api/users/{sample_user_id}/teams/{sample_team_id}")
    
    assert response.status_code == 200
    assert response.json() is True

def test_remove_user_from_team(client, user_team_service, sample_user_id, sample_team_id):
    """Test removing user from team."""
    user_team_service.remove_user_from_team.return_value = True
    
    response = client.delete(f"/api/users/{sample_user_id}/teams/{sample_team_id}")
    
    assert response.status_code == 200
    assert response.json() is True

def test_get_pipelines(client, pipeline_service, sample_user_id, sample_pipeline_config_output):
    """Test getting user pipelines."""
    pipeline_service.get_user_pipelines.return_value = [sample_pipeline_config_output]
    
    response = client.get(f"/api/users/{sample_user_id}/pipelines")
    
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == str(sample_pipeline_config_output.id)

def test_create_pipeline(client, pipeline_service, sample_user_id, sample_pipeline_config_input, sample_pipeline_config_output):
    """Test creating a pipeline."""
    pipeline_service.create_pipeline.return_value = sample_pipeline_config_output
    
    response = client.post(f"/api/users/{sample_user_id}/pipelines", json=sample_pipeline_config_input.dict())
    
    assert response.status_code == 200
    assert response.json()["id"] == str(sample_pipeline_config_output.id)

def test_update_pipeline(client, pipeline_service, sample_user_id, sample_pipeline_config_input, sample_pipeline_config_output):
    """Test updating a pipeline."""
    pipeline_service.update_pipeline.return_value = sample_pipeline_config_output
    
    response = client.put(f"/api/users/{sample_user_id}/pipelines/{sample_pipeline_config_output.id}", json=sample_pipeline_config_input.dict())
    
    assert response.status_code == 200
    assert response.json()["id"] == str(sample_pipeline_config_output.id)

def test_delete_pipeline(client, pipeline_service, sample_user_id, sample_pipeline_config_output):
    """Test deleting a pipeline."""
    pipeline_service.delete_pipeline.return_value = True
    
    response = client.delete(f"/api/users/{sample_user_id}/pipelines/{sample_pipeline_config_output.id}")
    
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

def test_set_default_pipeline(client, pipeline_service, sample_user_id, sample_pipeline_config_output):
    """Test setting a default pipeline."""
    pipeline_service.set_default_pipeline.return_value = sample_pipeline_config_output
    
    response = client.put(f"/api/users/{sample_user_id}/pipelines/{sample_pipeline_config_output.id}/default")
    
    assert response.status_code == 200
    assert response.json()["id"] == str(sample_pipeline_config_output.id)

def test_validate_pipeline(client, pipeline_service, sample_user_id, sample_pipeline_config_output):
    """Test validating a pipeline."""
    pipeline_service.validate_pipeline.return_value = {"status": "success"}
    
    response = client.post(f"/api/users/{sample_user_id}/pipelines/{sample_pipeline_config_output.id}/validate")
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_test_pipeline(client, pipeline_service, sample_user_id, sample_pipeline_config_output):
    """Test testing a pipeline."""
    pipeline_service.test_pipeline.return_value = {"status": "success"}
    
    response = client.post(f"/api/users/{sample_user_id}/pipelines/{sample_pipeline_config_output.id}/test", params={"query": "test query"})
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"

if __name__ == "__main__":
    pytest.main([__file__])
