"""Tests for user router endpoints."""

import io
from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from rag_solution.file_management.database import get_db
from rag_solution.models.collection import Collection
from rag_solution.models.pipeline import PipelineConfig
from rag_solution.models.team import Team
from rag_solution.models.user import User
from rag_solution.models.user_collection import UserCollection
from rag_solution.models.user_team import UserTeam


@pytest.fixture
@pytest.mark.api
def test_db(db: Session) -> Session:
    """Get test database session."""
    return db


@pytest.fixture
def client(test_db: Session) -> Generator[TestClient, None, None]:
    """Create test client with database override."""

    def override_get_db() -> Generator[None, None, None]:
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def test_user(test_db: Session) -> User:
    """Create a test user."""
    user = User(ibm_id="test-ibm-id", email="test@example.com", name="Test User")
    test_db.add(user)
    test_db.commit()
    return user


@pytest.fixture
def test_team(test_db: Session) -> Team:
    """Create a test team."""
    team = Team(name="Test Team", description="A team for testing")
    test_db.add(team)
    test_db.commit()
    return team


@pytest.fixture
def test_collection(test_db: Session) -> Collection:
    """Create a test collection."""
    collection = Collection(name="test-collection", description="Test collection", vector_db_name="test_collection")
    test_db.add(collection)
    test_db.commit()
    return collection


@pytest.fixture
def test_user_team(test_db: Session, test_user: User, test_team: Team) -> UserTeam:
    """Create a test user-team association."""
    user_team = UserTeam(user_id=test_user.id, team_id=test_team.id, role="member")
    test_db.add(user_team)
    test_db.commit()
    return user_team


@pytest.fixture
def test_user_collection(test_db: Session, test_user: User, test_collection: Collection) -> UserCollection:
    """Create a test user-collection association."""
    user_collection = UserCollection(user_id=test_user.id, collection_id=test_collection.id)
    test_db.add(user_collection)
    test_db.commit()
    return user_collection


@pytest.fixture
def test_pipeline(test_db: Session, test_user: User) -> PipelineConfig:
    """Create a test pipeline configuration."""
    pipeline = PipelineConfig(
        name="Test Pipeline",
        description="A pipeline for testing",
        user_id=test_user.id,
        is_default=True,
        config={"retriever": "bm25", "reranker": "none", "generator": "watsonx"},
    )
    test_db.add(pipeline)
    test_db.commit()
    return pipeline


class TestUserManagement:
    def test_create_user_success(self, client: TestClient) -> None:
        """Test successful user creation."""
        user_input = {"ibm_id": "new-ibm-id", "email": "new@example.com", "name": "New User"}

        response = client.post("/api/users", json=user_input)
        assert response.status_code == 201
        assert response.json()["email"] == "new@example.com"

    def test_create_user_invalid_input(self, client: TestClient) -> None:
        """Test user creation with invalid input."""
        user_input = {
            # Missing required fields
            "name": "Invalid User"
        }

        response = client.post("/api/users", json=user_input)
        assert response.status_code == 422

    def test_get_user_success(self, client: TestClient, test_user: User) -> None:
        """Test successful user retrieval."""
        response = client.get(f"/api/users/{test_user.id}")
        assert response.status_code == 200
        assert response.json()["email"] == test_user.email

    def test_get_user_not_found(self, client: TestClient) -> None:
        """Test user retrieval when not found."""
        response = client.get(f"/api/users/{uuid4()}")
        assert response.status_code == 404

    def test_update_user_success(self, client: TestClient, test_user: User) -> None:
        """Test successful user update."""
        update_data = {"ibm_id": test_user.ibm_id, "email": "updated@example.com", "name": "Updated User"}

        response = client.put(f"/api/users/{test_user.id}", json=update_data)
        assert response.status_code == 200
        assert response.json()["email"] == "updated@example.com"

    def test_delete_user_success(self, client: TestClient, test_user: User) -> None:
        """Test successful user deletion."""
        response = client.delete(f"/api/users/{test_user.id}")
        assert response.status_code == 200
        assert response.json() is True

    def test_list_users_success(self, client: TestClient, test_user: User) -> None:
        """Test successful users listing."""
        response = client.get("/api/users")
        assert response.status_code == 200
        users = response.json()
        assert len(users) > 0
        assert any(user["id"] == str(test_user.id) for user in users)


class TestUserCollections:
    def test_get_user_collections_success(
        self,
        client: TestClient,
        test_user: User,
        test_user_collection: UserCollection,  # noqa: ARG002
    ) -> None:
        """Test successful user collections retrieval."""
        # Mock authentication
        headers = {"Authorization": f"Bearer {test_user.id}"}
        response = client.get(f"/api/users/{test_user.id}/collections", headers=headers)
        assert response.status_code == 200
        collections = response.json()["collections"]
        assert len(collections) > 0

    def test_get_user_collections_unauthorized(self, client: TestClient, test_user: User) -> None:
        """Test user collections retrieval without authorization."""
        response = client.get(f"/api/users/{test_user.id}/collections")
        assert response.status_code == 403

    def test_add_user_to_collection_success(self, client: TestClient, test_user: User, test_collection: Collection) -> None:
        """Test successful addition of user to collection."""
        response = client.post(f"/api/users/{test_user.id}/collections/{test_collection.id}")
        assert response.status_code == 200
        assert response.json() is True

    def test_remove_user_from_collection_success(  # type: ignore[no-untyped-def]
        self,
        client: TestClient,
        test_user: User,
        test_collection: Collection,
        test_user_collection: UserCollection,  # noqa: ARG002
    ):
        """Test successful removal of user from collection."""
        response = client.delete(f"/api/users/{test_user.id}/collections/{test_collection.id}")
        assert response.status_code == 200
        assert response.json() is True


