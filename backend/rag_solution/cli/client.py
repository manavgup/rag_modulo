"""HTTP client for RAG CLI API communication.

This module provides a comprehensive HTTP client for communicating with
the RAG Modulo API, including authentication, error handling, and
request/response processing.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .auth import AuthManager
from .config import RAGConfig
from .exceptions import APIError, AuthenticationError, RAGCLIError


class RAGAPIClient:
    """HTTP client for RAG Modulo API communication.

    This client handles all API communication including authentication,
    request retries, error handling, and response processing.

    Attributes:
        config: Configuration settings for the client
        auth_manager: Authentication manager for token handling
        session: HTTP session for request management
    """

    def __init__(self, config: RAGConfig) -> None:
        """Initialize the RAG API client.

        Args:
            config: Configuration settings for the client
        """
        self.config = config
        self.auth_manager = AuthManager(profile=config.profile)
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create and configure HTTP session with retries.

        Returns:
            Configured requests Session object
        """
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1,
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _get_headers(self, additional_headers: dict[str, str] | None = None) -> dict[str, str]:
        """Get HTTP headers for requests.

        Args:
            additional_headers: Optional additional headers to include

        Returns:
            Dictionary of HTTP headers
        """
        headers = {"Content-Type": "application/json", "User-Agent": f"rag-cli/{self.config.profile}"}

        # Add authentication headers if token is available
        token = self.get_auth_token()
        if token:
            headers.update(self.auth_manager.generate_auth_headers(token))

        # Add any additional headers
        if additional_headers:
            headers.update(additional_headers)

        return headers

    def _build_url(self, endpoint: str) -> str:
        """Build complete API URL from endpoint.

        Args:
            endpoint: API endpoint path

        Returns:
            Complete API URL
        """
        base_url = str(self.config.api_url).rstrip("/")
        endpoint = endpoint.lstrip("/")
        return f"{base_url}/{endpoint}"

    def _handle_response(self, response: requests.Response) -> Any:
        """Handle API response and extract data.

        Args:
            response: HTTP response object

        Returns:
            Parsed response data

        Raises:
            AuthenticationError: If authentication fails
            APIError: If API request fails
        """
        try:
            # Handle authentication errors
            if response.status_code == 401:
                # Remove invalid token
                self.auth_manager.remove_token()
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("error", "Authentication failed")
                raise AuthenticationError(error_msg, details=error_data)

            # Handle other client/server errors
            if response.status_code >= 400:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("error", f"API request failed with status {response.status_code}")
                raise APIError(message=error_msg, status_code=response.status_code, details=error_data)

            # Parse successful response
            if response.content:
                return response.json()
            return {"success": True}

        except requests.exceptions.JSONDecodeError as e:
            # Handle non-JSON responses
            if response.status_code < 400:
                return {"content": response.text}
            raise APIError(f"Invalid JSON response: {response.text}") from e

    def get(self, endpoint: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
        """Make GET request to API.

        Args:
            endpoint: API endpoint path
            params: Optional query parameters
            headers: Optional additional headers

        Returns:
            API response data

        Raises:
            APIError: If request fails
            AuthenticationError: If authentication fails
        """
        try:
            url = self._build_url(endpoint)
            request_headers = self._get_headers(headers)

            response = self.session.get(url, params=params, headers=request_headers, timeout=self.config.timeout)

            return self._handle_response(response)

        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            raise APIError(f"GET request failed: {e!s}") from e

    def post(self, endpoint: str, data: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
        """Make POST request to API.

        Args:
            endpoint: API endpoint path
            data: Optional request body data
            headers: Optional additional headers

        Returns:
            API response data

        Raises:
            APIError: If request fails
            AuthenticationError: If authentication fails
        """
        try:
            url = self._build_url(endpoint)
            request_headers = self._get_headers(headers)

            response = self.session.post(url, json=data, headers=request_headers, timeout=self.config.timeout)

            return self._handle_response(response)

        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            raise APIError(f"POST request failed: {e!s}") from e

    def put(self, endpoint: str, data: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
        """Make PUT request to API.

        Args:
            endpoint: API endpoint path
            data: Optional request body data
            headers: Optional additional headers

        Returns:
            API response data

        Raises:
            APIError: If request fails
            AuthenticationError: If authentication fails
        """
        try:
            url = self._build_url(endpoint)
            request_headers = self._get_headers(headers)

            response = self.session.put(url, json=data, headers=request_headers, timeout=self.config.timeout)

            return self._handle_response(response)

        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            raise APIError(f"PUT request failed: {e!s}") from e

    def delete(self, endpoint: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
        """Make DELETE request to API.

        Args:
            endpoint: API endpoint path
            params: Optional query parameters
            headers: Optional additional headers

        Returns:
            API response data

        Raises:
            APIError: If request fails
            AuthenticationError: If authentication fails
        """
        try:
            url = self._build_url(endpoint)
            request_headers = self._get_headers(headers)

            response = self.session.delete(url, params=params, headers=request_headers, timeout=self.config.timeout)

            return self._handle_response(response)

        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            raise APIError(f"DELETE request failed: {e!s}") from e

    def post_file(
        self,
        endpoint: str,
        file_path: str | Path,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        """Upload file via POST request.

        Args:
            endpoint: API endpoint path
            file_path: Path to file to upload
            data: Optional additional form data
            headers: Optional additional headers

        Returns:
            API response data

        Raises:
            APIError: If request fails
            AuthenticationError: If authentication fails
            RAGCLIError: If file is not found
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise RAGCLIError(f"File not found: {file_path}")

        try:
            url = self._build_url(endpoint)

            # Get headers without Content-Type for multipart/form-data
            request_headers = self._get_headers(headers)
            if "Content-Type" in request_headers:
                del request_headers["Content-Type"]

            # Prepare files and data for multipart upload
            with open(file_path, "rb") as file_obj:
                files = {"file": (file_path.name, file_obj, "application/octet-stream")}

                response = self.session.post(url, files=files, data=data or {}, headers=request_headers, timeout=self.config.timeout)

            return self._handle_response(response)

        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            raise APIError(f"File upload failed: {e!s}") from e
        except OSError as e:
            raise RAGCLIError(f"File read error: {e!s}") from e

    def is_authenticated(self) -> bool:
        """Check if client is authenticated.

        Returns:
            True if client has valid authentication token
        """
        # Check if we have a token in config (direct token) or in auth manager (stored token)
        return bool(self.config.auth_token) or self.auth_manager.is_authenticated()

    def get_auth_token(self) -> str | None:
        """Get current authentication token.

        Returns:
            Authentication token or None if not authenticated
        """
        # Return config token if available, otherwise check auth manager
        return self.config.auth_token or self.auth_manager.get_current_token()

    def set_auth_token(self, token: str, expires_at: str | None = None) -> None:
        """Set authentication token.

        Args:
            token: JWT authentication token
            expires_at: Token expiration timestamp (ISO format)

        Raises:
            AuthenticationError: If token is invalid
        """
        if expires_at:
            try:
                exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            except ValueError as e:
                raise AuthenticationError("Invalid expiration timestamp format") from e
        else:
            # Default to 24 hours if no expiration provided
            exp_dt = datetime.now() + timedelta(hours=24)

        self.auth_manager.save_token(token, exp_dt)

    def logout(self) -> None:
        """Remove authentication token and logout.

        This method clears the stored authentication token,
        effectively logging the user out of the CLI.
        """
        self.auth_manager.remove_token()

    def test_connection(self) -> bool:
        """Test API connection.

        Returns:
            True if connection to API is successful
        """
        try:
            response = self.get("/api/health")
            return response is not None
        except (APIError, AuthenticationError, requests.exceptions.RequestException):
            return False
