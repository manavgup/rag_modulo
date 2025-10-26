"""Unit tests for UserCollectionInteractionService."""

from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
from backend.rag_solution.schemas.user_collection_schema import (
    FileInfo,
    UserCollectionDetailOutput,
    UserCollectionsOutput,
)
from backend.rag_solution.services.user_collection_interaction_service import UserCollectionInteractionService


class TestUserCollectionInteractionService:
    """Test cases for UserCollectionInteractionService."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Create a mock database session."""
        return Mock()

    @pytest.fixture
    def service(self, mock_db: Mock) -> UserCollectionInteractionService:
        """Create a UserCollectionInteractionService instance with mocked dependencies."""
        service = UserCollectionInteractionService(mock_db)
        # Mock the repository methods
        service.user_collection_repository.get_user_collections = Mock()
        service.user_collection_repository.add_user_to_collection = Mock()
        service.user_collection_repository.remove_user_from_collection = Mock()
        service.user_collection_repository.get_collection_users = Mock()
        service.collection_repository.get = Mock()
        return service

    @pytest.fixture
    def sample_user_id(self):
        """Create a sample user ID."""
        return uuid4()

    @pytest.fixture
    def sample_collection_id(self):
        """Create a sample collection ID."""
        return uuid4()

    @pytest.fixture
    def sample_file_info(self) -> FileInfo:
        """Create sample file info."""
        return FileInfo(id=str(uuid4()), filename="test.pdf")

    @pytest.fixture
    def sample_collection_detail(self, sample_collection_id: str, sample_file_info: FileInfo) -> UserCollectionDetailOutput:
        """Create sample collection detail."""
        return UserCollectionDetailOutput(
            collection_id=sample_collection_id,
            name="Test Collection",
            is_private=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            files=[sample_file_info],
            status="completed"
        )

    def test_init(self, mock_db: Mock) -> None:
        """Test UserCollectionInteractionService initialization."""
        service = UserCollectionInteractionService(mock_db)
        assert service.db == mock_db
        assert service.user_collection_repository is not None
        assert service.collection_repository is not None

    def test_get_user_collections_with_files_success(self, service: UserCollectionInteractionService, sample_user_id: str, sample_collection_detail: UserCollectionDetailOutput) -> None:
        """Test successful retrieval of user collections with files."""
        # Mock user collections
        mock_user_collection = Mock()
        mock_user_collection.collection_id = sample_collection_detail.collection_id

        service.user_collection_repository.get_user_collections.return_value = [mock_user_collection]

        # Mock full collection details
        mock_full_collection = Mock()
        mock_full_collection.id = sample_collection_detail.collection_id
        mock_full_collection.name = sample_collection_detail.name
        mock_full_collection.is_private = sample_collection_detail.is_private
        mock_full_collection.created_at = sample_collection_detail.created_at
        mock_full_collection.updated_at = sample_collection_detail.updated_at
        mock_full_collection.status = sample_collection_detail.status

        # Mock files
        mock_file = Mock()
        mock_file.id = sample_collection_detail.files[0].id
        mock_file.filename = sample_collection_detail.files[0].filename
        mock_full_collection.files = [mock_file]

        service.collection_repository.get.return_value = mock_full_collection

        result = service.get_user_collections_with_files(sample_user_id)

        assert isinstance(result, UserCollectionsOutput)
        assert result.user_id == sample_user_id
        assert len(result.collections) == 1
        assert result.collections[0].collection_id == sample_collection_detail.collection_id
        assert result.collections[0].name == sample_collection_detail.name
        assert len(result.collections[0].files) == 1
        assert result.collections[0].files[0].id == sample_collection_detail.files[0].id

    def test_get_user_collections_with_files_no_collections(self, service: UserCollectionInteractionService, sample_user_id: str) -> None:
        """Test retrieval when user has no collections."""
        service.user_collection_repository.get_user_collections.return_value = []

        result = service.get_user_collections_with_files(sample_user_id)

        assert isinstance(result, UserCollectionsOutput)
        assert result.user_id == sample_user_id
        assert result.collections == []

    def test_get_user_collections_with_files_collection_not_found(self, service: UserCollectionInteractionService, sample_user_id: str) -> None:
        """Test retrieval when collection is not found."""
        mock_user_collection = Mock()
        mock_user_collection.collection_id = str(uuid4())

        service.user_collection_repository.get_user_collections.return_value = [mock_user_collection]
        service.collection_repository.get.return_value = None

        result = service.get_user_collections_with_files(sample_user_id)

        assert isinstance(result, UserCollectionsOutput)
        assert result.user_id == sample_user_id
        assert result.collections == []

    def test_get_user_collections_with_files_exception(self, service: UserCollectionInteractionService, sample_user_id: str) -> None:
        """Test exception handling in get_user_collections_with_files."""
        service.user_collection_repository.get_user_collections.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            service.get_user_collections_with_files(sample_user_id)

    def test_get_user_collections_success(self, service: UserCollectionInteractionService, sample_user_id: str, sample_collection_detail: UserCollectionDetailOutput) -> None:
        """Test successful retrieval of user collections."""
        # Mock user collections with file info
        mock_user_collection = Mock()
        mock_user_collection.collection_id = sample_collection_detail.collection_id
        mock_user_collection.name = sample_collection_detail.name
        mock_user_collection.is_private = sample_collection_detail.is_private
        mock_user_collection.created_at = sample_collection_detail.created_at
        mock_user_collection.updated_at = sample_collection_detail.updated_at
        mock_user_collection.status = sample_collection_detail.status
        mock_user_collection.files = sample_collection_detail.files

        service.user_collection_repository.get_user_collections.return_value = [mock_user_collection]

        result = service.get_user_collections(sample_user_id)

        assert isinstance(result, UserCollectionsOutput)
        assert result.user_id == sample_user_id
        assert len(result.collections) == 1
        assert result.collections[0].collection_id == sample_collection_detail.collection_id
        assert result.collections[0].name == sample_collection_detail.name

    def test_get_user_collections_no_collections(self, service: UserCollectionInteractionService, sample_user_id: str) -> None:
        """Test retrieval when user has no collections."""
        service.user_collection_repository.get_user_collections.return_value = []

        result = service.get_user_collections(sample_user_id)

        assert isinstance(result, UserCollectionsOutput)
        assert result.user_id == sample_user_id
        assert result.collections == []

    def test_get_user_collections_exception(self, service: UserCollectionInteractionService, sample_user_id: str) -> None:
        """Test exception handling in get_user_collections."""
        service.user_collection_repository.get_user_collections.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            service.get_user_collections(sample_user_id)

    def test_add_user_to_collection_success(self, service: UserCollectionInteractionService, sample_user_id: str, sample_collection_id: str) -> None:
        """Test successful addition of user to collection."""
        service.user_collection_repository.add_user_to_collection.return_value = True

        result = service.add_user_to_collection(sample_user_id, sample_collection_id)

        assert result is True
        service.user_collection_repository.add_user_to_collection.assert_called_once_with(sample_user_id, sample_collection_id)

    def test_add_user_to_collection_failure(self, service: UserCollectionInteractionService, sample_user_id: str, sample_collection_id: str) -> None:
        """Test failed addition of user to collection."""
        service.user_collection_repository.add_user_to_collection.return_value = False

        result = service.add_user_to_collection(sample_user_id, sample_collection_id)

        assert result is False

    def test_remove_user_from_collection_success(self, service: UserCollectionInteractionService, sample_user_id: str, sample_collection_id: str) -> None:
        """Test successful removal of user from collection."""
        service.user_collection_repository.remove_user_from_collection.return_value = True

        result = service.remove_user_from_collection(sample_user_id, sample_collection_id)

        assert result is True
        service.user_collection_repository.remove_user_from_collection.assert_called_once_with(sample_user_id, sample_collection_id)

    def test_remove_user_from_collection_failure(self, service: UserCollectionInteractionService, sample_user_id: str, sample_collection_id: str) -> None:
        """Test failed removal of user from collection."""
        service.user_collection_repository.remove_user_from_collection.return_value = False

        result = service.remove_user_from_collection(sample_user_id, sample_collection_id)

        assert result is False

    def test_get_collection_users_success(self, service: UserCollectionInteractionService, sample_collection_id: str, sample_collection_detail: UserCollectionDetailOutput) -> None:
        """Test successful retrieval of collection users."""
        # Mock user collections
        mock_user_collection = Mock()
        mock_user_collection.collection_id = sample_collection_detail.collection_id
        mock_user_collection.name = sample_collection_detail.name
        mock_user_collection.is_private = sample_collection_detail.is_private
        mock_user_collection.created_at = sample_collection_detail.created_at
        mock_user_collection.updated_at = sample_collection_detail.updated_at
        mock_user_collection.status = sample_collection_detail.status
        mock_user_collection.files = sample_collection_detail.files

        service.user_collection_repository.get_collection_users.return_value = [mock_user_collection]

        result = service.get_collection_users(sample_collection_id)

        assert len(result) == 1
        assert isinstance(result[0], UserCollectionDetailOutput)
        assert result[0].collection_id == sample_collection_detail.collection_id
        assert result[0].name == sample_collection_detail.name

    def test_get_collection_users_empty(self, service: UserCollectionInteractionService, sample_collection_id: str) -> None:
        """Test retrieval when collection has no users."""
        service.user_collection_repository.get_collection_users.return_value = []

        result = service.get_collection_users(sample_collection_id)

        assert result == []
