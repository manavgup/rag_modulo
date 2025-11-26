# MCP Context Forge Integration with RAG Modulo

**Date**: November 2025
**Status**: Integration Design Proposal
**Version**: 1.0
**Parent Design**: [Agent and MCP Support Architecture](./agent-mcp-architecture.md)

## Executive Summary

This document proposes integrating IBM's **MCP Context Forge** as the central gateway for RAG Modulo's agent and MCP ecosystem. Instead of building a custom MCP client from scratch, we leverage Context Forge's production-ready federation, protocol translation, security, and admin UI capabilities.

## Why MCP Context Forge?

### Alignment with RAG Modulo's Agent Architecture

The original agent-mcp-architecture.md design proposed:

- Custom `MCPClient` for communicating with MCP servers
- Custom registry for agent discovery
- Custom protocol handling
- Custom authentication and rate limiting

**MCP Context Forge provides all of this out-of-the-box**:

| RAG Modulo Need | Context Forge Solution |
|-----------------|------------------------|
| MCP Client | Built-in protocol translation (stdio, SSE, WebSocket, HTTP) |
| Agent Registry | Unified registry of tools, resources, and prompts |
| Multi-protocol support | Virtualizes REST/gRPC as MCP servers |
| Authentication | Bearer token auth with JWT + RBAC |
| Rate limiting | Built-in with Redis backing |
| Observability | OpenTelemetry integration (Phoenix, Jaeger, Zipkin) |
| Admin UI | HTMX/Alpine.js management interface |
| Federation | Redis-backed distributed deployment |

### Benefits

1. **Reduced Development Time**: 2 weeks → 3-4 days (80% reduction)
2. **Production-Ready**: Battle-tested gateway with 400+ tests
3. **Extensibility**: Supports non-MCP services (REST, gRPC) as virtual MCP servers
4. **Centralized Management**: Single admin UI for all agents/tools
5. **Enterprise Features**: RBAC, team management, audit logging
6. **Scalability**: Redis federation for distributed deployments

## Architecture Integration

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
│  │          AgentService (Enhanced)                     │  │
│  │  - Agent config CRUD                                 │  │
│  │  - Collection-agent association                      │  │
│  │  - Pipeline execution orchestration                  │  │
│  └───────────────────┬──────────────────────────────────┘  │
│                      │                                      │
│                      ▼                                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │      ContextForgeClient (New)                        │  │
│  │  - Bearer token auth                                 │  │
│  │  - Tool invocation via SSE/HTTP                      │  │
│  │  - Resource fetching                                 │  │
│  │  - Gateway management (create virtual servers)       │  │
│  └───────────────────┬──────────────────────────────────┘  │
└────────────────────────┼────────────────────────────────────┘
                         │
                         ▼ (HTTP/SSE/WebSocket)
┌─────────────────────────────────────────────────────────────┐
│              MCP Context Forge Gateway                      │
│                    (IBM OSS Project)                        │
│                                                             │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │ Protocol       │  │ Authentication │  │  Federation  │  │
│  │ Translation    │  │ & RBAC         │  │  (Redis)     │  │
│  └────────────────┘  └────────────────┘  └──────────────┘  │
│                                                             │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │ Tool Registry  │  │ Rate Limiting  │  │  Observability│ │
│  │ & Discovery    │  │ & Retries      │  │  (OpenTelemetry)│
│  └────────────────┘  └────────────────┘  └──────────────┘  │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐│
│  │         Admin UI (HTMX + Alpine.js)                    ││
│  │  - Manage gateways, tools, servers                     ││
│  │  - Monitor agent execution                             ││
│  │  - Team/RBAC management                                ││
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

### Key Components

#### 1. ContextForgeClient (New Component)

Replaces the custom `MCPClient` from the original design:

