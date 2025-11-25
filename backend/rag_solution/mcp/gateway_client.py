"""Resilient MCP Gateway Client with circuit breaker pattern.

This module provides a production-grade client for communicating with MCP Context Forge Gateway.
Implements the resilience patterns recommended by Michael Nygard (Release It!):

- Circuit Breaker: Prevents cascading failures (5 failure threshold, 60s recovery)
- Health Checks: 5-second timeout for gateway availability
- Timeouts: 30-second default timeout on all calls
- Graceful Degradation: Returns empty results on failures, doesn't block core RAG flow
- Structured Logging: Contextual data for observability
- Metrics: Duration tracking for performance monitoring

Architecture follows the Content Enricher pattern (Gregor Hohpe) - enrichment is
parallel, optional, and asynchronous relative to the main search flow.
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx

from core.logging_utils import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting calls
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and rejecting calls."""

    def __init__(self, remaining_time: float) -> None:
        self.remaining_time = remaining_time
        super().__init__(f"Circuit breaker open, retry in {remaining_time:.1f}s")


@dataclass
class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance.

    Follows the circuit breaker pattern from Michael Nygard's Release It!:
    - CLOSED: Normal operation, tracking failures
    - OPEN: Too many failures, rejecting calls immediately
    - HALF_OPEN: Testing if service recovered with a single request

    Attributes:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before testing recovery
        failure_count: Current number of consecutive failures
        last_failure_time: Timestamp of last failure
        state: Current circuit state
    """

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    failure_count: int = field(default=0, init=False)
    last_failure_time: float | None = field(default=None, init=False)
    state: CircuitState = field(default=CircuitState.CLOSED, init=False)

    def record_success(self) -> None:
        """Record a successful call, potentially closing the circuit."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        logger.debug("Circuit breaker: success recorded, state=CLOSED")

    def record_failure(self) -> None:
        """Record a failed call, potentially opening the circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker OPEN after %d failures",
                self.failure_count,
                extra={"failure_count": self.failure_count, "recovery_timeout": self.recovery_timeout},
            )
        else:
            logger.debug(
                "Circuit breaker: failure recorded (%d/%d)",
                self.failure_count,
                self.failure_threshold,
            )

    def can_execute(self) -> bool:
        """Check if a call can be executed.

        Returns:
            True if call is allowed, False otherwise

        Raises:
            CircuitBreakerOpen: If circuit is open and recovery period hasn't elapsed
        """
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if self.last_failure_time is None:
                return True

            elapsed = time.time() - self.last_failure_time
            if elapsed >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker entering HALF_OPEN state for recovery test")
                return True

            remaining = self.recovery_timeout - elapsed
            raise CircuitBreakerOpenError(remaining)

        # HALF_OPEN: Allow one test request
        return True


@dataclass
class MCPToolResult:
    """Result from an MCP tool invocation.

    Attributes:
        tool_name: Name of the invoked tool
        success: Whether the invocation succeeded
        result: Tool output data if successful
        error: Error message if failed
        duration_ms: Execution time in milliseconds
    """

    tool_name: str
    success: bool
    result: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: float = 0.0


class MCPGatewayClient:
    """Resilient HTTP client for MCP Context Forge Gateway.

    Implements production resilience patterns:
    - Circuit breaker for fault tolerance
    - Health checks for availability monitoring
    - Configurable timeouts
    - Structured logging with context
    - Graceful degradation on failures

    Usage:
        client = MCPGatewayClient(gateway_url="http://mcp-gateway:8080")
        result = await client.invoke_tool("powerpoint", {"slides": [...]})
        if result.success:
            # Use result.result
            pass
    """

    def __init__(
        self,
        gateway_url: str,
        api_key: str | None = None,
        timeout: float = 30.0,
        health_check_timeout: float = 5.0,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        """Initialize the MCP Gateway client.

        Args:
            gateway_url: Base URL for the MCP Context Forge Gateway
            api_key: Optional API key for authentication
            timeout: Default timeout for tool invocations (seconds)
            health_check_timeout: Timeout for health checks (seconds)
            circuit_breaker: Optional custom circuit breaker instance
        """
        self.gateway_url = gateway_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.health_check_timeout = health_check_timeout
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            self._client = httpx.AsyncClient(
                base_url=self.gateway_url,
                headers=headers,
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> bool:
        """Check if the MCP Gateway is healthy.

        Returns:
            True if gateway is healthy, False otherwise
        """
        try:
            client = await self._get_client()
            response = await client.get("/health", timeout=self.health_check_timeout)
            is_healthy = response.status_code == 200

            if is_healthy:
                logger.debug("MCP Gateway health check passed")
            else:
                logger.warning(
                    "MCP Gateway health check failed with status %d",
                    response.status_code,
                )

            return is_healthy

        except httpx.TimeoutException:
            logger.warning("MCP Gateway health check timed out after %.1fs", self.health_check_timeout)
            return False
        except httpx.RequestError as e:
            logger.warning("MCP Gateway health check failed: %s", str(e))
            return False

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools from the MCP Gateway.

        Returns:
            List of tool definitions with name, description, and input schema
        """
        try:
            if not self.circuit_breaker.can_execute():
                return []

            client = await self._get_client()
            response = await client.get("/tools")
            response.raise_for_status()

            self.circuit_breaker.record_success()
            tools = response.json().get("tools", [])
            logger.info("Retrieved %d tools from MCP Gateway", len(tools))
            return tools

        except CircuitBreakerOpenError as e:
            logger.warning("Cannot list tools: %s", str(e))
            return []
        except httpx.HTTPStatusError as e:
            logger.error("Failed to list tools: HTTP %d", e.response.status_code)
            self.circuit_breaker.record_failure()
            return []
        except httpx.RequestError as e:
            logger.error("Failed to list tools: %s", str(e))
            self.circuit_breaker.record_failure()
            return []

    async def invoke_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        timeout: float | None = None,
    ) -> MCPToolResult:
        """Invoke an MCP tool with resilience handling.

        Args:
            tool_name: Name of the tool to invoke
            arguments: Tool input arguments
            timeout: Optional custom timeout for this invocation

        Returns:
            MCPToolResult with success status, result data, and metrics
        """
        start_time = time.time()

        try:
            if not self.circuit_breaker.can_execute():
                return MCPToolResult(
                    tool_name=tool_name,
                    success=False,
                    error="Circuit breaker open",
                    duration_ms=0,
                )

            client = await self._get_client()

            # Override timeout if specified
            request_timeout = timeout or self.timeout

            logger.info(
                "Invoking MCP tool",
                extra={
                    "tool_name": tool_name,
                    "timeout": request_timeout,
                    "circuit_state": self.circuit_breaker.state.value,
                },
            )

            response = await client.post(
                f"/tools/{tool_name}/invoke",
                json={"arguments": arguments},
                timeout=request_timeout,
            )
            response.raise_for_status()

            duration_ms = (time.time() - start_time) * 1000
            result_data = response.json()

            self.circuit_breaker.record_success()

            logger.info(
                "MCP tool invocation successful",
                extra={
                    "tool_name": tool_name,
                    "duration_ms": duration_ms,
                },
            )

            return MCPToolResult(
                tool_name=tool_name,
                success=True,
                result=result_data,
                duration_ms=duration_ms,
            )

        except CircuitBreakerOpenError as e:
            logger.warning(
                "MCP tool invocation blocked by circuit breaker",
                extra={"tool_name": tool_name, "remaining_time": e.remaining_time},
            )
            return MCPToolResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
                duration_ms=0,
            )

        except httpx.TimeoutException:
            duration_ms = (time.time() - start_time) * 1000
            self.circuit_breaker.record_failure()

            logger.error(
                "MCP tool invocation timed out",
                extra={
                    "tool_name": tool_name,
                    "timeout": timeout or self.timeout,
                    "duration_ms": duration_ms,
                },
            )

            return MCPToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Timeout after {timeout or self.timeout}s",
                duration_ms=duration_ms,
            )

        except httpx.HTTPStatusError as e:
            duration_ms = (time.time() - start_time) * 1000
            self.circuit_breaker.record_failure()

            logger.error(
                "MCP tool invocation failed with HTTP error",
                extra={
                    "tool_name": tool_name,
                    "status_code": e.response.status_code,
                    "duration_ms": duration_ms,
                },
            )

            return MCPToolResult(
                tool_name=tool_name,
                success=False,
                error=f"HTTP {e.response.status_code}: {e.response.text}",
                duration_ms=duration_ms,
            )

        except httpx.RequestError as e:
            duration_ms = (time.time() - start_time) * 1000
            self.circuit_breaker.record_failure()

            logger.error(
                "MCP tool invocation failed with request error",
                extra={
                    "tool_name": tool_name,
                    "error": str(e),
                    "duration_ms": duration_ms,
                },
            )

            return MCPToolResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
                duration_ms=duration_ms,
            )

    async def invoke_tools_parallel(
        self,
        invocations: list[tuple[str, dict[str, Any]]],
        timeout: float | None = None,
    ) -> list[MCPToolResult]:
        """Invoke multiple MCP tools in parallel.

        Args:
            invocations: List of (tool_name, arguments) tuples
            timeout: Optional custom timeout for each invocation

        Returns:
            List of MCPToolResult objects in same order as invocations
        """
        tasks = [self.invoke_tool(name, args, timeout) for name, args in invocations]
        return await asyncio.gather(*tasks)
