"""Pydantic schemas for MCP Gateway API endpoints.

These schemas define the request/response structures for MCP tool invocation
and search result enrichment endpoints.
"""

from typing import Any

from pydantic import UUID4, BaseModel, ConfigDict, Field


class MCPToolInput(BaseModel):
    """Input schema for MCP tool invocation.

    Attributes:
        tool_name: Name of the MCP tool to invoke
        arguments: Tool-specific input arguments
        timeout: Optional timeout override in seconds
    """

    tool_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the MCP tool to invoke",
        json_schema_extra={"examples": ["powerpoint", "visualization"]},
    )
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="Tool-specific input arguments",
    )
    timeout: float | None = Field(
        default=None,
        ge=1.0,
        le=300.0,
        description="Optional timeout override in seconds (1-300)",
    )

    model_config = ConfigDict(extra="forbid")


class MCPToolOutput(BaseModel):
    """Output schema for MCP tool invocation.

    Attributes:
        tool_name: Name of the invoked tool
        success: Whether the invocation succeeded
        result: Tool output data if successful
        error: Error message if failed
        duration_ms: Execution time in milliseconds
    """

    tool_name: str = Field(..., description="Name of the invoked tool")
    success: bool = Field(..., description="Whether the invocation succeeded")
    result: dict[str, Any] | None = Field(
        default=None,
        description="Tool output data if successful",
    )
    error: str | None = Field(
        default=None,
        description="Error message if failed",
    )
    duration_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Execution time in milliseconds",
    )

    model_config = ConfigDict(from_attributes=True)


class MCPToolDefinition(BaseModel):
    """Schema for MCP tool definition.

    Attributes:
        name: Tool name/identifier
        description: Human-readable description
        input_schema: JSON Schema for tool input
    """

    name: str = Field(..., description="Tool name/identifier")
    description: str = Field(..., description="Human-readable description")
    input_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema for tool input",
    )

    model_config = ConfigDict(from_attributes=True)


class MCPToolListOutput(BaseModel):
    """Output schema for listing available MCP tools.

    Attributes:
        tools: List of available tool definitions
        gateway_healthy: Whether the MCP gateway is healthy
    """

    tools: list[MCPToolDefinition] = Field(
        default_factory=list,
        description="List of available tool definitions",
    )
    gateway_healthy: bool = Field(
        default=False,
        description="Whether the MCP gateway is healthy",
    )

    model_config = ConfigDict(from_attributes=True)


class MCPEnrichmentInput(BaseModel):
    """Input schema for search result enrichment.

    Attributes:
        answer: The RAG-generated answer to enrich
        documents: Source documents used for the answer
        query: Original user query
        collection_id: Collection ID for context
        tools: List of enrichment tools to use
    """

    answer: str = Field(
        ...,
        min_length=1,
        description="The RAG-generated answer to enrich",
    )
    documents: list[dict[str, Any]] = Field(
        ...,
        min_length=1,
        description="Source documents used for the answer",
    )
    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Original user query",
    )
    collection_id: UUID4 = Field(..., description="Collection ID for context")
    tools: list[str] = Field(
        ...,
        min_length=1,
        description="List of enrichment tools to use",
        json_schema_extra={"examples": [["powerpoint"], ["powerpoint", "visualization"]]},
    )

    model_config = ConfigDict(extra="forbid")


class MCPEnrichmentArtifact(BaseModel):
    """Schema for an enrichment-generated artifact.

    Attributes:
        tool_name: Name of the tool that generated this artifact
        artifact_type: Type of artifact
        content: Artifact content (may be base64 for binary)
        content_type: MIME type of the content
        metadata: Additional metadata
    """

    tool_name: str = Field(..., description="Name of the tool that generated this artifact")
    artifact_type: str = Field(..., description="Type of artifact")
    content: str = Field(..., description="Artifact content (may be base64 for binary)")
    content_type: str = Field(..., description="MIME type of the content")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )

    model_config = ConfigDict(from_attributes=True)


class MCPEnrichmentOutput(BaseModel):
    """Output schema for search result enrichment.

    Attributes:
        original_answer: The original answer from RAG
        artifacts: List of generated artifacts
        enrichment_metadata: Metadata about the enrichment process
        errors: List of any errors during enrichment
    """

    original_answer: str = Field(..., description="The original answer from RAG")
    artifacts: list[MCPEnrichmentArtifact] = Field(
        default_factory=list,
        description="List of generated artifacts",
    )
    enrichment_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the enrichment process",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="List of any errors during enrichment",
    )

    model_config = ConfigDict(from_attributes=True)


class MCPHealthOutput(BaseModel):
    """Output schema for MCP gateway health check.

    Attributes:
        gateway_url: URL of the MCP gateway
        healthy: Whether the gateway is healthy
        circuit_breaker_state: Current circuit breaker state
        available_tools: Number of available tools
        error: Error message if unhealthy
    """

    gateway_url: str = Field(..., description="URL of the MCP gateway")
    healthy: bool = Field(..., description="Whether the gateway is healthy")
    circuit_breaker_state: str = Field(
        default="unknown",
        description="Current circuit breaker state (closed/open/half_open)",
    )
    available_tools: int = Field(
        default=0,
        ge=0,
        description="Number of available tools",
    )
    error: str | None = Field(
        default=None,
        description="Error message if unhealthy",
    )

    model_config = ConfigDict(from_attributes=True)
