# MCP Context Forge Integration

RAG Modulo integrates with [IBM MCP Context Forge](https://github.com/IBM/mcp-context-forge)
to provide tool-based enrichment capabilities for search results using the Model Context
Protocol (MCP).

## Overview

The MCP integration enables:

- **Tool-Based Enrichment**: Invoke external tools to enhance search results
- **Non-Blocking Design**: Enrichment failures never break core search functionality
- **Circuit Breaker Pattern**: Automatic failure detection and recovery
- **Real-Time Health Monitoring**: Track gateway availability and performance
- **Proxy Authentication**: Simple, secure authentication without JWT token management

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         RAG Modulo Backend                          │
│                                                                     │
│  ┌─────────────┐    ┌──────────────────────┐    ┌────────────────┐ │
│  │   Search    │───▶│ SearchResultEnricher │───▶│   MCP Client   │ │
│  │   Service   │    │   (Content Enricher) │    │ (Circuit Brkr) │ │
│  └─────────────┘    └──────────────────────┘    └───────┬────────┘ │
│                                                         │          │
└─────────────────────────────────────────────────────────┼──────────┘
                                                          │
                                     X-Authenticated-User │ (Proxy Auth)
                                                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Docker Infrastructure                           │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              MCP Context Forge (Port 3001)                   │   │
│  │                  TRUST_PROXY_AUTH=true                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │   │
│  │  │    Tools    │  │   Session   │  │    Tool Registry    │  │   │
│  │  │   Runtime   │  │  Management │  │                     │  │   │
│  │  └─────────────┘  └──────┬──────┘  └─────────────────────┘  │   │
│  │                          │                                   │   │
│  └──────────────────────────┼───────────────────────────────────┘   │
│                             │                                       │
│  ┌──────────────────────────▼───────────────────────────────────┐   │
│  │                    Redis (Port 6379)                         │   │
│  │               Session & Caching Storage                      │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Description |
|-----------|-------------|
| **SearchResultEnricher** | Content enricher that applies MCP tools to search results |
| **ResilientMCPGatewayClient** | HTTP client with circuit breaker pattern for reliability |
| **MCP Context Forge** | IBM's MCP gateway providing tool discovery and invocation |
| **Redis** | Session management and caching for MCP Context Forge |

---

## Authentication Architecture

RAG Modulo uses **Proxy Authentication** - a clean, simple approach where RAG Modulo acts as a
trusted backend service that passes authenticated user identity via HTTP headers.

### Why Proxy Authentication?

| Approach | Complexity | Security | Maintenance |
|----------|------------|----------|-------------|
| **JWT Token Dance** | High (token refresh, expiry, storage) | Good | High |
| **Proxy Auth** | Low (just headers) | Good | Low |

### How It Works

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

**Benefits:**

- No JWT token management in RAG Modulo
- No token refresh logic needed
- No credential synchronization between services
- User identity flows through for audit logging
- MCP Context Forge trusts the header from RAG Modulo

---

## Configuration

### Simple Setup

```bash
# In your .env file
ENABLE_MCP_GATEWAY=true                         # Enable MCP containers
MCP_GATEWAY_URL=http://localhost:3001           # Gateway URL
MCP_TRUST_PROXY_AUTH=true                       # Enable proxy auth in MCP
MCP_PROXY_USER_HEADER=X-Authenticated-User      # Header for user identity
```

### Environment Variables

#### RAG Modulo Backend Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `ENABLE_MCP_GATEWAY` | Enable MCP services (Redis + MCP Context Forge) | `false` |
| `MCP_GATEWAY_URL` | MCP Context Forge gateway URL | `http://localhost:3001` |
| `MCP_PROXY_USER_HEADER` | Header name for passing user identity | `X-Authenticated-User` |

**Advanced Settings** (usually not needed):

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_PORT` | MCP Context Forge port | `3001` |
| `MCP_TIMEOUT` | Request timeout in seconds | `30.0` |
| `MCP_HEALTH_TIMEOUT` | Health check timeout in seconds | `5.0` |
| `MCP_MAX_RETRIES` | Maximum retry attempts | `3` |
| `MCP_MAX_CONCURRENT` | Maximum concurrent requests | `5` |
| `MCP_CIRCUIT_BREAKER_THRESHOLD` | Failures before circuit opens | `5` |
| `MCP_CIRCUIT_BREAKER_TIMEOUT` | Recovery timeout in seconds | `60.0` |

#### MCP Context Forge Settings (Docker)

These are automatically passed from `.env` to MCP Context Forge via `docker-compose-infra.yml`:

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_TRUST_PROXY_AUTH` | Trust proxy-provided user identity | `true` |
| `MCP_PROXY_USER_HEADER` | Header containing user identity | `X-Authenticated-User` |
| `MCP_CLIENT_AUTH_ENABLED` | Require JWT auth for API calls | `false` |
| `MCP_AUTH_REQUIRED` | Require auth for admin UI | `false` |
| `MCP_LOG_LEVEL` | Logging level | `info` |

### Example `.env` Configuration

```bash
# ================================
# MCP CONTEXT FORGE INTEGRATION
# ================================
# RAG Modulo uses PROXY AUTHENTICATION - it acts as a trusted backend service
# that passes authenticated user identity via headers. No JWT token exchange needed.
# See: https://ibm.github.io/mcp-context-forge/manage/proxy/

# Step 1: Enable MCP Gateway (starts Redis + MCP Context Forge containers)
ENABLE_MCP_GATEWAY=true

# Step 2: Configure MCP Gateway connection
MCP_PORT=3001
MCP_GATEWAY_URL=http://localhost:3001

# Step 3: Enable proxy authentication (RECOMMENDED)
# MCP trusts the X-Authenticated-User header from RAG Modulo
MCP_TRUST_PROXY_AUTH=true
MCP_PROXY_USER_HEADER=X-Authenticated-User

# Step 4: Disable client JWT auth (we use proxy auth instead)
MCP_CLIENT_AUTH_ENABLED=false

# Step 5: Admin UI authentication (optional, for MCP web UI access)
MCP_AUTH_REQUIRED=false
MCP_ADMIN_EMAIL=admin@example.com
MCP_ADMIN_PASSWORD=change-me-in-production
MCP_JWT_SECRET=dev-jwt-secret-change-in-production

# To DISABLE MCP: Set ENABLE_MCP_GATEWAY=false
```

---

## Deployment

### Port Allocation

| Service | Port | Configurable | Description |
|---------|------|--------------|-------------|
| Frontend | 3000 | No | React development server |
| **MCP Context Forge** | **3001** | `MCP_PORT` | MCP gateway |
| Backend | 8000 | No | FastAPI server |
| Redis | 6379 | No | MCP session storage |
| Milvus | 19530 | No | Vector database |

### Local Development

MCP services (Redis + MCP Context Forge) are **optional** and only start when enabled via `ENABLE_MCP_GATEWAY=true`.

#### Quick Start

```bash
# 1. Configure .env
ENABLE_MCP_GATEWAY=true
MCP_TRUST_PROXY_AUTH=true
MCP_PROXY_USER_HEADER=X-Authenticated-User
MCP_CLIENT_AUTH_ENABLED=false

# 2. Start infrastructure (MCP services start automatically)
make local-dev-infra

# 3. Start backend
make local-dev-backend
```

#### Verify MCP is Running

```bash
# Check container status
docker ps | grep -E 'mcp-context-forge|redis'

# Check health endpoint
curl http://localhost:3001/health
# Expected: {"status":"healthy"}

# Check proxy auth environment
docker exec mcp-context-forge env | grep -E "TRUST_PROXY|PROXY_USER"
# Expected: TRUST_PROXY_AUTH=true, PROXY_USER_HEADER=X-Authenticated-User
```

### Docker Compose Configuration

The MCP services are configured in `docker-compose-infra.yml`:

```yaml
# MCP Context Forge Gateway
# Uses PROXY AUTHENTICATION - trusts X-Authenticated-User header from RAG Modulo
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
    # Admin UI auth (optional)
    AUTH_REQUIRED: ${MCP_AUTH_REQUIRED:-false}
    LOG_LEVEL: ${MCP_LOG_LEVEL:-info}
  healthcheck:
    test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:$${PORT}/health"]
  depends_on:
    redis:
      condition: service_healthy
  networks:
    - app-network
```

---

## Manual Testing

### 1. Health Check

```bash
curl http://localhost:3001/health
# Expected: {"status":"healthy"}
```

### 2. List Tools (with Proxy Auth Header)

```bash
curl -H "X-Authenticated-User: test@example.com" \
  http://localhost:3001/tools | jq .
```

### 3. Create a Test Tool

```bash
curl -X POST http://localhost:3001/tools \
  -H "X-Authenticated-User: admin@example.com" \
  -H "Content-Type: application/json" \
  -d '{
    "tool": {
      "name": "my_test_tool",
      "url": "https://httpbin.org/post",
      "description": "Test echo tool",
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
```

### 4. Invoke a Tool

**Important:** Use the `/mcp` endpoint with:

- `-L` flag to follow redirects
- `Accept: application/json` header

```bash
curl -L -X POST http://localhost:3001/mcp \
  -H "X-Authenticated-User: test@example.com" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "my-test-tool",
      "arguments": {"message": "Hello from RAG Modulo!"}
    }
  }' | jq .
```

**Expected Response:**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"json\": {\"message\": \"Hello from RAG Modulo!\"}...}"
      }
    ],
    "isError": false
  }
}
```

### 5. Test via RAG Modulo Backend API

```bash
# Check MCP health via backend
curl http://localhost:8000/api/v1/mcp/health | jq .