```python
# backend/rag_solution/mcp/context_forge_client.py
import httpx
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ContextForgeConfig(BaseModel):
    """Configuration for Context Forge gateway"""
    gateway_url: str
    api_token: str  # JWT bearer token
    timeout: int = 30
    max_retries: int = 3


class ToolInvocation(BaseModel):
    """Request to invoke a tool"""
    tool_name: str
    arguments: Dict[str, Any]
    gateway_id: Optional[str] = None  # Virtual gateway to use


class ToolResponse(BaseModel):
    """Response from tool invocation"""
    success: bool
    result: Dict[str, Any]
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}


class ContextForgeClient:
    """
    Client for IBM MCP Context Forge Gateway

    Provides unified access to MCP tools, resources, and prompts
    through Context Forge's federation layer.
    """

    def __init__(self, config: ContextForgeConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.gateway_url,
            headers={"Authorization": f"Bearer {config.api_token}"},
            timeout=config.timeout
        )

    async def list_gateways(self) -> List[Dict[str, Any]]:
        """List available virtual gateways"""
        response = await self.client.get("/api/v1/gateways")
        response.raise_for_status()
        return response.json()

    async def list_tools(self, gateway_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available tools

        Args:
            gateway_id: Optional specific virtual gateway to query

        Returns:
            List of tool definitions with schemas
        """
        params = {"gateway_id": gateway_id} if gateway_id else {}
        response = await self.client.get("/api/v1/tools", params=params)
        response.raise_for_status()
        return response.json()["tools"]

    async def invoke_tool(self, invocation: ToolInvocation) -> ToolResponse:
        """
        Invoke an MCP tool through Context Forge

        Args:
            invocation: Tool name, arguments, and optional gateway

        Returns:
            ToolResponse with result or error
        """
        try:
            # Context Forge handles protocol translation automatically
            response = await self.client.post(
                f"/api/v1/tools/{invocation.tool_name}/invoke",
                json={
                    "arguments": invocation.arguments,
                    "gateway_id": invocation.gateway_id
                }
            )
            response.raise_for_status()

            data = response.json()
            return ToolResponse(
                success=True,
                result=data.get("result", {}),
                metadata=data.get("metadata", {})
            )

        except httpx.HTTPStatusError as e:
            return ToolResponse(
                success=False,
                result={},
                error=f"HTTP {e.response.status_code}: {e.response.text}"
            )

        except Exception as e:
            return ToolResponse(
                success=False,
                result={},
                error=str(e)
            )

    async def get_resource(
        self,
        resource_uri: str,
        gateway_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch an MCP resource

        Args:
            resource_uri: URI of the resource to fetch
            gateway_id: Optional specific gateway to use

        Returns:
            Resource content
        """
        params = {
            "uri": resource_uri,
            "gateway_id": gateway_id
        } if gateway_id else {"uri": resource_uri}

        response = await self.client.get("/api/v1/resources", params=params)
        response.raise_for_status()
        return response.json()

    async def get_prompt(
        self,
        prompt_name: str,
        gateway_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get MCP prompt template

        Args:
            prompt_name: Name of the prompt template
            gateway_id: Optional specific gateway to use

        Returns:
            Prompt template
        """
        params = {"gateway_id": gateway_id} if gateway_id else {}
        response = await self.client.get(
            f"/api/v1/prompts/{prompt_name}",
            params=params
        )
        response.raise_for_status()
        return response.json()

    async def create_virtual_gateway(
        self,
        name: str,
        tool_ids: List[str],
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a virtual gateway bundling specific tools

        This enables creating custom agent bundles for collections.

        Args:
            name: Name for the virtual gateway
            tool_ids: List of tool IDs to include
            description: Optional description

        Returns:
            Virtual gateway details
        """
        response = await self.client.post(
            "/api/v1/gateways",
            json={
                "name": name,
                "tool_ids": tool_ids,
                "description": description
            }
        )
        response.raise_for_status()
        return response.json()

    async def register_external_server(
        self,
        name: str,
        server_type: str,  # "mcp", "rest", "grpc"
        endpoint: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Register an external MCP server or REST/gRPC service

        Context Forge will virtualize non-MCP services as MCP servers.

        Args:
            name: Server name
            server_type: Type of server (mcp, rest, grpc)
            endpoint: Server endpoint URL
            config: Server-specific configuration

        Returns:
            Registered server details
        """
        response = await self.client.post(
            "/api/v1/servers",
            json={
                "name": name,
                "type": server_type,
                "endpoint": endpoint,
                "config": config
            }
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
```

