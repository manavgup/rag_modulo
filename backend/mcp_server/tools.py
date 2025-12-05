"""MCP Tools for RAG Modulo.

This module defines MCP tools that expose RAG Modulo functionality:
- rag_whoami: Get current authenticated user info
- rag_list_collections: List available collections
- rag_search: Search documents in a collection
- rag_generate_podcast: Generate a podcast from collection content

Each tool validates authentication via MCP and forwards requests to the
FastAPI REST API, ensuring consistent behavior with the web interface.
"""

from typing import Any

import httpx
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

from core.config import get_settings
from core.enhanced_logging import get_logger
from mcp_server.permissions import TOOL_PERMISSIONS
from mcp_server.types import (
    MCPErrorType,
    MCPServerContext,
    _extract_headers_from_context,
    create_error_response,
    parse_uuid,
    validate_auth,
)

logger = get_logger(__name__)

# Get settings from centralized config
settings = get_settings()


def _build_auth_headers(ctx: Context[ServerSession, MCPServerContext, Any]) -> dict[str, str]:
    """Build authentication headers to forward to the API.

    Args:
        ctx: MCP context containing request headers

    Returns:
        Dictionary of authentication headers
    """
    headers = _extract_headers_from_context(ctx)
    auth_headers: dict[str, str] = {}

    if "authorization" in headers:
        auth_headers["Authorization"] = headers["authorization"]
    if "x-api-key" in headers:
        auth_headers["X-API-Key"] = headers["x-api-key"]
    if "x-authenticated-user" in headers:
        auth_headers["X-Authenticated-User"] = headers["x-authenticated-user"]

    return auth_headers


