"""Pydantic schemas for runtime configuration with hierarchical scope support.

This module provides schemas for the dynamic configuration system that enables
runtime configuration changes without application restart. Configurations are
organized hierarchically: collection > user > global > .env Settings.

Example:
    Create a user-level configuration override:

    >>> config_input = RuntimeConfigInput(
    ...     scope=ConfigScope.USER,
    ...     category=ConfigCategory.LLM,
    ...     user_id=user_uuid,
    ...     config_key="max_new_tokens",
    ...     config_value={"value": 1024, "type": "int"},
    ...     description="Increased token limit for detailed responses"
    ... )
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator


class ConfigScope(str, Enum):
    """Configuration scope hierarchy for precedence resolution.

    Precedence order (highest to lowest):
    - COLLECTION: Collection-specific overrides
    - USER: User-specific overrides
    - GLOBAL: System-wide defaults
    - (Settings from .env as final fallback, not stored in DB)
    """

    GLOBAL = "global"
    USER = "user"
    COLLECTION = "collection"


class ConfigCategory(str, Enum):
    """Configuration categories matching Settings structure.

    Categories organize related configuration parameters for easier management
    and allow bulk operations on specific subsystems.
    """

    LLM = "llm"  # LLM generation parameters (temperature, tokens, etc.)
    CHUNKING = "chunking"  # Document chunking strategies and parameters
    RETRIEVAL = "retrieval"  # Search/retrieval settings (top_k, thresholds)
    EMBEDDING = "embedding"  # Embedding model configuration
    COT = "cot"  # Chain of Thought reasoning parameters
    RERANKING = "reranking"  # Reranking model settings
    PODCAST = "podcast"  # Podcast generation configuration
    QUESTION = "question"  # Question suggestion parameters
    LOGGING = "logging"  # Logging configuration
    SYSTEM = "system"  # System-level settings


class RuntimeConfigBase(BaseModel):
    """Base schema with common fields for runtime configuration."""

    scope: ConfigScope = Field(..., description="Configuration scope (global/user/collection)")
    category: ConfigCategory = Field(..., description="Configuration category")
    config_key: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Configuration key matching Settings field name",
    )
    description: str | None = Field(None, max_length=1024, description="Human-readable description")

    model_config = ConfigDict(use_enum_values=True)


class RuntimeConfigInput(RuntimeConfigBase):
    """Input schema for creating/updating runtime configuration.

    Attributes:
        scope: Configuration scope (global/user/collection)
        category: Configuration category (llm/chunking/retrieval/etc.)
        config_key: Settings field name (e.g., 'max_new_tokens', 'temperature')
        config_value: JSON value with type metadata: {'value': ..., 'type': 'int'|'float'|'str'|'bool'|'list'}
        user_id: Required for USER scope, None otherwise
        collection_id: Required for COLLECTION scope, None otherwise
        is_active: Whether this configuration is active (default: True)
        description: Optional human-readable description
        created_by: User ID who created this configuration

    Examples:
        >>> # Global default
        >>> RuntimeConfigInput(
        ...     scope=ConfigScope.GLOBAL,
        ...     category=ConfigCategory.LLM,
        ...     config_key="temperature",
        ...     config_value={"value": 0.7, "type": "float"}
        ... )

        >>> # User override
        >>> RuntimeConfigInput(
        ...     scope=ConfigScope.USER,
        ...     category=ConfigCategory.CHUNKING,
        ...     user_id=user_uuid,
        ...     config_key="chunk_size",
        ...     config_value={"value": 512, "type": "int"}
        ... )
    """

    user_id: UUID4 | None = Field(None, description="User ID for user scope")
    collection_id: UUID4 | None = Field(None, description="Collection ID for collection scope")
    config_value: dict[str, Any] = Field(
        ..., description="JSON value with type: {'value': ..., 'type': 'int'|'float'|'str'|'bool'|'list'}"
    )
    is_active: bool = Field(True, description="Active status")
    created_by: UUID4 | None = Field(None, description="Creator user ID")

    model_config = ConfigDict(strict=True, extra="forbid", use_enum_values=True)

    @field_validator("config_value")
    @classmethod
    def validate_config_value(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate config_value structure and type metadata.

        Args:
            v: Config value dictionary

        Returns:
            Validated config value

        Raises:
            ValueError: If structure is invalid
        """
        if "value" not in v:
            raise ValueError("config_value must contain 'value' key")
        if "type" not in v:
            raise ValueError("config_value must contain 'type' key")
        if v["type"] not in ("int", "float", "str", "bool", "list", "dict"):
            raise ValueError(f"Invalid type '{v['type']}'. Must be one of: int, float, str, bool, list, dict")
        return v

    @field_validator("user_id")
    @classmethod
    def validate_user_id_for_scope(cls, v: UUID4 | None, info) -> UUID4 | None:
        """Validate user_id is provided for USER scope.

        Args:
            v: User ID value
            info: Field validation info with other field values

        Returns:
            Validated user ID

        Raises:
            ValueError: If user_id missing for USER scope or present for GLOBAL scope
        """
        scope = info.data.get("scope")
        if scope == ConfigScope.USER and v is None:
            raise ValueError("user_id is required for USER scope")
        if scope == ConfigScope.GLOBAL and v is not None:
            raise ValueError("user_id must be None for GLOBAL scope")
        return v

    @field_validator("collection_id")
    @classmethod
    def validate_collection_id_for_scope(cls, v: UUID4 | None, info) -> UUID4 | None:
        """Validate collection_id is provided for COLLECTION scope.

        Args:
            v: Collection ID value
            info: Field validation info with other field values

        Returns:
            Validated collection ID

        Raises:
            ValueError: If collection_id missing for COLLECTION scope or present for GLOBAL/USER scopes
        """
        scope = info.data.get("scope")
        if scope == ConfigScope.COLLECTION and v is None:
            raise ValueError("collection_id is required for COLLECTION scope")
        if scope in (ConfigScope.GLOBAL, ConfigScope.USER) and v is not None:
            raise ValueError(f"collection_id must be None for {scope} scope")
        return v


