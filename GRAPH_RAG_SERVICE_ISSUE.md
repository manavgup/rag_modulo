# Graph RAG Microservice with Neo4j Integration

## Issue Type
🚀 Feature Request - Microservice Architecture Enhancement

## Priority
**Medium** - Strategic enhancement for advanced RAG capabilities

## Summary
Implement a standalone Graph RAG microservice using Neo4j to provide relationship-aware document retrieval and knowledge graph capabilities. This service will run as a separate containerized component that complements the existing vector database architecture.

## Motivation

### Current State
- RAG Modulo uses vector similarity search (Milvus, Elasticsearch, etc.) for document retrieval
- Vector search excels at semantic similarity but lacks understanding of entity relationships
- No native support for graph-based reasoning or knowledge graph construction

### Desired State
- Microservice architecture with dedicated Graph RAG service
- Neo4j-powered knowledge graph for entity relationships and graph traversal
- Hybrid retrieval: Vector search finds candidates, graph enriches context
- Clean separation of concerns with RESTful API between services

### Business Value
- **Enhanced Context**: Graph traversal provides richer, more relevant context than flat chunks
- **Relationship Discovery**: Find documents through entity relationships, not just similarity
- **Knowledge Graph**: Build queryable knowledge graphs from document collections
- **Scalability**: Independent scaling of graph vs vector workloads
- **Flexibility**: Optional feature that doesn't disrupt existing architecture

## Architecture Design

### Microservice Approach

```
┌─────────────────────────────────────────────────────────────────┐
│                     RAG Modulo Backend (FastAPI)                 │
│                                                                   │
│  ┌──────────────────┐         ┌────────────────────────┐        │
│  │  Search Service  │────────▶│  Vector Store Service  │        │
│  │                  │         │  (Milvus/ES/etc)       │        │
│  │                  │         └────────────────────────┘        │
│  │                  │                                            │
│  │                  │         ┌────────────────────────┐        │
│  │                  │────────▶│  Graph RAG Client      │───┐    │
│  └──────────────────┘         │  (HTTP/gRPC)           │   │    │
│                                └────────────────────────┘   │    │
└─────────────────────────────────────────────────────────────┼───┘
                                                               │
                          REST/gRPC API                        │
                                                               │
┌──────────────────────────────────────────────────────────────▼───┐
│              Graph RAG Service (Separate Container)              │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐│
│  │ Entity Extractor │  │ Graph Builder    │  │ Graph Querier  ││
│  │ (NER/Patterns)   │  │ (Relationships)  │  │ (Cypher/Trav.) ││
│  └──────────────────┘  └──────────────────┘  └────────────────┘│
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Neo4j Driver                           │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────┬─┘
                                                                 │
                                                                 │
┌────────────────────────────────────────────────────────────────▼─┐
│                    Neo4j Database (Container)                    │
│                                                                   │
│  • Document & Chunk Nodes          • Vector Indexes             │
│  • Entity Nodes (Person, Org, etc) • Relationship Traversal     │
│  • CONTAINS, NEXT, MENTIONS edges  • Cypher Queries              │
└───────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

**1. Graph RAG Service** (New Python FastAPI Service)
- Entity extraction from document chunks
- Knowledge graph construction in Neo4j
- Graph-based context enrichment
- Relationship querying and traversal
- RESTful API for graph operations

**2. Graph RAG Client** (New module in main backend)
- HTTP client for Graph RAG service
- Request/response models
- Circuit breaker and retry logic
- Fallback to vector-only search if service unavailable

**3. Neo4j Database** (Container)
- Graph database for entities and relationships
- Vector indexes for similarity search
- APOC and GDS plugins for graph algorithms

## Technical Specification

### Graph RAG Service Structure

```
graph_rag_service/
├── Dockerfile
├── pyproject.toml
├── requirements.txt
├── README.md
├── main.py                      # FastAPI application entry point
├── config.py                    # Service configuration
├── core/
│   ├── __init__.py
│   ├── neo4j_client.py         # Neo4j connection management
│   ├── models.py               # Pydantic models
│   └── exceptions.py           # Custom exceptions
├── services/
│   ├── __init__.py
│   ├── entity_extractor.py     # Entity extraction logic
│   ├── graph_builder.py        # Graph construction
│   ├── graph_querier.py        # Query and traversal
│   └── context_enricher.py     # Context enhancement
├── api/
│   ├── __init__.py
│   ├── routes.py               # API endpoints
│   └── schemas.py              # Request/response schemas
├── utils/
│   ├── __init__.py
│   ├── cypher_queries.py       # Reusable Cypher queries
│   └── logging.py              # Structured logging
└── tests/
    ├── unit/
    ├── integration/
    └── conftest.py
