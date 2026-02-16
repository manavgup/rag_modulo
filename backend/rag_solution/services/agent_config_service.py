"""Service layer for Agent Configuration management.

This module provides the AgentConfigService that handles business logic
for managing agent configurations and collection-agent associations.

Reference: GitHub Issue #697
"""

from typing import Any

from pydantic import UUID4
from sqlalchemy.orm import Session

from core.config import Settings
from core.logging_utils import get_logger
from rag_solution.models.agent_config import AgentStage
from rag_solution.repository.agent_config_repository import AgentConfigRepository, CollectionAgentRepository
from rag_solution.schemas.agent_config_schema import (
    AgentConfigInput,
    AgentConfigListResponse,
    AgentConfigOutput,
    AgentConfigUpdate,
    CollectionAgentInput,
    CollectionAgentListResponse,
    CollectionAgentOutput,
    CollectionAgentUpdate,
)

logger = get_logger("services.agent_config")


class AgentConfigService:
    """Service for managing agent configurations.

    This service provides business logic for creating, updating, and
    managing agent configurations that can be attached to collections.
    """

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        """Initialize the service.

        Args:
            db: Database session
            settings: Application settings
        """
        self.db = db
        self.settings = settings or Settings()
        self._config_repo: AgentConfigRepository | None = None
        self._assoc_repo: CollectionAgentRepository | None = None

    @property
    def config_repo(self) -> AgentConfigRepository:
        """Lazy initialization of config repository."""
        if self._config_repo is None:
            self._config_repo = AgentConfigRepository(self.db)
        return self._config_repo

    @property
    def assoc_repo(self) -> CollectionAgentRepository:
        """Lazy initialization of association repository."""
        if self._assoc_repo is None:
            self._assoc_repo = CollectionAgentRepository(self.db)
        return self._assoc_repo

    # ========================================================================
    # Agent Configuration Methods
    # ========================================================================

    def create_config(
        self,
        config_input: AgentConfigInput,
        owner_user_id: UUID4 | None = None,
        is_system: bool = False,
    ) -> AgentConfigOutput:
        """Create a new agent configuration.

        Args:
            config_input: Agent config creation data
            owner_user_id: UUID of the owning user
            is_system: Whether this is a system-level config

        Returns:
            Created agent config
        """
        logger.info("Creating agent config: %s", config_input.name)
        config = self.config_repo.create(config_input, owner_user_id, is_system)
        logger.info("Created agent config %s with ID %s", config.name, config.id)
        return config

    def get_config(self, config_id: UUID4) -> AgentConfigOutput:
        """Get an agent configuration by ID.

        Args:
            config_id: UUID of the config

        Returns:
            Agent config
        """
        return self.config_repo.get_by_id(config_id)

    def update_config(
        self,
        config_id: UUID4,
        config_update: AgentConfigUpdate,
    ) -> AgentConfigOutput:
        """Update an agent configuration.

        Args:
            config_id: UUID of the config
            config_update: Update data

        Returns:
            Updated agent config
        """
        logger.info("Updating agent config %s", config_id)
        config = self.config_repo.update(config_id, config_update)
        logger.info("Updated agent config %s", config_id)
        return config

    def delete_config(self, config_id: UUID4) -> bool:
        """Delete an agent configuration.

        Args:
            config_id: UUID of the config

        Returns:
            True if deleted
        """
        logger.info("Deleting agent config %s", config_id)
        result = self.config_repo.delete(config_id)
        if result:
            logger.info("Deleted agent config %s", config_id)
        return result

    def list_configs(
        self,
        skip: int = 0,
        limit: int = 100,
        owner_user_id: UUID4 | None = None,
        stage: str | None = None,
        agent_type: str | None = None,
        status: str | None = None,
        include_system: bool = True,
    ) -> AgentConfigListResponse:
        """List agent configurations with optional filters.

        Args:
            skip: Pagination offset
            limit: Maximum results
            owner_user_id: Filter by owner
            stage: Filter by stage
            agent_type: Filter by type
            status: Filter by status
            include_system: Include system configs

        Returns:
            Paginated list of configs
        """
        configs, total = self.config_repo.list_configs(
            skip=skip,
            limit=limit,
            owner_user_id=owner_user_id,
            stage=stage,
            agent_type=agent_type,
            status=status,
            include_system=include_system,
        )
        return AgentConfigListResponse(configs=configs, total=total, skip=skip, limit=limit)

    def list_by_stage(
        self,
        stage: str,
        include_system: bool = True,
    ) -> list[AgentConfigOutput]:
        """List active configs for a specific stage.

        Args:
            stage: Pipeline stage
            include_system: Include system configs

        Returns:
            List of configs for the stage
        """
        try:
            agent_stage = AgentStage(stage)
        except ValueError as e:
            raise ValueError(f"Invalid stage: {stage}") from e
        return self.config_repo.list_by_stage(agent_stage, include_system)

    # ========================================================================
    # Collection-Agent Association Methods
    # ========================================================================

    def add_agent_to_collection(
        self,
        collection_id: UUID4,
        association_input: CollectionAgentInput,
    ) -> CollectionAgentOutput:
        """Add an agent to a collection.

        Args:
            collection_id: UUID of the collection
            association_input: Association data

        Returns:
            Created association
        """
        logger.info(
            "Adding agent %s to collection %s",
            association_input.agent_config_id,
            collection_id,
        )
        assoc = self.assoc_repo.create(collection_id, association_input)
        logger.info("Created association %s", assoc.id)
        return assoc

    def get_association(self, association_id: UUID4) -> CollectionAgentOutput:
        """Get a collection-agent association.

        Args:
            association_id: UUID of the association

        Returns:
            Association data
        """
        return self.assoc_repo.get_by_id(association_id)

    def update_association(
        self,
        association_id: UUID4,
        update_data: CollectionAgentUpdate,
    ) -> CollectionAgentOutput:
        """Update a collection-agent association.

        Args:
            association_id: UUID of the association
            update_data: Update data

        Returns:
            Updated association
        """
        logger.info("Updating association %s", association_id)
        assoc = self.assoc_repo.update(association_id, update_data)
        logger.info("Updated association %s", association_id)
        return assoc

    def remove_agent_from_collection(self, association_id: UUID4) -> bool:
        """Remove an agent from a collection.

        Args:
            association_id: UUID of the association

        Returns:
            True if removed
        """
        logger.info("Removing association %s", association_id)
        result = self.assoc_repo.delete(association_id)
        if result:
            logger.info("Removed association %s", association_id)
        return result

    def list_collection_agents(
        self,
        collection_id: UUID4,
        stage: str | None = None,
        enabled_only: bool = False,
    ) -> CollectionAgentListResponse:
        """List agents associated with a collection.

        Args:
            collection_id: UUID of the collection
            stage: Filter by stage
            enabled_only: Only enabled associations

        Returns:
            List of associations
        """
        associations = self.assoc_repo.list_by_collection(
            collection_id=collection_id,
            stage=stage,
            enabled_only=enabled_only,
        )
        return CollectionAgentListResponse(
            associations=associations,
            total=len(associations),
        )

    def batch_update_priorities(
        self,
        collection_id: UUID4,
        priorities: dict[UUID4, int],
    ) -> list[CollectionAgentOutput]:
        """Batch update priorities for collection agents.

        Args:
            collection_id: UUID of the collection
            priorities: Mapping of association ID to priority

        Returns:
            List of updated associations
        """
        logger.info("Batch updating %d priorities for collection %s", len(priorities), collection_id)
        return self.assoc_repo.batch_update_priorities(collection_id, priorities)

    def get_collection_agent_summary(self, collection_id: UUID4) -> dict[str, Any]:
        """Get a summary of agents for a collection.

        Args:
            collection_id: UUID of the collection

        Returns:
            Summary with counts per stage
        """
        associations = self.assoc_repo.list_by_collection(collection_id, enabled_only=True)

        summary = {
            "pre_search": 0,
            "post_search": 0,
            "response": 0,
            "total": 0,
            "enabled": 0,
        }

        for assoc in associations:
            if assoc.agent_config:
                stage = assoc.agent_config.stage
                if stage in summary:
                    summary[stage] += 1
            summary["total"] += 1
            if assoc.enabled:
                summary["enabled"] += 1

        return summary
