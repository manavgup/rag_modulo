# MCP Context Forge Integration with RAG Modulo

**Date**: November 2025
**Status**: Implemented
**Version**: 2.0
**Parent Design**: [Agent and MCP Support Architecture](./agent-mcp-architecture.md)

## Executive Summary

This document describes the integration of IBM's **MCP Context Forge** as the central gateway for
RAG Modulo's agent and MCP ecosystem. The integration uses **Proxy Authentication** for simple,
secure communication between RAG Modulo and MCP Context Forge.

## Why MCP Context Forge?

### Alignment with RAG Modulo's Agent Architecture

MCP Context Forge provides production-ready capabilities:

| RAG Modulo Need | Context Forge Solution |
|-----------------|------------------------|
| MCP Client | Built-in protocol translation (stdio, SSE, WebSocket, HTTP) |
| Agent Registry | Unified registry of tools, resources, and prompts |
| Multi-protocol support | Virtualizes REST/gRPC as MCP servers |
| Authentication | Proxy authentication (trusted backend) |
| Rate limiting | Built-in with Redis backing |
| Observability | OpenTelemetry integration |
| Admin UI | HTMX/Alpine.js management interface |
| Federation | Redis-backed distributed deployment |

### Benefits

1. **Reduced Development Time**: Leverages production-ready gateway
2. **Simple Authentication**: Proxy auth eliminates JWT token management
3. **Extensibility**: Supports non-MCP services (REST, gRPC) as virtual MCP servers
4. **Resilience**: Circuit breaker pattern with graceful degradation
5. **Scalability**: Redis federation for distributed deployments

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     RAG Modulo Frontend                     │
│              (React + Carbon Design System)                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   RAG Modulo Backend                        │
│                    (FastAPI Services)                       │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          SearchService                               │  │
│  │  - Query processing                                  │  │
│  │  - Vector search                                     │  │
│  │  - Result enrichment via MCP                         │  │
│  └───────────────────┬──────────────────────────────────┘  │
│                      │                                      │
│                      ▼                                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │      ResilientMCPGatewayClient                       │  │
│  │  - Circuit breaker (5 failures, 60s recovery)        │  │
│  │  - Exponential backoff retries                       │  │
│  │  - Proxy authentication via header                   │  │
│  │  - Prometheus-ready metrics                          │  │
│  └───────────────────┬──────────────────────────────────┘  │
└────────────────────────┼────────────────────────────────────┘
                         │
                         │ X-Authenticated-User header
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              MCP Context Forge Gateway                      │
│                TRUST_PROXY_AUTH=true                        │
│                                                             │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │ Protocol       │  │ Tool           │  │  Session     │  │
│  │ Translation    │  │ Registry       │  │  (Redis)     │  │
│  └────────────────┘  └────────────────┘  └──────────────┘  │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐│
│  │         Admin UI (HTMX + Alpine.js)                    ││
│  │  - Manage tools                                        ││
│  │  - Monitor execution                                   ││
│  └────────────────────────────────────────────────────────┘│
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼ (stdio, SSE, HTTP, gRPC)
┌─────────────────────────────────────────────────────────────┐
│                   External MCP Servers                      │
│                                                             │
│  ┌───────────────┐  ┌───────────────┐  ┌────────────────┐  │
│  │ PowerPoint    │  │ Translation   │  │ Data Analysis  │  │
│  │ Generator MCP │  │ Service MCP   │  │ Service MCP    │  │
│  └───────────────┘  └───────────────┘  └────────────────┘  │
│                                                             │
│  ┌───────────────┐  ┌───────────────┐  ┌────────────────┐  │
│  │ REST APIs     │  │ gRPC Services │  │ Custom Tools   │  │
│  │ (Virtualized) │  │ (Virtualized) │  │ (Native MCP)   │  │
│  └───────────────┘  └───────────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Authentication Architecture

RAG Modulo uses **Proxy Authentication** - a simple, secure approach where RAG Modulo acts as a trusted backend service:

