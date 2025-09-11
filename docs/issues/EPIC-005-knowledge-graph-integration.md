# EPIC-005: Knowledge Graph Integration

## Epic Overview

**Epic Title:** Implement Advanced Knowledge Graph Integration for Semantic Document Understanding and Relationship Discovery

**Epic Description:**
Build a comprehensive knowledge graph system that moves beyond simple vector search to provide semantic understanding, entity relationship mapping, cross-document connection discovery, and graph-based query answering. This system will extract entities and relationships from documents, construct semantic graphs, enable graph traversal queries, and provide relationship-aware search capabilities.

**Business Value:**
- Enhanced semantic understanding of document collections
- Discovery of hidden relationships across documents
- Improved query answering through relationship awareness
- Better context understanding for complex queries
- Foundation for advanced analytical and research capabilities
- Enable knowledge discovery and insight generation

**Epic Priority:** Medium-High
**Epic Size:** Extra Large (Epic)
**Target Release:** Q3 2025

---

## Technical Architecture

### Current State Analysis
- Simple vector-based retrieval
- No entity recognition or relationship extraction
- No semantic graph construction
- No cross-document relationship discovery
- Limited to keyword and semantic similarity search

### Target Architecture
```
Knowledge Graph Integration Layer
├── Entity Recognition & Extraction Engine
├── Relationship Extraction & Classification
├── Knowledge Graph Construction Service
├── Graph Database Integration (Neo4j/Amazon Neptune)
├── Graph Query Engine
├── Semantic Search Enhancement
├── Relationship Discovery Service
└── Graph Visualization & Exploration
```

---

## Database Schema Changes

### New Tables Required

#### 1. Entities Table
```sql
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_name VARCHAR(500) NOT NULL,
    entity_type VARCHAR(100) NOT NULL, -- 'PERSON', 'ORGANIZATION', 'LOCATION', 'CONCEPT', 'EVENT', 'PRODUCT', etc.
    canonical_name VARCHAR(500), -- Standardized name for deduplication
    description TEXT,
    confidence_score DECIMAL(5,3),
    entity_embedding VECTOR(1536),
    metadata JSONB, -- Additional entity properties
    source_documents UUID[], -- Array of document IDs where entity appears
    first_seen_at TIMESTAMP DEFAULT NOW(),
    last_seen_at TIMESTAMP DEFAULT NOW(),
    mention_count INTEGER DEFAULT 1,

    -- Graph database node ID for reference
    graph_node_id VARCHAR(255),

    CONSTRAINT entities_canonical_name_type_unique UNIQUE (canonical_name, entity_type)
);
```

#### 2. Entity Mentions Table
```sql
CREATE TABLE entity_mentions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID REFERENCES entities(id),
    document_id UUID, -- Reference to documents in the system
    collection_id UUID REFERENCES collections(id),
    mention_text VARCHAR(1000) NOT NULL,
    context_text TEXT, -- Surrounding context
    start_position INTEGER,
    end_position INTEGER,
    confidence_score DECIMAL(5,3),
    extraction_method VARCHAR(100), -- 'NER', 'pattern_matching', 'llm_extraction'
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 3. Relationships Table
```sql
CREATE TABLE relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_entity_id UUID REFERENCES entities(id),
    target_entity_id UUID REFERENCES entities(id),
    relationship_type VARCHAR(200) NOT NULL, -- 'WORKS_FOR', 'LOCATED_IN', 'PART_OF', 'RELATED_TO', etc.
    relationship_direction VARCHAR(20) DEFAULT 'DIRECTED', -- 'DIRECTED', 'UNDIRECTED'
    confidence_score DECIMAL(5,3),
    strength_score DECIMAL(5,3), -- How strong the relationship is
    evidence_text TEXT[], -- Text evidence supporting the relationship
    source_documents UUID[], -- Documents where relationship is mentioned
    extraction_method VARCHAR(100),
    temporal_info JSONB, -- When the relationship occurred/was valid
    metadata JSONB,

    -- Graph database relationship ID for reference
    graph_relationship_id VARCHAR(255),

    first_seen_at TIMESTAMP DEFAULT NOW(),
    last_seen_at TIMESTAMP DEFAULT NOW(),
    mention_count INTEGER DEFAULT 1,

    CONSTRAINT relationships_source_target_type_unique UNIQUE (source_entity_id, target_entity_id, relationship_type)
);
```

#### 4. Knowledge Graph Sessions Table
```sql
CREATE TABLE knowledge_graph_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    collection_id UUID REFERENCES collections(id),
    session_name VARCHAR(255),
    session_type VARCHAR(100), -- 'exploration', 'analysis', 'discovery', 'research'
    query_history JSONB, -- Array of queries and results
    discovered_insights JSONB, -- AI-generated insights
    bookmarked_entities UUID[], -- User-bookmarked entities
    bookmarked_relationships UUID[], -- User-bookmarked relationships
    session_metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_activity_at TIMESTAMP DEFAULT NOW()
);
```

#### 5. Entity Types & Ontology Table
```sql
CREATE TABLE entity_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type_name VARCHAR(100) NOT NULL UNIQUE,
    parent_type_id UUID REFERENCES entity_types(id),
    description TEXT,
    properties_schema JSONB, -- Schema for entity properties
    extraction_patterns JSONB, -- Patterns for extraction
    color_code VARCHAR(7), -- For visualization
    icon_name VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),

    -- Hierarchical structure support
    level INTEGER DEFAULT 0,
    path VARCHAR(1000) -- Materialized path for hierarchy
);
```

#### 6. Relationship Types Table
```sql
CREATE TABLE relationship_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type_name VARCHAR(200) NOT NULL UNIQUE,
    source_entity_types VARCHAR(100)[], -- Allowed source entity types
    target_entity_types VARCHAR(100)[], -- Allowed target entity types
    description TEXT,
    is_symmetric BOOLEAN DEFAULT FALSE,
    inverse_relationship VARCHAR(200), -- For directed relationships
    extraction_patterns JSONB,
    visualization_style JSONB, -- Style for graph visualization
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 7. Graph Analysis Results Table
```sql
CREATE TABLE graph_analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_id UUID REFERENCES collections(id),
    analysis_type VARCHAR(100), -- 'centrality', 'clustering', 'path_analysis', 'community_detection'
    analysis_parameters JSONB,
    results JSONB, -- Analysis results and metrics
    entity_scores JSONB, -- Scores for individual entities
    relationship_scores JSONB, -- Scores for relationships
    insights TEXT[], -- Generated insights
    visualization_data JSONB, -- Data for visualization
    created_at TIMESTAMP DEFAULT NOW(),
    analysis_duration_ms INTEGER
);
```

