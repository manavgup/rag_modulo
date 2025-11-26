"""Unit tests for SPIFFE authentication module.

This module tests the SPIFFE authentication functionality including:
- SPIFFE ID parsing and building
- JWT-SVID detection and validation
- Agent principal creation
- Configuration management
- Capability enforcement decorator

Reference: docs/architecture/spire-integration-architecture.md
"""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from core.spiffe_auth import (
    AGENT_TYPE_CAPABILITIES,
    AgentCapability,
    AgentPrincipal,
    AgentType,
    SPIFFEAuthenticator,
    SPIFFEConfig,
    build_spiffe_id,
    get_agent_principal_from_request,
    is_spiffe_jwt_svid,
    parse_spiffe_id,
    require_capabilities,
)


class TestSPIFFEConfig:
    """Tests for SPIFFEConfig class."""

    def test_from_env_defaults(self) -> None:
        """Test configuration with default values."""
        with patch.dict(os.environ, {}, clear=True):
            config = SPIFFEConfig.from_env()

            assert config.enabled is False  # Default is disabled
            assert config.trust_domain == "rag-modulo.example.com"
            assert config.endpoint_socket == "unix:///var/run/spire/agent.sock"
            assert config.default_audiences == ["rag-modulo", "mcp-gateway"]
            assert config.svid_ttl_seconds == 3600
            assert config.fallback_to_jwt is True

    def test_from_env_custom_values(self) -> None:
        """Test configuration with custom environment values."""
        custom_env = {
            "SPIFFE_ENABLED": "true",
            "SPIFFE_TRUST_DOMAIN": "custom.domain.com",
            "SPIFFE_ENDPOINT_SOCKET": "unix:///custom/socket.sock",
            "SPIFFE_JWT_AUDIENCES": "api1,api2,api3",
            "SPIFFE_SVID_TTL_SECONDS": "7200",
            "SPIFFE_FALLBACK_TO_JWT": "false",
        }
        with patch.dict(os.environ, custom_env, clear=True):
            config = SPIFFEConfig.from_env()

            assert config.enabled is True
            assert config.trust_domain == "custom.domain.com"
            assert config.endpoint_socket == "unix:///custom/socket.sock"
            assert config.default_audiences == ["api1", "api2", "api3"]
            assert config.svid_ttl_seconds == 7200
            assert config.fallback_to_jwt is False

    def test_from_env_enabled_variations(self) -> None:
        """Test different values for SPIFFE_ENABLED."""
        # True values
        for value in ["true", "True", "TRUE"]:
            with patch.dict(os.environ, {"SPIFFE_ENABLED": value}, clear=True):
                config = SPIFFEConfig.from_env()
                assert config.enabled is True, f"Expected True for '{value}'"

        # False values (including default)
        for value in ["false", "False", "FALSE", "0", "no", ""]:
            with patch.dict(os.environ, {"SPIFFE_ENABLED": value}, clear=True):
                config = SPIFFEConfig.from_env()
                assert config.enabled is False, f"Expected False for '{value}'"


class TestAgentType:
    """Tests for AgentType enum."""

    def test_agent_types(self) -> None:
        """Test all defined agent types."""
        assert AgentType.SEARCH_ENRICHER.value == "search-enricher"
        assert AgentType.COT_REASONING.value == "cot-reasoning"
        assert AgentType.QUESTION_DECOMPOSER.value == "question-decomposer"
        assert AgentType.SOURCE_ATTRIBUTION.value == "source-attribution"
        assert AgentType.ENTITY_EXTRACTION.value == "entity-extraction"
        assert AgentType.ANSWER_SYNTHESIS.value == "answer-synthesis"
        assert AgentType.CUSTOM.value == "custom"

    def test_agent_type_from_string(self) -> None:
        """Test creating agent type from string value."""
        assert AgentType("search-enricher") == AgentType.SEARCH_ENRICHER
        assert AgentType("cot-reasoning") == AgentType.COT_REASONING


