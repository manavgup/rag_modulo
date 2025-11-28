"""MCP Gateway router for RAG Modulo API.

This module provides FastAPI router endpoints for MCP (Model Context Protocol)
Gateway integration, enabling tool discovery and invocation capabilities.

API Endpoints:
- GET /api/v1/mcp/tools - List available MCP tools
- POST /api/v1/mcp/tools/{name}/invoke - Invoke a specific MCP tool
- GET /api/v1/mcp/health - Check MCP gateway health
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from core.config import Settings, get_settings
from core.logging_utils import get_logger
from rag_solution.core.dependencies import get_current_user
from rag_solution.schemas.mcp_schema import (
    MCPHealthStatus,
    MCPInvocationInput,
    MCPInvocationOutput,
    MCPInvocationStatus,
    MCPToolsResponse,
)
from rag_solution.services.mcp_gateway_client import ResilientMCPGatewayClient

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/mcp", tags=["mcp"])


def get_mcp_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ResilientMCPGatewayClient:
    """Dependency to create MCP gateway client.

    Args:
        settings: Application settings from dependency injection

    Returns:
        ResilientMCPGatewayClient: Initialized MCP client instance
    """
    return ResilientMCPGatewayClient(settings)


@router.get(
    "/health",
    response_model=MCPHealthStatus,
    summary="Check MCP gateway health",
    description="Perform a health check on the MCP Context Forge gateway",
    responses={
        200: {"description": "Health check completed (see healthy field for status)"},
        503: {"description": "MCP integration is disabled"},
    },
)
async def mcp_health(
    settings: Annotated[Settings, Depends(get_settings)],
    mcp_client: Annotated[ResilientMCPGatewayClient, Depends(get_mcp_client)],
) -> MCPHealthStatus:
    """Check MCP gateway health status.

    Returns health information including:
    - Gateway availability
    - Latency
    - Circuit breaker state

    Args:
        settings: Application settings
        mcp_client: MCP gateway client

    Returns:
        MCPHealthStatus: Health status information
    """
    if not settings.mcp_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP integration is disabled",
        )

    return await mcp_client.check_health()


@router.get(
    "/tools",
    response_model=MCPToolsResponse,
    summary="List available MCP tools",
    description="Retrieve a list of all available MCP tools from the gateway",
    responses={
        200: {"description": "List of available MCP tools"},
        503: {"description": "MCP integration is disabled or gateway unavailable"},
    },
)
async def list_tools(
    current_user: Annotated[dict, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    mcp_client: Annotated[ResilientMCPGatewayClient, Depends(get_mcp_client)],
) -> MCPToolsResponse:
    """List all available MCP tools.

    Returns tools available for invocation, including their:
    - Name and description
    - Input parameters
    - Category and version

    SECURITY: Requires authentication.

    Args:
        current_user: Authenticated user from JWT token
        settings: Application settings
        mcp_client: MCP gateway client

    Returns:
        MCPToolsResponse: List of available tools

    Raises:
        HTTPException: If MCP is disabled or gateway unavailable
    """
    if not settings.mcp_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP integration is disabled",
        )

    logger.info(
        "Listing MCP tools",
        extra={
            "user_id": current_user.get("uuid"),
        },
    )

    response = await mcp_client.list_tools()

    if not response.gateway_healthy:
        logger.warning(
            "MCP gateway unhealthy when listing tools",
            extra={
                "user_id": current_user.get("uuid"),
            },
        )

    return response


@router.post(
    "/tools/{tool_name}/invoke",
    response_model=MCPInvocationOutput,
    summary="Invoke an MCP tool",
    description="Invoke a specific MCP tool with the provided arguments",
    responses={
        200: {"description": "Tool invocation completed (check status field)"},
        400: {"description": "Invalid input data"},
        404: {"description": "Tool not found"},
        503: {"description": "MCP integration is disabled"},
    },
)
async def invoke_tool(
    tool_name: str,
    invocation_input: MCPInvocationInput,
    current_user: Annotated[dict, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    mcp_client: Annotated[ResilientMCPGatewayClient, Depends(get_mcp_client)],
) -> MCPInvocationOutput:
    """Invoke a specific MCP tool.

    Executes the named tool with provided arguments. Implements graceful
    degradation - tool failures are returned in the response status rather
    than throwing exceptions (except for validation errors).

    SECURITY: Requires authentication.

    Args:
        tool_name: Name of the tool to invoke
        invocation_input: Tool arguments and optional timeout
        current_user: Authenticated user from JWT token
        settings: Application settings
        mcp_client: MCP gateway client

    Returns:
        MCPInvocationOutput: Tool execution result

    Raises:
        HTTPException: If MCP is disabled or input validation fails
    """
    if not settings.mcp_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP integration is disabled",
        )

    if not tool_name or not tool_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tool name is required",
        )

    user_id = current_user.get("uuid")

    logger.info(
        "Invoking MCP tool",
        extra={
            "tool_name": tool_name,
            "user_id": user_id,
            "has_arguments": bool(invocation_input.arguments),
        },
    )

    result = await mcp_client.invoke_tool(
        tool_name=tool_name.strip(),
        arguments=invocation_input.arguments,
        timeout=invocation_input.timeout,
    )

    # Log result status
    if result.status == MCPInvocationStatus.SUCCESS:
        logger.info(
            "MCP tool invocation succeeded",
            extra={
                "tool_name": tool_name,
                "user_id": user_id,
                "execution_time_ms": result.execution_time_ms,
            },
        )
    else:
        logger.warning(
            "MCP tool invocation failed",
            extra={
                "tool_name": tool_name,
                "user_id": user_id,
                "status": result.status.value,
                "error": result.error,
            },
        )

    return result


@router.get(
    "/metrics",
    summary="Get MCP client metrics",
    description="Retrieve Prometheus-ready metrics from the MCP client",
    responses={
        200: {"description": "Client metrics"},
        503: {"description": "MCP integration is disabled"},
    },
)
async def get_metrics(
    current_user: Annotated[dict, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    mcp_client: Annotated[ResilientMCPGatewayClient, Depends(get_mcp_client)],
) -> dict:
    """Get MCP client metrics for monitoring.

    Returns Prometheus-ready metrics including:
    - Request counts (total, success, failed)
    - Circuit breaker state
    - Health check statistics

    SECURITY: Requires authentication.

    Args:
        current_user: Authenticated user from JWT token
        settings: Application settings
        mcp_client: MCP gateway client

    Returns:
        dict: Client metrics
    """
    if not settings.mcp_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP integration is disabled",
        )

    return mcp_client.get_metrics()
