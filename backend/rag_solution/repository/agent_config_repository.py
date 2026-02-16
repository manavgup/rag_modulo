"""Repository for AgentConfig and CollectionAgent database operations.

This module provides data access for agent configurations and collection-agent
associations used in the 3-stage search pipeline.

Reference: GitHub Issue #697
"""

from typing import Any

from pydantic import UUID4
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from core.custom_exceptions import RepositoryError
from core.logging_utils import get_logger
from rag_solution.core.exceptions import AlreadyExistsError, NotFoundError, ValidationError
from rag_solution.models.agent_config import AgentConfig, AgentConfigStatus, AgentStage, CollectionAgent
from rag_solution.schemas.agent_config_schema import (
    AgentConfigInput,
    AgentConfigOutput,
    AgentConfigUpdate,
    CollectionAgentInput,
    CollectionAgentOutput,
    CollectionAgentUpdate,
)

logger = get_logger(__name__)


class AgentConfigRepository:
    """Repository for handling AgentConfig database operations."""

    def __init__(self: Any, db: Session) -> None:
        """Initialize with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create(
        self,
        config_input: AgentConfigInput,
        owner_user_id: UUID4 | None = None,
        is_system: bool = False,
    ) -> AgentConfigOutput:
        """Create a new agent configuration.

        Args:
            config_input: Agent config creation data
            owner_user_id: UUID of the owning user (null for system configs)
            is_system: Whether this is a system-level config

        Returns:
            Created agent config data

        Raises:
            ValidationError: For validation errors
            RepositoryError: For other database errors
        """
        try:
            agent_config = AgentConfig(
                name=config_input.name,
                description=config_input.description,
                agent_type=config_input.agent_type,
                stage=config_input.stage.value,
                handler_module=config_input.handler_module,
                handler_class=config_input.handler_class,
                default_config=config_input.default_config,
                timeout_seconds=config_input.timeout_seconds,
                max_retries=config_input.max_retries,
                priority=config_input.priority,
                is_system=is_system,
                owner_user_id=owner_user_id,
                status=AgentConfigStatus.ACTIVE.value,
            )
            self.db.add(agent_config)
            self.db.commit()
            self.db.refresh(agent_config)
            return AgentConfigOutput.model_validate(agent_config)
        except IntegrityError as e:
            self.db.rollback()
            raise ValidationError("An error occurred while creating the agent config") from e
        except Exception as e:
            self.db.rollback()
            logger.error("Error creating agent config: %s", e)
            raise RepositoryError(f"Failed to create agent config: {e!s}") from e

    def get_by_id(self, config_id: UUID4) -> AgentConfigOutput:
        """Fetch agent config by ID.

        Args:
            config_id: UUID of the agent config

        Returns:
            Agent config data

        Raises:
            NotFoundError: If config not found
            RepositoryError: For database errors
        """
        try:
            config = (
                self.db.query(AgentConfig)
                .filter(AgentConfig.id == config_id)
                .options(joinedload(AgentConfig.owner))
                .first()
            )
            if not config:
                raise NotFoundError("AgentConfig", resource_id=str(config_id))
            return AgentConfigOutput.model_validate(config)
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Error getting agent config %s: %s", config_id, e)
            raise RepositoryError(f"Failed to get agent config by ID: {e!s}") from e

    def update(self, config_id: UUID4, config_update: AgentConfigUpdate) -> AgentConfigOutput:
        """Update agent config data.

        Args:
            config_id: UUID of the agent config
            config_update: Update data

        Returns:
            Updated agent config data

        Raises:
            NotFoundError: If config not found
            RepositoryError: For database errors
        """
        try:
            config = self.db.query(AgentConfig).filter(AgentConfig.id == config_id).first()
            if not config:
                raise NotFoundError("AgentConfig", resource_id=str(config_id))

            # Update only provided fields
            update_data = config_update.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                if value is not None:
                    if key == "status" and hasattr(value, "value"):
                        value = value.value
                    setattr(config, key, value)

            self.db.commit()
            self.db.refresh(config)
            return AgentConfigOutput.model_validate(config)
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Error updating agent config %s: %s", config_id, e)
            self.db.rollback()
            raise RepositoryError(f"Failed to update agent config: {e!s}") from e

    def delete(self, config_id: UUID4) -> bool:
        """Delete an agent config.

        Args:
            config_id: UUID of the agent config

        Returns:
            True if deleted, False if not found
        """
        try:
            result = self.db.query(AgentConfig).filter(AgentConfig.id == config_id).delete()
            self.db.commit()
            return result > 0
        except Exception as e:
            logger.error("Error deleting agent config %s: %s", config_id, e)
            self.db.rollback()
            raise RepositoryError(f"Failed to delete agent config: {e!s}") from e

    def list_configs(
        self,
        skip: int = 0,
        limit: int = 100,
        owner_user_id: UUID4 | None = None,
        stage: str | None = None,
        agent_type: str | None = None,
        status: str | None = None,
        include_system: bool = True,
    ) -> tuple[list[AgentConfigOutput], int]:
        """List agent configs with optional filters and pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            owner_user_id: Filter by owner user ID
            stage: Filter by stage
            agent_type: Filter by agent type
            status: Filter by status
            include_system: Whether to include system configs

        Returns:
            Tuple of (list of configs, total count)
        """
        try:
            query = self.db.query(AgentConfig)

            # Apply filters
            if owner_user_id:
                query = query.filter(AgentConfig.owner_user_id == owner_user_id)
            if stage:
                query = query.filter(AgentConfig.stage == stage)
            if agent_type:
                query = query.filter(AgentConfig.agent_type == agent_type)
            if status:
                query = query.filter(AgentConfig.status == status)
            if not include_system:
                query = query.filter(AgentConfig.is_system.is_(False))

            # Get total count
            total = query.count()

            # Apply pagination and fetch
            configs = (
                query.options(joinedload(AgentConfig.owner))
                .order_by(AgentConfig.stage, AgentConfig.priority, AgentConfig.name)
                .offset(skip)
                .limit(limit)
                .all()
            )

            return ([AgentConfigOutput.model_validate(c) for c in configs], total)
        except Exception as e:
            logger.error("Error listing agent configs: %s", e)
            raise RepositoryError(f"Failed to list agent configs: {e!s}") from e

    def list_by_stage(
        self,
        stage: AgentStage,
        include_system: bool = True,
    ) -> list[AgentConfigOutput]:
        """List active agent configs for a specific stage.

        Args:
            stage: Pipeline stage
            include_system: Whether to include system configs

        Returns:
            List of active agent configs for the stage
        """
        try:
            query = self.db.query(AgentConfig).filter(
                AgentConfig.stage == stage.value,
                AgentConfig.status == AgentConfigStatus.ACTIVE.value,
            )

            if not include_system:
                query = query.filter(AgentConfig.is_system.is_(False))

            configs = query.order_by(AgentConfig.priority, AgentConfig.name).all()
            return [AgentConfigOutput.model_validate(c) for c in configs]
        except Exception as e:
            logger.error("Error listing configs by stage %s: %s", stage, e)
            raise RepositoryError(f"Failed to list configs by stage: {e!s}") from e

    def count_by_owner(self, owner_user_id: UUID4) -> int:
        """Count agent configs owned by a user.

        Args:
            owner_user_id: UUID of the owner

        Returns:
            Number of configs
        """
        try:
            return (
                self.db.query(func.count(AgentConfig.id)).filter(AgentConfig.owner_user_id == owner_user_id).scalar()
                or 0
            )
        except Exception as e:
            logger.error("Error counting configs for owner %s: %s", owner_user_id, e)
            return 0


class CollectionAgentRepository:
    """Repository for handling CollectionAgent database operations."""

    def __init__(self: Any, db: Session) -> None:
        """Initialize with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create(
        self,
        collection_id: UUID4,
        association_input: CollectionAgentInput,
    ) -> CollectionAgentOutput:
        """Create a new collection-agent association.

        Args:
            collection_id: UUID of the collection
            association_input: Association creation data

        Returns:
            Created association data

        Raises:
            AlreadyExistsError: If association already exists
            NotFoundError: If collection or agent config not found
            RepositoryError: For database errors
        """
        try:
            # Check if association already exists
            existing = (
                self.db.query(CollectionAgent)
                .filter(
                    CollectionAgent.collection_id == collection_id,
                    CollectionAgent.agent_config_id == association_input.agent_config_id,
                )
                .first()
            )
            if existing:
                raise AlreadyExistsError(
                    "CollectionAgent",
                    "collection_id+agent_config_id",
                    f"{collection_id}+{association_input.agent_config_id}",
                )

            association = CollectionAgent(
                collection_id=collection_id,
                agent_config_id=association_input.agent_config_id,
                enabled=association_input.enabled,
                priority=association_input.priority,
                config_override=association_input.config_override,
            )
            self.db.add(association)
            self.db.commit()
            self.db.refresh(association)

            # Load the agent_config relationship
            self.db.refresh(association, attribute_names=["agent_config"])

            return CollectionAgentOutput.model_validate(association)
        except AlreadyExistsError:
            raise
        except IntegrityError as e:
            self.db.rollback()
            if "collection_id" in str(e):
                raise NotFoundError("Collection", resource_id=str(collection_id)) from e
            if "agent_config_id" in str(e):
                raise NotFoundError("AgentConfig", resource_id=str(association_input.agent_config_id)) from e
            raise ValidationError("An error occurred while creating the association") from e
        except Exception as e:
            self.db.rollback()
            logger.error("Error creating collection-agent association: %s", e)
            raise RepositoryError(f"Failed to create association: {e!s}") from e

    def get_by_id(self, association_id: UUID4) -> CollectionAgentOutput:
        """Fetch association by ID.

        Args:
            association_id: UUID of the association

        Returns:
            Association data

        Raises:
            NotFoundError: If association not found
            RepositoryError: For database errors
        """
        try:
            association = (
                self.db.query(CollectionAgent)
                .filter(CollectionAgent.id == association_id)
                .options(joinedload(CollectionAgent.agent_config))
                .first()
            )
            if not association:
                raise NotFoundError("CollectionAgent", resource_id=str(association_id))
            return CollectionAgentOutput.model_validate(association)
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Error getting association %s: %s", association_id, e)
            raise RepositoryError(f"Failed to get association by ID: {e!s}") from e

    def update(
        self,
        association_id: UUID4,
        update_data: CollectionAgentUpdate,
    ) -> CollectionAgentOutput:
        """Update a collection-agent association.

        Args:
            association_id: UUID of the association
            update_data: Update data

        Returns:
            Updated association data

        Raises:
            NotFoundError: If association not found
            RepositoryError: For database errors
        """
        try:
            association = self.db.query(CollectionAgent).filter(CollectionAgent.id == association_id).first()
            if not association:
                raise NotFoundError("CollectionAgent", resource_id=str(association_id))

            # Update only provided fields
            data = update_data.model_dump(exclude_unset=True)
            for key, value in data.items():
                if value is not None:
                    setattr(association, key, value)

            self.db.commit()
            self.db.refresh(association)
            return CollectionAgentOutput.model_validate(association)
        except NotFoundError:
            raise
        except Exception as e:
            logger.error("Error updating association %s: %s", association_id, e)
            self.db.rollback()
            raise RepositoryError(f"Failed to update association: {e!s}") from e

    def delete(self, association_id: UUID4) -> bool:
        """Delete an association.

        Args:
            association_id: UUID of the association

        Returns:
            True if deleted, False if not found
        """
        try:
            result = self.db.query(CollectionAgent).filter(CollectionAgent.id == association_id).delete()
            self.db.commit()
            return result > 0
        except Exception as e:
            logger.error("Error deleting association %s: %s", association_id, e)
            self.db.rollback()
            raise RepositoryError(f"Failed to delete association: {e!s}") from e

    def list_by_collection(
        self,
        collection_id: UUID4,
        stage: str | None = None,
        enabled_only: bool = False,
    ) -> list[CollectionAgentOutput]:
        """List associations for a collection.

        Args:
            collection_id: UUID of the collection
            stage: Optional stage filter
            enabled_only: Only return enabled associations

        Returns:
            List of associations ordered by priority
        """
        try:
            query = (
                self.db.query(CollectionAgent)
                .join(AgentConfig)
                .filter(CollectionAgent.collection_id == collection_id)
                .options(joinedload(CollectionAgent.agent_config))
            )

            if stage:
                query = query.filter(AgentConfig.stage == stage)
            if enabled_only:
                query = query.filter(CollectionAgent.enabled.is_(True))

            associations = query.order_by(CollectionAgent.priority, AgentConfig.name).all()
            return [CollectionAgentOutput.model_validate(a) for a in associations]
        except Exception as e:
            logger.error("Error listing associations for collection %s: %s", collection_id, e)
            raise RepositoryError(f"Failed to list associations: {e!s}") from e

    def batch_update_priorities(
        self,
        collection_id: UUID4,
        priorities: dict[UUID4, int],
    ) -> list[CollectionAgentOutput]:
        """Batch update priorities for multiple associations.

        Args:
            collection_id: UUID of the collection
            priorities: Mapping of association ID to new priority

        Returns:
            List of updated associations
        """
        try:
            updated = []
            for assoc_id, priority in priorities.items():
                association = (
                    self.db.query(CollectionAgent)
                    .filter(
                        CollectionAgent.id == assoc_id,
                        CollectionAgent.collection_id == collection_id,
                    )
                    .first()
                )
                if association:
                    association.priority = priority
                    updated.append(association)

            self.db.commit()

            # Refresh and return
            for assoc in updated:
                self.db.refresh(assoc)

            return [CollectionAgentOutput.model_validate(a) for a in updated]
        except Exception as e:
            logger.error("Error batch updating priorities: %s", e)
            self.db.rollback()
            raise RepositoryError(f"Failed to batch update priorities: {e!s}") from e

    def count_by_collection(self, collection_id: UUID4, enabled_only: bool = False) -> int:
        """Count associations for a collection.

        Args:
            collection_id: UUID of the collection
            enabled_only: Only count enabled associations

        Returns:
            Number of associations
        """
        try:
            query = self.db.query(func.count(CollectionAgent.id)).filter(
                CollectionAgent.collection_id == collection_id
            )
            if enabled_only:
                query = query.filter(CollectionAgent.enabled.is_(True))
            return query.scalar() or 0
        except Exception as e:
            logger.error("Error counting associations for collection %s: %s", collection_id, e)
            return 0

    def delete_by_collection(self, collection_id: UUID4) -> int:
        """Delete all associations for a collection.

        Args:
            collection_id: UUID of the collection

        Returns:
            Number of deleted associations
        """
        try:
            result = (
                self.db.query(CollectionAgent).filter(CollectionAgent.collection_id == collection_id).delete()
            )
            self.db.commit()
            return result
        except Exception as e:
            logger.error("Error deleting associations for collection %s: %s", collection_id, e)
            self.db.rollback()
            raise RepositoryError(f"Failed to delete associations: {e!s}") from e
