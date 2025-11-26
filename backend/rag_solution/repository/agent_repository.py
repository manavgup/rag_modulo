"""Repository for Agent entity database operations.

This module provides data access for AI agents with SPIFFE-based
workload identity.

Reference: docs/architecture/spire-integration-architecture.md
"""

from datetime import datetime
from typing import Any

from pydantic import UUID4
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from core.custom_exceptions import RepositoryError
from core.logging_utils import get_logger
from rag_solution.core.exceptions import AlreadyExistsError, NotFoundError, ValidationError
from rag_solution.models.agent import Agent, AgentStatus
from rag_solution.schemas.agent_schema import AgentInput, AgentOutput, AgentUpdate

logger = get_logger(__name__)


class AgentRepository:
    """Repository for handling Agent entity database operations."""

    def __init__(self: Any, db: Session) -> None:
        """Initialize with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create(
        self,
        agent_input: AgentInput,
        owner_user_id: UUID4,
        spiffe_id: str,
    ) -> AgentOutput:
        """Create a new agent.

        Args:
            agent_input: Agent creation data
            owner_user_id: UUID of the owning user
            spiffe_id: Generated SPIFFE ID for the agent

        Returns:
            Created agent data

        Raises:
            AlreadyExistsError: If SPIFFE ID already exists
            ValidationError: For validation errors
            RepositoryError: For other database errors
        """
        try:
            # Convert capabilities to list of strings
            capabilities = [cap.value for cap in agent_input.capabilities]

            agent = Agent(
                spiffe_id=spiffe_id,
                agent_type=agent_input.agent_type.value,
                name=agent_input.name,
                description=agent_input.description,
                owner_user_id=owner_user_id,
                team_id=agent_input.team_id,
                capabilities=capabilities,
                metadata=agent_input.metadata or {},
                status=AgentStatus.ACTIVE,
            )
            self.db.add(agent)
            self.db.commit()
            self.db.refresh(agent)
            return AgentOutput.model_validate(agent)
        except IntegrityError as e:
            self.db.rollback()
            if "agents_spiffe_id_key" in str(e) or "ix_agents_spiffe_id" in str(e):
                raise AlreadyExistsError("Agent", "spiffe_id", spiffe_id) from e
            raise ValidationError("An error occurred while creating the agent") from e
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating agent: {e!s}")
            raise RepositoryError(f"Failed to create agent: {e!s}") from e

    def get_by_id(self, agent_id: UUID4) -> AgentOutput:
        """Fetch agent by ID with relationships.

        Args:
            agent_id: UUID of the agent

        Returns:
            Agent data

        Raises:
            NotFoundError: If agent not found
            RepositoryError: For database errors
        """
        try:
            agent = (
                self.db.query(Agent)
                .filter(Agent.id == agent_id)
                .options(joinedload(Agent.owner), joinedload(Agent.team))
                .first()
            )
            if not agent:
                raise NotFoundError("Agent", resource_id=str(agent_id))
            return AgentOutput.model_validate(agent, from_attributes=True)
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting agent {agent_id}: {e!s}")
            raise RepositoryError(f"Failed to get agent by ID: {e!s}") from e

    def get_by_spiffe_id(self, spiffe_id: str) -> AgentOutput:
        """Fetch agent by SPIFFE ID.

        Args:
            spiffe_id: Full SPIFFE ID string

        Returns:
            Agent data

        Raises:
            NotFoundError: If agent not found
            RepositoryError: For database errors
        """
        try:
            agent = (
                self.db.query(Agent)
                .filter(Agent.spiffe_id == spiffe_id)
                .options(joinedload(Agent.owner), joinedload(Agent.team))
                .first()
            )
            if not agent:
                raise NotFoundError("Agent", identifier=f"spiffe_id={spiffe_id}")
            return AgentOutput.model_validate(agent)
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting agent by SPIFFE ID {spiffe_id}: {e!s}")
            raise RepositoryError(f"Failed to get agent by SPIFFE ID: {e!s}") from e

    def get_model_by_spiffe_id(self, spiffe_id: str) -> Agent | None:
        """Fetch agent model by SPIFFE ID (for internal use).

        Args:
            spiffe_id: Full SPIFFE ID string

        Returns:
            Agent model or None if not found
        """
        try:
            return self.db.query(Agent).filter(Agent.spiffe_id == spiffe_id).first()
        except Exception as e:
            logger.error(f"Error getting agent model by SPIFFE ID {spiffe_id}: {e!s}")
            return None

    def update(self, agent_id: UUID4, agent_update: AgentUpdate) -> AgentOutput:
        """Update agent data.

        Args:
            agent_id: UUID of the agent
            agent_update: Update data

        Returns:
            Updated agent data

        Raises:
            NotFoundError: If agent not found
            RepositoryError: For database errors
        """
        try:
            agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
            if not agent:
                raise NotFoundError("Agent", resource_id=str(agent_id))

            # Update only provided fields
            update_data = agent_update.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                if key == "capabilities" and value is not None:
                    # Convert capability enums to strings
                    value = [cap.value if hasattr(cap, "value") else cap for cap in value]
                if key == "status" and value is not None:
                    value = value.value if hasattr(value, "value") else value
                setattr(agent, key, value)

            self.db.commit()
            self.db.refresh(agent)
            return AgentOutput.model_validate(agent)
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error updating agent {agent_id}: {e!s}")
            self.db.rollback()
            raise RepositoryError(f"Failed to update agent: {e!s}") from e

    def update_status(self, agent_id: UUID4, status: str) -> AgentOutput:
        """Update agent status.

        Args:
            agent_id: UUID of the agent
            status: New status value

        Returns:
            Updated agent data

        Raises:
            NotFoundError: If agent not found
            RepositoryError: For database errors
        """
        try:
            agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
            if not agent:
                raise NotFoundError("Agent", resource_id=str(agent_id))

            agent.status = status
            self.db.commit()
            self.db.refresh(agent)
            return AgentOutput.model_validate(agent)
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error updating agent status {agent_id}: {e!s}")
            self.db.rollback()
            raise RepositoryError(f"Failed to update agent status: {e!s}") from e

    def update_capabilities(
        self,
        agent_id: UUID4,
        add_capabilities: list[str] | None = None,
        remove_capabilities: list[str] | None = None,
    ) -> AgentOutput:
        """Update agent capabilities.

        Args:
            agent_id: UUID of the agent
            add_capabilities: Capabilities to add
            remove_capabilities: Capabilities to remove

        Returns:
            Updated agent data

        Raises:
            NotFoundError: If agent not found
            RepositoryError: For database errors
        """
        try:
            agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
            if not agent:
                raise NotFoundError("Agent", resource_id=str(agent_id))

            current_capabilities = set(agent.capabilities)

            if add_capabilities:
                current_capabilities.update(add_capabilities)
            if remove_capabilities:
                current_capabilities.difference_update(remove_capabilities)

            agent.capabilities = list(current_capabilities)
            self.db.commit()
            self.db.refresh(agent)
            return AgentOutput.model_validate(agent)
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error updating agent capabilities {agent_id}: {e!s}")
            self.db.rollback()
            raise RepositoryError(f"Failed to update agent capabilities: {e!s}") from e

    def update_last_seen(self, agent_id: UUID4) -> None:
        """Update the last seen timestamp for an agent.

        Args:
            agent_id: UUID of the agent
        """
        try:
            agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
            if agent:
                agent.last_seen_at = datetime.now()
                self.db.commit()
        except Exception as e:
            logger.error(f"Error updating agent last_seen {agent_id}: {e!s}")
            self.db.rollback()

    def update_last_seen_by_spiffe_id(self, spiffe_id: str) -> None:
        """Update the last seen timestamp for an agent by SPIFFE ID.

        Args:
            spiffe_id: SPIFFE ID of the agent
        """
        try:
            agent = self.db.query(Agent).filter(Agent.spiffe_id == spiffe_id).first()
            if agent:
                agent.last_seen_at = datetime.now()
                self.db.commit()
        except Exception as e:
            logger.error(f"Error updating agent last_seen by SPIFFE ID {spiffe_id}: {e!s}")
            self.db.rollback()

    def delete(self, agent_id: UUID4) -> bool:
        """Delete an agent.

        Args:
            agent_id: UUID of the agent

        Returns:
            True if deleted, False if not found
        """
        try:
            result = self.db.query(Agent).filter(Agent.id == agent_id).delete()
            self.db.commit()
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting agent {agent_id}: {e!s}")
            self.db.rollback()
            raise RepositoryError(f"Failed to delete agent: {e!s}") from e

    def list_agents(
        self,
        skip: int = 0,
        limit: int = 100,
        owner_user_id: UUID4 | None = None,
        team_id: UUID4 | None = None,
        agent_type: str | None = None,
        status: str | None = None,
    ) -> tuple[list[AgentOutput], int]:
        """List agents with optional filters and pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            owner_user_id: Filter by owner user ID
            team_id: Filter by team ID
            agent_type: Filter by agent type
            status: Filter by status

        Returns:
            Tuple of (list of agents, total count)
        """
        try:
            query = self.db.query(Agent)

            # Apply filters
            if owner_user_id:
                query = query.filter(Agent.owner_user_id == owner_user_id)
            if team_id:
                query = query.filter(Agent.team_id == team_id)
            if agent_type:
                query = query.filter(Agent.agent_type == agent_type)
            if status:
                query = query.filter(Agent.status == status)

            # Get total count
            total = query.count()

            # Apply pagination and fetch
            agents = (
                query.options(joinedload(Agent.owner), joinedload(Agent.team))
                .order_by(Agent.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )

            return ([AgentOutput.model_validate(agent) for agent in agents], total)
        except Exception as e:
            logger.error(f"Error listing agents: {e!s}")
            raise RepositoryError(f"Failed to list agents: {e!s}") from e

    def list_by_owner(self, owner_user_id: UUID4, skip: int = 0, limit: int = 100) -> list[AgentOutput]:
        """List agents owned by a specific user.

        Args:
            owner_user_id: UUID of the owner
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of agents
        """
        agents, _ = self.list_agents(skip=skip, limit=limit, owner_user_id=owner_user_id)
        return agents

    def list_by_team(self, team_id: UUID4, skip: int = 0, limit: int = 100) -> list[AgentOutput]:
        """List agents in a specific team.

        Args:
            team_id: UUID of the team
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of agents
        """
        agents, _ = self.list_agents(skip=skip, limit=limit, team_id=team_id)
        return agents

    def list_active_by_type(self, agent_type: str, limit: int = 100) -> list[AgentOutput]:
        """List active agents of a specific type.

        Args:
            agent_type: Type of agent
            limit: Maximum number of records to return

        Returns:
            List of active agents
        """
        agents, _ = self.list_agents(limit=limit, agent_type=agent_type, status=AgentStatus.ACTIVE)
        return agents

    def count_by_owner(self, owner_user_id: UUID4) -> int:
        """Count agents owned by a user.

        Args:
            owner_user_id: UUID of the owner

        Returns:
            Number of agents
        """
        try:
            return self.db.query(func.count(Agent.id)).filter(Agent.owner_user_id == owner_user_id).scalar() or 0
        except Exception as e:
            logger.error(f"Error counting agents for owner {owner_user_id}: {e!s}")
            return 0

    def count_active(self) -> int:
        """Count all active agents.

        Returns:
            Number of active agents
        """
        try:
            return self.db.query(func.count(Agent.id)).filter(Agent.status == AgentStatus.ACTIVE).scalar() or 0
        except Exception as e:
            logger.error(f"Error counting active agents: {e!s}")
            return 0
