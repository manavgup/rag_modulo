"""Agent configuration model for search pipeline execution hooks.

This module defines the AgentConfig SQLAlchemy model for storing agent
configurations that can be attached to collections at different pipeline stages.

The 3-stage pipeline supports:
- Stage 1: Pre-Search Agents (query expansion, language detection, etc.)
- Stage 2: Post-Search Agents (re-ranking, deduplication, PII redaction)
- Stage 3: Response Agents (PowerPoint, PDF, Chart generation)

Reference: GitHub Issue #697
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.identity_service import IdentityService
from rag_solution.file_management.database import Base

if TYPE_CHECKING:
    from rag_solution.models.user import User


class AgentStage(str, Enum):
    """Pipeline stages where agents can execute.

    Attributes:
        PRE_SEARCH: Before vector search (query enhancement)
        POST_SEARCH: After vector search (result enhancement)
        RESPONSE: Response generation (artifacts)
    """

    PRE_SEARCH = "pre_search"
    POST_SEARCH = "post_search"
    RESPONSE = "response"


class AgentConfigStatus(str, Enum):
    """Agent configuration status.

    Attributes:
        ACTIVE: Agent config is active and available
        DISABLED: Agent config is temporarily disabled
        DEPRECATED: Agent config is deprecated (still works but not recommended)
    """

    ACTIVE = "active"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"


class AgentConfig(Base):
    """SQLAlchemy model for agent configurations in the search pipeline.

    AgentConfig defines a specific agent that can be attached to collections
    and executed at a specific stage in the search pipeline.

    Attributes:
        id: Unique identifier for the agent config (UUID)
        name: Human-readable name for the agent config
        description: Description of what the agent does
        agent_type: Type identifier (e.g., "query_expander", "reranker", "pdf_generator")
        stage: Pipeline stage where this agent executes
        handler_module: Python module path for the handler
        handler_class: Class name within the handler module
        default_config: Default configuration JSONB for the agent
        timeout_seconds: Maximum execution time before circuit breaker trips
        max_retries: Maximum retry attempts on failure
        priority: Default execution priority (lower = earlier execution)
        is_system: Whether this is a built-in system agent
        owner_user_id: User who created this agent config (null for system agents)
        status: Current status (active, disabled, deprecated)
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
    """

    __tablename__ = "agent_configs"

    __table_args__ = (
        Index("ix_agent_configs_stage", "stage"),
        Index("ix_agent_configs_agent_type", "agent_type"),
        Index("ix_agent_configs_status", "status"),
        Index("ix_agent_configs_owner_status", "owner_user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=IdentityService.generate_id,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable agent config name",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Description of agent functionality",
    )
    agent_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Agent type identifier (e.g., query_expander, reranker)",
    )
    stage: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=AgentStage.PRE_SEARCH.value,
        comment="Pipeline stage (pre_search, post_search, response)",
    )
    handler_module: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Python module path for the handler",
    )
    handler_class: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Class name within the handler module",
    )
    default_config: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Default configuration for the agent",
    )
    timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=30,
        comment="Maximum execution time in seconds",
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
        comment="Maximum retry attempts on failure",
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        comment="Default execution priority (lower = earlier)",
    )
    is_system: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        comment="Whether this is a built-in system agent",
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who created this config (null for system)",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=AgentConfigStatus.ACTIVE.value,
        comment="Status (active, disabled, deprecated)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    owner: Mapped[User | None] = relationship(
        "User",
        back_populates="agent_configs",
        foreign_keys=[owner_user_id],
    )
    collection_associations: Mapped[list["CollectionAgent"]] = relationship(
        "CollectionAgent",
        back_populates="agent_config",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """String representation of the agent config."""
        return (
            f"AgentConfig(id='{self.id}', name='{self.name}', "
            f"agent_type='{self.agent_type}', stage='{self.stage}', status='{self.status}')"
        )

    def is_active(self) -> bool:
        """Check if the agent config is active."""
        return self.status == AgentConfigStatus.ACTIVE.value


class CollectionAgent(Base):
    """Junction table for collection-agent associations.

    This table links collections to agent configs with collection-specific
    configuration overrides and priority settings.

    Attributes:
        id: Unique identifier for the association
        collection_id: UUID of the collection
        agent_config_id: UUID of the agent configuration
        enabled: Whether this agent is enabled for the collection
        priority: Execution priority override (lower = earlier)
        config_override: Collection-specific configuration overrides
        created_at: Timestamp of association creation
        updated_at: Timestamp of last update
    """

    __tablename__ = "collection_agents"

    __table_args__ = (
        Index("ix_collection_agents_collection", "collection_id"),
        Index("ix_collection_agents_agent", "agent_config_id"),
        Index("ix_collection_agents_enabled", "collection_id", "enabled"),
        Index("ix_collection_agents_priority", "collection_id", "priority"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=IdentityService.generate_id,
    )
    collection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
        comment="Collection this agent is attached to",
    )
    agent_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_configs.id", ondelete="CASCADE"),
        nullable=False,
        comment="Agent configuration to use",
    )
    enabled: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        comment="Whether agent is enabled for this collection",
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        comment="Execution priority override (lower = earlier)",
    )
    config_override: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Collection-specific configuration overrides",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    agent_config: Mapped[AgentConfig] = relationship(
        "AgentConfig",
        back_populates="collection_associations",
    )
    collection: Mapped["Collection"] = relationship(  # noqa: F821
        "Collection",
        back_populates="agent_associations",
    )

    def __repr__(self) -> str:
        """String representation of the collection-agent association."""
        return (
            f"CollectionAgent(id='{self.id}', collection_id='{self.collection_id}', "
            f"agent_config_id='{self.agent_config_id}', enabled={self.enabled}, priority={self.priority})"
        )

    def get_merged_config(self) -> dict:
        """Get merged configuration (default + overrides).

        Returns:
            Merged configuration dictionary
        """
        if not self.agent_config:
            return self.config_override

        merged = dict(self.agent_config.default_config)
        merged.update(self.config_override)
        return merged
