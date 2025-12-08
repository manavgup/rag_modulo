"""Pydantic schemas for Agent Configuration and Execution Hooks.

This module defines the request/response schemas for the Agent Configuration API
and execution hooks for the 3-stage search pipeline.

The 3-stage pipeline supports:
- Stage 1: Pre-Search Agents (query expansion, language detection, etc.)
- Stage 2: Post-Search Agents (re-ranking, deduplication, PII redaction)
- Stage 3: Response Agents (PowerPoint, PDF, Chart generation)

Reference: GitHub Issue #697
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import UUID4, BaseModel, ConfigDict, Field


class AgentStage(str, Enum):
    """Pipeline stages where agents can execute."""

    PRE_SEARCH = "pre_search"
    POST_SEARCH = "post_search"
    RESPONSE = "response"


class AgentConfigStatus(str, Enum):
    """Agent configuration status."""

    ACTIVE = "active"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"


class AgentExecutionStatus(str, Enum):
    """Status of an individual agent execution."""

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"
    CIRCUIT_OPEN = "circuit_open"


# ============================================================================
# Agent Configuration Schemas
# ============================================================================


class AgentConfigInput(BaseModel):
    """Schema for creating a new agent configuration.

    Attributes:
        name: Human-readable name for the agent config
        description: Description of what the agent does
        agent_type: Type identifier (e.g., "query_expander", "reranker")
        stage: Pipeline stage where this agent executes
        handler_module: Python module path for the handler
        handler_class: Class name within the handler module
        default_config: Default configuration for the agent
        timeout_seconds: Maximum execution time before circuit breaker trips
        max_retries: Maximum retry attempts on failure
        priority: Default execution priority (lower = earlier execution)
    """

    name: str = Field(..., min_length=1, max_length=255, description="Human-readable agent config name")
    description: str | None = Field(default=None, max_length=2000, description="Agent description")
    agent_type: str = Field(..., min_length=1, max_length=100, description="Agent type identifier")
    stage: AgentStage = Field(default=AgentStage.PRE_SEARCH, description="Pipeline stage")
    handler_module: str = Field(..., min_length=1, max_length=500, description="Python module path")
    handler_class: str = Field(..., min_length=1, max_length=255, description="Handler class name")
    default_config: dict[str, Any] = Field(default_factory=dict, description="Default configuration")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Max execution time")
    max_retries: int = Field(default=2, ge=0, le=5, description="Max retry attempts")
    priority: int = Field(default=100, ge=0, le=1000, description="Execution priority")


class AgentConfigUpdate(BaseModel):
    """Schema for updating an existing agent configuration.

    All fields are optional - only provided fields will be updated.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    default_config: dict[str, Any] | None = Field(default=None)
    timeout_seconds: int | None = Field(default=None, ge=1, le=300)
    max_retries: int | None = Field(default=None, ge=0, le=5)
    priority: int | None = Field(default=None, ge=0, le=1000)
    status: AgentConfigStatus | None = Field(default=None)


