# RAG Modulo MCP Server Architecture

**Date**: November 2025
**Status**: Architecture Design
**Version**: 1.0
**Related Documents**: [MCP Integration Architecture](./mcp-integration-architecture.md), [SPIRE Integration Architecture](./spire-integration-architecture.md)

## Overview

This document describes the architecture for exposing RAG Modulo's capabilities as an MCP
(Model Context Protocol) server. This enables external AI tools like Claude Desktop, workflow
automation systems, and other MCP clients to interact with RAG Modulo's search, ingestion,
and content generation features.

## Use Cases

### External MCP Clients

| Client | Use Case |
|--------|----------|
| **Claude Desktop** | User asks Claude to search their company documents |
| **n8n/Zapier** | Workflow automation: ingest email attachments, search on triggers |
| **Custom AI Bots** | Slack/Teams bots that query document collections |
| **Agent Frameworks** | LangChain, AutoGPT agents using RAG Modulo as knowledge source |

### Example Scenarios

**Scenario 1: Claude Desktop**

```
User in Claude Desktop:
"Search my company's financial documents for Q4 projections"

Claude Desktop:
1. Discovers rag_search tool via MCP
2. Calls rag_search(collection_id="...", query="Q4 projections")
3. Receives answer + sources from RAG Modulo
4. Presents to user with citations
```

**Scenario 2: Workflow Automation**

```
Trigger: New email received with attachment
Action 1: Extract attachment, upload to temp storage
Action 2: Call rag_ingest to add document to collection
Action 3: Call rag_search to check for related content
Action 4: Send Slack notification with summary
```

**Scenario 3: Multi-Agent System**

```
Orchestrator Agent:
1. Calls rag_list_collections to find relevant collection
2. Calls rag_search to gather information
3. Calls rag_generate_podcast to create audio summary
4. Combines results for final user response
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL MCP CLIENTS                                 │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │  Claude Desktop │  │  Custom AI Bot  │  │  Workflow Tool  │              │
│  │                 │  │                 │  │  (n8n, Zapier)  │              │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘              │
│           │                    │                    │                        │
│           └────────────────────┼────────────────────┘                        │
│                                │                                             │
│                                ▼ MCP Protocol (stdio/SSE/HTTP)               │
└─────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    RAG Modulo Native MCP Server                              │
│                    backend/rag_solution/mcp_server/                          │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                           Tools                                         ││
│  │                                                                         ││
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐           ││
│  │  │   rag_search    │ │   rag_ingest    │ │ rag_list_colls  │           ││
│  │  └─────────────────┘ └─────────────────┘ └─────────────────┘           ││
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐           ││
│  │  │ rag_gen_podcast │ │ rag_smart_q's   │ │ rag_get_doc     │           ││
│  │  └─────────────────┘ └─────────────────┘ └─────────────────┘           ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                          Resources                                      ││
│  │                                                                         ││
│  │  rag://collection/{id}/documents    - Document metadata                 ││
│  │  rag://collection/{id}/stats        - Collection statistics             ││
│  │  rag://search/{query}/results       - Cached search results             ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                       Authentication                                    ││
│  │                                                                         ││
│  │  • SPIFFE JWT-SVID (agent-to-agent) ◀── PR #695                        ││
│  │  • Bearer token (user-delegated access)                                ││
│  │  • API key (service accounts)                                          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                  RAG Modulo Backend Services                                 │
│         (SearchService, DocumentService, PodcastService, etc.)              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Exposed Tools

### rag_search

Search documents in a RAG Modulo collection.

```yaml
name: rag_search
description: Search documents in a RAG Modulo collection using semantic search with optional Chain-of-Thought reasoning

parameters:
  collection_id:
    type: string
    description: UUID of the collection to search
    required: true
  query:
    type: string
    description: Natural language search query
    required: true
  top_k:
    type: integer
    description: Number of results to return
    required: false
    default: 5
  use_cot:
    type: boolean
    description: Enable Chain-of-Thought reasoning for complex queries
    required: false
    default: false

returns:
  answer:
    type: string
    description: Synthesized answer from retrieved documents
  sources:
    type: array
    description: List of source documents with titles and relevance scores
  cot_steps:
    type: array
    description: Reasoning steps (if use_cot=true)
