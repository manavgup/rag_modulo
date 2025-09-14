"""Authentication management for RAG CLI.

This module handles JWT token management, profile-based authentication,
and session management for the CLI application.
"""

import contextlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .exceptions import AuthenticationError


class AuthResult(BaseModel):
    """Result of an authentication operation.

    This model represents the outcome of authentication attempts,
    providing structured information about success/failure and
    associated data.

    Attributes:
        success: Whether authentication was successful
        token: JWT token if authentication succeeded
        message: Human-readable message about the result
        error_code: Machine-readable error code if failed
        user_info: User information if authentication succeeded
    """

    success: bool = Field(description="Whether authentication was successful")
    token: str | None = Field(default=None, description="JWT token if successful")
    message: str = Field(description="Human-readable result message")
    error_code: str | None = Field(default=None, description="Error code if failed")
    user_info: dict[str, Any] | None = Field(default=None, description="User information if successful")

    model_config = {"str_strip_whitespace": True, "extra": "forbid"}


class TokenData(BaseModel):
    """JWT token data structure.

    This model represents stored token information including
    the token itself, expiration, and metadata.

    Attributes:
        token: The JWT token string
        expires_at: Token expiration timestamp
        profile: Profile name this token belongs to
        created_at: When the token was stored
        user_info: Associated user information
    """

    token: str = Field(description="JWT token string")
    expires_at: datetime = Field(description="Token expiration timestamp")
    profile: str = Field(description="Profile name")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    user_info: dict[str, Any] | None = Field(default=None, description="User information")

    model_config = {"str_strip_whitespace": True, "extra": "forbid"}


