"""MCP Server type definitions and utilities.

This module provides shared type definitions and utility functions used
across the MCP server implementation. Separated to avoid circular imports.

Error Types:
    - authorization_error: Authentication or permission failure
    - validation_error: Invalid input parameters
    - not_found: Requested resource does not exist
    - operation_error: Operation failed during execution
"""

import contextlib
from collections.abc import Callable, Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from enum import Enum
from typing import Any
from uuid import UUID

from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession
from sqlalchemy.orm import Session

# Type alias for the database session factory
DbSessionFactory = Callable[[], Generator[Session, None, None]]

# Context variable to store HTTP headers from the current request
# This is populated by middleware and read by tool handlers
# Note: Using None as default per B039 - mutable defaults not allowed for ContextVar
_request_headers: ContextVar[dict[str, str] | None] = ContextVar("request_headers", default=None)

# Session-based header storage for SSE transport
# Maps session_id -> headers dict
# This is needed because SSE tool calls happen in a different async context
_session_headers: dict[str, dict[str, str]] = {}

# Context variable to store the current session ID
_current_session_id: ContextVar[str | None] = ContextVar("current_session_id", default=None)

# Global header storage - fallback for when context variables don't propagate
# This stores the most recent auth headers from any request (connection-scoped)
# Used primarily for single-user testing scenarios (e.g., MCP Inspector)
_global_auth_headers: dict[str, str] = {}


def get_current_request_headers() -> dict[str, str]:
    """Get headers from the current request context.

    First checks the context variable, then falls back to session storage.

    Returns:
        Dictionary of header name to value mappings from the current request.
        Returns empty dict if no headers are available.
    """
    # First try context variable (works for sync requests)
    headers = _request_headers.get()
    if headers:
        return headers

    # Fall back to session storage for SSE transport
    session_id = _current_session_id.get()
    if session_id and session_id in _session_headers:
        return _session_headers[session_id]

    return {}


def set_current_request_headers(headers: dict[str, str]) -> None:
    """Set headers for the current request context.

    This is called by middleware to make headers available to tool handlers.

    Args:
        headers: Dictionary of header name to value mappings
    """
    _request_headers.set(headers)


def set_session_headers(session_id: str, headers: dict[str, str]) -> None:
    """Store headers by session ID for SSE transport.

    SSE tool calls happen in a different async context than the HTTP request,
    so we need to store headers by session ID and look them up later.

    Args:
        session_id: The MCP session ID
        headers: Dictionary of header name to value mappings
    """
    _session_headers[session_id] = headers


def get_session_headers(session_id: str) -> dict[str, str]:
    """Get headers for a specific session.

    Args:
        session_id: The MCP session ID

    Returns:
        Dictionary of header name to value mappings, or empty dict if not found
    """
    return _session_headers.get(session_id, {})


def set_current_session_id(session_id: str | None) -> None:
    """Set the current session ID in context.

    Args:
        session_id: The MCP session ID, or None to clear
    """
    _current_session_id.set(session_id)


def clear_session_headers(session_id: str) -> None:
    """Clear stored headers for a session (cleanup on disconnect).

    Args:
        session_id: The MCP session ID to clear
    """
    _session_headers.pop(session_id, None)


def set_global_auth_headers(headers: dict[str, str]) -> None:
    """Store headers globally as a fallback for SSE transport.

    This is used when context variables don't propagate across async boundaries.
    The global storage is primarily for single-user testing scenarios like MCP Inspector.

    Args:
        headers: Dictionary of header name to value mappings
    """
    global _global_auth_headers
    if headers:  # Only update if there are headers
        _global_auth_headers = headers.copy()


def get_global_auth_headers() -> dict[str, str]:
    """Get globally stored auth headers.

    Returns:
        Dictionary of header name to value mappings, or empty dict if none stored
    """
    return _global_auth_headers.copy()


class MCPErrorType(str, Enum):
    """Standard error types for MCP tool responses.

    These error types provide consistent categorization of failures
    across all MCP tools for easier client-side handling.
    """

    AUTHORIZATION = "authorization_error"
    VALIDATION = "validation_error"
    NOT_FOUND = "not_found"
    OPERATION = "operation_error"


