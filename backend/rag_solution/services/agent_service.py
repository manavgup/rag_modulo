"""Service layer for Agent entity operations.

This module provides business logic for managing AI agents with
SPIFFE-based workload identity.

Reference: docs/architecture/spire-integration-architecture.md
"""

import uuid

from pydantic import UUID4
from sqlalchemy.orm import Session

from core.logging_utils import get_logger
from core.spiffe_auth import (
    AgentCapability,
    AgentPrincipal,
    AgentType,
    SPIFFEConfig,
    build_spiffe_id,
    get_spiffe_authenticator,
)
from rag_solution.models.agent import AgentStatus
from rag_solution.repository.agent_repository import AgentRepository
from rag_solution.schemas.agent_schema import (
    AgentCapabilityUpdate,
    AgentInput,
    AgentListResponse,
    AgentOutput,
    AgentRegistrationRequest,
    AgentRegistrationResponse,
    AgentStatusUpdate,
    AgentUpdate,
    SPIFFEValidationRequest,
    SPIFFEValidationResponse,
)

logger = get_logger(__name__)


class AgentService:
    """Service for managing AI agent identities.

    This service handles:
    - Agent registration with SPIFFE ID generation
    - Agent CRUD operations
    - SPIFFE JWT-SVID validation
    - Capability management
    - Agent status management
    """

    def __init__(self, db: Session) -> None:
        """Initialize the agent service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.repository = AgentRepository(db)
        self._config = SPIFFEConfig.from_env()
        self._authenticator = get_spiffe_authenticator()

    def register_agent(
        self,
        request: AgentRegistrationRequest,
        owner_user_id: UUID4,
    ) -> AgentRegistrationResponse:
        """Register a new agent with SPIFFE ID generation.

        This creates an agent record and generates the SPIFFE ID that should
        be used when configuring the SPIRE registration entry.

        Args:
            request: Agent registration request
            owner_user_id: UUID of the owning user

        Returns:
            Registration response with agent data and SPIFFE ID
        """
        # Generate unique agent instance ID
        agent_instance_id = str(uuid.uuid4())[:8]

        # Determine trust domain
        trust_domain = request.trust_domain or self._config.trust_domain

        # Generate SPIFFE ID
        if request.custom_path:
            spiffe_id = f"spiffe://{trust_domain}/agent/{request.custom_path}"
        else:
            spiffe_id = build_spiffe_id(
                trust_domain=trust_domain,
                agent_type=AgentType(request.agent_type.value),
                agent_id=agent_instance_id,
            )

        # Create agent input
        agent_input = AgentInput(
            agent_type=request.agent_type,
            name=request.name,
            description=request.description,
            team_id=request.team_id,
            capabilities=request.capabilities,
            metadata=request.metadata,
        )

        # Create agent in database
        agent = self.repository.create(
            agent_input=agent_input,
            owner_user_id=owner_user_id,
            spiffe_id=spiffe_id,
        )

        # Generate registration instructions
        instructions = self._generate_registration_instructions(
            spiffe_id=spiffe_id,
            agent_type=request.agent_type.value,
        )

        return AgentRegistrationResponse(
            agent=agent,
            spiffe_id=spiffe_id,
            registration_instructions=instructions,
        )

    def _generate_registration_instructions(self, spiffe_id: str, agent_type: str) -> str:
        """Generate SPIRE registration instructions for an agent.

        Args:
            spiffe_id: The agent's SPIFFE ID
            agent_type: Type of agent

        Returns:
            Registration instructions string
        """
        return f"""To complete agent registration, create a SPIRE registration entry:

For Kubernetes:
```
spire-server entry create \\
    -spiffeID {spiffe_id} \\
    -parentID spiffe://{self._config.trust_domain}/spire/agent/k8s/node \\
    -selector k8s:ns:rag-modulo \\
    -selector k8s:sa:{agent_type}-agent \\
    -selector k8s:pod-label:app:{agent_type}
```

For Docker/Unix:
```
spire-server entry create \\
    -spiffeID {spiffe_id} \\
    -parentID spiffe://{self._config.trust_domain}/spire/agent/unix \\
    -selector unix:uid:1000 \\
    -selector docker:label:app:{agent_type}
```