```
┌─────────────────┐                    ┌─────────────────────┐
│  RAG Modulo     │                    │  MCP Context Forge  │
│    Backend      │                    │ TRUST_PROXY_AUTH=   │
│                 │                    │       true          │
└───────┬─────────┘                    └──────────┬──────────┘
        │                                         │
        │  GET /tools                             │
        │  X-Authenticated-User: user@example.com │
        │─────────────────────────────────────────▶│
        │                                         │
        │  [{name: "tool1", ...}]                 │
        │◀─────────────────────────────────────────│
        │                                         │
        │  POST /mcp                              │
        │  X-Authenticated-User: user@example.com │
        │  {method: "tools/call", params: {...}}  │
        │─────────────────────────────────────────▶│
        │                                         │
        │  {result: {content: [...]}}             │
        │◀─────────────────────────────────────────│
```

**Benefits over JWT Token Authentication:**

- No JWT token management complexity
- No token refresh logic needed
- No credential synchronization between services
- User identity flows through for audit logging
- MCP Context Forge trusts the header from RAG Modulo

See: [MCP Proxy Authentication Guide](https://ibm.github.io/mcp-context-forge/manage/proxy/)

## Key Components

### 1. ResilientMCPGatewayClient

The implemented client (`backend/rag_solution/services/mcp_gateway_client.py`) provides:

```python
class ResilientMCPGatewayClient:
    """Resilient client for MCP Context Forge Gateway.

    Key features:
    - ~700 lines implementation
    - Health checks with 5s timeout
    - Circuit breaker (5 failures, 60s recovery)
    - Proxy authentication via X-Authenticated-User header
    - Exponential backoff retries
    - Prometheus-ready metrics
    - Structured logging
    """

    def __init__(self, settings: Settings) -> None:
        self.gateway_url = settings.mcp_gateway_url.rstrip("/")
        self.timeout = settings.mcp_timeout
        self._proxy_user_header = settings.mcp_proxy_user_header
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=settings.mcp_circuit_breaker_threshold,
            recovery_timeout=settings.mcp_circuit_breaker_timeout,
        )

    def _get_headers(self, user_id: str | None = None) -> dict[str, str]:
        """Get HTTP headers with proxy authentication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if user_id:
            headers[self._proxy_user_header] = user_id
        return headers

    async def check_health(self) -> MCPHealthStatus:
        """Check MCP gateway health with 5-second timeout."""
        ...

    async def list_tools(self, user_id: str | None = None) -> MCPToolsResponse:
        """List available MCP tools from the gateway."""
        ...

    async def invoke_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        timeout: float | None = None,
        user_id: str | None = None,
    ) -> MCPInvocationOutput:
        """Invoke an MCP tool via /mcp JSON-RPC endpoint."""
        ...
```

### 2. Circuit Breaker Pattern

```python
class CircuitBreaker:
    """Circuit breaker for resilient MCP communication.

    States:
    - CLOSED: Normal operation, all requests pass through
    - OPEN: Failures exceeded threshold, requests fail fast
    - HALF_OPEN: After recovery timeout, allows test request
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
```

### 3. MCP Schema Models

Located in `backend/rag_solution/schemas/mcp_schema.py`:

```python
class MCPHealthStatus(BaseModel):
    healthy: bool
    gateway_url: str
    latency_ms: float | None = None
    circuit_breaker_state: str
    error: str | None = None

class MCPTool(BaseModel):
    name: str
    description: str
    parameters: list[MCPToolParameter]
    category: str | None = None
    version: str = "v1"
    enabled: bool = True

class MCPInvocationOutput(BaseModel):
    tool_name: str
    status: MCPInvocationStatus
    result: Any | None = None
    error: str | None = None
    execution_time_ms: float | None = None
```

## API Endpoints

### MCP Context Forge Endpoints

| Endpoint | Method | Headers | Description |
|----------|--------|---------|-------------|
| `/health` | GET | None | Health check |
| `/tools` | GET | `X-Authenticated-User` | List all tools |
| `/tools` | POST | `X-Authenticated-User`, `Content-Type` | Create a tool |
| `/tools/{id}` | DELETE | `X-Authenticated-User` | Delete a tool |
| `/mcp` | POST | `X-Authenticated-User`, `Content-Type`, `Accept` | JSON-RPC tool invocation |

### RAG Modulo Backend Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/mcp/health` | GET | MCP gateway health status |
| `/api/v1/mcp/tools` | GET | List available MCP tools |
| `/api/v1/mcp/tools/{name}/invoke` | POST | Invoke a specific tool |
| `/api/v1/mcp/metrics` | GET | Client metrics |

## Configuration

### Environment Variables

```bash
# ================================
# MCP CONTEXT FORGE INTEGRATION
# ================================
# RAG Modulo uses PROXY AUTHENTICATION - it acts as a trusted backend service
# that passes authenticated user identity via headers.
# See: https://ibm.github.io/mcp-context-forge/manage/proxy/

# Enable MCP Gateway (starts Redis + MCP Context Forge containers)
ENABLE_MCP_GATEWAY=true

# Gateway URL
MCP_PORT=3001
MCP_GATEWAY_URL=http://localhost:3001

# Proxy authentication settings
MCP_TRUST_PROXY_AUTH=true
MCP_PROXY_USER_HEADER=X-Authenticated-User

# Disable client JWT auth (we use proxy auth instead)
MCP_CLIENT_AUTH_ENABLED=false

# Admin UI auth (optional)
MCP_AUTH_REQUIRED=false
```

### Settings Model

In `backend/core/config.py`:

```python
class Settings(BaseSettings):
    # MCP Gateway Configuration
    enable_mcp_gateway: bool = Field(default=False, alias="ENABLE_MCP_GATEWAY")
    mcp_port: int = Field(default=3001, alias="MCP_PORT")
    mcp_gateway_url: str = Field(default="http://localhost:3001", alias="MCP_GATEWAY_URL")
    mcp_proxy_user_header: str = Field(default="X-Authenticated-User", alias="MCP_PROXY_USER_HEADER")

    # Resilience settings
    mcp_timeout: float = Field(default=30.0, alias="MCP_TIMEOUT")
    mcp_health_timeout: float = Field(default=5.0, alias="MCP_HEALTH_TIMEOUT")
    mcp_max_retries: int = Field(default=3, alias="MCP_MAX_RETRIES")
    mcp_circuit_breaker_threshold: int = Field(default=5, alias="MCP_CIRCUIT_BREAKER_THRESHOLD")
    mcp_circuit_breaker_timeout: float = Field(default=60.0, alias="MCP_CIRCUIT_BREAKER_TIMEOUT")
```

## Deployment

### Docker Compose Configuration

In `docker-compose-infra.yml`:

```yaml
# MCP Context Forge Gateway
mcp-context-forge:
  container_name: mcp-context-forge
  image: ghcr.io/ibm/mcp-context-forge:latest
  profiles:
    - mcp
  ports:
    - "${MCP_PORT:-3001}:${MCP_PORT:-3001}"
  environment:
    PORT: ${MCP_PORT:-3001}
    HOST: 0.0.0.0
    REDIS_URL: redis://redis:6379
    # Proxy authentication settings
    TRUST_PROXY_AUTH: ${MCP_TRUST_PROXY_AUTH:-true}
    PROXY_USER_HEADER: ${MCP_PROXY_USER_HEADER:-X-Authenticated-User}
    MCP_CLIENT_AUTH_ENABLED: ${MCP_CLIENT_AUTH_ENABLED:-false}
    AUTH_REQUIRED: ${MCP_AUTH_REQUIRED:-false}
    LOG_LEVEL: ${MCP_LOG_LEVEL:-info}
  healthcheck:
    test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:$${PORT}/health"]
    interval: 30s
    timeout: 5s
    retries: 3
  depends_on:
    redis:
      condition: service_healthy
  networks:
    - app-network

# Redis for MCP session management
redis:
  container_name: redis
  image: redis:7-alpine
  profiles:
    - mcp
  ports:
    - "6379:6379"
  volumes:
    - ./volumes/redis:/data
  command: redis-server --appendonly yes
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 5
  networks:
    - app-network
```

### Port Allocation

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | React development server |
| MCP Context Forge | 3001 | MCP gateway |
| Backend | 8000 | FastAPI server |
| Redis | 6379 | MCP session storage |

## Testing

### Manual Testing Commands

```bash
# 1. Health check
curl http://localhost:3001/health

# 2. List tools with proxy auth
curl -H "X-Authenticated-User: test@example.com" \
  http://localhost:3001/tools | jq .

# 3. Create a test tool
curl -X POST http://localhost:3001/tools \
  -H "X-Authenticated-User: admin@example.com" \
  -H "Content-Type: application/json" \
  -d '{
    "tool": {
      "name": "httpbin-echo",
      "url": "https://httpbin.org/post",
      "description": "Echo test tool",
      "request_type": "POST",
      "integration_type": "REST",
      "input_schema": {
        "type": "object",
        "properties": {
          "message": {"type": "string"}
        }
      }
    }
  }' | jq .

# 4. Invoke a tool (use /mcp endpoint with -L flag)
curl -L -X POST http://localhost:3001/mcp \
  -H "X-Authenticated-User: test@example.com" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "httpbin-echo",
      "arguments": {"message": "Hello from RAG Modulo!"}
    }
  }' | jq .
```

### Python Integration Test

```python
import asyncio
from rag_solution.services.mcp_gateway_client import ResilientMCPGatewayClient
from core.config import get_settings

async def test_mcp_integration():
    client = ResilientMCPGatewayClient(get_settings())

    # Health check
    health = await client.check_health()
    print(f"Gateway healthy: {health.healthy}")
    print(f"Circuit breaker state: {health.circuit_breaker_state}")

    # List tools
    tools = await client.list_tools(user_id="test@example.com")
    print(f"Available tools: {tools.total_count}")

    # Invoke a tool
    result = await client.invoke_tool(
        tool_name="httpbin-echo",
        arguments={"message": "Hello!"},
        user_id="test@example.com"
    )
    print(f"Invocation status: {result.status.value}")

asyncio.run(test_mcp_integration())
```

## Metrics and Monitoring

### Available Metrics

The `ResilientMCPGatewayClient` exposes Prometheus-ready metrics:

```python
metrics = client.get_metrics()
# {
#     "requests_total": 100,
#     "requests_success": 95,
#     "requests_failed": 5,
#     "requests_circuit_open": 0,
#     "health_checks_total": 50,
#     "health_checks_success": 48,
#     "circuit_breaker_state": "closed",
#     "circuit_breaker_failure_count": 0
# }
```

### Circuit Breaker State Transitions

```
              ┌──────────┐
    ───────▶  │  CLOSED  │ ──── 5 failures ────▶ ┌──────────┐
              └──────────┘                       │   OPEN   │
                    ▲                            └────┬─────┘
                    │                                 │
               success                          60s timeout
                    │                                 │
              ┌─────┴──────┐                          │
              │ HALF_OPEN  │ ◀────────────────────────┘
              └────────────┘
```

## Error Handling and Graceful Degradation

The MCP integration is designed to be non-blocking:

| Scenario | Behavior |
|----------|----------|
| Gateway unreachable | Search continues, enrichment skipped |
| Tool invocation fails | Original result returned unchanged |
| Circuit breaker open | Requests fail fast, no network overhead |
| Timeout | Partial results may be used if available |

Core RAG functionality is **never** affected by MCP failures.

## Security Considerations

1. **Network Isolation**: MCP Context Forge runs in the same Docker network as RAG Modulo
2. **Proxy Trust**: MCP is configured to trust only the `X-Authenticated-User` header from RAG Modulo
3. **No Exposed Secrets**: Proxy auth eliminates JWT token management in the codebase
4. **Audit Logging**: User identity flows through for tracking tool invocations
5. **Admin UI Protection**: Optional authentication for MCP web UI access

## Performance Considerations

1. **Circuit Breaker**: Prevents cascading failures and reduces latency during outages
2. **Exponential Backoff**: Retries with 1s, 2s, 4s delays to avoid thundering herd
3. **Connection Pooling**: httpx AsyncClient with connection reuse
4. **Health Check Timeout**: 5-second timeout prevents blocking on slow responses
5. **Graceful Degradation**: MCP failures don't impact core search latency

---

**References**:

- [MCP Context Forge Documentation](https://ibm.github.io/mcp-context-forge/)
- [Proxy Authentication Guide](https://ibm.github.io/mcp-context-forge/manage/proxy/)
- [RAG Modulo MCP Integration Guide](../features/mcp-integration.md)
- [Anthropic Model Context Protocol](https://modelcontextprotocol.io/)
