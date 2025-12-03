"""MCP Server implementation for RAG Modulo.

This module provides the core MCP server that exposes RAG Modulo functionality
as MCP tools and resources. Uses the FastMCP high-level API for clean integration.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from backend.core.config import get_settings
from backend.core.enhanced_logging import get_logger
from backend.mcp_server.auth import MCPAuthenticator

# Re-export from types for backward compatibility
from backend.mcp_server.types import (
    MCPServerContext,
    get_app_context,
    parse_uuid,
    validate_auth,
)
from backend.rag_solution.services.collection_service import CollectionService
from backend.rag_solution.services.file_management_service import FileManagementService
from backend.rag_solution.services.podcast_service import PodcastService
from backend.rag_solution.services.question_service import QuestionService
from backend.rag_solution.services.search_service import SearchService

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

    This context manager initializes all required services at startup
    and ensures proper cleanup on shutdown.

    Args:
        server: The FastMCP server instance

    Yields:
        MCPServerContext with initialized services

    Raises:
        ValueError: If required authentication configuration is missing
    """
    logger.info("Initializing RAG Modulo MCP Server...")

    # Import here to avoid circular imports
    from backend.rag_solution.repository.database import get_db

    # Get database session
    db_gen = get_db()
    db_session = next(db_gen)

    try:
        # Get settings instance
        settings = get_settings()

        # Validate authentication configuration at startup
        _validate_auth_configuration(settings)

        # Initialize services
        search_service = SearchService(db=db_session, settings=settings)
        collection_service = CollectionService(db=db_session, settings=settings)
        podcast_service = PodcastService(
            session=db_session,
            collection_service=collection_service,
            search_service=search_service,
        )
        question_service = QuestionService(db=db_session, settings=settings)
        file_service = FileManagementService(db=db_session, settings=settings)
        authenticator = MCPAuthenticator(settings=settings)

        context = MCPServerContext(
            db_session=db_session,
            search_service=search_service,
            collection_service=collection_service,
            podcast_service=podcast_service,
            question_service=question_service,
            file_service=file_service,
            authenticator=authenticator,
            settings=settings,
        )

        logger.info("RAG Modulo MCP Server initialized successfully")
        yield context

    finally:
        logger.info("Shutting down RAG Modulo MCP Server...")
        try:
            db_session.close()
        except Exception as e:
            logger.warning("Error closing database session: %s", e)
        logger.info("RAG Modulo MCP Server shutdown complete")


def create_mcp_server() -> FastMCP:
    """Create and configure the MCP server with all RAG tools and resources.

    Returns:
        Configured FastMCP server instance ready to run
    """
    # Import here to avoid circular imports
    from backend.mcp_server.resources import register_rag_resources
    from backend.mcp_server.tools import register_rag_tools

    mcp = FastMCP(
        name="RAG Modulo",
        lifespan=server_lifespan,
    )

    # Register tools and resources
    register_rag_tools(mcp)
    register_rag_resources(mcp)

    logger.info("RAG Modulo MCP Server created with tools and resources")
    return mcp


def run_server(transport: str = "stdio", port: int = 8080) -> None:
    """Run the MCP server with the specified transport.

    Args:
        transport: Transport type - 'stdio', 'sse', or 'http'
        port: Port number for SSE/HTTP transports (default: 8080)

    Raises:
        ValueError: If transport type is not supported
    """
    mcp = create_mcp_server()

    if transport == "stdio":
        logger.info("Starting MCP server with stdio transport")
        mcp.run(transport="stdio")
    elif transport == "sse":
        logger.info("Starting MCP server with SSE transport on port %d", port)
        mcp.settings.port = port
        mcp.run(transport="sse")
    elif transport == "http":
        logger.info("Starting MCP server with HTTP transport on port %d", port)
        mcp.settings.port = port

        async def run_http() -> None:
            await mcp.run_streamable_http_async()

        asyncio.run(run_http())
    else:
        raise ValueError(f"Unsupported transport: {transport}. Use 'stdio', 'sse', or 'http'")