After creating the registration entry, the agent workload can fetch SVIDs via:
```python
from spiffe import JwtSource

with JwtSource() as source:
    svid = source.fetch_svid(audience={{"backend-api", "mcp-gateway"}})
    # Use svid.token in Authorization header
```
"""

    def create_agent(
        self,
        agent_input: AgentInput,
        owner_user_id: UUID4,
        spiffe_id: str | None = None,
    ) -> AgentOutput:
        """Create a new agent.

        Args:
            agent_input: Agent creation data
            owner_user_id: UUID of the owning user
            spiffe_id: Optional pre-generated SPIFFE ID

        Returns:
            Created agent data
        """
        if not spiffe_id:
            # Generate SPIFFE ID
            agent_instance_id = str(uuid.uuid4())[:8]
            spiffe_id = build_spiffe_id(
                trust_domain=self._config.trust_domain,
                agent_type=AgentType(agent_input.agent_type.value),
                agent_id=agent_instance_id,
            )

        return self.repository.create(
            agent_input=agent_input,
            owner_user_id=owner_user_id,
            spiffe_id=spiffe_id,
        )

    def get_agent(self, agent_id: UUID4) -> AgentOutput:
        """Get an agent by ID.

        Args:
            agent_id: UUID of the agent

        Returns:
            Agent data

        Raises:
            NotFoundError: If agent not found
        """
        return self.repository.get_by_id(agent_id)

    def get_agent_by_spiffe_id(self, spiffe_id: str) -> AgentOutput:
        """Get an agent by SPIFFE ID.

        Args:
            spiffe_id: Full SPIFFE ID string

        Returns:
            Agent data

        Raises:
            NotFoundError: If agent not found
        """
        return self.repository.get_by_spiffe_id(spiffe_id)

    def update_agent(self, agent_id: UUID4, agent_update: AgentUpdate) -> AgentOutput:
        """Update an agent.

        Args:
            agent_id: UUID of the agent
            agent_update: Update data

        Returns:
            Updated agent data

        Raises:
            NotFoundError: If agent not found
        """
        return self.repository.update(agent_id, agent_update)

    def delete_agent(self, agent_id: UUID4) -> bool:
        """Delete an agent.

        Args:
            agent_id: UUID of the agent

        Returns:
            True if deleted
        """
        return self.repository.delete(agent_id)

    def update_agent_status(
        self,
        agent_id: UUID4,
        status_update: AgentStatusUpdate,
    ) -> AgentOutput:
        """Update agent status.

        Args:
            agent_id: UUID of the agent
            status_update: Status update request

        Returns:
            Updated agent data

        Raises:
            NotFoundError: If agent not found
        """
        # Log status change with reason
        logger.info(
            "Updating agent %s status to %s. Reason: %s",
            agent_id,
            status_update.status.value,
            status_update.reason or "No reason provided",
        )
        return self.repository.update_status(agent_id, status_update.status.value)

    def update_agent_capabilities(
        self,
        agent_id: UUID4,
        capability_update: AgentCapabilityUpdate,
    ) -> AgentOutput:
        """Update agent capabilities.

        Args:
            agent_id: UUID of the agent
            capability_update: Capability update request

        Returns:
            Updated agent data

        Raises:
            NotFoundError: If agent not found
        """
        add_caps = [cap.value for cap in capability_update.add_capabilities]
        remove_caps = [cap.value for cap in capability_update.remove_capabilities]

        return self.repository.update_capabilities(
            agent_id=agent_id,
            add_capabilities=add_caps,
            remove_capabilities=remove_caps,
        )

    def list_agents(
        self,
        skip: int = 0,
        limit: int = 100,
        owner_user_id: UUID4 | None = None,
        team_id: UUID4 | None = None,
        agent_type: str | None = None,
        status: str | None = None,
    ) -> AgentListResponse:
        """List agents with filtering and pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            owner_user_id: Filter by owner
            team_id: Filter by team
            agent_type: Filter by type
            status: Filter by status

        Returns:
            Paginated agent list
        """
        agents, total = self.repository.list_agents(
            skip=skip,
            limit=limit,
            owner_user_id=owner_user_id,
            team_id=team_id,
            agent_type=agent_type,
            status=status,
        )
        return AgentListResponse(
            agents=agents,
            total=total,
            skip=skip,
            limit=limit,
        )

    def list_user_agents(self, owner_user_id: UUID4, skip: int = 0, limit: int = 100) -> list[AgentOutput]:
        """List agents owned by a user.

        Args:
            owner_user_id: UUID of the owner
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of agents
        """
        return self.repository.list_by_owner(owner_user_id, skip, limit)

    def validate_jwt_svid(self, request: SPIFFEValidationRequest) -> SPIFFEValidationResponse:
        """Validate a SPIFFE JWT-SVID.

        This validates the token and returns agent identity information.

        Args:
            request: Validation request with token

        Returns:
            Validation response
        """
        try:
            principal = self._authenticator.validate_jwt_svid(
                token=request.token,
                required_audience=request.required_audience,
            )

            if principal is None:
                return SPIFFEValidationResponse(
                    valid=False,
                    error="Invalid or expired JWT-SVID",
                )

            # Update last seen for the agent
            self.repository.update_last_seen_by_spiffe_id(principal.spiffe_id)

            return SPIFFEValidationResponse(
                valid=True,
                spiffe_id=principal.spiffe_id,
                agent_type=principal.agent_type.value,
                agent_id=principal.agent_id,
                capabilities=[cap.value for cap in principal.capabilities],
                audiences=principal.audiences,
                expires_at=principal.expires_at,
            )
        except Exception as e:
            logger.error("Error validating JWT-SVID: %s", e)
            return SPIFFEValidationResponse(
                valid=False,
                error=str(e),
            )

    def get_agent_principal_from_token(self, token: str) -> AgentPrincipal | None:
        """Extract agent principal from a JWT-SVID token.

        This is used by the authentication middleware to identify agents.

        Args:
            token: JWT-SVID token

        Returns:
            AgentPrincipal if valid, None otherwise
        """
        principal = self._authenticator.validate_jwt_svid(token)

        if principal is None:
            return None

        # Check if agent exists and is active
        agent_model = self.repository.get_model_by_spiffe_id(principal.spiffe_id)
        if agent_model is None:
            logger.warning("Agent with SPIFFE ID %s not found in database", principal.spiffe_id)
            # Allow unknown agents if SPIFFE validation passed (for new agents)
            return principal

        if not agent_model.is_active():
            logger.warning("Agent %s is not active (status: %s)", principal.spiffe_id, agent_model.status)
            return None

        # Update last seen
        agent_model.update_last_seen()
        self.db.commit()

        # Merge database capabilities with SVID capabilities
        db_capabilities = [
            AgentCapability(cap) for cap in agent_model.capabilities if cap in AgentCapability.__members__
        ]
        principal.capabilities = list(set(principal.capabilities + db_capabilities))

        return principal

    def suspend_agent(self, agent_id: UUID4, reason: str | None = None) -> AgentOutput:
        """Suspend an agent.

        Args:
            agent_id: UUID of the agent
            reason: Optional reason for suspension

        Returns:
            Updated agent data
        """
        return self.update_agent_status(
            agent_id,
            AgentStatusUpdate(status=AgentStatus.SUSPENDED, reason=reason),
        )

    def activate_agent(self, agent_id: UUID4, reason: str | None = None) -> AgentOutput:
        """Activate an agent.

        Args:
            agent_id: UUID of the agent
            reason: Optional reason for activation

        Returns:
            Updated agent data
        """
        return self.update_agent_status(
            agent_id,
            AgentStatusUpdate(status=AgentStatus.ACTIVE, reason=reason),
        )

    def revoke_agent(self, agent_id: UUID4, reason: str | None = None) -> AgentOutput:
        """Revoke an agent's credentials.

        Args:
            agent_id: UUID of the agent
            reason: Optional reason for revocation

        Returns:
            Updated agent data
        """
        return self.update_agent_status(
            agent_id,
            AgentStatusUpdate(status=AgentStatus.REVOKED, reason=reason),
        )

    def get_agent_count_for_user(self, owner_user_id: UUID4) -> int:
        """Get the number of agents owned by a user.

        Args:
            owner_user_id: UUID of the owner

        Returns:
            Agent count
        """
        return self.repository.count_by_owner(owner_user_id)

    def get_active_agent_count(self) -> int:
        """Get the total number of active agents.

        Returns:
            Active agent count
        """
        return self.repository.count_active()