---

## Graph Database Integration

### Neo4j Schema Design
```cypher
// Entity node constraints
CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT entity_canonical_name IF NOT EXISTS FOR (e:Entity) REQUIRE (e.canonical_name, e.type) IS UNIQUE;

// Relationship constraints
CREATE CONSTRAINT relationship_id IF NOT EXISTS FOR ()-[r:RELATIONSHIP]-() REQUIRE r.id IS UNIQUE;

// Indexes for performance
CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.type);
CREATE INDEX entity_name_index IF NOT EXISTS FOR (e:Entity) ON (e.name);
CREATE INDEX relationship_type_index IF NOT EXISTS FOR ()-[r:RELATIONSHIP]-() ON (r.type);

// Entity node structure
(:Entity {
    id: "uuid",
    name: "entity_name",
    canonical_name: "standardized_name",
    type: "PERSON|ORGANIZATION|LOCATION|...",
    description: "entity_description",
    confidence: 0.95,
    embedding: [0.1, 0.2, ...], // Vector embedding
    properties: {...}, // Additional properties
    first_seen: datetime(),
    last_seen: datetime(),
    mention_count: 10
})

// Relationship structure
()-[:RELATIONSHIP {
    id: "uuid",
    type: "WORKS_FOR|LOCATED_IN|...",
    confidence: 0.87,
    strength: 0.92,
    evidence: ["text1", "text2"],
    temporal_start: datetime(),
    temporal_end: datetime(),
    first_seen: datetime(),
    last_seen: datetime(),
    mention_count: 5
}]-()
```

---

## New Models Required

### 1. Entity Model (`backend/rag_solution/models/entity.py`)
```python
from sqlalchemy import String, DateTime, JSON, DECIMAL, Integer, ARRAY, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Dict, List, Any, Optional
import uuid
from datetime import datetime
from rag_solution.file_management.database import Base

class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_name: Mapped[str] = mapped_column(String(500), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    canonical_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(DECIMAL(5,3), nullable=True)
    entity_embedding: Mapped[Optional[List[float]]] = mapped_column(None, nullable=True)  # Vector type
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    source_documents: Mapped[Optional[List[str]]] = mapped_column(ARRAY(UUID), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    mention_count: Mapped[int] = mapped_column(Integer, default=1)
    graph_node_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    mentions: Mapped[List["EntityMention"]] = relationship("EntityMention", back_populates="entity")
    source_relationships: Mapped[List["Relationship"]] = relationship("Relationship",
                                                                    foreign_keys="Relationship.source_entity_id",
                                                                    back_populates="source_entity")
    target_relationships: Mapped[List["Relationship"]] = relationship("Relationship",
                                                                    foreign_keys="Relationship.target_entity_id",
                                                                    back_populates="target_entity")
```

### 2. Entity Mention Model (`backend/rag_solution/models/entity_mention.py`)
### 3. Relationship Model (`backend/rag_solution/models/relationship.py`)
### 4. Knowledge Graph Session Model (`backend/rag_solution/models/knowledge_graph_session.py`)
### 5. Entity Type Model (`backend/rag_solution/models/entity_type.py`)
### 6. Relationship Type Model (`backend/rag_solution/models/relationship_type.py`)
### 7. Graph Analysis Result Model (`backend/rag_solution/models/graph_analysis_result.py`)

---

## New Schemas Required

