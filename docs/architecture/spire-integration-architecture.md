# SPIRE Integration Architecture for Agent Identity in RAG Modulo

## Executive Summary

This document outlines the architecture for integrating SPIFFE/SPIRE into RAG Modulo to provide
cryptographic workload identities for AI agents. By combining SPIRE's production-ready SPIFFE
implementation with IBM MCP Context Forge, RAG Modulo will gain zero-trust agent authentication,
enabling secure agent-to-agent (A2A) communication and verifiable machine identities.

## Table of Contents

1. [Background and Motivation](#1-background-and-motivation)
2. [Current State Analysis](#2-current-state-analysis)
3. [SPIFFE/SPIRE Fundamentals](#3-spiffespire-fundamentals)
4. [Proposed Architecture](#4-proposed-architecture)
5. [Integration Points](#5-integration-points)
6. [Agent Identity Model](#6-agent-identity-model)
7. [Deployment Topology](#7-deployment-topology)
8. [Security Considerations](#8-security-considerations)
9. [Implementation Phases](#9-implementation-phases)
10. [References](#10-references)

---

## 1. Background and Motivation

### 1.1 Why Agent Identity Matters

As RAG Modulo evolves to support AI agents through IBM MCP Context Forge integration (PR #684),
a critical need emerges: **verifiable machine/agent identities**. Unlike human users authenticated
via OAuth/OIDC, AI agents require:

- **Cryptographic identity** that cannot be forged or impersonated
- **Zero-trust verification** at every interaction point
- **Automatic credential rotation** without service disruption
- **Audit trails** for agent actions tied to immutable identities
- **Cross-service trust** in distributed agent ecosystems

### 1.2 Limitations of Current Approach

The current authentication system in RAG Modulo (`backend/core/authentication_middleware.py`) relies on:

- JWT tokens with shared secrets
- Human-centric OAuth/OIDC flows
- Mock token patterns for development
- No native support for workload/machine identities

These approaches don't scale for multi-agent systems where:

- Agents spawn dynamically
- Credentials must rotate automatically
- Trust must be cryptographically verifiable
- Agent-to-agent calls require mutual authentication

### 1.3 Strategic Value

SPIRE integration enables RAG Modulo to:

1. **Establish trust domains** for agent ecosystems
2. **Issue verifiable identities** (SVIDs) to each agent workload
3. **Enable mTLS** for secure agent-to-agent communication
4. **Support federation** across organizational boundaries
5. **Align with industry standards** (SPIFFE is a CNCF graduated project)

---

## 2. Current State Analysis

### 2.1 RAG Modulo Authentication Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Current Authentication Flow                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌───────────────────────┐    ┌──────────────┐  │
│  │  Client  │───▶│ AuthenticationMiddleware │───▶│  User Model  │  │
│  │ (Human)  │    │ (JWT / OAuth / Mock)    │    │ (PostgreSQL) │  │
│  └──────────┘    └───────────────────────┘    └──────────────┘  │
│                                                                  │
│  Authentication Methods:                                         │
│  • JWT tokens (custom claims: sub, email, name, uuid, role)     │
│  • OIDC/OAuth via backend/auth/oidc.py                          │
│  • Mock tokens for dev/test (SKIP_AUTH, DEVELOPMENT_MODE)       │
│                                                                  │
│  User Model (backend/rag_solution/models/user.py):              │
│  • id (UUID), ibm_id, email, name, role                         │
│  • Relationships: collections, teams, files, pipelines          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 IBM MCP Context Forge Integration (PR #684)

PR #684 introduces the MCP Gateway integration with:

- **ResilientMCPGatewayClient**: Circuit breaker pattern for gateway calls
- **SearchResultEnricher**: Tool-based search enrichment
- **MCP Router**: `/api/v1/mcp/*` endpoints for tool discovery/invocation
- **JWT Support**: `mcp_jwt_token` configuration (identified security gap)

```
┌─────────────────────────────────────────────────────────────────┐
│              MCP Context Forge Architecture                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────┐    ┌─────────────────┐    ┌──────────────────┐  │
│  │ RAG Modulo │───▶│ MCP Context     │───▶│ External MCP     │  │
│  │  Backend   │    │ Forge Gateway   │    │ Tool Servers     │  │
│  └────────────┘    └─────────────────┘    └──────────────────┘  │
│        │                    │                                    │
│        │           ┌────────┴────────┐                          │
│        │           │ Virtual Servers │                          │
│        │           │ Tool Registry   │                          │
│        │           │ Federation      │                          │
│        │           └─────────────────┘                          │
│        │                                                         │
│        ▼                                                         │
│  Current Auth: JWT Bearer tokens                                │
│  Gap: No cryptographic workload identity                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. SPIFFE/SPIRE Fundamentals

### 3.1 Core Concepts

| Component | Description |
|-----------|-------------|
| **SPIFFE** | Secure Production Identity Framework For Everyone - the specification |
| **SPIRE** | SPIFFE Runtime Environment - production-ready implementation |
| **SVID** | SPIFFE Verifiable Identity Document - the credential |
| **Trust Domain** | Namespace for identities (e.g., `spiffe://rag-modulo.example.com`) |
| **Workload** | Any running process that needs identity (agent, service, etc.) |

### 3.2 SPIFFE ID Structure

```
spiffe://trust-domain/path/to/workload

Examples:
spiffe://rag-modulo.example.com/agent/search-enricher
spiffe://rag-modulo.example.com/agent/cot-reasoning/instance-1
spiffe://rag-modulo.example.com/service/backend-api
spiffe://rag-modulo.example.com/mcp/tool-server/watson-nlp
```

### 3.3 SVID Types

| Type | Format | Use Case |
|------|--------|----------|
| **X.509-SVID** | X.509 certificate | mTLS, long-lived connections, service mesh |
| **JWT-SVID** | JWT token | REST APIs, short-lived authentication, federation |

For RAG Modulo's agent architecture, **JWT-SVIDs** are recommended because:

- Native integration with existing JWT middleware
- Audience-scoped access control
- Lightweight verification without certificate chains
- Better fit for MCP's HTTP-based protocols

### 3.4 Attestation Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    SPIRE Attestation Flow                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Node Attestation (Server ←→ Agent)                          │
│     Agent proves node identity using platform evidence:          │
│     • Kubernetes ServiceAccount tokens                          │
│     • AWS Instance Identity Documents                           │
│     • Azure Managed Identity                                    │
│     • Docker container selectors                                │
│                                                                  │
│  2. Workload Attestation (Agent ←→ Workload)                    │
│     Agent verifies workload properties:                         │
│     • Kubernetes: namespace, service account, pod labels        │
│     • Unix: uid, gid, binary path, sha256 hash                  │
│     • Docker: image ID, container labels, environment           │
│                                                                  │
│  3. SVID Issuance                                               │
│     ┌─────────┐    ┌──────────┐    ┌────────┐                  │
│     │Workload │───▶│ SPIRE    │───▶│ SPIRE  │                  │
│     │(Agent)  │    │ Agent    │    │ Server │                  │
│     └─────────┘    └──────────┘    └────────┘                  │
│          │              │               │                       │
│          │   Request    │   Fetch       │                       │
│          │   SVID       │   from cache  │                       │
│          │              │   or server   │                       │
│          ▼              ▼               │                       │
│     ┌──────────────────────┐            │                       │
│     │   JWT-SVID Token     │◀───────────┘                       │
│     │   (Signed, scoped)   │                                    │
│     └──────────────────────┘                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Proposed Architecture

### 4.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    RAG Modulo + SPIRE + MCP Architecture                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Trust Domain: spiffe://rag-modulo.example.com                              │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         SPIRE Server Cluster                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────────────────────┐   │   │
│  │  │   SPIRE     │  │ Registration │  │    Trust Bundle Store     │   │   │
│  │  │   Server    │  │   Entries    │  │ (PostgreSQL / Datastore)  │   │   │
│  │  └─────────────┘  └─────────────┘  └────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                          │                                                   │
│            ┌─────────────┼─────────────────────────┐                        │
│            │             │                         │                        │
│            ▼             ▼                         ▼                        │
│  ┌──────────────┐  ┌──────────────┐      ┌──────────────────┐              │
│  │ SPIRE Agent  │  │ SPIRE Agent  │      │  SPIRE Agent     │              │
│  │ (Backend Pod)│  │ (MCP Gateway)│      │  (Tool Servers)  │              │
│  └──────────────┘  └──────────────┘      └──────────────────┘              │
│         │                │                       │                          │
│         ▼                ▼                       ▼                          │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐              │
│  │  RAG Modulo  │  │  MCP Context     │  │   MCP Tool       │              │
│  │   Backend    │◀▶│  Forge Gateway   │◀▶│   Servers        │              │
│  │              │  │                  │  │ (WatsonX, etc.)  │              │
│  │ SPIFFE ID:   │  │  SPIFFE ID:      │  │  SPIFFE ID:      │              │
│  │ /service/    │  │  /gateway/       │  │  /mcp/tool/      │              │
│  │   backend    │  │    mcp-forge     │  │    watson-nlp    │              │
│  └──────────────┘  └──────────────────┘  └──────────────────┘              │
│         │                │                       │                          │
│         │                │                       │                          │
│         ▼                ▼                       ▼                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Agent Workloads (JWT-SVID)                       │   │
│  │                                                                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │   Search    │  │   Chain of  │  │  Question   │  │   Source    │ │   │
│  │  │  Enricher   │  │   Thought   │  │ Decomposer  │  │ Attribution │ │   │
│  │  │   Agent     │  │    Agent    │  │   Agent     │  │    Agent    │ │   │
│  │  │             │  │             │  │             │  │             │ │   │
│  │  │ SPIFFE ID:  │  │ SPIFFE ID:  │  │ SPIFFE ID:  │  │ SPIFFE ID:  │ │   │
│  │  │/agent/      │  │/agent/      │  │/agent/      │  │/agent/      │ │   │
│  │  │ search-     │  │ cot-        │  │ question-   │  │ source-     │ │   │
│  │  │ enricher    │  │ reasoning   │  │ decomposer  │  │ attribution │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Component Descriptions

| Component | Purpose | SPIFFE ID Pattern |
|-----------|---------|-------------------|
| **SPIRE Server** | Central authority for identity management | N/A (infrastructure) |
| **SPIRE Agent** | Per-node daemon, exposes Workload API | N/A (infrastructure) |
| **RAG Modulo Backend** | Main API service | `spiffe://rag-modulo.example.com/service/backend` |
| **MCP Context Forge Gateway** | Tool registry and routing | `spiffe://rag-modulo.example.com/gateway/mcp-forge` |
| **MCP Tool Servers** | External tool providers | `spiffe://rag-modulo.example.com/mcp/tool/{tool-name}` |
| **Agent Workloads** | AI agents performing tasks | `spiffe://rag-modulo.example.com/agent/{agent-type}` |

---

## 5. Integration Points

### 5.1 Python SPIFFE Client Integration

The `py-spiffe` library provides native Python support for SPIFFE:

```python
# Installation: pip install spiffe

from spiffe import WorkloadApiClient, JwtSource

# Fetch JWT-SVID for agent authentication
with WorkloadApiClient() as client:
    jwt_svid = client.fetch_jwt_svid(audience={"mcp-gateway", "backend-api"})
    spiffe_id = jwt_svid.spiffe_id  # spiffe://rag-modulo.example.com/agent/search-enricher
    token = jwt_svid.token          # JWT to use in Authorization header

# Auto-refreshing JWT source for long-running agents
with JwtSource() as source:
    svid = source.fetch_svid(audience={'mcp-gateway'})
    # Token automatically rotates before expiration
```

### 5.2 Integration with AuthenticationMiddleware

Extend `backend/core/authentication_middleware.py` to support SPIFFE JWT-SVIDs:

```
┌─────────────────────────────────────────────────────────────────┐
│               Enhanced Authentication Flow                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐                                                    │
│  │  Request │                                                    │
│  └────┬─────┘                                                    │
│       │                                                          │
│       ▼                                                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              AuthenticationMiddleware                      │  │
│  │                                                            │  │
│  │  1. Check bypass mode (dev/test)                          │  │
│  │  2. Check open paths                                      │  │
│  │  3. Extract Authorization header                          │  │
│  │                                                            │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │           Token Type Detection                       │  │  │
│  │  │                                                       │  │  │
│  │  │  ┌─────────────┐   ┌──────────────┐   ┌───────────┐ │  │  │
│  │  │  │ User JWT    │   │ SPIFFE       │   │ Mock      │ │  │  │
│  │  │  │ (iss=self)  │   │ JWT-SVID     │   │ Token     │ │  │  │
│  │  │  │             │   │ (iss=SPIRE)  │   │           │ │  │  │
│  │  │  └──────┬──────┘   └──────┬───────┘   └─────┬─────┘ │  │  │
│  │  │         │                 │                 │       │  │  │
│  │  │         ▼                 ▼                 ▼       │  │  │
│  │  │  ┌──────────────────────────────────────────────┐  │  │  │
│  │  │  │          Unified Principal Object            │  │  │  │
│  │  │  │  • identity_type: "user" | "agent"           │  │  │  │
│  │  │  │  • spiffe_id: (for agents)                   │  │  │  │
│  │  │  │  • user_id: (for users)                      │  │  │  │
│  │  │  │  • capabilities: [list of allowed actions]   │  │  │  │
│  │  │  └──────────────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │                                                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 Integration with MCP Context Forge

Enhance the MCP Gateway client to use SPIFFE authentication:

```
┌─────────────────────────────────────────────────────────────────┐
│            MCP Gateway SPIFFE Integration                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                ResilientMCPGatewayClient                 │    │
│  │                                                          │    │
│  │  ┌────────────────────────────────────────────────────┐ │    │
│  │  │           SPIFFEAuthenticator                       │ │    │
│  │  │                                                     │ │    │
│  │  │  • JwtSource for auto-refreshing tokens            │ │    │
│  │  │  • Audience scoping per endpoint                   │ │    │
│  │  │  • Fallback to legacy JWT if SPIRE unavailable     │ │    │
│  │  │                                                     │ │    │
│  │  └────────────────────────────────────────────────────┘ │    │
│  │                                                          │    │
│  │  def _get_auth_headers(self, audience: str) -> dict:    │    │
│  │      svid = self.jwt_source.fetch_svid(audience={aud})  │    │
│  │      return {"Authorization": f"Bearer {svid.token}"}   │    │
│  │                                                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Benefits:                                                       │
│  • Mutual authentication (both sides verify SPIFFE IDs)         │
│  • No shared secrets to manage or rotate                        │
│  • Audience validation prevents token reuse attacks             │
│  • Cryptographic proof of workload identity                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Agent Identity Model

### 6.1 Agent Schema Extension

Extend the existing data model to support agent identities:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Identity Model                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Table: agents                                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Column           │ Type        │ Description                ││
│  │──────────────────┼─────────────┼────────────────────────────││
│  │ id               │ UUID        │ Primary key                ││
│  │ spiffe_id        │ VARCHAR     │ SPIFFE identity (unique)   ││
│  │ agent_type       │ VARCHAR     │ Type classification        ││
│  │ name             │ VARCHAR     │ Human-readable name        ││
│  │ description      │ TEXT        │ Purpose/capabilities       ││
│  │ owner_user_id    │ UUID (FK)   │ User who owns this agent   ││
│  │ team_id          │ UUID (FK)   │ Team association (optional)││
│  │ capabilities     │ JSONB       │ Allowed actions/scopes     ││
│  │ metadata         │ JSONB       │ Additional properties      ││
│  │ status           │ VARCHAR     │ active/suspended/revoked   ││
│  │ created_at       │ TIMESTAMP   │ Registration time          ││
│  │ last_seen_at     │ TIMESTAMP   │ Last authentication        ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  SPIFFE ID Pattern:                                             │
│  spiffe://rag-modulo.example.com/agent/{agent_type}/{agent_id}  │
│                                                                  │
│  Example:                                                        │
│  spiffe://rag-modulo.example.com/agent/search-enricher/abc123   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Agent Types and Capabilities

| Agent Type | SPIFFE Path | Capabilities |
|------------|-------------|--------------|
| `search-enricher` | `/agent/search-enricher/{id}` | `mcp:tool:invoke`, `search:read` |
| `cot-reasoning` | `/agent/cot-reasoning/{id}` | `search:read`, `llm:invoke`, `pipeline:execute` |
| `question-decomposer` | `/agent/question-decomposer/{id}` | `search:read`, `llm:invoke` |
| `source-attribution` | `/agent/source-attribution/{id}` | `document:read`, `search:read` |
| `entity-extraction` | `/agent/entity-extraction/{id}` | `document:read`, `llm:invoke` |
| `answer-synthesis` | `/agent/answer-synthesis/{id}` | `search:read`, `llm:invoke`, `cot:invoke` |

### 6.3 Registration Entry Templates

SPIRE registration entries map SPIFFE IDs to selectors:

```yaml
# Kubernetes deployment selector example
entries:
  - spiffe_id: spiffe://rag-modulo.example.com/agent/search-enricher
    parent_id: spiffe://rag-modulo.example.com/spire/agent/k8s/node
    selectors:
      - k8s:ns:rag-modulo
      - k8s:sa:search-enricher-agent
      - k8s:pod-label:app:search-enricher
    ttl: 3600  # 1 hour token lifetime

  - spiffe_id: spiffe://rag-modulo.example.com/agent/cot-reasoning
    parent_id: spiffe://rag-modulo.example.com/spire/agent/k8s/node
    selectors:
      - k8s:ns:rag-modulo
      - k8s:sa:cot-reasoning-agent
      - k8s:pod-label:app:cot-reasoning
    ttl: 3600

  - spiffe_id: spiffe://rag-modulo.example.com/service/backend
    parent_id: spiffe://rag-modulo.example.com/spire/agent/k8s/node
    selectors:
      - k8s:ns:rag-modulo
      - k8s:sa:backend-api
      - k8s:pod-label:app:rag-modulo-backend
    ttl: 86400  # 24 hours for services
```

---

## 7. Deployment Topology

### 7.1 Kubernetes Deployment

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Kubernetes Deployment Topology                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Namespace: spire-system                                                    │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │ StatefulSet: spire-server (replicas: 3 for HA)                  │  │  │
│  │  │                                                                  │  │  │
│  │  │  • Shared PostgreSQL datastore for consistency                  │  │  │
│  │  │  • Trust bundle distribution via ConfigMap                      │  │  │
│  │  │  • K8s Workload Registrar sidecar for auto-registration        │  │  │
│  │  │                                                                  │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                        │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │ DaemonSet: spire-agent                                          │  │  │
│  │  │                                                                  │  │  │
│  │  │  • One agent per node                                           │  │  │
│  │  │  • CSI driver for workload API exposure (recommended)           │  │  │
│  │  │  • Rolling update strategy (maxUnavailable: 5)                  │  │  │
│  │  │                                                                  │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  Namespace: rag-modulo                                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │  │
│  │  │ Deployment:     │  │ Deployment:     │  │ Deployment:         │   │  │
│  │  │ backend-api     │  │ mcp-gateway     │  │ agent-workers       │   │  │
│  │  │                 │  │                 │  │                     │   │  │
│  │  │ • SPIRE CSI     │  │ • SPIRE CSI     │  │ • SPIRE CSI         │   │  │
│  │  │   volume mount  │  │   volume mount  │  │   volume mount      │   │  │
│  │  │ • py-spiffe     │  │ • SPIFFE auth   │  │ • JwtSource         │   │  │
│  │  │   WorkloadAPI   │  │   middleware    │  │   per agent type    │   │  │
│  │  │                 │  │                 │  │                     │   │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘   │  │
│  │                                                                        │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │                   Infrastructure Services                        │  │  │
│  │  │                                                                  │  │  │
│  │  │  PostgreSQL │ Milvus │ MinIO │ MLFlow │ Redis                   │  │  │
│  │  │  (existing infrastructure - no SPIFFE changes required)         │  │  │
│  │  │                                                                  │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Docker Compose Development Setup

For local development, a simplified SPIRE deployment:

```yaml
# docker-compose.spire.yml (new file)
services:
  spire-server:
    image: ghcr.io/spiffe/spire-server:1.9.0
    volumes:
      - ./spire/server.conf:/etc/spire/server.conf
      - ./spire/data:/var/lib/spire/server
    ports:
      - "8081:8081"  # Server API
    command: ["-config", "/etc/spire/server.conf"]

  spire-agent:
    image: ghcr.io/spiffe/spire-agent:1.9.0
    volumes:
      - ./spire/agent.conf:/etc/spire/agent.conf
      - /var/run/spire:/var/run/spire  # Workload API socket
    depends_on:
      - spire-server
    command: ["-config", "/etc/spire/agent.conf"]
    pid: "host"  # Required for Unix workload attestation

  # Extend existing backend service
  backend:
    volumes:
      - /var/run/spire:/var/run/spire:ro
    environment:
      - SPIFFE_ENDPOINT_SOCKET=unix:///var/run/spire/agent.sock
      - SPIFFE_ENABLED=true
```

---

## 8. Security Considerations

### 8.1 Threat Model

| Threat | Mitigation |
|--------|------------|
| **Agent impersonation** | SPIRE attestation verifies workload properties before issuing SVIDs |
| **Token theft** | Short TTLs (1 hour), audience scoping, automatic rotation |
| **Replay attacks** | JWT `exp` and `aud` claims prevent cross-service reuse |
| **Compromised node** | SPIRE agent revocation, registration entry removal |
| **Trust domain compromise** | Federation allows cross-org trust without shared root |
| **Insider threat** | Audit logging via SPIRE, capability-based access control |

### 8.2 Trust Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                    Trust Hierarchy                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Level 0: Trust Domain Root                                     │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ spiffe://rag-modulo.example.com                             ││
│  │ (SPIRE Server - root of trust)                              ││
│  └─────────────────────────────────────────────────────────────┘│
│                          │                                       │
│                          ▼                                       │
│  Level 1: Infrastructure Services                               │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │   /service/   │  │   /gateway/   │  │   /spire/     │       │
│  │   backend     │  │   mcp-forge   │  │   agent/*     │       │
│  └───────────────┘  └───────────────┘  └───────────────┘       │
│                          │                                       │
│                          ▼                                       │
│  Level 2: Agent Workloads                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ /agent/search-enricher/* │ /agent/cot-reasoning/* │ ...   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          │                                       │
│                          ▼                                       │
│  Level 3: External Tool Servers (Federated)                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ spiffe://external-tool.example.com/tool/*                 │  │
│  │ (Federated trust via bundle exchange)                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 8.3 Capability-Based Access Control

```python
# Example capability definitions for agents
AGENT_CAPABILITIES = {
    "search-enricher": {
        "allowed_audiences": ["mcp-gateway", "backend-api"],
        "allowed_actions": [
            "mcp:tool:invoke",
            "search:read",
        ],
        "rate_limit": 100,  # requests per minute
    },
    "cot-reasoning": {
        "allowed_audiences": ["backend-api", "llm-provider"],
        "allowed_actions": [
            "search:read",
            "llm:invoke",
            "pipeline:execute",
        ],
        "rate_limit": 50,
    },
}
```

---

## 9. Implementation Phases

### Phase 1: Foundation (Weeks 1-2)

**Objective**: Deploy SPIRE infrastructure and establish trust domain

1. **SPIRE Server Deployment**
   - Deploy SPIRE Server (StatefulSet in Kubernetes or Docker container)
   - Configure PostgreSQL as datastore
   - Set up trust domain: `spiffe://rag-modulo.example.com`

2. **SPIRE Agent Deployment**
   - Deploy SPIRE Agent (DaemonSet in K8s or sidecar in Docker)
   - Configure node attestation (K8s ServiceAccount tokens)
   - Expose Workload API via CSI driver or hostPath

3. **Registration Entries**
   - Create initial entries for backend service
   - Create entries for MCP Gateway
   - Validate SVID issuance

**Deliverables**:

- Working SPIRE infrastructure
- Trust bundle generation
- Basic SVID fetch validation

### Phase 2: Backend Integration (Weeks 3-4)

**Objective**: Integrate SPIFFE authentication into RAG Modulo backend

1. **Add py-spiffe Dependency**

   ```toml
   # pyproject.toml
   [tool.poetry.dependencies]
   spiffe = "^0.2.2"
   ```

2. **Create SPIFFE Authentication Module**
   - New file: `backend/core/spiffe_auth.py`
   - `SPIFFEAuthenticator` class with JwtSource
   - Token validation and SPIFFE ID extraction

3. **Extend AuthenticationMiddleware**
   - Detect SPIFFE JWT-SVIDs (issuer check)
   - Create unified Principal object
   - Support both user JWTs and agent SVIDs

4. **Add Agent Data Model**
   - Create `Agent` SQLAlchemy model
   - Create agent repository and service
   - Add agent management endpoints

**Deliverables**:

- SPIFFE-aware authentication middleware
- Agent data model and APIs
- Integration tests

### Phase 3: MCP Gateway Integration (Weeks 5-6)

**Objective**: Enable SPIFFE authentication for MCP tool invocations

1. **Update ResilientMCPGatewayClient**
   - Add `SPIFFEAuthenticator` integration
   - Implement audience-scoped token fetching
   - Graceful fallback to legacy JWT

2. **Mutual Authentication**
   - MCP Gateway validates agent SVIDs
   - Agent validates gateway SVID
   - Log SPIFFE IDs for audit

3. **Tool Server Registration**
   - Create SPIRE entries for tool servers
   - Configure federation if cross-domain

**Deliverables**:

- SPIFFE-authenticated MCP calls
- Mutual TLS option for sensitive tools
- Audit logging integration

### Phase 4: Agent Workloads (Weeks 7-8)

**Objective**: Enable individual AI agents to obtain and use SVIDs

1. **Agent Worker Framework**
   - Base class for SPIFFE-enabled agents
   - Automatic SVID lifecycle management
   - Capability validation

2. **Implement Agent Types**
   - SearchEnricherAgent
   - ChainOfThoughtAgent
   - QuestionDecomposerAgent
   - SourceAttributionAgent

3. **Agent Orchestration**
   - Agent spawning with SPIFFE registration
   - Dynamic capability assignment
   - Agent monitoring and health checks

**Deliverables**:

- Working agent workloads with SVIDs
- Agent orchestration framework
- End-to-end integration tests

### Phase 5: Production Hardening (Weeks 9-10)

**Objective**: Production-ready deployment with HA and monitoring

1. **High Availability**
   - SPIRE Server clustering (3 replicas)
   - Shared PostgreSQL datastore
   - Agent failover testing

2. **Observability**
   - OpenTelemetry integration for SPIRE
   - SPIFFE ID correlation in logs
   - Grafana dashboards for SVID metrics

3. **Security Audit**
   - Penetration testing
   - Token TTL tuning
   - Revocation procedures

**Deliverables**:

- Production-ready deployment
- Monitoring and alerting
- Security documentation

---

## 10. References

### SPIFFE/SPIRE Documentation

- [SPIFFE Concepts](https://spiffe.io/docs/latest/spiffe-about/spiffe-concepts/)
- [SPIRE Concepts](https://spiffe.io/docs/latest/spire-about/spire-concepts/)
- [Quickstart for Kubernetes](https://spiffe.io/docs/latest/try/getting-started-k8s/)
- [JWT-SVID Specification](https://github.com/spiffe/spiffe/blob/main/standards/JWT-SVID.md)

### Python Libraries

- [py-spiffe (GitHub)](https://github.com/HewlettPackard/py-spiffe)
- [spiffe on PyPI](https://pypi.org/project/spiffe/)

### IBM MCP Context Forge

- [IBM MCP Context Forge (GitHub)](https://github.com/IBM/mcp-context-forge)
- [PR #684: MCP Gateway Integration](https://github.com/manavgup/rag_modulo/pull/684)

### Industry Resources

- [SPIFFE/SPIRE CSI Driver](https://www.kusari.dev/blog/spiffe-spire-csi-driver)
- [Indeed Engineering: Workload Identity with SPIRE](https://engineering.indeedblog.com/blog/2024/07/workload-identity-with-spire-oidc-for-k8s-istio/)
- [Understanding SPIRE Kubernetes Workload Registrar](https://medium.com/@nathalia.gomazako/understanding-spire-kubernetes-workload-registrar-5dd153ce68fc)

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **SPIFFE** | Secure Production Identity Framework For Everyone |
| **SPIRE** | SPIFFE Runtime Environment |
| **SVID** | SPIFFE Verifiable Identity Document |
| **Trust Domain** | Administrative namespace for SPIFFE identities |
| **Workload** | Any process requiring identity (service, agent, job) |
| **Attestation** | Process of verifying workload identity |
| **Registration Entry** | Mapping of SPIFFE ID to workload selectors |
| **JWT-SVID** | SVID in JWT format for stateless verification |
| **X.509-SVID** | SVID in X.509 certificate format for mTLS |
| **Agent (SPIRE)** | Per-node daemon exposing Workload API |
| **Agent (AI)** | AI workload performing RAG tasks |

## Appendix B: Configuration Templates

### SPIRE Server Configuration

```hcl
# spire/server.conf
server {
    bind_address = "0.0.0.0"
    bind_port = "8081"
    trust_domain = "rag-modulo.example.com"
    data_dir = "/var/lib/spire/server"
    log_level = "INFO"

    jwt_issuer = "spire://rag-modulo.example.com"

    ca_ttl = "168h"  # 7 days
    default_x509_svid_ttl = "24h"
    default_jwt_svid_ttl = "1h"
}

plugins {
    DataStore "sql" {
        plugin_data {
            database_type = "postgres"
            connection_string = "${SPIRE_DB_CONNECTION_STRING}"  # Set via environment variable
        }
    }

    KeyManager "disk" {
        plugin_data {
            keys_path = "/var/lib/spire/server/keys"
        }
    }

    NodeAttestor "k8s_sat" {
        plugin_data {
            clusters = {
                "rag-modulo-cluster" = {
                    service_account_allow_list = ["spire-system:spire-agent"]
                }
            }
        }
    }
}
```

### SPIRE Agent Configuration

```hcl
# spire/agent.conf
agent {
    data_dir = "/var/lib/spire/agent"
    log_level = "INFO"
    server_address = "spire-server"
    server_port = "8081"
    socket_path = "/var/run/spire/agent.sock"
    trust_domain = "rag-modulo.example.com"
}

plugins {
    NodeAttestor "k8s_sat" {
        plugin_data {
            cluster = "rag-modulo-cluster"
        }
    }

    KeyManager "memory" {
        plugin_data {}
    }

    WorkloadAttestor "k8s" {
        plugin_data {
            skip_kubelet_verification = true
        }
    }
}
```

---

*Document Version: 1.0*
*Last Updated: 2025-01-26*
*Author: Claude Code (AI-Assisted Architecture Design)*
*Status: Architecture Proposal - Pending Review*