#### 2. Enhanced AgentService

Update the `AgentService` to use `ContextForgeClient` instead of custom `MCPClient`:

```python
# backend/rag_solution/services/agent_service.py (updated)
from rag_solution.mcp.context_forge_client import ContextForgeClient, ToolInvocation


class AgentService:
    """Service for managing and executing agents"""

    def __init__(
        self,
        db: AsyncSession,
        registry: AgentRegistry,
        context_forge: ContextForgeClient  # NEW
    ):
        self.db = db
        self.registry = registry
        self.context_forge = context_forge  # Replace custom MCPClient

    async def create_collection_virtual_gateway(
        self,
        collection_id: UUID,
        user_id: UUID
    ) -> str:
        """
        Create a virtual gateway in Context Forge for a collection

        Bundles all agents associated with the collection into
        a single gateway for efficient execution.

        Returns:
            Gateway ID
        """
        # Get collection's agents
        agent_configs = await self._get_collection_agents(
            collection_id=collection_id,
            enabled=True
        )

        # Map agents to Context Forge tool IDs
        tool_ids = []
        for config in agent_configs:
            # Agents can specify their Context Forge tool mapping
            tool_id = config.config.get("context_forge_tool_id")
            if tool_id:
                tool_ids.append(tool_id)

        # Create virtual gateway
        gateway = await self.context_forge.create_virtual_gateway(
            name=f"collection_{collection_id}",
            tool_ids=tool_ids,
            description=f"Virtual gateway for collection {collection_id}"
        )

        return gateway["id"]

    async def execute_agents(
        self,
        context: AgentContext,
        trigger_stage: str
    ) -> List[AgentResult]:
        """Execute all enabled agents for a collection at given stage"""

        # Get agent configs for collection
        agent_configs = await self._get_collection_agents(
            collection_id=context.collection_id,
            trigger_stage=trigger_stage,
            enabled=True
        )

        # Sort by priority
        agent_configs.sort(key=lambda x: x.priority)

        results = []
        for config in agent_configs:
            try:
                # Check if agent is MCP-based
                if config.config.get("type") == "mcp":
                    result = await self._execute_mcp_agent(config, context)
                else:
                    # Execute built-in agent
                    agent = self.registry.get_agent(
                        agent_id=config.agent_id,
                        config=config.config
                    )
                    result = await agent.execute(
                        context=context,
                        input_data=self._prepare_input(context, config)
                    )

                results.append(result)

                # Update context for next agent
                if not context.previous_agent_results:
                    context.previous_agent_results = []
                context.previous_agent_results.append(result)

            except Exception as e:
                results.append(AgentResult(
                    agent_id=config.agent_id,
                    success=False,
                    data={},
                    metadata={},
                    errors=[str(e)]
                ))

        return results

    async def _execute_mcp_agent(
        self,
        config: AgentConfig,
        context: AgentContext
    ) -> AgentResult:
        """
        Execute an MCP-based agent via Context Forge

        Args:
            config: Agent configuration with Context Forge tool mapping
            context: Execution context

        Returns:
            AgentResult
        """
        tool_name = config.config.get("context_forge_tool_id")
        gateway_id = config.config.get("gateway_id")

        # Prepare tool arguments from context
        arguments = self._map_context_to_tool_args(context, config)

        # Invoke tool via Context Forge
        invocation = ToolInvocation(
            tool_name=tool_name,
            arguments=arguments,
            gateway_id=gateway_id
        )

        response = await self.context_forge.invoke_tool(invocation)

        return AgentResult(
            agent_id=config.agent_id,
            success=response.success,
            data=response.result,
            metadata=response.metadata,
            errors=[response.error] if response.error else None
        )

    def _map_context_to_tool_args(
        self,
        context: AgentContext,
        config: AgentConfig
    ) -> Dict[str, Any]:
        """
        Map AgentContext to MCP tool arguments

        Uses config.config["argument_mapping"] to transform context
        into tool-specific arguments.
        """
        mapping = config.config.get("argument_mapping", {})
        args = {}

        for tool_arg, context_field in mapping.items():
            if context_field == "query":
                args[tool_arg] = context.query
            elif context_field == "documents":
                args[tool_arg] = context.retrieved_documents
            elif context_field == "conversation_history":
                args[tool_arg] = context.conversation_history
            # Add more mappings as needed

        return args
```