def create_error_response(
    error: str | Exception,
    error_type: MCPErrorType,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a standardized error response for MCP tools.

    Args:
        error: Error message or exception
        error_type: Category of error from MCPErrorType
        details: Optional additional error details

    Returns:
        Dictionary with error, error_type, and optional details
    """
    response: dict[str, Any] = {
        "error": str(error),
        "error_type": error_type.value,
    }
    if details:
        response["details"] = details
    return response


# Try to import get_http_headers for HTTP transport header extraction
try:
    from fastmcp.server.dependencies import get_http_headers
except ImportError:
    # Fallback if using older mcp package version
    get_http_headers = None  # type: ignore[misc, assignment]

# Service imports must come after try/except block above to avoid circular imports
from mcp_server.auth import MCPAuthContext, MCPAuthenticator  # noqa: E402


@contextmanager
def db_session_context(factory: DbSessionFactory) -> Generator[Session, None, None]:
    """Context manager for proper database session lifecycle.

    Creates a new database session from the factory and ensures proper cleanup,
    including rollback on errors and session closure. This ensures each MCP
    request gets its own isolated database session, preventing race conditions
    and transaction conflicts in concurrent requests.

    Args:
        factory: A callable that returns a generator yielding a Session

    Yields:
        Session: Database session that is properly managed

    Example:
        with db_session_context(app_ctx.db_session_factory) as db:
            result = db.query(Model).all()

    Raises:
        Exception: Any database errors are propagated after cleanup
    """
    db_gen = factory()
    db_session = next(db_gen)
    try:
        yield db_session
    finally:
        # Exhaust the generator to trigger its cleanup code
        with contextlib.suppress(StopIteration):
            next(db_gen)


@dataclass
class MCPServerContext:
    """Application context holding shared resources for MCP tools.

    This context is initialized at server startup and made available
    to all tool handlers through the lifespan context.

    IMPORTANT: Database sessions are created per-request using db_session_factory
    to prevent race conditions and transaction conflicts in concurrent requests.
    Services that need database access should be instantiated within the request
    scope using db_session_context().

    Attributes:
        db_session_factory: Factory function that creates isolated database sessions
        authenticator: MCP authentication handler
        settings: Application settings
    """

    db_session_factory: DbSessionFactory
    authenticator: MCPAuthenticator
    settings: Any


def get_app_context(ctx: Context[ServerSession, MCPServerContext, Any]) -> MCPServerContext:
    """Extract the application context from the MCP request context.

    This helper function provides type-safe access to the MCPServerContext
    from within tool handlers.

    Args:
        ctx: The MCP Context object from a tool handler

    Returns:
        The MCPServerContext with all initialized services
    """
    return ctx.request_context.lifespan_context


def parse_uuid(value: str, field_name: str = "id") -> UUID:
    """Parse and validate a UUID string.

    Args:
        value: String representation of UUID
        field_name: Name of the field for error messages

    Returns:
        Parsed UUID object

    Raises:
        ValueError: If the string is not a valid UUID
    """
    try:
        return UUID(value)
    except ValueError as e:
        raise ValueError(f"Invalid {field_name}: {value}. Must be a valid UUID.") from e


def _extract_headers_from_context(
    ctx: Context[ServerSession, MCPServerContext, Any],
) -> dict[str, str]:
    """Extract authentication headers from MCP context.

    Attempts to extract headers from multiple sources (in priority order):
    1. Context variable (set by middleware for SSE/HTTP transports)
    2. Session-based storage (for SSE where tool calls are in different async context)
    3. HTTP transport headers (via get_http_headers if available)
    4. MCP request context metadata (client-provided)

    Args:
        ctx: The MCP Context object from a tool handler

    Returns:
        Dictionary of header name to value mappings
    """
    headers: dict[str, str] = {}

    # Try to get session ID from MCP context and set it for session-based header lookup
    # This enables fallback to session storage in get_current_request_headers()
    session_id = None
    try:
        if hasattr(ctx, "request_context") and ctx.request_context:
            # Try multiple ways to get session_id
            session = getattr(ctx.request_context, "session", None)
            if session:
                # First try session_id attribute
                session_id = getattr(session, "session_id", None)
                # Then try _session_id (private attribute)
                if not session_id:
                    session_id = getattr(session, "_session_id", None)
                # Then try id attribute
                if not session_id:
                    session_id = getattr(session, "id", None)
                # Last resort: use object id
                if not session_id:
                    session_id = str(id(session))

            # Also check request_context meta for session info
            if not session_id:
                meta = getattr(ctx.request_context, "meta", None)
                if meta:
                    session_id = getattr(meta, "session_id", None)

        if session_id:
            set_current_session_id(str(session_id))
    except Exception:
        pass

    # Source 1: Get headers from context variable (set by middleware)
    # This is the primary source for SSE/HTTP transports
    # Falls back to session storage if context variable is empty
    ctx_headers = get_current_request_headers()
    if ctx_headers:
        headers.update({k.lower(): v for k, v in ctx_headers.items()})

    # Source 2: Try direct session header lookup if we found a session_id
    # This handles cases where context variables don't propagate
    if not headers and session_id:
        session_headers = get_session_headers(str(session_id))
        if session_headers:
            headers.update({k.lower(): v for k, v in session_headers.items()})

    # Source 3: Try to get HTTP headers from transport layer (fastmcp)
    if get_http_headers is not None:
        try:
            http_headers = get_http_headers()
            if http_headers:
                # Normalize header names (HTTP headers are case-insensitive)
                # Don't overwrite existing headers from context variable
                for k, v in http_headers.items():
                    if k.lower() not in headers:
                        headers[k.lower()] = v
        except Exception:
            # HTTP headers not available (e.g., stdio transport)
            pass

    # Source 4: Extract from MCP request context metadata
    # MCP clients can provide auth info via request metadata
    try:
        if hasattr(ctx, "request_context") and ctx.request_context:
            meta = getattr(ctx.request_context, "meta", None)
            if meta:
                # Map common metadata fields to HTTP header equivalents
                # Header field name mappings (not secrets)
                header_mappings = {  # pragma: allowlist secret
                    "authorization": "authorization",
                    "x_spiffe_jwt": "x-spiffe-jwt",
                    "x_api_key": "x-api-key",  # pragma: allowlist secret
                    "x_authenticated_user": "x-authenticated-user",
                    "user_id": "x-authenticated-user",
                }
                for meta_key, header_name in header_mappings.items():
                    value = getattr(meta, meta_key, None)
                    if value and header_name not in headers:
                        headers[header_name] = str(value)
    except Exception:
        # Metadata extraction failed, continue with available headers
        pass

    # Source 5: Global auth headers fallback (for SSE transport)
    # This catches headers that were captured on /sse connection but couldn't
    # be correlated to the tool call via session_id
    if not headers:
        global_headers = get_global_auth_headers()
        if global_headers:
            headers.update({k.lower(): v for k, v in global_headers.items()})

    return headers


async def validate_auth(
    ctx: Context[ServerSession, MCPServerContext, Any],
    required_permissions: list[str] | None = None,
) -> MCPAuthContext:
    """Validate authentication and authorization for an MCP request.

    Extracts authentication credentials from the request context and
    validates them using the configured authenticator.

    Headers are extracted from multiple sources:
    - HTTP transport layer (when using HTTP/SSE transport)
    - MCP request metadata (client-provided auth info)

    Args:
        ctx: The MCP Context object from a tool handler
        required_permissions: Optional list of required permissions

    Returns:
        MCPAuthContext with validated user information

    Raises:
        PermissionError: If authentication fails or permissions are insufficient
    """
    app_ctx = get_app_context(ctx)

    # Extract auth headers from available sources
    headers = _extract_headers_from_context(ctx)

    auth_context = await app_ctx.authenticator.authenticate_request(
        headers=headers,
        required_permissions=required_permissions or [],
    )

    return auth_context