class AgentConfigOutput(BaseModel):
    """Schema for agent configuration response data.

    Attributes:
        id: Unique identifier for the agent config
        name: Human-readable name
        description: Agent description
        agent_type: Type identifier
        stage: Pipeline stage
        handler_module: Python module path
        handler_class: Handler class name
        default_config: Default configuration
        timeout_seconds: Max execution time
        max_retries: Max retry attempts
        priority: Execution priority
        is_system: Whether this is a built-in system agent
        owner_user_id: User who created this config
        status: Current status
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: UUID4
    name: str
    description: str | None
    agent_type: str
    stage: str
    handler_module: str
    handler_class: str
    default_config: dict[str, Any]
    timeout_seconds: int
    max_retries: int
    priority: int
    is_system: bool
    owner_user_id: UUID4 | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentConfigListResponse(BaseModel):
    """Schema for paginated agent config list response."""

    configs: list[AgentConfigOutput]
    total: int
    skip: int
    limit: int


# ============================================================================
# Collection-Agent Association Schemas
# ============================================================================


class CollectionAgentInput(BaseModel):
    """Schema for associating an agent with a collection.

    Attributes:
        agent_config_id: UUID of the agent configuration
        enabled: Whether agent is enabled for this collection
        priority: Execution priority override
        config_override: Collection-specific configuration overrides
    """

    agent_config_id: UUID4 = Field(..., description="Agent configuration ID")
    enabled: bool = Field(default=True, description="Whether agent is enabled")
    priority: int = Field(default=100, ge=0, le=1000, description="Priority override")
    config_override: dict[str, Any] = Field(default_factory=dict, description="Config overrides")


class CollectionAgentUpdate(BaseModel):
    """Schema for updating a collection-agent association."""

    enabled: bool | None = Field(default=None)
    priority: int | None = Field(default=None, ge=0, le=1000)
    config_override: dict[str, Any] | None = Field(default=None)


class CollectionAgentOutput(BaseModel):
    """Schema for collection-agent association response data."""

    id: UUID4
    collection_id: UUID4
    agent_config_id: UUID4
    enabled: bool
    priority: int
    config_override: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    agent_config: AgentConfigOutput | None = None

    model_config = ConfigDict(from_attributes=True)


class CollectionAgentListResponse(BaseModel):
    """Schema for collection agent associations list."""

    associations: list[CollectionAgentOutput]
    total: int


class BatchPriorityUpdate(BaseModel):
    """Schema for batch updating agent priorities.

    Attributes:
        priorities: Mapping of association ID to new priority
    """

    priorities: dict[UUID4, int] = Field(..., description="Association ID to priority mapping")


# ============================================================================
# Agent Execution Schemas
# ============================================================================


class AgentContext(BaseModel):
    """Context passed to agents during pipeline execution.

    This provides all the information an agent needs to execute,
    including the search input, retrieved documents, and stage-specific data.

    Attributes:
        search_input: Original search request data
        collection_id: Collection being searched
        user_id: User making the request
        stage: Current pipeline stage
        query: Current query (may be modified by previous agents)
        query_results: Retrieved documents (populated after retrieval stage)
        previous_results: Results from previously executed agents in this stage
        config: Merged configuration for this agent
        metadata: Additional context metadata
    """

    search_input: dict[str, Any] = Field(..., description="Original search request")
    collection_id: UUID4 = Field(..., description="Collection ID")
    user_id: UUID4 = Field(..., description="User ID")
    stage: AgentStage = Field(..., description="Current pipeline stage")
    query: str = Field(..., description="Current query")
    query_results: list[dict[str, Any]] = Field(default_factory=list, description="Retrieved documents")
    previous_results: list["AgentResult"] = Field(default_factory=list, description="Previous agent results")
    config: dict[str, Any] = Field(default_factory=dict, description="Merged agent config")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class AgentResult(BaseModel):
    """Result from an agent execution.

    Attributes:
        agent_config_id: ID of the agent configuration
        agent_name: Name of the agent
        agent_type: Type of the agent
        stage: Pipeline stage where executed
        status: Execution status
        execution_time_ms: Time taken in milliseconds
        modified_query: Modified query (for pre-search agents)
        modified_results: Modified results (for post-search agents)
        artifacts: Generated artifacts (for response agents)
        metadata: Additional result metadata
        error_message: Error message if failed
    """

    agent_config_id: UUID4 = Field(..., description="Agent config ID")
    agent_name: str = Field(..., description="Agent name")
    agent_type: str = Field(..., description="Agent type")
    stage: str = Field(..., description="Pipeline stage")
    status: AgentExecutionStatus = Field(..., description="Execution status")
    execution_time_ms: float = Field(..., description="Execution time in ms")
    modified_query: str | None = Field(default=None, description="Modified query")
    modified_results: list[dict[str, Any]] | None = Field(default=None, description="Modified results")
    artifacts: list["AgentArtifact"] | None = Field(default=None, description="Generated artifacts")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Result metadata")
    error_message: str | None = Field(default=None, description="Error message")


class AgentArtifact(BaseModel):
    """Artifact generated by a response agent.

    Attributes:
        artifact_type: Type of artifact (e.g., "pdf", "pptx", "chart")
        content_type: MIME type of the content
        filename: Suggested filename
        data_url: Base64 data URL or download URL
        metadata: Additional artifact metadata
    """

    artifact_type: str = Field(..., description="Artifact type")
    content_type: str = Field(..., description="MIME type")
    filename: str = Field(..., description="Suggested filename")
    data_url: str | None = Field(default=None, description="Data URL or download URL")
    size_bytes: int | None = Field(default=None, description="Size in bytes")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Artifact metadata")


class AgentExecutionSummary(BaseModel):
    """Summary of all agent executions for a search request.

    Attributes:
        total_agents: Total number of agents executed
        successful: Number of successful executions
        failed: Number of failed executions
        skipped: Number of skipped executions
        total_execution_time_ms: Total execution time in milliseconds
        pre_search_results: Results from pre-search stage
        post_search_results: Results from post-search stage
        response_results: Results from response stage
        artifacts: All generated artifacts
    """

    total_agents: int = Field(default=0, description="Total agents executed")
    successful: int = Field(default=0, description="Successful executions")
    failed: int = Field(default=0, description="Failed executions")
    skipped: int = Field(default=0, description="Skipped executions")
    total_execution_time_ms: float = Field(default=0.0, description="Total execution time")
    pre_search_results: list[AgentResult] = Field(default_factory=list)
    post_search_results: list[AgentResult] = Field(default_factory=list)
    response_results: list[AgentResult] = Field(default_factory=list)
    artifacts: list[AgentArtifact] = Field(default_factory=list)


# ============================================================================
# Pipeline Metadata Schema
# ============================================================================


class PipelineMetadata(BaseModel):
    """Metadata about pipeline execution including agent timing.

    Attributes:
        pipeline_version: Version of the pipeline architecture
        stages_executed: List of stages that were executed
        total_execution_time_ms: Total pipeline execution time
        agent_execution_summary: Summary of agent executions
        timings: Detailed timing breakdown by stage
    """

    pipeline_version: str = Field(default="v2_with_agents", description="Pipeline version")
    stages_executed: list[str] = Field(default_factory=list, description="Executed stages")
    total_execution_time_ms: float = Field(default=0.0, description="Total execution time")
    agent_execution_summary: AgentExecutionSummary | None = Field(default=None)
    timings: dict[str, float] = Field(default_factory=dict, description="Stage timings")


# Update forward references
AgentContext.model_rebuild()
AgentResult.model_rebuild()