#### 3. Updated Database Models

Add Context Forge-specific fields to `AgentConfig`:

```python
# backend/rag_solution/models/agent.py (updated)
class AgentConfig(Base):
    """User-configured agent instance"""

    __tablename__ = "agent_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    agent_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)

    # Configuration now includes Context Forge integration
    config = Column(JSON, nullable=False)
    # Example config structure:
    # {
    #   "type": "mcp",  # or "builtin"
    #   "context_forge_tool_id": "powerpoint_generator",
    #   "gateway_id": "collection_abc123",
    #   "argument_mapping": {
    #     "query": "query",
    #     "documents": "documents",
    #     "template": "config.template"
    #   },
    #   "settings": { ... }
    # }

    enabled = Column(Boolean, default=True)
    trigger_stage = Column(String)
    priority = Column(Integer, default=0)

    # Relationships
    collections = relationship(
        "Collection",
        secondary=collection_agents,
        back_populates="agents"
    )
    user = relationship("User", back_populates="agent_configs")
```

#### 4. API Endpoints for Context Forge Integration

Add endpoints for managing Context Forge gateways and servers:

```python
# backend/rag_solution/router/agent_router.py (updated)
from rag_solution.mcp.context_forge_client import ContextForgeClient


@router.post("/context-forge/servers", response_model=Dict[str, Any])
async def register_mcp_server(
    server_config: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    context_forge: ContextForgeClient = Depends(get_context_forge_client)
):
    """
    Register an external MCP server or REST/gRPC service with Context Forge

    Example request body:
    {
      "name": "PowerPoint Generator",
      "server_type": "mcp",
      "endpoint": "http://ppt-generator:8080",
      "config": {
        "protocol": "sse",
        "auth_token": "..."
      }
    }
    """
    server = await context_forge.register_external_server(
        name=server_config["name"],
        server_type=server_config["server_type"],
        endpoint=server_config["endpoint"],
        config=server_config.get("config", {})
    )
    return server


@router.get("/context-forge/tools", response_model=List[Dict[str, Any]])
async def list_context_forge_tools(
    gateway_id: Optional[str] = None,
    context_forge: ContextForgeClient = Depends(get_context_forge_client)
):
    """
    List all tools available in Context Forge

    Optionally filter by virtual gateway ID
    """
    tools = await context_forge.list_tools(gateway_id=gateway_id)
    return tools


@router.post("/collections/{collection_id}/gateway")
async def create_collection_gateway(
    collection_id: UUID,
    current_user: User = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service)
):
    """
    Create a virtual gateway in Context Forge for this collection

    Bundles all collection agents into a single gateway for efficient execution.
    """
    gateway_id = await agent_service.create_collection_virtual_gateway(
        collection_id=collection_id,
        user_id=current_user.id
    )
    return {"gateway_id": gateway_id, "collection_id": collection_id}
```

## Deployment Architecture

### Docker Compose Setup (Development)

