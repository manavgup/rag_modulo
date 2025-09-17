"""Collection management commands for RAG CLI.

This module implements CLI commands for managing document collections,
including creation, listing, updating, sharing, and deletion operations.
"""

from typing import Any

from rag_solution.cli.client import RAGAPIClient
from rag_solution.cli.config import RAGConfig
from rag_solution.cli.exceptions import APIError, AuthenticationError, RAGCLIError

from .base import BaseCommand, CommandResult


class CollectionCommands(BaseCommand):
    """Commands for collection management operations.

    This class implements all collection-related CLI commands,
    providing methods to interact with the collections API.
    """

    def __init__(self, api_client: RAGAPIClient, config: RAGConfig | None = None) -> None:
        """Initialize collection commands.

        Args:
            api_client: HTTP API client instance
            config: Optional configuration settings
        """
        super().__init__(api_client, config)

    def list_collections(
        self, private_only: bool = False, shared_only: bool = False, team: str | None = None
    ) -> CommandResult:
        """List available collections.

        Args:
            private_only: Show only private collections
            shared_only: Show only shared collections
            team: Filter by team name

        Returns:
            CommandResult with collections data
        """
        self._require_authentication()

        try:
            params: dict[str, Any] = {}
            if private_only:
                params["private"] = True
            if shared_only:
                params["shared"] = True
            if team:
                params["team"] = team

            response = self.api_client.get("/api/collections", params=params)

            # Handle both list and dict response formats
            if isinstance(response, list):
                total_count = len(response)
                # Wrap list in dict for CommandResult compatibility
                result_data = {"collections": response, "total": total_count}
            else:
                total_count = response.get("total", len(response.get("collections", [])))
                result_data = response

            return self._create_success_result(
                data=result_data,
                message=f"Found {total_count} collections",
            )

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def create_collection(
        self, name: str, description: str | None = None, vector_db: str = "milvus", is_private: bool = False
    ) -> CommandResult:
        """Create a new collection.

        Args:
            name: Collection name
            description: Optional collection description
            vector_db: Vector database to use
            is_private: Whether collection is private

        Returns:
            CommandResult with created collection data
        """
        self._require_authentication()

        try:
            # Use the correct schema format expected by CollectionInput
            data = {
                "name": name,
                "is_private": is_private,
                "users": [],  # Will be populated by the server with current user
                "status": "created",
            }

            # Note: vector_db is handled by the server/service layer, not in the input schema
            # The description field is not part of CollectionInput schema currently
            # These parameters are kept for API compatibility but not used in current implementation
            _ = description  # Suppress unused parameter warning
            _ = vector_db  # Suppress unused parameter warning

            response = self.api_client.post("/api/collections", data=data)

            return self._create_success_result(data=response, message=f"Collection '{name}' created successfully")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def create_collection_with_documents(self, name: str, files: list[str], is_private: bool = False) -> CommandResult:
        """Create a new collection with documents.

        This method calls the create_collection_with_documents endpoint which:
        - Creates the collection
        - Uploads the provided files
        - Triggers background document processing
        - Processes documents into vector store

        Args:
            name: Collection name
            files: List of file paths to upload
            is_private: Whether collection is private

        Returns:
            CommandResult with created collection data
        """
        self._require_authentication()

        try:
            import os

            # Prepare form data
            form_data = {"collection_name": name, "is_private": str(is_private).lower()}

            # Prepare files for upload
            file_objects = []
            try:
                for file_path in files:
                    if not os.path.exists(file_path):
                        return self._create_error_result(f"File not found: {file_path}")

                    with open(file_path, "rb") as file_obj:
                        file_objects.append(
                            ("files", (os.path.basename(file_path), file_obj.read(), "application/octet-stream"))
                        )

                # Use the API client's session to make form-data request
                response = self.api_client.session.post(
                    f"{self.api_client.config.api_url}/api/collections",
                    data=form_data,
                    files=file_objects,
                    timeout=120,  # Longer timeout for file uploads
                )

                response.raise_for_status()
                result_data = response.json()

                return self._create_success_result(
                    data=result_data,
                    message=f"Collection '{name}' created with {len(files)} documents. Processing started in background.",
                )

            finally:
                # Files are now read into memory, no need to close them
                pass

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)
        except Exception as e:
            return self._create_error_result(f"Failed to create collection with documents: {e!s}")

    def get_collection(self, collection_id: str, include_stats: bool = False) -> CommandResult:
        """Get collection details.

        Args:
            collection_id: Collection identifier
            include_stats: Include collection statistics

        Returns:
            CommandResult with collection details
        """
        self._require_authentication()

        try:
            params = {}
            if include_stats:
                params["include_stats"] = True

            response = self.api_client.get(f"/api/collections/{collection_id}", params=params)

            return self._create_success_result(data=response, message="Collection details retrieved successfully")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def get_collection_status(self, collection_id: str) -> CommandResult:
        """Get collection processing status.

        Args:
            collection_id: Collection identifier

        Returns:
            CommandResult with collection status information
        """
        self._require_authentication()

        try:
            response = self.api_client.get(f"/api/collections/{collection_id}")

            # Extract just the status information
            status_data = {
                "id": response.get("id"),
                "status": response.get("status"),
                "name": response.get("name"),
                "message": response.get("message", ""),
            }

            return self._create_success_result(
                data=status_data, message=f"Collection status: {status_data.get('status', 'unknown')}"
            )

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def update_collection(
        self, collection_id: str, name: str | None = None, description: str | None = None
    ) -> CommandResult:
        """Update collection details.

        Args:
            collection_id: Collection identifier
            name: New collection name
            description: New collection description

        Returns:
            CommandResult with updated collection data
        """
        self._require_authentication()

        try:
            data = {}
            if name:
                data["name"] = name
            if description is not None:  # Allow empty string
                data["description"] = description

            if not data:
                return self._create_error_result(message="No updates provided", error_code="NO_UPDATES")

            response = self.api_client.put(f"/api/collections/{collection_id}", data=data)

            return self._create_success_result(data=response, message="Collection updated successfully")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def delete_collection(self, collection_id: str, force: bool = False) -> CommandResult:
        """Delete a collection.

        Args:
            collection_id: Collection identifier
            force: Force deletion without confirmation

        Returns:
            CommandResult with deletion status
        """
        self._require_authentication()

        # Check for dry-run mode
        if self._is_dry_run():
            return self._create_dry_run_result(
                f"delete collection {collection_id}", {"collection_id": collection_id, "force": force}
            )

        try:
            params = {}
            if force:
                params["force"] = True

            response = self.api_client.delete(f"/api/collections/{collection_id}", params=params)

            return self._create_success_result(data=response, message="Collection deleted successfully")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def share_collection(self, collection_id: str, user_email: str, permission: str = "read") -> CommandResult:
        """Share collection with a user.

        Args:
            collection_id: Collection identifier
            user_email: Email of user to share with
            permission: Permission level (read/write)

        Returns:
            CommandResult with sharing status
        """
        self._require_authentication()

        try:
            data = {"user_email": user_email, "permission": permission}

            response = self.api_client.post(f"/api/collections/{collection_id}/share", data=data)

            return self._create_success_result(data=response, message=f"Collection shared with {user_email}")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def list_collection_shares(self, collection_id: str) -> CommandResult:
        """List collection sharing permissions.

        Args:
            collection_id: Collection identifier

        Returns:
            CommandResult with sharing information
        """
        self._require_authentication()

        try:
            response = self.api_client.get(f"/api/collections/{collection_id}/shares")

            return self._create_success_result(data=response, message="Collection sharing information retrieved")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def update_collection_share(self, share_id: str, permission: str) -> CommandResult:
        """Update collection sharing permission.

        Args:
            share_id: Share record identifier
            permission: New permission level

        Returns:
            CommandResult with updated sharing data
        """
        self._require_authentication()

        try:
            data = {"permission": permission}

            response = self.api_client.put(f"/api/collection-shares/{share_id}", data=data)

            return self._create_success_result(data=response, message="Sharing permission updated successfully")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def remove_collection_share(self, share_id: str) -> CommandResult:
        """Remove collection sharing.

        Args:
            share_id: Share record identifier

        Returns:
            CommandResult with removal status
        """
        self._require_authentication()

        try:
            response = self.api_client.delete(f"/api/collection-shares/{share_id}")

            return self._create_success_result(data=response, message="Collection sharing removed successfully")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)
