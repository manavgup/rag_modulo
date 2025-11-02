"""RuntimeConfig model for operational overrides and feature flags.

This model stores runtime operational configuration that can be changed without
application restart. It is designed for admin-level controls, feature flags,
A/B testing, and emergency overrides.

Use Cases:
    - Feature flags: Enable/disable experimental features
    - Emergency overrides: Force-disable problematic functionality
    - A/B testing: Enable features for specific users/collections
    - Performance tuning: Adjust batch sizes, timeouts, retry counts
    - Circuit breakers: Disable failing external services

NOT for:
    - User preferences: Use PipelineConfig.config_metadata instead
    - Collection-specific settings: Use PipelineConfig.config_metadata instead
    - LLM parameters per user: Use LLMParameters table instead
    - Infrastructure config: Use .env and Settings class instead

Configuration precedence: collection > user > global > .env Settings
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Enum, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from core.identity_service import IdentityService
from rag_solution.file_management.database import Base
from rag_solution.schemas.runtime_config_schema import ConfigCategory, ConfigScope

if TYPE_CHECKING:
    pass


class RuntimeConfig(Base):  # pylint: disable=too-few-public-methods
    """Operational configuration override with hierarchical scope.

    This model enables runtime changes to system behavior without restart.
    Intended for admin-level operational controls, not end-user preferences.

    Examples:
        Global feature flag:
            scope='GLOBAL', category='SYSTEM', config_key='enable_new_reranker',
            config_value={'value': True, 'type': 'bool'}

        Emergency override:
            scope='GLOBAL', category='OVERRIDE', config_key='force_disable_reranking',
            config_value={'value': True, 'type': 'bool'}

        User A/B test:
            scope='USER', category='EXPERIMENT', config_key='enable_semantic_chunking',
            user_id='...', config_value={'value': True, 'type': 'bool'}

        Performance tuning:
            scope='GLOBAL', category='PERFORMANCE', config_key='embedding_batch_size',
            config_value={'value': 10, 'type': 'int'}

    Attributes:
        id: Unique identifier
        scope: Configuration scope (GLOBAL/USER/COLLECTION)
        category: Configuration category (SYSTEM/OVERRIDE/EXPERIMENT/PERFORMANCE)
        config_key: Configuration key (e.g., 'enable_new_reranker')
        config_value: JSONB with type metadata: {'value': ..., 'type': 'int'|'float'|'str'|'bool'|'list'|'dict'}
        user_id: Optional user ID for USER/COLLECTION scopes
        collection_id: Optional collection ID for COLLECTION scope
        is_active: Whether this configuration is currently active
        description: Optional human-readable description
        created_by: User ID who created this configuration
        created_at: Creation timestamp
        updated_at: Last update timestamp

    Constraints:
        - Unique constraint on (scope, category, config_key, user_id, collection_id)
        - Ensures only one config per scope/category/key/user/collection combination
    """

    __tablename__ = "runtime_configs"

    # 🆔 Identification
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=IdentityService.generate_id
    )

    # ⚙️ Configuration Attributes
    scope: Mapped[ConfigScope] = mapped_column(
        Enum(ConfigScope, name="configscope", create_type=False), nullable=False, index=True
    )
    category: Mapped[ConfigCategory] = mapped_column(
        Enum(ConfigCategory, name="configcategory", create_type=False), nullable=False, index=True
    )
    config_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # 💾 Configuration Value (JSONB for flexible type storage)
    config_value: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, comment="JSON with type metadata: {'value': ..., 'type': 'int'|'float'|'str'|...}"
    )

    # 🔗 Foreign Keys (nullable for global scope)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True, comment="Required for USER/COLLECTION scopes"
    )
    collection_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True, comment="Required for COLLECTION scope"
    )

    # 🟢 Flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # 📝 Metadata
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # 📊 Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 🔐 Unique Constraint
    # Ensures only one config per scope/category/key/user/collection combination
    __table_args__ = (
        UniqueConstraint(
            "scope",
            "category",
            "config_key",
            "user_id",
            "collection_id",
            name="uq_runtime_config_scope_category_key_user_collection",
        ),
        {"extend_existing": True},
    )

    # 🔗 Relationships (TYPE_CHECKING imports prevent circular dependencies)
    # Note: Relationships to User and Collection models are optional
    # They enable ORM navigation but are not required for basic functionality
    # Uncomment if bidirectional navigation is needed:
    #
    # user: Mapped[User | None] = relationship("User", back_populates="runtime_configs")
    # collection: Mapped[Collection | None] = relationship("Collection", back_populates="runtime_configs")

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<RuntimeConfig(id={self.id}, scope={self.scope}, "
            f"category={self.category}, key={self.config_key}, "
            f"user_id={self.user_id}, collection_id={self.collection_id})>"
        )