# List tools via backend
curl http://localhost:8000/api/v1/mcp/tools | jq .

# Get MCP metrics
curl http://localhost:8000/api/v1/mcp/metrics | jq .
```

### 6. Python Integration Test

```python
import asyncio
from rag_solution.services.mcp_gateway_client import ResilientMCPGatewayClient
from core.config import get_settings

async def test():
    client = ResilientMCPGatewayClient(get_settings())

    # Health check
    health = await client.check_health()
    print(f"Health: {health.healthy}")

    # List tools (with user identity for audit)
    tools = await client.list_tools(user_id="test@example.com")
    print(f"Tools: {tools.total_count}")

    # Invoke a tool
    result = await client.invoke_tool(
        "httpbin-echo",
        {"message": "Hello!"},
        user_id="test@example.com"
    )
    print(f"Result: {result.status.value}")

asyncio.run(test())
```

---

## API Endpoints Reference

### MCP Context Forge Endpoints

| Endpoint | Method | Headers Required | Description |
|----------|--------|------------------|-------------|
| `/health` | GET | None | Health check |
| `/tools` | GET | `X-Authenticated-User` | List all tools |
| `/tools` | POST | `X-Authenticated-User`, `Content-Type` | Create a tool |
| `/tools/{id}` | DELETE | `X-Authenticated-User` | Delete a tool |
| `/mcp` | POST | `X-Authenticated-User`, `Content-Type`, `Accept` | JSON-RPC endpoint (tool invocation) |

### RAG Modulo Backend Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/mcp/health` | GET | MCP gateway health status |
| `/api/v1/mcp/tools` | GET | List available MCP tools |
| `/api/v1/mcp/tools/{name}/invoke` | POST | Invoke a specific tool |
| `/api/v1/mcp/metrics` | GET | Client metrics |

