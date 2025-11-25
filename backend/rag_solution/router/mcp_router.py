"""MCP Gateway router for RAG Modulo API.

This module provides FastAPI router endpoints for MCP tool invocation and
search result enrichment. Implements two core endpoints:

1. POST /api/mcp/tools/invoke - Invoke an MCP tool
2. POST /api/mcp/enrich - Enrich search results with MCP tools

Additional endpoints:
- GET /api/mcp/tools - List available tools
- GET /api/mcp/health - Gateway health status
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from core.config import Settings, get_settings
from core.logging_utils import get_logger
from rag_solution.core.dependencies import get_current_user
from rag_solution.mcp.enricher import SearchResultEnricher
from rag_solution.mcp.gateway_client import MCPGatewayClient
from rag_solution.schemas.mcp_schema import (
    MCPEnrichmentArtifact,
    MCPEnrichmentInput,
    MCPEnrichmentOutput,
    MCPHealthOutput,
    MCPToolDefinition,
    MCPToolInput,
    MCPToolListOutput,
    MCPToolOutput,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/mcp", tags=["mcp"])

# Singleton client instance (created on first use)
_mcp_client: MCPGatewayClient | None = None


def get_mcp_client(settings: Annotated[Settings, Depends(get_settings)]) -> MCPGatewayClient:
    """Get or create the MCP Gateway client singleton.

    Args:
        settings: Application settings from dependency injection

    Returns:
        MCPGatewayClient: Configured MCP gateway client
    """
    global _mcp_client

    if _mcp_client is None:
        _mcp_client = MCPGatewayClient(
            gateway_url=settings.mcp_gateway_url,
            api_key=settings.mcp_gateway_api_key,
            timeout=settings.mcp_gateway_timeout,
            health_check_timeout=settings.mcp_gateway_health_timeout,
        )
        logger.info("MCP Gateway client initialized for %s", settings.mcp_gateway_url)

    return _mcp_client


def get_enricher(
    settings: Annotated[Settings, Depends(get_settings)],
    mcp_client: Annotated[MCPGatewayClient, Depends(get_mcp_client)],
) -> SearchResultEnricher:
    """Get the search result enricher.

    Args:
        settings: Application settings
        mcp_client: MCP gateway client

    Returns:
        SearchResultEnricher: Configured enricher instance
    """
    return SearchResultEnricher(
        mcp_client=mcp_client,
        settings=settings,
        max_concurrent_tools=settings.mcp_max_concurrent_tools,
        enrichment_timeout=settings.mcp_enrichment_timeout,
    )


@router.get(
    "/health",
    response_model=MCPHealthOutput,
    summary="Check MCP Gateway health status",
    description="Returns health status of the MCP Gateway including circuit breaker state",
    responses={
        200: {"description": "Health status retrieved"},
        503: {"description": "Gateway unavailable"},
    },
)
async def health_check(
    mcp_client: Annotated[MCPGatewayClient, Depends(get_mcp_client)],
) -> MCPHealthOutput:
    """Check MCP Gateway health status.

    Returns health information including:
    - Gateway connectivity
    - Circuit breaker state
    - Number of available tools
    """
    try:
        is_healthy = await mcp_client.health_check()
        tools_count = 0

        if is_healthy:
            tools = await mcp_client.list_tools()
            tools_count = len(tools)

        return MCPHealthOutput(
            gateway_url=mcp_client.gateway_url,
            healthy=is_healthy,
            circuit_breaker_state=mcp_client.circuit_breaker.state.value,
            available_tools=tools_count,
            error=None if is_healthy else "Gateway health check failed",
        )

    except Exception as e:
        logger.error("MCP health check failed: %s", str(e))
        return MCPHealthOutput(
            gateway_url=mcp_client.gateway_url,
            healthy=False,
            circuit_breaker_state=mcp_client.circuit_breaker.state.value,
            available_tools=0,
            error=str(e),
        )


@router.get(
    "/tools",
    response_model=MCPToolListOutput,
    summary="List available MCP tools",
    description="Returns list of tools available from the MCP Gateway",
    responses={
        200: {"description": "Tool list retrieved"},
        503: {"description": "Gateway unavailable"},
    },
)
async def list_tools(
    mcp_client: Annotated[MCPGatewayClient, Depends(get_mcp_client)],
    _current_user: Annotated[dict, Depends(get_current_user)],
) -> MCPToolListOutput:
    """List available MCP tools.

    SECURITY: Requires authentication.

    Returns:
        List of tool definitions with names, descriptions, and input schemas
    """
    try:
        is_healthy = await mcp_client.health_check()
        tools_data = await mcp_client.list_tools()

        tools = [
            MCPToolDefinition(
                name=t.get("name", "unknown"),
                description=t.get("description", ""),
                input_schema=t.get("inputSchema", {}),
            )
            for t in tools_data
        ]

        return MCPToolListOutput(
            tools=tools,
            gateway_healthy=is_healthy,
        )

    except Exception as e:
        logger.error("Failed to list MCP tools: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MCP Gateway unavailable: {e!s}",
        ) from e


@router.post(
    "/tools/invoke",
    response_model=MCPToolOutput,
    summary="Invoke an MCP tool",
    description="Invoke a specific MCP tool with provided arguments",
    responses={
        200: {"description": "Tool invoked successfully"},
        400: {"description": "Invalid tool or arguments"},
        401: {"description": "Unauthorized"},
        503: {"description": "Gateway unavailable or circuit breaker open"},
    },
)
async def invoke_tool(
    tool_input: MCPToolInput,
    mcp_client: Annotated[MCPGatewayClient, Depends(get_mcp_client)],
    _current_user: Annotated[dict, Depends(get_current_user)],
) -> MCPToolOutput:
    """Invoke an MCP tool.

    SECURITY: Requires authentication.

    Args:
        tool_input: Tool name and arguments

    Returns:
        MCPToolOutput with result or error
    """
    logger.info(
        "Tool invocation requested",
        extra={
            "tool_name": tool_input.tool_name,
            "has_timeout": tool_input.timeout is not None,
        },
    )

    result = await mcp_client.invoke_tool(
        tool_name=tool_input.tool_name,
        arguments=tool_input.arguments,
        timeout=tool_input.timeout,
    )

    return MCPToolOutput(
        tool_name=result.tool_name,
        success=result.success,
        result=result.result,
        error=result.error,
        duration_ms=result.duration_ms,
    )


@router.post(
    "/enrich",
    response_model=MCPEnrichmentOutput,
    summary="Enrich search results with MCP tools",
    description="Generate artifacts (presentations, visualizations) from search results",
    responses={
        200: {"description": "Enrichment completed (may include partial results)"},
        400: {"description": "Invalid input"},
        401: {"description": "Unauthorized"},
    },
)
async def enrich_results(
    enrichment_input: MCPEnrichmentInput,
    enricher: Annotated[SearchResultEnricher, Depends(get_enricher)],
    _current_user: Annotated[dict, Depends(get_current_user)],
) -> MCPEnrichmentOutput:
    """Enrich search results with MCP tools.

    SECURITY: Requires authentication.

    This endpoint is designed for graceful degradation:
    - Partial results are returned if some tools fail
    - Core answer is always preserved
    - Errors are logged but don't cause HTTP failures

    Args:
        enrichment_input: Search results and tools to apply

    Returns:
        MCPEnrichmentOutput with original answer, artifacts, and any errors
    """
    logger.info(
        "Enrichment requested",
        extra={
            "tools": enrichment_input.tools,
            "collection_id": str(enrichment_input.collection_id),
            "document_count": len(enrichment_input.documents),
        },
    )

    result = await enricher.enrich_results(
        answer=enrichment_input.answer,
        documents=enrichment_input.documents,
        query=enrichment_input.query,
        collection_id=enrichment_input.collection_id,
        tool_hints=enrichment_input.tools,
    )

    # Convert dataclass artifacts to Pydantic models
    artifacts = [
        MCPEnrichmentArtifact(
            tool_name=a.tool_name,
            artifact_type=a.artifact_type,
            content=a.content if isinstance(a.content, str) else "",
            content_type=a.content_type,
            metadata=a.metadata,
        )
        for a in result.artifacts
    ]

    return MCPEnrichmentOutput(
        original_answer=result.original_answer,
        artifacts=artifacts,
        enrichment_metadata=result.enrichment_metadata,
        errors=result.errors,
    )