```

### API Endpoints

**Graph RAG Service Endpoints:**

```python
# POST /api/v1/graph/collections
# Create knowledge graph collection
{
  "collection_name": "tech_docs",
  "entity_types": ["Person", "Organization", "Technology", "Concept"],
  "relationship_types": ["MENTIONS", "RELATES_TO", "PART_OF"]
}

# POST /api/v1/graph/ingest
# Ingest documents into knowledge graph
{
  "collection_name": "tech_docs",
  "documents": [
    {
      "document_id": "doc_001",
      "chunks": [
        {
          "chunk_id": "chunk_001",
          "text": "Machine learning is a subset of AI...",
          "metadata": {...}
        }
      ]
    }
  ]
}

# POST /api/v1/graph/query
# Query knowledge graph for context enrichment
{
  "collection_name": "tech_docs",
  "chunk_ids": ["chunk_001", "chunk_002"],  # From vector search
  "enrichment_strategy": "surrounding_context",  # or "entity_links", "cross_document"
  "max_depth": 2,
  "max_results": 10
}

# GET /api/v1/graph/entities/{collection_name}
# List entities in collection
# Returns: [{"entity_id": "...", "type": "Person", "name": "...", "mention_count": 5}]

# GET /api/v1/graph/relationships/{collection_name}
# Get relationship statistics
# Returns: {"MENTIONS": 150, "RELATES_TO": 89, ...}

# POST /api/v1/graph/traverse
# Custom graph traversal queries
{
  "collection_name": "tech_docs",
  "start_chunk_id": "chunk_001",
  "traversal_pattern": "(:Chunk)-[:NEXT*1..3]->(:Chunk)",
  "filters": {...}
}

# DELETE /api/v1/graph/collections/{collection_name}
# Delete knowledge graph collection

# GET /api/v1/health
# Health check endpoint
```

**Main Backend Integration:**

```python
# backend/rag_solution/services/graph_rag_client.py

class GraphRAGClient:
    """Client for Graph RAG microservice."""

    async def enrich_search_results(
        self,
        collection_name: str,
        vector_results: list[QueryResult],
        strategy: str = "surrounding_context"
    ) -> list[EnrichedQueryResult]:
        """Enrich vector search results with graph context."""

    async def ingest_documents(
        self,
        collection_name: str,
        documents: list[Document]
    ) -> dict[str, Any]:
        """Send documents to Graph RAG service for ingestion."""
```

### Core Features

#### 1. Entity Extraction

```python
# graph_rag_service/services/entity_extractor.py

class EntityExtractor:
    """Extract entities from text using pattern matching and NER."""

    def extract_entities(
        self,
        text: str,
        entity_types: list[str]
    ) -> list[Entity]:
        """
        Extract entities using:
        - Regex patterns (emails, URLs, dates)
        - spaCy NER for Person, Organization, Location
        - Custom patterns for domain-specific entities
        """

    def link_entities(
        self,
        entities: list[Entity],
        existing_graph: Neo4jGraph
    ) -> list[EntityLink]:
        """
        Link extracted entities to existing graph nodes.
        Performs entity resolution and deduplication.
        """
```

#### 2. Graph Construction

```python
# graph_rag_service/services/graph_builder.py

