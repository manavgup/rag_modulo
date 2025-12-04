"""MCP Server implementation for RAG Modulo.

This module provides the core MCP server that exposes RAG Modulo functionality
as MCP tools and resources. Uses the FastMCP high-level API for clean integration.

Database Session Management:
    This server uses a per-request session factory pattern to prevent race conditions
    and transaction conflicts in concurrent requests. Instead of sharing a single
    database session, each tool/resource creates its own session using:

        with db_session_context(app_ctx.db_session_factory) as db:
            service = SomeService(db=db, settings=app_ctx.settings)
            result = service.do_something()
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from core.config import get_settings
from core.enhanced_logging import get_logger
from mcp_server.auth import MCPAuthenticator

# Re-export from types for backward compatibility
from mcp_server.types import (
    MCPServerContext,
    get_app_context,
    parse_uuid,
    validate_auth,
)

logger = get_logger(__name__)

# Export types for external modules
__all__ = [
    "MCPServerContext",
    "create_mcp_server",
    "get_app_context",
    "parse_uuid",
    "run_server",
    "server_lifespan",
    "validate_auth",
]


def _validate_auth_configuration(settings: object) -> None:
    """Validate authentication configuration at startup.

    Logs warnings for missing or insecure configurations.
    In production mode with MCP_AUTH_REQUIRED=true, raises ValueError
    for critical misconfigurations.

    Args:
        settings: Application settings object

    Raises:
        ValueError: If JWT_SECRET_KEY is missing and MCP_AUTH_REQUIRED is true
    """
    jwt_secret = getattr(settings, "JWT_SECRET_KEY", None)
    api_key = getattr(settings, "MCP_API_KEY", None)
    auth_required = getattr(settings, "MCP_AUTH_REQUIRED", False)

    if not jwt_secret:
        if auth_required:
            raise ValueError(
                "JWT_SECRET_KEY must be configured when MCP_AUTH_REQUIRED=true. "
                "Set JWT_SECRET_KEY in environment or disable auth requirement."
            )
        logger.warning(
            "JWT_SECRET_KEY not configured - Bearer token authentication will not work. "
            "Set JWT_SECRET_KEY environment variable for production use."
        )

    if not api_key:
        logger.warning(
            "MCP_API_KEY not configured - API key authentication will not work. "
            "Consider setting MCP_API_KEY for programmatic access."
        )


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[MCPServerContext]:
    """Manage server lifecycle with proper resource initialization and cleanup.

    This context manager initializes shared resources at startup (authenticator,
    settings) and provides a database session factory for per-request session
    creation.

    IMPORTANT: Database sessions are created per-request using db_session_factory
    to prevent race conditions and transaction conflicts in concurrent requests.
    Each tool/resource should create its own session using:

        with db_session_context(app_ctx.db_session_factory) as db:
            service = SomeService(db=db, settings=app_ctx.settings)
            result = service.do_something()

    Args:
        server: The FastMCP server instance

    Yields:
        MCPServerContext with db_session_factory and shared resources

    Raises:
        ValueError: If required authentication configuration is missing
    """
    logger.info("Initializing RAG Modulo MCP Server...")

    # Import here to avoid circular imports
    from rag_solution.file_management.database import get_db

    # Get settings instance
    settings = get_settings()

    # Validate authentication configuration at startup
    _validate_auth_configuration(settings)

    # Initialize authenticator (shared across requests - stateless)
    authenticator = MCPAuthenticator(settings=settings)

    # Create context with factory instead of shared session
    # Services are created per-request in tools/resources using db_session_context
    context = MCPServerContext(
        db_session_factory=get_db,
        authenticator=authenticator,
        settings=settings,
    )

    logger.info("RAG Modulo MCP Server initialized successfully")

    try:
        yield context
    finally:
        logger.info("RAG Modulo MCP Server shutdown complete")


def create_mcp_server() -> FastMCP:
    """Create and configure the MCP server with all RAG tools and resources.

    Returns:
        Configured FastMCP server instance ready to run
    """
    # Import here to avoid circular imports
    from mcp_server.resources import register_rag_resources
    from mcp_server.tools import register_rag_tools

    mcp = FastMCP(
        name="RAG Modulo",
        lifespan=server_lifespan,
    )

    # Register tools and resources
    register_rag_tools(mcp)
    register_rag_resources(mcp)

    logger.info("RAG Modulo MCP Server created with tools and resources")
    return mcp


def _run_sse_with_middleware(mcp: FastMCP, port: int) -> None:
    """Run SSE transport with header capture middleware.

    Creates a custom Starlette app that wraps MCP SSE routes with
    HeaderCaptureMiddleware to enable header extraction in tool handlers.

    Args:
        mcp: The FastMCP server instance
        port: Port number to listen on
    """
    import uvicorn
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route

    from mcp_server.middleware import HeaderCaptureMiddleware
    from mcp_server.types import set_global_auth_headers, set_session_headers

    # Create SSE transport for MCP
    sse_transport = SseServerTransport("/messages/")

    # Create handler that connects SSE transport to MCP server
    async def handle_sse(request):
        # Capture auth headers from the SSE connection and store globally
        # This ensures headers are available to tool handlers even when
        # context variables don't propagate across async boundaries
        auth_headers = [
            "authorization",
            "x-api-key",
            "x-authenticated-user",
            "x-spiffe-jwt",
        ]
        headers = {}
        for header_name in auth_headers:
            value = request.headers.get(header_name)
            if value:
                headers[header_name] = value
        if headers:
            set_global_auth_headers(headers)
            logger.info("handle_sse: Captured and stored auth headers globally: %s", list(headers.keys()))
        else:
            logger.debug("handle_sse: No auth headers found in SSE connection request")

        async with sse_transport.connect_sse(
            request.scope,
            request.receive,
            request._send,
        ) as streams:
            await mcp._mcp_server.run(
                streams[0],
                streams[1],
                mcp._mcp_server.create_initialization_options(),
            )

    # Create handler for MCP messages
    async def handle_messages(request):
        # Extract session_id and store headers before delegating to SSE transport
        # This ensures headers are available to tool handlers even in different async context
        session_id = request.query_params.get("session_id")

        # Capture auth-related headers
        auth_headers = [
            "authorization",
            "x-api-key",
            "x-authenticated-user",
            "x-spiffe-jwt",
        ]
        headers = {}
        for header_name in auth_headers:
            value = request.headers.get(header_name)
            if value:
                headers[header_name] = value

        if headers:
            # Store by session_id if available
            if session_id:
                set_session_headers(session_id, headers)
                logger.debug("Stored headers for session %s: %s", session_id, list(headers.keys()))
            # Also store globally as fallback
            set_global_auth_headers(headers)
            logger.debug("handle_messages: Stored headers globally: %s", list(headers.keys()))

        return await sse_transport.handle_post_message(
            request.scope,
            request.receive,
            request._send,
        )

    # Create Starlette app with MCP routes
    routes = [
        Route("/sse", endpoint=handle_sse),
        Route("/messages/", endpoint=handle_messages, methods=["POST"]),
    ]

    app = Starlette(routes=routes)

    # Add our header capture middleware
    app.add_middleware(HeaderCaptureMiddleware)

    logger.info("Running SSE server with header capture middleware on port %d", port)

    # Run with uvicorn
    uvicorn.run(app, host="127.0.0.1", port=port)


def run_server(transport: str | None = None, port: int | None = None) -> None:
    """Run the MCP server with the specified transport.

    Args:
        transport: Transport type - 'stdio', 'sse', or 'http'. If None, uses MCP_SERVER_TRANSPORT env var.
        port: Port number for SSE/HTTP transports. If None, uses MCP_SERVER_PORT env var.

    Raises:
        ValueError: If transport type is not supported
    """
    settings = get_settings()

    # Use config defaults if not specified
    transport = transport or settings.mcp_server_transport
    port = port or settings.mcp_server_port

    mcp = create_mcp_server()

    if transport == "stdio":
        logger.info("Starting MCP server with stdio transport")
        mcp.run(transport="stdio")
    elif transport == "sse":
        logger.info("Starting MCP server with SSE transport on port %d", port)
        # Use custom SSE server with header capture middleware
        _run_sse_with_middleware(mcp, port)
    elif transport == "http":
        logger.info("Starting MCP server with HTTP transport on port %d", port)
        mcp.settings.port = port

        async def run_http() -> None:
            await mcp.run_streamable_http_async()

        asyncio.run(run_http())
    else:
        raise ValueError(f"Unsupported transport: {transport}. Use 'stdio', 'sse', or 'http'")
