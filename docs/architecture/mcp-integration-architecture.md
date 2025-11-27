# MCP Integration Architecture

**Date**: November 2025
**Status**: Architecture Design
**Version**: 1.0
**Related PRs**: #671, #684, #695

## Overview

This document describes the architecture for integrating Model Context Protocol (MCP) into
RAG Modulo. The integration enables bidirectional MCP communication:

1. **RAG Modulo as MCP Client**: Consuming external MCP tools (PowerPoint generation, charts, translation)
2. **RAG Modulo as MCP Server**: Exposing RAG capabilities to external AI tools (Claude Desktop, workflow systems)

## PR Comparison and Decision

### PR #671 vs #684 Analysis

| Aspect | PR #671 | PR #684 | Decision |
|--------|---------|---------|----------|
| **File Organization** | `mcp/` dedicated directory | `services/` directory | #684 naming preferred |
| **Lines Changed** | 2,502 | 2,846 | Similar |
| **Test Functions** | 63 | 50 | #671 has more tests |
| **Mergeable** | Yes | Unknown | #671 confirmed |

### Decision: Adopt #684 File Naming with #671 Test Coverage

We will use #684's file naming convention (`mcp_gateway_client.py`, `search_result_enricher.py`)
placed in the `services/` directory, as this follows the existing service-based architecture
pattern. However, we should incorporate the additional test coverage from #671.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MCP Context Forge                                  │
│                        (Central Gateway/Registry)                            │
│                                                                              │
│  Registered Servers:                                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ Internal (RAG Modulo consumes):                                      │   │
│  │   • ppt-generator-mcp (PowerPoint)                                   │   │
│  │   • chart-generator-mcp (Visualizations)                             │   │
│  │   • translator-mcp (Language translation)                            │   │
│  │   • web-enricher-mcp (Real-time data)                                │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ External (RAG Modulo exposes):                                       │   │
│  │   • rag-modulo-mcp (search, ingest, podcast, collections)            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
         ▲                                                    ▲
         │                                                    │
         │ RAG Modulo calls                    External tools call
         │ external MCP tools                  RAG Modulo MCP server
         │                                                    │
         ▼                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          RAG Modulo Backend                                  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │   MCP Client                        │    MCP Server                   │  │
│  │   services/mcp_gateway_client.py    │    mcp_server/server.py         │  │
│  │   services/search_result_enricher.py│    mcp_server/tools.py          │  │
│  │                                     │                                 │  │
│  │   Consumes: ppt-generator,          │    Exposes: rag_search,         │  │
│  │   chart-generator, etc.             │    rag_ingest, rag_podcast      │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                     Core Services                                       ││
│  │   SearchService, DocumentService, PodcastService, CollectionService    ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
         ▲
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          RAG Modulo Frontend                                 │
│                                                                              │
│  • Triggers searches → gets artifacts back                                  │
│  • Configures which agents run per collection                               │
│  • Downloads/previews generated artifacts                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## File Structure

```
backend/rag_solution/
├── services/
│   ├── mcp_gateway_client.py          # Client to call external MCP tools
│   ├── search_result_enricher.py      # Post-search enrichment agent
│   └── ... (existing services)
│
├── mcp_server/                         # RAG Modulo as MCP server
│   ├── __init__.py
│   ├── server.py                       # MCP server setup, transport handling
│   ├── tools.py                        # Tool definitions (rag_search, rag_ingest, etc.)
│   ├── resources.py                    # MCP resources (collection metadata, etc.)
│   └── auth.py                         # SPIFFE/Bearer token validation
│
├── schemas/
│   ├── mcp_schema.py                   # Schemas for MCP requests/responses
│   └── ...
│
└── router/
    ├── mcp_router.py                   # REST endpoints for MCP management
    └── ...

tests/unit/
├── services/
│   ├── test_mcp_gateway_client.py
│   └── test_search_result_enricher.py
├── router/
│   └── test_mcp_router.py
└── mcp_server/
    ├── test_server.py
    └── test_tools.py
```

## MCP Client Components

### MCPGatewayClient

Thin wrapper with circuit breaker pattern for calling external MCP tools via Context Forge.

**Key Features**:

- Circuit breaker: 5 failure threshold, 60s recovery timeout
- Health checks: 5-second timeout
- Default timeout: 30 seconds on all calls
- Graceful degradation on failures

### SearchResultEnricher

Content Enricher pattern implementation for augmenting search results with external data.

**Capabilities**:

- Real-time data enrichment (stock prices, weather, etc.)
- External knowledge base queries
- Document metadata enhancement

## MCP Server Components

RAG Modulo exposes its capabilities as MCP tools for external consumption.

### Exposed Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `rag_search` | Search documents in a collection | `collection_id`, `query`, `top_k`, `use_cot` |
| `rag_ingest` | Add documents to a collection | `collection_id`, `documents` |
| `rag_list_collections` | List accessible collections | `include_stats` |
| `rag_generate_podcast` | Generate podcast from collection | `collection_id`, `topic`, `duration_minutes` |
| `rag_smart_questions` | Get suggested follow-up questions | `collection_id`, `context` |

### Exposed Resources

| Resource URI | Description |
|--------------|-------------|
| `rag://collection/{id}/documents` | Document metadata for a collection |
| `rag://collection/{id}/stats` | Collection statistics |
| `rag://search/{query}/results` | Cached search results |

### Authentication

- **SPIFFE JWT-SVID** (PR #695): For agent-to-agent calls
- **Bearer token**: For user-delegated access from Claude Desktop, etc.

## Integration with Context Forge

IBM's MCP Context Forge serves as the central gateway providing:

- Protocol translation (stdio, SSE, WebSocket, HTTP)
- Tool registry and discovery
- Bearer token auth with JWT + RBAC
- Rate limiting with Redis backing
- OpenTelemetry integration
- Admin UI for management
- Redis-backed federation for distributed deployment

## Security Considerations

1. **Network Isolation**: Context Forge runs in same VPC as RAG Modulo backend
2. **JWT Authentication**: Secure token-based auth for all API calls
3. **RBAC**: Team-based access control for sensitive tools
4. **Secrets Management**: MCP server credentials managed by Context Forge
5. **Audit Logging**: All tool invocations logged via OpenTelemetry
6. **Capability Validation**: SPIFFE capabilities mapped to MCP tool permissions

## Related Documents

- [SearchService Agent Hooks Architecture](./search-agent-hooks-architecture.md)
- [RAG Modulo MCP Server Architecture](./rag-modulo-mcp-server-architecture.md)
- [SPIRE Integration Architecture](./spire-integration-architecture.md)
- [Agent MCP Architecture Design](../design/agent-mcp-architecture.md)
- [MCP Context Forge Integration Design](../design/mcp-context-forge-integration.md)
