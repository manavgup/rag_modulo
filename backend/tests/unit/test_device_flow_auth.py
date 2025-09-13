"""Unit tests for IBM OIDC Device Authorization Flow.

This module tests the device authorization flow implementation
without external dependencies, focusing on the flow logic and API integration.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from rag_solution.router.auth_router import (
    DeviceFlowPollRequest,
    DeviceFlowStartRequest,
    poll_device_token,
    start_device_flow,
)


@pytest.mark.unit
class TestDeviceFlowBackend:
    """Test device flow backend implementation."""

    @pytest.fixture
    def mock_settings(self):
        """Mock application settings."""
        settings = Mock()
        settings.ibm_client_id = "test-client-id"
        settings.ibm_client_secret = "test-client-secret"
        settings.oidc_device_auth_url = "https://prepiam.ice.ibmcloud.com/v1.0/endpoint/default/device_authorization"
        settings.oidc_token_url = "https://prepiam.ice.ibmcloud.com/v1.0/endpoint/default/token"
        return settings

    @pytest.fixture
    def mock_device_response(self):
        """Mock IBM device authorization response."""
        return {
            "device_code": "device_12345",
            "user_code": "ABCD-1234",
            "verification_uri": "https://prepiam.ice.ibmcloud.com/device",
            "verification_uri_complete": "https://prepiam.ice.ibmcloud.com/device?user_code=ABCD-1234",
            "expires_in": 600,
            "interval": 5,
        }

    @pytest.fixture
    def mock_token_response(self):
        """Mock IBM token response."""
        return {
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "refresh_token_123",
            "userinfo": {"sub": "user123", "email": "test@ibm.com", "name": "Test User"},
        }

    @pytest.mark.asyncio
    async def test_start_device_flow_success(self, mock_settings, mock_device_response):
        """Test successful device flow initiation."""
        # Mock HTTP client response
        with patch("rag_solution.router.auth_router.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_device_response
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            # Test the endpoint
            request = DeviceFlowStartRequest(provider="ibm")
            result = await start_device_flow(request, mock_settings)

            # Verify response structure
            assert result.device_code == "device_12345"
            assert result.user_code == "ABCD-1234"
            assert result.verification_uri == "https://prepiam.ice.ibmcloud.com/device"
            assert result.expires_in == 600
            assert result.interval == 5

    @pytest.mark.asyncio
    async def test_start_device_flow_ibm_error(self, mock_settings):
        """Test device flow initiation when IBM returns error."""
        from fastapi import HTTPException

        with patch("rag_solution.router.auth_router.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {"error": "invalid_client"}
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            # Should raise HTTPException
            request = DeviceFlowStartRequest(provider="ibm")
            with pytest.raises(HTTPException) as exc_info:
                await start_device_flow(request, mock_settings)

            assert "invalid_client" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_poll_device_token_pending(self, mock_settings):
        """Test polling when user hasn't authorized yet."""
        from rag_solution.core.device_flow import DeviceFlowRecord, get_device_flow_storage

        # Store a pending device flow record
        storage = get_device_flow_storage()
        record = DeviceFlowRecord(
            device_code="device_12345",
            user_code="ABCD-1234",
            verification_uri="https://prepiam.ice.ibmcloud.com/device",
            expires_at=datetime.now() + timedelta(minutes=10),
            interval=5,
            status="pending",
        )
        storage.store_record(record)

        with patch("rag_solution.router.auth_router.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {"error": "authorization_pending"}
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            mock_db = Mock()
            request = DeviceFlowPollRequest(device_code="device_12345")
            result = await poll_device_token(request, mock_settings, mock_db)

            assert result.status == "pending"
            assert result.error == "authorization_pending"

    @pytest.mark.asyncio
    async def test_poll_device_token_success(self, mock_settings, mock_token_response):
        """Test successful token retrieval after authorization."""
        from rag_solution.core.device_flow import DeviceFlowRecord, get_device_flow_storage

        # Store a pending device flow record
        storage = get_device_flow_storage()
        record = DeviceFlowRecord(
            device_code="device_12345",
            user_code="ABCD-1234",
            verification_uri="https://prepiam.ice.ibmcloud.com/device",
            expires_at=datetime.now() + timedelta(minutes=10),
            interval=5,
            status="pending",
        )
        storage.store_record(record)

        with patch("rag_solution.router.auth_router.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_token_response
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            # Mock user service
            with patch("rag_solution.router.auth_router.UserService") as mock_user_service_class:
                mock_user = Mock()
                mock_user.id = 123
                mock_user.email = "test@ibm.com"
                mock_user.username = "test@ibm.com"

                mock_user_service = Mock()
                mock_user_service.get_or_create_user_by_fields.return_value = mock_user
                mock_user_service_class.return_value = mock_user_service

                # Mock JWT creation
                with patch("auth.oidc.create_access_token") as mock_create_token:
                    mock_create_token.return_value = "jwt_token_123"

                    mock_db = Mock()
                    request = DeviceFlowPollRequest(device_code="device_12345")
                    result = await poll_device_token(request, mock_settings, mock_db)

                    assert result.status == "success"
                    assert result.access_token == "jwt_token_123"
                    assert result.user["email"] == "test@ibm.com"

    @pytest.mark.asyncio
    async def test_poll_device_token_expired(self, mock_settings):
        """Test polling when device code has expired."""
        from rag_solution.core.device_flow import DeviceFlowRecord, get_device_flow_storage

        # Store an expired device flow record
        storage = get_device_flow_storage()
        record = DeviceFlowRecord(
            device_code="device_12345",
            user_code="ABCD-1234",
            verification_uri="https://prepiam.ice.ibmcloud.com/device",
            expires_at=datetime.now() - timedelta(minutes=1),  # Already expired
            interval=5,
            status="pending",
        )
        storage.store_record(record)

        mock_db = Mock()
        request = DeviceFlowPollRequest(device_code="device_12345")
        result = await poll_device_token(request, mock_settings, mock_db)

        assert result.status == "error"
        assert result.error == "expired_token"


# CLI tests will be added once CLI integration is implemented


@pytest.mark.skip(reason="CLI integration not yet complete")
@pytest.mark.unit
class TestDeviceFlowCLI:
    """Test device flow CLI implementation.

    These tests are skipped until CLI integration is complete.
    They will test RAGConfig, RAGAPIClient, and AuthCommands which are not yet implemented.
    """

    def test_cli_placeholder(self):
        """Placeholder test for CLI functionality."""
        pytest.skip("CLI integration not yet complete")
