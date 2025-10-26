"""Unit tests for UserCollectionService."""

from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import UUID4

from backend.rag_solution.services.user_collection_service import UserCollectionService
from backend.rag_solution.schemas.collection_schema import CollectionOutput, CollectionStatus
from backend.rag_solution.schemas.user_collection_schema import UserCollectionOutput, FileInfo
from backend.rag_solution.core.exceptions import NotFoundError


class TestUserCollectionService:
    """Test cases for UserCollectionService."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Create a mock database session."""
        return Mock()

    @pytest.fixture
    def mock_user_collection_repository(self) -> Mock:
        """Create a mock user collection repository."""
        return Mock()

    @pytest.fixture
    def service(self, mock_db: Mock, mock_user_collection_repository: Mock) -> UserCollectionService:
        """Create a UserCollectionService instance with mocked dependencies."""
        service = UserCollectionService(mock_db)
        service.user_collection_repository = mock_user_collection_repository
        return service

    @pytest.fixture
    def sample_user_id(self) -> UUID4:
        """Create a sample user ID."""
        return uuid4()

    @pytest.fixture
    def sample_collection_id(self) -> UUID4:
        """Create a sample collection ID."""
        return uuid4()

    def test_init(self, mock_db: Mock) -> None:
        """Test UserCollectionService initialization."""
        service = UserCollectionService(mock_db)

        assert service.db == mock_db
        assert service.user_collection_repository is not None
        assert hasattr(service.user_collection_repository, 'db')

    def test_get_user_collections_success(self, service: UserCollectionService, sample_user_id: UUID4, mock_user_collection_repository: Mock) -> None:
        """Test get_user_collections with successful result."""
        # Mock repository response
        mock_user_collection = Mock()
        mock_user_collection.id = uuid4()
        mock_user_collection.name = "Test Collection"
        mock_user_collection.vector_db_name = "test_vector_db"
        mock_user_collection.is_private = False
        mock_user_collection.created_at = datetime.now(timezone.utc)
        mock_user_collection.updated_at = datetime.now(timezone.utc)
        mock_user_collection.user_ids = [uuid4()]
        file_mock = Mock()
        file_mock.id = uuid4()
        file_mock.filename = "test.pdf"
        file_mock.file_size_bytes = 1024
        mock_user_collection.files = [file_mock]
        mock_user_collection.status = CollectionStatus.COMPLETED

        mock_user_collection_repository.get_user_collections.return_value = [mock_user_collection]

        result = service.get_user_collections(sample_user_id)

        assert len(result) == 1
        assert isinstance(result[0], CollectionOutput)
        assert result[0].name == "Test Collection"
        assert result[0].vector_db_name == "test_vector_db"
        assert result[0].is_private is False
        assert result[0].status == CollectionStatus.COMPLETED
        mock_user_collection_repository.get_user_collections.assert_called_once_with(sample_user_id)

    def test_get_user_collections_empty(self, service: UserCollectionService, sample_user_id: UUID4, mock_user_collection_repository: Mock) -> None:
        """Test get_user_collections with empty result."""
        mock_user_collection_repository.get_user_collections.return_value = []

        result = service.get_user_collections(sample_user_id)

        assert result == []
        mock_user_collection_repository.get_user_collections.assert_called_once_with(sample_user_id)

    def test_add_user_to_collection_success(self, service: UserCollectionService, sample_user_id: UUID4, sample_collection_id: UUID4, mock_user_collection_repository: Mock) -> None:
        """Test add_user_to_collection with successful result."""
        mock_user_collection_repository.add_user_to_collection.return_value = True

        result = service.add_user_to_collection(sample_user_id, sample_collection_id)

        assert result is True
        mock_user_collection_repository.add_user_to_collection.assert_called_once_with(sample_user_id, sample_collection_id)

    def test_add_user_to_collection_failure(self, service: UserCollectionService, sample_user_id: UUID4, sample_collection_id: UUID4, mock_user_collection_repository: Mock) -> None:
        """Test add_user_to_collection with failure result."""
        mock_user_collection_repository.add_user_to_collection.return_value = False

        result = service.add_user_to_collection(sample_user_id, sample_collection_id)

        assert result is False
        mock_user_collection_repository.add_user_to_collection.assert_called_once_with(sample_user_id, sample_collection_id)

    def test_remove_user_from_collection_success(self, service: UserCollectionService, sample_user_id: UUID4, sample_collection_id: UUID4, mock_user_collection_repository: Mock) -> None:
        """Test remove_user_from_collection with successful result."""
        mock_user_collection_repository.remove_user_from_collection.return_value = True

        result = service.remove_user_from_collection(sample_user_id, sample_collection_id)

        assert result is True
        mock_user_collection_repository.remove_user_from_collection.assert_called_once_with(sample_user_id, sample_collection_id)

    def test_remove_user_from_collection_failure(self, service: UserCollectionService, sample_user_id: UUID4, sample_collection_id: UUID4, mock_user_collection_repository: Mock) -> None:
        """Test remove_user_from_collection with failure result."""
        mock_user_collection_repository.remove_user_from_collection.return_value = False

        result = service.remove_user_from_collection(sample_user_id, sample_collection_id)

        assert result is False
        mock_user_collection_repository.remove_user_from_collection.assert_called_once_with(sample_user_id, sample_collection_id)

    def test_get_collection_users_success(self, service: UserCollectionService, sample_collection_id: UUID4, mock_user_collection_repository: Mock) -> None:
        """Test get_collection_users with existing collection."""
        # Mock collection exists
        mock_collection = Mock()
        service.db.query.return_value.filter.return_value.first.return_value = mock_collection

        # Mock repository response
        mock_user_collection = UserCollectionOutput(
            id=uuid4(),
            name="Test Collection",
            user_id=uuid4(),
            collection_id=sample_collection_id
        )
        mock_user_collection_repository.get_collection_users.return_value = [mock_user_collection]

        result = service.get_collection_users(sample_collection_id)

        assert len(result) == 1
        assert isinstance(result[0], UserCollectionOutput)
        assert result[0].collection_id == sample_collection_id
        service.db.query.assert_called_once()
        mock_user_collection_repository.get_collection_users.assert_called_once_with(sample_collection_id)

    def test_get_collection_users_collection_not_found(self, service: UserCollectionService, sample_collection_id: UUID4) -> None:
        """Test get_collection_users with non-existent collection."""
        # Mock collection doesn't exist
        service.db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            service.get_collection_users(sample_collection_id)

        assert exc_info.value.resource_type == "Collection"
        # resource_id is passed as string to NotFoundError constructor
        assert str(sample_collection_id) in str(exc_info.value.message)
        service.db.query.assert_called_once()

    def test_remove_all_users_from_collection_success(self, service: UserCollectionService, sample_collection_id: UUID4, mock_user_collection_repository: Mock) -> None:
        """Test remove_all_users_from_collection with successful result."""
        mock_user_collection_repository.remove_all_users_from_collection.return_value = True

        result = service.remove_all_users_from_collection(sample_collection_id)

        assert result is True
        mock_user_collection_repository.remove_all_users_from_collection.assert_called_once_with(sample_collection_id)

    def test_remove_all_users_from_collection_failure(self, service: UserCollectionService, sample_collection_id: UUID4, mock_user_collection_repository: Mock) -> None:
        """Test remove_all_users_from_collection with failure result."""
        mock_user_collection_repository.remove_all_users_from_collection.return_value = False

        result = service.remove_all_users_from_collection(sample_collection_id)

        assert result is False
        mock_user_collection_repository.remove_all_users_from_collection.assert_called_once_with(sample_collection_id)

    # Additional tests for edge cases and coverage

    def test_get_user_collections_multiple_collections(self, service: UserCollectionService, sample_user_id: UUID4, mock_user_collection_repository: Mock) -> None:
        """Test get_user_collections with multiple collections."""
        # Create multiple mock collections
        mock_collections = []
        for i in range(5):
            mock_collection = Mock()
            mock_collection.id = uuid4()
            mock_collection.name = f"Test Collection {i}"
            mock_collection.vector_db_name = f"test_vector_db_{i}"
            mock_collection.is_private = i % 2 == 0
            mock_collection.created_at = datetime.now(timezone.utc)
            mock_collection.updated_at = datetime.now(timezone.utc)
            mock_collection.user_ids = [uuid4(), uuid4()]
            # Create proper file mock with required fields
            file_mock = Mock()
            file_mock.id = uuid4()
            file_mock.filename = f"test{i}.pdf"
            file_mock.file_size_bytes = 1024 * (i + 1)
            mock_collection.files = [file_mock]
            mock_collection.status = CollectionStatus.COMPLETED
            mock_collections.append(mock_collection)

        mock_user_collection_repository.get_user_collections.return_value = mock_collections

        result = service.get_user_collections(sample_user_id)

        assert len(result) == 5
        for i, collection in enumerate(result):
            assert isinstance(collection, CollectionOutput)
            assert collection.name == f"Test Collection {i}"
            assert collection.vector_db_name == f"test_vector_db_{i}"
            assert collection.is_private == (i % 2 == 0)

    def test_get_user_collections_empty_files_list(self, service: UserCollectionService, sample_user_id: UUID4, mock_user_collection_repository: Mock) -> None:
        """Test get_user_collections with empty files list."""
        mock_collection = Mock()
        mock_collection.id = uuid4()
        mock_collection.name = "Collection Without Files"
        mock_collection.vector_db_name = "test_db"
        mock_collection.is_private = True
        mock_collection.created_at = datetime.now(timezone.utc)
        mock_collection.updated_at = datetime.now(timezone.utc)
        mock_collection.user_ids = [uuid4()]
        mock_collection.files = []
        mock_collection.status = CollectionStatus.CREATED

        mock_user_collection_repository.get_user_collections.return_value = [mock_collection]

        result = service.get_user_collections(sample_user_id)

        assert len(result) == 1
        assert result[0].files == []
        assert result[0].status == CollectionStatus.CREATED

    def test_get_user_collections_with_processing_status(self, service: UserCollectionService, sample_user_id: UUID4, mock_user_collection_repository: Mock) -> None:
        """Test get_user_collections with processing status."""
        mock_collection = Mock()
        mock_collection.id = uuid4()
        mock_collection.name = "Processing Collection"
        mock_collection.vector_db_name = "test_db"
        mock_collection.is_private = False
        mock_collection.created_at = datetime.now(timezone.utc)
        mock_collection.updated_at = datetime.now(timezone.utc)
        mock_collection.user_ids = []
        mock_collection.files = []
        mock_collection.status = CollectionStatus.PROCESSING

        mock_user_collection_repository.get_user_collections.return_value = [mock_collection]

        result = service.get_user_collections(sample_user_id)

        assert len(result) == 1
        assert result[0].status == CollectionStatus.PROCESSING

    def test_get_user_collections_with_error_status(self, service: UserCollectionService, sample_user_id: UUID4, mock_user_collection_repository: Mock) -> None:
        """Test get_user_collections with error status."""
        mock_collection = Mock()
        mock_collection.id = uuid4()
        mock_collection.name = "Error Collection"
        mock_collection.vector_db_name = "test_db"
        mock_collection.is_private = True
        mock_collection.created_at = datetime.now(timezone.utc)
        mock_collection.updated_at = datetime.now(timezone.utc)
        mock_collection.user_ids = [uuid4()]
        mock_collection.files = []
        mock_collection.status = CollectionStatus.ERROR

        mock_user_collection_repository.get_user_collections.return_value = [mock_collection]

        result = service.get_user_collections(sample_user_id)

        assert len(result) == 1
        assert result[0].status == CollectionStatus.ERROR

    def test_get_user_collections_repository_exception(self, service: UserCollectionService, sample_user_id: UUID4, mock_user_collection_repository: Mock) -> None:
        """Test get_user_collections when repository raises exception."""
        mock_user_collection_repository.get_user_collections.side_effect = Exception("Database connection error")

        with pytest.raises(Exception) as exc_info:
            service.get_user_collections(sample_user_id)

        assert "Database connection error" in str(exc_info.value)

    def test_get_collection_users_empty_result(self, service: UserCollectionService, sample_collection_id: UUID4, mock_user_collection_repository: Mock) -> None:
        """Test get_collection_users with no users."""
        # Mock collection exists
        mock_collection = Mock()
        service.db.query.return_value.filter.return_value.first.return_value = mock_collection

        mock_user_collection_repository.get_collection_users.return_value = []

        result = service.get_collection_users(sample_collection_id)

        assert result == []

    def test_get_collection_users_multiple_users(self, service: UserCollectionService, sample_collection_id: UUID4, mock_user_collection_repository: Mock) -> None:
        """Test get_collection_users with multiple users."""
        # Mock collection exists
        mock_collection = Mock()
        service.db.query.return_value.filter.return_value.first.return_value = mock_collection

        # Create multiple users
        mock_users = [
            UserCollectionOutput(
                id=uuid4(),
                name=f"User Collection {i}",
                user_id=uuid4(),
                collection_id=sample_collection_id
            )
            for i in range(3)
        ]

        mock_user_collection_repository.get_collection_users.return_value = mock_users

        result = service.get_collection_users(sample_collection_id)

        assert len(result) == 3
        for user in result:
            assert isinstance(user, UserCollectionOutput)
            assert user.collection_id == sample_collection_id

    def test_get_collection_users_database_query_exception(self, service: UserCollectionService, sample_collection_id: UUID4) -> None:
        """Test get_collection_users when database query raises exception."""
        service.db.query.return_value.filter.return_value.first.side_effect = Exception("Database query failed")

        with pytest.raises(Exception) as exc_info:
            service.get_collection_users(sample_collection_id)

        assert "Database query failed" in str(exc_info.value)

    def test_add_user_to_collection_repository_exception(self, service: UserCollectionService, sample_user_id: UUID4, sample_collection_id: UUID4, mock_user_collection_repository: Mock) -> None:
        """Test add_user_to_collection when repository raises exception."""
        mock_user_collection_repository.add_user_to_collection.side_effect = Exception("Failed to add user")

        with pytest.raises(Exception) as exc_info:
            service.add_user_to_collection(sample_user_id, sample_collection_id)

        assert "Failed to add user" in str(exc_info.value)

    def test_remove_user_from_collection_repository_exception(self, service: UserCollectionService, sample_user_id: UUID4, sample_collection_id: UUID4, mock_user_collection_repository: Mock) -> None:
        """Test remove_user_from_collection when repository raises exception."""
        mock_user_collection_repository.remove_user_from_collection.side_effect = Exception("Failed to remove user")

        with pytest.raises(Exception) as exc_info:
            service.remove_user_from_collection(sample_user_id, sample_collection_id)

        assert "Failed to remove user" in str(exc_info.value)
