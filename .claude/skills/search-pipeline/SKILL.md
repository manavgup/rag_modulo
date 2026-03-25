---
name: Search Pipeline
description: RAG Modulo search architecture including pipeline resolution, Chain of Thought reasoning, MCP gateway, and agentic search patterns. Trigger when modifying search flow, CoT, or MCP integration.
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Search Pipeline Architecture

## Core Flow

1. Request arrives at `router/search_router.py` -> `SearchService.search()`
2. Pipeline resolved automatically: `_resolve_user_default_pipeline()`
3. Complex question detection: `_should_use_chain_of_thought()`
4. If CoT: `ChainOfThoughtService` orchestrates decomposition + synthesis
5. Vector search via configured provider (Milvus default)
6. Response assembly with source attribution

## Key Files

- Entry: `backend/rag_solution/services/search_service.py`
- CoT: `backend/rag_solution/services/chain_of_thought_service.py`
- Schema: `backend/rag_solution/schemas/search_schema.py`
- MCP Gateway: `backend/rag_solution/services/mcp_gateway_client.py`
- MCP Server: `backend/mcp_server/server.py`

## CoT Hardening

- Structured output: XML `<thinking>` / `<answer>` tags
- Multi-layer parsing: XML -> JSON -> markers -> regex -> full response
- Quality scoring: 0.0-1.0 confidence with artifact detection
- Retry logic: up to 3 attempts, quality threshold 0.6
- Docs: `docs/features/chain-of-thought-hardening.md`