class AuthManager:
    """Authentication manager for CLI operations.

    This class handles JWT token storage, validation, and management
    for different CLI profiles. It provides methods for login, logout,
    and token validation.
    """

    def __init__(self, profile: str = "default") -> None:
        """Initialize the AuthManager.

        Args:
            profile: Profile name for authentication context
        """
        self.profile = profile
        self.config_dir = Path.home() / ".rag-cli"
        self.tokens_dir = self.config_dir / "tokens"
        self.tokens_dir.mkdir(parents=True, exist_ok=True)
        self.token_file = self.tokens_dir / f"{profile}.json"

    def create_token_data(self, token: str, expires_at: datetime, user_info: dict[str, Any] | None = None) -> dict[str, Any]:
        """Create token data structure.

        Args:
            token: JWT token string
            expires_at: Token expiration timestamp
            user_info: Optional user information

        Returns:
            Dictionary containing token data
        """
        token_data = TokenData(token=token, expires_at=expires_at, profile=self.profile, user_info=user_info)
        return token_data.model_dump()

    def save_token(self, token: str, expires_at: datetime, user_info: dict[str, Any] | None = None) -> None:
        """Save authentication token to file.

        Args:
            token: JWT token string
            expires_at: Token expiration timestamp
            user_info: Optional user information

        Raises:
            AuthenticationError: If token save fails
        """
        try:
            token_data = self.create_token_data(token, expires_at, user_info)
            self.token_file.write_text(json.dumps(token_data, indent=2, default=str), encoding="utf-8")
        except Exception as e:
            raise AuthenticationError(f"Failed to save authentication token: {e!s}") from e

    def load_token(self) -> TokenData | None:
        """Load authentication token from file.

        Returns:
            TokenData if token exists and is valid, None otherwise
        """
        if not self.token_file.exists():
            return None

        try:
            token_text = self.token_file.read_text(encoding="utf-8")
            token_dict = json.loads(token_text)

            # Convert datetime strings back to datetime objects
            if "expires_at" in token_dict:
                token_dict["expires_at"] = datetime.fromisoformat(token_dict["expires_at"].replace("Z", "+00:00"))
            if "created_at" in token_dict:
                token_dict["created_at"] = datetime.fromisoformat(token_dict["created_at"].replace("Z", "+00:00"))

            return TokenData(**token_dict)
        except (json.JSONDecodeError, ValueError, KeyError, TypeError):
            # Invalid token file, remove it
            with contextlib.suppress(Exception):
                self.token_file.unlink()
            return None

    def is_token_valid(self, token: str, expires_at: datetime) -> bool:
        """Check if a token is valid and not expired.

        Args:
            token: JWT token string
            expires_at: Token expiration timestamp

        Returns:
            True if token is valid and not expired
        """
        if not token or not expires_at:
            return False

        # Check if token is expired (with 10-minute buffer)
        now = datetime.now()
        buffer = timedelta(minutes=10)

        return not expires_at <= now + buffer

    def get_current_token(self) -> str | None:
        """Get current valid authentication token.

        Returns:
            Valid JWT token string or None if no valid token exists
        """
        token_data = self.load_token()
        if not token_data:
            return None

        if not self.is_token_valid(token_data.token, token_data.expires_at):
            # Token is expired, remove it
            self.remove_token()
            return None

        return token_data.token

    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated.

        Returns:
            True if user has a valid authentication token
        """
        return self.get_current_token() is not None

    def remove_token(self) -> None:
        """Remove stored authentication token.

        This method is called during logout or when tokens expire.
        """
        if self.token_file.exists():
            with contextlib.suppress(Exception):
                self.token_file.unlink()

    def generate_auth_headers(self, token: str) -> dict[str, str]:
        """Generate HTTP headers for authenticated requests.

        Args:
            token: JWT authentication token

        Returns:
            Dictionary of HTTP headers including Authorization
        """
        return {"Authorization": f"Bearer {token}"}

    def extract_token_info(self, response_data: dict[str, Any]) -> dict[str, Any]:
        """Extract token information from API response.

        Args:
            response_data: API response containing token information

        Returns:
            Dictionary containing extracted token information
        """
        return {
            "token": response_data.get("access_token", ""),
            "token_type": response_data.get("token_type", "Bearer"),
            "expires_in": response_data.get("expires_in", 3600),
            "user": response_data.get("user", {}),
        }

    def get_user_info(self) -> dict[str, Any] | None:
        """Get user information from stored token data.

        Returns:
            User information dictionary or None if not available
        """
        token_data = self.load_token()
        if token_data and self.is_token_valid(token_data.token, token_data.expires_at):
            return token_data.user_info
        return None


class LoginWorkflow:
    """Workflow manager for login operations.

    This class defines the steps required for a complete login workflow
    and provides methods to validate and execute the login process.
    """

    @staticmethod
    def get_required_steps() -> list[str]:
        """Get the required steps for login workflow.

        Returns:
            List of required login steps
        """
        return ["validate_credentials", "authenticate_with_api", "extract_token", "save_token", "update_profile"]

    @staticmethod
    def validate_workflow_data(data: dict[str, Any]) -> bool:
        """Validate workflow data structure.

        Args:
            data: Workflow data to validate

        Returns:
            True if data is valid
        """
        required_fields = ["credentials", "api_endpoint", "token_field"]
        return all(field in data for field in required_fields)

    @staticmethod
    def get_workflow_status() -> str:
        """Get current workflow status.

        Returns:
            Current workflow status string
        """
        return "ready"


class LogoutWorkflow:
    """Workflow manager for logout operations.

    This class defines the steps required for a complete logout workflow
    and provides methods to validate and execute the logout process.
    """

    @staticmethod
    def get_required_steps() -> list[str]:
        """Get the required steps for logout workflow.

        Returns:
            List of required logout steps
        """
        return ["validate_token_exists", "revoke_token_with_api", "remove_local_token", "update_profile_status"]

    @staticmethod
    def validate_logout_data(data: dict[str, Any]) -> bool:
        """Validate logout data structure.

        Args:
            data: Logout data to validate

        Returns:
            True if data is valid
        """
        return "token" in data and "api_endpoint" in data

    @staticmethod
    def get_logout_status() -> str:
        """Get current logout workflow status.

        Returns:
            Current logout status string
        """
        return "ready"


class CredentialValidator:
    """Validator for user credentials.

    This class provides validation methods for different types
    of user credentials including email and password validation.
    """

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email format.

        Args:
            email: Email address to validate

        Returns:
            True if email format is valid
        """
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(email_pattern, email))

    @staticmethod
    def is_valid_password(password: str) -> bool:
        """Validate password format.

        Args:
            password: Password to validate

        Returns:
            True if password meets minimum requirements
        """
        # Basic password validation - minimum length
        return len(password) >= 8


