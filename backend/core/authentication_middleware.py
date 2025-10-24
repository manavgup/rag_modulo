"""Authentication middleware for FastAPI application.

This module provides middleware for handling JWT-based authentication,
including support for development/testing modes and mock user creation.
"""

import logging
import os
from typing import Any

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware

from auth.oidc import verify_jwt_token
from core.config import get_settings
from core.mock_auth import create_mock_user_data, ensure_mock_user_exists, is_bypass_mode_active, is_mock_token
from rag_solution.core.exceptions import NotFoundError

# Get settings safely for middleware
settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for handling JWT-based authentication.

    This middleware provides authentication for FastAPI routes, supporting:
    - JWT token validation
    - Development/testing mode bypass
    - Mock user creation for testing
    - Open path configuration
    """

    def __init__(self, app: Any) -> None:
        """Initialize the authentication middleware.

        Args:
            app: The FastAPI application instance.
        """
        super().__init__(app)
        self._open_paths = self._get_open_paths()

    def _get_open_paths(self) -> set[str]:
        """Get list of paths that don't require authentication.

        Returns:
            List of open paths that bypass authentication.
        """
        return {
            "/api/",
            "/api/auth/login",
            "/api/auth/callback",  # Important for OAuth flow
            "/api/health",
            "/api/auth/oidc-config",
            "/api/auth/token",  # Important for token exchange
            "/api/auth/userinfo",  # Allow initial access for token verification
            "/api/auth/session",  # Allow checking session status
            "/api/auth/device/start",  # Device flow initiation
            "/api/auth/device/poll",  # Device flow polling
            "/api/auth/cli/start",  # CLI authentication initiation
            "/api/auth/cli/token",  # CLI token exchange
            # API Documentation endpoints (unprotected for developer experience)
            "/docs",
            "/openapi.json",
            "/redoc",
            "/docs/oauth2-redirect",
            "/docs/swagger-ui.css",
            "/docs/swagger-ui-bundle.js",
            "/docs/swagger-ui-standalone-preset.js",
            "/docs/favicon.png",
        }

    def _is_bypass_mode_active(self) -> bool:
        """Check if authentication bypass is active.

        Returns:
            True if authentication should be bypassed.
        """
        return is_bypass_mode_active()

    def _create_mock_user_session(self) -> str | None:
        """Create a database session and ensure mock user exists.

        Returns:
            User UUID if successful, None otherwise.
        """
        try:
            current_settings = get_settings()
            # Construct database URL from individual components
            db_url = (
                f"postgresql://{current_settings.collectiondb_user}:"
                f"{current_settings.collectiondb_pass}@"
                f"{current_settings.collectiondb_host}:"
                f"{current_settings.collectiondb_port}/"
                f"{current_settings.collectiondb_name}"
            )
            engine = create_engine(db_url)
            session_factory = sessionmaker(bind=engine)
            session = session_factory()

            # Ensure mock user exists with full initialization
            actual_user_id = ensure_mock_user_exists(session, current_settings)
            user_uuid = str(actual_user_id)

            session.close()
            logger.info("AuthMiddleware: Mock user ready with ID: %s", user_uuid)
            return user_uuid
        except (ValueError, TypeError, AttributeError, ConnectionError, NotFoundError) as e:
            logger.warning("AuthMiddleware: Could not ensure mock user initialization: %s", e)
            return None

    def _set_mock_user_state(self, request: Request, user_uuid: str) -> None:
        """Set mock user data in request state.

        Args:
            request: The FastAPI request object.
            user_uuid: The user UUID to set.
        """
        mock_data = create_mock_user_data(user_uuid)
        # Allow role override via header for testing
        mock_data["role"] = request.headers.get("X-User-Role", mock_data["role"])
        request.state.user = mock_data

    def _handle_bypass_mode(self, request: Request) -> bool:
        """Handle authentication bypass mode.

        Args:
            request: The FastAPI request object.

        Returns:
            True if request should continue, False if response is returned.
        """
        logger.debug(
            "AuthMiddleware: Bypass mode active (skip_auth=%s, dev=%s, test=%s)",
            os.getenv("SKIP_AUTH", "false").lower() == "true",
            os.getenv("DEVELOPMENT_MODE", "false").lower() == "true",
            os.getenv("TESTING", "false").lower() == "true",
        )

        # Get or create mock user with full initialization
        mock_user_uuid = self._create_mock_user_session()
        if mock_user_uuid:
            user_uuid = mock_user_uuid
            logger.info("AuthMiddleware: Using created mock user UUID: %s", user_uuid)
        else:
            # If mock user creation fails, use header UUID or fail gracefully
            user_uuid = request.headers.get("X-User-UUID")
            if not user_uuid:
                logger.error("AuthMiddleware: Failed to create mock user and no X-User-UUID header provided")
                return False
            logger.warning("AuthMiddleware: Failed to create mock user, using header UUID: %s", user_uuid)

        self._set_mock_user_state(request, user_uuid)
        return True

    def _is_open_path(self, request: Request) -> bool:
        """Check if the request path is open (doesn't require authentication).

        Args:
            request: The FastAPI request object.

        Returns:
            True if path is open, False otherwise.
        """
        path = request.url.path
        logger.debug("AuthMiddleware: Checking path '%s' against open_paths: %s", path, self._open_paths)

        if path in self._open_paths or path.startswith("/static/"):
            logger.info("AuthMiddleware: Allowing access to open path: %s", path)
            return True
        return False

    def _handle_mock_token(self, request: Request, token: str) -> bool:  # pylint: disable=unused-argument  # noqa: ARG002
        """Handle mock token authentication.

        Args:
            request: The FastAPI request object.
            token: The mock token.

        Returns:
            True if mock token was handled successfully.
        """
        logger.info("AuthMiddleware: Detected mock token")

        # Get or create mock user with full initialization
        mock_user_uuid = self._create_mock_user_session()
        if mock_user_uuid:
            user_uuid = mock_user_uuid
            logger.info("AuthMiddleware: Using created mock user UUID: %s", user_uuid)
        else:
            # If mock user creation fails, use header UUID or fail gracefully
            user_uuid = request.headers.get("X-User-UUID")
            if not user_uuid:
                logger.error("AuthMiddleware: Failed to create mock user and no X-User-UUID header provided")
                return False
            logger.warning("AuthMiddleware: Failed to create mock user, using header UUID: %s", user_uuid)

        self._set_mock_user_state(request, user_uuid)
        logger.info("AuthMiddleware: Using mock test token")
        return True

    def _handle_jwt_token(self, request: Request, token: str) -> bool:
        """Handle JWT token authentication.

        Args:
            request: The FastAPI request object.
            token: The JWT token.

        Returns:
            True if JWT token was handled successfully.
        """
        try:
            # Check if this is a mock token using centralized function
            if is_mock_token(token):
                return self._handle_mock_token(request, token)

            # Verify JWT using the verify_jwt_token function
            payload = verify_jwt_token(token)
            request.state.user = {
                "id": payload.get("sub"),
                "email": payload.get("email"),
                "name": payload.get("name"),
                "uuid": payload.get("uuid"),
                "role": payload.get("role"),
            }
            logger.info("AuthMiddleware: JWT token validated successfully. User: %s", request.state.user)
            return True
        except jwt.ExpiredSignatureError:
            logger.warning("AuthMiddleware: Expired JWT token")
            return False
        except jwt.InvalidTokenError as e:
            logger.warning("AuthMiddleware: Invalid JWT token - %s", e)
            return False

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Process the request through authentication middleware.

        Args:
            request: The FastAPI request object.
            call_next: The next middleware/handler in the chain.

        Returns:
            The response from the next handler or an authentication error response.
        """
        logger.info("AuthMiddleware: Processing request to %s", request.url.path)
        logger.debug("AuthMiddleware: Request headers: %s", request.headers)

        # Skip authentication entirely in test/development mode
        skip_auth = os.getenv("SKIP_AUTH", "false").lower() == "true"
        development_mode = os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"
        testing_mode = os.getenv("TESTING", "false").lower() == "true"
        if skip_auth or development_mode or testing_mode:  # noqa: SIM102
            if self._handle_bypass_mode(request):
                return await call_next(request)

        # Skip authentication for open paths and static files
        if self._is_open_path(request):
            return await call_next(request)

        # Check for JWT in Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            logger.info("AuthMiddleware: JWT token found in Authorization header")
            token = auth_header.split(" ")[1]

            if not self._handle_jwt_token(request, token):
                return JSONResponse(status_code=401, content={"detail": "Invalid authentication credentials"})
        else:
            logger.info("AuthMiddleware: No JWT token found")

        # Require authentication for all other paths
        if not hasattr(request.state, "user"):
            logger.warning("AuthMiddleware: User not authenticated for protected endpoint: %s", request.url.path)
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})

        logger.info("AuthMiddleware: Passing request to next middleware/handler")
        logger.info("AuthMiddleware: About to call next handler for %s", request.url.path)

        try:
            response = await call_next(request)
            logger.info("AuthMiddleware: Response status code: %s", response.status_code)
            return response
        except Exception as e:
            logger.error("AuthMiddleware: Exception in call_next: %s", e, exc_info=True)
            raise

    def add_open_path(self, path: str) -> None:
        """Add a path to the list of open paths that don't require authentication.

        Args:
            path: The path to add to open paths
        """
        self._open_paths.add(path)
        logger.info("AuthMiddleware: Added open path: %s", path)

    def remove_open_path(self, path: str) -> None:
        """Remove a path from the list of open paths.

        Args:
            path: The path to remove from open paths
        """
        self._open_paths.discard(path)
        logger.info("AuthMiddleware: Removed open path: %s", path)

    def get_open_paths(self) -> set[str]:
        """Get the current set of open paths.

        Returns:
            Set of open paths
        """
        return self._open_paths.copy()
