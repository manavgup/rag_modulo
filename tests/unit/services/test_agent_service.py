"""Unit tests for Agent service.

This module tests the AgentService functionality including:
- Agent registration with SPIFFE ID generation
- Agent CRUD operations
- Status management
- Capability management
- JWT-SVID validation

Reference: docs/architecture/spire-integration-architecture.md
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from core.spiffe_auth import AgentCapability, AgentPrincipal, AgentType
from rag_solution.schemas.agent_schema import AgentCapability as SchemaAgentCapability
from rag_solution.schemas.agent_schema import (
    AgentCapabilityUpdate,
    AgentInput,
    AgentOutput,
    AgentRegistrationRequest,
    AgentStatusUpdate,
    AgentUpdate,
    SPIFFEValidationRequest,
)
from rag_solution.schemas.agent_schema import AgentStatus as SchemaAgentStatus
from rag_solution.schemas.agent_schema import AgentType as SchemaAgentType
from rag_solution.services.agent_service import AgentService


@pytest.fixture
def mock_db() -> MagicMock:
    """Create a mock database session."""
    return MagicMock()


@pytest.fixture
def mock_repository() -> MagicMock:
    """Create a mock agent repository."""
    return MagicMock()


@pytest.fixture
def sample_agent_output() -> AgentOutput:
    """Create a sample agent output for testing."""
    return AgentOutput(
        id=uuid.uuid4(),
        spiffe_id="spiffe://rag-modulo.example.com/agent/search-enricher/agent-001",
        agent_type="search-enricher",
        name="Test Agent",
        description="A test agent",
        owner_user_id=uuid.uuid4(),
        team_id=None,
        capabilities=["search:read", "llm:invoke"],
        metadata={},
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        last_seen_at=None,
    )


class TestAgentServiceRegistration:
    """Tests for agent registration functionality."""

    def test_register_agent_generates_spiffe_id(self, mock_db: MagicMock, sample_agent_output: AgentOutput) -> None:
        """Test that registration generates a valid SPIFFE ID."""
        with patch("rag_solution.services.agent_service.AgentRepository") as mock_repo_class:
            mock_repo_instance = MagicMock()
            mock_repo_instance.create.return_value = sample_agent_output
            mock_repo_class.return_value = mock_repo_instance

            service = AgentService(mock_db)
            request = AgentRegistrationRequest(
                agent_type=SchemaAgentType.SEARCH_ENRICHER,
                name="Test Agent",
                description="Test description",
                capabilities=[SchemaAgentCapability.SEARCH_READ],
            )

            result = service.register_agent(request, uuid.uuid4())

            assert result is not None
            assert result.spiffe_id.startswith("spiffe://")
            assert "agent/search-enricher/" in result.spiffe_id
            assert result.registration_instructions is not None

    def test_register_agent_with_custom_trust_domain(
        self, mock_db: MagicMock, sample_agent_output: AgentOutput
    ) -> None:
        """Test registration with custom trust domain."""
        with patch("rag_solution.services.agent_service.AgentRepository") as mock_repo_class:
            mock_repo_instance = MagicMock()
            mock_repo_instance.create.return_value = sample_agent_output
            mock_repo_class.return_value = mock_repo_instance

            service = AgentService(mock_db)
            request = AgentRegistrationRequest(
                agent_type=SchemaAgentType.COT_REASONING,
                name="Custom Domain Agent",
                trust_domain="custom.domain.com",
            )

            result = service.register_agent(request, uuid.uuid4())

            assert result is not None
            # The SPIFFE ID should use the custom trust domain
            mock_repo_instance.create.assert_called_once()
            call_args = mock_repo_instance.create.call_args
            assert "custom.domain.com" in call_args.kwargs["spiffe_id"]

    def test_register_agent_with_custom_path(self, mock_db: MagicMock, sample_agent_output: AgentOutput) -> None:
        """Test registration with custom SPIFFE path."""
        with patch("rag_solution.services.agent_service.AgentRepository") as mock_repo_class:
            mock_repo_instance = MagicMock()
            mock_repo_instance.create.return_value = sample_agent_output
            mock_repo_class.return_value = mock_repo_instance

            service = AgentService(mock_db)
            request = AgentRegistrationRequest(
                agent_type=SchemaAgentType.CUSTOM,
                name="Custom Path Agent",
                custom_path="custom/path/agent-xyz",
            )

            result = service.register_agent(request, uuid.uuid4())

            assert result is not None
            mock_repo_instance.create.assert_called_once()
            call_args = mock_repo_instance.create.call_args
            assert "/agent/custom/path/agent-xyz" in call_args.kwargs["spiffe_id"]


class TestAgentServiceCRUD:
    """Tests for agent CRUD operations."""

    def test_create_agent(self, mock_db: MagicMock, sample_agent_output: AgentOutput) -> None:
        """Test creating an agent."""
        with patch("rag_solution.services.agent_service.AgentRepository") as mock_repo_class:
            mock_repo_instance = MagicMock()
            mock_repo_instance.create.return_value = sample_agent_output
            mock_repo_class.return_value = mock_repo_instance

            service = AgentService(mock_db)
            agent_input = AgentInput(
                agent_type=SchemaAgentType.SEARCH_ENRICHER,
                name="New Agent",
                capabilities=[SchemaAgentCapability.SEARCH_READ],
            )

            result = service.create_agent(agent_input, uuid.uuid4())

            assert result is not None
            assert result.name == sample_agent_output.name
            mock_repo_instance.create.assert_called_once()

    def test_get_agent(self, mock_db: MagicMock, sample_agent_output: AgentOutput) -> None:
        """Test getting an agent by ID."""
        with patch("rag_solution.services.agent_service.AgentRepository") as mock_repo_class:
            mock_repo_instance = MagicMock()
            mock_repo_instance.get_by_id.return_value = sample_agent_output
            mock_repo_class.return_value = mock_repo_instance

            service = AgentService(mock_db)
            result = service.get_agent(sample_agent_output.id)

            assert result is not None
            assert result.id == sample_agent_output.id
            mock_repo_instance.get_by_id.assert_called_once_with(sample_agent_output.id)

    def test_get_agent_by_spiffe_id(self, mock_db: MagicMock, sample_agent_output: AgentOutput) -> None:
        """Test getting an agent by SPIFFE ID."""
        with patch("rag_solution.services.agent_service.AgentRepository") as mock_repo_class:
            mock_repo_instance = MagicMock()
            mock_repo_instance.get_by_spiffe_id.return_value = sample_agent_output
            mock_repo_class.return_value = mock_repo_instance

            service = AgentService(mock_db)
            result = service.get_agent_by_spiffe_id(sample_agent_output.spiffe_id)

            assert result is not None
            assert result.spiffe_id == sample_agent_output.spiffe_id
            mock_repo_instance.get_by_spiffe_id.assert_called_once_with(sample_agent_output.spiffe_id)

    def test_update_agent(self, mock_db: MagicMock, sample_agent_output: AgentOutput) -> None:
        """Test updating an agent."""
        with patch("rag_solution.services.agent_service.AgentRepository") as mock_repo_class:
            mock_repo_instance = MagicMock()
            updated_output = sample_agent_output.model_copy()
            updated_output.name = "Updated Name"
            mock_repo_instance.update.return_value = updated_output
            mock_repo_class.return_value = mock_repo_instance

            service = AgentService(mock_db)
            update = AgentUpdate(name="Updated Name")

            result = service.update_agent(sample_agent_output.id, update)

            assert result is not None
            assert result.name == "Updated Name"
            mock_repo_instance.update.assert_called_once()

    def test_delete_agent(self, mock_db: MagicMock) -> None:
        """Test deleting an agent."""
        with patch("rag_solution.services.agent_service.AgentRepository") as mock_repo_class:
            mock_repo_instance = MagicMock()
            mock_repo_instance.delete.return_value = True
            mock_repo_class.return_value = mock_repo_instance

            service = AgentService(mock_db)
            agent_id = uuid.uuid4()

            result = service.delete_agent(agent_id)

            assert result is True
            mock_repo_instance.delete.assert_called_once_with(agent_id)


class TestAgentServiceStatusManagement:
    """Tests for agent status management."""

    def test_update_agent_status(self, mock_db: MagicMock, sample_agent_output: AgentOutput) -> None:
        """Test updating agent status."""
        with patch("rag_solution.services.agent_service.AgentRepository") as mock_repo_class:
            mock_repo_instance = MagicMock()
            suspended_output = sample_agent_output.model_copy()
            suspended_output.status = "suspended"
            mock_repo_instance.update_status.return_value = suspended_output
            mock_repo_class.return_value = mock_repo_instance

            service = AgentService(mock_db)
            status_update = AgentStatusUpdate(
                status=SchemaAgentStatus.SUSPENDED,
                reason="Maintenance",
            )

            result = service.update_agent_status(sample_agent_output.id, status_update)

            assert result is not None
            assert result.status == "suspended"
            mock_repo_instance.update_status.assert_called_once()

    def test_suspend_agent(self, mock_db: MagicMock, sample_agent_output: AgentOutput) -> None:
        """Test suspending an agent."""
        with patch("rag_solution.services.agent_service.AgentRepository") as mock_repo_class:
            mock_repo_instance = MagicMock()
            suspended_output = sample_agent_output.model_copy()
            suspended_output.status = "suspended"
            mock_repo_instance.update_status.return_value = suspended_output
            mock_repo_class.return_value = mock_repo_instance

            service = AgentService(mock_db)
            result = service.suspend_agent(sample_agent_output.id, "Security review")

            assert result is not None
            assert result.status == "suspended"

    def test_activate_agent(self, mock_db: MagicMock, sample_agent_output: AgentOutput) -> None:
        """Test activating an agent."""
        with patch("rag_solution.services.agent_service.AgentRepository") as mock_repo_class:
            mock_repo_instance = MagicMock()
            active_output = sample_agent_output.model_copy()
            active_output.status = "active"
            mock_repo_instance.update_status.return_value = active_output
            mock_repo_class.return_value = mock_repo_instance

            service = AgentService(mock_db)
            result = service.activate_agent(sample_agent_output.id, "Review complete")

            assert result is not None
            assert result.status == "active"

    def test_revoke_agent(self, mock_db: MagicMock, sample_agent_output: AgentOutput) -> None:
        """Test revoking an agent."""
        with patch("rag_solution.services.agent_service.AgentRepository") as mock_repo_class:
            mock_repo_instance = MagicMock()
            revoked_output = sample_agent_output.model_copy()
            revoked_output.status = "revoked"
            mock_repo_instance.update_status.return_value = revoked_output
            mock_repo_class.return_value = mock_repo_instance

            service = AgentService(mock_db)
            result = service.revoke_agent(sample_agent_output.id, "Policy violation")

            assert result is not None
            assert result.status == "revoked"


class TestAgentServiceCapabilities:
    """Tests for agent capability management."""

    def test_update_agent_capabilities(self, mock_db: MagicMock, sample_agent_output: AgentOutput) -> None:
        """Test updating agent capabilities."""
        with patch("rag_solution.services.agent_service.AgentRepository") as mock_repo_class:
            mock_repo_instance = MagicMock()
            updated_output = sample_agent_output.model_copy()
            updated_output.capabilities = ["search:read", "llm:invoke", "cot:invoke"]
            mock_repo_instance.update_capabilities.return_value = updated_output
            mock_repo_class.return_value = mock_repo_instance

            service = AgentService(mock_db)
            capability_update = AgentCapabilityUpdate(
                add_capabilities=[SchemaAgentCapability.COT_INVOKE],
                remove_capabilities=[],
            )

            result = service.update_agent_capabilities(sample_agent_output.id, capability_update)

            assert result is not None
            assert "cot:invoke" in result.capabilities


class TestAgentServiceListing:
    """Tests for agent listing functionality."""

    def test_list_agents(self, mock_db: MagicMock, sample_agent_output: AgentOutput) -> None:
        """Test listing agents with pagination."""
        with patch("rag_solution.services.agent_service.AgentRepository") as mock_repo_class:
            mock_repo_instance = MagicMock()
            mock_repo_instance.list_agents.return_value = ([sample_agent_output], 1)
            mock_repo_class.return_value = mock_repo_instance

            service = AgentService(mock_db)
            result = service.list_agents(skip=0, limit=10)

            assert result is not None
            assert result.total == 1
            assert len(result.agents) == 1
            assert result.skip == 0
            assert result.limit == 10

    def test_list_agents_with_filters(self, mock_db: MagicMock, sample_agent_output: AgentOutput) -> None:
        """Test listing agents with filters."""
        with patch("rag_solution.services.agent_service.AgentRepository") as mock_repo_class:
            mock_repo_instance = MagicMock()
            mock_repo_instance.list_agents.return_value = ([sample_agent_output], 1)
            mock_repo_class.return_value = mock_repo_instance

            service = AgentService(mock_db)
            owner_id = uuid.uuid4()
            team_id = uuid.uuid4()

            result = service.list_agents(
                skip=0,
                limit=10,
                owner_user_id=owner_id,
                team_id=team_id,
                agent_type="search-enricher",
                status="active",
            )

            assert result is not None
            mock_repo_instance.list_agents.assert_called_once_with(
                skip=0,
                limit=10,
                owner_user_id=owner_id,
                team_id=team_id,
                agent_type="search-enricher",
                status="active",
            )

    def test_list_user_agents(self, mock_db: MagicMock, sample_agent_output: AgentOutput) -> None:
        """Test listing agents for a specific user."""
        with patch("rag_solution.services.agent_service.AgentRepository") as mock_repo_class:
            mock_repo_instance = MagicMock()
            mock_repo_instance.list_by_owner.return_value = [sample_agent_output]
            mock_repo_class.return_value = mock_repo_instance

            service = AgentService(mock_db)
            owner_id = uuid.uuid4()

            result = service.list_user_agents(owner_id)

            assert result is not None
            assert len(result) == 1
            mock_repo_instance.list_by_owner.assert_called_once()


class TestAgentServiceValidation:
    """Tests for JWT-SVID validation."""

    def test_validate_jwt_svid_valid(self, mock_db: MagicMock) -> None:
        """Test validating a valid JWT-SVID."""
        with (
            patch("rag_solution.services.agent_service.AgentRepository") as mock_repo_class,
            patch("rag_solution.services.agent_service.get_spiffe_authenticator") as mock_get_auth,
        ):
            mock_repo_instance = MagicMock()
            mock_repo_class.return_value = mock_repo_instance

            mock_authenticator = MagicMock()
            mock_principal = AgentPrincipal(
                spiffe_id="spiffe://rag-modulo.example.com/agent/search-enricher/agent-001",
                agent_type=AgentType.SEARCH_ENRICHER,
                agent_id="agent-001",
                capabilities=[AgentCapability.SEARCH_READ],
                audiences=["backend-api"],
                expires_at=datetime.now(UTC),
            )
            mock_authenticator.validate_jwt_svid.return_value = mock_principal
            mock_get_auth.return_value = mock_authenticator

            service = AgentService(mock_db)
            request = SPIFFEValidationRequest(token="valid.jwt.token")

            result = service.validate_jwt_svid(request)

            assert result is not None
            assert result.valid is True
            assert result.spiffe_id == mock_principal.spiffe_id

    def test_validate_jwt_svid_invalid(self, mock_db: MagicMock) -> None:
        """Test validating an invalid JWT-SVID."""
        with (
            patch("rag_solution.services.agent_service.AgentRepository") as mock_repo_class,
            patch("rag_solution.services.agent_service.get_spiffe_authenticator") as mock_get_auth,
        ):
            mock_repo_instance = MagicMock()
            mock_repo_class.return_value = mock_repo_instance

            mock_authenticator = MagicMock()
            mock_authenticator.validate_jwt_svid.return_value = None
            mock_get_auth.return_value = mock_authenticator

            service = AgentService(mock_db)
            request = SPIFFEValidationRequest(token="invalid.jwt.token")

            result = service.validate_jwt_svid(request)

            assert result is not None
            assert result.valid is False
            assert result.error is not None


class TestAgentServiceMetrics:
    """Tests for agent metrics and counting."""

    def test_get_agent_count_for_user(self, mock_db: MagicMock) -> None:
        """Test getting agent count for a user."""
        with patch("rag_solution.services.agent_service.AgentRepository") as mock_repo_class:
            mock_repo_instance = MagicMock()
            mock_repo_instance.count_by_owner.return_value = 5
            mock_repo_class.return_value = mock_repo_instance

            service = AgentService(mock_db)
            owner_id = uuid.uuid4()

            result = service.get_agent_count_for_user(owner_id)

            assert result == 5
            mock_repo_instance.count_by_owner.assert_called_once_with(owner_id)

    def test_get_active_agent_count(self, mock_db: MagicMock) -> None:
        """Test getting total active agent count."""
        with patch("rag_solution.services.agent_service.AgentRepository") as mock_repo_class:
            mock_repo_instance = MagicMock()
            mock_repo_instance.count_active.return_value = 10
            mock_repo_class.return_value = mock_repo_instance

            service = AgentService(mock_db)
            result = service.get_active_agent_count()

            assert result == 10
            mock_repo_instance.count_active.assert_called_once()