class SessionManager:
    """Manager for CLI session data.

    This class handles session-related operations including
    session creation, validation, and cleanup.
    """

    def create_session(self, user_id: str, token: str) -> dict[str, Any]:
        """Create a new CLI session.

        Args:
            user_id: User identifier
            token: Authentication token

        Returns:
            Dictionary containing session data
        """
        now = datetime.now()
        return {
            "user_id": user_id,
            "token": token,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=24)).isoformat(),
        }

    def validate_session(self, session_data: dict[str, Any]) -> bool:
        """Validate session data.

        Args:
            session_data: Session data to validate

        Returns:
            True if session is valid
        """
        required_fields = ["user_id", "token", "created_at", "expires_at"]
        return all(field in session_data for field in required_fields)

    def is_session_expired(self, session_data: dict[str, Any]) -> bool:
        """Check if session is expired.

        Args:
            session_data: Session data to check

        Returns:
            True if session is expired
        """
        try:
            expires_at = datetime.fromisoformat(session_data["expires_at"])
            return datetime.now() >= expires_at
        except (KeyError, ValueError):
            return True


class TokenRefreshManager:
    """Manager for token refresh operations.

    This class handles automatic token refresh logic
    and determines when tokens need to be refreshed.
    """

    def needs_refresh(self, expires_at: datetime) -> bool:
        """Check if token needs to be refreshed.

        Args:
            expires_at: Token expiration timestamp

        Returns:
            True if token should be refreshed
        """
        now = datetime.now()
        # Refresh if less than 30 minutes remaining
        refresh_threshold = timedelta(minutes=30)

        return expires_at <= (now + refresh_threshold)

    def get_refresh_threshold(self) -> timedelta:
        """Get the refresh threshold duration.

        Returns:
            Refresh threshold as timedelta
        """
        return timedelta(minutes=30)

    def calculate_refresh_time(self, expires_at: datetime) -> datetime:
        """Calculate when token should be refreshed.

        Args:
            expires_at: Token expiration timestamp

        Returns:
            When token should be refreshed
        """
        return expires_at - self.get_refresh_threshold()


class MultiProfileAuthManager:
    """Manager for authentication across multiple profiles.

    This class provides methods to manage authentication state
    across different CLI profiles.
    """

    def __init__(self) -> None:
        """Initialize the MultiProfileAuthManager."""
        self.profile_auth_state: dict[str, bool] = {}
        self.profile_tokens: dict[str, str | None] = {}

    def set_authenticated(self, profile: str, is_auth: bool, token: str | None = None) -> None:
        """Set authentication state for a profile.

        Args:
            profile: Profile name
            is_auth: Whether profile is authenticated
            token: Authentication token if authenticated
        """
        self.profile_auth_state[profile] = is_auth
        self.profile_tokens[profile] = token

    def is_authenticated(self, profile: str) -> bool:
        """Check if a profile is authenticated.

        Args:
            profile: Profile name

        Returns:
            True if profile is authenticated
        """
        return self.profile_auth_state.get(profile, False)

    def get_token(self, profile: str) -> str | None:
        """Get authentication token for a profile.

        Args:
            profile: Profile name

        Returns:
            Authentication token or None
        """
        return self.profile_tokens.get(profile)
