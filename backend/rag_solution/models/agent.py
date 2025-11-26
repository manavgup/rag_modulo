"""Agent model for SPIFFE-based workload identity.

This module defines the Agent SQLAlchemy model for storing agent identities
that are authenticated via SPIFFE/SPIRE. Agents are AI workloads that perform
various tasks in the RAG pipeline.

Reference: docs/architecture/spire-integration-architecture.md
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.identity_service import IdentityService
from rag_solution.file_management.database import Base

if TYPE_CHECKING:
    from rag_solution.models.team import Team
    from rag_solution.models.user import User


class AgentStatus(str):
    """Agent status enumeration.

    Attributes:
        ACTIVE: Agent is active and can authenticate
        SUSPENDED: Agent is temporarily suspended
        REVOKED: Agent credentials have been revoked
        PENDING: Agent is pending approval/registration
    """

    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    PENDING = "pending"


class Agent(Base):
    """SQLAlchemy model for AI agent identities.

    Agents are workloads that authenticate using SPIFFE JWT-SVIDs. Each agent
    has a unique SPIFFE ID and a set of capabilities that define what actions
    it can perform.

    Attributes:
        id: Unique identifier for the agent (UUID)
        spiffe_id: Full SPIFFE ID (e.g., "spiffe://trust-domain/agent/type/id")
        agent_type: Classification of agent (e.g., "search-enricher", "cot-reasoning")
        name: Human-readable name for the agent
        description: Description of the agent's purpose
        owner_user_id: UUID of the user who owns this agent
        team_id: Optional team association
        capabilities: JSONB array of capability strings
        agent_metadata: Additional JSONB metadata (named to avoid SQLAlchemy reserved word)
        status: Current status (active, suspended, revoked, pending)
        created_at: Timestamp of agent creation
        updated_at: Timestamp of last update
        last_seen_at: Timestamp of last successful authentication
    """

    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=IdentityService.generate_id,
    )
    spiffe_id: Mapped[str] = mapped_column(
        String(512),
        unique=True,
        index=True,
        nullable=False,
        comment="Full SPIFFE ID (spiffe://trust-domain/agent/type/id)",
    )
    agent_type: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
        comment="Agent type classification",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable agent name",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Description of agent purpose and capabilities",
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who owns this agent",
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional team association",
    )
    capabilities: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Array of capability strings",
    )
    agent_metadata: Mapped[dict] = mapped_column(
        "metadata",  # Maps to 'metadata' column in database
        JSONB,
        nullable=False,
        default=dict,
        comment="Additional agent metadata",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=AgentStatus.ACTIVE,
        index=True,
        comment="Agent status (active, suspended, revoked, pending)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False,
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="Last successful authentication timestamp",
    )

    # Relationships
    owner: Mapped[User] = relationship(
        "User",
        back_populates="agents",
        foreign_keys=[owner_user_id],
    )
    team: Mapped[Team | None] = relationship(
        "Team",
        back_populates="agents",
        foreign_keys=[team_id],
    )

    def __repr__(self) -> str:
        """String representation of the agent."""
        return (
            f"Agent(id='{self.id}', spiffe_id='{self.spiffe_id}', "
            f"agent_type='{self.agent_type}', name='{self.name}', status='{self.status}')"
        )

    def is_active(self) -> bool:
        """Check if the agent is active."""
        return self.status == AgentStatus.ACTIVE

    def has_capability(self, capability: str) -> bool:
        """Check if the agent has a specific capability.

        Args:
            capability: The capability string to check

        Returns:
            True if the agent has the capability
        """
        return capability in self.capabilities

    def add_capability(self, capability: str) -> None:
        """Add a capability to the agent.

        Args:
            capability: The capability string to add
        """
        if capability not in self.capabilities:
            self.capabilities = [*self.capabilities, capability]

    def remove_capability(self, capability: str) -> None:
        """Remove a capability from the agent.

        Args:
            capability: The capability string to remove
        """
        if capability in self.capabilities:
            self.capabilities = [c for c in self.capabilities if c != capability]

    def suspend(self) -> None:
        """Suspend the agent."""
        self.status = AgentStatus.SUSPENDED

    def activate(self) -> None:
        """Activate the agent."""
        self.status = AgentStatus.ACTIVE

    def revoke(self) -> None:
        """Revoke the agent's credentials."""
        self.status = AgentStatus.REVOKED

    def update_last_seen(self) -> None:
        """Update the last seen timestamp to now."""
        self.last_seen_at = datetime.now()
