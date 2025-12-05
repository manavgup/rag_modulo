"""Tests for MCP server type definitions and utilities."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from backend.mcp_server.auth import MCPAuthContext
from backend.mcp_server.types import (
    MCPServerContext,
    _extract_headers_from_context,
    get_app_context,
    parse_uuid,
    validate_auth,
)


class TestParseUuid:
    """Tests for parse_uuid function."""

    def test_valid_uuid(self):
        """Test parsing a valid UUID string."""
        valid_uuid = "123e4567-e89b-12d3-a456-426614174000"
        result = parse_uuid(valid_uuid)
        assert isinstance(result, UUID)
        assert str(result) == valid_uuid

    def test_invalid_uuid_raises_error(self):
        """Test that invalid UUID raises ValueError."""
        with pytest.raises(ValueError, match="Invalid id"):
            parse_uuid("not-a-uuid")

    def test_custom_field_name_in_error(self):
        """Test that custom field name appears in error message."""
        with pytest.raises(ValueError, match="Invalid collection_id"):
            parse_uuid("invalid", field_name="collection_id")


class TestGetAppContext:
    """Tests for get_app_context function."""

    def test_extracts_lifespan_context(self):
        """Test that lifespan context is correctly extracted."""
        mock_app_ctx = MagicMock(spec=MCPServerContext)
        mock_request_ctx = MagicMock()
        mock_request_ctx.lifespan_context = mock_app_ctx

        mock_ctx = MagicMock()
        mock_ctx.request_context = mock_request_ctx

        result = get_app_context(mock_ctx)
        assert result is mock_app_ctx


class TestExtractHeadersFromContext:
    """Tests for _extract_headers_from_context function."""

    def test_empty_context_returns_empty_headers(self):
        """Test that empty context returns empty headers dict."""
        mock_ctx = MagicMock()
        mock_ctx.request_context = None

        with patch("backend.mcp_server.types.get_http_headers", None):
            headers = _extract_headers_from_context(mock_ctx)
            assert headers == {}

    def test_extracts_from_http_headers(self):
        """Test extraction of HTTP headers via get_http_headers."""
        mock_ctx = MagicMock()
        mock_ctx.request_context = None

        mock_http_headers = {
            "Authorization": "Bearer token123",
            "X-API-Key": "test-api-key-12345",  # pragma: allowlist secret
        }

        with patch(
            "backend.mcp_server.types.get_http_headers",
            return_value=mock_http_headers,
        ):
            headers = _extract_headers_from_context(mock_ctx)
            assert headers["authorization"] == "Bearer token123"
            assert headers["x-api-key"] == "test-api-key-12345"

    def test_extracts_from_context_metadata(self):
        """Test extraction of headers from MCP context metadata."""
        mock_meta = MagicMock()
        mock_meta.authorization = "Bearer token456"
        mock_meta.x_api_key = "test-api-key-67890"  # pragma: allowlist secret
        mock_meta.x_authenticated_user = "user@example.com"

        mock_request_ctx = MagicMock()
        mock_request_ctx.meta = mock_meta

        mock_ctx = MagicMock()
        mock_ctx.request_context = mock_request_ctx

        with patch("backend.mcp_server.types.get_http_headers", None):
            headers = _extract_headers_from_context(mock_ctx)
            assert headers["authorization"] == "Bearer token456"
            assert headers["x-api-key"] == "test-api-key-67890"
            assert headers["x-authenticated-user"] == "user@example.com"

    def test_http_headers_take_precedence_over_metadata(self):
        """Test that HTTP headers take precedence over metadata."""
        mock_meta = MagicMock()
        mock_meta.authorization = "Bearer metadata-token"

        mock_request_ctx = MagicMock()
        mock_request_ctx.meta = mock_meta

        mock_ctx = MagicMock()
        mock_ctx.request_context = mock_request_ctx

        mock_http_headers = {"Authorization": "Bearer http-token"}

        with patch(
            "backend.mcp_server.types.get_http_headers",
            return_value=mock_http_headers,
        ):
            headers = _extract_headers_from_context(mock_ctx)
            # HTTP headers are processed first, so they take precedence
            assert headers["authorization"] == "Bearer http-token"

    def test_handles_http_headers_exception_gracefully(self):
        """Test that HTTP header extraction failures are handled gracefully."""
        mock_meta = MagicMock()
        mock_meta.authorization = "Bearer fallback-token"

        mock_request_ctx = MagicMock()
        mock_request_ctx.meta = mock_meta

        mock_ctx = MagicMock()
        mock_ctx.request_context = mock_request_ctx

        def raise_error():
            raise RuntimeError("HTTP not available")

        with patch("backend.mcp_server.types.get_http_headers", raise_error):
            # Should not raise, should fall back to metadata
            headers = _extract_headers_from_context(mock_ctx)
            assert headers["authorization"] == "Bearer fallback-token"

    def test_handles_metadata_exception_gracefully(self):
        """Test that metadata extraction failures are handled gracefully."""
        mock_ctx = MagicMock()
        # Make request_context raise when accessing meta
        mock_ctx.request_context = MagicMock()
        mock_ctx.request_context.meta = property(lambda _: (_ for _ in ()).throw(RuntimeError("Metadata error")))

        with patch("backend.mcp_server.types.get_http_headers", None):
            # Should not raise, should return empty dict
            headers = _extract_headers_from_context(mock_ctx)
            # May be empty or have partial data depending on implementation
            assert isinstance(headers, dict)

    def test_user_id_metadata_maps_to_authenticated_user_header(self):
        """Test that user_id metadata maps to x-authenticated-user header."""
        mock_meta = MagicMock()
        mock_meta.user_id = "user123"
        mock_meta.authorization = None
        mock_meta.x_spiffe_jwt = None
        mock_meta.x_api_key = None
        mock_meta.x_authenticated_user = None

        mock_request_ctx = MagicMock()
        mock_request_ctx.meta = mock_meta

        mock_ctx = MagicMock()
        mock_ctx.request_context = mock_request_ctx

        with patch("backend.mcp_server.types.get_http_headers", None):
            headers = _extract_headers_from_context(mock_ctx)
            assert headers["x-authenticated-user"] == "user123"


class TestValidateAuth:
    """Tests for validate_auth function."""

    @pytest.mark.asyncio
    async def test_calls_authenticator_with_extracted_headers(self):
        """Test that validate_auth passes extracted headers to authenticator."""
        mock_auth_context = MCPAuthContext(
            username="test@example.com",
            auth_method="api_key",
            permissions=["read"],
            is_authenticated=True,
        )

        mock_authenticator = AsyncMock()
        mock_authenticator.authenticate_request.return_value = mock_auth_context

        mock_app_ctx = MagicMock(spec=MCPServerContext)
        mock_app_ctx.authenticator = mock_authenticator

        mock_request_ctx = MagicMock()
        mock_request_ctx.lifespan_context = mock_app_ctx
        mock_request_ctx.meta = None

        mock_ctx = MagicMock()
        mock_ctx.request_context = mock_request_ctx

        with patch("backend.mcp_server.types.get_http_headers", None):
            result = await validate_auth(mock_ctx, required_permissions=["read"])

        assert result == mock_auth_context
        mock_authenticator.authenticate_request.assert_called_once()
        call_args = mock_authenticator.authenticate_request.call_args
        assert call_args.kwargs["required_permissions"] == ["read"]

    @pytest.mark.asyncio
    async def test_default_permissions_is_empty_list(self):
        """Test that default permissions is an empty list."""
        mock_auth_context = MCPAuthContext(
            username="test@example.com",
            auth_method="api_key",
            permissions=[],
            is_authenticated=True,
        )

        mock_authenticator = AsyncMock()
        mock_authenticator.authenticate_request.return_value = mock_auth_context

        mock_app_ctx = MagicMock(spec=MCPServerContext)
        mock_app_ctx.authenticator = mock_authenticator

        mock_request_ctx = MagicMock()
        mock_request_ctx.lifespan_context = mock_app_ctx
        mock_request_ctx.meta = None

        mock_ctx = MagicMock()
        mock_ctx.request_context = mock_request_ctx

        with patch("backend.mcp_server.types.get_http_headers", None):
            await validate_auth(mock_ctx)  # No permissions specified

        call_args = mock_authenticator.authenticate_request.call_args
        assert call_args.kwargs["required_permissions"] == []

    @pytest.mark.asyncio
    async def test_passes_headers_from_http_transport(self):
        """Test that headers from HTTP transport are passed to authenticator."""
        mock_auth_context = MCPAuthContext(
            username="test@example.com",
            auth_method="bearer",
            permissions=[],
            is_authenticated=True,
        )

        mock_authenticator = AsyncMock()
        mock_authenticator.authenticate_request.return_value = mock_auth_context

        mock_app_ctx = MagicMock(spec=MCPServerContext)
        mock_app_ctx.authenticator = mock_authenticator

        mock_request_ctx = MagicMock()
        mock_request_ctx.lifespan_context = mock_app_ctx
        mock_request_ctx.meta = None

        mock_ctx = MagicMock()
        mock_ctx.request_context = mock_request_ctx

        mock_http_headers = {
            "Authorization": "Bearer test-token",
            "X-Authenticated-User": "http-user@example.com",
        }

        with patch(
            "backend.mcp_server.types.get_http_headers",
            return_value=mock_http_headers,
        ):
            await validate_auth(mock_ctx)

        call_args = mock_authenticator.authenticate_request.call_args
        headers = call_args.kwargs["headers"]
        assert headers["authorization"] == "Bearer test-token"
        assert headers["x-authenticated-user"] == "http-user@example.com"
