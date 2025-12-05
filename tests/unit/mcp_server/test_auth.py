"""Unit tests for MCP authentication module.

Tests for SPIFFE JWT-SVID, Bearer token, API key, and trusted proxy authentication.
"""

import sys
from dataclasses import dataclass
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from backend.mcp_server.auth import MCPAuthContext, MCPAuthenticator


@dataclass
class MockSettings:
    """Mock settings for testing."""

    SPIFFE_ENDPOINT_SOCKET: str | None = None
    JWT_SECRET_KEY: str | None = "test-secret-key"
    MCP_API_KEY: str | None = "test-api-key-12345"


class TestMCPAuthContext:
    """Tests for MCPAuthContext dataclass."""

    def test_default_values(self) -> None:
        """Test MCPAuthContext has correct default values."""
        ctx = MCPAuthContext()

        assert ctx.user_id is None
        assert ctx.username is None
        assert ctx.agent_id is None
        assert ctx.permissions == []
        assert ctx.is_authenticated is False
        assert ctx.auth_method == "none"
        assert ctx.metadata == {}

    def test_custom_values(self) -> None:
        """Test MCPAuthContext with custom values."""
        user_id = UUID("12345678-1234-5678-1234-567812345678")
        ctx = MCPAuthContext(
            user_id=user_id,
            username="testuser@example.com",
            agent_id="spiffe://example.org/agent/test",
            permissions=["rag:search", "rag:read"],
            is_authenticated=True,
            auth_method="bearer",
            metadata={"exp": 1234567890},
        )

        assert ctx.user_id == user_id
        assert ctx.username == "testuser@example.com"
        assert ctx.agent_id == "spiffe://example.org/agent/test"
        assert ctx.permissions == ["rag:search", "rag:read"]
        assert ctx.is_authenticated is True
        assert ctx.auth_method == "bearer"
        assert ctx.metadata == {"exp": 1234567890}


