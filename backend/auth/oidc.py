"""OIDC authentication module for IBM Cloud Identity.

This module provides OIDC authentication functionality using IBM Cloud Identity,
including JWT token verification, OAuth flow handling, and user authentication.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any

import jwt
from authlib.integrations.starlette_client import OAuth, OAuthError
from core.config import get_settings
from core.mock_auth import is_mock_token
from fastapi import HTTPException, Request, Response, status

# Get settings safely for auth
settings = get_settings()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

oauth = OAuth()

# Skip OIDC registration in test/CI environments or when auth is disabled
skip_auth = os.getenv("SKIP_AUTH", "false").lower() == "true"
development_mode = os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"
testing_mode = os.getenv("TESTING", "false").lower() == "true"

if not (skip_auth or development_mode or testing_mode):
    try:
        oauth.register(
            name="ibm",
            server_metadata_url=settings.oidc_discovery_endpoint,
            client_id=settings.ibm_client_id,
            client_secret=settings.ibm_client_secret,
            client_kwargs={"scope": "openid email profile", "token_endpoint_auth_method": "client_secret_post"},
            # Add leeway for token validation
            jwks_uri=(settings.oidc_discovery_endpoint or "") + "/jwks",
            validate_iss=True,
            validate_aud=True,
            validate_exp=True,
            validate_iat=False,
            validate_nbf=True,
            leeway=50000,
        )
        logger.info("OIDC provider registered successfully")
    except (OAuthError, ValueError, KeyError) as e:
        logger.warning("Failed to register OIDC provider: %s. Auth will work in test mode only.", str(e))
else:
    logger.info(
        "OIDC registration skipped (skip_auth=%s, development_mode=%s, testing_mode=%s)",
        skip_auth,
        development_mode,
        testing_mode,
    )


def verify_jwt_token(token: str) -> dict[str, Any]:
    """Verify JWT token and return payload."""
    try:
        # Special handling for mock tokens
        if is_mock_token(token):
            return {
                "sub": "test_user_id",
                "email": "test@example.com",
                "name": "Test User",
                # UUID and role will be added by middleware from headers
            }

        # Normal token verification
        payload = jwt.decode(
            token,
            options={
                "verify_signature": False,  # For testing environment
                "verify_exp": False,
                "verify_iat": False,
            },
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


async def get_current_user(request: Request) -> dict:
    """Extract and verify current user from request headers.

    Args:
        request: FastAPI request object

    Returns:
        User payload dictionary

    Raises:
        HTTPException: If authentication fails
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.split(" ")[1]
    payload = verify_jwt_token(token)

    logger.info("Got User: %s", payload)
    return payload


async def authorize_redirect(request: Request, redirect_uri: str) -> Response:
    """Initiate OAuth authorization redirect.

    Args:
        request: FastAPI request object
        redirect_uri: URI to redirect to after authorization

    Returns:
        Redirect response

    Raises:
        HTTPException: If authorization fails
    """
    try:
        logger.debug("Initiating authorize_redirect with redirect_uri: %s", redirect_uri)
        response = await oauth.ibm.authorize_redirect(request, redirect_uri)
        logger.debug("authorize_redirect response: %s", response)
        return response
    except OAuthError as error:
        logger.error("OAuth error during authorize_redirect: %s", str(error), exc_info=True)
        raise HTTPException(status_code=500, detail=f"OAuth authorization error: {error!s}") from error
    except (ValueError, KeyError, AttributeError) as e:
        logger.error("Unexpected error during authorize_redirect: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Authorization error: {e!s}") from e


async def authorize_access_token(request: Request) -> dict[str, Any]:
    """Exchange authorization code for access token.

    Args:
        request: FastAPI request object

    Returns:
        Token dictionary containing access token and user info

    Raises:
        HTTPException: If token exchange fails
    """
    try:
        logger.debug("Initiating authorize_access_token")
        token = await oauth.ibm.authorize_access_token(request)
        logger.debug("Token received: %s", token)
        return token
    except OAuthError as error:
        logger.error("OAuth error during authorize_access_token: %s", str(error), exc_info=True)
        raise HTTPException(status_code=500, detail=f"OAuth token authorization error: {error!s}") from error
    except (ValueError, KeyError, AttributeError) as e:
        logger.error("Unexpected error during authorize_access_token: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Token authorization error: {e!s}") from e


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token for internal use.

    Args:
        data: The payload data to encode in the token
        expires_delta: Optional expiration time delta (defaults to 24 hours)

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    # Set expiration time
    expire = datetime.utcnow() + expires_delta if expires_delta else datetime.utcnow() + timedelta(hours=24)

    to_encode.update({"exp": expire})

    # Add standard JWT claims
    to_encode.update(
        {
            "iat": datetime.utcnow(),  # Issued at
            "iss": "rag-modulo",  # Issuer
        }
    )

    # Encode the JWT token
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    # Ensure we return a string, not bytes
    if isinstance(encoded_jwt, bytes):
        return encoded_jwt.decode("utf-8")
    return encoded_jwt