def register_rag_tools(mcp: FastMCP) -> None:
    """Register all RAG tools with the MCP server.

    Args:
        mcp: The FastMCP server instance to register tools with
    """

    @mcp.tool()  # type: ignore[misc]
    async def rag_whoami(
        ctx: Context[ServerSession, MCPServerContext, Any],
    ) -> dict[str, Any]:
        """Get current authenticated user information.

        Returns the user_id, username, and permissions of the currently
        authenticated user. Call this tool first to discover your identity.

        Returns:
            Dictionary containing:
            - user_id: UUID of the authenticated user
            - username: Username or email of the user
            - permissions: List of permissions granted
            - auth_method: How the user was authenticated

        Raises:
            PermissionError: If authentication fails
        """
        try:
            auth_context = await validate_auth(ctx, TOOL_PERMISSIONS["rag_whoami"])
        except PermissionError as e:
            logger.warning("Whoami authorization failed: %s", e)
            return create_error_response(e, MCPErrorType.AUTHORIZATION)

        await ctx.info(f"Authenticated as {auth_context.username}")

        return {
            "user_id": str(auth_context.user_id),
            "username": auth_context.username,
            "permissions": auth_context.permissions,
            "auth_method": auth_context.auth_method,
        }

    @mcp.tool()  # type: ignore[misc]
    async def rag_list_collections(
        user_id: str,
        ctx: Context[ServerSession, MCPServerContext, Any],
    ) -> dict[str, Any]:
        """List collections accessible to the user.

        Calls the REST API to get all collections the user has access to.

        Args:
            user_id: UUID of the user
            ctx: MCP context

        Returns:
            Dictionary containing:
            - collections: List of collection summaries
            - count: Total number of collections

        Raises:
            PermissionError: If authentication fails
        """
        try:
            await validate_auth(ctx, TOOL_PERMISSIONS["rag_list_collections"])
        except PermissionError as e:
            logger.warning("List collections authorization failed: %s", e)
            return create_error_response(e, MCPErrorType.AUTHORIZATION)

        try:
            # Validate user_id format (for future use in user-scoped queries)
            _ = parse_uuid(user_id, "user_id")
        except ValueError as e:
            return create_error_response(e, MCPErrorType.VALIDATION)

        await ctx.info("Fetching collections from API...")

        # Call the REST API
        auth_headers = _build_auth_headers(ctx)
        api_url = f"{settings.rag_api_base_url}/api/collections"

        try:
            async with httpx.AsyncClient(timeout=settings.mcp_timeout) as client:
                response = await client.get(api_url, headers=auth_headers)

                if response.status_code == 200:
                    collections = response.json()
                    await ctx.info(f"Found {len(collections)} collections")
                    return {
                        "collections": collections,
                        "count": len(collections),
                    }
                else:
                    error_msg = f"API error: {response.status_code}"
                    logger.error("List collections failed: %s - %s", error_msg, response.text)
                    return create_error_response(error_msg, MCPErrorType.OPERATION)

        except httpx.RequestError as e:
            error_msg = f"Failed to connect to API: {e}"
            logger.error(error_msg)
            return create_error_response(error_msg, MCPErrorType.OPERATION)

    @mcp.tool()  # type: ignore[misc]
    async def rag_search(
        collection_id: str,
        question: str,
        user_id: str,
        ctx: Context[ServerSession, MCPServerContext, Any],
    ) -> dict[str, Any]:
        """Search documents in a collection.

        Calls the REST API to perform semantic search across the collection.
        Result count is controlled by the API's NUMBER_OF_RESULTS setting.

        Args:
            collection_id: UUID of the collection to search
            question: The search query
            user_id: UUID of the user performing the search
            ctx: MCP context

        Returns:
            Dictionary containing:
            - answer: Generated answer from RAG
            - sources: List of source documents
            - metadata: Search metadata

        Raises:
            PermissionError: If authentication fails
        """
        try:
            await validate_auth(ctx, TOOL_PERMISSIONS["rag_search"])
        except PermissionError as e:
            logger.warning("Search authorization failed: %s", e)
            return create_error_response(e, MCPErrorType.AUTHORIZATION)

        # Validate inputs
        try:
            collection_uuid = parse_uuid(collection_id, "collection_id")
            user_uuid = parse_uuid(user_id, "user_id")
        except ValueError as e:
            return create_error_response(e, MCPErrorType.VALIDATION)

        await ctx.info(f"Searching collection {collection_id}...")

        # Call the REST API
        auth_headers = _build_auth_headers(ctx)
        api_url = f"{settings.rag_api_base_url}/api/search"

        search_payload = {
            "question": question,
            "collection_id": str(collection_uuid),
            "user_id": str(user_uuid),
        }

        try:
            async with httpx.AsyncClient(timeout=settings.mcp_timeout) as client:
                response = await client.post(
                    api_url,
                    json=search_payload,
                    headers=auth_headers,
                )

                if response.status_code == 200:
                    result: dict[str, Any] = response.json()
                    await ctx.info("Search completed successfully")
                    return result
                else:
                    error_msg = f"Search API error: {response.status_code}"
                    logger.error("Search failed: %s - %s", error_msg, response.text)
                    return create_error_response(error_msg, MCPErrorType.OPERATION)

        except httpx.RequestError as e:
            error_msg = f"Failed to connect to API: {e}"
            logger.error(error_msg)
            return create_error_response(error_msg, MCPErrorType.OPERATION)

    @mcp.tool()  # type: ignore[misc]
    async def rag_generate_podcast(
        collection_id: str,
        user_id: str,
        ctx: Context[ServerSession, MCPServerContext, Any],
        title: str | None = None,
        description: str | None = None,
        duration: str = "medium",
        language: str = "en",
    ) -> dict[str, Any]:
        """Generate an AI podcast from collection content.

        Calls the REST API to generate a podcast script from the collection.
        Audio generation requires additional processing time.

        Args:
            collection_id: UUID of the collection
            user_id: UUID of the user
            ctx: MCP context
            title: Optional podcast title
            description: Optional description/focus area
            duration: Podcast length - short, medium, long, extended
            language: Language code (default: en)

        Returns:
            Dictionary containing:
            - status: Generation status
            - script: Generated podcast script (if ready)
            - message: Status message

        Raises:
            PermissionError: If authentication fails
        """
        try:
            await validate_auth(ctx, TOOL_PERMISSIONS["rag_generate_podcast"])
        except PermissionError as e:
            logger.warning("Podcast authorization failed: %s", e)
            return create_error_response(e, MCPErrorType.AUTHORIZATION)

        # Validate inputs
        try:
            collection_uuid = parse_uuid(collection_id, "collection_id")
            user_uuid = parse_uuid(user_id, "user_id")
        except ValueError as e:
            return create_error_response(e, MCPErrorType.VALIDATION)

        valid_durations = {"short", "medium", "long", "extended"}
        if duration.lower() not in valid_durations:
            return create_error_response(
                f"duration must be one of: {', '.join(valid_durations)}",
                MCPErrorType.VALIDATION,
            )

        await ctx.info(f"Generating podcast for collection {collection_id}...")

        # Call the REST API
        auth_headers = _build_auth_headers(ctx)
        api_url = f"{settings.rag_api_base_url}/api/podcasts/generate"

        podcast_payload = {
            "collection_id": str(collection_uuid),
            "user_id": str(user_uuid),
            "duration": duration,
            "language": language,
        }
        if title:
            podcast_payload["title"] = title
        if description:
            podcast_payload["description"] = description

        try:
            # Longer timeout for generation
            async with httpx.AsyncClient(timeout=settings.mcp_timeout * 2) as client:
                response = await client.post(
                    api_url,
                    json=podcast_payload,
                    headers=auth_headers,
                )

                if response.status_code == 200:
                    result: dict[str, Any] = response.json()
                    await ctx.info("Podcast generation completed")
                    return result
                elif response.status_code == 202:
                    # Accepted - generation in progress
                    async_result: dict[str, Any] = response.json()
                    await ctx.info("Podcast generation started (async)")
                    return {
                        "status": "processing",
                        "message": "Podcast generation started. Check status endpoint for completion.",
                        **async_result,
                    }
                else:
                    error_msg = f"Podcast API error: {response.status_code}"
                    logger.error("Podcast generation failed: %s - %s", error_msg, response.text)
                    return create_error_response(error_msg, MCPErrorType.OPERATION)

        except httpx.RequestError as e:
            error_msg = f"Failed to connect to API: {e}"
            logger.error(error_msg)
            return create_error_response(error_msg, MCPErrorType.OPERATION)