```

### rag_ingest

Add documents to a collection.

```yaml
name: rag_ingest
description: Add one or more documents to a RAG Modulo collection

parameters:
  collection_id:
    type: string
    description: UUID of the target collection
    required: true
  documents:
    type: array
    description: List of documents to ingest
    required: true
    items:
      type: object
      properties:
        title:
          type: string
          description: Document title
        content:
          type: string
          description: Document content (text)
        metadata:
          type: object
          description: Optional metadata (author, date, tags, etc.)

returns:
  ingested_count:
    type: integer
    description: Number of documents successfully ingested
  document_ids:
    type: array
    description: UUIDs of ingested documents
  errors:
    type: array
    description: Any errors encountered during ingestion
```

### rag_list_collections

List collections accessible to the authenticated agent/user.

```yaml
name: rag_list_collections
description: List document collections the authenticated agent can access

parameters:
  include_stats:
    type: boolean
    description: Include document counts and last updated timestamps
    required: false
    default: false

returns:
  collections:
    type: array
    items:
      type: object
      properties:
        id:
          type: string
          description: Collection UUID
        name:
          type: string
          description: Collection name
        description:
          type: string
          description: Collection description
        document_count:
          type: integer
          description: Number of documents (if include_stats=true)
        last_updated:
          type: string
          description: ISO timestamp of last update (if include_stats=true)
```

### rag_generate_podcast

Generate an audio podcast from collection content.

```yaml
name: rag_generate_podcast
description: Generate an AI-powered audio podcast from collection documents

parameters:
  collection_id:
    type: string
    description: UUID of the source collection
    required: true
  topic:
    type: string
    description: Focus topic for the podcast (optional - uses all content if not specified)
    required: false
  duration_minutes:
    type: integer
    description: Target podcast duration in minutes
    required: false
    default: 5
    minimum: 1
    maximum: 30

returns:
  audio_url:
    type: string
    description: URL to download the generated audio file
  transcript:
    type: string
    description: Full text transcript of the podcast
  duration:
    type: number
    description: Actual duration in seconds
```

### rag_smart_questions

Get AI-suggested follow-up questions based on context.

```yaml
name: rag_smart_questions
description: Generate intelligent follow-up questions based on collection content and conversation context

parameters:
  collection_id:
    type: string
    description: UUID of the collection
    required: true
  context:
    type: string
    description: Current conversation context or recent query
    required: false
  count:
    type: integer
    description: Number of questions to generate
    required: false
    default: 3
    minimum: 1
    maximum: 10

returns:
  questions:
    type: array
    items:
      type: string
    description: List of suggested follow-up questions
```

### rag_get_document

Retrieve a specific document's content and metadata.

```yaml
name: rag_get_document
description: Retrieve full content and metadata for a specific document

parameters:
  document_id:
    type: string
    description: UUID of the document
    required: true

returns:
  id:
    type: string
    description: Document UUID
  title:
    type: string
    description: Document title
  content:
    type: string
    description: Full document text content
  metadata:
    type: object
    description: Document metadata
  collection_id:
    type: string
    description: Parent collection UUID
  created_at:
    type: string
    description: ISO timestamp of document creation
```

## Exposed Resources

MCP resources provide read-only access to RAG Modulo data.

### rag://collection/{id}/documents

Document metadata for a collection.

```json
{
  "uri": "rag://collection/abc123/documents",
  "name": "Collection Documents",
  "description": "List of documents in the collection",
  "mimeType": "application/json"
}
```

**Content**:

```json
{
  "collection_id": "abc123",
  "documents": [
    {
      "id": "doc1",
      "title": "Q4 Financial Report",
      "created_at": "2024-10-15T10:00:00Z",
      "word_count": 5000,
      "metadata": { "author": "Finance Team" }
    }
  ],
  "total_count": 150
}
```

### rag://collection/{id}/stats

Collection statistics.

```json
{
  "uri": "rag://collection/abc123/stats",
  "name": "Collection Statistics",
  "description": "Usage statistics for the collection",
  "mimeType": "application/json"
}
```

**Content**:

```json
{
  "collection_id": "abc123",
  "document_count": 150,
  "total_words": 500000,
  "total_chunks": 2500,
  "last_ingestion": "2024-11-20T14:30:00Z",
  "query_count_30d": 1250,
  "avg_query_time_ms": 450
}
```

### rag://search/{query}/results

Cached search results (for efficiency when same query is repeated).

```json
{
  "uri": "rag://search/q4+projections/results",
  "name": "Cached Search Results",
  "description": "Cached results for recent search query",
  "mimeType": "application/json"
}
```

## Authentication

### SPIFFE JWT-SVID (Agent-to-Agent)

For AI agents authenticated via SPIFFE/SPIRE (PR #695):

```
Authorization: Bearer <JWT-SVID>

