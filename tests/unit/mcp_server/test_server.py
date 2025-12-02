"""Unit tests for MCP server module.

Tests for server creation, lifespan management, and transport handling.
"""

import sys
from dataclasses import dataclass
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from backend.mcp_server.server import (
    MCPServerContext,
    _validate_auth_configuration,
    create_mcp_server,
    get_app_context,
    parse_uuid,
)


@dataclass
class MockSettings:
    """Mock settings for testing."""

    SPIFFE_ENDPOINT_SOCKET: str | None = None
    JWT_SECRET_KEY: str | None = "test-secret-key"
    MCP_API_KEY: str | None = "valid-api-key-12345"


class TestParseUuid:
    """Tests for parse_uuid utility function."""

    def test_parse_valid_uuid(self) -> None:
        """Test parsing a valid UUID string."""
        uuid_str = "12345678-1234-5678-1234-567812345678"
        result = parse_uuid(uuid_str, "test_field")
        assert result == UUID(uuid_str)

    def test_parse_uuid_without_dashes(self) -> None:
        """Test parsing UUID without dashes."""
        uuid_str = "12345678123456781234567812345678"
        result = parse_uuid(uuid_str, "test_field")
        assert result == UUID(uuid_str)

    def test_parse_invalid_uuid(self) -> None:
        """Test parsing invalid UUID raises ValueError."""
        with pytest.raises(ValueError, match="test_field"):
            parse_uuid("not-a-uuid", "test_field")

    def test_parse_empty_uuid(self) -> None:
        """Test parsing empty string raises ValueError."""
        with pytest.raises(ValueError, match="test_field"):
            parse_uuid("", "test_field")

    def test_parse_uuid_with_custom_field_name(self) -> None:
        """Test error message contains custom field name."""
        with pytest.raises(ValueError, match="collection_id"):
            parse_uuid("invalid", "collection_id")


class TestMCPServerContext:
    """Tests for MCPServerContext dataclass."""

    def test_context_creation(self) -> None:
        """Test creating MCPServerContext with all fields."""
        mock_db = MagicMock()
        mock_search = MagicMock()
        mock_collection = MagicMock()
        mock_podcast = MagicMock()
        mock_question = MagicMock()
        mock_file = MagicMock()
        mock_auth = MagicMock()
        mock_settings = MockSettings()

        ctx = MCPServerContext(
            db_session=mock_db,
            search_service=mock_search,
            collection_service=mock_collection,
            podcast_service=mock_podcast,
            question_service=mock_question,
            file_service=mock_file,
            authenticator=mock_auth,
            settings=mock_settings,
        )

        assert ctx.db_session == mock_db
        assert ctx.search_service == mock_search
        assert ctx.collection_service == mock_collection
        assert ctx.podcast_service == mock_podcast
        assert ctx.question_service == mock_question
        assert ctx.file_service == mock_file
        assert ctx.authenticator == mock_auth
        assert ctx.settings == mock_settings


class TestGetAppContext:
    """Tests for get_app_context helper function."""

    def test_get_app_context_valid(self) -> None:
        """Test getting app context from MCP context."""
        mock_app_ctx = MagicMock(spec=MCPServerContext)
        mock_mcp_ctx = MagicMock()
        mock_mcp_ctx.request_context.lifespan_context = mock_app_ctx

        result = get_app_context(mock_mcp_ctx)

        assert result == mock_app_ctx

    def test_get_app_context_missing_lifespan(self) -> None:
        """Test that get_app_context returns None when lifespan context is None."""
        mock_mcp_ctx = MagicMock()
        mock_mcp_ctx.request_context.lifespan_context = None

        # The function returns whatever lifespan_context is, even if None
        result = get_app_context(mock_mcp_ctx)
        assert result is None