### 1. Entity Schemas (`backend/rag_solution/schemas/entity_schema.py`)
```python
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
from enum import Enum

class EntityType(str, Enum):
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    LOCATION = "LOCATION"
    CONCEPT = "CONCEPT"
    EVENT = "EVENT"
    PRODUCT = "PRODUCT"
    TECHNOLOGY = "TECHNOLOGY"
    DATE = "DATE"
    MONEY = "MONEY"
    PERCENT = "PERCENT"

class ExtractionMethod(str, Enum):
    NER = "NER"
    PATTERN_MATCHING = "pattern_matching"
    LLM_EXTRACTION = "llm_extraction"
    MANUAL = "manual"

class EntityBase(BaseModel):
    entity_name: str = Field(..., min_length=1, max_length=500)
    entity_type: EntityType
    canonical_name: Optional[str] = None
    description: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = None

class EntityCreate(EntityBase):
    source_documents: Optional[List[uuid.UUID]] = None

class EntityUpdate(BaseModel):
    entity_name: Optional[str] = None
    canonical_name: Optional[str] = None
    description: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = None

class Entity(EntityBase):
    id: uuid.UUID
    source_documents: Optional[List[uuid.UUID]]
    first_seen_at: datetime
    last_seen_at: datetime
    mention_count: int
    graph_node_id: Optional[str]

    class Config:
        from_attributes = True

class EntityMentionBase(BaseModel):
    mention_text: str = Field(..., min_length=1, max_length=1000)
    context_text: Optional[str] = None
    start_position: Optional[int] = None
    end_position: Optional[int] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    extraction_method: ExtractionMethod
    metadata: Optional[Dict[str, Any]] = None

class EntityMentionCreate(EntityMentionBase):
    entity_id: uuid.UUID
    document_id: Optional[uuid.UUID] = None
    collection_id: Optional[uuid.UUID] = None

class EntityMention(EntityMentionBase):
    id: uuid.UUID
    entity_id: uuid.UUID
    document_id: Optional[uuid.UUID]
    collection_id: Optional[uuid.UUID]
    created_at: datetime

    class Config:
        from_attributes = True
```

### 2. Relationship Schemas (`backend/rag_solution/schemas/relationship_schema.py`)
### 3. Knowledge Graph Schemas (`backend/rag_solution/schemas/knowledge_graph_schema.py`)

---

## New Services Required

### 1. Entity Recognition Service (`backend/rag_solution/services/entity_recognition_service.py`)
**Responsibilities:**
- Extract entities from documents
- Classify entity types
- Handle entity disambiguation

**Key Methods:**
```python
class EntityRecognitionService:
    async def extract_entities_from_text(self, text: str, document_id: Optional[UUID] = None) -> List[EntityCreate]
    async def extract_entities_from_document(self, document_id: UUID) -> List[Entity]
    async def classify_entity_type(self, entity_text: str, context: str) -> EntityType
    async def disambiguate_entity(self, entity_text: str, context: str, existing_entities: List[Entity]) -> Optional[Entity]
    async def generate_entity_embedding(self, entity: Entity) -> List[float]
    async def batch_process_documents(self, document_ids: List[UUID]) -> Dict[UUID, List[Entity]]
```

### 2. Relationship Extraction Service (`backend/rag_solution/services/relationship_extraction_service.py`)
**Responsibilities:**
- Extract relationships between entities
- Classify relationship types
- Calculate relationship confidence

**Key Methods:**
```python
class RelationshipExtractionService:
    async def extract_relationships_from_text(self, text: str, entities: List[Entity]) -> List[Relationship]
    async def extract_relationships_from_document(self, document_id: UUID) -> List[Relationship]
    async def classify_relationship_type(self, source_entity: Entity, target_entity: Entity, context: str) -> str
    async def calculate_relationship_confidence(self, relationship: Relationship, evidence: List[str]) -> float
    async def identify_temporal_relationships(self, text: str, entities: List[Entity]) -> List[Dict[str, Any]]
    async def merge_duplicate_relationships(self, relationships: List[Relationship]) -> List[Relationship]
```

### 3. Knowledge Graph Service (`backend/rag_solution/services/knowledge_graph_service.py`)
**Responsibilities:**
- Manage knowledge graph construction
- Handle graph database operations
- Coordinate entity and relationship services

**Key Methods:**
```python
class KnowledgeGraphService:
    async def build_knowledge_graph(self, collection_id: UUID) -> Dict[str, Any]
    async def update_knowledge_graph(self, collection_id: UUID, new_documents: List[UUID]) -> Dict[str, Any]
    async def get_entity_neighborhood(self, entity_id: UUID, depth: int = 2) -> Dict[str, Any]
    async def find_path_between_entities(self, source_entity_id: UUID, target_entity_id: UUID) -> List[Dict[str, Any]]
    async def get_graph_statistics(self, collection_id: UUID) -> Dict[str, Any]
    async def export_graph_data(self, collection_id: UUID, format: str = "json") -> str
```

### 4. Graph Database Service (`backend/rag_solution/services/graph_database_service.py`)
**Responsibilities:**
- Interface with Neo4j/Neptune
- Execute graph queries
- Manage graph database operations