```yaml
# docker-compose.yml (updated)
version: '3.8'

services:
  # Existing RAG Modulo services
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile.backend
    environment:
      - CONTEXT_FORGE_URL=http://mcp-gateway:8000
      - CONTEXT_FORGE_TOKEN=${CONTEXT_FORGE_TOKEN}
    depends_on:
      - postgres
      - milvus
      - mcp-gateway

  frontend:
    build:
      context: frontend
      dockerfile: Dockerfile.frontend
    depends_on:
      - backend

  # MCP Context Forge Gateway
  mcp-gateway:
    image: ghcr.io/ibm/mcp-context-forge:latest
    ports:
      - "8001:8000"  # Gateway API
      - "8002:8001"  # Admin UI
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@postgres:5432/mcp_gateway
      - JWT_SECRET=${JWT_SECRET}
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318
    depends_on:
      - redis
      - postgres
    volumes:
      - ./config/mcp-gateway:/app/config

  # Redis for Context Forge federation
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # OpenTelemetry Collector (optional)
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # Jaeger UI
      - "4318:4318"    # OTLP HTTP

  # Example MCP Server: PowerPoint Generator
  ppt-generator-mcp:
    build:
      context: ./agents/ppt-generator
      dockerfile: Dockerfile
    environment:
      - MCP_SERVER_PORT=8080
    ports:
      - "8080:8080"
```

### Kubernetes Deployment (Production)

```yaml
# deployment/helm/rag-modulo/templates/mcp-gateway-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-gateway
  namespace: {{ .Values.namespace }}
spec:
  replicas: {{ .Values.mcpGateway.replicas }}
  selector:
    matchLabels:
      app: mcp-gateway
  template:
    metadata:
      labels:
        app: mcp-gateway
    spec:
      containers:
      - name: gateway
        image: {{ .Values.mcpGateway.image.repository }}:{{ .Values.mcpGateway.image.tag }}
        ports:
        - containerPort: 8000
          name: api
        - containerPort: 8001
          name: admin
        env:
        - name: REDIS_URL
          value: "redis://{{ .Release.Name }}-redis:6379"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: mcp-gateway-secrets
              key: database-url
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: mcp-gateway-secrets
              key: jwt-secret
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          value: "http://jaeger-collector:4318"
        resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: mcp-gateway
  namespace: {{ .Values.namespace }}
spec:
  selector:
    app: mcp-gateway
  ports:
  - name: api
    port: 8000
    targetPort: 8000
  - name: admin
    port: 8001
    targetPort: 8001
  type: ClusterIP
```

## Configuration

### Environment Variables

Add to `.env.example`:

```bash
# MCP Context Forge Configuration
CONTEXT_FORGE_URL=http://localhost:8001
CONTEXT_FORGE_TOKEN=your_jwt_token_here
CONTEXT_FORGE_REDIS_URL=redis://localhost:6379
CONTEXT_FORGE_DB_URL=postgresql://postgres:password@localhost:5432/mcp_gateway

# OpenTelemetry (optional)
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_SERVICE_NAME=rag-modulo-agents
```

### Application Configuration

```python
# backend/core/config.py (updated)
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ... existing settings ...

    # MCP Context Forge
    context_forge_url: str = "http://localhost:8001"
    context_forge_token: str
    context_forge_timeout: int = 30
    context_forge_max_retries: int = 3

    class Config:
        env_file = ".env"


settings = Settings()
```

## Integration with Existing Agents

### Example: PowerPoint Generator via Context Forge

Instead of building a custom Python agent, we deploy a standalone MCP server and register it with Context Forge:

#### 1. MCP Server (Python)