class TestUserTeams:
    def test_get_user_teams_success(
        self,
        client: TestClient,
        test_user: User,
        test_user_team: UserTeam,  # noqa: ARG002
    ) -> None:
        """Test successful user teams retrieval."""
        response = client.get(f"/api/users/{test_user.id}/teams")
        assert response.status_code == 200
        teams = response.json()
        assert len(teams) > 0
        assert teams[0]["role"] == "member"

    def test_add_user_to_team_success(self, client: TestClient, test_user: User, test_team: Team) -> None:
        """Test successful addition of user to team."""
        response = client.post(f"/api/users/{test_user.id}/teams/{test_team.id}")
        assert response.status_code == 200
        assert response.json() is True

    def test_remove_user_from_team_success(  # type: ignore[no-untyped-def]
        self,
        client: TestClient,
        test_user: User,
        test_team: Team,
        test_user_team: UserTeam,  # noqa: ARG002
    ):
        """Test successful removal of user from team."""
        response = client.delete(f"/api/users/{test_user.id}/teams/{test_team.id}")
        assert response.status_code == 200
        assert response.json() is True


class TestUserFiles:
    def test_upload_file_success(self, client: TestClient, test_user: User, test_collection: Collection) -> None:
        """Test successful file upload."""
        # Create a test file
        file_content = b"Test file content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}

        response = client.post(f"/api/users/{test_user.id}/collections/{test_collection.id}/files", files=files)
        assert response.status_code == 200
        assert response.json()["filename"] == "test.txt"

    def test_upload_file_with_metadata_success(self, client: TestClient, test_user: User, test_collection: Collection) -> None:
        """Test successful file upload with metadata."""
        file_content = b"Test file content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        metadata = {"total_pages": 1, "total_chunks": 1, "keywords": ["test"]}

        response = client.post(
            f"/api/users/{test_user.id}/collections/{test_collection.id}/files",
            files=files,
            data={"metadata": metadata},
        )
        assert response.status_code == 200
        assert response.json()["metadata"]["total_pages"] == 1


class TestUserPipelines:
    def test_get_pipelines_success(
        self,
        client: TestClient,
        test_user: User,
        test_pipeline: PipelineConfig,  # noqa: ARG002
    ) -> None:
        """Test successful pipelines retrieval."""
        # Mock authentication
        headers = {"Authorization": f"Bearer {test_user.id}"}
        response = client.get(f"/api/users/{test_user.id}/pipelines", headers=headers)
        assert response.status_code == 200
        pipelines = response.json()
        assert len(pipelines) > 0
        assert pipelines[0]["name"] == "Test Pipeline"

    def test_create_pipeline_success(self, client: TestClient, test_user: User) -> None:
        """Test successful pipeline creation."""
        # Mock authentication
        pipeline_input = {
            "name": "New Pipeline",
            "description": "A new test pipeline",
            "config": {"retriever": "bm25", "reranker": "none", "generator": "watsonx"},
        }

        response = client.post(f"/api/users/{test_user.id}/pipelines", json=pipeline_input)
        assert response.status_code == 200
        assert response.json()["name"] == "New Pipeline"

    def test_update_pipeline_success(self, client: TestClient, test_user: User, test_pipeline: PipelineConfig) -> None:
        """Test successful pipeline update."""
        # Mock authentication
        headers = {"Authorization": f"Bearer {test_user.id}"}

        update_data = {
            "name": "Updated Pipeline",
            "description": "An updated test pipeline",
            "config": {"retriever": "bm25", "reranker": "none", "generator": "watsonx"},
        }

        response = client.put(f"/api/users/{test_user.id}/pipelines/{test_pipeline.id}", json=update_data, headers=headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Pipeline"

    def test_delete_pipeline_success(self, client: TestClient, test_user: User, test_pipeline: PipelineConfig) -> None:
        """Test successful pipeline deletion."""
        # Mock authentication
        headers = {"Authorization": f"Bearer {test_user.id}"}

        response = client.delete(f"/api/users/{test_user.id}/pipelines/{test_pipeline.id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_set_default_pipeline_success(self, client: TestClient, test_user: User, test_pipeline: PipelineConfig) -> None:
        """Test successful setting of default pipeline."""
        # Mock authentication
        headers = {"Authorization": f"Bearer {test_user.id}"}

        response = client.put(f"/api/users/{test_user.id}/pipelines/{test_pipeline.id}/default", headers=headers)
        assert response.status_code == 200
        assert response.json()["is_default"] is True

    def test_validate_pipeline_success(self, client: TestClient, test_user: User, test_pipeline: PipelineConfig) -> None:
        """Test successful pipeline validation."""
        # Mock authentication
        headers = {"Authorization": f"Bearer {test_user.id}"}

        response = client.post(f"/api/users/{test_user.id}/pipelines/{test_pipeline.id}/validate", headers=headers)
        assert response.status_code == 200
        assert "result" in response.json()

    def test_test_pipeline_success(self, client: TestClient, test_user: User, test_pipeline: PipelineConfig) -> None:
        """Test successful pipeline testing."""
        # Mock authentication
        headers = {"Authorization": f"Bearer {test_user.id}"}

        response = client.post(
            f"/api/users/{test_user.id}/pipelines/{test_pipeline.id}/test",
            params={"query": "What is this test about?"},
            headers=headers,
        )
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__])
