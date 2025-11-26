"""Unit tests for SPIFFE authentication module.

This module tests the SPIFFE authentication functionality including:
- SPIFFE ID parsing and building
- JWT-SVID detection and validation
- Agent principal creation
- Configuration management

Reference: docs/architecture/spire-integration-architecture.md
"""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from core.spiffe_auth import (
    AgentCapability,
    AgentPrincipal,
    AgentType,
    SPIFFEAuthenticator,
    SPIFFEConfig,
    build_spiffe_id,
    is_spiffe_jwt_svid,
    parse_spiffe_id,
)


class TestSPIFFEConfig:
    """Tests for SPIFFEConfig class."""

    def test_from_env_defaults(self) -> None:
        """Test configuration with default values."""
        with patch.dict(os.environ, {}, clear=True):
            config = SPIFFEConfig.from_env()

            assert config.trust_domain == "rag-modulo.example.com"
            assert config.agent_socket_path == "/run/spire/sockets/agent.sock"
            assert config.audiences == ["backend-api", "mcp-gateway"]
            assert config.enabled is True

    def test_from_env_custom_values(self) -> None:
        """Test configuration with custom environment values."""
        custom_env = {
            "SPIFFE_TRUST_DOMAIN": "custom.domain.com",
            "SPIFFE_AGENT_SOCKET": "/custom/socket.sock",
            "SPIFFE_AUDIENCES": "api1,api2,api3",
            "SPIFFE_ENABLED": "false",
        }
        with patch.dict(os.environ, custom_env, clear=True):
            config = SPIFFEConfig.from_env()

            assert config.trust_domain == "custom.domain.com"
            assert config.agent_socket_path == "/custom/socket.sock"
            assert config.audiences == ["api1", "api2", "api3"]
            assert config.enabled is False

    def test_from_env_enabled_variations(self) -> None:
        """Test different values for SPIFFE_ENABLED."""
        for value, expected in [("true", True), ("TRUE", True), ("1", True), ("false", False), ("0", False)]:
            with patch.dict(os.environ, {"SPIFFE_ENABLED": value}, clear=True):
                config = SPIFFEConfig.from_env()
                assert config.enabled is expected, f"Expected {expected} for {value}"


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
        """Test creating an agent principal."""
        principal = AgentPrincipal(
            spiffe_id="spiffe://rag-modulo.example.com/agent/search-enricher/agent-001",
            agent_type=AgentType.SEARCH_ENRICHER,
            agent_id="agent-001",
            capabilities=[AgentCapability.SEARCH_READ, AgentCapability.LLM_INVOKE],
            audiences=["backend-api"],
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

        assert principal.spiffe_id == "spiffe://rag-modulo.example.com/agent/search-enricher/agent-001"
        assert principal.agent_type == AgentType.SEARCH_ENRICHER
        assert principal.agent_id == "agent-001"
        assert len(principal.capabilities) == 2
        assert AgentCapability.SEARCH_READ in principal.capabilities

    def test_is_expired_false(self) -> None:
        """Test is_expired returns False for valid principal."""
        principal = AgentPrincipal(
            spiffe_id="spiffe://domain/agent/type/id",
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
            spiffe_id="spiffe://domain/agent/type/id",
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
            spiffe_id="spiffe://domain/agent/type/id",
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
            spiffe_id="spiffe://domain/agent/type/id",
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
            spiffe_id="spiffe://domain/agent/type/id",
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
            spiffe_id="spiffe://domain/agent/type/id",
            agent_type=AgentType.SEARCH_ENRICHER,
            agent_id="id",
            capabilities=[AgentCapability.SEARCH_READ, AgentCapability.LLM_INVOKE],
            audiences=[],
            expires_at=None,
        )

        assert principal.has_all_capabilities([AgentCapability.SEARCH_READ]) is True
        assert principal.has_all_capabilities([AgentCapability.SEARCH_READ, AgentCapability.LLM_INVOKE]) is True
        assert principal.has_all_capabilities([AgentCapability.SEARCH_READ, AgentCapability.ADMIN]) is False


class TestSPIFFEIDParsing:
    """Tests for SPIFFE ID parsing functions."""

    def test_parse_spiffe_id_agent(self) -> None:
        """Test parsing a valid agent SPIFFE ID."""
        spiffe_id = "spiffe://rag-modulo.example.com/agent/search-enricher/agent-001"
        result = parse_spiffe_id(spiffe_id)

        assert result is not None
        assert result["trust_domain"] == "rag-modulo.example.com"
        assert result["path"] == "/agent/search-enricher/agent-001"
        assert result["agent_type"] == "search-enricher"
        assert result["agent_id"] == "agent-001"

    def test_parse_spiffe_id_workload(self) -> None:
        """Test parsing a workload SPIFFE ID."""
        spiffe_id = "spiffe://rag-modulo.example.com/workload/backend-api"
        result = parse_spiffe_id(spiffe_id)

        assert result is not None
        assert result["trust_domain"] == "rag-modulo.example.com"
        assert result["path"] == "/workload/backend-api"
        assert result["agent_type"] is None
        assert result["agent_id"] is None

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
            trust_domain="test.domain",
            agent_socket_path="/tmp/socket",
            audiences=["api"],
            enabled=False,
        )

        authenticator = SPIFFEAuthenticator(config)
        result = authenticator.validate_jwt_svid("any.token.here")

        assert result is None

    def test_authenticator_validates_trust_domain(self) -> None:
        """Test that authenticator validates trust domain."""
        config = SPIFFEConfig(
            trust_domain="expected.domain",
            agent_socket_path="/tmp/socket",
            audiences=["api"],
            enabled=True,
        )

        authenticator = SPIFFEAuthenticator(config)

        with patch("core.spiffe_auth.jwt.decode") as mock_decode:
            mock_decode.return_value = {
                "sub": "spiffe://wrong.domain/agent/type/id",
                "aud": ["api"],
                "exp": (datetime.now(UTC) + timedelta(hours=1)).timestamp(),
            }

            result = authenticator.validate_jwt_svid("mock.token")
            assert result is None

    def test_authenticator_validates_audience(self) -> None:
        """Test that authenticator validates audience."""
        config = SPIFFEConfig(
            trust_domain="test.domain",
            agent_socket_path="/tmp/socket",
            audiences=["expected-audience"],
            enabled=True,
        )

        authenticator = SPIFFEAuthenticator(config)

        with patch("core.spiffe_auth.jwt.decode") as mock_decode:
            mock_decode.return_value = {
                "sub": "spiffe://test.domain/agent/search-enricher/id",
                "aud": ["wrong-audience"],
                "exp": (datetime.now(UTC) + timedelta(hours=1)).timestamp(),
            }

            result = authenticator.validate_jwt_svid("mock.token", required_audience="expected-audience")
            assert result is None

    def test_authenticator_creates_principal(self) -> None:
        """Test that authenticator creates valid principal from JWT."""
        config = SPIFFEConfig(
            trust_domain="rag-modulo.example.com",
            agent_socket_path="/tmp/socket",
            audiences=["backend-api"],
            enabled=True,
        )

        authenticator = SPIFFEAuthenticator(config)
        exp_time = datetime.now(UTC) + timedelta(hours=1)

        with patch("core.spiffe_auth.jwt.decode") as mock_decode:
            mock_decode.return_value = {
                "sub": "spiffe://rag-modulo.example.com/agent/search-enricher/agent-001",
                "aud": ["backend-api"],
                "exp": exp_time.timestamp(),
                "capabilities": ["search:read", "llm:invoke"],
            }

            result = authenticator.validate_jwt_svid("mock.token")

            assert result is not None
            assert result.spiffe_id == "spiffe://rag-modulo.example.com/agent/search-enricher/agent-001"
            assert result.agent_type == AgentType.SEARCH_ENRICHER
            assert result.agent_id == "agent-001"
            assert AgentCapability.SEARCH_READ in result.capabilities
            assert AgentCapability.LLM_INVOKE in result.capabilities

    def test_authenticator_handles_expired_token(self) -> None:
        """Test that authenticator rejects expired tokens."""
        config = SPIFFEConfig(
            trust_domain="test.domain",
            agent_socket_path="/tmp/socket",
            audiences=["api"],
            enabled=True,
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