```python
# agents/ppt-generator/server.py
from mcp import Server, Tool, ToolParameter
from pptx import Presentation
import base64
from io import BytesIO


server = Server("powerpoint-generator")


@server.tool(
    name="generate_powerpoint",
    description="Generate PowerPoint presentation from documents",
    parameters=[
        ToolParameter(
            name="title",
            type="string",
            description="Presentation title"
        ),
        ToolParameter(
            name="documents",
            type="array",
            description="List of documents to include"
        ),
        ToolParameter(
            name="max_slides",
            type="integer",
            description="Maximum number of slides",
            default=10
        )
    ]
)
async def generate_powerpoint(title: str, documents: list, max_slides: int = 10):
    """Generate PowerPoint from documents"""
    prs = Presentation()

    # Title slide
    title_slide = prs.slides.add_slide(prs.slide_layouts[0])
    title_slide.shapes.title.text = title

    # Content slides
    for doc in documents[:max_slides]:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = doc.get("title", "")
        slide.shapes.placeholders[1].text = doc.get("content", "")

    # Encode as base64
    ppt_buffer = BytesIO()
    prs.save(ppt_buffer)
    ppt_buffer.seek(0)
    ppt_base64 = base64.b64encode(ppt_buffer.read()).decode('utf-8')

    return {
        "presentation": ppt_base64,
        "format": "pptx",
        "filename": f"{title}.pptx",
        "slides": len(prs.slides)
    }


if __name__ == "__main__":
    server.run()
```

#### 2. Register with Context Forge

```bash
# Register PowerPoint Generator MCP server
curl -X POST http://localhost:8001/api/v1/servers \
  -H "Authorization: Bearer $CONTEXT_FORGE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "PowerPoint Generator",
    "type": "mcp",
    "endpoint": "http://ppt-generator-mcp:8080",
    "config": {
      "protocol": "stdio",
      "transport": "sse"
    }
  }'
```

#### 3. Create Agent Configuration in RAG Modulo

```python
# Via RAG Modulo API
POST /api/v1/agents/configs
{
  "agent_id": "ppt_generator",
  "name": "PowerPoint Generator",
  "config": {
    "type": "mcp",
    "context_forge_tool_id": "generate_powerpoint",
    "argument_mapping": {
      "title": "query",
      "documents": "documents",
      "max_slides": "config.max_slides"
    },
    "settings": {
      "max_slides": 15
    }
  },
  "trigger_stage": "response",
  "priority": 10
}
```

#### 4. Associate with Collection

```python
POST /api/v1/agents/collections/{collection_id}/agents
{
  "collection_id": "abc123...",
  "agent_config_id": "xyz789..."
}
```

Now when users search in this collection, the PowerPoint Generator agent will automatically execute during the "response" stage, creating a presentation from the search results.

## Admin UI Integration

Context Forge provides an admin UI at `http://localhost:8002` where users can:

1. **Manage Gateways**: View/create/delete virtual gateways
2. **Monitor Tools**: See all available MCP tools across servers
3. **View Execution Logs**: Real-time monitoring of agent invocations
4. **Team Management**: RBAC for agent access control
5. **Observability**: OpenTelemetry traces for debugging

### Embed Admin UI in RAG Modulo Frontend

```typescript
// frontend/src/components/agents/ContextForgeAdmin.tsx
import React from 'react';

export const ContextForgeAdmin: React.FC = () => {
  const contextForgeUrl = process.env.REACT_APP_CONTEXT_FORGE_ADMIN_URL;

  return (
    <div className="context-forge-admin">
      <h2>Agent Gateway Administration</h2>
      <iframe
        src={contextForgeUrl}
        title="MCP Context Forge Admin"
        style={{
          width: '100%',
          height: '800px',
          border: 'none'
        }}
      />
    </div>
  );
};
```

## Migration from Custom MCPClient

### Phase 1: Deploy Context Forge (Week 1)

1. **Day 1-2**: Deploy Context Forge as separate service
   - Docker Compose for dev
   - Helm chart for staging/production
2. **Day 3-4**: Configure authentication and RBAC
3. **Day 5**: Register initial MCP servers (PowerPoint, Translation)

### Phase 2: Update RAG Modulo Backend (Week 1)

1. **Day 1-2**: Implement `ContextForgeClient`
2. **Day 3-4**: Update `AgentService` to use Context Forge
3. **Day 5**: Migration script for existing agent configs

### Phase 3: Testing and Validation (Week 2)

1. **Day 1-2**: Integration tests with Context Forge
2. **Day 3-4**: End-to-end agent execution tests
3. **Day 5**: Performance testing and optimization

