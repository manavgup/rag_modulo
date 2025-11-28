"""API schemas for MCP (Model Context Protocol) Gateway integration.

This module defines the data structures for MCP tool discovery,
invocation, and search result enrichment.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import UUID4, BaseModel, ConfigDict, Field


class MCPToolParameter(BaseModel):
    """Schema for an MCP tool input parameter.

    Attributes:
        name: Parameter name
        type: Parameter type (string, number, boolean, object, array)
        description: Human-readable description of the parameter
        required: Whether the parameter is required
        default: Default value if not provided
    """

    name: str
    type: str
    description: str | None = None
    required: bool = False
    default: Any | None = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class MCPTool(BaseModel):
    """Schema for an MCP tool definition.

    Attributes:
        name: Unique tool identifier
        description: Human-readable description of what the tool does
        parameters: List of input parameters for the tool
        category: Optional category for grouping tools
        version: Tool version (default: v1)
        enabled: Whether the tool is currently enabled
    """

    name: str
    description: str
    parameters: list[MCPToolParameter] = Field(default_factory=list)
    category: str | None = None
    version: str = "v1"
    enabled: bool = True

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class MCPToolsResponse(BaseModel):
    """Response schema for listing available MCP tools.

    Attributes:
        tools: List of available MCP tools
        total_count: Total number of tools available
        gateway_healthy: Whether the MCP gateway is healthy
    """

    tools: list[MCPTool]
    total_count: int
    gateway_healthy: bool = True

    model_config = ConfigDict(from_attributes=True)


class MCPInvocationInput(BaseModel):
    """Input schema for invoking an MCP tool.

    Attributes:
        arguments: Dictionary of argument name to value
        timeout: Optional timeout override in seconds
        user_id: Optional user ID for audit logging
    """

    arguments: dict[str, Any] = Field(default_factory=dict)
    timeout: float | None = Field(default=None, ge=1.0, le=300.0)
    user_id: UUID4 | None = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class MCPInvocationStatus(str, Enum):
    """Status of an MCP tool invocation."""

    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CIRCUIT_OPEN = "circuit_open"


class MCPInvocationOutput(BaseModel):
    """Output schema for an MCP tool invocation.

    Attributes:
        tool_name: Name of the tool that was invoked
        status: Invocation status (success, error, timeout, circuit_open)
        result: Result data from the tool (if successful)
        error: Error message (if failed)
        execution_time_ms: Execution time in milliseconds
        timestamp: When the invocation occurred
    """

    tool_name: str
    status: MCPInvocationStatus
    result: Any | None = None
    error: str | None = None
    execution_time_ms: float | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(from_attributes=True)


class MCPHealthStatus(BaseModel):
    """Health status of the MCP gateway.

    Attributes:
        healthy: Overall health status
        gateway_url: URL of the MCP gateway
        latency_ms: Health check latency in milliseconds
        circuit_breaker_state: Current circuit breaker state
        last_check: When the last health check was performed
        error: Error message if unhealthy
    """

    healthy: bool
    gateway_url: str
    latency_ms: float | None = None
    circuit_breaker_state: str = "closed"  # closed, open, half_open
    last_check: datetime = Field(default_factory=lambda: datetime.now(UTC))
    error: str | None = None

    model_config = ConfigDict(from_attributes=True)


class MCPEnrichmentConfig(BaseModel):
    """Configuration for MCP-based search result enrichment.

    Attributes:
        enabled: Whether enrichment is enabled
        tools: List of tool names to use for enrichment
        timeout: Timeout for enrichment operations
        parallel: Whether to run enrichment in parallel
        fail_silently: Whether to continue if enrichment fails
    """

    enabled: bool = True
    tools: list[str] = Field(default_factory=list)
    timeout: float = 30.0
    parallel: bool = True
    fail_silently: bool = True

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class MCPEnrichmentResult(BaseModel):
    """Result of MCP-based enrichment for a single item.

    Attributes:
        tool_name: Name of the tool used
        success: Whether the enrichment succeeded
        data: Enrichment data (if successful)
        error: Error message (if failed)
        execution_time_ms: Time taken for enrichment
    """

    tool_name: str
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    execution_time_ms: float | None = None

    model_config = ConfigDict(from_attributes=True)


class MCPEnrichedSearchResult(BaseModel):
    """Search result with MCP enrichment data.

    Attributes:
        original_score: Original relevance score
        enrichments: List of enrichment results from MCP tools
        combined_score: Combined score after enrichment (if applicable)
    """

    original_score: float
    enrichments: list[MCPEnrichmentResult] = Field(default_factory=list)
    combined_score: float | None = None

    model_config = ConfigDict(from_attributes=True)
