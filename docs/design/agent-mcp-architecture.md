# Agent and MCP Support Architecture

**Date**: November 2025
**Status**: Design Proposal
**Version**: 1.0

## Executive Summary

This document proposes an architecture for introducing extensible agent support and Model Context Protocol (MCP) integration into RAG Modulo, enabling dynamic capabilities like search augmentation, PowerPoint generation, and custom processing workflows within collection conversations.

## Current Architecture Analysis

### Existing Components

Based on RAG Modulo's current structure:

**Services** (`backend/rag_solution/services/`):

- `SearchService` - Core RAG search with CoT reasoning
- `ConversationService` - Manages conversation state
- `ChainOfThoughtService` - Complex query decomposition
- `QuestionDecomposer` - Multi-part question handling
- `AnswerSynthesizer` - Response generation

**Models** (`backend/rag_solution/models/`):

- `Collection` - Document collections
- `Conversation` - Chat history
- `Question` - User queries with context

**Schemas** (`backend/rag_solution/schemas/`):

- `SearchInput` - Search request validation
- `SearchOutput` - Search response structure
- `ConversationCreate` - Conversation initialization

### Extension Points

1. **Search Pipeline** - Post-retrieval augmentation
2. **Conversation Flow** - Agent invocation during chat
3. **Document Processing** - Custom processors
4. **Response Generation** - Output format transformation

## Proposed Architecture

### 1. Agent Framework

#### Agent Registry

```python
# backend/rag_solution/agents/registry.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List
from pydantic import BaseModel

class AgentCapability(str, Enum):
    SEARCH_AUGMENTATION = "search_augmentation"
    DOCUMENT_GENERATION = "document_generation"
    DATA_ANALYSIS = "data_analysis"
    VISUALIZATION = "visualization"
    TRANSLATION = "translation"

class AgentManifest(BaseModel):
    """Agent metadata and configuration"""
    agent_id: str
    name: str
    version: str
    description: str
    capabilities: List[AgentCapability]
    mcp_server_url: Optional[str] = None  # MCP server endpoint
    config_schema: Dict[str, Any]  # JSON Schema for configuration
    input_schema: Dict[str, Any]   # Expected input format
    output_schema: Dict[str, Any]  # Expected output format

class BaseAgent(ABC):
    """Base class for all agents"""

    def __init__(self, manifest: AgentManifest, config: Dict[str, Any]):
        self.manifest = manifest
        self.config = config

    @abstractmethod
    async def execute(
        self,
        context: AgentContext,
        input_data: Dict[str, Any]
    ) -> AgentResult:
        """Execute agent logic"""
        pass

    @abstractmethod
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate agent configuration"""
        pass

class AgentRegistry:
    """Central registry for agent discovery and loading"""

    def __init__(self):
        self._agents: Dict[str, AgentManifest] = {}
        self._instances: Dict[str, BaseAgent] = {}

    def register_agent(self, manifest: AgentManifest, agent_class: Type[BaseAgent]):
        """Register a new agent"""
        self._agents[manifest.agent_id] = manifest

    def get_agent(self, agent_id: str, config: Dict[str, Any]) -> BaseAgent:
        """Get or create agent instance"""
        pass

    def list_agents_by_capability(
        self,
        capability: AgentCapability
    ) -> List[AgentManifest]:
        """Find agents by capability"""
        pass

# Global registry instance
agent_registry = AgentRegistry()
```

#### Agent Context

```python
# backend/rag_solution/agents/context.py
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import UUID

@dataclass
class AgentContext:
    """Execution context passed to agents"""

    # Collection context
    collection_id: UUID
    user_id: UUID

    # Conversation context
    conversation_id: Optional[UUID] = None
    conversation_history: List[Dict[str, str]] = None

    # Search context (if invoked during search)
    query: Optional[str] = None
    retrieved_documents: Optional[List[Dict[str, Any]]] = None
    search_metadata: Optional[Dict[str, Any]] = None

    # Pipeline context
    pipeline_stage: str  # 'pre_search', 'post_search', 'response_generation'

    # Agent chaining
    previous_agent_results: List['AgentResult'] = None

@dataclass
class AgentResult:
    """Result from agent execution"""

    agent_id: str
    success: bool
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    errors: Optional[List[str]] = None

    # For chaining agents
    next_agent_id: Optional[str] = None
```

### 2. MCP Integration Layer

#### MCP Client

