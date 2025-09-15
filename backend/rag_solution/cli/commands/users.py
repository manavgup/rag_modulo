"""User management commands for RAG CLI.

This module implements CLI commands for managing users including
creation, listing, updating, and batch operations.
"""

from typing import Any

from rag_solution.cli.client import RAGAPIClient
from rag_solution.cli.config import RAGConfig
from rag_solution.cli.exceptions import APIError, AuthenticationError, RAGCLIError

from .base import BaseCommand, CommandResult


class UserCommands(BaseCommand):
    """Commands for user management operations.

    This class implements all user-related CLI commands,
    providing methods to interact with the users API.
    """

    def __init__(self, api_client: RAGAPIClient, config: RAGConfig | None = None) -> None:
        """Initialize user commands.

        Args:
            api_client: HTTP API client instance
            config: Optional configuration settings
        """
        super().__init__(api_client, config)

    def list_users(self, role: str | None = None, team: str | None = None, active_only: bool = False) -> CommandResult:
        """List users in the system.

        Args:
            role: Filter by user role
            team: Filter by team membership
            active_only: Show only active users

        Returns:
            CommandResult with users data
        """
        self._require_authentication()

        try:
            params: dict[str, Any] = {}
            if role:
                params["role"] = role
            if team:
                params["team"] = team
            if active_only:
                params["active"] = True

            response = self.api_client.get("/api/users", params=params)

            return self._create_success_result(data=response, message=f"Found {response.get('total', 0)} users")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def create_user(self, email: str, name: str, role: str = "user", teams: list[str] | None = None) -> CommandResult:
        """Create a new user.

        Args:
            email: User email address
            name: User full name
            role: User role (user/admin)
            teams: Optional list of team assignments

        Returns:
            CommandResult with created user data
        """
        self._require_authentication()

        try:
            data: dict[str, Any] = {"email": email, "name": name, "role": role}

            if teams:
                data["teams"] = teams

            response = self.api_client.post("/api/users", data=data)

            return self._create_success_result(data=response, message=f"User '{email}' created successfully")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def get_user(self, user_identifier: str) -> CommandResult:
        """Get user details.

        Args:
            user_identifier: User ID or email address

        Returns:
            CommandResult with user details
        """
        self._require_authentication()

        try:
            # Check if identifier looks like an email
            endpoint = (
                f"/api/users/by-email/{user_identifier}" if "@" in user_identifier else f"/api/users/{user_identifier}"
            )

            response = self.api_client.get(endpoint)

            return self._create_success_result(data=response, message="User details retrieved successfully")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def update_user(
        self, user_id: str, name: str | None = None, role: str | None = None, active: bool | None = None
    ) -> CommandResult:
        """Update user details.

        Args:
            user_id: User identifier
            name: New user name
            role: New user role
            active: New active status

        Returns:
            CommandResult with updated user data
        """
        self._require_authentication()

        try:
            data: dict[str, Any] = {}
            if name:
                data["name"] = name
            if role:
                data["role"] = role
            if active is not None:
                data["active"] = active

            if not data:
                return self._create_error_result(message="No updates provided", error_code="NO_UPDATES")

            response = self.api_client.put(f"/api/users/{user_id}", data=data)

            return self._create_success_result(data=response, message="User updated successfully")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def delete_user(self, user_id: str, force: bool = False) -> CommandResult:
        """Delete a user.

        Args:
            user_id: User identifier
            force: Force deletion without confirmation

        Returns:
            CommandResult with deletion status
        """
        self._require_authentication()

        # Check for dry-run mode
        if self._is_dry_run():
            return self._create_dry_run_result(f"delete user {user_id}", {"user_id": user_id, "force": force})

        try:
            params: dict[str, Any] = {}
            if force:
                params["force"] = True

            response = self.api_client.delete(f"/api/users/{user_id}", params=params)

            return self._create_success_result(data=response, message="User deleted successfully")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def get_current_user(self) -> CommandResult:
        """Get current authenticated user details.

        Returns:
            CommandResult with current user data
        """
        self._require_authentication()

        try:
            response = self.api_client.get("/api/users/me")

            return self._create_success_result(data=response, message="Current user details retrieved")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def import_users(
        self, users_data: dict[str, Any], conflict_resolution: str = "skip", dry_run: bool = False
    ) -> CommandResult:
        """Import multiple users from data.

        Args:
            users_data: Dictionary containing users to import
            conflict_resolution: How to handle existing users (skip/update/error)
            dry_run: Only validate without importing

        Returns:
            CommandResult with import results
        """
        self._require_authentication()

        try:
            data = {**users_data}
            if conflict_resolution != "skip":
                data["conflict_resolution"] = conflict_resolution
            if dry_run:
                data["dry_run"] = True

            response = self.api_client.post("/api/users/import", data=data)

            imported_count = response.get("imported", 0)
            error_count = response.get("errors", 0)

            if dry_run:
                message = f"Would import {response.get('would_import', 0)} users"
            else:
                message = f"Imported {imported_count} users"
                if error_count > 0:
                    message += f" with {error_count} errors"

            return self._create_success_result(data=response, message=message)

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def export_users(
        self, include_inactive: bool = False, teams: list[str] | None = None, roles: list[str] | None = None
    ) -> CommandResult:
        """Export users data.

        Args:
            include_inactive: Include inactive users in export
            teams: Filter by specific teams
            roles: Filter by specific roles

        Returns:
            CommandResult with exported users data
        """
        self._require_authentication()

        try:
            params: dict[str, Any] = {}
            if include_inactive:
                params["include_inactive"] = True
            if teams:
                params["teams"] = teams
            if roles:
                params["roles"] = roles

            response = self.api_client.get("/api/users/export", params=params)

            return self._create_success_result(
                data=response, message=f"Exported {response.get('total_count', 0)} users"
            )

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def batch_delete_users(self, user_ids: list[str]) -> CommandResult:
        """Delete multiple users in batch.

        Args:
            user_ids: List of user identifiers to delete

        Returns:
            CommandResult with batch deletion results
        """
        self._require_authentication()

        try:
            data = {"user_ids": user_ids}

            response = self.api_client.post("/api/users/batch/delete", data=data)

            deleted_count = response.get("deleted", 0)
            error_count = response.get("errors", 0)

            message = f"Deleted {deleted_count} users"
            if error_count > 0:
                message += f" with {error_count} errors"

            return self._create_success_result(data=response, message=message)

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def batch_update_users(self, updates: list[dict[str, Any]]) -> CommandResult:
        """Update multiple users in batch.

        Args:
            updates: List of user update dictionaries

        Returns:
            CommandResult with batch update results
        """
        self._require_authentication()

        try:
            data = {"updates": updates}

            response = self.api_client.put("/api/users/batch", data=data)

            updated_count = response.get("updated", 0)
            error_count = response.get("errors", 0)

            message = f"Updated {updated_count} users"
            if error_count > 0:
                message += f" with {error_count} errors"

            return self._create_success_result(data=response, message=message)

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)