class TestCreateMcpServer:
    """Tests for create_mcp_server function."""

    def test_create_mcp_server_returns_fastmcp(self) -> None:
        """Test that create_mcp_server returns a FastMCP instance."""
        # Mock the modules that are imported locally
        mock_tools_module = MagicMock()
        mock_tools_module.register_rag_tools = MagicMock()
        mock_resources_module = MagicMock()
        mock_resources_module.register_rag_resources = MagicMock()

        with patch.dict(
            sys.modules,
            {
                "backend.mcp_server.tools": mock_tools_module,
                "backend.mcp_server.resources": mock_resources_module,
            },
        ):
            server = create_mcp_server()

            # FastMCP should have name and version
            assert server.name == "RAG Modulo"

    def test_create_mcp_server_registers_tools(self) -> None:
        """Test that create_mcp_server registers tools."""
        # Mock the modules that are imported locally
        mock_tools_module = MagicMock()
        mock_register_tools = MagicMock()
        mock_tools_module.register_rag_tools = mock_register_tools
        mock_resources_module = MagicMock()
        mock_register_resources = MagicMock()
        mock_resources_module.register_rag_resources = mock_register_resources

        with patch.dict(
            sys.modules,
            {
                "backend.mcp_server.tools": mock_tools_module,
                "backend.mcp_server.resources": mock_resources_module,
            },
        ):
            server = create_mcp_server()

            mock_register_tools.assert_called_once_with(server)
            mock_register_resources.assert_called_once_with(server)


class TestServerLifespan:
    """Tests for server lifespan management."""

    @pytest.mark.asyncio
    async def test_lifespan_initializes_services(self) -> None:
        """Test that lifespan context initializes all services."""
        from backend.mcp_server.server import server_lifespan

        mock_server = MagicMock()
        mock_db_session = MagicMock()
        mock_settings = MockSettings()

        # Mock for local imports
        mock_database_module = MagicMock()
        mock_database_module.get_db.return_value = iter([mock_db_session])

        # Service mocks
        mock_search_service = MagicMock()
        mock_collection_service = MagicMock()
        mock_podcast_service = MagicMock()
        mock_question_service = MagicMock()
        mock_file_service = MagicMock()
        mock_authenticator = MagicMock()

        with (
            patch.dict(
                sys.modules,
                {
                    "backend.rag_solution.repository.database": mock_database_module,
                },
            ),
            patch("backend.mcp_server.server.get_settings", return_value=mock_settings),
            patch("backend.mcp_server.server.SearchService", return_value=mock_search_service),
            patch("backend.mcp_server.server.CollectionService", return_value=mock_collection_service),
            patch("backend.mcp_server.server.PodcastService", return_value=mock_podcast_service),
            patch("backend.mcp_server.server.QuestionService", return_value=mock_question_service),
            patch("backend.mcp_server.server.FileManagementService", return_value=mock_file_service),
            patch("backend.mcp_server.server.MCPAuthenticator", return_value=mock_authenticator),
        ):
            async with server_lifespan(mock_server) as ctx:
                assert isinstance(ctx, MCPServerContext)
                assert ctx.db_session == mock_db_session
                assert ctx.search_service == mock_search_service
                assert ctx.collection_service == mock_collection_service

    @pytest.mark.asyncio
    async def test_lifespan_closes_db_on_exit(self) -> None:
        """Test that lifespan closes database session on exit."""
        from backend.mcp_server.server import server_lifespan

        mock_server = MagicMock()
        mock_db_session = MagicMock()
        mock_settings = MockSettings()

        # Mock for local imports
        mock_database_module = MagicMock()
        mock_database_module.get_db.return_value = iter([mock_db_session])

        with (
            patch.dict(
                sys.modules,
                {
                    "backend.rag_solution.repository.database": mock_database_module,
                },
            ),
            patch("backend.mcp_server.server.get_settings", return_value=mock_settings),
            patch("backend.mcp_server.server.SearchService"),
            patch("backend.mcp_server.server.CollectionService"),
            patch("backend.mcp_server.server.PodcastService"),
            patch("backend.mcp_server.server.QuestionService"),
            patch("backend.mcp_server.server.FileManagementService"),
            patch("backend.mcp_server.server.MCPAuthenticator"),
        ):
            async with server_lifespan(mock_server):
                pass

            # DB session should be closed after exiting context
            mock_db_session.close.assert_called_once()


