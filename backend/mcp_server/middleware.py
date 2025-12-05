"""MCP Server middleware for header extraction.

This module provides Starlette middleware that captures HTTP headers
from incoming requests and makes them available to MCP tool handlers
via context variables.

The MCP SSE transport doesn't pass HTTP headers to tool handlers by default.
This middleware intercepts requests and stores headers in a context variable
that can be accessed by _extract_headers_from_context().
"""

import logging
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from mcp_server.types import (
    set_current_request_headers,
    set_global_auth_headers,
    set_session_headers,
)

logger = logging.getLogger(__name__)


class HeaderCaptureMiddleware(BaseHTTPMiddleware):
    """Middleware that captures HTTP headers for MCP tool authentication.

    This middleware extracts authentication-related headers from incoming
    requests and stores them in a context variable that persists through
    the request lifecycle, including async MCP tool handlers.

    The following headers are captured (if present):
    - Authorization: Bearer tokens
    - X-API-Key: API key authentication
    - X-Authenticated-User: Trusted proxy user identity
    - X-SPIFFE-JWT: SPIFFE JWT-SVID for workload identity

    Example:
        app = Starlette(...)
        app.add_middleware(HeaderCaptureMiddleware)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and capture authentication headers.

        Args:
            request: The incoming Starlette request
            call_next: The next middleware or route handler

        Returns:
            Response from the next handler
        """
        # Log request path for debugging
        logger.info(
            "HeaderCaptureMiddleware: Processing %s %s",
            request.method,
            request.url.path,
        )

        # Extract all headers as a dict (normalized to lowercase keys)
        headers: dict[str, str] = {}

        # List of headers we care about for authentication
        auth_headers = [
            "authorization",
            "x-api-key",
            "x-authenticated-user",
            "x-spiffe-jwt",
            "x-forwarded-for",
            "x-real-ip",
        ]

        for header_name in auth_headers:
            value = request.headers.get(header_name)
            if value:
                headers[header_name] = value
                logger.debug("HeaderCaptureMiddleware: Found header %s", header_name)

        # Log headers at debug level to avoid noise and prevent sensitive data exposure
        logger.debug(
            "HeaderCaptureMiddleware: Request headers present: %s",
            list(request.headers.keys()),
        )
        logger.debug("HeaderCaptureMiddleware: Captured auth headers: %s", list(headers.keys()))

        # Store headers in context variable for tool handlers
        set_current_request_headers(headers)

        # Also store globally for SSE transport fallback
        # This ensures headers captured on /sse are available to tool handlers
        # even when context variables don't propagate across async boundaries
        if headers:
            set_global_auth_headers(headers)
            logger.debug("HeaderCaptureMiddleware: Stored headers globally")

        # For /messages/ requests, also store headers by session_id
        # This enables tool handlers to access headers in SSE transport
        # where the tool call happens in a different async context
        if request.url.path.rstrip("/").endswith("/messages"):
            session_id = request.query_params.get("session_id")
            if session_id:
                set_session_headers(session_id, headers)
                logger.debug(
                    "HeaderCaptureMiddleware: Stored headers for session %s",
                    session_id,
                )

        # Continue processing the request
        response = await call_next(request)

        return response
