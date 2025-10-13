"""Unit tests for file size calculation in repositories."""

import os
import tempfile
from unittest.mock import patch

from rag_solution.repository.collection_repository import CollectionRepository
from rag_solution.repository.file_repository import FileRepository


class TestFileSizeCalculation:
    """Test file size calculation methods in repositories."""

    def test_collection_repository_get_file_size_with_existing_file(self):
        """Test file size calculation with existing file."""
        # Create temporary file with known size
        with tempfile.NamedTemporaryFile(delete=False, mode="w") as temp_file:
            temp_file.write("Hello, World!")  # 13 bytes
            temp_file_path = temp_file.name

        try:
            # Test the file size calculation
            file_size = CollectionRepository._get_file_size(temp_file_path)
            assert file_size == 13
        finally:
            # Clean up
            os.unlink(temp_file_path)

    def test_collection_repository_get_file_size_with_missing_file(self):
        """Test file size calculation with missing file."""
        non_existent_path = "/path/to/nonexistent/file.txt"
        file_size = CollectionRepository._get_file_size(non_existent_path)
        assert file_size is None

    def test_collection_repository_get_file_size_with_none_path(self):
        """Test file size calculation with None path."""
        file_size = CollectionRepository._get_file_size(None)
        assert file_size is None

    def test_collection_repository_get_file_size_with_empty_path(self):
        """Test file size calculation with empty string path."""
        file_size = CollectionRepository._get_file_size("")
        assert file_size is None

    @patch("os.path.getsize")
    @patch("os.path.exists")
    def test_collection_repository_get_file_size_with_os_error(self, mock_exists, mock_getsize):
        """Test file size calculation when OS error occurs."""
        mock_exists.return_value = True
        mock_getsize.side_effect = OSError("Permission denied")

        file_size = CollectionRepository._get_file_size("/some/file.txt")
        assert file_size is None

    def test_file_repository_get_file_size_with_existing_file(self):
        """Test file size calculation with existing file."""
        # Create temporary file with known size
        with tempfile.NamedTemporaryFile(delete=False, mode="w") as temp_file:
            temp_file.write("Test content for file repository!")  # 33 characters
            temp_file_path = temp_file.name

        try:
            # Test the file size calculation
            file_size = FileRepository._get_file_size(temp_file_path)
            assert file_size == 33
        finally:
            # Clean up
            os.unlink(temp_file_path)

    def test_file_repository_get_file_size_with_missing_file(self):
        """Test file size calculation with missing file."""
        non_existent_path = "/path/to/nonexistent/file.txt"
        file_size = FileRepository._get_file_size(non_existent_path)
        assert file_size is None

    def test_file_repository_get_file_size_with_none_path(self):
        """Test file size calculation with None path."""
        file_size = FileRepository._get_file_size(None)
        assert file_size is None

    @patch("os.path.getsize")
    @patch("os.path.exists")
    def test_file_repository_get_file_size_with_os_error(self, mock_exists, mock_getsize):
        """Test file size calculation when OS error occurs."""
        mock_exists.return_value = True
        mock_getsize.side_effect = OSError("Permission denied")

        file_size = FileRepository._get_file_size("/some/file.txt")
        assert file_size is None