class TestMCPAuthenticator:
    """Tests for MCPAuthenticator class."""

    @pytest.fixture
    def settings(self) -> MockSettings:
        """Create mock settings."""
        return MockSettings()

    @pytest.fixture
    def authenticator(self, settings: MockSettings) -> MCPAuthenticator:
        """Create authenticator instance."""
        return MCPAuthenticator(settings)

    def test_init(self, settings: MockSettings) -> None:
        """Test authenticator initialization."""
        auth = MCPAuthenticator(settings)

        # The refactored authenticator only stores settings
        # SPIFFE validation is delegated to backend.core.spiffe_auth
        assert auth.settings == settings

    @pytest.mark.asyncio
    async def test_authenticate_request_no_credentials(self, authenticator: MCPAuthenticator) -> None:
        """Test authentication with no credentials returns unauthenticated context."""
        headers: dict[str, str] = {}

        result = await authenticator.authenticate_request(headers)

        assert result.is_authenticated is False
        assert result.auth_method == "none"

    @pytest.mark.asyncio
    async def test_authenticate_request_no_credentials_with_required_permissions(
        self, authenticator: MCPAuthenticator
    ) -> None:
        """Test authentication raises PermissionError when required permissions are missing."""
        headers: dict[str, str] = {}

        with pytest.raises(PermissionError, match="Authentication required"):
            await authenticator.authenticate_request(headers, required_permissions=["rag:search"])

    @pytest.mark.asyncio
    async def test_authenticate_api_key_valid(self, authenticator: MCPAuthenticator) -> None:
        """Test valid API key authentication."""
        headers = {"X-API-Key": "test-api-key-12345"}  # pragma: allowlist secret

        result = await authenticator.authenticate_request(headers)

        assert result.is_authenticated is True
        assert result.auth_method == "api_key"
        assert "rag:search" in result.permissions
        assert "rag:read" in result.permissions

    @pytest.mark.asyncio
    async def test_authenticate_api_key_lowercase_header(self, authenticator: MCPAuthenticator) -> None:
        """Test API key authentication with lowercase header."""
        headers = {"x-api-key": "test-api-key-12345"}  # pragma: allowlist secret

        result = await authenticator.authenticate_request(headers)

        assert result.is_authenticated is True
        assert result.auth_method == "api_key"

    @pytest.mark.asyncio
    async def test_authenticate_api_key_invalid(self, authenticator: MCPAuthenticator) -> None:
        """Test invalid API key returns unauthenticated context."""
        headers = {"X-API-Key": "wrong-api-key"}

        result = await authenticator.authenticate_request(headers)

        assert result.is_authenticated is False

    @pytest.mark.asyncio
    async def test_authenticate_api_key_not_configured(self, settings: MockSettings) -> None:
        """Test API key auth when not configured."""
        settings.MCP_API_KEY = None
        auth = MCPAuthenticator(settings)
        headers = {"X-API-Key": "some-key"}

        result = await auth.authenticate_request(headers)

        assert result.is_authenticated is False

    @pytest.mark.asyncio
    async def test_authenticate_bearer_valid(self, authenticator: MCPAuthenticator) -> None:
        """Test valid Bearer token authentication."""
        import jwt

        # Create a valid JWT
        user_id = "12345678-1234-5678-1234-567812345678"
        token = jwt.encode(
            {"sub": user_id, "email": "test@example.com"},
            "test-secret-key",
            algorithm="HS256",
        )
        headers = {"Authorization": f"Bearer {token}"}

        result = await authenticator.authenticate_request(headers)

        assert result.is_authenticated is True
        assert result.auth_method == "bearer"
        assert result.user_id == UUID(user_id)
        assert result.username == "test@example.com"

    @pytest.mark.asyncio
    async def test_authenticate_bearer_lowercase_header(self, authenticator: MCPAuthenticator) -> None:
        """Test Bearer token with lowercase header."""
        import jwt

        user_id = "12345678-1234-5678-1234-567812345678"
        token = jwt.encode({"sub": user_id}, "test-secret-key", algorithm="HS256")
        headers = {"authorization": f"Bearer {token}"}

        result = await authenticator.authenticate_request(headers)

        assert result.is_authenticated is True

    @pytest.mark.asyncio
    async def test_authenticate_bearer_invalid_signature(self, authenticator: MCPAuthenticator) -> None:
        """Test Bearer token with invalid signature."""
        import jwt

        token = jwt.encode({"sub": "test"}, "wrong-secret", algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}

        result = await authenticator.authenticate_request(headers)

        assert result.is_authenticated is False

    @pytest.mark.asyncio
    async def test_authenticate_bearer_no_secret_configured(self, settings: MockSettings) -> None:
        """Test Bearer auth when secret key not configured."""
        settings.JWT_SECRET_KEY = None
        auth = MCPAuthenticator(settings)
        headers = {"Authorization": "Bearer some-token"}

        result = await auth.authenticate_request(headers)

        assert result.is_authenticated is False

    @pytest.mark.asyncio
    async def test_authenticate_bearer_malformed_token(self, authenticator: MCPAuthenticator) -> None:
        """Test Bearer token that is malformed."""
        headers = {"Authorization": "Bearer not-a-valid-jwt"}

        result = await authenticator.authenticate_request(headers)

        assert result.is_authenticated is False

    @pytest.mark.asyncio
    async def test_authenticate_bearer_with_permissions_in_token(self, authenticator: MCPAuthenticator) -> None:
        """Test Bearer token with custom permissions."""
        import jwt

        user_id = "12345678-1234-5678-1234-567812345678"
        token = jwt.encode(
            {
                "sub": user_id,
                "permissions": ["rag:admin", "rag:write"],
            },
            "test-secret-key",
            algorithm="HS256",
        )
        headers = {"Authorization": f"Bearer {token}"}

        result = await authenticator.authenticate_request(headers)

        assert result.is_authenticated is True
        assert "rag:admin" in result.permissions
        assert "rag:write" in result.permissions

    @pytest.mark.asyncio
    async def test_authenticate_spiffe_no_socket(self, authenticator: MCPAuthenticator) -> None:
        """Test SPIFFE auth when socket not configured."""
        headers = {"X-SPIFFE-JWT": "some-jwt"}

        result = await authenticator.authenticate_request(headers)

        # Should fall through to next auth method or fail
        assert result.is_authenticated is False

    @pytest.mark.asyncio
    async def test_authenticate_spiffe_valid(self, settings: MockSettings) -> None:
        """Test valid SPIFFE JWT-SVID authentication.

        The MCP auth now delegates to backend.core.spiffe_auth.SPIFFEAuthenticator
        which performs proper JWT validation including trust domain verification.
        """
        import jwt

        from backend.core.spiffe_auth import AgentPrincipal, AgentType

        auth = MCPAuthenticator(settings)

        # Create a SPIFFE JWT with the correct trust domain (rag-modulo.example.com)
        spiffe_jwt = jwt.encode(
            {"sub": "spiffe://rag-modulo.example.com/agent/search-enricher/test123", "aud": ["rag-modulo"]},
            "any-secret",
            algorithm="HS256",
        )
        headers = {"X-SPIFFE-JWT": spiffe_jwt}

        # Mock the global SPIFFE authenticator to return a valid principal
        mock_principal = AgentPrincipal(
            spiffe_id="spiffe://rag-modulo.example.com/agent/search-enricher/test123",
            trust_domain="rag-modulo.example.com",
            agent_type=AgentType.SEARCH_ENRICHER,
            agent_id="test123",
            capabilities=[],
            metadata={"signature_validated": True},
        )

        mock_authenticator = MagicMock()
        mock_authenticator.validate_jwt_svid.return_value = mock_principal

        with patch("backend.core.spiffe_auth.get_spiffe_authenticator", return_value=mock_authenticator):
            result = await auth.authenticate_request(headers)

            assert result.is_authenticated is True
            assert result.auth_method == "spiffe"
            assert result.agent_id == "spiffe://rag-modulo.example.com/agent/search-enricher/test123"
            assert result.metadata.get("trust_domain") == "rag-modulo.example.com"

    @pytest.mark.asyncio
    async def test_authenticate_spiffe_lowercase_header(self, settings: MockSettings) -> None:
        """Test SPIFFE JWT with lowercase header."""
        import jwt

        from backend.core.spiffe_auth import AgentPrincipal, AgentType

        auth = MCPAuthenticator(settings)

        spiffe_jwt = jwt.encode(
            {"sub": "spiffe://rag-modulo.example.com/agent/cot-reasoning/test"},
            "any-secret",
            algorithm="HS256",
        )
        headers = {"x-spiffe-jwt": spiffe_jwt}

        # Mock the global SPIFFE authenticator
        mock_principal = AgentPrincipal(
            spiffe_id="spiffe://rag-modulo.example.com/agent/cot-reasoning/test",
            trust_domain="rag-modulo.example.com",
            agent_type=AgentType.COT_REASONING,
            agent_id="test",
            capabilities=[],
            metadata={},
        )

        mock_authenticator = MagicMock()
        mock_authenticator.validate_jwt_svid.return_value = mock_principal

        with patch("backend.core.spiffe_auth.get_spiffe_authenticator", return_value=mock_authenticator):
            result = await auth.authenticate_request(headers)

            assert result.is_authenticated is True

    @pytest.mark.asyncio
    async def test_authenticate_spiffe_invalid_subject(self, settings: MockSettings) -> None:
        """Test SPIFFE JWT with non-SPIFFE subject."""
        import jwt

        settings.SPIFFE_ENDPOINT_SOCKET = "unix:///run/spire/sockets/agent.sock"
        auth = MCPAuthenticator(settings)

        # JWT without SPIFFE ID in subject
        spiffe_jwt = jwt.encode(
            {"sub": "not-a-spiffe-id"},
            "any-secret",
            algorithm="HS256",
        )
        headers = {"X-SPIFFE-JWT": spiffe_jwt}

        result = await auth.authenticate_request(headers)

        assert result.is_authenticated is False

    @pytest.mark.asyncio
    async def test_authenticate_trusted_user_valid(self, authenticator: MCPAuthenticator) -> None:
        """Test trusted proxy user authentication."""
        mock_user = MagicMock()
        mock_user.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_user.email = "test@example.com"

        # Create mock modules for the local imports
        mock_database = MagicMock()
        mock_db = MagicMock()
        mock_database.get_db.return_value = iter([mock_db])

        mock_user_service_module = MagicMock()
        mock_service = MagicMock()
        mock_service.get_or_create_user_by_fields.return_value = mock_user
        mock_user_service_module.UserService.return_value = mock_service

        with patch.dict(
            sys.modules,
            {
                "backend.rag_solution.repository.database": mock_database,
                "backend.rag_solution.services.user_service": mock_user_service_module,
            },
        ):
            # Reimport to pick up the mocked modules
            headers = {"X-Authenticated-User": "test@example.com"}
            result = await authenticator.authenticate_request(headers)

            assert result.is_authenticated is True
            assert result.auth_method == "trusted_proxy"
            assert result.user_id == mock_user.id
            assert "rag:write" in result.permissions

    @pytest.mark.asyncio
    async def test_authenticate_trusted_user_not_found(self, authenticator: MCPAuthenticator) -> None:
        """Test trusted proxy user when user cannot be created."""
        mock_database = MagicMock()
        mock_db = MagicMock()
        mock_database.get_db.return_value = iter([mock_db])

        mock_user_service_module = MagicMock()
        mock_service = MagicMock()
        mock_service.get_or_create_user_by_fields.return_value = None
        mock_user_service_module.UserService.return_value = mock_service

        with patch.dict(
            sys.modules,
            {
                "backend.rag_solution.repository.database": mock_database,
                "backend.rag_solution.services.user_service": mock_user_service_module,
            },
        ):
            headers = {"X-Authenticated-User": "unknown@example.com"}
            result = await authenticator.authenticate_request(headers)

            assert result.is_authenticated is False

    @pytest.mark.asyncio
    async def test_authenticate_trusted_user_lowercase_header(self, authenticator: MCPAuthenticator) -> None:
        """Test trusted proxy with lowercase header."""
        mock_user = MagicMock()
        mock_user.id = UUID("12345678-1234-5678-1234-567812345678")
        mock_user.email = "test@example.com"

        mock_database = MagicMock()
        mock_db = MagicMock()
        mock_database.get_db.return_value = iter([mock_db])

        mock_user_service_module = MagicMock()
        mock_service = MagicMock()
        mock_service.get_or_create_user_by_fields.return_value = mock_user
        mock_user_service_module.UserService.return_value = mock_service

        with patch.dict(
            sys.modules,
            {
                "backend.rag_solution.repository.database": mock_database,
                "backend.rag_solution.services.user_service": mock_user_service_module,
            },
        ):
            headers = {"x-authenticated-user": "test@example.com"}
            result = await authenticator.authenticate_request(headers)

            assert result.is_authenticated is True

    @pytest.mark.asyncio
    async def test_authenticate_trusted_user_db_error(self, authenticator: MCPAuthenticator) -> None:
        """Test trusted proxy user when database error occurs."""
        mock_database = MagicMock()
        mock_database.get_db.side_effect = Exception("Database connection failed")

        with patch.dict(
            sys.modules,
            {
                "backend.rag_solution.repository.database": mock_database,
            },
        ):
            headers = {"X-Authenticated-User": "test@example.com"}
            result = await authenticator.authenticate_request(headers)

            assert result.is_authenticated is False

    def test_check_permissions_no_required(self, authenticator: MCPAuthenticator) -> None:
        """Test permission check with no required permissions."""
        ctx = MCPAuthContext(permissions=["rag:search"])

        # Should not raise
        authenticator._check_permissions(ctx, [])

    def test_check_permissions_all_present(self, authenticator: MCPAuthenticator) -> None:
        """Test permission check when all required permissions present."""
        ctx = MCPAuthContext(permissions=["rag:search", "rag:read", "rag:write"])

        # Should not raise
        authenticator._check_permissions(ctx, ["rag:search", "rag:read"])

    def test_check_permissions_missing(self, authenticator: MCPAuthenticator) -> None:
        """Test permission check raises when permissions missing."""
        ctx = MCPAuthContext(permissions=["rag:read"])

        with pytest.raises(PermissionError, match="rag:admin"):
            authenticator._check_permissions(ctx, ["rag:read", "rag:admin"])

    @pytest.mark.asyncio
    async def test_auth_priority_spiffe_first(self, settings: MockSettings) -> None:
        """Test that SPIFFE auth is tried before Bearer and API key."""
        import jwt

        from backend.core.spiffe_auth import AgentPrincipal, AgentType

        auth = MCPAuthenticator(settings)

        # Provide both SPIFFE and Bearer tokens
        spiffe_jwt = jwt.encode(
            {"sub": "spiffe://rag-modulo.example.com/agent/test"},
            "any-secret",
            algorithm="HS256",
        )
        bearer_jwt = jwt.encode(
            {"sub": "12345678-1234-5678-1234-567812345678"},
            "test-secret-key",
            algorithm="HS256",
        )

        headers = {
            "X-SPIFFE-JWT": spiffe_jwt,
            "Authorization": f"Bearer {bearer_jwt}",
            "X-API-Key": "test-api-key-12345",  # pragma: allowlist secret
        }

        # Mock the global SPIFFE authenticator to return a valid principal
        mock_principal = AgentPrincipal(
            spiffe_id="spiffe://rag-modulo.example.com/agent/test",
            trust_domain="rag-modulo.example.com",
            agent_type=AgentType.CUSTOM,
            agent_id="test",
            capabilities=[],
            metadata={},
        )

        mock_authenticator = MagicMock()
        mock_authenticator.validate_jwt_svid.return_value = mock_principal

        with patch("backend.core.spiffe_auth.get_spiffe_authenticator", return_value=mock_authenticator):
            result = await auth.authenticate_request(headers)

            # SPIFFE should be used since it's tried first and is valid
            assert result.auth_method == "spiffe"

    @pytest.mark.asyncio
    async def test_auth_fallback_to_bearer(self, authenticator: MCPAuthenticator) -> None:
        """Test fallback to Bearer when SPIFFE fails."""
        import jwt

        bearer_jwt = jwt.encode(
            {"sub": "12345678-1234-5678-1234-567812345678"},
            "test-secret-key",
            algorithm="HS256",
        )

        headers = {
            "X-SPIFFE-JWT": "invalid-jwt",
            "Authorization": f"Bearer {bearer_jwt}",
        }

        result = await authenticator.authenticate_request(headers)

        assert result.auth_method == "bearer"

    @pytest.mark.asyncio
    async def test_auth_fallback_to_api_key(self, authenticator: MCPAuthenticator) -> None:
        """Test fallback to API key when SPIFFE and Bearer fail."""
        headers = {
            "X-SPIFFE-JWT": "invalid-jwt",
            "Authorization": "Bearer invalid-token",
            "X-API-Key": "test-api-key-12345",  # pragma: allowlist secret
        }

        result = await authenticator.authenticate_request(headers)

        assert result.auth_method == "api_key"

    @pytest.mark.asyncio
    async def test_spiffe_auth_uses_global_authenticator(self, settings: MockSettings) -> None:
        """Test that SPIFFE auth uses the global authenticator from spiffe_auth module.

        The MCP auth now delegates to backend.core.spiffe_auth.SPIFFEAuthenticator
        instead of managing its own SPIFFE source.
        """
        import jwt

        auth = MCPAuthenticator(settings)

        spiffe_jwt = jwt.encode(
            {"sub": "spiffe://rag-modulo.example.com/agent/test"},
            "any-secret",
            algorithm="HS256",
        )
        headers = {"X-SPIFFE-JWT": spiffe_jwt}

        # Mock the global authenticator to return None (validation failed)
        mock_authenticator = MagicMock()
        mock_authenticator.validate_jwt_svid.return_value = None

        with patch("backend.core.spiffe_auth.get_spiffe_authenticator", return_value=mock_authenticator):
            result = await auth.authenticate_request(headers)

            # Should call validate_jwt_svid on the global authenticator
            mock_authenticator.validate_jwt_svid.assert_called_once()
            # Since validation returned None, auth should fail
            assert result.is_authenticated is False


class TestMCPAuthContextPermissions:
    """Tests for permission handling in auth context."""

    def test_empty_permissions(self) -> None:
        """Test context with empty permissions list."""
        ctx = MCPAuthContext(permissions=[])
        assert len(ctx.permissions) == 0

    def test_multiple_permissions(self) -> None:
        """Test context with multiple permissions."""
        perms = ["rag:search", "rag:read", "rag:write", "rag:admin"]
        ctx = MCPAuthContext(permissions=perms)
        assert ctx.permissions == perms

    def test_permissions_list_is_mutable(self) -> None:
        """Test that permissions list is mutable."""
        ctx = MCPAuthContext()
        ctx.permissions.append("rag:new")
        assert "rag:new" in ctx.permissions
