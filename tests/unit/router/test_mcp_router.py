"""Unit tests for MCP Router endpoints.

Tests the MCP router API endpoints including:
- Health check endpoint
- List tools endpoint
- Invoke tool endpoint
- Metrics endpoint
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from rag_solution.router.mcp_router import router
from rag_solution.schemas.mcp_schema import (
    MCPHealthStatus,
    MCPInvocationOutput,
    MCPInvocationStatus,
    MCPTool,
    MCPToolsResponse,
)


class TestMCPRouter:
    """Test MCP router endpoints."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.mcp_enabled = True
        settings.mcp_gateway_url = "http://localhost:3001"
        settings.mcp_timeout = 30.0
        settings.mcp_health_timeout = 5.0
        settings.mcp_max_retries = 3
        settings.mcp_max_concurrent = 5
        settings.mcp_circuit_breaker_threshold = 5
        settings.mcp_circuit_breaker_timeout = 60.0
        settings.mcp_jwt_token = None
        return settings

    @pytest.fixture
    def mock_mcp_client(self):
        """Create mock MCP client."""
        client = Mock()
        client.check_health = AsyncMock()
        client.list_tools = AsyncMock()
        client.invoke_tool = AsyncMock()
        client.get_metrics = Mock()
        return client

    @pytest.fixture
    def mock_current_user(self):
        """Create mock current user."""
        return {"uuid": "test-user-id", "email": "test@example.com"}

    @pytest.fixture
    def app(self, mock_settings, mock_mcp_client, mock_current_user):
        """Create FastAPI test app with mocked dependencies."""
        from rag_solution.router.mcp_router import get_mcp_client

        from core.config import get_settings
        from rag_solution.core.dependencies import get_current_user

        app = FastAPI()
        app.include_router(router)

        # Override dependencies
        app.dependency_overrides[get_settings] = lambda: mock_settings
        app.dependency_overrides[get_mcp_client] = lambda: mock_mcp_client
        app.dependency_overrides[get_current_user] = lambda: mock_current_user

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)


class TestHealthEndpoint(TestMCPRouter):
    """Test /api/v1/mcp/health endpoint."""

    def test_health_success(self, client, mock_mcp_client):
        """Test successful health check."""
        mock_mcp_client.check_health.return_value = MCPHealthStatus(
            healthy=True,
            gateway_url="http://localhost:3001",
            latency_ms=50.0,
            circuit_breaker_state="closed",
        )

        response = client.get("/api/v1/mcp/health")

        assert response.status_code == 200
        data = response.json()
        assert data["healthy"] is True
        assert data["gateway_url"] == "http://localhost:3001"
        assert data["circuit_breaker_state"] == "closed"

    def test_health_unhealthy(self, client, mock_mcp_client):
        """Test unhealthy gateway response."""
        mock_mcp_client.check_health.return_value = MCPHealthStatus(
            healthy=False,
            gateway_url="http://localhost:3001",
            error="Connection refused",
            circuit_breaker_state="open",
        )

        response = client.get("/api/v1/mcp/health")

        assert response.status_code == 200  # Still 200, check healthy field
        data = response.json()
        assert data["healthy"] is False
        assert data["error"] == "Connection refused"

    def test_health_mcp_disabled(self, client, mock_settings):
        """Test health endpoint when MCP is disabled."""
        mock_settings.mcp_enabled = False

        response = client.get("/api/v1/mcp/health")

        assert response.status_code == 503


class TestListToolsEndpoint(TestMCPRouter):
    """Test /api/v1/mcp/tools endpoint."""

    def test_list_tools_success(self, client, mock_mcp_client):
        """Test successful tool listing."""
        mock_mcp_client.list_tools.return_value = MCPToolsResponse(
            tools=[
                MCPTool(
                    name="summarizer",
                    description="Summarizes text",
                    version="v1",
                    enabled=True,
                ),
                MCPTool(
                    name="entity_extractor",
                    description="Extracts entities",
                    version="v1",
                    enabled=True,
                ),
            ],
            total_count=2,
            gateway_healthy=True,
        )

        response = client.get("/api/v1/mcp/tools")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tools"]) == 2
        assert data["total_count"] == 2
        assert data["gateway_healthy"] is True

    def test_list_tools_empty(self, client, mock_mcp_client):
        """Test empty tool list."""
        mock_mcp_client.list_tools.return_value = MCPToolsResponse(
            tools=[],
            total_count=0,
            gateway_healthy=True,
        )

        response = client.get("/api/v1/mcp/tools")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tools"]) == 0

    def test_list_tools_mcp_disabled(self, client, mock_settings):
        """Test list tools when MCP is disabled."""
        mock_settings.mcp_enabled = False

        response = client.get("/api/v1/mcp/tools")

        assert response.status_code == 503


