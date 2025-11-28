"""Resilient MCP Gateway Client with circuit breaker pattern.

This module provides a thin, resilient wrapper around the MCP Context Forge
Gateway, implementing health checks, circuit breaker, timeouts, and structured
logging as per the expert panel recommendations.

Key features:
- Health monitoring with 5-second timeout
- Circuit breaker (5 failures, 60s recovery)
- Graceful degradation (core RAG works if tools fail)
- API versioning (v1 format)
- Prometheus-ready metrics
- Structured logging
"""

import asyncio
import time
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import httpx

from core.config import Settings
from core.logging_utils import get_logger
from rag_solution.schemas.mcp_schema import (
    MCPHealthStatus,
    MCPInvocationOutput,
    MCPInvocationStatus,
    MCPTool,
    MCPToolParameter,
    MCPToolsResponse,
)

logger = get_logger(__name__)


class CircuitBreakerState(str, Enum):
    """Circuit breaker state machine states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Simple circuit breaker implementation.

    Tracks failures and opens the circuit when threshold is exceeded.
    After recovery timeout, allows a test request through (half-open state).

    Attributes:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before testing recovery
        state: Current circuit state
        failure_count: Current number of consecutive failures
        last_failure_time: Timestamp of last failure
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0) -> None:
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures to trigger open state (default: 5)
            recovery_timeout: Seconds to wait before half-open state (default: 60s)
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self._lock = asyncio.Lock()

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (rejecting requests)."""
        return self.state == CircuitBreakerState.OPEN

    async def check_state(self) -> CircuitBreakerState:
        """Check and potentially transition circuit state.

        If circuit is open and recovery timeout has passed,
        transition to half-open state to allow a test request.

        Returns:
            Current circuit state after any transitions
        """
        async with self._lock:
            if self.state == CircuitBreakerState.OPEN and self.last_failure_time:
                elapsed = datetime.now(UTC) - self.last_failure_time
                if elapsed >= timedelta(seconds=self.recovery_timeout):
                    logger.info(
                        "Circuit breaker transitioning to half-open state",
                        extra={
                            "recovery_timeout": self.recovery_timeout,
                            "elapsed_seconds": elapsed.total_seconds(),
                        },
                    )
                    self.state = CircuitBreakerState.HALF_OPEN
            return self.state

    async def record_success(self) -> None:
        """Record a successful call, resetting failure count."""
        async with self._lock:
            previous_state = self.state
            self.failure_count = 0
            self.state = CircuitBreakerState.CLOSED

            if previous_state != CircuitBreakerState.CLOSED:
                logger.info(
                    "Circuit breaker closed after successful call",
                    extra={
                        "previous_state": previous_state.value,
                        "current_state": self.state.value,
                    },
                )

    async def record_failure(self) -> None:
        """Record a failed call, potentially opening the circuit."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now(UTC)

            if self.failure_count >= self.failure_threshold:
                previous_state = self.state
                self.state = CircuitBreakerState.OPEN
                logger.warning(
                    "Circuit breaker opened after threshold exceeded",
                    extra={
                        "failure_count": self.failure_count,
                        "threshold": self.failure_threshold,
                        "recovery_timeout": self.recovery_timeout,
                        "previous_state": previous_state.value,
                    },
                )
            else:
                logger.debug(
                    "Circuit breaker recorded failure",
                    extra={
                        "failure_count": self.failure_count,
                        "threshold": self.failure_threshold,
                    },
                )


class ResilientMCPGatewayClient:
    """Resilient client for MCP Context Forge Gateway.

    Implements the expert panel's recommended thin wrapper approach:
    - ~100 lines core logic
    - Health checks with 5s timeout
    - Circuit breaker (5 failures, 60s recovery)
    - Graceful degradation
    - Structured logging

    Usage:
        settings = get_settings()
        client = ResilientMCPGatewayClient(settings)

        # Check health
        health = await client.check_health()

        # List available tools
        tools = await client.list_tools()

        # Invoke a tool
        result = await client.invoke_tool("powerpoint_generator", {"topic": "AI"})

    Attributes:
        settings: Application settings
        gateway_url: MCP gateway base URL
        timeout: Request timeout in seconds
        health_timeout: Health check timeout
        circuit_breaker: Circuit breaker instance
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize the MCP gateway client.

        Args:
            settings: Application settings with MCP configuration
        """
        self.settings = settings
        self.gateway_url = settings.mcp_gateway_url.rstrip("/")
        self.timeout = settings.mcp_timeout
        self.health_timeout = settings.mcp_health_timeout
        self.max_retries = settings.mcp_max_retries
        self.jwt_token = settings.mcp_jwt_token

        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=settings.mcp_circuit_breaker_threshold,
            recovery_timeout=settings.mcp_circuit_breaker_timeout,
        )

        # Metrics counters (Prometheus-ready)
        self._metrics = {
            "requests_total": 0,
            "requests_success": 0,
            "requests_failed": 0,
            "requests_circuit_open": 0,
            "health_checks_total": 0,
            "health_checks_success": 0,
        }

        logger.info(
            "MCP Gateway client initialized",
            extra={
                "gateway_url": self.gateway_url,
                "timeout": self.timeout,
                "health_timeout": self.health_timeout,
                "circuit_breaker_threshold": settings.mcp_circuit_breaker_threshold,
                "circuit_breaker_timeout": settings.mcp_circuit_breaker_timeout,
            },
        )

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for requests.

        Returns:
            Dictionary of headers including auth if configured
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
        return headers

    async def check_health(self) -> MCPHealthStatus:
        """Check MCP gateway health.

        Performs a health check with 5-second timeout as per requirements.
        Does NOT trigger circuit breaker on health check failures.

        Returns:
            MCPHealthStatus with health information
        """
        self._metrics["health_checks_total"] += 1
        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=self.health_timeout) as client:
                response = await client.get(
                    f"{self.gateway_url}/health",
                    headers=self._get_headers(),
                )
                response.raise_for_status()

                latency_ms = (time.perf_counter() - start_time) * 1000
                self._metrics["health_checks_success"] += 1

                logger.debug(
                    "MCP gateway health check succeeded",
                    extra={
                        "latency_ms": latency_ms,
                        "status_code": response.status_code,
                    },
                )

                return MCPHealthStatus(
                    healthy=True,
                    gateway_url=self.gateway_url,
                    latency_ms=latency_ms,
                    circuit_breaker_state=self.circuit_breaker.state.value,
                )

        except httpx.TimeoutException:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(
                "MCP gateway health check timed out",
                extra={
                    "timeout": self.health_timeout,
                    "latency_ms": latency_ms,
                },
            )
            return MCPHealthStatus(
                healthy=False,
                gateway_url=self.gateway_url,
                latency_ms=latency_ms,
                circuit_breaker_state=self.circuit_breaker.state.value,
                error=f"Health check timed out after {self.health_timeout}s",
            )

        except httpx.HTTPStatusError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(
                "MCP gateway health check failed with HTTP error",
                extra={
                    "status_code": e.response.status_code,
                    "latency_ms": latency_ms,
                },
            )
            return MCPHealthStatus(
                healthy=False,
                gateway_url=self.gateway_url,
                latency_ms=latency_ms,
                circuit_breaker_state=self.circuit_breaker.state.value,
                error=f"HTTP {e.response.status_code}",
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(
                "MCP gateway health check failed",
                extra={
                    "error": str(e),
                    "latency_ms": latency_ms,
                },
            )
            return MCPHealthStatus(
                healthy=False,
                gateway_url=self.gateway_url,
                latency_ms=latency_ms,
                circuit_breaker_state=self.circuit_breaker.state.value,
                error=str(e),
            )

    async def list_tools(self) -> MCPToolsResponse:
        """List available MCP tools from the gateway.

        Respects circuit breaker state. Falls back gracefully if gateway unavailable.

        Returns:
            MCPToolsResponse with available tools

        Raises:
            ExternalServiceError: If circuit is open or request fails after retries
        """
        state = await self.circuit_breaker.check_state()

        if state == CircuitBreakerState.OPEN:
            self._metrics["requests_circuit_open"] += 1
            logger.warning(
                "Circuit breaker open, rejecting list_tools request",
                extra={"circuit_state": state.value},
            )
            return MCPToolsResponse(tools=[], total_count=0, gateway_healthy=False)

        self._metrics["requests_total"] += 1
        start_time = time.perf_counter()

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        f"{self.gateway_url}/api/v1/tools",
                        headers=self._get_headers(),
                    )
                    response.raise_for_status()
                    data = response.json()

                    # Parse tools from response
                    tools = []
                    for tool_data in data.get("tools", []):
                        params = [
                            MCPToolParameter(
                                name=p.get("name", ""),
                                type=p.get("type", "string"),
                                description=p.get("description"),
                                required=p.get("required", False),
                                default=p.get("default"),
                            )
                            for p in tool_data.get("parameters", [])
                        ]
                        tools.append(
                            MCPTool(
                                name=tool_data.get("name", ""),
                                description=tool_data.get("description", ""),
                                parameters=params,
                                category=tool_data.get("category"),
                                version=tool_data.get("version", "v1"),
                                enabled=tool_data.get("enabled", True),
                            )
                        )

                    await self.circuit_breaker.record_success()
                    self._metrics["requests_success"] += 1

                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    logger.debug(
                        "Successfully listed MCP tools",
                        extra={
                            "tool_count": len(tools),
                            "latency_ms": elapsed_ms,
                        },
                    )

                    return MCPToolsResponse(
                        tools=tools,
                        total_count=len(tools),
                        gateway_healthy=True,
                    )

            except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError) as e:
                if attempt < self.max_retries:
                    delay = 2**attempt  # Exponential backoff
                    logger.warning(
                        "MCP list_tools failed, retrying",
                        extra={
                            "attempt": attempt + 1,
                            "max_retries": self.max_retries,
                            "delay": delay,
                            "error": str(e),
                        },
                    )
                    await asyncio.sleep(delay)
                    continue

                await self.circuit_breaker.record_failure()
                self._metrics["requests_failed"] += 1

                logger.error(
                    "MCP list_tools failed after retries",
                    extra={
                        "attempts": attempt + 1,
                        "error": str(e),
                    },
                )

                # Return empty response for graceful degradation
                return MCPToolsResponse(tools=[], total_count=0, gateway_healthy=False)

        # Should not reach here, but for type safety
        return MCPToolsResponse(tools=[], total_count=0, gateway_healthy=False)

    async def invoke_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> MCPInvocationOutput:
        """Invoke an MCP tool.

        Implements graceful degradation - core RAG functionality is not affected
        if tool invocation fails.

        Args:
            tool_name: Name of the tool to invoke
            arguments: Tool arguments dictionary
            timeout: Optional timeout override

        Returns:
            MCPInvocationOutput with result or error information
        """
        state = await self.circuit_breaker.check_state()

        if state == CircuitBreakerState.OPEN:
            self._metrics["requests_circuit_open"] += 1
            logger.warning(
                "Circuit breaker open, rejecting invoke_tool request",
                extra={
                    "tool_name": tool_name,
                    "circuit_state": state.value,
                },
            )
            return MCPInvocationOutput(
                tool_name=tool_name,
                status=MCPInvocationStatus.CIRCUIT_OPEN,
                error="Circuit breaker is open - MCP gateway temporarily unavailable",
            )

        self._metrics["requests_total"] += 1
        start_time = time.perf_counter()
        request_timeout = timeout or self.timeout

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=request_timeout) as client:
                    response = await client.post(
                        f"{self.gateway_url}/api/v1/tools/{tool_name}/invoke",
                        json={"arguments": arguments or {}},
                        headers=self._get_headers(),
                    )
                    response.raise_for_status()
                    data = response.json()

                    await self.circuit_breaker.record_success()
                    self._metrics["requests_success"] += 1

                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    logger.info(
                        "MCP tool invocation succeeded",
                        extra={
                            "tool_name": tool_name,
                            "execution_time_ms": elapsed_ms,
                        },
                    )

                    return MCPInvocationOutput(
                        tool_name=tool_name,
                        status=MCPInvocationStatus.SUCCESS,
                        result=data.get("result"),
                        execution_time_ms=elapsed_ms,
                    )

            except httpx.TimeoutException:
                if attempt < self.max_retries:
                    delay = 2**attempt
                    logger.warning(
                        "MCP tool invocation timed out, retrying",
                        extra={
                            "tool_name": tool_name,
                            "attempt": attempt + 1,
                            "delay": delay,
                            "timeout": request_timeout,
                        },
                    )
                    await asyncio.sleep(delay)
                    continue

                await self.circuit_breaker.record_failure()
                self._metrics["requests_failed"] += 1

                elapsed_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    "MCP tool invocation timed out after retries",
                    extra={
                        "tool_name": tool_name,
                        "timeout": request_timeout,
                        "execution_time_ms": elapsed_ms,
                    },
                )

                return MCPInvocationOutput(
                    tool_name=tool_name,
                    status=MCPInvocationStatus.TIMEOUT,
                    error=f"Tool invocation timed out after {request_timeout}s",
                    execution_time_ms=elapsed_ms,
                )

            except httpx.HTTPStatusError as e:
                if attempt < self.max_retries and e.response.status_code >= 500:
                    delay = 2**attempt
                    logger.warning(
                        "MCP tool invocation failed with server error, retrying",
                        extra={
                            "tool_name": tool_name,
                            "status_code": e.response.status_code,
                            "attempt": attempt + 1,
                            "delay": delay,
                        },
                    )
                    await asyncio.sleep(delay)
                    continue

                await self.circuit_breaker.record_failure()
                self._metrics["requests_failed"] += 1

                elapsed_ms = (time.perf_counter() - start_time) * 1000
                error_detail = e.response.text[:200] if e.response.text else str(e)

                logger.error(
                    "MCP tool invocation failed with HTTP error",
                    extra={
                        "tool_name": tool_name,
                        "status_code": e.response.status_code,
                        "error": error_detail,
                        "execution_time_ms": elapsed_ms,
                    },
                )

                return MCPInvocationOutput(
                    tool_name=tool_name,
                    status=MCPInvocationStatus.ERROR,
                    error=f"HTTP {e.response.status_code}: {error_detail}",
                    execution_time_ms=elapsed_ms,
                )

            except Exception as e:
                if attempt < self.max_retries:
                    delay = 2**attempt
                    logger.warning(
                        "MCP tool invocation failed, retrying",
                        extra={
                            "tool_name": tool_name,
                            "error": str(e),
                            "attempt": attempt + 1,
                            "delay": delay,
                        },
                    )
                    await asyncio.sleep(delay)
                    continue

                await self.circuit_breaker.record_failure()
                self._metrics["requests_failed"] += 1

                elapsed_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    "MCP tool invocation failed after retries",
                    extra={
                        "tool_name": tool_name,
                        "error": str(e),
                        "execution_time_ms": elapsed_ms,
                    },
                )

                return MCPInvocationOutput(
                    tool_name=tool_name,
                    status=MCPInvocationStatus.ERROR,
                    error=str(e),
                    execution_time_ms=elapsed_ms,
                )

        # Should not reach here, but for type safety
        return MCPInvocationOutput(
            tool_name=tool_name,
            status=MCPInvocationStatus.ERROR,
            error="Unknown error after retries",
        )

    def get_metrics(self) -> dict[str, Any]:
        """Get client metrics for monitoring.

        Returns:
            Dictionary of Prometheus-ready metrics
        """
        return {
            **self._metrics,
            "circuit_breaker_state": self.circuit_breaker.state.value,
            "circuit_breaker_failure_count": self.circuit_breaker.failure_count,
        }

    async def is_available(self) -> bool:
        """Quick availability check.

        Checks if MCP gateway is available without full health check.
        Useful for conditional enrichment logic.

        Returns:
            True if gateway appears available, False otherwise
        """
        state = await self.circuit_breaker.check_state()
        if state == CircuitBreakerState.OPEN:
            return False

        health = await self.check_health()
        return health.healthy