JWT Claims:
{
  "sub": "spiffe://rag-modulo.example.com/agent/search-enricher/abc123",
  "aud": ["rag-modulo-mcp"],
  "exp": 1732800000
}
```

The MCP server validates the JWT-SVID and extracts:

- Agent SPIFFE ID
- Capabilities (from agents table)
- Owner user ID (for collection access)

### Bearer Token (User-Delegated)

For external clients acting on behalf of users:

```
Authorization: Bearer <user-access-token>
```

User tokens are issued via existing OAuth flow and include:

- User ID
- Scopes (read, write, admin)
- Expiration

### API Key (Service Accounts)

For service-to-service integration:

```
X-API-Key: <service-api-key>
```

API keys are associated with:

- Service account user
- Allowed collections
- Rate limits

## Authorization

### Capability-Based Access Control

SPIFFE agents have capabilities that map to MCP tool permissions:

| Capability | Allowed Tools |
|------------|---------------|
| `search:read` | `rag_search`, `rag_list_collections`, `rag_get_document` |
| `search:write` | `rag_ingest` |
| `llm:invoke` | `rag_generate_podcast`, `rag_smart_questions` |
| `collection:read` | All read operations on owned collections |
| `collection:write` | Create/modify collections |

### Collection Access

Agents can only access collections where:

1. They are owned by the agent's owner_user_id
2. They are shared with the agent's team_id
3. The collection is marked as public

## File Structure

```
backend/rag_solution/mcp_server/
├── __init__.py
├── server.py           # MCP server setup, transport handling
├── tools.py            # Tool definitions and implementations
├── resources.py        # Resource definitions
├── auth.py             # SPIFFE/Bearer/API key validation
└── schemas.py          # Request/response schemas

tests/unit/mcp_server/
├── __init__.py
├── test_server.py
├── test_tools.py
├── test_resources.py
└── test_auth.py
```

## Server Implementation

### Transport Options

| Transport | Use Case | Port |
|-----------|----------|------|
| **stdio** | Claude Desktop, local CLI | N/A |
| **SSE** | Web clients, real-time updates | 8010 |
| **HTTP** | REST-like integration | 8010 |

### Example Server Setup

```python
# backend/rag_solution/mcp_server/server.py

from mcp import Server, Tool, Resource
from mcp.transports import StdioTransport, SSETransport

from .tools import (
    rag_search,
    rag_ingest,
    rag_list_collections,
    rag_generate_podcast,
    rag_smart_questions,
    rag_get_document,
)
from .resources import collection_documents, collection_stats, search_results
from .auth import validate_auth

server = Server("rag-modulo")

# Register tools
server.register_tool(rag_search)
server.register_tool(rag_ingest)
server.register_tool(rag_list_collections)
server.register_tool(rag_generate_podcast)
server.register_tool(rag_smart_questions)
server.register_tool(rag_get_document)

# Register resources
server.register_resource(collection_documents)
server.register_resource(collection_stats)
server.register_resource(search_results)

# Auth middleware
server.use(validate_auth)

# Run server
if __name__ == "__main__":
    transport = StdioTransport()  # Or SSETransport(port=8010)
    server.run(transport)
```

## Integration with Context Forge

Register RAG Modulo MCP server with Context Forge for federation:

```bash
curl -X POST http://localhost:8001/api/v1/servers \
  -H "Authorization: Bearer $CONTEXT_FORGE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "RAG Modulo",
    "type": "mcp",
    "endpoint": "http://rag-modulo-backend:8010",
    "config": {
      "protocol": "sse",
      "auth_required": true
    }
  }'
