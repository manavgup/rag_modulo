"""Document management commands for RAG CLI.

This module implements CLI commands for managing documents including
upload, listing, update, delete, and batch operations.
"""

from pathlib import Path
from typing import Any

from rag_solution.cli.client import RAGAPIClient
from rag_solution.cli.config import RAGConfig

from .base import BaseCommand, CommandResult


class DocumentCommands(BaseCommand):
    """Commands for document management operations.

    This class implements all document-related CLI commands,
    providing methods to interact with the documents API.
    """

    def __init__(self, api_client: RAGAPIClient, config: RAGConfig | None = None) -> None:
        """Initialize document commands.

        Args:
            api_client: HTTP API client instance
            config: Optional configuration settings
        """
        super().__init__(api_client, config)

    def list_documents(self, collection_id: str | None = None, status: str | None = None, limit: int = 50) -> CommandResult:
        """List documents in the system.

        Args:
            collection_id: Filter by collection
            status: Filter by document status
            limit: Maximum number of documents to return

        Returns:
            CommandResult with documents data
        """
        self._require_authentication()

        try:
            from typing import Any

            params: dict[str, Any] = {"limit": limit}
            if collection_id:
                params["collection_id"] = collection_id
            if status:
                params["status"] = status

            response = self.api_client.get("/api/files", params=params)

            return self._create_success_result(data=response, message=f"Found {response.get('total', 0)} documents")

        except Exception as e:
            return self._handle_api_error(e)

    def upload_document(self, file_path: str | Path, collection_id: str, metadata: dict[str, Any] | None = None) -> CommandResult:
        """Upload a document to a collection.

        Args:
            file_path: Path to the document file
            collection_id: Target collection ID
            metadata: Optional document metadata

        Returns:
            CommandResult with upload status
        """
        self._require_authentication()

        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return self._create_error_result(message=f"File not found: {file_path}", error_code="FILE_NOT_FOUND")

            data: dict[str, Any] = {"collection_id": collection_id}

            if metadata:
                data["metadata"] = metadata

            response = self.api_client.post_file("/api/files/upload", file_path, data=data)

            return self._create_success_result(data=response, message=f"Document '{file_path.name}' uploaded successfully")

        except Exception as e:
            return self._handle_api_error(e)

    def get_document(self, document_id: str) -> CommandResult:
        """Get document details.

        Args:
            document_id: Document identifier

        Returns:
            CommandResult with document details
        """
        self._require_authentication()

        try:
            response = self.api_client.get(f"/api/files/{document_id}")

            return self._create_success_result(data=response, message="Document details retrieved successfully")

        except Exception as e:
            return self._handle_api_error(e)

    def update_document(self, document_id: str, name: str | None = None, metadata: dict[str, Any] | None = None) -> CommandResult:
        """Update document details.

        Args:
            document_id: Document identifier
            name: New document name
            metadata: New document metadata

        Returns:
            CommandResult with updated document data
        """
        self._require_authentication()

        try:
            data: dict[str, Any] = {}
            if name:
                data["name"] = name
            if metadata:
                data["metadata"] = metadata

            if not data:
                return self._create_error_result(message="No updates provided", error_code="NO_UPDATES")

            response = self.api_client.put(f"/api/files/{document_id}", data=data)

            return self._create_success_result(data=response, message="Document updated successfully")

        except Exception as e:
            return self._handle_api_error(e)

    def delete_document(self, document_id: str, force: bool = False) -> CommandResult:
        """Delete a document.

        Args:
            document_id: Document identifier
            force: Force deletion without confirmation

        Returns:
            CommandResult with deletion status
        """
        self._require_authentication()

        try:
            params = {}
            if force:
                params["force"] = True

            response = self.api_client.delete(f"/api/files/{document_id}", params=params)

            return self._create_success_result(data=response, message="Document deleted successfully")

        except Exception as e:
            return self._handle_api_error(e)

    def batch_upload_documents(self, file_paths: list[str | Path], collection_id: str, parallel: bool = False) -> CommandResult:
        """Upload multiple documents in batch.

        Args:
            file_paths: List of file paths to upload
            collection_id: Target collection ID
            parallel: Whether to upload files in parallel

        Returns:
            CommandResult with batch upload results
        """
        self._require_authentication()

        try:
            # Validate all files exist
            valid_files = []
            for file_path in file_paths:
                path_obj = Path(file_path)
                if not path_obj.exists():
                    return self._create_error_result(message=f"File not found: {file_path}", error_code="FILE_NOT_FOUND")
                valid_files.append(path_obj)

            # TODO: Implement proper file handling for batch upload
            # files = [("files", (file_path.name, file_path.open("rb"))) for file_path in valid_files]

            data: dict[str, Any] = {"collection_id": collection_id, "parallel": parallel}
            # TODO: Implement proper batch file upload mechanism
            response = self.api_client.post("/api/files/batch-upload", data=data)

            uploaded_count = response.get("uploaded", 0)
            error_count = response.get("errors", 0)

            message = f"Uploaded {uploaded_count} documents"
            if error_count > 0:
                message += f" with {error_count} errors"

            return self._create_success_result(data=response, message=message)

        except Exception as e:
            return self._handle_api_error(e)

    def process_document(self, document_id: str, force_reprocess: bool = False) -> CommandResult:
        """Process or reprocess a document.

        Args:
            document_id: Document identifier
            force_reprocess: Force reprocessing even if already processed

        Returns:
            CommandResult with processing status
        """
        self._require_authentication()

        try:
            data = {"force_reprocess": force_reprocess}

            response = self.api_client.post(f"/api/files/{document_id}/process", data=data)

            return self._create_success_result(data=response, message="Document processing initiated successfully")

        except Exception as e:
            return self._handle_api_error(e)

    def get_processing_status(self, document_id: str) -> CommandResult:
        """Get document processing status.

        Args:
            document_id: Document identifier

        Returns:
            CommandResult with processing status
        """
        self._require_authentication()

        try:
            response = self.api_client.get(f"/api/files/{document_id}/status")

            return self._create_success_result(data=response, message="Processing status retrieved successfully")

        except Exception as e:
            return self._handle_api_error(e)

    def download_document(self, document_id: str, output_path: str | Path | None = None) -> CommandResult:
        """Download a document.

        Args:
            document_id: Document identifier
            output_path: Optional output file path

        Returns:
            CommandResult with download status
        """
        self._require_authentication()

        try:
            # TODO: Implement proper streaming download
            response = self.api_client.get(f"/api/files/{document_id}/download")

            # Determine output path
            if output_path:
                output_file = Path(output_path)
            else:
                # Use document name from headers if available
                filename = response.headers.get("Content-Disposition", "").split("filename=")[-1].strip('"')
                if not filename:
                    filename = f"document_{document_id}"
                output_file = Path(filename)

            # Write file content
            with output_file.open("wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return self._create_success_result(data={"file_path": str(output_file)}, message=f"Document downloaded to {output_file}")

        except Exception as e:
            return self._handle_api_error(e)

    def get_document_chunks(self, document_id: str, limit: int = 50) -> CommandResult:
        """Get chunks for a document.

        Args:
            document_id: Document identifier
            limit: Maximum number of chunks to return

        Returns:
            CommandResult with document chunks
        """
        self._require_authentication()

        try:
            params = {"limit": limit}

            response = self.api_client.get(f"/api/files/{document_id}/chunks", params=params)

            return self._create_success_result(data=response, message=f"Retrieved {len(response.get('chunks', []))} chunks")

        except Exception as e:
            return self._handle_api_error(e)