**Key Methods:**
```python
class GraphDatabaseService:
    async def create_entity_node(self, entity: Entity) -> str
    async def create_relationship_edge(self, relationship: Relationship) -> str
    async def update_entity_node(self, entity_id: UUID, updates: Dict[str, Any]) -> bool
    async def delete_entity_node(self, entity_id: UUID) -> bool
    async def execute_cypher_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]
    async def find_nodes_by_property(self, property_name: str, value: Any) -> List[Dict[str, Any]]
    async def get_node_relationships(self, node_id: str, direction: str = "BOTH") -> List[Dict[str, Any]]
```

### 5. Graph Query Service (`backend/rag_solution/services/graph_query_service.py`)
**Responsibilities:**
- Handle complex graph queries
- Generate graph-based answers
- Perform graph analysis

**Key Methods:**
```python
class GraphQueryService:
    async def query_entities_by_type(self, entity_type: str, collection_id: UUID) -> List[Entity]
    async def query_relationships_by_type(self, relationship_type: str, collection_id: UUID) -> List[Relationship]
    async def find_central_entities(self, collection_id: UUID, centrality_type: str = "betweenness") -> List[Dict[str, Any]]
    async def detect_communities(self, collection_id: UUID, algorithm: str = "louvain") -> List[Dict[str, Any]]
    async def analyze_entity_importance(self, collection_id: UUID) -> Dict[UUID, float]
    async def generate_graph_insights(self, collection_id: UUID) -> List[str]
```

### 6. Semantic Search Enhancement Service (`backend/rag_solution/services/semantic_search_enhancement_service.py`)
**Responsibilities:**
- Enhance search with graph context
- Provide relationship-aware results
- Integrate graph data with vector search

---

## New Router Endpoints Required

### 1. Entity Router (`backend/rag_solution/router/entity_router.py`)
```python
# Entity management
POST   /api/v1/entities                           # Create new entity
GET    /api/v1/entities                           # List entities
GET    /api/v1/entities/{entity_id}               # Get entity details
PUT    /api/v1/entities/{entity_id}               # Update entity
DELETE /api/v1/entities/{entity_id}               # Delete entity
GET    /api/v1/entities/search                    # Search entities
GET    /api/v1/entities/types                     # Get entity types

# Entity mentions
GET    /api/v1/entities/{entity_id}/mentions      # Get entity mentions
POST   /api/v1/entities/{entity_id}/mentions      # Add mention
DELETE /api/v1/entities/{entity_id}/mentions/{mention_id}  # Delete mention

# Entity relationships
GET    /api/v1/entities/{entity_id}/relationships # Get entity relationships
GET    /api/v1/entities/{entity_id}/neighborhood  # Get entity neighborhood
```

### 2. Relationship Router (`backend/rag_solution/router/relationship_router.py`)
```python
# Relationship management
POST   /api/v1/relationships                      # Create new relationship
GET    /api/v1/relationships                      # List relationships
GET    /api/v1/relationships/{relationship_id}    # Get relationship details
PUT    /api/v1/relationships/{relationship_id}    # Update relationship
DELETE /api/v1/relationships/{relationship_id}    # Delete relationship
GET    /api/v1/relationships/search               # Search relationships
GET    /api/v1/relationships/types                # Get relationship types

# Relationship analysis
GET    /api/v1/relationships/between/{source_id}/{target_id}  # Find relationships between entities
GET    /api/v1/relationships/paths/{source_id}/{target_id}   # Find paths between entities
```

### 3. Knowledge Graph Router (`backend/rag_solution/router/knowledge_graph_router.py`)
```python
# Graph construction
POST   /api/v1/knowledge-graph/build/{collection_id}         # Build knowledge graph
POST   /api/v1/knowledge-graph/update/{collection_id}        # Update knowledge graph
GET    /api/v1/knowledge-graph/status/{collection_id}        # Get build status
DELETE /api/v1/knowledge-graph/{collection_id}               # Delete knowledge graph

# Graph exploration
GET    /api/v1/knowledge-graph/{collection_id}/entities      # Get graph entities
GET    /api/v1/knowledge-graph/{collection_id}/relationships # Get graph relationships
GET    /api/v1/knowledge-graph/{collection_id}/statistics    # Get graph statistics
POST   /api/v1/knowledge-graph/{collection_id}/query         # Execute graph query

# Graph analysis
POST   /api/v1/knowledge-graph/{collection_id}/analyze       # Perform graph analysis
GET    /api/v1/knowledge-graph/{collection_id}/insights      # Get insights
GET    /api/v1/knowledge-graph/{collection_id}/central-entities  # Get central entities
POST   /api/v1/knowledge-graph/{collection_id}/communities   # Detect communities
```

### 4. Graph Query Router (`backend/rag_solution/router/graph_query_router.py`)
```python
# Advanced queries
POST   /api/v1/graph-query/cypher                 # Execute Cypher query
POST   /api/v1/graph-query/natural-language       # Natural language graph query
POST   /api/v1/graph-query/path-analysis          # Path analysis between entities
POST   /api/v1/graph-query/similarity             # Find similar entities
POST   /api/v1/graph-query/recommendation         # Entity recommendations

# Search enhancement
POST   /api/v1/graph-query/enhanced-search        # Graph-enhanced search
GET    /api/v1/graph-query/search-suggestions     # Get search suggestions based on graph
```

