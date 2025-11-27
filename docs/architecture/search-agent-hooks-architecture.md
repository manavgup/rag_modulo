# SearchService Agent Hooks Architecture

**Date**: November 2025
**Status**: Architecture Design
**Version**: 1.0
**Related Documents**: [MCP Integration Architecture](./mcp-integration-architecture.md)

## Overview

This document describes the three-stage agent execution hook system integrated into
SearchService. Agents can be injected at strategic points in the search pipeline to enhance,
transform, or augment the search process.

## Pipeline Flow

```
User Query: "What are the revenue projections for Q4?"
                │
                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 1: PRE-SEARCH AGENTS                                                  │
│                                                                              │
│  Purpose: Enhance/transform the query BEFORE vector search                   │
│                                                                              │
│  Example agents:                                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ • Query Expander: "revenue projections Q4" →                           │ │
│  │   "revenue projections Q4 2024 2025 forecast financial outlook"        │ │
│  │                                                                        │ │
│  │ • Language Detector/Translator: Detect non-English, translate to EN    │ │
│  │                                                                        │ │
│  │ • Acronym Resolver: "Q4" → "fourth quarter, Q4, Oct-Dec"               │ │
│  │                                                                        │ │
│  │ • Intent Classifier: Tag as "financial_analysis" for routing           │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  Input:  { query: "What are the revenue projections for Q4?" }              │
│  Output: { query: "revenue projections Q4 2024 forecast...", metadata: {} } │
└─────────────────────────────────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  CORE RAG SEARCH (existing logic - unchanged)                                │
│                                                                              │
│  • Vector embedding of (enhanced) query                                     │
│  • Milvus similarity search                                                 │
│  • Document retrieval                                                       │
│  • Optional: Chain-of-Thought reasoning                                     │
│                                                                              │
│  Output: 10 ranked documents with scores                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 2: POST-SEARCH AGENTS                                                 │
│                                                                              │
│  Purpose: Process/filter/augment retrieved documents BEFORE answer gen      │
│                                                                              │
│  Example agents:                                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ • Re-ranker: Use cross-encoder to re-score documents for relevance     │ │
│  │                                                                        │ │
│  │ • Deduplicator: Remove near-duplicate content across documents         │ │
│  │                                                                        │ │
│  │ • Fact Checker: Validate claims against trusted sources                │ │
│  │                                                                        │ │
│  │ • PII Redactor: Remove sensitive info before showing to user           │ │
│  │                                                                        │ │
│  │ • External Enricher: Add real-time stock prices, weather, etc.         │ │
│  │   (This is what SearchResultEnricher does)                             │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  Input:  { documents: [...10 docs...], query: "..." }                       │
│  Output: { documents: [...8 docs, reordered, enriched...] }                 │
└─────────────────────────────────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ANSWER GENERATION (existing logic - unchanged)                              │
│                                                                              │
│  • LLM synthesizes answer from documents                                    │
│  • Source attribution                                                       │
│  • CoT reasoning steps (if enabled)                                         │
│                                                                              │
│  Output: { answer: "Based on the documents...", sources: [...] }            │
└─────────────────────────────────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 3: RESPONSE AGENTS                                                    │
│                                                                              │
│  Purpose: Generate artifacts/transformations from the final answer           │
│                                                                              │
│  Example agents:                                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ • PowerPoint Generator: Create slides from answer + sources            │ │
│  │   Output: { type: "pptx", data: "base64...", filename: "Q4.pptx" }     │ │
│  │                                                                        │ │
│  │ • PDF Report Generator: Formatted document with citations              │ │
│  │   Output: { type: "pdf", data: "base64...", filename: "report.pdf" }   │ │
│  │                                                                        │ │
│  │ • Chart Generator: Visualize numerical data from answer                │ │
│  │   Output: { type: "png", data: "base64...", filename: "chart.png" }    │ │
│  │                                                                        │ │
│  │ • Audio Summary: Text-to-speech of key findings                        │ │
│  │   Output: { type: "mp3", data: "base64...", filename: "summary.mp3" }  │ │
│  │                                                                        │ │
│  │ • Email Draft: Format answer for email sharing                         │ │
│  │   Output: { type: "html", data: "<html>...", subject: "Q4 Summary" }   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  These run in PARALLEL since they're independent transformations            │
└─────────────────────────────────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  FINAL RESPONSE                                                              │
│                                                                              │
│  {                                                                           │
│    "answer": "Based on the financial documents, Q4 revenue is...",          │
│    "sources": [                                                              │
│      { "document_id": "...", "title": "Q4 Forecast", "score": 0.92 }        │
│    ],                                                                        │
│    "cot_steps": [...],  // If CoT enabled                                   │
│    "agent_artifacts": [  // NEW - from response agents                      │
│      {                                                                       │
│        "agent_id": "ppt_generator",                                         │
│        "type": "pptx",                                                       │
│        "data": "UEsDBBQAAAAIAH...",  // base64                              │
│        "filename": "Q4_Revenue_Projections.pptx",                           │
│        "metadata": { "slides": 5 }                                          │
│      },                                                                      │
│      {                                                                       │
│        "agent_id": "chart_generator",                                       │
│        "type": "png",                                                        │
│        "data": "iVBORw0KGgo...",  // base64                                 │
│        "filename": "revenue_chart.png",                                     │
│        "metadata": { "width": 800, "height": 600 }                          │
│      }                                                                       │
│    ]                                                                         │
│  }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Agent Stages

### Stage 1: Pre-Search Agents

**Purpose**: Transform or enhance the query before vector search.

**Execution**: Sequential by priority (results chain to next agent).

| Agent Type | Description | Use Case |
|------------|-------------|----------|
| Query Expander | Adds synonyms and related terms | Improve recall |
| Language Detector | Identifies query language | Multi-language support |
| Translator | Translates non-English queries | Internationalization |
| Acronym Resolver | Expands abbreviations | Domain-specific search |
| Intent Classifier | Tags query intent | Routing and filtering |
| Spell Checker | Corrects typos | User experience |

**Input Schema**:

```python
class PreSearchInput:
    query: str
    collection_id: UUID
    user_id: UUID
    metadata: dict[str, Any]
