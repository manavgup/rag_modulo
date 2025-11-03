"""RuntimeConfig repository for managing runtime configuration entities in the database."""

import logging
from typing import Any

from pydantic import UUID4
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.models.runtime_config import RuntimeConfig
from rag_solution.schemas.runtime_config_schema import (
    ConfigCategory,
    ConfigScope,
    EffectiveConfig,
    RuntimeConfigInput,
    RuntimeConfigOutput,
)

logger = logging.getLogger(__name__)


class RuntimeConfigRepository:
    """Repository for managing RuntimeConfig entities in the database."""

    def __init__(self, db: Session, settings: Settings) -> None:
        """Initialize the RuntimeConfigRepository.

        Args:
            db: The database session
            settings: Application settings for fallback values
        """
        self.db = db
        self.settings = settings

    def create(self, config_input: RuntimeConfigInput) -> RuntimeConfigOutput:
        """Create a new runtime configuration.

        Args:
            config_input: The configuration data to create

        Returns:
            The created configuration

        Raises:
            IntegrityError: If unique constraint is violated
            SQLAlchemyError: If there's a database error
        """
        try:
            db_config = RuntimeConfig(
                scope=config_input.scope,
                category=config_input.category,
                config_key=config_input.config_key,
                config_value=config_input.config_value,
                user_id=config_input.user_id,
                collection_id=config_input.collection_id,
                is_active=config_input.is_active,
                description=config_input.description,
                created_by=config_input.created_by,
            )
            self.db.add(db_config)
            self.db.commit()
            self.db.refresh(db_config)

            logger.info(
                "Created runtime config: scope=%s, category=%s, key=%s",
                config_input.scope,
                config_input.category,
                config_input.config_key,
            )
            return RuntimeConfigOutput.model_validate(db_config)
        except IntegrityError as e:
            self.db.rollback()
            logger.error("Integrity error creating runtime config: %s", str(e))
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Error creating runtime config: %s", str(e))
            raise

    def get(self, config_id: UUID4) -> RuntimeConfigOutput | None:
        """Retrieve a runtime configuration by its ID.

        Args:
            config_id: The ID of the configuration to retrieve

        Returns:
            The configuration or None if not found
        """
        try:
            config = self.db.query(RuntimeConfig).filter(RuntimeConfig.id == config_id).first()
            if config:
                return RuntimeConfigOutput.model_validate(config)
            return None
        except SQLAlchemyError as e:
            logger.error("Error retrieving runtime config %s: %s", config_id, str(e))
            raise

    def get_by_scope(
        self,
        scope: ConfigScope,
        category: ConfigCategory,
        config_key: str,
        user_id: UUID4 | None = None,
        collection_id: UUID4 | None = None,
    ) -> RuntimeConfigOutput | None:
        """Get configuration by scope, category, and key.

        Args:
            scope: Configuration scope
            category: Configuration category
            config_key: Configuration key
            user_id: User ID (required for USER/COLLECTION scopes)
            collection_id: Collection ID (required for COLLECTION scope)

        Returns:
            The configuration or None if not found
        """
        try:
            query = self.db.query(RuntimeConfig).filter(
                and_(
                    RuntimeConfig.scope == scope,
                    RuntimeConfig.category == category,
                    RuntimeConfig.config_key == config_key,
                    RuntimeConfig.is_active.is_(True),
                )
            )

            # Add scope-specific filters
            if scope == ConfigScope.USER:
                query = query.filter(RuntimeConfig.user_id == user_id)
            elif scope == ConfigScope.COLLECTION:
                query = query.filter(
                    and_(RuntimeConfig.user_id == user_id, RuntimeConfig.collection_id == collection_id)
                )
            else:  # GLOBAL
                query = query.filter(RuntimeConfig.user_id.is_(None), RuntimeConfig.collection_id.is_(None))

            config = query.first()
            if config:
                return RuntimeConfigOutput.model_validate(config)
            return None
        except SQLAlchemyError as e:
            logger.error("Error retrieving runtime config by scope: %s", str(e))
            raise

    def get_all_for_user(self, user_id: UUID4, category: ConfigCategory | None = None) -> list[RuntimeConfigOutput]:
        """Get all user-level configurations.

        Args:
            user_id: The user ID
            category: Optional category filter

        Returns:
            List of user configurations
        """
        try:
            query = self.db.query(RuntimeConfig).filter(
                and_(
                    RuntimeConfig.scope == ConfigScope.USER,
                    RuntimeConfig.user_id == user_id,
                    RuntimeConfig.is_active.is_(True),
                )
            )

            if category:
                query = query.filter(RuntimeConfig.category == category)

            configs = query.all()
            return [RuntimeConfigOutput.model_validate(c) for c in configs]
        except SQLAlchemyError as e:
            logger.error("Error retrieving user configs: %s", str(e))
            raise

    def get_all_for_collection(
        self, collection_id: UUID4, category: ConfigCategory | None = None
    ) -> list[RuntimeConfigOutput]:
        """Get all collection-level configurations.

        Args:
            collection_id: The collection ID
            category: Optional category filter

        Returns:
            List of collection configurations
        """
        try:
            query = self.db.query(RuntimeConfig).filter(
                and_(
                    RuntimeConfig.scope == ConfigScope.COLLECTION,
                    RuntimeConfig.collection_id == collection_id,
                    RuntimeConfig.is_active.is_(True),
                )
            )

            if category:
                query = query.filter(RuntimeConfig.category == category)

            configs = query.all()
            return [RuntimeConfigOutput.model_validate(c) for c in configs]
        except SQLAlchemyError as e:
            logger.error("Error retrieving collection configs: %s", str(e))
            raise

    def get_effective_config(
        self, user_id: UUID4, collection_id: UUID4 | None, category: ConfigCategory
    ) -> EffectiveConfig:
        """Get effective configuration after applying hierarchical precedence.

        Precedence: collection > user > global > Settings

        Args:
            user_id: The user ID
            collection_id: Optional collection ID
            category: Configuration category

        Returns:
            Effective configuration with merged values and source tracking
        """
        try:
            values: dict[str, Any] = {}
            sources: dict[str, str] = {}

            # Step 1: Get global configs
            global_configs = (
                self.db.query(RuntimeConfig)
                .filter(
                    and_(
                        RuntimeConfig.scope == ConfigScope.GLOBAL,
                        RuntimeConfig.category == category,
                        RuntimeConfig.is_active.is_(True),
                        RuntimeConfig.user_id.is_(None),
                        RuntimeConfig.collection_id.is_(None),
                    )
                )
                .all()
            )

            for config in global_configs:
                config_output = RuntimeConfigOutput.model_validate(config)
                values[config.config_key] = config_output.typed_value
                sources[config.config_key] = "global"

            # Step 2: Override with user configs
            user_configs = (
                self.db.query(RuntimeConfig)
                .filter(
                    and_(
                        RuntimeConfig.scope == ConfigScope.USER,
                        RuntimeConfig.category == category,
                        RuntimeConfig.user_id == user_id,
                        RuntimeConfig.is_active.is_(True),
                    )
                )
                .all()
            )

            for config in user_configs:
                config_output = RuntimeConfigOutput.model_validate(config)
                values[config.config_key] = config_output.typed_value
                sources[config.config_key] = "user"

            # Step 3: Override with collection configs (if collection_id provided)
            if collection_id:
                collection_configs = (
                    self.db.query(RuntimeConfig)
                    .filter(
                        and_(
                            RuntimeConfig.scope == ConfigScope.COLLECTION,
                            RuntimeConfig.category == category,
                            RuntimeConfig.collection_id == collection_id,
                            RuntimeConfig.is_active.is_(True),
                        )
                    )
                    .all()
                )

                for config in collection_configs:
                    config_output = RuntimeConfigOutput.model_validate(config)
                    values[config.config_key] = config_output.typed_value
                    sources[config.config_key] = "collection"

            logger.info(
                "Resolved effective config for category=%s: %d values from %s",
                category,
                len(values),
                set(sources.values()),
            )

            return EffectiveConfig(category=category, values=values, sources=sources)
        except SQLAlchemyError as e:
            logger.error("Error resolving effective config: %s", str(e))
            raise

    def update(self, config_id: UUID4, updates: dict[str, Any]) -> RuntimeConfigOutput | None:
        """Update an existing runtime configuration.

        Args:
            config_id: The configuration ID
            updates: Dictionary of fields to update

        Returns:
            The updated configuration or None if not found

        Raises:
            SQLAlchemyError: If there's a database error
        """
        try:
            config = self.db.query(RuntimeConfig).filter(RuntimeConfig.id == config_id).first()
            if not config:
                return None

            for key, value in updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)

            self.db.commit()
            self.db.refresh(config)

            logger.info("Updated runtime config: id=%s, fields=%s", config_id, list(updates.keys()))
            return RuntimeConfigOutput.model_validate(config)
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Error updating runtime config %s: %s", config_id, str(e))
            raise

    def delete(self, config_id: UUID4) -> bool:
        """Delete a runtime configuration.

        Args:
            config_id: The configuration ID

        Returns:
            True if deleted, False if not found

        Raises:
            SQLAlchemyError: If there's a database error
        """
        try:
            config = self.db.query(RuntimeConfig).filter(RuntimeConfig.id == config_id).first()
            if not config:
                return False

            self.db.delete(config)
            self.db.commit()

            logger.info("Deleted runtime config: id=%s", config_id)
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Error deleting runtime config %s: %s", config_id, str(e))
            raise

    def toggle_active(self, config_id: UUID4, is_active: bool) -> RuntimeConfigOutput | None:
        """Toggle the active status of a configuration.

        Args:
            config_id: The configuration ID
            is_active: New active status

        Returns:
            The updated configuration or None if not found

        Raises:
            SQLAlchemyError: If there's a database error
        """
        try:
            config = self.db.query(RuntimeConfig).filter(RuntimeConfig.id == config_id).first()
            if not config:
                return None

            config.is_active = is_active
            self.db.commit()
            self.db.refresh(config)

            logger.info("Toggled runtime config active status: id=%s, is_active=%s", config_id, is_active)
            return RuntimeConfigOutput.model_validate(config)
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Error toggling runtime config %s: %s", config_id, str(e))
            raise