---

## Frontend Changes Required

### 1. New React Components

#### Knowledge Graph Visualization (`webui/src/components/KnowledgeGraph/`)
- `GraphVisualization.jsx` - Interactive graph visualization
- `EntityNode.jsx` - Entity node component
- `RelationshipEdge.jsx` - Relationship edge component
- `GraphControls.jsx` - Graph manipulation controls
- `GraphLegend.jsx` - Graph legend and filters
- `GraphMinimap.jsx` - Graph overview and navigation

#### Entity Management (`webui/src/components/EntityManagement/`)
- `EntityBrowser.jsx` - Browse and search entities
- `EntityDetails.jsx` - Detailed entity information
- `EntityRelationships.jsx` - Entity relationship view
- `EntityTimeline.jsx` - Entity mention timeline
- `EntityMerging.jsx` - Merge duplicate entities
- `EntityTypeManager.jsx` - Manage entity types

#### Graph Exploration (`webui/src/components/GraphExploration/`)
- `GraphExplorer.jsx` - Main graph exploration interface
- `PathAnalysis.jsx` - Path analysis between entities
- `CommunityDetection.jsx` - Community detection visualization
- `CentralityAnalysis.jsx` - Centrality analysis results
- `GraphInsights.jsx` - AI-generated graph insights
- `GraphQuery.jsx` - Natural language graph queries

#### Enhanced Search Interface
- Update `SearchInterface.jsx` to include graph context
- Add entity and relationship filters
- Display graph-enhanced search results
- Show entity context in search results

### 2. New Context Providers
- `KnowledgeGraphContext.jsx` - Manage graph state
- `EntityContext.jsx` - Manage entity state
- `GraphVisualizationContext.jsx` - Manage visualization state

### 3. New Libraries and Dependencies
```json
{
  "vis-network": "^9.1.2",              // Graph visualization
  "cytoscape": "^3.23.0",               // Alternative graph library
  "react-cytoscapejs": "^2.0.0",        // React wrapper for Cytoscape
  "d3": "^7.6.1",                       // Advanced visualizations
  "react-force-graph": "^1.41.13",      // Force-directed graph
  "sigma": "^2.4.0",                    // High-performance graph rendering
  "graphology": "^0.24.1",              // Graph data structure library
  "@neo4j/cypher-query-language": "^1.0.5", // Cypher query support
  "react-json-tree": "^0.17.0"          // JSON tree visualization
}
```

### 4. Enhanced Features
- **Interactive Graph Exploration**: Zoom, pan, filter, and search
- **Multi-level Detail**: From overview to detailed entity information
- **Real-time Updates**: Live graph updates as documents are processed
- **Export Capabilities**: Export graph data and visualizations
- **Graph Analytics**: Built-in analysis tools and metrics

---

## Database Migration Scripts

### Migration Script: `migrations/add_knowledge_graph_tables.sql`
```sql
-- Create vector extension if not exists
CREATE EXTENSION IF NOT EXISTS vector;

-- Create knowledge graph tables
-- (Include all CREATE TABLE statements from above)

-- Create indexes for performance
CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_canonical_name ON entities(canonical_name);
CREATE INDEX idx_entities_mention_count ON entities(mention_count DESC);
CREATE INDEX idx_entity_mentions_entity_id ON entity_mentions(entity_id);
CREATE INDEX idx_entity_mentions_document_id ON entity_mentions(document_id);
CREATE INDEX idx_entity_mentions_collection_id ON entity_mentions(collection_id);
CREATE INDEX idx_relationships_source_entity ON relationships(source_entity_id);
CREATE INDEX idx_relationships_target_entity ON relationships(target_entity_id);
CREATE INDEX idx_relationships_type ON relationships(relationship_type);
CREATE INDEX idx_relationships_confidence ON relationships(confidence_score DESC);
CREATE INDEX idx_graph_sessions_user_id ON knowledge_graph_sessions(user_id);
CREATE INDEX idx_graph_sessions_collection_id ON knowledge_graph_sessions(collection_id);

-- Create vector indexes for entity embeddings
CREATE INDEX idx_entities_embedding ON entities
USING ivfflat (entity_embedding vector_cosine_ops) WITH (lists = 100);

-- Create entity normalization function
CREATE OR REPLACE FUNCTION normalize_entity_name(entity_name TEXT)
RETURNS TEXT AS $$
BEGIN
    -- Basic normalization: lowercase, trim, collapse whitespace
    RETURN TRIM(REGEXP_REPLACE(LOWER(entity_name), '\s+', ' ', 'g'));
END;
$$ LANGUAGE plpgsql;

-- Create entity deduplication function
CREATE OR REPLACE FUNCTION find_similar_entities(
    entity_name TEXT,
    entity_type TEXT,
    similarity_threshold DECIMAL DEFAULT 0.8
) RETURNS TABLE(id UUID, name TEXT, similarity DECIMAL) AS $$
BEGIN
    RETURN QUERY
    SELECT e.id, e.entity_name,
           SIMILARITY(normalize_entity_name(entity_name), normalize_entity_name(e.entity_name)) as sim
    FROM entities e
    WHERE e.entity_type = find_similar_entities.entity_type
    AND SIMILARITY(normalize_entity_name(entity_name), normalize_entity_name(e.entity_name)) >= similarity_threshold
    ORDER BY sim DESC;
END;
$$ LANGUAGE plpgsql;

-- Create relationship strength calculation function
CREATE OR REPLACE FUNCTION calculate_relationship_strength(
    relationship_id UUID
) RETURNS DECIMAL AS $$
DECLARE
    strength DECIMAL;
    mention_count INTEGER;
    confidence DECIMAL;
BEGIN
    SELECT r.mention_count, r.confidence_score
    INTO mention_count, confidence
    FROM relationships r
    WHERE r.id = relationship_id;

    -- Calculate strength based on mention count and confidence
    strength := LEAST(1.0, (LOG(mention_count + 1) / 5.0) * confidence);

    RETURN strength;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to update entity last_seen_at on new mentions
CREATE OR REPLACE FUNCTION update_entity_last_seen()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE entities
    SET last_seen_at = NOW(),
        mention_count = mention_count + 1
    WHERE id = NEW.entity_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER entity_mention_update_trigger
    AFTER INSERT ON entity_mentions
    FOR EACH ROW EXECUTE FUNCTION update_entity_last_seen();
```

