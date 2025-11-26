"""Pydantic schemas for Agent entity.

This module defines the request/response schemas for the Agent API,
supporting SPIFFE-based workload identity for AI agents.

Reference: docs/architecture/spire-integration-architecture.md
"""

from datetime import datetime
from enum import Enum

from pydantic import UUID4, BaseModel, ConfigDict, Field


class AgentType(str, Enum):
    """Enumeration of supported agent types."""

    SEARCH_ENRICHER = "search-enricher"
    COT_REASONING = "cot-reasoning"
    QUESTION_DECOMPOSER = "question-decomposer"
    SOURCE_ATTRIBUTION = "source-attribution"
    ENTITY_EXTRACTION = "entity-extraction"
    ANSWER_SYNTHESIS = "answer-synthesis"
    CUSTOM = "custom"


class AgentStatus(str, Enum):
    """Enumeration of agent statuses."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    PENDING = "pending"


class AgentCapability(str, Enum):
    """Enumeration of agent capabilities for access control."""

    MCP_TOOL_INVOKE = "mcp:tool:invoke"
    SEARCH_READ = "search:read"
    SEARCH_WRITE = "search:write"
    LLM_INVOKE = "llm:invoke"
    PIPELINE_EXECUTE = "pipeline:execute"
    DOCUMENT_READ = "document:read"
    DOCUMENT_WRITE = "document:write"
    COT_INVOKE = "cot:invoke"
    AGENT_SPAWN = "agent:spawn"
    ADMIN = "admin"


class AgentInput(BaseModel):
    """Schema for creating a new agent.

    Attributes:
        agent_type: Type of agent (from AgentType enum)
        name: Human-readable name for the agent
        description: Optional description of the agent's purpose
        team_id: Optional team to associate the agent with
        capabilities: List of capabilities to grant the agent
        metadata: Optional additional metadata
    """

    agent_type: AgentType = Field(..., description="Type of agent")
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable agent name")
    description: str | None = Field(default=None, max_length=2000, description="Agent description")
    team_id: UUID4 | None = Field(default=None, description="Optional team association")
    capabilities: list[AgentCapability] = Field(
        default_factory=list,
        description="Agent capabilities",
    )
    metadata: dict | None = Field(default=None, description="Additional metadata")


class AgentUpdate(BaseModel):
    """Schema for updating an existing agent.

    All fields are optional - only provided fields will be updated.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    team_id: UUID4 | None = Field(default=None)
    capabilities: list[AgentCapability] | None = Field(default=None)
    metadata: dict | None = Field(default=None)
    status: AgentStatus | None = Field(default=None)


class AgentOutput(BaseModel):
    """Schema for agent response data.

    Attributes:
        id: Unique identifier for the agent
        spiffe_id: Full SPIFFE ID
        agent_type: Type of agent
        name: Human-readable name
        description: Agent description
        owner_user_id: UUID of the owning user
        team_id: Optional team association
        capabilities: List of granted capabilities
        metadata: Additional metadata
        status: Current agent status
        created_at: Creation timestamp
        updated_at: Last update timestamp
        last_seen_at: Last authentication timestamp
    """

    id: UUID4
    spiffe_id: str
    agent_type: str
    name: str
    description: str | None
    owner_user_id: UUID4
    team_id: UUID4 | None
    capabilities: list[str]
    metadata: dict
    status: str
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AgentListResponse(BaseModel):
    """Schema for paginated agent list response."""

    agents: list[AgentOutput]
    total: int
    skip: int
    limit: int


class AgentStatusUpdate(BaseModel):
    """Schema for updating agent status."""

    status: AgentStatus = Field(..., description="New agent status")
    reason: str | None = Field(default=None, max_length=500, description="Reason for status change")


class AgentCapabilityUpdate(BaseModel):
    """Schema for updating agent capabilities."""

    add_capabilities: list[AgentCapability] = Field(
        default_factory=list,
        description="Capabilities to add",
    )
    remove_capabilities: list[AgentCapability] = Field(
        default_factory=list,
        description="Capabilities to remove",
    )


class AgentRegistrationRequest(BaseModel):
    """Schema for registering a new agent with SPIFFE ID generation.

    This is used when creating an agent that will obtain SVIDs from SPIRE.
    """

    agent_type: AgentType = Field(..., description="Type of agent")
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable agent name")
    description: str | None = Field(default=None, max_length=2000)
    team_id: UUID4 | None = Field(default=None)
    capabilities: list[AgentCapability] = Field(default_factory=list)
    metadata: dict | None = Field(default=None)
    # SPIFFE-specific fields
    trust_domain: str | None = Field(
        default=None,
        description="Trust domain (uses default if not provided)",
    )
    custom_path: str | None = Field(
        default=None,
        description="Custom SPIFFE ID path suffix (generated if not provided)",
    )


class AgentRegistrationResponse(BaseModel):
    """Response schema for agent registration.

    Includes the SPIFFE ID that should be used for SPIRE registration entry.
    """

    agent: AgentOutput
    spiffe_id: str = Field(..., description="SPIFFE ID for SPIRE registration")
    registration_instructions: str = Field(
        ...,
        description="Instructions for completing SPIRE registration",
    )


class SPIFFEValidationRequest(BaseModel):
    """Schema for validating a SPIFFE JWT-SVID."""

    token: str = Field(..., description="JWT-SVID token to validate")
    required_audience: str | None = Field(default=None, description="Required audience claim")


class SPIFFEValidationResponse(BaseModel):
    """Response schema for SPIFFE JWT-SVID validation."""

    valid: bool
    spiffe_id: str | None = None
    agent_type: str | None = None
    agent_id: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    audiences: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None
    error: str | None = None