class TestInvokeToolEndpoint(TestMCPRouter):
    """Test /api/v1/mcp/tools/{tool_name}/invoke endpoint."""

    def test_invoke_tool_success(self, client, mock_mcp_client):
        """Test successful tool invocation."""
        mock_mcp_client.invoke_tool.return_value = MCPInvocationOutput(
            tool_name="summarizer",
            status=MCPInvocationStatus.SUCCESS,
            result={"summary": "This is a summary"},
            execution_time_ms=150.0,
        )

        response = client.post(
            "/api/v1/mcp/tools/summarizer/invoke",
            json={"arguments": {"text": "Hello world"}},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tool_name"] == "summarizer"
        assert data["status"] == "success"
        assert data["result"]["summary"] == "This is a summary"

    def test_invoke_tool_error(self, client, mock_mcp_client):
        """Test tool invocation with error."""
        mock_mcp_client.invoke_tool.return_value = MCPInvocationOutput(
            tool_name="failing_tool",
            status=MCPInvocationStatus.ERROR,
            error="Tool execution failed",
            execution_time_ms=50.0,
        )

        response = client.post(
            "/api/v1/mcp/tools/failing_tool/invoke",
            json={"arguments": {}},
        )

        assert response.status_code == 200  # Still 200, check status field
        data = response.json()
        assert data["status"] == "error"
        assert data["error"] == "Tool execution failed"

    def test_invoke_tool_timeout(self, client, mock_mcp_client):
        """Test tool invocation timeout."""
        mock_mcp_client.invoke_tool.return_value = MCPInvocationOutput(
            tool_name="slow_tool",
            status=MCPInvocationStatus.TIMEOUT,
            error="Operation timed out after 30s",
            execution_time_ms=30000.0,
        )

        response = client.post(
            "/api/v1/mcp/tools/slow_tool/invoke",
            json={"arguments": {}, "timeout": 30.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "timeout"

    def test_invoke_tool_circuit_open(self, client, mock_mcp_client):
        """Test tool invocation with circuit open."""
        mock_mcp_client.invoke_tool.return_value = MCPInvocationOutput(
            tool_name="any_tool",
            status=MCPInvocationStatus.CIRCUIT_OPEN,
            error="Circuit breaker is open",
        )

        response = client.post(
            "/api/v1/mcp/tools/any_tool/invoke",
            json={"arguments": {}},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "circuit_open"

    def test_invoke_tool_empty_name(self, client):
        """Test tool invocation with empty name."""
        response = client.post(
            "/api/v1/mcp/tools/ /invoke",
            json={"arguments": {}},
        )

        assert response.status_code == 400

    def test_invoke_tool_mcp_disabled(self, client, mock_settings):
        """Test invoke tool when MCP is disabled."""
        mock_settings.mcp_enabled = False

        response = client.post(
            "/api/v1/mcp/tools/summarizer/invoke",
            json={"arguments": {}},
        )

        assert response.status_code == 503


class TestMetricsEndpoint(TestMCPRouter):
    """Test /api/v1/mcp/metrics endpoint."""

    def test_get_metrics_success(self, client, mock_mcp_client):
        """Test successful metrics retrieval."""
        mock_mcp_client.get_metrics.return_value = {
            "requests_total": 100,
            "requests_success": 95,
            "requests_failed": 5,
            "circuit_breaker_state": "closed",
            "circuit_breaker_failure_count": 0,
        }

        response = client.get("/api/v1/mcp/metrics")

        assert response.status_code == 200
        data = response.json()
        assert data["requests_total"] == 100
        assert data["requests_success"] == 95
        assert data["circuit_breaker_state"] == "closed"

    def test_get_metrics_mcp_disabled(self, client, mock_settings):
        """Test metrics when MCP is disabled."""
        mock_settings.mcp_enabled = False

        response = client.get("/api/v1/mcp/metrics")

        assert response.status_code == 503