---

## Circuit Breaker States

The resilient client uses a circuit breaker pattern:

| State | Description | Behavior |
|-------|-------------|----------|
| **CLOSED** | Normal operation | All requests pass through |
| **OPEN** | Failures exceeded threshold | Requests fail fast |
| **HALF_OPEN** | Recovery period | Single test request allowed |

### State Transitions

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

---

## Error Handling

The MCP integration is designed to be non-blocking:

| Scenario | Behavior |
|----------|----------|
| Gateway unreachable | Search continues, enrichment skipped |
| Tool invocation fails | Original result returned unchanged |
| Circuit breaker open | Requests fail fast, no network overhead |
| Timeout | Partial results may be used if available |

### Error Response Format

```json
{
  "tool_name": "failing_tool",
  "status": "error",
  "error": "Tool execution failed: connection timeout",
  "execution_time_ms": 30000.0
}
```

---

## Troubleshooting

### Common Issues

#### 1. Gateway Not Reachable

```bash
# Check container status
docker ps | grep mcp-context-forge

# Check logs
docker logs mcp-context-forge

# Verify health
curl http://localhost:3001/health
```

#### 2. Proxy Auth Not Working

```bash
# Verify environment variables in container
docker exec mcp-context-forge env | grep -E "TRUST_PROXY|PROXY_USER|CLIENT_AUTH"

# Expected:
# TRUST_PROXY_AUTH=true
# PROXY_USER_HEADER=X-Authenticated-User
# MCP_CLIENT_AUTH_ENABLED=false

# If not set, restart the container
docker compose -f docker-compose-infra.yml --profile mcp up -d mcp-context-forge
```

#### 3. Tool Invocation Returns "Method Invalid"

Use the correct endpoint and headers:

```bash
# WRONG - /rpc endpoint
curl -X POST http://localhost:3001/rpc ...

# CORRECT - /mcp endpoint with Accept header and redirect follow
curl -L -X POST http://localhost:3001/mcp \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -H "X-Authenticated-User: user@example.com" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{...}}'
```

#### 4. Missing Volume Directories