```python
# backend/rag_solution/mcp/client.py
import httpx
from typing import Any, Dict, List

class MCPClient:
    """
    Client for Model Context Protocol servers

    Based on Anthropic's MCP specification:
    - Resource management
    - Tool invocation
    - Prompt templates
    """

    def __init__(self, server_url: str, api_key: Optional[str] = None):
        self.server_url = server_url
        self.api_key = api_key
        self.client = httpx.AsyncClient()

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available MCP tools"""
        response = await self.client.get(f"{self.server_url}/mcp/tools")
        return response.json()["tools"]

    async def invoke_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Invoke an MCP tool"""
        response = await self.client.post(
            f"{self.server_url}/mcp/tools/{tool_name}/invoke",
            json={"arguments": arguments}
        )
        return response.json()

    async def get_resource(self, resource_uri: str) -> Dict[str, Any]:
        """Fetch an MCP resource"""
        response = await self.client.get(
            f"{self.server_url}/mcp/resources",
            params={"uri": resource_uri}
        )
        return response.json()

    async def get_prompt(self, prompt_name: str) -> Dict[str, Any]:
        """Get MCP prompt template"""
        response = await self.client.get(
            f"{self.server_url}/mcp/prompts/{prompt_name}"
        )
        return response.json()

#### MCP Agent Adapter

```python
# backend/rag_solution/agents/mcp_adapter.py
class MCPAgent(BaseAgent):
    """
    Adapter that wraps MCP servers as agents

    Enables any MCP server to be used as an agent in RAG Modulo
    """

    def __init__(self, manifest: AgentManifest, config: Dict[str, Any]):
        super().__init__(manifest, config)
        self.mcp_client = MCPClient(
            server_url=manifest.mcp_server_url,
            api_key=config.get("mcp_api_key")
        )
        self.tool_mapping = config.get("tool_mapping", {})

    async def execute(
        self,
        context: AgentContext,
        input_data: Dict[str, Any]
    ) -> AgentResult:
        """Execute by invoking MCP tool"""

        # Map agent input to MCP tool arguments
        tool_name = self.tool_mapping.get("default_tool")
        mcp_args = self._map_input_to_mcp(input_data, context)

        try:
            result = await self.mcp_client.invoke_tool(tool_name, mcp_args)

            return AgentResult(
                agent_id=self.manifest.agent_id,
                success=True,
                data=result,
                metadata={"mcp_tool": tool_name}
            )
        except Exception as e:
            return AgentResult(
                agent_id=self.manifest.agent_id,
                success=False,
                data={},
                metadata={},
                errors=[str(e)]
            )

    def _map_input_to_mcp(
        self,
        input_data: Dict[str, Any],
        context: AgentContext
    ) -> Dict[str, Any]:
        """Map agent input to MCP tool arguments"""
        # Implement mapping logic based on tool_mapping config
        pass
```

### 3. Collection-Agent Association

#### Database Models

```python
# backend/rag_solution/models/agent.py
from sqlalchemy import Column, String, JSON, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

# Many-to-many association table
collection_agents = Table(
    'collection_agents',
    Base.metadata,
    Column('collection_id', UUID(as_uuid=True), ForeignKey('collections.id')),
    Column('agent_config_id', UUID(as_uuid=True), ForeignKey('agent_configs.id'))
)

class AgentConfig(Base):
    """User-configured agent instance"""

    __tablename__ = "agent_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    agent_id = Column(String, nullable=False)  # From AgentManifest
    name = Column(String, nullable=False)
    description = Column(String)
    config = Column(JSON, nullable=False)  # Agent-specific configuration
    enabled = Column(Boolean, default=True)

    # Execution settings
    trigger_stage = Column(String)  # 'pre_search', 'post_search', 'response'
    priority = Column(Integer, default=0)  # Execution order

    # Relationships
    collections = relationship(
        "Collection",
        secondary=collection_agents,
        back_populates="agents"
    )
    user = relationship("User", back_populates="agent_configs")

# Update Collection model
class Collection(Base):
    # ... existing fields ...

    agents = relationship(
        "AgentConfig",
        secondary=collection_agents,
        back_populates="collections"
    )
```

#### Schemas

```python
# backend/rag_solution/schemas/agent.py
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from uuid import UUID

class AgentConfigCreate(BaseModel):
    """Create agent configuration"""
    agent_id: str
    name: str
    description: Optional[str] = None
    config: Dict[str, Any]
    trigger_stage: str = Field(..., pattern="^(pre_search|post_search|response)$")
    priority: int = Field(default=0, ge=0)

class AgentConfigUpdate(BaseModel):
    """Update agent configuration"""
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    trigger_stage: Optional[str] = None
    priority: Optional[int] = None

