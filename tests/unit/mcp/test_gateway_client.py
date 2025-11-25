"""Unit tests for MCP Gateway Client.

Tests the ResilientMCPGatewayClient including:
- Circuit breaker pattern
- Health checks
- Tool invocation
- Error handling and graceful degradation
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from rag_solution.mcp.gateway_client import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    MCPGatewayClient,
    MCPToolResult,
)


class TestCircuitBreaker:
    """Test suite for CircuitBreaker class."""

    def test_initial_state_is_closed(self):
        """Circuit breaker should start in CLOSED state."""
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.can_execute()

    def test_record_success_resets_failure_count(self):
        """Recording success should reset failure count and close circuit."""
        cb = CircuitBreaker()
        cb.failure_count = 3
        cb.state = CircuitState.HALF_OPEN

        cb.record_success()

        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_record_failure_increments_count(self):
        """Recording failure should increment failure count."""
        cb = CircuitBreaker(failure_threshold=5)

        cb.record_failure()

        assert cb.failure_count == 1
        assert cb.state == CircuitState.CLOSED

    def test_circuit_opens_after_threshold_reached(self):
        """Circuit should open after failure threshold is reached."""
        cb = CircuitBreaker(failure_threshold=3)

        for _ in range(3):
            cb.record_failure()

        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 3

    def test_open_circuit_raises_exception(self):
        """Open circuit should raise CircuitBreakerOpenError."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60.0)

        cb.record_failure()
        cb.record_failure()

        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            cb.can_execute()

        assert exc_info.value.remaining_time > 0

    def test_circuit_enters_half_open_after_recovery_timeout(self):
        """Circuit should enter HALF_OPEN state after recovery timeout."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        cb.record_failure()
        cb.record_failure()

        # Wait for recovery timeout
        time.sleep(0.15)

        assert cb.can_execute()
        assert cb.state == CircuitState.HALF_OPEN

    def test_custom_thresholds(self):
        """Circuit breaker should respect custom threshold values."""
        cb = CircuitBreaker(failure_threshold=10, recovery_timeout=120.0)

        assert cb.failure_threshold == 10
        assert cb.recovery_timeout == 120.0


class TestMCPToolResult:
    """Test suite for MCPToolResult dataclass."""

    def test_successful_result(self):
        """Test creating a successful tool result."""
        result = MCPToolResult(
            tool_name="test_tool",
            success=True,
            result={"output": "test"},
            duration_ms=100.5,
        )

        assert result.tool_name == "test_tool"
        assert result.success is True
        assert result.result == {"output": "test"}
        assert result.error is None
        assert result.duration_ms == 100.5

    def test_failed_result(self):
        """Test creating a failed tool result."""
        result = MCPToolResult(
            tool_name="test_tool",
            success=False,
            error="Connection failed",
            duration_ms=50.0,
        )

        assert result.tool_name == "test_tool"
        assert result.success is False
        assert result.result is None
        assert result.error == "Connection failed"


class TestMCPGatewayClient:
    """Test suite for MCPGatewayClient class."""

    @pytest.fixture
    def client(self):
        """Create a test client instance."""
        return MCPGatewayClient(
            gateway_url="http://localhost:8080",
            api_key="test-api-key",
            timeout=30.0,
            health_check_timeout=5.0,
        )

    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test successful health check."""
        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            result = await client.health_check()

            assert result is True
            mock_http.get.assert_called_once_with("/health", timeout=5.0)

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """Test health check failure."""
        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 503
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            result = await client.health_check()

            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_timeout(self, client):
        """Test health check timeout handling."""
        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_get_client.return_value = mock_http

            result = await client.health_check()

            assert result is False

    @pytest.mark.asyncio
    async def test_list_tools_success(self, client):
        """Test successful tool listing."""
        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "tools": [
                    {"name": "tool1", "description": "First tool"},
                    {"name": "tool2", "description": "Second tool"},
                ]
            }
            mock_response.raise_for_status = MagicMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            tools = await client.list_tools()

            assert len(tools) == 2
            assert tools[0]["name"] == "tool1"

    @pytest.mark.asyncio
    async def test_list_tools_with_circuit_breaker_open(self, client):
        """Test list_tools returns empty list when circuit breaker is open."""
        client.circuit_breaker.state = CircuitState.OPEN
        client.circuit_breaker.last_failure_time = time.time()
        client.circuit_breaker.failure_count = 5

        tools = await client.list_tools()

        assert tools == []

    @pytest.mark.asyncio
    async def test_invoke_tool_success(self, client):
        """Test successful tool invocation."""
        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"output": "test result"}
            mock_response.raise_for_status = MagicMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            result = await client.invoke_tool("test_tool", {"input": "test"})

            assert result.success is True
            assert result.tool_name == "test_tool"
            assert result.result == {"output": "test result"}
            assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_invoke_tool_timeout(self, client):
        """Test tool invocation timeout handling."""
        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_get_client.return_value = mock_http

            result = await client.invoke_tool("test_tool", {"input": "test"})

            assert result.success is False
            assert "Timeout" in result.error
            assert client.circuit_breaker.failure_count == 1

    @pytest.mark.asyncio
    async def test_invoke_tool_http_error(self, client):
        """Test tool invocation HTTP error handling."""
        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            error = httpx.HTTPStatusError("Error", request=MagicMock(), response=mock_response)
            mock_http.post = AsyncMock(side_effect=error)
            mock_get_client.return_value = mock_http

            result = await client.invoke_tool("test_tool", {"input": "test"})

            assert result.success is False
            assert "500" in result.error
            assert client.circuit_breaker.failure_count == 1

    @pytest.mark.asyncio
    async def test_invoke_tool_circuit_breaker_open(self, client):
        """Test tool invocation blocked by open circuit breaker."""
        client.circuit_breaker.state = CircuitState.OPEN
        client.circuit_breaker.last_failure_time = time.time()
        client.circuit_breaker.failure_count = 5

        result = await client.invoke_tool("test_tool", {"input": "test"})

        assert result.success is False
        assert "Circuit breaker open" in result.error

    @pytest.mark.asyncio
    async def test_invoke_tools_parallel(self, client):
        """Test parallel tool invocation."""
        with patch.object(client, "invoke_tool") as mock_invoke:
            mock_invoke.return_value = MCPToolResult(
                tool_name="test",
                success=True,
                result={"output": "test"},
            )

            invocations = [
                ("tool1", {"input": "a"}),
                ("tool2", {"input": "b"}),
                ("tool3", {"input": "c"}),
            ]

            results = await client.invoke_tools_parallel(invocations)

            assert len(results) == 3
            assert mock_invoke.call_count == 3

    @pytest.mark.asyncio
    async def test_client_close(self, client):
        """Test client close method."""
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.aclose = AsyncMock()
        client._client = mock_http

        await client.close()

        mock_http.aclose.assert_called_once()

    def test_client_initialization(self):
        """Test client initialization with various parameters."""
        client = MCPGatewayClient(
            gateway_url="http://test:9090/",
            api_key="my-key",
            timeout=60.0,
            health_check_timeout=10.0,
        )

        assert client.gateway_url == "http://test:9090"  # Trailing slash removed
        assert client.api_key == "my-key"
        assert client.timeout == 60.0
        assert client.health_check_timeout == 10.0
        assert client.circuit_breaker is not None

    def test_client_with_custom_circuit_breaker(self):
        """Test client with custom circuit breaker."""
        custom_cb = CircuitBreaker(failure_threshold=10, recovery_timeout=120.0)

        client = MCPGatewayClient(
            gateway_url="http://test:8080",
            circuit_breaker=custom_cb,
        )

        assert client.circuit_breaker is custom_cb
        assert client.circuit_breaker.failure_threshold == 10
