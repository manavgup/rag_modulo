"""Service layer for runtime configuration management.

This service provides business logic for managing runtime configurations
with hierarchical precedence (collection > user > global > Settings fallback).
"""

from typing import Any

from pydantic import UUID4
from sqlalchemy.orm import Session

from core.config import Settings
from core.custom_exceptions import NotFoundError, ValidationError
from core.logging_utils import get_logger
from rag_solution.repository.runtime_config_repository import RuntimeConfigRepository
from rag_solution.schemas.runtime_config_schema import (
    ConfigCategory,
    ConfigScope,
    EffectiveConfig,
    RuntimeConfigInput,
    RuntimeConfigOutput,
)

logger = get_logger("services.runtime_config")


class RuntimeConfigService:
    """Service for managing runtime configuration with hierarchical precedence.

    This service implements the business logic layer between the router and repository,
    providing:
    - Configuration CRUD operations
    - Hierarchical configuration resolution (collection > user > global > Settings)
    - Scope validation
    - Settings fallback integration
    """

    def __init__(self, db: Session, settings: Settings) -> None:
        """Initialize the runtime configuration service.

        Args:
            db: Database session
            settings: Application settings for fallback values
        """
        self.db = db
        self.settings = settings
        self.repository = RuntimeConfigRepository(db, settings)

    def create_config(self, config_input: RuntimeConfigInput) -> RuntimeConfigOutput:
        """Create a new runtime configuration.

        Validates scope constraints before creation:
        - USER scope requires user_id
        - COLLECTION scope requires both user_id and collection_id
        - GLOBAL scope must not have user_id or collection_id

        Args:
            config_input: Configuration input data

        Returns:
            RuntimeConfigOutput: Created configuration

        Raises:
            ValidationError: If scope constraints are violated
        """
        # Validate scope constraints
        self._validate_scope_constraints(config_input)

        logger.info(
            "Creating config: scope=%s, category=%s, key=%s",
            config_input.scope,
            config_input.category,
            config_input.config_key,
        )

        created_config = self.repository.create(config_input)
        logger.info("Created config with id=%s", created_config.id)

        return created_config

    def get_config(self, config_id: UUID4) -> RuntimeConfigOutput:
        """Get a specific configuration by ID.

        Args:
            config_id: Configuration UUID

        Returns:
            RuntimeConfigOutput: Configuration data

        Raises:
            NotFoundException: If configuration not found
        """
        config = self.repository.get(config_id)
        if not config:
            raise NotFoundError(
                resource_type="RuntimeConfig",
                resource_id=str(config_id),
            )

        return config

    def get_effective_config(
        self, user_id: UUID4, collection_id: UUID4 | None, category: ConfigCategory
    ) -> EffectiveConfig:
        """Get effective configuration with hierarchical precedence.

        Implements the precedence model: collection > user > global > Settings

        Args:
            user_id: User UUID
            collection_id: Optional collection UUID for collection-scoped configs
            category: Configuration category to retrieve

        Returns:
            EffectiveConfig: Merged configuration with source tracking
        """
        logger.debug(
            "Getting effective config: user_id=%s, collection_id=%s, category=%s",
            user_id,
            collection_id,
            category,
        )

        effective_config = self.repository.get_effective_config(user_id, collection_id, category)

        logger.debug(
            "Effective config for %s: %d values from %s",
            category,
            len(effective_config.values),
            set(effective_config.sources.values()),
        )

        return effective_config

    def update_config(self, config_id: UUID4, updates: dict[str, Any]) -> RuntimeConfigOutput:
        """Update an existing configuration.

        Args:
            config_id: Configuration UUID
            updates: Dictionary of fields to update

        Returns:
            RuntimeConfigOutput: Updated configuration

        Raises:
            NotFoundException: If configuration not found
            ValidationError: If updates violate scope constraints
        """
        # Get existing config to validate scope changes
        existing_config = self.get_config(config_id)

        # If scope is being changed, validate new scope constraints
        if "scope" in updates or "user_id" in updates or "collection_id" in updates:
            # Build a temporary input for validation
            temp_input = RuntimeConfigInput(
                scope=updates.get("scope", existing_config.scope),
                category=existing_config.category,
                config_key=existing_config.config_key,
                config_value=existing_config.config_value,
                user_id=updates.get("user_id", existing_config.user_id),
                collection_id=updates.get("collection_id", existing_config.collection_id),
                description=existing_config.description,
                is_active=existing_config.is_active,
                created_by=existing_config.created_by,
            )
            self._validate_scope_constraints(temp_input)

        logger.info("Updating config id=%s with %d fields", config_id, len(updates))

        updated_config = self.repository.update(config_id, updates)
        if not updated_config:
            raise NotFoundError(
                resource_type="RuntimeConfig",
                resource_id=str(config_id),
            )

        logger.info("Updated config id=%s", config_id)
        return updated_config

    def delete_config(self, config_id: UUID4) -> None:
        """Delete a configuration.

        Args:
            config_id: Configuration UUID

        Raises:
            NotFoundException: If configuration not found
        """
        logger.info("Deleting config id=%s", config_id)

        deleted = self.repository.delete(config_id)
        if not deleted:
            raise NotFoundError(
                resource_type="RuntimeConfig",
                resource_id=str(config_id),
            )

        logger.info("Deleted config id=%s", config_id)

    def toggle_config(self, config_id: UUID4, is_active: bool) -> RuntimeConfigOutput:
        """Toggle active status of a configuration.

        Args:
            config_id: Configuration UUID
            is_active: New active status

        Returns:
            RuntimeConfigOutput: Updated configuration

        Raises:
            NotFoundException: If configuration not found
        """
        logger.info("Toggling config id=%s to is_active=%s", config_id, is_active)

        toggled_config = self.repository.toggle_active(config_id, is_active)
        if not toggled_config:
            raise NotFoundError(
                resource_type="RuntimeConfig",
                resource_id=str(config_id),
            )

        logger.info("Toggled config id=%s to is_active=%s", config_id, is_active)
        return toggled_config

    def list_user_configs(self, user_id: UUID4, category: ConfigCategory | None = None) -> list[RuntimeConfigOutput]:
        """List all configurations for a user.

        Args:
            user_id: User UUID
            category: Optional category filter

        Returns:
            list[RuntimeConfigOutput]: List of user configurations
        """
        logger.debug("Listing user configs: user_id=%s, category=%s", user_id, category)

        configs = self.repository.get_all_for_user(user_id, category)

        logger.debug("Found %d user configs", len(configs))
        return configs

    def list_collection_configs(
        self, collection_id: UUID4, category: ConfigCategory | None = None
    ) -> list[RuntimeConfigOutput]:
        """List all configurations for a collection.

        Args:
            collection_id: Collection UUID
            category: Optional category filter

        Returns:
            list[RuntimeConfigOutput]: List of collection configurations
        """
        logger.debug("Listing collection configs: collection_id=%s, category=%s", collection_id, category)

        configs = self.repository.get_all_for_collection(collection_id, category)

        logger.debug("Found %d collection configs", len(configs))
        return configs

    def _validate_scope_constraints(self, config_input: RuntimeConfigInput) -> None:
        """Validate scope constraints for configuration.

        Rules:
        - GLOBAL: Must not have user_id or collection_id
        - USER: Must have user_id, must not have collection_id
        - COLLECTION: Must have both user_id and collection_id

        Args:
            config_input: Configuration input to validate

        Raises:
            ValidationError: If scope constraints are violated
        """
        scope = config_input.scope
        user_id = config_input.user_id
        collection_id = config_input.collection_id

        if scope == ConfigScope.GLOBAL:
            if user_id or collection_id:
                raise ValidationError(
                    field="scope",
                    message="GLOBAL scope must not have user_id or collection_id",
                )
        elif scope == ConfigScope.USER:
            if not user_id:
                raise ValidationError(
                    field="user_id",
                    message="USER scope requires user_id",
                )
            if collection_id:
                raise ValidationError(
                    field="collection_id",
                    message="USER scope must not have collection_id",
                )
        elif scope == ConfigScope.COLLECTION:
            if not user_id:
                raise ValidationError(
                    field="user_id",
                    message="COLLECTION scope requires user_id",
                )
            if not collection_id:
                raise ValidationError(
                    field="collection_id",
                    message="COLLECTION scope requires collection_id",
                )