### Phase 4: Frontend and Documentation (Week 2)

1. **Day 1-2**: Embed Context Forge admin UI
2. **Day 3-4**: Update API documentation
3. **Day 5**: User guides and examples

## Benefits Summary

| Aspect | Custom MCPClient | With Context Forge |
|--------|------------------|-------------------|
| **Development Time** | 2 weeks | 3-4 days |
| **Protocol Support** | stdio, HTTP | stdio, SSE, WebSocket, HTTP, gRPC |
| **Federation** | None | Redis-backed distributed |
| **Admin UI** | Build from scratch | Production-ready HTMX/Alpine.js |
| **Authentication** | Custom JWT | Built-in RBAC + teams |
| **Observability** | Custom logging | OpenTelemetry integration |
| **Rate Limiting** | Custom | Built-in Redis-backed |
| **Retries** | Manual | Automatic with circuit breaker |
| **Non-MCP Services** | Not supported | Virtualized as MCP servers |
| **Testing** | Write from scratch | 400+ existing tests |

## Security Considerations

1. **Network Isolation**: Context Forge runs in same VPC as RAG Modulo backend
2. **JWT Authentication**: Secure token-based auth for all API calls
3. **RBAC**: Team-based access control for sensitive tools
4. **Secrets Management**: Never expose MCP server credentials; Context Forge handles auth
5. **Audit Logging**: All tool invocations logged via OpenTelemetry

## Performance Considerations

1. **Redis Caching**: Context Forge caches tool definitions and gateway configs
2. **Federation**: Distribute load across multiple Context Forge instances
3. **Async Execution**: Non-blocking tool invocations via SSE
4. **Connection Pooling**: HTTP client connection reuse
5. **Timeout Management**: Configurable timeouts per tool

## Monitoring and Observability

### OpenTelemetry Integration

```python
# backend/core/telemetry.py (new)
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_telemetry():
    """Configure OpenTelemetry for agent execution tracing"""
    provider = TracerProvider()

    # Export to same OTLP endpoint as Context Forge
    otlp_exporter = OTLPSpanExporter(
        endpoint=settings.otel_exporter_otlp_endpoint
    )

    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    trace.set_tracer_provider(provider)


# Add tracing to AgentService
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


class AgentService:
    async def execute_agents(self, context: AgentContext, trigger_stage: str):
        with tracer.start_as_current_span("execute_agents") as span:
            span.set_attribute("collection_id", str(context.collection_id))
            span.set_attribute("trigger_stage", trigger_stage)

            # ... existing logic ...

            span.set_attribute("agents_executed", len(results))
            return results
```

### Grafana Dashboards

Context Forge provides pre-built Grafana dashboards for:

- Tool invocation rates
- Error rates by tool
- Latency percentiles (p50, p95, p99)
- Gateway health and availability

## Conclusion

Integrating IBM's MCP Context Forge with RAG Modulo provides a production-ready, enterprise-grade agent execution platform with minimal development effort. By leveraging Context Forge's federation, protocol translation, security, and observability features, we can focus on building powerful agents rather than infrastructure.

**Key Advantages**:

- 80% reduction in development time (2 weeks → 3-4 days)
- Production-ready gateway with 400+ tests
- Support for non-MCP services (REST, gRPC) via virtualization
- Enterprise features: RBAC, teams, audit logging, observability
- Scalable architecture with Redis federation

**Recommended Next Steps**:

1. Deploy Context Forge in development environment
2. Implement `ContextForgeClient` wrapper
3. Migrate one example agent (PowerPoint Generator)
4. Validate integration with end-to-end tests
5. Update documentation and rollout to production

---

**References**:

- [MCP Context Forge GitHub](https://github.com/IBM/mcp-context-forge)
- [RAG Modulo Agent Architecture](./agent-mcp-architecture.md)
- [Anthropic Model Context Protocol](https://modelcontextprotocol.io/)