class TestAgentCapability:
    """Tests for AgentCapability enum."""

    def test_capabilities(self) -> None:
        """Test all defined capabilities."""
        assert AgentCapability.MCP_TOOL_INVOKE.value == "mcp:tool:invoke"
        assert AgentCapability.SEARCH_READ.value == "search:read"
        assert AgentCapability.SEARCH_WRITE.value == "search:write"
        assert AgentCapability.LLM_INVOKE.value == "llm:invoke"
        assert AgentCapability.PIPELINE_EXECUTE.value == "pipeline:execute"
        assert AgentCapability.DOCUMENT_READ.value == "document:read"
        assert AgentCapability.DOCUMENT_WRITE.value == "document:write"
        assert AgentCapability.COT_INVOKE.value == "cot:invoke"
        assert AgentCapability.AGENT_SPAWN.value == "agent:spawn"
        assert AgentCapability.ADMIN.value == "admin"


class TestAgentPrincipal:
    """Tests for AgentPrincipal class."""

    def test_create_agent_principal(self) -> None:
        """Test creating an agent principal directly."""
        principal = AgentPrincipal(
            spiffe_id="spiffe://rag-modulo.example.com/agent/search-enricher/agent-001",
            trust_domain="rag-modulo.example.com",
            agent_type=AgentType.SEARCH_ENRICHER,
            agent_id="agent-001",
            capabilities=[AgentCapability.SEARCH_READ, AgentCapability.LLM_INVOKE],
            audiences=["backend-api"],
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

        assert principal.spiffe_id == "spiffe://rag-modulo.example.com/agent/search-enricher/agent-001"
        assert principal.trust_domain == "rag-modulo.example.com"
        assert principal.agent_type == AgentType.SEARCH_ENRICHER
        assert principal.agent_id == "agent-001"
        assert len(principal.capabilities) == 2
        assert AgentCapability.SEARCH_READ in principal.capabilities

    def test_from_spiffe_id(self) -> None:
        """Test creating an agent principal from SPIFFE ID."""
        spiffe_id = "spiffe://rag-modulo.example.com/agent/search-enricher/agent-001"
        principal = AgentPrincipal.from_spiffe_id(spiffe_id)

        assert principal.spiffe_id == spiffe_id
        assert principal.trust_domain == "rag-modulo.example.com"
        assert principal.agent_type == AgentType.SEARCH_ENRICHER
        assert principal.agent_id == "agent-001"
        # Default capabilities for search-enricher
        assert AgentCapability.MCP_TOOL_INVOKE in principal.capabilities
        assert AgentCapability.SEARCH_READ in principal.capabilities

    def test_from_spiffe_id_custom_capabilities(self) -> None:
        """Test creating an agent principal with custom capabilities."""
        spiffe_id = "spiffe://rag-modulo.example.com/agent/cot-reasoning/cot-001"
        custom_caps = [AgentCapability.ADMIN, AgentCapability.SEARCH_WRITE]

        principal = AgentPrincipal.from_spiffe_id(spiffe_id, capabilities=custom_caps)

        assert principal.agent_type == AgentType.COT_REASONING
        assert principal.capabilities == custom_caps

    def test_from_spiffe_id_invalid(self) -> None:
        """Test creating an agent principal from invalid SPIFFE ID."""
        invalid_ids = [
            "not-a-spiffe-id",
            "http://example.com/agent/type/id",
            "spiffe://domain/not-agent/type",  # Missing 'agent' prefix
        ]

        for invalid_id in invalid_ids:
            with pytest.raises(ValueError):
                AgentPrincipal.from_spiffe_id(invalid_id)

    def test_is_expired_false(self) -> None:
        """Test is_expired returns False for valid principal."""
        principal = AgentPrincipal(
            spiffe_id="spiffe://domain/agent/custom/id",
            trust_domain="domain",
            agent_type=AgentType.CUSTOM,
            agent_id="id",
            capabilities=[],
            audiences=[],
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

        assert principal.is_expired() is False

    def test_is_expired_true(self) -> None:
        """Test is_expired returns True for expired principal."""
        principal = AgentPrincipal(
            spiffe_id="spiffe://domain/agent/custom/id",
            trust_domain="domain",
            agent_type=AgentType.CUSTOM,
            agent_id="id",
            capabilities=[],
            audiences=[],
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )

        assert principal.is_expired() is True

    def test_is_expired_none(self) -> None:
        """Test is_expired returns False when no expiration set."""
        principal = AgentPrincipal(
            spiffe_id="spiffe://domain/agent/custom/id",
            trust_domain="domain",
            agent_type=AgentType.CUSTOM,
            agent_id="id",
            capabilities=[],
            audiences=[],
            expires_at=None,
        )

        assert principal.is_expired() is False

    def test_has_capability(self) -> None:
        """Test has_capability method."""
        principal = AgentPrincipal(
            spiffe_id="spiffe://domain/agent/search-enricher/id",
            trust_domain="domain",
            agent_type=AgentType.SEARCH_ENRICHER,
            agent_id="id",
            capabilities=[AgentCapability.SEARCH_READ, AgentCapability.LLM_INVOKE],
            audiences=[],
            expires_at=None,
        )

        assert principal.has_capability(AgentCapability.SEARCH_READ) is True
        assert principal.has_capability(AgentCapability.LLM_INVOKE) is True
        assert principal.has_capability(AgentCapability.ADMIN) is False

    def test_has_any_capability(self) -> None:
        """Test has_any_capability method."""
        principal = AgentPrincipal(
            spiffe_id="spiffe://domain/agent/search-enricher/id",
            trust_domain="domain",
            agent_type=AgentType.SEARCH_ENRICHER,
            agent_id="id",
            capabilities=[AgentCapability.SEARCH_READ],
            audiences=[],
            expires_at=None,
        )

        assert principal.has_any_capability([AgentCapability.SEARCH_READ, AgentCapability.ADMIN]) is True
        assert principal.has_any_capability([AgentCapability.ADMIN, AgentCapability.COT_INVOKE]) is False

    def test_has_all_capabilities(self) -> None:
        """Test has_all_capabilities method."""
        principal = AgentPrincipal(
            spiffe_id="spiffe://domain/agent/search-enricher/id",
            trust_domain="domain",
            agent_type=AgentType.SEARCH_ENRICHER,
            agent_id="id",
            capabilities=[AgentCapability.SEARCH_READ, AgentCapability.LLM_INVOKE],
            audiences=[],
            expires_at=None,
        )

        assert principal.has_all_capabilities([AgentCapability.SEARCH_READ]) is True
        assert principal.has_all_capabilities([AgentCapability.SEARCH_READ, AgentCapability.LLM_INVOKE]) is True
        assert principal.has_all_capabilities([AgentCapability.SEARCH_READ, AgentCapability.ADMIN]) is False

    def test_is_valid_for_audience(self) -> None:
        """Test is_valid_for_audience method."""
        principal = AgentPrincipal(
            spiffe_id="spiffe://domain/agent/search-enricher/id",
            trust_domain="domain",
            agent_type=AgentType.SEARCH_ENRICHER,
            agent_id="id",
            capabilities=[],
            audiences=["backend-api", "mcp-gateway"],
            expires_at=None,
        )

        assert principal.is_valid_for_audience("backend-api") is True
        assert principal.is_valid_for_audience("mcp-gateway") is True
        assert principal.is_valid_for_audience("unknown-api") is False


class TestSPIFFEIDParsing:
    """Tests for SPIFFE ID parsing functions."""

    def test_parse_spiffe_id_agent(self) -> None:
        """Test parsing a valid agent SPIFFE ID."""
        spiffe_id = "spiffe://rag-modulo.example.com/agent/search-enricher/agent-001"
        result = parse_spiffe_id(spiffe_id)

        assert result is not None
        trust_domain, path = result
        assert trust_domain == "rag-modulo.example.com"
        assert path == "agent/search-enricher/agent-001"

    def test_parse_spiffe_id_workload(self) -> None:
        """Test parsing a workload SPIFFE ID."""
        spiffe_id = "spiffe://rag-modulo.example.com/workload/backend-api"
        result = parse_spiffe_id(spiffe_id)

        assert result is not None
        trust_domain, path = result
        assert trust_domain == "rag-modulo.example.com"
        assert path == "workload/backend-api"

    def test_parse_spiffe_id_invalid(self) -> None:
        """Test parsing invalid SPIFFE IDs."""
        invalid_ids = [
            "not-a-spiffe-id",
            "http://example.com/agent/type/id",
            "spiffe://",
            "",
        ]

        for invalid_id in invalid_ids:
            result = parse_spiffe_id(invalid_id)
            assert result is None, f"Expected None for {invalid_id}"

    def test_build_spiffe_id(self) -> None:
        """Test building a SPIFFE ID."""
        spiffe_id = build_spiffe_id(
            trust_domain="rag-modulo.example.com",
            agent_type=AgentType.SEARCH_ENRICHER,
            agent_id="agent-001",
        )

        assert spiffe_id == "spiffe://rag-modulo.example.com/agent/search-enricher/agent-001"

    def test_build_spiffe_id_without_agent_id(self) -> None:
        """Test building a SPIFFE ID without agent ID."""
        spiffe_id = build_spiffe_id(
            trust_domain="rag-modulo.example.com",
            agent_type=AgentType.SEARCH_ENRICHER,
        )

        assert spiffe_id == "spiffe://rag-modulo.example.com/agent/search-enricher"

    def test_build_spiffe_id_custom_type(self) -> None:
        """Test building a SPIFFE ID with custom agent type."""
        spiffe_id = build_spiffe_id(
            trust_domain="custom.domain",
            agent_type=AgentType.COT_REASONING,
            agent_id="cot-agent-123",
        )

        assert spiffe_id == "spiffe://custom.domain/agent/cot-reasoning/cot-agent-123"


class TestIsSPIFFEJWTSVID:
    """Tests for is_spiffe_jwt_svid function."""

    def test_valid_spiffe_jwt(self) -> None:
        """Test detecting a valid SPIFFE JWT-SVID."""
        # Create a mock JWT with SPIFFE claims
        # In reality, this would be a properly signed JWT
        # For testing, we just check the structure detection
        with patch("core.spiffe_auth.jwt.decode") as mock_decode:
            mock_decode.return_value = {
                "sub": "spiffe://rag-modulo.example.com/agent/search-enricher/agent-001",
                "aud": ["backend-api"],
                "exp": 1234567890,
            }

            result = is_spiffe_jwt_svid("mock.jwt.token")
            assert result is True

    def test_non_spiffe_jwt(self) -> None:
        """Test detecting a non-SPIFFE JWT."""
        with patch("core.spiffe_auth.jwt.decode") as mock_decode:
            mock_decode.return_value = {
                "sub": "user@example.com",
                "aud": ["backend-api"],
                "exp": 1234567890,
            }

            result = is_spiffe_jwt_svid("mock.jwt.token")
            assert result is False

    def test_invalid_jwt(self) -> None:
        """Test handling invalid JWT."""
        with patch("core.spiffe_auth.jwt.decode") as mock_decode:
            mock_decode.side_effect = Exception("Invalid token")

            result = is_spiffe_jwt_svid("invalid.token")
            assert result is False

    def test_empty_token(self) -> None:
        """Test handling empty token."""
        result = is_spiffe_jwt_svid("")
        assert result is False

    def test_mock_token_detection(self) -> None:
        """Test that mock tokens are not detected as SPIFFE."""
        result = is_spiffe_jwt_svid("mock-jwt-token")
        assert result is False


class TestSPIFFEAuthenticator:
    """Tests for SPIFFEAuthenticator class."""

    def test_authenticator_disabled(self) -> None:
        """Test authenticator when SPIFFE is disabled."""
        config = SPIFFEConfig(
            enabled=False,
            trust_domain="test.domain",
            endpoint_socket="/tmp/socket",
            default_audiences=["api"],
        )

        authenticator = SPIFFEAuthenticator(config)
        # When disabled, validation should return None for non-SPIFFE tokens
        result = authenticator.validate_jwt_svid("any.token.here")

        assert result is None

    def test_authenticator_validates_trust_domain(self) -> None:
        """Test that authenticator validates trust domain."""
        config = SPIFFEConfig(
            enabled=True,
            trust_domain="expected.domain",
            endpoint_socket="/tmp/socket",
            default_audiences=["api"],
            fallback_to_jwt=True,  # Allow fallback for testing without SPIRE
        )

        authenticator = SPIFFEAuthenticator(config)

        with patch("core.spiffe_auth.jwt.decode") as mock_decode:
            mock_decode.return_value = {
                "sub": "spiffe://wrong.domain/agent/type/id",
                "aud": ["api"],
                "exp": (datetime.now(UTC) + timedelta(hours=1)).timestamp(),
            }

            result = authenticator.validate_jwt_svid("mock.token")
            # Should reject due to trust domain mismatch
            assert result is None

    def test_authenticator_validates_audience(self) -> None:
        """Test that authenticator validates audience."""
        config = SPIFFEConfig(
            enabled=True,
            trust_domain="test.domain",
            endpoint_socket="/tmp/socket",
            default_audiences=["expected-audience"],
            fallback_to_jwt=True,
        )

        authenticator = SPIFFEAuthenticator(config)

        with patch("core.spiffe_auth.jwt.decode") as mock_decode:
            mock_decode.return_value = {
                "sub": "spiffe://test.domain/agent/search-enricher/id",
                "aud": ["wrong-audience"],
                "exp": (datetime.now(UTC) + timedelta(hours=1)).timestamp(),
            }

            result = authenticator.validate_jwt_svid("mock.token", required_audience="expected-audience")
            # Should reject due to audience mismatch
            assert result is None

    def test_authenticator_creates_principal_with_fallback(self) -> None:
        """Test that authenticator creates valid principal from JWT when using fallback."""
        config = SPIFFEConfig(
            enabled=True,
            trust_domain="rag-modulo.example.com",
            endpoint_socket="/tmp/socket",
            default_audiences=["backend-api"],
            fallback_to_jwt=True,  # Allow fallback when SPIRE unavailable
        )

        authenticator = SPIFFEAuthenticator(config)
        exp_time = datetime.now(UTC) + timedelta(hours=1)
        iat_time = datetime.now(UTC)

        with patch("core.spiffe_auth.jwt.decode") as mock_decode:
            mock_decode.return_value = {
                "sub": "spiffe://rag-modulo.example.com/agent/search-enricher/agent-001",
                "aud": ["backend-api"],
                "iat": iat_time.timestamp(),
                "exp": exp_time.timestamp(),
            }

            result = authenticator.validate_jwt_svid("mock.token")

            assert result is not None
            assert result.spiffe_id == "spiffe://rag-modulo.example.com/agent/search-enricher/agent-001"
            assert result.trust_domain == "rag-modulo.example.com"
            assert result.agent_type == AgentType.SEARCH_ENRICHER
            assert result.agent_id == "agent-001"
            # Should have default capabilities for search-enricher
            assert AgentCapability.MCP_TOOL_INVOKE in result.capabilities
            assert AgentCapability.SEARCH_READ in result.capabilities

    def test_authenticator_handles_expired_token(self) -> None:
        """Test that authenticator rejects expired tokens."""
        config = SPIFFEConfig(
            enabled=True,
            trust_domain="test.domain",
            endpoint_socket="/tmp/socket",
            default_audiences=["api"],
            fallback_to_jwt=True,
        )

        authenticator = SPIFFEAuthenticator(config)

        with patch("core.spiffe_auth.jwt.decode") as mock_decode:
            mock_decode.return_value = {
                "sub": "spiffe://test.domain/agent/search-enricher/id",
                "aud": ["api"],
                "exp": (datetime.now(UTC) - timedelta(hours=1)).timestamp(),
            }

            result = authenticator.validate_jwt_svid("mock.token")
            assert result is None

    def test_authenticator_rejects_non_spiffe_token(self) -> None:
        """Test that authenticator rejects non-SPIFFE tokens."""
        config = SPIFFEConfig(
            enabled=True,
            trust_domain="test.domain",
            endpoint_socket="/tmp/socket",
            default_audiences=["api"],
            fallback_to_jwt=True,
        )

        authenticator = SPIFFEAuthenticator(config)

        with patch("core.spiffe_auth.jwt.decode") as mock_decode:
            # Token without spiffe:// prefix in sub
            mock_decode.return_value = {
                "sub": "user@example.com",
                "aud": ["api"],
                "exp": (datetime.now(UTC) + timedelta(hours=1)).timestamp(),
            }

            result = authenticator.validate_jwt_svid("mock.token")
            assert result is None

    def test_authenticator_is_available_false_when_disabled(self) -> None:
        """Test is_available returns False when SPIFFE is disabled."""
        config = SPIFFEConfig(enabled=False)
        authenticator = SPIFFEAuthenticator(config)

        assert authenticator.is_available is False

    def test_authenticator_get_auth_headers_empty_when_unavailable(self) -> None:
        """Test get_auth_headers returns empty dict when SPIFFE unavailable."""
        config = SPIFFEConfig(enabled=False)
        authenticator = SPIFFEAuthenticator(config)

        headers = authenticator.get_auth_headers()
        assert headers == {}


class TestRequireCapabilitiesDecorator:
    """Tests for require_capabilities decorator."""

    @pytest.mark.asyncio
    async def test_require_capabilities_allows_user_requests(self) -> None:
        """Test that user requests are allowed regardless of capabilities."""
        from fastapi import Request

        # Create a mock request with user state
        mock_request = MagicMock(spec=Request)
        mock_request.state.agent_principal = None
        mock_request.state.user = {"uuid": "user-123", "identity_type": "user"}

        @require_capabilities(AgentCapability.ADMIN)
        async def protected_endpoint(request: Request) -> str:
            return "success"

        result = await protected_endpoint(request=mock_request)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_require_capabilities_allows_agent_with_capability(self) -> None:
        """Test that agents with required capability are allowed."""
        from fastapi import Request

        principal = AgentPrincipal(
            spiffe_id="spiffe://domain/agent/search-enricher/id",
            trust_domain="domain",
            agent_type=AgentType.SEARCH_ENRICHER,
            agent_id="id",
            capabilities=[AgentCapability.SEARCH_READ],
            audiences=[],
        )

        mock_request = MagicMock(spec=Request)
        mock_request.state.agent_principal = principal
        mock_request.state.user = None

        @require_capabilities(AgentCapability.SEARCH_READ)
        async def protected_endpoint(request: Request) -> str:
            return "success"

        result = await protected_endpoint(request=mock_request)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_require_capabilities_denies_agent_without_capability(self) -> None:
        """Test that agents without required capability are denied."""
        from fastapi import HTTPException, Request

        principal = AgentPrincipal(
            spiffe_id="spiffe://domain/agent/search-enricher/id",
            trust_domain="domain",
            agent_type=AgentType.SEARCH_ENRICHER,
            agent_id="id",
            capabilities=[AgentCapability.SEARCH_READ],  # Only has SEARCH_READ
            audiences=[],
        )

        mock_request = MagicMock(spec=Request)
        mock_request.state.agent_principal = principal
        mock_request.state.user = None

        @require_capabilities(AgentCapability.ADMIN)  # Requires ADMIN
        async def protected_endpoint(request: Request) -> str:
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await protected_endpoint(request=mock_request)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_capabilities_require_all(self) -> None:
        """Test require_all parameter."""
        from fastapi import HTTPException, Request

        principal = AgentPrincipal(
            spiffe_id="spiffe://domain/agent/search-enricher/id",
            trust_domain="domain",
            agent_type=AgentType.SEARCH_ENRICHER,
            agent_id="id",
            capabilities=[AgentCapability.SEARCH_READ, AgentCapability.LLM_INVOKE],
            audiences=[],
        )

        mock_request = MagicMock(spec=Request)
        mock_request.state.agent_principal = principal
        mock_request.state.user = None

        # Test with require_all=True (default) - should pass when agent has all
        @require_capabilities(AgentCapability.SEARCH_READ, AgentCapability.LLM_INVOKE, require_all=True)
        async def endpoint_all(request: Request) -> str:
            return "success"

        result = await endpoint_all(request=mock_request)
        assert result == "success"

        # Test with require_all=True but agent missing one capability
        @require_capabilities(AgentCapability.SEARCH_READ, AgentCapability.ADMIN, require_all=True)
        async def endpoint_missing(request: Request) -> str:
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await endpoint_missing(request=mock_request)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_capabilities_require_any(self) -> None:
        """Test require_all=False (require any)."""
        from fastapi import Request

        principal = AgentPrincipal(
            spiffe_id="spiffe://domain/agent/search-enricher/id",
            trust_domain="domain",
            agent_type=AgentType.SEARCH_ENRICHER,
            agent_id="id",
            capabilities=[AgentCapability.SEARCH_READ],  # Only has one
            audiences=[],
        )

        mock_request = MagicMock(spec=Request)
        mock_request.state.agent_principal = principal
        mock_request.state.user = None

        # Should pass when agent has any of the required capabilities
        @require_capabilities(AgentCapability.SEARCH_READ, AgentCapability.ADMIN, require_all=False)
        async def endpoint_any(request: Request) -> str:
            return "success"

        result = await endpoint_any(request=mock_request)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_require_capabilities_unauthenticated(self) -> None:
        """Test that unauthenticated requests are denied."""
        from fastapi import HTTPException, Request

        mock_request = MagicMock(spec=Request)
        mock_request.state.agent_principal = None
        mock_request.state.user = None

        @require_capabilities(AgentCapability.SEARCH_READ)
        async def protected_endpoint(request: Request) -> str:
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            await protected_endpoint(request=mock_request)

        assert exc_info.value.status_code == 401


class TestGetAgentPrincipalFromRequest:
    """Tests for get_agent_principal_from_request utility."""

    def test_returns_principal_when_present(self) -> None:
        """Test returns agent principal when present in request."""
        principal = AgentPrincipal(
            spiffe_id="spiffe://domain/agent/search-enricher/id",
            trust_domain="domain",
            agent_type=AgentType.SEARCH_ENRICHER,
            agent_id="id",
            capabilities=[],
            audiences=[],
        )

        mock_request = MagicMock()
        mock_request.state.agent_principal = principal

        result = get_agent_principal_from_request(mock_request)
        assert result == principal

    def test_returns_none_when_not_present(self) -> None:
        """Test returns None when no agent principal in request."""
        mock_request = MagicMock()
        mock_request.state = MagicMock(spec=[])  # Empty spec, no agent_principal

        result = get_agent_principal_from_request(mock_request)
        assert result is None


class TestAgentTypeCapabilities:
    """Tests for default agent type capabilities mapping."""

    def test_search_enricher_default_capabilities(self) -> None:
        """Test default capabilities for search-enricher agent."""
        caps = AGENT_TYPE_CAPABILITIES[AgentType.SEARCH_ENRICHER]
        assert AgentCapability.MCP_TOOL_INVOKE in caps
        assert AgentCapability.SEARCH_READ in caps
        assert AgentCapability.ADMIN not in caps

    def test_cot_reasoning_default_capabilities(self) -> None:
        """Test default capabilities for cot-reasoning agent."""
        caps = AGENT_TYPE_CAPABILITIES[AgentType.COT_REASONING]
        assert AgentCapability.SEARCH_READ in caps
        assert AgentCapability.LLM_INVOKE in caps
        assert AgentCapability.PIPELINE_EXECUTE in caps
        assert AgentCapability.COT_INVOKE in caps

    def test_custom_agent_no_default_capabilities(self) -> None:
        """Test custom agents have no default capabilities."""
        caps = AGENT_TYPE_CAPABILITIES[AgentType.CUSTOM]
        assert caps == []
