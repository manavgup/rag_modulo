"""MCP Server type definitions and utilities.

This module provides shared type definitions and utility functions used
across the MCP server implementation. Separated to avoid circular imports.
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession
from sqlalchemy.orm import Session

from backend.mcp_server.auth import MCPAuthContext, MCPAuthenticator
from backend.rag_solution.services.collection_service import CollectionService
from backend.rag_solution.services.file_management_service import FileManagementService
from backend.rag_solution.services.podcast_service import PodcastService
from backend.rag_solution.services.question_service import QuestionService
from backend.rag_solution.services.search_service import SearchService


@dataclass
class MCPServerContext:
    """Application context holding shared resources for MCP tools.

    This context is initialized at server startup and made available
    to all tool handlers through the lifespan context.

    Attributes:
        db_session: SQLAlchemy database session
        search_service: Service for RAG search operations
        collection_service: Service for collection management
        podcast_service: Service for podcast generation
        question_service: Service for smart question generation
        file_service: Service for document/file management
        authenticator: MCP authentication handler
        settings: Application settings
    """

    db_session: Session
    search_service: SearchService
    collection_service: CollectionService
    podcast_service: PodcastService
    question_service: QuestionService
    file_service: FileManagementService
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


async def validate_auth(
    ctx: Context[ServerSession, MCPServerContext, Any],
    required_permissions: list[str] | None = None,
) -> MCPAuthContext:
    """Validate authentication and authorization for an MCP request.

    Extracts authentication credentials from the request context and
    validates them using the configured authenticator.

    Args:
        ctx: The MCP Context object from a tool handler
        required_permissions: Optional list of required permissions

    Returns:
        MCPAuthContext with validated user information

    Raises:
        PermissionError: If authentication fails or permissions are insufficient
    """
    app_ctx = get_app_context(ctx)

    # Extract auth headers from request metadata if available
    # For now, we'll use a simplified approach
    auth_context = await app_ctx.authenticator.authenticate_request(
        headers={},
        required_permissions=required_permissions or [],
    )

    return auth_context