---

## Graph Database Setup

### Neo4j Configuration
```yaml
# docker-compose.yml addition for Neo4j
neo4j:
  image: neo4j:5.13
  container_name: rag_modulo_neo4j
  environment:
    NEO4J_AUTH: neo4j/password
    NEO4J_PLUGINS: '["apoc", "graph-data-science"]'
    NEO4J_apoc_export_file_enabled: true
    NEO4J_apoc_import_file_enabled: true
    NEO4J_dbms_security_procedures_unrestricted: apoc.*,gds.*
  ports:
    - "7474:7474"  # HTTP
    - "7687:7687"  # Bolt
  volumes:
    - neo4j_data:/data
    - neo4j_logs:/logs
    - neo4j_conf:/conf
    - neo4j_plugins:/plugins
```

### Graph Database Initialization Script
```cypher
// Create constraints and indexes
CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT entity_canonical IF NOT EXISTS FOR (e:Entity) REQUIRE (e.canonical_name, e.type) IS UNIQUE;
CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.type);
CREATE INDEX entity_name_index IF NOT EXISTS FOR (e:Entity) ON (e.name);
CREATE INDEX relationship_type_index IF NOT EXISTS FOR ()-[r:RELATIONSHIP]-() ON (r.type);

// Create sample entity types
MERGE (person:EntityType {name: "PERSON", color: "#FF6B6B"})
MERGE (org:EntityType {name: "ORGANIZATION", color: "#4ECDC4"})
MERGE (loc:EntityType {name: "LOCATION", color: "#45B7D1"})
MERGE (concept:EntityType {name: "CONCEPT", color: "#96CEB4"});
```

---

## Testing Strategy

### Atomic Tests
Create `backend/tests/atomic/test_knowledge_graph_models.py`:
- `test_entity_model_creation()` - Test Entity model instantiation
- `test_entity_mention_model_creation()` - Test EntityMention model
- `test_relationship_model_creation()` - Test Relationship model
- `test_knowledge_graph_session_model_creation()` - Test KnowledgeGraphSession model
- `test_entity_type_model_creation()` - Test EntityType model
- `test_relationship_type_model_creation()` - Test RelationshipType model
- `test_entity_schema_validation()` - Test Pydantic schema validation
- `test_relationship_schema_validation()` - Test relationship schema validation

### Unit Tests

#### Entity Recognition Service Tests (`backend/tests/unit/test_entity_recognition_service.py`)
- `test_extract_entities_from_text()` - Test entity extraction
- `test_classify_entity_type()` - Test entity type classification
- `test_disambiguate_entity()` - Test entity disambiguation
- `test_generate_entity_embedding()` - Test embedding generation
- `test_batch_process_documents()` - Test batch processing
- `test_handle_multilingual_entities()` - Test multilingual support

#### Relationship Extraction Service Tests (`backend/tests/unit/test_relationship_extraction_service.py`)
- `test_extract_relationships_from_text()` - Test relationship extraction
- `test_classify_relationship_type()` - Test relationship classification
- `test_calculate_relationship_confidence()` - Test confidence calculation
- `test_identify_temporal_relationships()` - Test temporal relationship extraction
- `test_merge_duplicate_relationships()` - Test relationship deduplication

#### Knowledge Graph Service Tests (`backend/tests/unit/test_knowledge_graph_service.py`)
- `test_build_knowledge_graph()` - Test graph construction
- `test_update_knowledge_graph()` - Test incremental updates
- `test_get_entity_neighborhood()` - Test neighborhood queries
- `test_find_path_between_entities()` - Test path finding
- `test_get_graph_statistics()` - Test statistics calculation
- `test_export_graph_data()` - Test data export

