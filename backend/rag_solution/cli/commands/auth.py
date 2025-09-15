"""Authentication commands for RAG CLI.

This module implements CLI commands for authentication operations,
including login, logout, and profile management.
"""

from getpass import getpass

from rag_solution.cli.client import RAGAPIClient
from rag_solution.cli.config import RAGConfig
from rag_solution.cli.exceptions import AuthenticationError

from .base import BaseCommand, CommandResult


class AuthCommands(BaseCommand):
    """Commands for authentication operations.

    This class implements authentication-related CLI commands,
    providing methods for login, logout, and status checking.
    """

    def __init__(self, api_client: RAGAPIClient, config: RAGConfig | None = None) -> None:
        """Initialize authentication commands.

        Args:
            api_client: HTTP API client instance
            config: Optional configuration settings
        """
        super().__init__(api_client, config)

    def login(
        self,
        username: str | None = None,
        password: str | None = None,
        provider: str = "local",
        interactive: bool = True,
    ) -> CommandResult:
        """Login to RAG Modulo.

        Args:
            username: Username/email for login
            password: Password for login
            provider: Authentication provider (local, ibm, etc.)
            interactive: Whether to prompt for missing credentials

        Returns:
            CommandResult with authentication status
        """
        try:
            # Handle IBM OIDC authentication
            if provider == "ibm":
                return self._handle_oidc_login(provider, username)

            # Handle local authentication
            if interactive and not username:
                username = input("Username/Email: ")

            if not username:
                return self._create_error_result(message="Username is required", error_code="MISSING_USERNAME")

            if interactive and not password:
                password = getpass("Password: ")

            if not password:
                return self._create_error_result(message="Password is required", error_code="MISSING_PASSWORD")

            # Make login request
            response = self.api_client.post("/api/auth/login", data={"username": username, "password": password})

            # Extract token and save it
            if "access_token" in response:
                token = response["access_token"]
                expires_at = response.get("expires_at")

                # Save token to auth manager
                self.api_client.set_auth_token(token, expires_at)

                return self._create_success_result(
                    data={"username": username, "authenticated": True}, message=f"Successfully logged in as {username}"
                )
            else:
                return self._create_error_result(message="Login failed - no token received", error_code="LOGIN_FAILED")

        except AuthenticationError as e:
            return self._create_error_result(message=f"Authentication failed: {e}", error_code="AUTH_FAILED")
        except Exception as e:
            return self._handle_api_error(e)

    def _handle_oidc_login(self, provider: str, username: str | None = None) -> CommandResult:
        """Handle OIDC authentication flow using browser-based authentication.

        Args:
            provider: OIDC provider name (e.g., 'ibm')
            username: Optional username hint

        Returns:
            CommandResult with authentication status
        """
        import uuid
        import webbrowser

        try:
            if provider != "ibm":
                return self._create_error_result(
                    message=f"OIDC provider '{provider}' is not supported. Currently only 'ibm' is supported.",
                    error_code="UNSUPPORTED_PROVIDER",
                )

            # Step 1: Start CLI authentication to get authorization URL
            cli_request = {
                "provider": provider,
                "client_id": f"rag-cli-{uuid.uuid4().hex[:8]}",
                "scope": "openid profile email",
            }

            print("\n" + "=" * 60)
            print("🔐 IBM OIDC Authentication Required")
            print("=" * 60)
            print("\nInitiating browser-based authentication...")

            start_response = self.api_client.post("/api/auth/cli/start", data=cli_request)

            auth_url = start_response["auth_url"]
            start_response["state"]  # State handled by browser

            print("\nOpening your browser for authentication...")
            print(f"If the browser doesn't open, visit: {auth_url}")
            print("\nAfter logging in, you'll be redirected to a page with your JWT token.")
            print("=" * 60 + "\n")

            # Step 2: Open browser
            webbrowser.open(auth_url)

            # Step 3: Prompt user for JWT token from callback page
            print("Please complete the authentication in your browser.")
            jwt_token = input("Enter the JWT token from the callback page: ").strip()

            if not jwt_token:
                return self._create_error_result(
                    message="JWT token is required to complete authentication", error_code="MISSING_JWT_TOKEN"
                )

            # Step 4: Validate the JWT token and get user info
            print("\nValidating JWT token...")

            # Set the token temporarily to validate it
            self.api_client.set_auth_token(jwt_token)

            # Validate token by calling userinfo endpoint
            user_response = self.api_client.get("/api/auth/userinfo")

            # Step 5: Token is valid, user info retrieved
            access_token = jwt_token
            expires_at = None  # JWT tokens contain their own expiration
            user_info = user_response

            # Save token to auth manager
            self.api_client.set_auth_token(access_token, expires_at)

            username = user_info.get("email") or user_info.get("name") or "Unknown"

            print("✅ Authentication successful!")

            return self._create_success_result(
                data={"username": username, "authenticated": True, "provider": provider, "user": user_info},
                message=f"Successfully authenticated as {username} via {provider.upper()} OIDC",
            )

        except AuthenticationError as e:
            return self._create_error_result(message=f"Authentication failed: {e}", error_code="AUTH_FAILED")
        except Exception as e:
            return self._create_error_result(
                message=f"Failed to complete OIDC authentication: {e}", error_code="OIDC_FAILED"
            )

    def set_token(self, token: str, expires_in: int = 86400) -> CommandResult:
        """Set authentication token directly.

        This is useful when you've authenticated via the web UI and want
        to use the same token in the CLI.

        Args:
            token: JWT authentication token
            expires_in: Token expiration in seconds (default: 24 hours)

        Returns:
            CommandResult with status
        """
        try:
            from datetime import datetime, timedelta

            # Calculate expiration
            expires_at = datetime.now() + timedelta(seconds=expires_in)

            # Save token
            self.api_client.set_auth_token(token, expires_at.isoformat())

            # Verify token works by calling /api/auth/userinfo
            try:
                response = self.api_client.get("/api/auth/userinfo")
                username = response.get("email") or response.get("name") or "Unknown"

                return self._create_success_result(
                    data={"username": username, "authenticated": True},
                    message=f"Token set successfully. Authenticated as {username}",
                )
            except Exception as e:
                # Token might be invalid
                self.api_client.logout()  # Remove invalid token
                return self._create_error_result(message=f"Token validation failed: {e}", error_code="INVALID_TOKEN")

        except Exception as e:
            return self._handle_api_error(e)

    def logout(self) -> CommandResult:
        """Logout from RAG Modulo.

        Returns:
            CommandResult with logout status
        """
        try:
            # Remove stored token
            self.api_client.logout()

            return self._create_success_result(message="Successfully logged out")

        except Exception as e:
            return self._handle_api_error(e)

    def status(self) -> CommandResult:
        """Check authentication status.

        Returns:
            CommandResult with authentication status
        """
        try:
            if self.api_client.is_authenticated():
                # Try to get user info to verify token is valid
                try:
                    response = self.api_client.get("/api/auth/me")
                    username = response.get("username", "Unknown")

                    return self._create_success_result(
                        data={"authenticated": True, "username": username}, message=f"Authenticated as {username}"
                    )
                except Exception:
                    # Token might be expired or invalid
                    return self._create_error_result(
                        message="Authentication token is invalid or expired", error_code="TOKEN_INVALID"
                    )
            else:
                return self._create_error_result(message="Not authenticated", error_code="NOT_AUTHENTICATED")

        except Exception as e:
            return self._handle_api_error(e)

    def list_profiles(self) -> CommandResult:
        """List available authentication profiles.

        Returns:
            CommandResult with profile list
        """
        # This would list profiles from configuration
        # For now, return a simple implementation
        profiles = ["default"]  # Could be expanded to read from config

        return self._create_success_result(
            data={"profiles": profiles, "active": self.config.profile if self.config else "default"},
            message=f"Found {len(profiles)} profile(s)",
        )