```

**Output Schema**:

```python
class PreSearchOutput:
    query: str  # Modified query
    metadata: dict[str, Any]  # Additional context
    skip_search: bool = False  # If True, skip core search
```

### Stage 2: Post-Search Agents

**Purpose**: Process, filter, or augment retrieved documents before answer generation.

**Execution**: Sequential by priority (documents flow through each agent).

| Agent Type | Description | Use Case |
|------------|-------------|----------|
| Re-ranker | Cross-encoder re-scoring | Improve precision |
| Deduplicator | Remove near-duplicates | Cleaner results |
| Fact Checker | Validate against trusted sources | Accuracy |
| PII Redactor | Remove sensitive information | Compliance |
| External Enricher | Add real-time data | Currency |
| Relevance Filter | Remove low-quality results | Quality |

**Input Schema**:

```python
class PostSearchInput:
    documents: list[Document]
    query: str
    collection_id: UUID
    user_id: UUID
    metadata: dict[str, Any]
```

**Output Schema**:

```python
class PostSearchOutput:
    documents: list[Document]  # Modified/filtered documents
    metadata: dict[str, Any]  # Enrichment data
```

### Stage 3: Response Agents

**Purpose**: Generate artifacts or transformations from the final answer.

**Execution**: Parallel (independent transformations).

| Agent Type | Description | Output Format |
|------------|-------------|---------------|
| PowerPoint Generator | Create presentation slides | `.pptx` |
| PDF Report Generator | Formatted document with citations | `.pdf` |
| Chart Generator | Visualize numerical data | `.png`, `.svg` |
| Audio Summary | Text-to-speech narration | `.mp3` |
| Email Draft | Format for email sharing | `.html` |
| Executive Summary | Condensed key findings | `.txt` |

**Input Schema**:

```python
class ResponseAgentInput:
    answer: str
    sources: list[Source]
    query: str
    documents: list[Document]
    collection_id: UUID
    user_id: UUID
    cot_steps: list[CotStep] | None
```

**Output Schema**:

```python
class AgentArtifact:
    agent_id: str
    type: str  # "pptx", "pdf", "png", "mp3", "html"
    data: str  # base64 encoded
    filename: str
    metadata: dict[str, Any]
```

## Agent Priority and Chaining

Agents at each stage execute in priority order (lower number = higher priority):

```
Pre-search stage (priority order):
  1. Language Detector (priority: 0)  → detects "es" (Spanish)
  2. Translator (priority: 10)        → uses detection, translates to EN
  3. Query Expander (priority: 20)    → expands the translated query