class AgentConfigResponse(BaseModel):
    """Agent configuration response"""
    id: UUID
    user_id: UUID
    agent_id: str
    name: str
    description: Optional[str]
    config: Dict[str, Any]
    enabled: bool
    trigger_stage: str
    priority: int

    class Config:
        from_attributes = True

class CollectionAgentAssociation(BaseModel):
    """Associate agent with collection"""
    collection_id: UUID
    agent_config_id: UUID
```

### 4. Agent Execution Pipeline

#### Agent Service

```python
# backend/rag_solution/services/agent_service.py
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

class AgentService:
    """Service for managing and executing agents"""

    def __init__(
        self,
        db: AsyncSession,
        registry: AgentRegistry
    ):
        self.db = db
        self.registry = registry

    async def create_agent_config(
        self,
        user_id: UUID,
        agent_data: AgentConfigCreate
    ) -> AgentConfig:
        """Create user agent configuration"""

        # Validate agent exists
        manifest = self.registry.get_manifest(agent_data.agent_id)
        if not manifest:
            raise ValueError(f"Agent {agent_data.agent_id} not found")

        # Validate config against schema
        # ... validation logic ...

        agent_config = AgentConfig(
            user_id=user_id,
            **agent_data.dict()
        )
        self.db.add(agent_config)
        await self.db.commit()
        return agent_config

    async def add_agent_to_collection(
        self,
        collection_id: UUID,
        agent_config_id: UUID,
        user_id: UUID
    ):
        """Associate agent with collection"""

        # Verify ownership
        collection = await self._get_collection(collection_id, user_id)
        agent_config = await self._get_agent_config(agent_config_id, user_id)

        collection.agents.append(agent_config)
        await self.db.commit()

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
                agent = self.registry.get_agent(
                    agent_id=config.agent_id,
                    config=config.config
                )

                # Execute agent
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
```

#### Integration with SearchService

```python
# backend/rag_solution/services/search_service.py (updated)
class SearchService:

    def __init__(
        self,
        # ... existing dependencies ...
        agent_service: AgentService
    ):
        # ... existing initialization ...
        self.agent_service = agent_service

    async def search(
        self,
        search_input: SearchInput
    ) -> SearchOutput:
        """Enhanced search with agent support"""

        # Create agent context
        agent_context = AgentContext(
            collection_id=search_input.collection_id,
            user_id=search_input.user_id,
            conversation_id=search_input.conversation_id,
            query=search_input.question,
            pipeline_stage="pre_search"
        )

        # PRE-SEARCH AGENTS
        # Can modify query, add filters, etc.
        pre_search_results = await self.agent_service.execute_agents(
            context=agent_context,
            trigger_stage="pre_search"
        )

        # Apply pre-search agent modifications
        modified_query = self._apply_pre_search_results(
            search_input.question,
            pre_search_results
        )

        # CORE SEARCH (existing logic)
        search_results = await self._perform_search(modified_query, search_input)

        # Update context with search results
        agent_context.retrieved_documents = search_results.documents
        agent_context.search_metadata = search_results.metadata
        agent_context.pipeline_stage = "post_search"

        # POST-SEARCH AGENTS
        # Can re-rank, filter, augment results
        post_search_results = await self.agent_service.execute_agents(
            context=agent_context,
            trigger_stage="post_search"
        )

        # Apply post-search agent modifications
        augmented_results = self._apply_post_search_results(
            search_results,
            post_search_results
        )

        # RESPONSE GENERATION
        response = await self._generate_response(augmented_results)

        # Update context for response agents
        agent_context.pipeline_stage = "response"

        # RESPONSE AGENTS
        # Can format output, generate artifacts (PPT, PDF, etc.)
        response_results = await self.agent_service.execute_agents(
            context=agent_context,
            trigger_stage="response"
        )

        # Add agent artifacts to response
        response.agent_artifacts = self._extract_artifacts(response_results)

        return response
```

### 5. Example Agents

#### Search Augmentation Agent

```python
# backend/rag_solution/agents/builtin/search_augmenter.py
class SearchAugmenterAgent(BaseAgent):
    """Enhances search results with external data"""

    manifest = AgentManifest(
        agent_id="search_augmenter",
        name="Search Result Augmenter",
        version="1.0.0",
        description="Enhances search results with additional context",
        capabilities=[AgentCapability.SEARCH_AUGMENTATION],
        config_schema={
            "type": "object",
            "properties": {
                "external_sources": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "max_external_results": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10
                }
            }
        },
        input_schema={},
        output_schema={}
    )

    async def execute(
        self,
        context: AgentContext,
        input_data: Dict[str, Any]
    ) -> AgentResult:
        """Augment search results with external sources"""

        external_results = []
        for source in self.config["external_sources"]:
            results = await self._fetch_from_source(
                source,
                context.query,
                limit=self.config["max_external_results"]
            )
            external_results.extend(results)

        return AgentResult(
            agent_id=self.manifest.agent_id,
            success=True,
            data={"external_documents": external_results},
            metadata={"sources": self.config["external_sources"]}
        )

