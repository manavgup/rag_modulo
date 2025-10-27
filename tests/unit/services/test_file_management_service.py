"""
Comprehensive unit tests for FileManagementService.

This module tests the FileManagementService class functionality including
file CRUD operations, file upload/download, validation, and error handling.
Target: 70%+ line coverage with fully mocked dependencies.
"""

from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch
from uuid import uuid4

import pytest
from core.config import Settings
from rag_solution.core.exceptions import NotFoundError, ValidationError
from rag_solution.schemas.file_schema import FileInput, FileMetadata, FileOutput
from rag_solution.services.file_management_service import FileManagementService
from fastapi import UploadFile
from sqlalchemy.orm import Session


class TestFileManagementService:
    """Test cases for FileManagementService."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_settings(self):
        """Mock settings with file storage path."""
        settings = Mock(spec=Settings)
        settings.file_storage_path = "/tmp/test_storage"
        return settings

    @pytest.fixture
    def file_management_service(self, mock_db, mock_settings):
        """Create FileManagementService instance with mocked dependencies."""
        with patch("rag_solution.services.file_management_service.FileRepository") as MockFileRepository:
            service = FileManagementService(mock_db, mock_settings)
            # Store mock repository for easy access in tests
            service._mock_repository = MockFileRepository.return_value
            return service

    @pytest.fixture
    def sample_file_input(self):
        """Sample file input for testing."""
        collection_id = uuid4()
        return FileInput(
            collection_id=collection_id,
            filename="test_document.pdf",
            file_path="/path/to/test_document.pdf",
            file_type="application/pdf",
            metadata=FileMetadata(),
            document_id="doc_123"
        )

    @pytest.fixture
    def sample_file_output(self, sample_file_input):
        """Sample file output for testing."""
        return FileOutput(
            id=uuid4(),
            collection_id=sample_file_input.collection_id,
            filename=sample_file_input.filename,
            file_path=sample_file_input.file_path,
            file_type=sample_file_input.file_type,
            metadata=sample_file_input.metadata,
            document_id=sample_file_input.document_id,
            file_size_bytes=1024
        )

    @pytest.fixture
    def mock_upload_file(self):
        """Create a mock UploadFile for testing."""
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.pdf"
        mock_file.file = BytesIO(b"test file content")
        return mock_file

    # ============================================================================
    # SERVICE INITIALIZATION TESTS
    # ============================================================================

    @pytest.mark.unit
    def test_service_initialization(self, file_management_service, mock_db, mock_settings):
        """Test FileManagementService initialization."""
        assert file_management_service.file_repository is not None
        assert file_management_service.settings == mock_settings

    # ============================================================================
    # CREATE FILE TESTS
    # ============================================================================

    @pytest.mark.unit
    def test_create_file_success(self, file_management_service, sample_file_input, sample_file_output):
        """Test successful file record creation."""
        # Arrange
        user_id = uuid4()
        file_management_service.file_repository.create.return_value = sample_file_output

        # Act
        result = file_management_service.create_file(sample_file_input, user_id)

        # Assert
        assert result == sample_file_output
        file_management_service.file_repository.create.assert_called_once_with(sample_file_input, user_id)

    @pytest.mark.unit
    def test_create_file_repository_error(self, file_management_service, sample_file_input):
        """Test file creation when repository raises error."""
        # Arrange
        user_id = uuid4()
        file_management_service.file_repository.create.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            file_management_service.create_file(sample_file_input, user_id)

    # ============================================================================
    # GET FILE BY ID TESTS
    # ============================================================================

    @pytest.mark.unit
    def test_get_file_by_id_success(self, file_management_service, sample_file_output):
        """Test successful file retrieval by ID."""
        # Arrange
        file_id = sample_file_output.id
        file_management_service.file_repository.get.return_value = sample_file_output

        # Act
        result = file_management_service.get_file_by_id(file_id)

        # Assert
        assert result == sample_file_output
        file_management_service.file_repository.get.assert_called_once_with(file_id)

    @pytest.mark.unit
    def test_get_file_by_id_not_found(self, file_management_service):
        """Test file retrieval when file doesn't exist."""
        # Arrange
        file_id = uuid4()
        file_management_service.file_repository.get.side_effect = NotFoundError(
            resource_type="File",
            resource_id=str(file_id)
        )

        # Act & Assert
        with pytest.raises(NotFoundError, match="File not found"):
            file_management_service.get_file_by_id(file_id)

    # ============================================================================
    # GET FILE BY NAME TESTS
    # ============================================================================

    @pytest.mark.unit
    def test_get_file_by_name_success(self, file_management_service, sample_file_output):
        """Test successful file retrieval by name."""
        # Arrange
        collection_id = sample_file_output.collection_id
        filename = sample_file_output.filename
        file_management_service.file_repository.get_file_by_name.return_value = sample_file_output

        # Act
        result = file_management_service.get_file_by_name(collection_id, filename)

        # Assert
        assert result == sample_file_output
        file_management_service.file_repository.get_file_by_name.assert_called_once_with(collection_id, filename)

    @pytest.mark.unit
    def test_get_file_by_name_not_found(self, file_management_service):
        """Test file retrieval by name when file doesn't exist."""
        # Arrange
        collection_id = uuid4()
        filename = "nonexistent.pdf"
        file_management_service.file_repository.get_file_by_name.side_effect = NotFoundError(
            resource_type="File",
            identifier=f"{filename} in collection {collection_id}"
        )

        # Act & Assert
        with pytest.raises(NotFoundError):
            file_management_service.get_file_by_name(collection_id, filename)

    @pytest.mark.unit
    def test_get_file_by_name_unexpected_error(self, file_management_service):
        """Test file retrieval by name with unexpected error."""
        # Arrange
        collection_id = uuid4()
        filename = "test.pdf"
        file_management_service.file_repository.get_file_by_name.side_effect = RuntimeError("Database connection lost")

        # Act & Assert
        with pytest.raises(RuntimeError, match="Database connection lost"):
            file_management_service.get_file_by_name(collection_id, filename)

    # ============================================================================
    # UPDATE FILE TESTS
    # ============================================================================

    @pytest.mark.unit
    def test_update_file_success(self, file_management_service, sample_file_input, sample_file_output):
        """Test successful file update."""
        # Arrange
        file_id = sample_file_output.id
        file_management_service.file_repository.update.return_value = sample_file_output

        # Act
        result = file_management_service.update_file(file_id, sample_file_input)

        # Assert
        assert result == sample_file_output
        file_management_service.file_repository.update.assert_called_once_with(file_id, sample_file_input)

    @pytest.mark.unit
    def test_update_file_not_found(self, file_management_service, sample_file_input):
        """Test file update when file doesn't exist."""
        # Arrange
        file_id = uuid4()
        file_management_service.file_repository.update.side_effect = NotFoundError(
            resource_type="File",
            resource_id=str(file_id)
        )

        # Act & Assert
        with pytest.raises(NotFoundError, match="File not found"):
            file_management_service.update_file(file_id, sample_file_input)

    # ============================================================================
    # DELETE FILE TESTS
    # ============================================================================

    @pytest.mark.unit
    def test_delete_file_success_with_filesystem_cleanup(self, file_management_service, sample_file_output):
        """Test successful file deletion with filesystem cleanup."""
        # Arrange
        file_id = sample_file_output.id
        file_management_service.file_repository.get.return_value = sample_file_output

        # Mock Path.exists and Path.unlink
        with patch("rag_solution.services.file_management_service.Path") as MockPath:
            mock_path_instance = Mock()
            mock_path_instance.exists.return_value = True
            MockPath.return_value = mock_path_instance

            # Act
            file_management_service.delete_file(file_id)

            # Assert
            file_management_service.file_repository.get.assert_called_once_with(file_id)
            file_management_service.file_repository.delete.assert_called_once_with(file_id)
            mock_path_instance.exists.assert_called_once()
            mock_path_instance.unlink.assert_called_once()

    @pytest.mark.unit
    def test_delete_file_success_without_filesystem_file(self, file_management_service, sample_file_output):
        """Test successful file deletion when filesystem file doesn't exist."""
        # Arrange
        file_id = sample_file_output.id
        file_management_service.file_repository.get.return_value = sample_file_output

        # Mock Path.exists to return False
        with patch("rag_solution.services.file_management_service.Path") as MockPath:
            mock_path_instance = Mock()
            mock_path_instance.exists.return_value = False
            MockPath.return_value = mock_path_instance

            # Act
            file_management_service.delete_file(file_id)

            # Assert
            file_management_service.file_repository.delete.assert_called_once_with(file_id)
            mock_path_instance.unlink.assert_not_called()

    @pytest.mark.unit
    def test_delete_file_not_found(self, file_management_service):
        """Test file deletion when file doesn't exist."""
        # Arrange
        file_id = uuid4()
        file_management_service.file_repository.get.side_effect = NotFoundError(
            resource_type="File",
            resource_id=str(file_id)
        )

        # Act & Assert
        with pytest.raises(NotFoundError, match="File not found"):
            file_management_service.delete_file(file_id)

    @pytest.mark.unit
    def test_delete_file_with_none_file_path(self, file_management_service, sample_file_output):
        """Test file deletion when file_path is None."""
        # Arrange
        file_id = sample_file_output.id
        sample_file_output.file_path = None
        file_management_service.file_repository.get.return_value = sample_file_output

        # Act
        file_management_service.delete_file(file_id)

        # Assert - should not attempt filesystem operations
        file_management_service.file_repository.delete.assert_called_once_with(file_id)

    # ============================================================================
    # DELETE FILES (BULK) TESTS
    # ============================================================================

    @pytest.mark.unit
    def test_delete_files_success(self, file_management_service, sample_file_output):
        """Test successful bulk file deletion."""
        # Arrange
        collection_id = sample_file_output.collection_id
        filenames = ["file1.pdf", "file2.pdf"]

        file_management_service.file_repository.get_file_by_name.return_value = sample_file_output

        # Mock delete_file method
        file_management_service.delete_file = Mock()

        # Act
        result = file_management_service.delete_files(collection_id, filenames)

        # Assert
        assert result is True
        assert file_management_service.file_repository.get_file_by_name.call_count == 2
        assert file_management_service.delete_file.call_count == 2

    @pytest.mark.unit
    def test_delete_files_with_error(self, file_management_service):
        """Test bulk file deletion with error."""
        # Arrange
        collection_id = uuid4()
        filenames = ["file1.pdf"]
        file_management_service.file_repository.get_file_by_name.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            file_management_service.delete_files(collection_id, filenames)

    # ============================================================================
    # GET FILES BY COLLECTION TESTS
    # ============================================================================

    @pytest.mark.unit
    def test_get_files_by_collection_success(self, file_management_service, sample_file_output):
        """Test successful retrieval of files by collection."""
        # Arrange
        collection_id = sample_file_output.collection_id
        files = [sample_file_output, sample_file_output]
        file_management_service.file_repository.get_files.return_value = files

        # Act
        result = file_management_service.get_files_by_collection(collection_id)

        # Assert
        assert result == files
        assert len(result) == 2
        file_management_service.file_repository.get_files.assert_called_once_with(collection_id)

    @pytest.mark.unit
    def test_get_files_by_collection_empty(self, file_management_service):
        """Test retrieval of files when collection has no files."""
        # Arrange
        collection_id = uuid4()
        file_management_service.file_repository.get_files.return_value = []

        # Act
        result = file_management_service.get_files_by_collection(collection_id)

        # Assert
        assert result == []

    @pytest.mark.unit
    def test_get_files_by_collection_error(self, file_management_service):
        """Test file retrieval with error."""
        # Arrange
        collection_id = uuid4()
        file_management_service.file_repository.get_files.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            file_management_service.get_files_by_collection(collection_id)

    # ============================================================================
    # GET FILES (FILENAMES) TESTS
    # ============================================================================

    @pytest.mark.unit
    def test_get_files_success(self, file_management_service, sample_file_output):
        """Test successful retrieval of filenames."""
        # Arrange
        collection_id = sample_file_output.collection_id
        files = [sample_file_output]
        file_management_service.get_files_by_collection = Mock(return_value=files)

        # Act
        result = file_management_service.get_files(collection_id)

        # Assert
        assert result == [sample_file_output.filename]
        file_management_service.get_files_by_collection.assert_called_once_with(collection_id)

    @pytest.mark.unit
    def test_get_files_no_files_found(self, file_management_service):
        """Test filename retrieval when no files exist."""
        # Arrange
        collection_id = uuid4()
        file_management_service.get_files_by_collection = Mock(return_value=[])

        # Act & Assert
        with pytest.raises(NotFoundError, match="File not found"):
            file_management_service.get_files(collection_id)

    @pytest.mark.unit
    def test_get_files_filters_none_filenames(self, file_management_service):
        """Test that get_files filters out files with None filenames."""
        # Arrange
        collection_id = uuid4()
        file_with_name = FileOutput(
            id=uuid4(),
            collection_id=collection_id,
            filename="test.pdf",
            file_path="/path/test.pdf",
            file_type="application/pdf"
        )
        file_without_name = FileOutput(
            id=uuid4(),
            collection_id=collection_id,
            filename=None,
            file_path="/path/unknown",
            file_type="application/octet-stream"
        )
        files = [file_with_name, file_without_name]
        file_management_service.get_files_by_collection = Mock(return_value=files)

        # Act
        result = file_management_service.get_files(collection_id)

        # Assert
        assert result == ["test.pdf"]
        assert len(result) == 1

    @pytest.mark.unit
    def test_get_files_propagates_not_found_error(self, file_management_service):
        """Test that get_files propagates NotFoundError."""
        # Arrange
        collection_id = uuid4()
        file_management_service.get_files_by_collection = Mock(
            side_effect=NotFoundError(resource_type="File", resource_id=str(collection_id))
        )

        # Act & Assert
        with pytest.raises(NotFoundError):
            file_management_service.get_files(collection_id)

    @pytest.mark.unit
    def test_get_files_handles_unexpected_error(self, file_management_service):
        """Test get_files with unexpected error."""
        # Arrange
        collection_id = uuid4()
        file_management_service.get_files_by_collection = Mock(
            side_effect=RuntimeError("Unexpected error")
        )

        # Act & Assert
        with pytest.raises(RuntimeError, match="Unexpected error"):
            file_management_service.get_files(collection_id)

    # ============================================================================
    # UPLOAD FILE TESTS
    # ============================================================================

    @pytest.mark.unit
    def test_upload_file_success(self, file_management_service):
        """Test successful file upload to filesystem."""
        # Arrange
        user_id = uuid4()
        collection_id = uuid4()
        file_content = b"test file content"
        filename = "test.pdf"

        # Mock Path operations with proper path building
        with patch("rag_solution.services.file_management_service.Path") as MockPath:
            # Create mocks for the path chain
            mock_user_folder = MagicMock()
            mock_collection_folder = MagicMock()
            mock_file_path = MagicMock()

            # Set up the Path construction chain
            # First Path() call creates user folder
            # user_folder / collection_id creates collection folder
            # collection_folder / filename creates file path
            MockPath.return_value = mock_user_folder
            mock_user_folder.__truediv__.return_value = mock_collection_folder
            mock_collection_folder.__truediv__.return_value = mock_file_path

            # Mock file writing
            mock_file_handle = mock_open()
            mock_file_path.open = mock_file_handle

            # Act
            result = file_management_service.upload_file(user_id, collection_id, file_content, filename)

            # Assert
            assert result == mock_file_path
            mock_collection_folder.mkdir.assert_called_once_with(parents=True, exist_ok=True)
            mock_file_handle.assert_called_once_with("wb")

    @pytest.mark.unit
    def test_upload_file_settings_none_error(self, mock_db):
        """Test file upload when settings is None."""
        # Arrange
        service = FileManagementService(mock_db, None)
        user_id = uuid4()
        collection_id = uuid4()
        file_content = b"test"
        filename = "test.pdf"

        # Act & Assert
        with pytest.raises(ValueError, match="Settings must be provided"):
            service.upload_file(user_id, collection_id, file_content, filename)

    @pytest.mark.unit
    def test_upload_file_filesystem_error(self, file_management_service):
        """Test file upload with filesystem error."""
        # Arrange
        user_id = uuid4()
        collection_id = uuid4()
        file_content = b"test file content"
        filename = "test.pdf"

        # Mock Path to raise exception
        with patch("rag_solution.services.file_management_service.Path") as MockPath:
            MockPath.side_effect = OSError("Disk full")

            # Act & Assert
            with pytest.raises(OSError, match="Disk full"):
                file_management_service.upload_file(user_id, collection_id, file_content, filename)

    # ============================================================================
    # SAVE FILE TESTS
    # ============================================================================

    @pytest.mark.unit
    def test_save_file_success(self, file_management_service, mock_upload_file):
        """Test successful file save operation."""
        # Arrange
        collection_id = uuid4()
        user_id = uuid4()

        # Mock upload_file method
        file_management_service.upload_file = Mock(return_value=Path("/tmp/test.pdf"))

        # Mock create_file method
        mock_file_output = Mock(spec=FileOutput)
        file_management_service.create_file = Mock(return_value=mock_file_output)

        # Act
        result = file_management_service.save_file(mock_upload_file, collection_id, user_id)

        # Assert
        assert result == "/tmp/test.pdf"
        file_management_service.upload_file.assert_called_once()
        file_management_service.create_file.assert_called_once()

    @pytest.mark.unit
    def test_save_file_with_unknown_filename(self, file_management_service):
        """Test save file when filename is None."""
        # Arrange
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = None
        mock_file.file = BytesIO(b"content")
        collection_id = uuid4()
        user_id = uuid4()

        file_management_service.upload_file = Mock(return_value=Path("/tmp/unknown"))
        file_management_service.create_file = Mock(return_value=Mock())

        # Act
        result = file_management_service.save_file(mock_file, collection_id, user_id)

        # Assert
        assert result == "/tmp/unknown"
        # Verify create_file was called with "unknown" as filename
        call_args = file_management_service.create_file.call_args
        assert call_args[0][0].filename == "unknown"

    # ============================================================================
    # UPLOAD AND CREATE FILE RECORD TESTS
    # ============================================================================

    @pytest.mark.unit
    def test_upload_and_create_file_record_success(self, file_management_service, mock_upload_file):
        """Test successful upload and file record creation."""
        # Arrange
        user_id = uuid4()
        collection_id = uuid4()
        document_id = "doc_123"
        metadata = FileMetadata()

        file_management_service.upload_file = Mock(return_value=Path("/tmp/test.pdf"))
        mock_file_output = Mock(spec=FileOutput)
        file_management_service.create_file = Mock(return_value=mock_file_output)

        # Act
        result = file_management_service.upload_and_create_file_record(
            mock_upload_file, user_id, collection_id, document_id, metadata
        )

        # Assert
        assert result == mock_file_output
        file_management_service.upload_file.assert_called_once()
        file_management_service.create_file.assert_called_once()

    @pytest.mark.unit
    def test_upload_and_create_file_record_no_filename_error(self, file_management_service):
        """Test upload and create file record when filename is None."""
        # Arrange
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = None
        user_id = uuid4()
        collection_id = uuid4()
        document_id = "doc_123"

        # Act & Assert
        with pytest.raises(ValidationError, match="File name cannot be empty"):
            file_management_service.upload_and_create_file_record(
                mock_file, user_id, collection_id, document_id
            )

    @pytest.mark.unit
    def test_upload_and_create_file_record_upload_error(self, file_management_service, mock_upload_file):
        """Test upload and create file record with upload error."""
        # Arrange
        user_id = uuid4()
        collection_id = uuid4()
        document_id = "doc_123"

        file_management_service.upload_file = Mock(side_effect=OSError("Upload failed"))

        # Act & Assert
        with pytest.raises(OSError, match="Upload failed"):
            file_management_service.upload_and_create_file_record(
                mock_upload_file, user_id, collection_id, document_id
            )

    @pytest.mark.unit
    def test_upload_and_create_file_record_with_metadata(self, file_management_service, mock_upload_file):
        """Test upload and create file record with custom metadata."""
        # Arrange
        user_id = uuid4()
        collection_id = uuid4()
        document_id = "doc_123"
        metadata = FileMetadata()

        file_management_service.upload_file = Mock(return_value=Path("/tmp/test.pdf"))
        mock_file_output = Mock(spec=FileOutput)
        file_management_service.create_file = Mock(return_value=mock_file_output)

        # Act
        result = file_management_service.upload_and_create_file_record(
            mock_upload_file, user_id, collection_id, document_id, metadata
        )

        # Assert
        assert result == mock_file_output
        # Verify metadata was passed to create_file
        call_args = file_management_service.create_file.call_args
        assert call_args[0][0].metadata == metadata

    # ============================================================================
    # UPDATE FILE METADATA TESTS
    # ============================================================================

    @pytest.mark.unit
    def test_update_file_metadata_success(self, file_management_service, sample_file_output):
        """Test successful file metadata update."""
        # Arrange
        file_id = sample_file_output.id
        collection_id = sample_file_output.collection_id
        new_metadata = FileMetadata()

        file_management_service.file_repository.get.return_value = sample_file_output
        updated_output = sample_file_output
        updated_output.metadata = new_metadata
        file_management_service.file_repository.update.return_value = updated_output

        # Act
        result = file_management_service.update_file_metadata(collection_id, file_id, new_metadata)

        # Assert
        assert result == updated_output
        file_management_service.file_repository.get.assert_called_once_with(file_id)
        file_management_service.file_repository.update.assert_called_once()

    @pytest.mark.unit
    def test_update_file_metadata_wrong_collection(self, file_management_service, sample_file_output):
        """Test metadata update when file doesn't belong to collection."""
        # Arrange
        file_id = sample_file_output.id
        wrong_collection_id = uuid4()  # Different from sample_file_output.collection_id
        new_metadata = FileMetadata()

        file_management_service.file_repository.get.return_value = sample_file_output

        # Act & Assert
        with pytest.raises(ValidationError, match="File does not belong to collection"):
            file_management_service.update_file_metadata(wrong_collection_id, file_id, new_metadata)

    @pytest.mark.unit
    def test_update_file_metadata_file_not_found(self, file_management_service):
        """Test metadata update when file doesn't exist."""
        # Arrange
        file_id = uuid4()
        collection_id = uuid4()
        new_metadata = FileMetadata()

        file_management_service.file_repository.get.side_effect = NotFoundError(
            resource_type="File",
            resource_id=str(file_id)
        )

        # Act & Assert
        with pytest.raises(NotFoundError, match="File not found"):
            file_management_service.update_file_metadata(collection_id, file_id, new_metadata)

    # ============================================================================
    # DETERMINE FILE TYPE TESTS
    # ============================================================================

    @pytest.mark.unit
    def test_determine_file_type_pdf(self, file_management_service):
        """Test file type determination for PDF."""
        result = file_management_service.determine_file_type("document.pdf")
        assert result == "application/pdf"

    @pytest.mark.unit
    def test_determine_file_type_docx(self, file_management_service):
        """Test file type determination for DOCX."""
        result = file_management_service.determine_file_type("document.docx")
        assert result == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    @pytest.mark.unit
    def test_determine_file_type_txt(self, file_management_service):
        """Test file type determination for TXT."""
        result = file_management_service.determine_file_type("notes.txt")
        assert result == "text/plain"

    @pytest.mark.unit
    def test_determine_file_type_unknown(self, file_management_service):
        """Test file type determination for unknown extension."""
        result = file_management_service.determine_file_type("file.unknown")
        assert result == "application/octet-stream"

    @pytest.mark.unit
    def test_determine_file_type_no_extension(self, file_management_service):
        """Test file type determination for file without extension."""
        result = file_management_service.determine_file_type("filename")
        assert result == "application/octet-stream"

    # ============================================================================
    # GET FILE PATH TESTS
    # ============================================================================

    @pytest.mark.unit
    def test_get_file_path_success(self, file_management_service, sample_file_output, mock_settings):
        """Test successful file path retrieval."""
        # Arrange
        collection_id = sample_file_output.collection_id
        filename = sample_file_output.filename

        # Update file path to be within storage root for security check
        file_path_within_storage = Path(mock_settings.file_storage_path) / "test_document.pdf"
        sample_file_output.file_path = str(file_path_within_storage)

        # Mock the repository method, not the service method
        file_management_service.file_repository.get_file_by_name = Mock(return_value=sample_file_output)

        # Act
        result = file_management_service.get_file_path(collection_id, filename)

        # Assert
        assert result == file_path_within_storage.resolve()
        file_management_service.file_repository.get_file_by_name.assert_called_once_with(collection_id, filename)

    @pytest.mark.unit
    def test_get_file_path_no_path_error(self, file_management_service, sample_file_output):
        """Test file path retrieval when file has no path."""
        # Arrange
        collection_id = sample_file_output.collection_id
        filename = sample_file_output.filename
        sample_file_output.file_path = None
        file_management_service.get_file_by_name = Mock(return_value=sample_file_output)

        # Act & Assert
        with pytest.raises(ValueError, match="has no file path"):
            file_management_service.get_file_path(collection_id, filename)

    @pytest.mark.unit
    def test_get_file_path_file_not_found(self, file_management_service):
        """Test file path retrieval when file doesn't exist."""
        # Arrange
        collection_id = uuid4()
        filename = "nonexistent.pdf"
        file_management_service.get_file_by_name = Mock(
            side_effect=NotFoundError(resource_type="File", identifier=filename)
        )

        # Act & Assert
        with pytest.raises(NotFoundError):
            file_management_service.get_file_path(collection_id, filename)

    @pytest.mark.unit
    def test_get_file_path_unexpected_error(self, file_management_service):
        """Test file path retrieval with unexpected error."""
        # Arrange
        collection_id = uuid4()
        filename = "test.pdf"
        file_management_service.get_file_by_name = Mock(
            side_effect=RuntimeError("Unexpected error")
        )

        # Act & Assert
        with pytest.raises(RuntimeError, match="Unexpected error"):
            file_management_service.get_file_path(collection_id, filename)