#### Graph Database Service Tests (`backend/tests/unit/test_graph_database_service.py`)
- `test_create_entity_node()` - Test node creation
- `test_create_relationship_edge()` - Test edge creation
- `test_execute_cypher_query()` - Test query execution
- `test_find_nodes_by_property()` - Test property-based search
- `test_get_node_relationships()` - Test relationship retrieval

#### Graph Query Service Tests (`backend/tests/unit/test_graph_query_service.py`)
- `test_query_entities_by_type()` - Test entity type queries
- `test_find_central_entities()` - Test centrality analysis
- `test_detect_communities()` - Test community detection
- `test_analyze_entity_importance()` - Test importance analysis
- `test_generate_graph_insights()` - Test insight generation

### Integration Tests

#### Knowledge Graph Integration Tests (`backend/tests/integration/test_knowledge_graph_integration.py`)
- `test_end_to_end_graph_construction()` - Test complete graph building
- `test_entity_relationship_extraction_pipeline()` - Test extraction pipeline
- `test_graph_database_synchronization()` - Test PostgreSQL-Neo4j sync
- `test_incremental_graph_updates()` - Test incremental updates
- `test_graph_query_performance()` - Test query performance

#### Graph Database Integration Tests (`backend/tests/integration/test_graph_database_integration.py`)
- `test_neo4j_connection()` - Test Neo4j connectivity
- `test_graph_crud_operations()` - Test CRUD operations
- `test_complex_graph_queries()` - Test complex queries
- `test_graph_analysis_algorithms()` - Test analysis algorithms
- `test_data_consistency()` - Test data consistency between systems

#### Search Enhancement Tests (`backend/tests/integration/test_search_enhancement.py`)
- `test_graph_enhanced_search()` - Test enhanced search
- `test_entity_context_in_results()` - Test entity context
- `test_relationship_aware_ranking()` - Test relationship-based ranking
- `test_semantic_search_with_graph()` - Test semantic enhancement

### E2E Tests

#### Frontend Knowledge Graph Tests (`backend/tests/e2e/test_knowledge_graph_ui.py`)
- `test_graph_visualization_interface()` - Test graph visualization
- `test_entity_exploration_flow()` - Test entity exploration
- `test_relationship_discovery_ui()` - Test relationship discovery
- `test_graph_query_interface()` - Test query interface
- `test_graph_analysis_dashboard()` - Test analysis dashboard

#### API Integration Tests (`backend/tests/e2e/test_knowledge_graph_api.py`)
- `test_entity_management_api()` - Test entity API workflow
- `test_relationship_management_api()` - Test relationship API
- `test_knowledge_graph_api()` - Test graph management API
- `test_graph_query_api()` - Test query API
- `test_knowledge_graph_full_workflow()` - Test complete workflow

### Performance Tests

#### Knowledge Graph Performance Tests (`backend/tests/performance/test_knowledge_graph_performance.py`)
- `test_large_graph_construction()` - Test large graph building
- `test_entity_extraction_throughput()` - Test extraction performance
- `test_graph_query_performance()` - Test query response times
- `test_concurrent_graph_operations()` - Test concurrent operations
- `test_graph_visualization_performance()` - Test visualization performance

---

## Success Criteria & Milestones

### Milestone 1: Core Infrastructure (Week 1-3)
**Success Criteria:**
- [ ] All database tables created and migrated
- [ ] All models implemented with proper relationships
- [ ] All schemas defined with validation
- [ ] Neo4j integration functional
- [ ] Basic entity and relationship services working
- [ ] Atomic tests passing (100% coverage)

**Deliverables:**
- Database migration scripts
- Model classes with relationships
- Pydantic schemas with validation
- Neo4j setup and configuration
- Basic services implementation
- Atomic test suite

### Milestone 2: Entity Recognition System (Week 4-6)
**Success Criteria:**
- [ ] Entity extraction from text functional
- [ ] Entity type classification accurate
- [ ] Entity disambiguation working
- [ ] Entity embedding generation functional
- [ ] Batch processing capabilities
- [ ] Unit tests passing (90%+ coverage)

**Deliverables:**
- Entity recognition service
- Entity classification algorithms
- Disambiguation logic
- Embedding generation
- Batch processing system
- Unit test suite

### Milestone 3: Relationship Extraction (Week 7-9)
**Success Criteria:**
- [ ] Relationship extraction functional
- [ ] Relationship type classification working
- [ ] Confidence scoring accurate
- [ ] Temporal relationship extraction
- [ ] Relationship deduplication
- [ ] Integration tests passing

**Deliverables:**
- Relationship extraction service
- Classification algorithms
- Confidence scoring system
- Temporal analysis
- Deduplication logic
- Integration test suite

### Milestone 4: Knowledge Graph Construction (Week 10-12)
**Success Criteria:**
- [ ] Graph construction pipeline functional
- [ ] Incremental graph updates working
- [ ] Graph database synchronization
- [ ] Graph statistics and metrics
- [ ] Data export capabilities
- [ ] Performance benchmarks met

**Deliverables:**
- Knowledge graph service
- Graph construction pipeline
- Update mechanisms
- Statistics calculation
- Export functionality
- Performance optimization