# Register agent
agent_registry.register_agent(
    SearchAugmenterAgent.manifest,
    SearchAugmenterAgent
)
```

#### PowerPoint Generator Agent

```python
# backend/rag_solution/agents/builtin/ppt_generator.py
from pptx import Presentation
import base64

class PowerPointGeneratorAgent(BaseAgent):
    """Generates PowerPoint presentations from search results"""

    manifest = AgentManifest(
        agent_id="ppt_generator",
        name="PowerPoint Generator",
        version="1.0.0",
        description="Creates PowerPoint presentations from search results",
        capabilities=[AgentCapability.DOCUMENT_GENERATION],
        config_schema={
            "type": "object",
            "properties": {
                "template": {"type": "string"},
                "max_slides": {"type": "integer"},
                "include_sources": {"type": "boolean"}
            }
        },
        input_schema={},
        output_schema={}
    )

    async def execute(
        self,
        context: AgentContext,
        input_data: Dict[str, Any]
    ) -> AgentResult:
        """Generate PowerPoint from search results"""

        prs = Presentation()

        # Title slide
        title_slide = prs.slides.add_slide(prs.slide_layouts[0])
        title_slide.shapes.title.text = context.query

        # Content slides
        for doc in context.retrieved_documents[:self.config["max_slides"]]:
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = doc["title"]
            slide.shapes.placeholders[1].text = doc["content"]

        # Save to bytes
        from io import BytesIO
        ppt_buffer = BytesIO()
        prs.save(ppt_buffer)
        ppt_buffer.seek(0)

        # Encode as base64
        ppt_base64 = base64.b64encode(ppt_buffer.read()).decode('utf-8')

        return AgentResult(
            agent_id=self.manifest.agent_id,
            success=True,
            data={
                "presentation": ppt_base64,
                "format": "pptx",
                "filename": f"{context.query[:50]}.pptx"
            },
            metadata={"slides": len(prs.slides)}
        )
```

### 6. API Endpoints

```python
# backend/rag_solution/router/agent_router.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from uuid import UUID

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

@router.get("/", response_model=List[AgentManifest])
async def list_available_agents():
    """List all available agents"""
    return agent_registry.list_all()

@router.get("/capabilities/{capability}", response_model=List[AgentManifest])
async def list_agents_by_capability(capability: AgentCapability):
    """List agents by capability"""
    return agent_registry.list_agents_by_capability(capability)

@router.post("/configs", response_model=AgentConfigResponse)
async def create_agent_config(
    agent_data: AgentConfigCreate,
    current_user: User = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service)
):
    """Create agent configuration"""
    return await agent_service.create_agent_config(current_user.id, agent_data)

@router.get("/configs", response_model=List[AgentConfigResponse])
async def list_user_agents(
    current_user: User = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service)
):
    """List user's agent configurations"""
    return await agent_service.list_user_agents(current_user.id)

@router.post("/collections/{collection_id}/agents")
async def add_agent_to_collection(
    collection_id: UUID,
    association: CollectionAgentAssociation,
    current_user: User = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service)
):
    """Add agent to collection"""
    await agent_service.add_agent_to_collection(
        collection_id=collection_id,
        agent_config_id=association.agent_config_id,
        user_id=current_user.id
    )
    return {"status": "success"}

@router.get("/collections/{collection_id}/agents", response_model=List[AgentConfigResponse])
async def list_collection_agents(
    collection_id: UUID,
    current_user: User = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service)
):
    """List agents associated with collection"""
    return await agent_service.list_collection_agents(collection_id, current_user.id)
```

### 7. Frontend Integration

#### Agent Management UI

```typescript
// frontend/src/components/agents/AgentManager.tsx
import React, { useState, useEffect } from 'react';
import { Button, Modal, DataTable } from '@carbon/react';
import { Add } from '@carbon/icons-react';

interface AgentManifest {
  agent_id: string;
  name: string;
  description: string;
  capabilities: string[];
}

interface AgentConfig {
  id: string;
  agent_id: string;
  name: string;
  enabled: boolean;
  trigger_stage: string;
}

