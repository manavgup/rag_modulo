"""Unit tests for MCP Gateway Client.

Tests the ResilientMCPGatewayClient service including:
- Circuit breaker functionality
- Health check mechanisms
- Tool listing and invocation
- Retry logic and error handling
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from rag_solution.schemas.mcp_schema import MCPInvocationStatus


class TestCircuitBreaker:
    """Test circuit breaker implementation."""

    @pytest.fixture
    def circuit_breaker(self):
        """Create circuit breaker instance."""
        from rag_solution.services.mcp_gateway_client import CircuitBreaker

        return CircuitBreaker(failure_threshold=3, recovery_timeout=10.0)

    @pytest.mark.asyncio
    async def test_circuit_breaker_initial_state(self, circuit_breaker):
        """Test circuit breaker starts in closed state."""
        from rag_solution.services.mcp_gateway_client import CircuitBreakerState

        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.failure_count == 0
        assert not circuit_breaker.is_open

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_success(self, circuit_breaker):
        """Test circuit breaker resets on success."""
        from rag_solution.services.mcp_gateway_client import CircuitBreakerState

        # Record some failures first
        await circuit_breaker.record_failure()
        await circuit_breaker.record_failure()
        assert circuit_breaker.failure_count == 2

        # Success should reset
        await circuit_breaker.record_success()
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_threshold(self, circuit_breaker):
        """Test circuit breaker opens after failure threshold."""
        from rag_solution.services.mcp_gateway_client import CircuitBreakerState

        # Record failures up to threshold
        for _ in range(3):
            await circuit_breaker.record_failure()

        assert circuit_breaker.state == CircuitBreakerState.OPEN
        assert circuit_breaker.is_open

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_after_timeout(self, circuit_breaker):
        """Test circuit breaker transitions to half-open after recovery timeout."""
        from rag_solution.services.mcp_gateway_client import CircuitBreakerState

        # Open the circuit
        for _ in range(3):
            await circuit_breaker.record_failure()

        # Simulate time passing
        circuit_breaker.last_failure_time = datetime.now(UTC) - timedelta(seconds=15)

        state = await circuit_breaker.check_state()
        assert state == CircuitBreakerState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_closes_on_success_from_half_open(self, circuit_breaker):
        """Test circuit breaker closes after successful call in half-open state."""
        from rag_solution.services.mcp_gateway_client import CircuitBreakerState

        # Get to half-open state
        for _ in range(3):
            await circuit_breaker.record_failure()
        circuit_breaker.last_failure_time = datetime.now(UTC) - timedelta(seconds=15)
        await circuit_breaker.check_state()

        # Success should close it
        await circuit_breaker.record_success()
        assert circuit_breaker.state == CircuitBreakerState.CLOSED


class TestResilientMCPGatewayClient:
    """Test ResilientMCPGatewayClient."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.mcp_enabled = True
        settings.mcp_gateway_url = "http://localhost:3001"
        settings.mcp_timeout = 30.0
        settings.mcp_health_timeout = 5.0
        settings.mcp_max_retries = 3
        settings.mcp_circuit_breaker_threshold = 5
        settings.mcp_circuit_breaker_timeout = 60.0
        settings.mcp_jwt_token = None
        return settings

    @pytest.fixture
    def mcp_client(self, mock_settings):
        """Create MCP client instance."""
        from rag_solution.services.mcp_gateway_client import ResilientMCPGatewayClient

        return ResilientMCPGatewayClient(mock_settings)

    def test_client_initialization(self, mcp_client, mock_settings):
        """Test client initializes with correct settings."""
        assert mcp_client.gateway_url == "http://localhost:3001"
        assert mcp_client.timeout == 30.0
        assert mcp_client.health_timeout == 5.0
        assert mcp_client.max_retries == 3

    def test_headers_without_jwt(self, mcp_client):
        """Test headers are generated correctly without JWT."""
        headers = mcp_client._get_headers()
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers

    def test_headers_with_jwt(self, mock_settings):
        """Test headers include JWT token when configured."""
        from rag_solution.services.mcp_gateway_client import ResilientMCPGatewayClient

        mock_settings.mcp_jwt_token = "test-token"
        client = ResilientMCPGatewayClient(mock_settings)

        headers = client._get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-token"

    @pytest.mark.asyncio
    async def test_health_check_success(self, mcp_client):
        """Test successful health check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            health = await mcp_client.check_health()

            assert health.healthy is True
            assert health.gateway_url == "http://localhost:3001"
            assert health.latency_ms is not None

    @pytest.mark.asyncio
    async def test_health_check_timeout(self, mcp_client):
        """Test health check handles timeout."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            health = await mcp_client.check_health()

            assert health.healthy is False
            assert "timed out" in health.error.lower()

    @pytest.mark.asyncio
    async def test_health_check_http_error(self, mcp_client):
        """Test health check handles HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 503

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.HTTPStatusError("Error", request=Mock(), response=mock_response))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            health = await mcp_client.check_health()

            assert health.healthy is False
            assert "503" in health.error

    @pytest.mark.asyncio
    async def test_list_tools_success(self, mcp_client):
        """Test successful tool listing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(return_value={
            "tools": [
                {
                    "name": "summarizer",
                    "description": "Summarizes text",
                    "parameters": [
                        {"name": "text", "type": "string", "required": True}
                    ],
                    "version": "v1",
                    "enabled": True,
                }
            ]
        })

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = await mcp_client.list_tools()

            assert response.gateway_healthy is True
            assert len(response.tools) == 1
            assert response.tools[0].name == "summarizer"
            assert response.tools[0].description == "Summarizes text"

    @pytest.mark.asyncio
    async def test_list_tools_circuit_open(self, mcp_client):
        """Test list tools returns empty when circuit is open."""
        from rag_solution.services.mcp_gateway_client import CircuitBreakerState

        # Manually set circuit to open state
        mcp_client.circuit_breaker.state = CircuitBreakerState.OPEN

        response = await mcp_client.list_tools()

        assert response.gateway_healthy is False
        assert len(response.tools) == 0

    @pytest.mark.asyncio
    async def test_invoke_tool_success(self, mcp_client):
        """Test successful tool invocation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(return_value={
            "result": {"summary": "This is a summary"}
        })

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await mcp_client.invoke_tool("summarizer", {"text": "Hello world"})

            assert result.status == MCPInvocationStatus.SUCCESS
            assert result.tool_name == "summarizer"
            assert result.result is not None
            assert result.execution_time_ms is not None

    @pytest.mark.asyncio
    async def test_invoke_tool_timeout(self, mcp_client):
        """Test tool invocation handles timeout."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Speed up test by setting max_retries to 0
            mcp_client.max_retries = 0

            result = await mcp_client.invoke_tool("summarizer", {"text": "test"})

            assert result.status == MCPInvocationStatus.TIMEOUT
            assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invoke_tool_circuit_open(self, mcp_client):
        """Test tool invocation returns circuit open status."""
        from rag_solution.services.mcp_gateway_client import CircuitBreakerState

        mcp_client.circuit_breaker.state = CircuitBreakerState.OPEN

        result = await mcp_client.invoke_tool("summarizer", {"text": "test"})

        assert result.status == MCPInvocationStatus.CIRCUIT_OPEN
        assert "circuit breaker" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invoke_tool_http_error(self, mcp_client):
        """Test tool invocation handles HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Tool not found"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(
                side_effect=httpx.HTTPStatusError("Not Found", request=Mock(), response=mock_response)
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            mcp_client.max_retries = 0

            result = await mcp_client.invoke_tool("unknown_tool", {})

            assert result.status == MCPInvocationStatus.ERROR
            assert "404" in result.error

    def test_get_metrics(self, mcp_client):
        """Test metrics retrieval."""
        metrics = mcp_client.get_metrics()

        assert "requests_total" in metrics
        assert "requests_success" in metrics
        assert "requests_failed" in metrics
        assert "circuit_breaker_state" in metrics

    @pytest.mark.asyncio
    async def test_is_available_true(self, mcp_client):
        """Test availability check returns true when gateway healthy."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            available = await mcp_client.is_available()

            assert available is True

    @pytest.mark.asyncio
    async def test_is_available_false_circuit_open(self, mcp_client):
        """Test availability returns false when circuit open."""
        from rag_solution.services.mcp_gateway_client import CircuitBreakerState

        mcp_client.circuit_breaker.state = CircuitBreakerState.OPEN

        available = await mcp_client.is_available()

        assert available is False


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker with client."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings with low threshold for testing."""
        settings = Mock()
        settings.mcp_enabled = True
        settings.mcp_gateway_url = "http://localhost:3001"
        settings.mcp_timeout = 1.0  # Short timeout
        settings.mcp_health_timeout = 1.0
        settings.mcp_max_retries = 0  # No retries for speed
        settings.mcp_circuit_breaker_threshold = 2  # Low threshold
        settings.mcp_circuit_breaker_timeout = 1.0  # Short recovery
        settings.mcp_jwt_token = None
        return settings

    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self, mock_settings):
        """Test circuit opens after multiple failures."""
        from rag_solution.services.mcp_gateway_client import (
            CircuitBreakerState,
            ResilientMCPGatewayClient,
        )

        client = ResilientMCPGatewayClient(mock_settings)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Make enough failures to trip circuit
            for _ in range(3):
                await client.invoke_tool("test", {})

            assert client.circuit_breaker.state == CircuitBreakerState.OPEN