Each agent receives:
  - AgentContext with query, collection_id, user_id
  - previous_agent_results: List of results from earlier agents in this stage
```

## AgentContext

Context object passed to all agents:

```python
@dataclass
class AgentContext:
    # Collection context
    collection_id: UUID
    user_id: UUID

    # Conversation context
    conversation_id: UUID | None = None
    conversation_history: list[dict[str, str]] | None = None

    # Search context (populated as pipeline progresses)
    query: str | None = None
    retrieved_documents: list[dict[str, Any]] | None = None
    search_metadata: dict[str, Any] | None = None

    # Pipeline context
    pipeline_stage: str  # 'pre_search', 'post_search', 'response'

    # Agent chaining
    previous_agent_results: list[AgentResult] | None = None
```

## AgentResult

Result object returned by all agents:

```python
@dataclass
class AgentResult:
    agent_id: str
    success: bool
    data: dict[str, Any]
    metadata: dict[str, Any]
    errors: list[str] | None = None

    # For chaining agents
    next_agent_id: str | None = None
```

## Collection-Agent Association

Agents are configured per collection:

```
Collection Settings → Agents & Tools
┌─────────────────────────────────────────────────────────────────────────┐
│ ☑ PowerPoint Generator              Stage: Response   Priority: 1      │
│   Creates slides from search results                   [Configure]     │
├─────────────────────────────────────────────────────────────────────────┤
│ ☑ Query Expander                    Stage: Pre-search  Priority: 0     │
│   Adds synonyms and related terms                     [Configure]      │
├─────────────────────────────────────────────────────────────────────────┤
│ ☐ External Knowledge Enricher       Stage: Post-search Priority: 5     │
│   Augments with real-time market data                 [Configure]      │
└─────────────────────────────────────────────────────────────────────────┘
```

## Database Schema

### AgentConfig Table

```sql
CREATE TABLE agent_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    agent_id VARCHAR(100) NOT NULL,  -- From agent registry
    name VARCHAR(255) NOT NULL,
    description TEXT,
    config JSONB NOT NULL DEFAULT '{}',  -- Agent-specific settings
    enabled BOOLEAN NOT NULL DEFAULT true,
    trigger_stage VARCHAR(50) NOT NULL,  -- 'pre_search', 'post_search', 'response'
    priority INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Many-to-many: Collections ↔ AgentConfigs
CREATE TABLE collection_agents (
    collection_id UUID NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    agent_config_id UUID NOT NULL REFERENCES agent_configs(id) ON DELETE CASCADE,
    PRIMARY KEY (collection_id, agent_config_id)
);

-- Indexes
CREATE INDEX idx_agent_configs_user_id ON agent_configs(user_id);
CREATE INDEX idx_agent_configs_trigger_stage ON agent_configs(trigger_stage);
CREATE INDEX idx_agent_configs_enabled ON agent_configs(enabled);
```

### Example AgentConfig

```json
{
  "id": "abc123...",
  "user_id": "user456...",
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
      "max_slides": 15,
      "template": "corporate"
    }
  },
  "enabled": true,
  "trigger_stage": "response",
  "priority": 10
}
```

## Error Handling

- **Agent Timeout**: Each agent has configurable timeout (default 30s)
- **Agent Failure**: Logged, skipped, pipeline continues
- **Circuit Breaker**: Failing agents disabled after threshold
- **Fallback**: Optional fallback agents for critical stages

## Performance Considerations

1. **Pre-search agents**: Run sequentially (query transformation order matters)
2. **Post-search agents**: Run sequentially (document filtering order matters)
3. **Response agents**: Run in parallel (independent artifact generation)
4. **Caching**: Agent results cached by (query_hash, agent_id, config_hash)
5. **Timeouts**: Per-agent and per-stage timeouts prevent runaway execution

## Observability

- All agent executions logged with structured context
- OpenTelemetry spans for each agent invocation
- Metrics: execution time, success rate, artifact sizes
- Traces flow through Context Forge for end-to-end visibility

## Related Documents

- [MCP Integration Architecture](./mcp-integration-architecture.md)
- [RAG Modulo MCP Server Architecture](./rag-modulo-mcp-server-architecture.md)
- [Agent MCP Architecture Design](../design/agent-mcp-architecture.md)
