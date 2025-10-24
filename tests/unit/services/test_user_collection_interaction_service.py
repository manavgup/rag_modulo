"""
Unit tests for UserCollectionInteractionService.

This module tests the UserCollectionInteractionService class which handles
user-collection interactions including fetching collections with files,
managing user-collection relationships, and retrieving collection users.
"""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from datetime import datetime

from rag_solution.services.user_collection_interaction_service import UserCollectionInteractionService
from rag_solution.schemas.user_collection_schema import UserCollectionsOutput, UserCollectionDetailOutput, FileInfo
from rag_solution.core.exceptions import NotFoundError


class TestUserCollectionInteractionService:
    """Test cases for UserCollectionInteractionService."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return Mock()

    @pytest.fixture
    def mock_user_collection_repository(self):
        """Create a mock user collection repository."""
        return Mock()

    @pytest.fixture
    def mock_collection_repository(self):
        """Create a mock collection repository."""
        return Mock()

    @pytest.fixture
    def service(self, mock_db_session, mock_user_collection_repository, mock_collection_repository):
        """Create a service instance with mocked dependencies."""
        with patch('rag_solution.services.user_collection_interaction_service.UserCollectionRepository', return_value=mock_user_collection_repository), \
             patch('rag_solution.services.user_collection_interaction_service.CollectionRepository', return_value=mock_collection_repository):
            return UserCollectionInteractionService(mock_db_session)

    @pytest.fixture
    def sample_user_id(self):
        """Create a sample user ID."""
        return uuid4()

    @pytest.fixture
    def sample_collection_id(self):
        """Create a sample collection ID."""
        return uuid4()

    @pytest.fixture
    def sample_file_info(self):
        """Create sample file info."""
        return FileInfo(id=uuid4(), filename="test_document.pdf")

    @pytest.fixture
    def sample_collection(self, sample_collection_id, sample_file_info):
        """Create a sample collection with files."""
        collection = Mock()
        collection.id = sample_collection_id
        collection.name = "Test Collection"
        collection.is_private = True
        collection.created_at = datetime.now()
        collection.updated_at = datetime.now()
        collection.status = "active"
        collection.files = [sample_file_info]
        return collection

    @pytest.fixture
    def sample_user_collection(self, sample_collection_id, sample_file_info):
        """Create a sample user collection."""
        user_collection = Mock()
        user_collection.collection_id = sample_collection_id
        user_collection.name = "Test Collection"
        user_collection.is_private = True
        user_collection.created_at = datetime.now()
        user_collection.updated_at = datetime.now()
        user_collection.status = "active"
        user_collection.files = [sample_file_info]
        return user_collection

    def test_service_initialization(self, service, mock_db_session, mock_user_collection_repository, mock_collection_repository):
        """Test service initialization with dependencies."""
        assert service.db == mock_db_session
        assert service.user_collection_repository == mock_user_collection_repository
        assert service.collection_repository == mock_collection_repository

    def test_get_user_collections_with_files_success(self, service, sample_user_id, sample_collection, sample_user_collection):
        """Test successful retrieval of user collections with files."""
        # Setup
        service.user_collection_repository.get_user_collections.return_value = [sample_user_collection]
        service.collection_repository.get.return_value = sample_collection

        # Execute
        result = service.get_user_collections_with_files(sample_user_id)

        # Verify
        assert isinstance(result, UserCollectionsOutput)
        assert result.user_id == sample_user_id
        assert len(result.collections) == 1

        collection = result.collections[0]
        assert collection.collection_id == sample_collection.id
        assert collection.name == sample_collection.name
        assert collection.is_private == sample_collection.is_private
        assert collection.files == [FileInfo(id=sample_file_info.id, filename=sample_file_info.filename)]

        # Verify method calls
        service.user_collection_repository.get_user_collections.assert_called_once_with(sample_user_id)
        service.collection_repository.get.assert_called_once_with(sample_user_collection.collection_id)

    def test_get_user_collections_with_files_no_collections(self, service, sample_user_id):
        """Test retrieval when user has no collections."""
        # Setup
        service.user_collection_repository.get_user_collections.return_value = []

        # Execute
        result = service.get_user_collections_with_files(sample_user_id)

        # Verify
        assert isinstance(result, UserCollectionsOutput)
        assert result.user_id == sample_user_id
        assert result.collections == []

    def test_get_user_collections_with_files_collection_not_found(self, service, sample_user_id, sample_user_collection):
        """Test handling when collection is not found."""
        # Setup
        service.user_collection_repository.get_user_collections.return_value = [sample_user_collection]
        service.collection_repository.get.return_value = None

        # Execute
        result = service.get_user_collections_with_files(sample_user_id)

        # Verify
        assert isinstance(result, UserCollectionsOutput)
        assert result.user_id == sample_user_id
        assert result.collections == []

    def test_get_user_collections_with_files_exception(self, service, sample_user_id):
        """Test exception handling in get_user_collections_with_files."""
        # Setup
        service.user_collection_repository.get_user_collections.side_effect = Exception("Database error")

        # Execute & Verify
        with pytest.raises(Exception, match="Database error"):
            service.get_user_collections_with_files(sample_user_id)

    def test_get_user_collections_success(self, service, sample_user_id, sample_user_collection):
        """Test successful retrieval of user collections without detailed files."""
        # Setup
        service.user_collection_repository.get_user_collections.return_value = [sample_user_collection]

        # Execute
        result = service.get_user_collections(sample_user_id)

        # Verify
        assert isinstance(result, UserCollectionsOutput)
        assert result.user_id == sample_user_id
        assert len(result.collections) == 1

        collection = result.collections[0]
        assert collection.collection_id == sample_user_collection.collection_id
        assert collection.name == sample_user_collection.name
        assert collection.is_private == sample_user_collection.is_private
        assert collection.files == sample_user_collection.files

    def test_get_user_collections_no_collections(self, service, sample_user_id):
        """Test retrieval when user has no collections."""
        # Setup
        service.user_collection_repository.get_user_collections.return_value = []

        # Execute
        result = service.get_user_collections(sample_user_id)

        # Verify
        assert isinstance(result, UserCollectionsOutput)
        assert result.user_id == sample_user_id
        assert result.collections == []

    def test_get_user_collections_exception(self, service, sample_user_id):
        """Test exception handling in get_user_collections."""
        # Setup
        service.user_collection_repository.get_user_collections.side_effect = Exception("Database error")

        # Execute & Verify
        with pytest.raises(Exception, match="Database error"):
            service.get_user_collections(sample_user_id)

    def test_add_user_to_collection_success(self, service, sample_user_id, sample_collection_id):
        """Test successful addition of user to collection."""
        # Setup
        service.user_collection_repository.add_user_to_collection.return_value = True

        # Execute
        result = service.add_user_to_collection(sample_user_id, sample_collection_id)

        # Verify
        assert result is True
        service.user_collection_repository.add_user_to_collection.assert_called_once_with(sample_user_id, sample_collection_id)

    def test_add_user_to_collection_failure(self, service, sample_user_id, sample_collection_id):
        """Test failure to add user to collection."""
        # Setup
        service.user_collection_repository.add_user_to_collection.return_value = False

        # Execute
        result = service.add_user_to_collection(sample_user_id, sample_collection_id)

        # Verify
        assert result is False

    def test_remove_user_from_collection_success(self, service, sample_user_id, sample_collection_id):
        """Test successful removal of user from collection."""
        # Setup
        service.user_collection_repository.remove_user_from_collection.return_value = True

        # Execute
        result = service.remove_user_from_collection(sample_user_id, sample_collection_id)

        # Verify
        assert result is True
        service.user_collection_repository.remove_user_from_collection.assert_called_once_with(sample_user_id, sample_collection_id)

    def test_remove_user_from_collection_failure(self, service, sample_user_id, sample_collection_id):
        """Test failure to remove user from collection."""
        # Setup
        service.user_collection_repository.remove_user_from_collection.return_value = False

        # Execute
        result = service.remove_user_from_collection(sample_user_id, sample_collection_id)

        # Verify
        assert result is False

    def test_get_collection_users_success(self, service, sample_collection_id, sample_user_collection):
        """Test successful retrieval of collection users."""
        # Setup
        service.user_collection_repository.get_collection_users.return_value = [sample_user_collection]

        # Execute
        result = service.get_collection_users(sample_collection_id)

        # Verify
        assert len(result) == 1
        assert isinstance(result[0], UserCollectionDetailOutput)

        user_collection = result[0]
        assert user_collection.collection_id == sample_user_collection.collection_id
        assert user_collection.name == sample_user_collection.name
        assert user_collection.is_private == sample_user_collection.is_private
        assert user_collection.files == sample_user_collection.files

    def test_get_collection_users_empty(self, service, sample_collection_id):
        """Test retrieval when collection has no users."""
        # Setup
        service.user_collection_repository.get_collection_users.return_value = []

        # Execute
        result = service.get_collection_users(sample_collection_id)

        # Verify
        assert result == []

    def test_get_collection_users_multiple(self, service, sample_collection_id):
        """Test retrieval of multiple collection users."""
        # Setup
        user_collection1 = Mock()
        user_collection1.collection_id = sample_collection_id
        user_collection1.name = "Collection 1"
        user_collection1.is_private = True
        user_collection1.created_at = datetime.now()
        user_collection1.updated_at = datetime.now()
        user_collection1.status = "active"
        user_collection1.files = []

        user_collection2 = Mock()
        user_collection2.collection_id = sample_collection_id
        user_collection2.name = "Collection 2"
        user_collection2.is_private = False
        user_collection2.created_at = datetime.now()
        user_collection2.updated_at = datetime.now()
        user_collection2.status = "active"
        user_collection2.files = []

        service.user_collection_repository.get_collection_users.return_value = [user_collection1, user_collection2]

        # Execute
        result = service.get_collection_users(sample_collection_id)

        # Verify
        assert len(result) == 2
        assert all(isinstance(uc, UserCollectionDetailOutput) for uc in result)
        assert result[0].name == "Collection 1"
        assert result[1].name == "Collection 2"

    def test_logging_behavior(self, service, sample_user_id, sample_collection_id, caplog):
        """Test that appropriate logging occurs."""
        # Setup
        service.user_collection_repository.get_user_collections.return_value = []

        # Execute
        service.get_user_collections(sample_user_id)
        service.add_user_to_collection(sample_user_id, sample_collection_id)

        # Verify logging
        assert f"Fetching collections for user: {sample_user_id}" in caplog.text
        assert f"Adding user {sample_user_id} to collection {sample_collection_id}" in caplog.text
