"""
Unit tests for FileManagementService.

This module tests the FileManagementService class which handles file upload,
storage, retrieval, and management operations for collections.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from uuid import uuid4
from pathlib import Path
from datetime import datetime
from fastapi import UploadFile

from rag_solution.services.file_management_service import FileManagementService
from rag_solution.schemas.file_schema import FileInput, FileOutput, FileMetadata
from rag_solution.core.exceptions import NotFoundError, ValidationError
from core.config import Settings


class TestFileManagementService:
    """Test cases for FileManagementService."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return Mock()

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.upload_dir = "/tmp/uploads"
        settings.max_file_size = 10 * 1024 * 1024  # 10MB
        return settings

    @pytest.fixture
    def service(self, mock_db_session, mock_settings):
        """Create a service instance with mocked dependencies."""
        return FileManagementService(mock_db_session, mock_settings)

    @pytest.fixture
    def sample_user_id(self):
        """Create a sample user ID."""
        return uuid4()

    @pytest.fixture
    def sample_collection_id(self):
        """Create a sample collection ID."""
        return uuid4()

    @pytest.fixture
    def sample_file_id(self):
        """Create a sample file ID."""
        return uuid4()

    @pytest.fixture
    def sample_file_input(self, sample_collection_id):
        """Create a sample file input."""
        return FileInput(
            collection_id=sample_collection_id,
            filename="test_document.pdf",
            file_path="/tmp/uploads/test_document.pdf",
            file_type="application/pdf",
            metadata=FileMetadata(size=1024, pages=5)
        )

    @pytest.fixture
    def sample_file_output(self, sample_file_id, sample_collection_id, sample_user_id):
        """Create a sample file output."""
        return FileOutput(
            id=sample_file_id,
            collection_id=sample_collection_id,
            user_id=sample_user_id,
            filename="test_document.pdf",
            file_path="/tmp/uploads/test_document.pdf",
            file_type="application/pdf",
            metadata=FileMetadata(size=1024, pages=5),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    @pytest.fixture
    def sample_upload_file(self):
        """Create a sample upload file."""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test_document.pdf"
        mock_file.file.read.return_value = b"PDF content here"
        return mock_file

    def test_service_initialization(self, service, mock_db_session, mock_settings):
        """Test service initialization with dependencies."""
        assert service.db == mock_db_session
        assert service.settings == mock_settings
        assert hasattr(service, 'file_repository')

    def test_create_file_success(self, service, sample_file_input, sample_user_id, sample_file_output):
        """Test successful file creation."""
        # Setup
        service.file_repository.create.return_value = sample_file_output

        # Execute
        result = service.create_file(sample_file_input, sample_user_id)

        # Verify
        assert result == sample_file_output
        service.file_repository.create.assert_called_once_with(sample_file_input, sample_user_id)

    def test_get_file_by_id_success(self, service, sample_file_id, sample_file_output):
        """Test successful file retrieval by ID."""
        # Setup
        service.file_repository.get.return_value = sample_file_output

        # Execute
        result = service.get_file_by_id(sample_file_id)

        # Verify
        assert result == sample_file_output
        service.file_repository.get.assert_called_once_with(sample_file_id)

    def test_get_file_by_id_not_found(self, service, sample_file_id):
        """Test file retrieval when file not found."""
        # Setup
        service.file_repository.get.side_effect = NotFoundError("File", str(sample_file_id))

        # Execute & Verify
        with pytest.raises(NotFoundError):
            service.get_file_by_id(sample_file_id)

    def test_get_file_by_name_success(self, service, sample_collection_id, sample_file_output):
        """Test successful file retrieval by name."""
        # Setup
        service.file_repository.get_file_by_name.return_value = sample_file_output

        # Execute
        result = service.get_file_by_name(sample_collection_id, "test_document.pdf")

        # Verify
        assert result == sample_file_output
        service.file_repository.get_file_by_name.assert_called_once_with(sample_collection_id, "test_document.pdf")

    def test_get_file_by_name_not_found(self, service, sample_collection_id):
        """Test file retrieval by name when file not found."""
        # Setup
        service.file_repository.get_file_by_name.side_effect = NotFoundError("File", "test_document.pdf")

        # Execute & Verify
        with pytest.raises(NotFoundError):
            service.get_file_by_name(sample_collection_id, "test_document.pdf")

    def test_get_file_by_name_unexpected_error(self, service, sample_collection_id):
        """Test file retrieval by name with unexpected error."""
        # Setup
        service.file_repository.get_file_by_name.side_effect = Exception("Database error")

        # Execute & Verify
        with pytest.raises(Exception, match="Database error"):
            service.get_file_by_name(sample_collection_id, "test_document.pdf")

    def test_update_file_success(self, service, sample_file_id, sample_file_input, sample_file_output):
        """Test successful file update."""
        # Setup
        service.file_repository.update.return_value = sample_file_output

        # Execute
        result = service.update_file(sample_file_id, sample_file_input)

        # Verify
        assert result == sample_file_output
        service.file_repository.update.assert_called_once_with(sample_file_id, sample_file_input)

    def test_update_file_not_found(self, service, sample_file_id, sample_file_input):
        """Test file update when file not found."""
        # Setup
        service.file_repository.update.side_effect = NotFoundError("File", str(sample_file_id))

        # Execute & Verify
        with pytest.raises(NotFoundError):
            service.update_file(sample_file_id, sample_file_input)

    @patch('rag_solution.services.file_management_service.Path')
    def test_delete_file_success(self, mock_path_class, service, sample_file_id, sample_file_output):
        """Test successful file deletion."""
        # Setup
        service.file_repository.get.return_value = sample_file_output
        service.file_repository.delete.return_value = None

        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.unlink.return_value = None
        mock_path_class.return_value = mock_path

        # Execute
        service.delete_file(sample_file_id)

        # Verify
        service.file_repository.get.assert_called_once_with(sample_file_id)
        service.file_repository.delete.assert_called_once_with(sample_file_id)
        mock_path.unlink.assert_called_once()

    @patch('rag_solution.services.file_management_service.Path')
    def test_delete_file_not_found(self, mock_path_class, service, sample_file_id):
        """Test file deletion when file not found."""
        # Setup
        service.file_repository.get.side_effect = NotFoundError("File", str(sample_file_id))

        # Execute & Verify
        with pytest.raises(NotFoundError):
            service.delete_file(sample_file_id)

    @patch('rag_solution.services.file_management_service.Path')
    def test_delete_file_file_not_exists(self, mock_path_class, service, sample_file_id, sample_file_output):
        """Test file deletion when physical file doesn't exist."""
        # Setup
        service.file_repository.get.return_value = sample_file_output
        service.file_repository.delete.return_value = None

        mock_path = Mock()
        mock_path.exists.return_value = False
        mock_path_class.return_value = mock_path

        # Execute
        service.delete_file(sample_file_id)

        # Verify
        service.file_repository.get.assert_called_once_with(sample_file_id)
        service.file_repository.delete.assert_called_once_with(sample_file_id)
        mock_path.unlink.assert_not_called()

    def test_delete_files_success(self, service, sample_collection_id, sample_file_output):
        """Test successful deletion of multiple files."""
        # Setup
        filenames = ["file1.pdf", "file2.pdf"]
        service.file_repository.get_file_by_name.return_value = sample_file_output
        service.file_repository.get.return_value = sample_file_output
        service.file_repository.delete.return_value = None

        with patch.object(service, 'delete_file') as mock_delete_file:
            # Execute
            result = service.delete_files(sample_collection_id, filenames)

            # Verify
            assert result is True
            assert mock_delete_file.call_count == 2

    def test_delete_files_error(self, service, sample_collection_id):
        """Test deletion of multiple files with error."""
        # Setup
        filenames = ["file1.pdf"]
        service.file_repository.get_file_by_name.side_effect = Exception("Database error")

        # Execute & Verify
        with pytest.raises(Exception, match="Database error"):
            service.delete_files(sample_collection_id, filenames)

    def test_delete_file_by_id_success(self, service, sample_collection_id, sample_file_id, sample_file_output):
        """Test successful deletion of file by ID."""
        # Setup
        service.file_repository.get_file_by_name.return_value = sample_file_output
        service.file_repository.get.return_value = sample_file_output
        service.file_repository.delete.return_value = None

        with patch.object(service, 'delete_file') as mock_delete_file:
            # Execute
            service.delete_file_by_id(sample_collection_id, sample_file_id)

            # Verify
            mock_delete_file.assert_called_once_with(sample_file_id)

    def test_delete_file_by_id_not_found(self, service, sample_collection_id, sample_file_id):
        """Test deletion of file by ID when file not found."""
        # Setup
        service.file_repository.get_file_by_name.side_effect = NotFoundError("File", "test_document.pdf")

        # Execute & Verify
        with pytest.raises(NotFoundError):
            service.delete_file_by_id(sample_collection_id, sample_file_id)

    def test_determine_file_type_pdf(self, service):
        """Test file type determination for PDF."""
        result = service.determine_file_type("document.pdf")
        assert result == "application/pdf"

    def test_determine_file_type_txt(self, service):
        """Test file type determination for text file."""
        result = service.determine_file_type("document.txt")
        assert result == "text/plain"

    def test_determine_file_type_unknown(self, service):
        """Test file type determination for unknown file type."""
        result = service.determine_file_type("document.unknown")
        assert result is None

    @patch('rag_solution.services.file_management_service.Path')
    def test_upload_file_success(self, mock_path_class, service, sample_user_id, sample_collection_id):
        """Test successful file upload."""
        # Setup
        content = b"PDF content"
        filename = "test.pdf"

        mock_path = Mock()
        mock_path.exists.return_value = False
        mock_path.mkdir.return_value = None
        mock_path_class.return_value = mock_path

        with patch('builtins.open', mock_open()) as mock_file:
            # Execute
            result = service.upload_file(sample_user_id, sample_collection_id, content, filename)

            # Verify
            assert result is not None
            mock_file.assert_called_once()
            mock_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch('rag_solution.services.file_management_service.Path')
    def test_upload_file_existing_file(self, mock_path_class, service, sample_user_id, sample_collection_id):
        """Test file upload when file already exists."""
        # Setup
        content = b"PDF content"
        filename = "test.pdf"

        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path

        with patch('builtins.open', mock_open()) as mock_file:
            # Execute
            result = service.upload_file(sample_user_id, sample_collection_id, content, filename)

            # Verify
            assert result is not None
            mock_file.assert_called_once()

    def test_save_file_success(self, service, sample_upload_file, sample_collection_id, sample_user_id):
        """Test successful file saving."""
        with patch.object(service, 'upload_file') as mock_upload, \
             patch.object(service, 'create_file') as mock_create, \
             patch.object(service, 'determine_file_type') as mock_determine:

            # Setup
            mock_upload.return_value = "/tmp/uploads/test_document.pdf"
            mock_determine.return_value = "application/pdf"
            mock_create.return_value = Mock()

            # Execute
            result = service.save_file(sample_upload_file, sample_collection_id, sample_user_id)

            # Verify
            assert result == "/tmp/uploads/test_document.pdf"
            mock_upload.assert_called_once_with(sample_user_id, sample_collection_id, b"PDF content here", "test_document.pdf")
            mock_determine.assert_called_once_with("test_document.pdf")
            mock_create.assert_called_once()

    def test_save_file_unknown_filename(self, service, sample_collection_id, sample_user_id):
        """Test file saving with unknown filename."""
        # Setup
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = None
        mock_file.file.read.return_value = b"Content"

        with patch.object(service, 'upload_file') as mock_upload, \
             patch.object(service, 'create_file') as mock_create, \
             patch.object(service, 'determine_file_type') as mock_determine:

            # Setup
            mock_upload.return_value = "/tmp/uploads/unknown"
            mock_determine.return_value = None
            mock_create.return_value = Mock()

            # Execute
            result = service.save_file(mock_file, sample_collection_id, sample_user_id)

            # Verify
            assert result == "/tmp/uploads/unknown"
            mock_upload.assert_called_once_with(sample_user_id, sample_collection_id, b"Content", "unknown")

    def test_get_files_by_collection_success(self, service, sample_collection_id, sample_file_output):
        """Test successful retrieval of files by collection."""
        # Setup
        service.file_repository.get_files_by_collection.return_value = [sample_file_output]

        # Execute
        result = service.get_files_by_collection(sample_collection_id)

        # Verify
        assert len(result) == 1
        assert result[0] == sample_file_output
        service.file_repository.get_files_by_collection.assert_called_once_with(sample_collection_id)

    def test_get_files_by_collection_empty(self, service, sample_collection_id):
        """Test retrieval of files by collection when no files exist."""
        # Setup
        service.file_repository.get_files_by_collection.return_value = []

        # Execute
        result = service.get_files_by_collection(sample_collection_id)

        # Verify
        assert result == []

    def test_logging_behavior(self, service, sample_file_input, sample_user_id, caplog):
        """Test that appropriate logging occurs."""
        # Setup
        service.file_repository.create.return_value = Mock()

        # Execute
        service.create_file(sample_file_input, sample_user_id)

        # Verify logging
        assert "Creating file record: test_document.pdf" in caplog.text
        assert "File record created successfully" in caplog.text