export const AgentManager: React.FC<{ collectionId: string }> = ({ collectionId }) => {
  const [availableAgents, setAvailableAgents] = useState<AgentManifest[]>([]);
  const [collectionAgents, setCollectionAgents] = useState<AgentConfig[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);

  useEffect(() => {
    loadAvailableAgents();
    loadCollectionAgents();
  }, [collectionId]);

  const loadAvailableAgents = async () => {
    const response = await fetch('/api/v1/agents/');
    const agents = await response.json();
    setAvailableAgents(agents);
  };

  const loadCollectionAgents = async () => {
    const response = await fetch(`/api/v1/agents/collections/${collectionId}/agents`);
    const agents = await response.json();
    setCollectionAgents(agents);
  };

  const addAgent = async (agentId: string, config: any) => {
    // Create agent config
    const response = await fetch('/api/v1/agents/configs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        agent_id: agentId,
        name: config.name,
        config: config.settings,
        trigger_stage: config.trigger_stage
      })
    });

    const agentConfig = await response.json();

    // Associate with collection
    await fetch(`/api/v1/agents/collections/${collectionId}/agents`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        collection_id: collectionId,
        agent_config_id: agentConfig.id
      })
    });

    loadCollectionAgents();
    setShowAddModal(false);
  };

  return (
    <div className="agent-manager">
      <div className="agent-manager__header">
        <h3>Collection Agents</h3>
        <Button
          renderIcon={Add}
          onClick={() => setShowAddModal(true)}
        >
          Add Agent
        </Button>
      </div>

      <DataTable
        rows={collectionAgents}
        headers={[
          { key: 'name', header: 'Name' },
          { key: 'agent_id', header: 'Type' },
          { key: 'trigger_stage', header: 'Trigger' },
          { key: 'enabled', header: 'Enabled' }
        ]}
      />

      {showAddModal && (
        <AgentAddModal
          availableAgents={availableAgents}
          onAdd={addAgent}
          onClose={() => setShowAddModal(false)}
        />
      )}
    </div>
  );
};
```

## Implementation Plan

### Phase 1: Core Agent Framework (2 weeks)

- [ ] Implement `BaseAgent`, `AgentManifest`, `AgentRegistry`
- [ ] Create database models and migrations
- [ ] Implement `AgentService` with basic CRUD
- [ ] Create API endpoints for agent management
- [ ] Write unit tests

### Phase 2: Search Integration (1 week)

- [ ] Update `SearchService` with agent execution hooks
- [ ] Implement `AgentContext` and `AgentResult`
- [ ] Add agent execution to search pipeline
- [ ] Test pre-search and post-search agents
- [ ] Integration tests

### Phase 3: MCP Integration (2 weeks)

- [ ] Implement `MCPClient` based on Anthropic spec
- [ ] Create `MCPAgent` adapter
- [ ] Add MCP server discovery
- [ ] Test with sample MCP servers
- [ ] Documentation for MCP integration

### Phase 4: Built-in Agents (1-2 weeks)

- [ ] Implement Search Augmenter agent
- [ ] Implement PowerPoint Generator agent
- [ ] Implement Translation agent
- [ ] Implement Data Analysis agent
- [ ] Agent marketplace/registry UI

### Phase 5: Frontend & Polish (1 week)

- [ ] Agent management UI components
- [ ] Collection-agent association UI
- [ ] Agent artifact display in search results
- [ ] Agent execution status/logs viewer
- [ ] Documentation and examples

## Benefits

1. **Extensibility** - Users can add custom capabilities without modifying core code
2. **MCP Compatibility** - Leverage existing MCP ecosystem
3. **Modularity** - Agents are isolated and independently testable
4. **Flexibility** - Agents can be enabled/disabled per collection
5. **Composability** - Chain multiple agents together
6. **Third-party Integration** - Easy integration with external services

## Security Considerations

1. **Agent Validation** - Validate agent configurations against schemas
2. **Resource Limits** - Limit agent execution time and memory
3. **Sandboxing** - Run agents in isolated environments
4. **User Permissions** - Verify user ownership of collections/agents
5. **MCP Authentication** - Secure API keys for MCP servers
6. **Audit Logging** - Log all agent executions

## Performance Considerations

1. **Async Execution** - All agents run asynchronously
2. **Caching** - Cache agent results where appropriate
3. **Timeouts** - Implement execution timeouts
4. **Circuit Breaker** - Disable failing agents automatically
5. **Parallel Execution** - Run independent agents in parallel

## Conclusion

This architecture provides a clean, extensible foundation for agent and MCP support in RAG Modulo. It integrates seamlessly with the existing service-based architecture while maintaining backward compatibility. Users can enhance their RAG workflows with custom agents for search augmentation, document generation, and more - all through a simple configuration interface.