class GraphBuilder:
    """Build knowledge graph from documents and entities."""

    def create_document_graph(
        self,
        collection_name: str,
        documents: list[Document]
    ) -> GraphStats:
        """
        Create graph structure:
        - Document nodes
        - Chunk nodes with embeddings
        - CONTAINS edges (Document -> Chunk)
        - NEXT edges (Chunk -> Chunk)
        """

    def create_entity_graph(
        self,
        collection_name: str,
        chunks: list[Chunk],
        entities: list[Entity]
    ) -> GraphStats:
        """
        Create entity graph:
        - Entity nodes (Person, Org, etc)
        - MENTIONS edges (Chunk -> Entity)
        - RELATES_TO edges (Entity -> Entity)
        """

    def create_cross_document_links(
        self,
        collection_name: str
    ) -> GraphStats:
        """
        Find and create cross-document relationships:
        - Shared entities
        - Similar topics
        - Reference relationships
        """
```

#### 3. Graph Querying

```python
# graph_rag_service/services/graph_querier.py

class GraphQuerier:
    """Query and traverse knowledge graph."""

    def get_surrounding_context(
        self,
        chunk_id: str,
        max_depth: int = 2
    ) -> list[Chunk]:
        """
        Get surrounding chunks via NEXT relationships.
        Provides document flow context.
        """

    def get_entity_links(
        self,
        chunk_id: str,
        max_depth: int = 2
    ) -> list[tuple[Chunk, Entity, str]]:
        """
        Get chunks linked through shared entities.
        Returns: (chunk, entity, relationship_type)
        """

    def get_cross_document_context(
        self,
        chunk_id: str,
        max_results: int = 5
    ) -> list[Chunk]:
        """
        Find related chunks in other documents.
        Uses entity co-occurrence and topic similarity.
        """

    def execute_cypher(
        self,
        query: str,
        parameters: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Execute custom Cypher query."""
```

#### 4. Context Enrichment

```python
# graph_rag_service/services/context_enricher.py

class ContextEnricher:
    """Enrich search results with graph context."""

    def enrich_results(
        self,
        results: list[ChunkResult],
        strategy: EnrichmentStrategy,
        max_depth: int = 2
    ) -> list[EnrichedResult]:
        """
        Enrich search results using graph traversal.

        Strategies:
        - surrounding_context: Use NEXT edges for document flow
        - entity_links: Use entity relationships
        - cross_document: Find related chunks across documents
        - hybrid: Combine all strategies
        """
```

### Data Models

```python
# graph_rag_service/core/models.py

from pydantic import BaseModel, Field
from typing import Literal

class Entity(BaseModel):
    """Entity extracted from text."""
    entity_id: str
    entity_type: Literal["Person", "Organization", "Technology", "Concept", "Location"]
    name: str
    aliases: list[str] = []
    metadata: dict[str, Any] = {}

class EntityMention(BaseModel):
    """Mention of an entity in a chunk."""
    chunk_id: str
    entity_id: str
    start_index: int
    end_index: int
    confidence: float

class Relationship(BaseModel):
    """Relationship between entities."""
    relationship_type: str
    source_entity_id: str
    target_entity_id: str
    confidence: float
    evidence_chunk_ids: list[str]

class GraphStats(BaseModel):
    """Statistics about knowledge graph."""
    num_documents: int
    num_chunks: int
    num_entities: int
    num_relationships: int
    entity_type_counts: dict[str, int]
    relationship_type_counts: dict[str, int]

class EnrichmentRequest(BaseModel):
    """Request for context enrichment."""
    collection_name: str
    chunk_ids: list[str]
    enrichment_strategy: Literal["surrounding_context", "entity_links", "cross_document", "hybrid"]
    max_depth: int = Field(default=2, ge=1, le=5)
    max_results: int = Field(default=10, ge=1, le=50)

class EnrichedChunk(BaseModel):
    """Chunk enriched with graph context."""
    chunk_id: str
    text: str
    document_id: str
    original_score: float

    # Enrichment data
    surrounding_chunks: list[str] = []  # Chunk IDs
    linked_entities: list[Entity] = []
    cross_document_chunks: list[str] = []
    enrichment_metadata: dict[str, Any] = {}
```

### Neo4j Schema

```cypher
// Document nodes
CREATE CONSTRAINT document_id_unique
IF NOT EXISTS
FOR (d:Document) REQUIRE d.document_id IS UNIQUE;

// Chunk nodes with vector embeddings
CREATE CONSTRAINT chunk_id_unique
IF NOT EXISTS
FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE;

CREATE VECTOR INDEX chunk_embeddings
IF NOT EXISTS
FOR (c:Chunk) ON (c.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 768,
    `vector.similarity_function`: 'cosine'
  }
};

// Entity nodes
CREATE CONSTRAINT entity_id_unique
IF NOT EXISTS
FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE;

CREATE INDEX entity_name_idx
IF NOT EXISTS
FOR (e:Entity) ON (e.name);

// Collection organization
CREATE INDEX collection_name_idx
IF NOT EXISTS
FOR (n) ON (n.collection_name);

// Graph structure
// (Document)-[:CONTAINS]->(Chunk)
// (Chunk)-[:NEXT]->(Chunk)
// (Chunk)-[:MENTIONS]->(Entity)
// (Entity)-[:RELATES_TO]->(Entity)
```

## Implementation Phases

### Phase 1: Foundation (Week 1)
**Goal:** Basic service infrastructure and Neo4j integration

**Tasks:**
- [ ] Create `graph_rag_service/` directory structure
- [ ] Set up FastAPI application with health check endpoint
- [ ] Implement Neo4j connection management
- [ ] Create Docker container for Graph RAG service
- [ ] Add Neo4j container to docker-compose.yml
- [ ] Implement basic logging and configuration
- [ ] Create Pydantic models for API

**Deliverables:**
- Running Graph RAG service container
- Neo4j container with proper configuration
- Health check endpoint functional
- Basic integration tests

**Acceptance Criteria:**
- `docker-compose up` starts all services including Graph RAG
- Health check returns 200 OK
- Neo4j accessible via Bolt protocol
- Service logs to stdout with structured format

### Phase 2: Graph Construction (Week 2)
**Goal:** Document and entity ingestion into Neo4j

**Tasks:**
- [ ] Implement entity extraction service (regex + spaCy)
- [ ] Create graph builder for document structure
- [ ] Implement `/api/v1/graph/collections` endpoint (create)
- [ ] Implement `/api/v1/graph/ingest` endpoint
- [ ] Create Cypher queries for graph construction
- [ ] Add entity resolution and deduplication
- [ ] Implement graph statistics endpoint

**Deliverables:**
- Documents can be ingested into Neo4j
- Entities extracted and stored as nodes
- Graph relationships created (CONTAINS, NEXT, MENTIONS)
- API documentation with examples

**Acceptance Criteria:**
- Ingested documents appear in Neo4j Browser
- Entity extraction accuracy >80% for common types
- Graph statistics endpoint returns correct counts
- Integration tests pass for ingestion flow

### Phase 3: Graph Querying (Week 3)
**Goal:** Context enrichment and graph traversal

**Tasks:**
- [ ] Implement graph querier service
- [ ] Create surrounding context retrieval
- [ ] Create entity-based linking
- [ ] Implement cross-document discovery
- [ ] Implement `/api/v1/graph/query` endpoint
- [ ] Add traversal pattern support
- [ ] Create context enricher service
- [ ] Optimize Cypher queries for performance

**Deliverables:**
- Graph traversal queries functional
- Context enrichment returns relevant results
- Multiple enrichment strategies available
- Performance benchmarks documented

**Acceptance Criteria:**
- Surrounding context retrieval <100ms for depth=2
- Entity linking finds cross-document connections
- Enrichment API returns valid EnrichedChunk objects
- Graph traversal handles edge cases gracefully

### Phase 4: Backend Integration (Week 4)
**Goal:** Integrate Graph RAG service with main backend

**Tasks:**
- [ ] Create Graph RAG client in main backend
- [ ] Add HTTP client with retry logic and circuit breaker
- [ ] Update SearchService to support graph enrichment
- [ ] Add configuration flags for enabling/disabling Graph RAG
- [ ] Create hybrid search strategy (vector + graph)
- [ ] Add fallback handling if Graph RAG unavailable
- [ ] Update API documentation
- [ ] Create end-to-end tests

**Deliverables:**
- SearchService can call Graph RAG service
- Hybrid search returns enriched results
- Graceful degradation if service unavailable
- User documentation for Graph RAG features

**Acceptance Criteria:**
- Search API can enable graph enrichment via query parameter
- Results include graph context when available
- System works normally if Graph RAG service down
- E2E tests cover hybrid search flow

### Phase 5: Advanced Features (Week 5+)
**Goal:** Production-ready features and optimization

**Tasks:**
- [ ] Add entity extraction caching
- [ ] Implement graph pruning strategies
- [ ] Add community detection for topic clustering
- [ ] Create graph analytics endpoints
- [ ] Implement graph export/import
- [ ] Add monitoring and metrics (Prometheus)
- [ ] Create operational runbook
- [ ] Performance optimization and load testing

**Deliverables:**
- Production-ready Graph RAG service
- Monitoring dashboards
- Operational documentation
- Performance benchmarks

**Acceptance Criteria:**
- Service handles 100+ concurrent requests
- P95 latency <200ms for enrichment
- Prometheus metrics available
- Runbook covers common issues

## Docker Configuration

### Graph RAG Service Dockerfile

```dockerfile
# graph_rag_service/Dockerfile

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install Poetry and dependencies
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

# Copy application code
COPY . .

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8001/api/v1/health')"

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
```

### Docker Compose Updates

```yaml
# docker-compose.yml

services:
  # ... existing services ...

  # Neo4j Database
  neo4j:
    image: neo4j:5.15-community
    container_name: rag_neo4j
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD:-password}
      - NEO4J_PLUGINS=["apoc", "graph-data-science"]
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*,gds.*
      - NEO4J_dbms_memory_heap_initial__size=512M
      - NEO4J_dbms_memory_heap_max__size=2G
      - NEO4J_server_memory_pagecache_size=512M
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - neo4j_import:/var/lib/neo4j/import
      - neo4j_plugins:/plugins
    networks:
      - rag_network
    healthcheck:
      test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "${NEO4J_PASSWORD:-password}", "RETURN 1"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Graph RAG Service
  graph-rag-service:
    build:
      context: ./graph_rag_service
      dockerfile: Dockerfile
    container_name: rag_graph_service
    ports:
      - "8001:8001"
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USERNAME=neo4j
      - NEO4J_PASSWORD=${NEO4J_PASSWORD:-password}
      - NEO4J_DATABASE=neo4j
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - GRAPH_RAG_API_KEY=${GRAPH_RAG_API_KEY:-dev-key}
    depends_on:
      neo4j:
        condition: service_healthy
    networks:
      - rag_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Main Backend (updated)
  backend:
    # ... existing config ...
    environment:
      # ... existing env vars ...
      - GRAPH_RAG_SERVICE_URL=http://graph-rag-service:8001
      - GRAPH_RAG_ENABLED=${GRAPH_RAG_ENABLED:-false}
      - GRAPH_RAG_API_KEY=${GRAPH_RAG_API_KEY:-dev-key}
    depends_on:
      # ... existing dependencies ...
      graph-rag-service:
        condition: service_healthy

volumes:
  # ... existing volumes ...
  neo4j_data:
  neo4j_logs:
  neo4j_import:
  neo4j_plugins:

networks:
  rag_network:
    driver: bridge
```

## Configuration

### Environment Variables

```bash
# .env

# Neo4j Configuration
NEO4J_PASSWORD=your_secure_password_here
NEO4J_URI=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_DATABASE=neo4j

# Graph RAG Service Configuration
GRAPH_RAG_ENABLED=true
GRAPH_RAG_SERVICE_URL=http://graph-rag-service:8001
GRAPH_RAG_API_KEY=your_api_key_here
GRAPH_RAG_TIMEOUT=30
GRAPH_RAG_MAX_RETRIES=3

# Graph Features
GRAPH_ENTITY_EXTRACTION=true
GRAPH_ENTITY_TYPES=Person,Organization,Technology,Concept,Location
GRAPH_MAX_TRAVERSAL_DEPTH=3
GRAPH_ENRICHMENT_STRATEGY=hybrid

# Entity Extraction
SPACY_MODEL=en_core_web_sm
ENTITY_MIN_CONFIDENCE=0.7
```

### Service Configuration

```python
# graph_rag_service/config.py

from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    """Graph RAG Service Configuration."""

    # Service
    service_name: str = "graph-rag-service"
    service_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "password"
    neo4j_database: str = "neo4j"
    neo4j_max_connection_pool_size: int = 50
    neo4j_connection_timeout: int = 30

    # Entity Extraction
    spacy_model: str = "en_core_web_sm"
    entity_types: list[str] = ["Person", "Organization", "Technology", "Concept"]
    entity_min_confidence: float = 0.7

    # Graph Configuration
    max_traversal_depth: int = 3
    max_enrichment_results: int = 50
    graph_batch_size: int = 100

    # API Security
    api_key: str = "dev-key"
    cors_origins: list[str] = ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = False
```

## Dependencies

### Graph RAG Service Dependencies

```toml
# graph_rag_service/pyproject.toml

[tool.poetry]
name = "graph-rag-service"
version = "1.0.0"
description = "Graph RAG microservice with Neo4j"
authors = ["RAG Modulo Team"]

[tool.poetry.dependencies]
python = "^3.12"
fastapi = "^0.109.0"
uvicorn = {extras = ["standard"], version = "^0.27.0"}
pydantic = "^2.6.0"
pydantic-settings = "^2.1.0"
neo4j = "^5.15.0"
spacy = "^3.7.0"
httpx = "^0.26.0"
tenacity = "^8.2.3"
prometheus-client = "^0.19.0"
structlog = "^24.1.0"
python-multipart = "^0.0.6"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
pytest-asyncio = "^0.23.0"
pytest-cov = "^4.1.0"
pytest-mock = "^3.12.0"
ruff = "^0.1.14"
mypy = "^1.8.0"
black = "^24.1.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

### Main Backend Updates

```toml
# pyproject.toml (add to existing)

[tool.poetry.dependencies]
# ... existing dependencies ...
httpx = "^0.26.0"         # For Graph RAG client
tenacity = "^8.2.3"       # For retry logic
circuitbreaker = "^1.4.0" # For circuit breaker pattern
```

## Testing Strategy

### Unit Tests

```python
# graph_rag_service/tests/unit/test_entity_extractor.py

import pytest
from services.entity_extractor import EntityExtractor

@pytest.fixture
def extractor():
    return EntityExtractor()

def test_extract_person_entities(extractor):
    text = "John Smith works at Microsoft."
    entities = extractor.extract_entities(text, ["Person", "Organization"])

    assert len(entities) >= 2
    assert any(e.entity_type == "Person" and "John Smith" in e.name for e in entities)
    assert any(e.entity_type == "Organization" and "Microsoft" in e.name for e in entities)

def test_extract_technical_terms(extractor):
    text = "We use machine learning and Python for data analysis."
    entities = extractor.extract_entities(text, ["Technology"])

    assert len(entities) >= 2
    assert any("machine learning" in e.name.lower() for e in entities)
    assert any("python" in e.name.lower() for e in entities)
```

### Integration Tests

```python
# graph_rag_service/tests/integration/test_graph_builder.py

import pytest
from neo4j import GraphDatabase
from services.graph_builder import GraphBuilder

@pytest.fixture
def neo4j_session():
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
    with driver.session() as session:
        yield session
    driver.close()

@pytest.mark.integration
def test_create_document_graph(neo4j_session, graph_builder, sample_documents):
    stats = graph_builder.create_document_graph("test_collection", sample_documents)

    assert stats.num_documents == len(sample_documents)
    assert stats.num_chunks > 0

    # Verify graph structure
    result = neo4j_session.run("""
        MATCH (d:Document_test_collection)-[:CONTAINS]->(c:Chunk_test_collection)
        RETURN count(*) as chunk_count
    """)
    assert result.single()["chunk_count"] == stats.num_chunks
```

### End-to-End Tests

```python
# tests/e2e/test_hybrid_search.py

import pytest
from httpx import AsyncClient

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_search_with_graph_enrichment():
    """Test full hybrid search flow: vector search + graph enrichment."""

    # 1. Ingest documents to both vector store and graph
    async with AsyncClient(base_url="http://localhost:8000") as client:
        response = await client.post(
            "/api/v1/collections/test_collection/documents",
            json={"documents": sample_documents}
        )
        assert response.status_code == 200

    # 2. Perform search with graph enrichment enabled
    async with AsyncClient(base_url="http://localhost:8000") as client:
        response = await client.post(
            "/api/v1/search",
            json={
                "question": "What is machine learning?",
                "collection_id": "test_collection",
                "user_id": "user_123",
                "config_metadata": {
                    "graph_enrichment_enabled": True,
                    "enrichment_strategy": "hybrid"
                }
            }
        )
        assert response.status_code == 200
        results = response.json()

        # 3. Verify enriched results
        assert "results" in results
        assert len(results["results"]) > 0

        # Should include graph context
        first_result = results["results"][0]
        assert "enrichment_metadata" in first_result
        assert first_result["enrichment_metadata"]["strategy"] == "hybrid"
```

## Monitoring & Observability

### Metrics

```python
# graph_rag_service/utils/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# Request metrics
graph_requests_total = Counter(
    'graph_rag_requests_total',
    'Total Graph RAG requests',
    ['endpoint', 'status']
)

graph_request_duration = Histogram(
    'graph_rag_request_duration_seconds',
    'Graph RAG request duration',
    ['endpoint']
)

# Entity extraction metrics
entities_extracted_total = Counter(
    'entities_extracted_total',
    'Total entities extracted',
    ['entity_type']
)

# Graph metrics
graph_nodes_total = Gauge(
    'graph_nodes_total',
    'Total nodes in graph',
    ['collection', 'node_type']
)

graph_relationships_total = Gauge(
    'graph_relationships_total',
    'Total relationships in graph',
    ['collection', 'relationship_type']
)

# Query metrics
graph_traversal_duration = Histogram(
    'graph_traversal_duration_seconds',
    'Graph traversal query duration',
    ['strategy', 'depth']
)
```

### Logging

```python
# graph_rag_service/utils/logging.py

import structlog
import logging

def configure_logging(log_level: str = "INFO"):
    """Configure structured logging."""

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper())
    )
```

## Documentation

### API Documentation

- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`
- OpenAPI JSON: `http://localhost:8001/openapi.json`

### User Documentation

Create `graph_rag_service/README.md`:
- Architecture overview
- API endpoint documentation
- Configuration guide
- Deployment instructions
- Troubleshooting guide

### Developer Documentation

Create `docs/development/graph-rag-service.md`:
- Development setup
- Testing procedures
- Code structure
- Contributing guidelines
- Performance tuning

## Acceptance Criteria

### Phase 1 (Foundation)
- [ ] Graph RAG service container builds successfully
- [ ] Neo4j container starts and is accessible
- [ ] Health check endpoint returns 200 OK
- [ ] Docker Compose starts all services without errors
- [ ] Basic integration tests pass

### Phase 2 (Graph Construction)
- [ ] Documents can be ingested via API
- [ ] Entities extracted with >80% accuracy
- [ ] Graph structure created in Neo4j (verified via Neo4j Browser)
- [ ] Graph statistics endpoint returns accurate counts
- [ ] Integration tests cover ingestion flow

### Phase 3 (Graph Querying)
- [ ] Surrounding context retrieval works correctly
- [ ] Entity-based linking finds cross-document connections
- [ ] Graph traversal queries execute in <100ms for depth=2
- [ ] Context enrichment API returns valid results
- [ ] Performance benchmarks documented

### Phase 4 (Backend Integration)
- [ ] SearchService can call Graph RAG service
- [ ] Hybrid search returns enriched results
- [ ] System handles Graph RAG service unavailability gracefully
- [ ] E2E tests cover hybrid search flow
- [ ] API documentation updated

### Phase 5 (Production Ready)
- [ ] Service handles 100+ concurrent requests
- [ ] P95 latency <200ms for enrichment
- [ ] Prometheus metrics exposed and accurate
- [ ] Monitoring dashboards created
- [ ] Operational runbook complete
- [ ] Load testing completed

## Success Metrics

### Technical Metrics
- **Latency**: P95 < 200ms for graph enrichment
- **Throughput**: 100+ requests/second
- **Availability**: 99.9% uptime
- **Accuracy**: Entity extraction >80% precision/recall
- **Graph Quality**: >70% of entities have cross-document links

### Business Metrics
- **Context Relevance**: 20-30% improvement in context quality (user feedback)
- **Answer Quality**: 15-25% improvement in answer accuracy
- **User Satisfaction**: Increased relevance scores in search results
- **Adoption**: Graph enrichment used in >50% of searches when enabled

## Risks & Mitigations

### Risk 1: Performance Degradation
**Impact:** Graph queries could slow down search responses
**Mitigation:**
- Async graph enrichment (doesn't block vector search)
- Aggressive query timeouts (100-200ms max)
- Caching of frequent graph patterns
- Circuit breaker to disable if too slow

### Risk 2: Neo4j Scaling
**Impact:** Graph database may not scale to large collections
**Mitigation:**
- Start with pilot collections (<100K documents)
- Implement graph pruning strategies
- Use Neo4j Enterprise for clustering (if needed)
- Monitor graph size and query performance

### Risk 3: Entity Extraction Accuracy
**Impact:** Poor entity extraction leads to low-quality graph
**Mitigation:**
- Start with conservative patterns (high precision)
- Implement user feedback for entity validation
- Add domain-specific entity rules
- Consider fine-tuning NER model

### Risk 4: Service Dependency
**Impact:** Graph RAG service downtime affects main app
**Mitigation:**
- Feature flag to enable/disable (default: disabled)
- Graceful degradation (fallback to vector-only search)
- Circuit breaker pattern
- Independent deployment and scaling

### Risk 5: Increased Complexity
**Impact:** Additional service increases operational burden
**Mitigation:**
- Comprehensive documentation
- Automated testing (unit, integration, e2e)
- Monitoring and alerting
- Operational runbook for common issues

## Future Enhancements

### Short Term (3-6 months)
- Fine-tuned entity extraction models
- Graph-based query expansion
- Entity disambiguation and resolution
- Temporal relationship tracking

### Medium Term (6-12 months)
- Community detection for topic clustering
- Graph embeddings for entity similarity
- Multi-hop reasoning queries
- Knowledge graph reasoning (inference)

### Long Term (12+ months)
- Dynamic graph updates (incremental ingestion)
- Distributed graph processing
- Graph neural networks for recommendations
- Cross-lingual entity linking

## References

### Neo4j Documentation
- [Neo4j Vector Search](https://neo4j.com/docs/cypher-manual/current/indexes-for-vector-search/)
- [APOC Procedures](https://neo4j.com/labs/apoc/)
- [Graph Data Science Library](https://neo4j.com/docs/graph-data-science/)

### Research Papers
- [Graph-based Retrieval Augmented Generation (GraphRAG)](https://arxiv.org/abs/2404.16130)
- [Knowledge Graphs for RAG](https://arxiv.org/abs/2310.04835)
- [Entity-centric Contextualization](https://arxiv.org/abs/2309.08354)

### Implementation Examples
- [Microsoft GraphRAG](https://github.com/microsoft/graphrag)
- [LangChain Graph QA](https://python.langchain.com/docs/use_cases/graph/)
- [Neo4j + RAG Examples](https://github.com/neo4j-labs/llm-graph-builder)

## Notes

- This is a **microservice architecture** approach - Graph RAG service is completely independent
- Service can be enabled/disabled via feature flag without code changes
- Follows existing RAG Modulo patterns (FastAPI, Pydantic, Docker)
- No external framework dependencies (LangChain/LlamaIndex) - custom implementation
- Gradual rollout: Start with pilot collections, expand based on success metrics

---

**Estimated Total Effort:** 5-6 weeks (1 developer)
**Estimated Infrastructure Cost:** ~$50-100/month (Neo4j Community Edition, 2 vCPUs, 4GB RAM)
**Priority:** Medium (strategic enhancement, not critical path)
**Complexity:** Medium-High (microservice architecture, graph algorithms)