class RuntimeConfigOutput(RuntimeConfigBase):
    """Output schema for runtime configuration responses.

    Attributes:
        id: Unique configuration identifier
        scope: Configuration scope
        category: Configuration category
        config_key: Configuration key
        config_value: JSON value with type metadata
        user_id: User ID (for USER/COLLECTION scopes)
        collection_id: Collection ID (for COLLECTION scope)
        is_active: Active status
        created_at: Creation timestamp
        updated_at: Last update timestamp
        created_by: Creator user ID
    """

    id: UUID4 = Field(..., description="Configuration ID")
    user_id: UUID4 | None = Field(None, description="User ID for user scope")
    collection_id: UUID4 | None = Field(None, description="Collection ID for collection scope")
    config_value: dict[str, Any] = Field(..., description="JSON value with type metadata")
    is_active: bool = Field(..., description="Active status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: UUID4 | None = Field(None, description="Creator user ID")

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    @property
    def typed_value(self) -> int | float | str | bool | list | dict:
        """Extract typed value from config_value JSON structure.

        Returns:
            Python value with correct type (int, float, str, bool, list, or dict)

        Raises:
            ValueError: If value is None or type conversion fails

        Example:
            >>> config = RuntimeConfigOutput(...)
            >>> config.config_value = {"value": 1024, "type": "int"}
            >>> config.typed_value  # Returns: 1024 (as int)
        """
        value_type = self.config_value.get("type", "str")
        raw_value = self.config_value.get("value")

        if raw_value is None:
            raise ValueError("config_value['value'] cannot be None")

        # Use match/case for type-safe value extraction
        # JSONB validation ensures raw_value matches declared type
        match value_type:
            case "int":
                return int(raw_value)
            case "float":
                return float(raw_value)
            case "bool":
                return bool(raw_value)
            case "list":
                # Trust JSONB schema validation - raw_value is guaranteed to be list
                return raw_value  # type: ignore[return-value]
            case "dict":
                # Trust JSONB schema validation - raw_value is guaranteed to be dict
                return raw_value  # type: ignore[return-value]
            case _:
                # Default to string for any other type
                return str(raw_value)


class EffectiveConfig(BaseModel):
    """Effective configuration after applying hierarchical precedence.

    This schema represents the final resolved configuration values after
    applying the precedence hierarchy: collection > user > global > Settings.

    Attributes:
        category: Configuration category
        values: Effective configuration values (dict of config_key: value)
        sources: Source map showing where each value comes from

    Example:
        >>> effective = EffectiveConfig(
        ...     category=ConfigCategory.LLM,
        ...     values={"temperature": 0.8, "max_new_tokens": 1024},
        ...     sources={"temperature": "user", "max_new_tokens": "settings"}
        ... )
        >>> effective.get("temperature")  # Returns: 0.8
        >>> effective.get("top_k", default=5)  # Returns: 5 (fallback)
    """

    category: ConfigCategory = Field(..., description="Configuration category")
    values: dict[str, Any] = Field(..., description="Effective configuration values")
    sources: dict[str, str] = Field(..., description="Source map: config_key → scope (collection/user/global/settings)")

    model_config = ConfigDict(use_enum_values=True)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with fallback.

        Args:
            key: Configuration key to retrieve
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self.values.get(key, default)