```

## SPIFFE + MCP Coexistence

### Identity Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Identity Architecture                                    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    Human Users                                          ││
│  │  - Authenticate via OIDC/OAuth (existing auth)                         ││
│  │  - JWT with user claims                                                ││
│  │  - Access collections they own                                         ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                             ▲                                                │
│                             │ Creates & owns                                 │
│                             ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │              AI Agents (PR #695 SPIFFE)                                 ││
│  │                                                                         ││
│  │  SPIFFE ID: spiffe://rag-modulo.example.com/agent/{type}/{id}          ││
│  │                                                                         ││
│  │  Agent Record:                                                          ││
│  │  - id: UUID                                                             ││
│  │  - spiffe_id: Full SPIFFE ID                                            ││
│  │  - agent_type: search-enricher, cot-reasoning, etc.                     ││
│  │  - owner_user_id: UUID (who created/owns this agent)                    ││
│  │  - capabilities: [search:read, llm:invoke, etc.]                        ││
│  │  - status: active, suspended, revoked, pending                          ││
│  │                                                                         ││
│  │  Auth Flow:                                                             ││
│  │  1. Agent presents JWT-SVID from SPIRE                                  ││
│  │  2. MCP Server validates via SpiffeAuthenticator                        ││
│  │  3. Creates AgentPrincipal with capabilities                            ││
│  │  4. CBAC (Capability-Based Access Control)                              ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                             ▲                                                │
│                             │ Invokes via MCP                                │
│                             ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │            MCP Tools                                                    ││
│  │                                                                         ││
│  │  MCP Server handles:                                                    ││
│  │  - Protocol translation (stdio, SSE, HTTP)                              ││
│  │  - Tool discovery and invocation                                        ││
│  │  - Rate limiting and circuit breakers                                   ││
│  │                                                                         ││
│  │  Identity Propagation:                                                  ││
│  │  - Agent's SPIFFE ID passed in X-Spiffe-Id header                       ││
│  │  - MCP tools validate agent capabilities                                ││
│  │  - Audit log includes agent identity                                    ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

### Example Flow

```python
# Agent executes MCP tool with SPIFFE identity

# 1. Agent authenticates with SPIFFE JWT-SVID
agent_principal = await spiffe_authenticator.validate_svid(jwt_token)
# AgentPrincipal(spiffe_id="spiffe://rag-modulo/agent/search-enricher/abc123",
#                capabilities=["search:read", "llm:invoke"])

# 2. Agent calls MCP tool
response = await mcp_server.invoke_tool(
    tool_name="rag_search",
    arguments={"collection_id": "...", "query": "Q4 projections"},
    auth_context=agent_principal
)

# 3. MCP tool validates capability
if "search:read" not in agent_principal.capabilities:
    raise PermissionDenied("Agent lacks search:read capability")

# 4. Audit log captures full chain
logger.info(
    "MCP tool invoked",
    agent_spiffe_id=agent_principal.spiffe_id,
    tool="rag_search",
    owner_user_id=str(agent.owner_user_id)
)
```

## Security Considerations

1. **Authentication Required**: All MCP endpoints require authentication
2. **Capability Validation**: Every tool invocation checks agent capabilities
3. **Collection Scoping**: Agents can only access authorized collections
4. **Rate Limiting**: Per-agent rate limits prevent abuse
5. **Audit Logging**: All tool invocations logged with identity context
6. **Token Expiration**: JWT-SVIDs have short lifetimes (15 minutes)
7. **Revocation**: Agents can be suspended/revoked immediately

## Observability

- OpenTelemetry spans for all MCP operations
- Metrics: tool invocation counts, latency, error rates
- Structured logging with agent identity context
- Integration with Context Forge admin UI

## Related Documents

- [MCP Integration Architecture](./mcp-integration-architecture.md)
- [SearchService Agent Hooks Architecture](./search-agent-hooks-architecture.md)
- [SPIRE Integration Architecture](./spire-integration-architecture.md)