```bash
mkdir -p volumes/redis volumes/mcp_tools
```

#### 5. Port Conflict

MCP Context Forge uses port 3001 to avoid conflict with frontend (port 3000).

```bash
# Change port if needed
MCP_PORT=3002
MCP_GATEWAY_URL=http://localhost:3002
```

---

# RAG Modulo MCP Server

RAG Modulo can also act as an **MCP Server**, exposing its RAG capabilities to MCP clients
such as Claude Desktop, enabling LLMs to interact with your document collections.

## Overview

The MCP Server exposes:

- **Tools**: 4 tools for search, collections, and podcast generation (calls REST API)
- **Resources**: Collection documents, statistics, and user collections
- **Authentication**: SPIFFE JWT-SVID, Bearer tokens, API keys, trusted proxy

## Quick Start

### Running the Server

```bash
# Run with stdio transport (for Claude Desktop)
python -m mcp_server

# Run with SSE transport (for web clients)
python -m mcp_server --transport sse --port 8080

# Run with HTTP transport (for API clients)
python -m mcp_server --transport http --port 8080
```

### Claude Desktop Configuration

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "rag-modulo": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "/path/to/rag_modulo"
    }
  }
}
```

## Available Tools

The MCP server exposes four core tools that call the RAG Modulo REST API:

| Tool | Description | Required Permissions |
|------|-------------|---------------------|
| `rag_whoami` | Get current authenticated user info | None (uses auth headers) |
| `rag_list_collections` | List accessible collections | `rag:list` |
| `rag_search` | Search documents and generate answers | `rag:search` |
| `rag_generate_podcast` | Generate podcasts from content | `rag:podcast`, `rag:read` |

### Architecture Note

All tools forward requests to the FastAPI REST API, ensuring consistent behavior
with the web interface. Authentication headers are passed through to the API.

### Tool Examples

#### Whoami

```json
{
  "method": "tools/call",
  "params": {
    "name": "rag_whoami",
    "arguments": {}
  }
}
```

Response:

```json
{
  "user_id": "d1f93297-3e3c-42b0-8da7-09efde032c25",
  "username": "dev@example.com",
  "auth_method": "trusted_proxy",
  "permissions": ["rag:read", "rag:write", "rag:search", "rag:list", "rag:ingest"]
}
```

#### Search

```json
{
  "method": "tools/call",
  "params": {
    "name": "rag_search",
    "arguments": {
      "question": "What is machine learning?",
      "collection_id": "uuid-here",
      "user_id": "user-uuid",
      "max_results": 10
    }
  }
}
```

#### List Collections

```json
{
  "method": "tools/call",
  "params": {
    "name": "rag_list_collections",
    "arguments": {
      "user_id": "user-uuid"
    }
  }
}
```

#### Generate Podcast

```json
{
  "method": "tools/call",
  "params": {
    "name": "rag_generate_podcast",
    "arguments": {
      "collection_id": "uuid-here",
      "user_id": "user-uuid",
      "duration": "medium",
      "language": "en"
    }
  }
}
```

## Available Resources

| Resource URI | Description |
|-------------|-------------|
| `rag://collection/{id}/documents` | List documents in a collection |
| `rag://collection/{id}/stats` | Collection statistics |
| `rag://user/{id}/collections` | User's collections |

## Authentication

The MCP server supports multiple authentication methods:

### 1. SPIFFE JWT-SVID

For workload identity in agent environments:

```
X-SPIFFE-JWT: eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 2. Bearer Token

For user API access:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 3. API Key

For programmatic access:

```
X-API-Key: your-api-key
```

### 4. Trusted Proxy

For deployment behind an authenticated proxy:

```
X-Authenticated-User: user@example.com
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RAG_API_BASE_URL` | Base URL for RAG Modulo REST API | `http://localhost:8000` |
| `MCP_SERVER_TRANSPORT` | Transport type (stdio, sse, http) | `stdio` |
| `MCP_SERVER_PORT` | Port for SSE/HTTP transports | `8080` |
| `MCP_TIMEOUT` | Request timeout in seconds | `30.0` |
| `JWT_SECRET_KEY` | Secret for JWT validation | Required for Bearer auth |
| `MCP_API_KEY` | API key for programmatic access | Optional |

**Deployment Note:** When deploying in containers (Docker/Kubernetes), set `RAG_API_BASE_URL` to the internal service name:

- Docker Compose: `http://backend:8000`
- Kubernetes: `http://backend-service:8000`

## Permissions

Permissions follow the pattern `rag:{action}`:

| Permission | Description |
|-----------|-------------|
| `rag:search` | Perform semantic search queries |
| `rag:read` | Read document content and metadata |
| `rag:write` | Create, update, or delete documents |
| `rag:list` | List collections and resources |
| `rag:ingest` | Ingest documents into collections |
| `rag:podcast` | Generate podcasts from content |
| `rag:generate` | Use LLM generation features |
| `rag:admin` | Administrative operations |

## Error Handling

All tools return consistent error responses:

```json
{
  "error": "Collection not found",
  "error_type": "not_found",
  "details": {}
}
```

Error types:

- `authorization_error`: Authentication or permission failure
- `validation_error`: Invalid input parameters
- `not_found`: Requested resource does not exist
- `operation_error`: Operation failed during execution

## Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                          MCP Client                                 │
│           (Claude Desktop, Web Client, API Client)                  │
└───────────────────────────────┬────────────────────────────────────┘
                                │
                    stdio / SSE / HTTP
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                     RAG Modulo MCP Server                           │
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────────┐  │
│  │   MCPAuthenti-  │  │     FastMCP     │  │   MCPServerContext │  │
│  │     cator       │  │     Server      │  │     (Services)     │  │
│  └────────┬────────┘  └────────┬────────┘  └─────────┬──────────┘  │
│           │                    │                     │             │
│           └───────────┬────────┴─────────────────────┘             │
│                       │                                             │
│                       ▼                                             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                        MCP Tools                             │   │
│  │  ┌───────────────┐  ┌────────────────┐  ┌─────────────────┐ │   │
│  │  │  rag_search   │  │ rag_list_colls │  │   rag_ingest    │ │   │
│  │  └───────────────┘  └────────────────┘  └─────────────────┘ │   │
│  │  ┌───────────────┐  ┌────────────────┐  ┌─────────────────┐ │   │
│  │  │ rag_podcast   │  │ rag_questions  │  │  rag_get_doc    │ │   │
│  │  └───────────────┘  └────────────────┘  └─────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                     RAG Modulo Services                             │
│  SearchService, CollectionService, PodcastService, etc.           │
└────────────────────────────────────────────────────────────────────┘
```

## Testing with MCP Inspector

The MCP server can be tested using [MCP Inspector](https://github.com/modelcontextprotocol/inspector):

### SSE Transport

```bash
# Start the MCP server with SSE transport
cd backend
poetry run python -m mcp_server --transport sse --port 8080 --log-level DEBUG

# In MCP Inspector, connect to:
# URL: http://localhost:8080/sse
# Headers:
#   X-Authenticated-User: dev@example.com
```

### Testing Authentication

1. **Connect** to `http://localhost:8080/sse` with the `X-Authenticated-User` header
2. **Call** `rag_whoami` to verify authentication
3. **Call** `rag_list_collections` to see the user's collections

### Header Capture Middleware

The MCP server uses middleware to capture authentication headers from SSE connections
and make them available to tool handlers. Headers are stored in:

1. **Context variables**: For synchronous requests
2. **Session storage**: Keyed by session ID for async SSE tool calls
3. **Global storage**: Fallback for single-user testing scenarios

Captured headers:

- `Authorization`: Bearer tokens
- `X-API-Key`: API key authentication
- `X-Authenticated-User`: Trusted proxy user identity
- `X-SPIFFE-JWT`: SPIFFE JWT-SVID for workload identity

---

## Development

### Module Structure

```
backend/mcp_server/
├── __init__.py         # Package exports
├── __main__.py         # CLI entry point
├── server.py           # FastMCP server creation and lifecycle
├── tools.py            # MCP tool implementations
├── resources.py        # MCP resource implementations
├── auth.py             # Authentication handlers
├── middleware.py       # Header capture middleware for SSE
├── types.py            # Type definitions and utilities
└── permissions.py      # Permission constants
```

### Running Tests

```bash
# Unit tests for MCP server
poetry run pytest tests/unit/mcp_server/ -v

# Integration tests
poetry run pytest tests/integration/test_mcp_server.py -v
```

---

## Related Documentation

- [MCP Context Forge Documentation](https://ibm.github.io/mcp-context-forge/)
- [Proxy Authentication Guide](https://ibm.github.io/mcp-context-forge/manage/proxy/)
- [Search & Retrieval](search-retrieval.md) - Core search functionality
- [Chain of Thought](chain-of-thought/index.md) - Advanced reasoning
- [LLM Integration](llm-integration.md) - Provider configuration
- [FastMCP Documentation](https://github.com/anthropics/anthropic-sdk-python) - MCP SDK