class TestRunServer:
    """Tests for run_server function."""

    def test_run_server_stdio_transport(self) -> None:
        """Test run_server with stdio transport."""
        from backend.mcp_server.server import run_server

        with patch("backend.mcp_server.server.create_mcp_server") as mock_create:
            mock_mcp = MagicMock()
            mock_create.return_value = mock_mcp

            run_server(transport="stdio", port=8080)

            mock_mcp.run.assert_called_once_with(transport="stdio")

    def test_run_server_sse_transport(self) -> None:
        """Test run_server with SSE transport."""
        from backend.mcp_server.server import run_server

        with patch("backend.mcp_server.server.create_mcp_server") as mock_create:
            mock_mcp = MagicMock()
            mock_create.return_value = mock_mcp

            run_server(transport="sse", port=9000)

            # SSE transport should set port on settings
            mock_mcp.run.assert_called_once_with(transport="sse")

    def test_run_server_http_transport(self) -> None:
        """Test run_server with HTTP transport."""
        from backend.mcp_server.server import run_server

        with (
            patch("backend.mcp_server.server.create_mcp_server") as mock_create,
            patch("backend.mcp_server.server.asyncio") as mock_asyncio,
        ):
            mock_mcp = MagicMock()
            mock_create.return_value = mock_mcp

            run_server(transport="http", port=8080)

            # HTTP transport uses asyncio.run with streamable-http
            mock_asyncio.run.assert_called_once()

    def test_run_server_default_transport(self) -> None:
        """Test run_server defaults to stdio transport."""
        from backend.mcp_server.server import run_server

        with patch("backend.mcp_server.server.create_mcp_server") as mock_create:
            mock_mcp = MagicMock()
            mock_create.return_value = mock_mcp

            run_server()

            mock_mcp.run.assert_called_once_with(transport="stdio")


class TestModuleExports:
    """Tests for module exports."""

    def test_mcp_server_init_exports(self) -> None:
        """Test that __init__.py exports correct functions."""
        from backend.mcp_server import create_mcp_server, run_server

        assert callable(create_mcp_server)
        assert callable(run_server)

    def test_mcp_server_all(self) -> None:
        """Test __all__ contains expected exports."""
        import backend.mcp_server as mcp_server

        assert "create_mcp_server" in mcp_server.__all__
        assert "run_server" in mcp_server.__all__


class TestValidateAuthConfiguration:
    """Tests for _validate_auth_configuration function."""

    def test_no_jwt_secret_key_logs_warning_when_auth_not_required(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test warning is logged when JWT_SECRET_KEY is missing and auth not required."""

        @dataclass
        class SettingsNoJWT:
            JWT_SECRET_KEY: str | None = None
            MCP_API_KEY: str | None = "valid-api-key"
            MCP_AUTH_REQUIRED: bool = False

        with caplog.at_level("WARNING"):
            _validate_auth_configuration(SettingsNoJWT())

        assert "JWT_SECRET_KEY not configured" in caplog.text
        assert "Bearer token authentication will not work" in caplog.text

    def test_no_jwt_secret_key_raises_when_auth_required(self) -> None:
        """Test ValueError is raised when JWT_SECRET_KEY is missing and MCP_AUTH_REQUIRED=true."""

        @dataclass
        class SettingsAuthRequired:
            JWT_SECRET_KEY: str | None = None
            MCP_API_KEY: str | None = "valid-api-key"
            MCP_AUTH_REQUIRED: bool = True

        with pytest.raises(ValueError) as exc_info:
            _validate_auth_configuration(SettingsAuthRequired())

        assert "JWT_SECRET_KEY must be configured" in str(exc_info.value)
        assert "MCP_AUTH_REQUIRED=true" in str(exc_info.value)

    def test_no_api_key_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test warning is logged when MCP_API_KEY is missing."""

        @dataclass
        class SettingsNoAPIKey:
            JWT_SECRET_KEY: str | None = "secret-key"
            MCP_API_KEY: str | None = None
            MCP_AUTH_REQUIRED: bool = False

        with caplog.at_level("WARNING"):
            _validate_auth_configuration(SettingsNoAPIKey())

        assert "MCP_API_KEY not configured" in caplog.text
        assert "API key authentication will not work" in caplog.text

    def test_all_configured_no_warnings(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test no warnings when all auth configuration is present."""

        @dataclass
        class SettingsComplete:
            JWT_SECRET_KEY: str | None = "secret-key"
            MCP_API_KEY: str | None = "api-key"
            MCP_AUTH_REQUIRED: bool = False

        with caplog.at_level("WARNING"):
            _validate_auth_configuration(SettingsComplete())

        # No warnings about JWT or API key
        assert "JWT_SECRET_KEY not configured" not in caplog.text
        assert "MCP_API_KEY not configured" not in caplog.text

    def test_jwt_secret_key_present_with_auth_required_no_error(self) -> None:
        """Test no error when JWT_SECRET_KEY is present and MCP_AUTH_REQUIRED=true."""

        @dataclass
        class SettingsAuthRequiredWithJWT:
            JWT_SECRET_KEY: str | None = "secret-key"
            MCP_API_KEY: str | None = "api-key"
            MCP_AUTH_REQUIRED: bool = True

        # Should not raise
        _validate_auth_configuration(SettingsAuthRequiredWithJWT())