### Milestone 5: Graph Query & Analysis (Week 13-15)
**Success Criteria:**
- [ ] Graph query engine functional
- [ ] Centrality analysis working
- [ ] Community detection implemented
- [ ] Path analysis functional
- [ ] Insight generation working
- [ ] Query performance optimized

**Deliverables:**
- Graph query service
- Analysis algorithms
- Community detection
- Path finding algorithms
- Insight generation
- Query optimization

### Milestone 6: Search Enhancement (Week 16-17)
**Success Criteria:**
- [ ] Graph-enhanced search functional
- [ ] Entity context in search results
- [ ] Relationship-aware ranking
- [ ] Search suggestion system
- [ ] Performance benchmarks met

**Deliverables:**
- Search enhancement service
- Context integration
- Ranking algorithms
- Suggestion system
- Performance optimization

### Milestone 7: API & Backend Complete (Week 18-19)
**Success Criteria:**
- [ ] All REST API endpoints implemented
- [ ] Real-time graph updates functional
- [ ] API integration tests passing
- [ ] Error handling comprehensive
- [ ] Performance optimized

**Deliverables:**
- Complete REST API
- Real-time update system
- API documentation
- Error handling framework
- Performance optimization

### Milestone 8: Frontend Implementation (Week 20-24)
**Success Criteria:**
- [ ] Graph visualization functional
- [ ] Entity management interface complete
- [ ] Graph exploration tools working
- [ ] Analysis dashboard functional
- [ ] E2E tests passing

**Deliverables:**
- Graph visualization components
- Entity management interface
- Exploration tools
- Analysis dashboard
- Complete frontend integration

### Milestone 9: Production Readiness (Week 25-26)
**Success Criteria:**
- [ ] Performance tests passing
- [ ] Security review passed
- [ ] Documentation complete
- [ ] Load testing successful
- [ ] User acceptance testing completed

**Deliverables:**
- Performance test suite
- Security audit results
- Complete documentation
- Load testing reports
- Production deployment

---

## Risk Assessment & Mitigation

### High Risks
1. **Entity recognition accuracy and consistency**
   - *Mitigation:* Use multiple extraction methods, implement validation, add human feedback loops

2. **Graph database performance with large datasets**
   - *Mitigation:* Implement proper indexing, query optimization, consider sharding strategies

3. **Complexity of relationship extraction and classification**
   - *Mitigation:* Start with simple relationships, use proven NLP libraries, iterative improvement

### Medium Risks
1. **Data synchronization between PostgreSQL and Neo4j**
   - *Mitigation:* Implement robust sync mechanisms, add consistency checks, use event-driven updates

2. **Graph visualization performance with large graphs**
   - *Mitigation:* Implement graph pruning, level-of-detail rendering, virtualization techniques

### Low Risks
1. **Learning curve for graph query languages**
   - *Mitigation:* Provide natural language query interface, add query templates, comprehensive documentation

2. **Integration complexity with existing RAG pipeline**
   - *Mitigation:* Implement gradual integration, maintain backward compatibility

---

## Dependencies

### Internal Dependencies
- Agent Orchestration Framework (EPIC-001)
- Workflow Engine (EPIC-002)
- Memory & Context Management (EPIC-003)
- Chain-of-Thought Reasoning (EPIC-004)
- Existing document processing pipeline

### External Dependencies
- Neo4j or Amazon Neptune for graph database
- Advanced NLP libraries for entity/relationship extraction
- Graph visualization libraries
- High-performance computing resources for large graphs

---

## Post-Epic Considerations

### Future Enhancements
1. Advanced graph machine learning algorithms
2. Automated ontology learning and evolution
3. Multi-modal knowledge graphs (text, images, videos)
4. Federated knowledge graphs across collections
5. Real-time collaborative graph editing

### Technical Debt
1. Consider distributed graph processing for scale
2. Implement comprehensive graph analytics
3. Add graph versioning and change tracking
4. Consider graph neural networks for advanced analysis

---

## Privacy & Security Considerations

### Data Privacy
- Entity and relationship data encryption
- User control over knowledge graph visibility
- Anonymization options for sensitive entities
- Compliance with data protection regulations

### Security Measures
- Access control for graph data
- Audit logging for graph operations
- Data validation and sanitization
- Rate limiting for graph queries

---

## Definition of Done

### Epic-Level DoD
- [ ] All user stories completed and accepted
- [ ] All tests passing (atomic, unit, integration, E2E, performance)
- [ ] Documentation complete and reviewed
- [ ] Security and privacy review completed
- [ ] Performance benchmarks met
- [ ] Production deployment successful
- [ ] User acceptance testing completed
- [ ] Knowledge graph system fully functional with visualization

### Story-Level DoD
- [ ] Feature implemented according to specifications
- [ ] Unit tests written and passing
- [ ] Integration tests written and passing
- [ ] Code reviewed and approved
- [ ] Documentation updated
- [ ] Database migrations tested
- [ ] API endpoints tested
- [ ] Frontend components tested
- [ ] Graph database operations tested
- [ ] Performance benchmarks met
- [ ] Security measures implemented
