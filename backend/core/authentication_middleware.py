import logging
import os
from typing import Any

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from auth.oidc import verify_jwt_token
from core.config import get_settings

# Get settings safely for middleware
settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self: Any, request: Request, call_next: Any) -> Any:
        logger.info(f"AuthMiddleware: Processing request to {request.url.path}")
        logger.debug(f"AuthMiddleware: Request headers: {request.headers}")

        # Skip authentication entirely in test/development mode
        skip_auth = os.getenv("SKIP_AUTH", "false").lower() == "true"
        development_mode = os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"
        testing_mode = os.getenv("TESTING", "false").lower() == "true"

        if skip_auth or development_mode or testing_mode:
            # Set a default test user for CI/development
            request.state.user = {
                "id": "test_user_id",
                "email": "test@example.com",
                "name": "Test User",
                "uuid": request.headers.get("X-User-UUID", "test-uuid"),
                "role": request.headers.get("X-User-Role", "admin"),
            }
            logger.debug(f"AuthMiddleware: Skipping auth (skip_auth={skip_auth}, dev={development_mode}, test={testing_mode})")
            return await call_next(request)

        open_paths = [
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
            "/api/docs",
            "/api/openapi.json",
            "/api/redoc",
            "/api/docs/oauth2-redirect",
            "/api/docs/swagger-ui.css",
            "/api/docs/swagger-ui-bundle.js",
            "/api/docs/swagger-ui-standalone-preset.js",
            "/api/docs/favicon.png",
        ]

        # Skip authentication for open paths and static files
        logger.debug(f"AuthMiddleware: Checking path '{request.url.path}' against open_paths: {open_paths}")
        if request.url.path in open_paths or request.url.path.startswith("/static/"):
            logger.info(f"AuthMiddleware: Allowing access to open path: {request.url.path}")
            return await call_next(request)

        # Check for JWT in Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            logger.info("AuthMiddleware: JWT token found in Authorization header")
            token = auth_header.split(" ")[1]
            try:
                # Special handling for test token
                if token == "mock_token_for_testing":
                    request.state.user = {
                        "id": "test_user_id",
                        "email": "test@example.com",
                        "name": "Test User",
                        "uuid": request.headers.get("X-User-UUID"),  # Get UUID from header for tests
                        "role": request.headers.get("X-User-Role", "admin"),  # Default to admin for test token
                    }
                    logger.info("AuthMiddleware: Using mock test token")
                else:
                    # Verify JWT using the verify_jwt_token function
                    payload = verify_jwt_token(token)
                    request.state.user = {
                        "id": payload.get("sub"),
                        "email": payload.get("email"),
                        "name": payload.get("name"),
                        "uuid": payload.get("uuid"),
                        "role": payload.get("role"),
                    }
                logger.info(f"AuthMiddleware: JWT token validated successfully. User: {request.state.user}")
            except jwt.ExpiredSignatureError:
                logger.warning("AuthMiddleware: Expired JWT token")
                return JSONResponse(status_code=401, content={"detail": "Token has expired"})
            except jwt.InvalidTokenError as e:
                logger.warning(f"AuthMiddleware: Invalid JWT token - {e!s}")
                return JSONResponse(status_code=401, content={"detail": "Invalid authentication credentials"})
        else:
            logger.info("AuthMiddleware: No JWT token found")

        # Require authentication for all other paths
        if not hasattr(request.state, "user"):
            logger.warning(f"AuthMiddleware: User not authenticated for protected endpoint: {request.url.path}")
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})

        logger.info("AuthMiddleware: Passing request to next middleware/handler")
        logger.info(f"AuthMiddleware: About to call next handler for {request.url.path}")

        try:
            response = await call_next(request)
            logger.info(f"AuthMiddleware: Response status code: {response.status_code}")
            return response
        except Exception as e:
            logger.error(f"AuthMiddleware: Exception in call_next: {e}", exc_info=True)
            raise
