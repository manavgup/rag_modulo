"""Atomic tests for core service data validation and schemas."""

from datetime import UTC
from uuid import uuid4

import pytest

from rag_solution.schemas.collection_schema import CollectionInput, CollectionOutput, CollectionStatus
from rag_solution.schemas.team_schema import TeamInput, TeamOutput
from rag_solution.schemas.user_schema import UserInput, UserOutput


@pytest.mark.atomic
class TestCoreServicesDataValidation:
    """Test core service data validation and schemas - no external dependencies."""

    def test_user_input_validation(self):
        """Test UserInput schema validation."""
        # Valid user input
        valid_user = UserInput(email="test@example.com", ibm_id="test_user_123", name="Test User", role="user")

        assert valid_user.email == "test@example.com"
        assert valid_user.ibm_id == "test_user_123"
        assert valid_user.name == "Test User"
        assert valid_user.role == "user"

    def test_user_output_validation(self):
        """Test UserOutput schema validation."""
        # Valid user output
        user_id = uuid4()
        provider_id = uuid4()
        valid_user = UserOutput(
            id=user_id,
            email="test@example.com",
            ibm_id="test_user_123",
            name="Test User",
            role="user",
            preferred_provider_id=provider_id,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        assert valid_user.id == user_id
        assert valid_user.email == "test@example.com"
        assert valid_user.ibm_id == "test_user_123"
        assert valid_user.name == "Test User"
        assert valid_user.role == "user"
        assert valid_user.preferred_provider_id == provider_id

    def test_user_role_enum_validation(self):
        """Test UserRole enum validation."""
        # Test all valid user roles
        valid_roles = ["user", "admin", "super_admin"]

        for role in valid_roles:
            user = UserInput(email="test@example.com", ibm_id="test_user", name="Test User", role=role)
            assert user.role == role

    def test_user_email_validation(self):
        """Test user email validation rules."""
        # Valid email formats
        valid_emails = ["test@example.com", "user.name@domain.co.uk", "test+tag@example.org", "user123@test-domain.com"]

        for email in valid_emails:
            user = UserInput(email=email, ibm_id="test_user", name="Test User", role="user")
            assert user.email == email
            assert isinstance(user.email, str)
            assert "@" in user.email
            assert "." in user.email.split("@")[1]  # Domain has extension

    def test_team_input_validation(self):
        """Test TeamInput schema validation."""
        # Valid team input
        valid_team = TeamInput(name="Test Team", description="Test team description")

        assert valid_team.name == "Test Team"
        assert valid_team.description == "Test team description"

    def test_team_output_validation(self):
        """Test TeamOutput schema validation."""
        # Valid team output
        team_id = uuid4()
        valid_team = TeamOutput(id=team_id, name="Test Team", description="Test team description")

        assert valid_team.id == team_id
        assert valid_team.name == "Test Team"
        assert valid_team.description == "Test team description"

    def test_team_name_validation(self):
        """Test team name validation rules."""
        # Valid team names
        valid_names = ["Test Team", "Team-123", "team_with_underscores", "Team Name With Spaces", "Team123"]

        for name in valid_names:
            team = TeamInput(name=name, description="Test description")
            assert team.name == name
            assert isinstance(team.name, str)
            assert len(team.name.strip()) > 0

    def test_collection_input_validation(self):
        """Test CollectionInput schema validation."""
        # Valid collection input
        user_id = uuid4()
        valid_collection = CollectionInput(name="Test Collection", is_private=True, users=[user_id], status=CollectionStatus.CREATED)

        assert valid_collection.name == "Test Collection"
        assert valid_collection.is_private is True
        assert valid_collection.users == [user_id]
        assert valid_collection.status == CollectionStatus.CREATED

    def test_collection_output_validation(self):
        """Test CollectionOutput schema validation."""
        # Valid collection output
        collection_id = uuid4()
        user_id = uuid4()
        from datetime import datetime

        test_datetime = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        valid_collection = CollectionOutput(
            id=collection_id,
            name="Test Collection",
            vector_db_name="test_vector_db",
            is_private=True,
            user_ids=[user_id],
            files=[],
            status=CollectionStatus.COMPLETED,
            created_at=test_datetime,
            updated_at=test_datetime,
        )

        assert valid_collection.id == collection_id
        assert valid_collection.name == "Test Collection"
        assert valid_collection.vector_db_name == "test_vector_db"
        assert valid_collection.is_private is True
        assert valid_collection.user_ids == [user_id]
        assert valid_collection.status == CollectionStatus.COMPLETED

    def test_collection_privacy_validation(self):
        """Test collection privacy validation."""
        # Test private collection
        private_collection = CollectionInput(name="Private Collection", is_private=True, users=[], status=CollectionStatus.CREATED)
        assert private_collection.is_private is True

        # Test public collection
        public_collection = CollectionInput(name="Public Collection", is_private=False, users=[], status=CollectionStatus.CREATED)
        assert not public_collection.is_private

    def test_collection_status_validation(self):
        """Test collection status validation."""
        # Test all valid statuses
        statuses = [
            CollectionStatus.CREATED,
            CollectionStatus.PROCESSING,
            CollectionStatus.COMPLETED,
            CollectionStatus.ERROR,
        ]

        for status in statuses:
            collection = CollectionInput(name=f"Collection {status}", is_private=True, users=[], status=status)
            assert collection.status == status

    def test_core_services_serialization(self):
        """Test core services data serialization."""
        # Test user serialization
        user = UserInput(email="serialization@test.com", ibm_id="serialization_user", name="Serialization User", role="user")

        data = user.model_dump()
        assert isinstance(data, dict)
        assert "email" in data
        assert "ibm_id" in data
        assert "name" in data
        assert "role" in data
        assert data["email"] == "serialization@test.com"
        assert data["role"] == "user"

        # Test team serialization
        team = TeamInput(name="Serialization Team", description="Test team for serialization")

        data = team.model_dump()
        assert isinstance(data, dict)
        assert "name" in data
        assert "description" in data
        assert data["name"] == "Serialization Team"

        # Test collection serialization
        collection = CollectionInput(name="Serialization Collection", is_private=False, users=[], status=CollectionStatus.CREATED)

        data = collection.model_dump()
        assert isinstance(data, dict)
        assert "name" in data
        assert "is_private" in data
        assert "users" in data
        assert "status" in data
        assert data["name"] == "Serialization Collection"
        assert not data["is_private"]
