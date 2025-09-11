# Epic: Workflow Engine

**Epic ID**: EPIC-002
**Priority**: P0 (Critical)
**Estimated Effort**: 2 months
**Teams Involved**: Backend, Frontend, DevOps
**Dependencies**: EPIC-001 (Agent Orchestration)

## 🎯 Epic Overview

### Business Value
Enable non-technical users to create complex document processing workflows through a visual interface. This will democratize advanced RAG capabilities, allowing business analysts and domain experts to build sophisticated document analysis pipelines without coding, reducing dependency on engineering teams and accelerating time-to-value.

### Current State
- Hard-coded linear document processing
- No conditional logic support
- No workflow persistence or reusability
- No visual workflow creation
- No workflow versioning or sharing

### Desired State
- Visual drag-and-drop workflow builder
- Conditional logic (if/then/else)
- Loops and iterations
- Parallel processing branches
- Workflow templates and marketplace
- Version control for workflows
- Workflow scheduling and triggers

## 📊 Database Schema Changes

### New Tables

```sql
-- Workflow definitions
CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    user_id UUID REFERENCES users(id),
    team_id UUID REFERENCES teams(id),
    version INTEGER DEFAULT 1,
    parent_workflow_id UUID REFERENCES workflows(id), -- For versioning
    definition JSONB NOT NULL, -- Workflow JSON definition
    status VARCHAR(50) DEFAULT 'draft', -- 'draft', 'published', 'deprecated'
    is_template BOOLEAN DEFAULT false,
    is_public BOOLEAN DEFAULT false,
    tags TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP,
    UNIQUE(name, user_id, version)
);

-- Workflow nodes (for easier querying)
CREATE TABLE workflow_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    node_id VARCHAR(100) NOT NULL, -- Node ID within workflow
    node_type VARCHAR(50) NOT NULL, -- 'start', 'agent', 'condition', 'loop', 'parallel', 'end'
    node_name VARCHAR(255),
    configuration JSONB,
    position JSONB, -- {x: 100, y: 200} for UI positioning
    connections JSONB, -- Array of connected node IDs
    UNIQUE(workflow_id, node_id)
);

-- Workflow executions
CREATE TABLE workflow_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows(id),
    user_id UUID REFERENCES users(id),
    trigger_type VARCHAR(50), -- 'manual', 'scheduled', 'event', 'api'
    input_data JSONB,
    output_data JSONB,
    status VARCHAR(50) NOT NULL, -- 'pending', 'running', 'completed', 'failed', 'cancelled'
    current_node_id VARCHAR(100),
    execution_path JSONB, -- Array of executed nodes
    variables JSONB, -- Workflow variables/state
    error_message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER
);

-- Node execution history
CREATE TABLE node_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID REFERENCES workflow_executions(id) ON DELETE CASCADE,
    node_id VARCHAR(100) NOT NULL,
    node_type VARCHAR(50) NOT NULL,
    input_data JSONB,
    output_data JSONB,
    status VARCHAR(50) NOT NULL,
    error_message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,
    retry_count INTEGER DEFAULT 0
);

-- Workflow schedules
CREATE TABLE workflow_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows(id),
    user_id UUID REFERENCES users(id),
    schedule_name VARCHAR(255),
    cron_expression VARCHAR(100), -- '0 0 * * *' for daily
    timezone VARCHAR(50) DEFAULT 'UTC',
    input_data JSONB, -- Default input for scheduled runs
    is_active BOOLEAN DEFAULT true,
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Workflow triggers (event-based)
CREATE TABLE workflow_triggers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows(id),
    trigger_type VARCHAR(50) NOT NULL, -- 'file_upload', 'collection_update', 'webhook'
    trigger_config JSONB, -- Type-specific configuration
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Workflow templates marketplace
CREATE TABLE workflow_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows(id),
    category VARCHAR(100),
    use_case TEXT,
    preview_image_url TEXT,
    usage_count INTEGER DEFAULT 0,
    rating DECIMAL(3,2),
    is_featured BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_workflows_user_id ON workflows(user_id);
CREATE INDEX idx_workflows_status ON workflows(status);
CREATE INDEX idx_workflows_tags ON workflows USING GIN(tags);
CREATE INDEX idx_workflow_executions_workflow_id ON workflow_executions(workflow_id);
CREATE INDEX idx_workflow_executions_status ON workflow_executions(status);
CREATE INDEX idx_node_executions_execution_id ON node_executions(execution_id);
CREATE INDEX idx_workflow_schedules_next_run ON workflow_schedules(next_run_at) WHERE is_active = true;
```

### SQLAlchemy Models

```python
# backend/rag_solution/models/workflow_models.py
from sqlalchemy import Column, String, Boolean, JSON, ForeignKey, Integer, Float, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"))
    version = Column(Integer, default=1)
    parent_workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"))
    definition = Column(JSON, nullable=False)
    status = Column(String(50), default='draft')
    is_template = Column(Boolean, default=False)
    is_public = Column(Boolean, default=False)
    tags = Column(ARRAY(String))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="workflows")
    team = relationship("Team", back_populates="workflows")
    nodes = relationship("WorkflowNode", back_populates="workflow", cascade="all, delete-orphan")
    executions = relationship("WorkflowExecution", back_populates="workflow")
    schedules = relationship("WorkflowSchedule", back_populates="workflow")
    triggers = relationship("WorkflowTrigger", back_populates="workflow")
```

## 🛣️ API Routes

### New Router: `/api/workflows`

```python
# backend/rag_solution/router/workflow_router.py

@router.post("/workflows", response_model=WorkflowResponse)
async def create_workflow(
    workflow: WorkflowCreate,
    current_user: User = Depends(get_current_user),
    workflow_service: WorkflowService = Depends()
):
    """
    Create a new workflow.

    Request Body:
    {
        "name": "Document Analysis Pipeline",
        "description": "Analyzes and summarizes documents",
        "definition": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "next": "doc_processor"
                },
                {
                    "id": "doc_processor",
                    "type": "agent",
                    "agent": "research",
                    "config": {...},
                    "next": "condition1"
                },
                {
                    "id": "condition1",
                    "type": "condition",
                    "condition": "output.confidence > 0.8",
                    "true_branch": "synthesize",
                    "false_branch": "validate"
                }
            ]
        },
        "tags": ["document", "analysis"]
    }
    """

@router.get("/workflows", response_model=List[WorkflowSummary])
async def list_workflows(
    status: Optional[str] = None,
    tags: Optional[List[str]] = Query(None),
    is_template: bool = False,
    current_user: User = Depends(get_current_user)
):
    """List user's workflows with filtering."""

@router.get("/workflows/{workflow_id}", response_model=WorkflowDetail)
async def get_workflow(workflow_id: UUID):
    """Get detailed workflow definition."""

@router.put("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    update: WorkflowUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update workflow definition."""

@router.post("/workflows/{workflow_id}/execute", response_model=ExecutionResponse)
async def execute_workflow(
    workflow_id: UUID,
    input_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Execute a workflow with input data."""

@router.get("/workflows/{workflow_id}/executions", response_model=List[ExecutionSummary])
async def list_workflow_executions(
    workflow_id: UUID,
    status: Optional[str] = None,
    limit: int = 10
):
    """List execution history for a workflow."""

@router.get("/executions/{execution_id}", response_model=ExecutionDetail)
async def get_execution_detail(execution_id: UUID):
    """Get detailed execution information including node execution history."""

@router.post("/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: UUID):
    """Cancel a running workflow execution."""

@router.websocket("/executions/{execution_id}/stream")
async def stream_execution(
    websocket: WebSocket,
    execution_id: UUID
):
    """WebSocket for real-time execution updates."""

@router.post("/workflows/{workflow_id}/schedule", response_model=ScheduleResponse)
async def schedule_workflow(
    workflow_id: UUID,
    schedule: ScheduleCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Schedule recurring workflow execution.

    Request Body:
    {
        "schedule_name": "Daily Report",
        "cron_expression": "0 9 * * *",
        "timezone": "America/New_York",
        "input_data": {...}
    }
    """

@router.post("/workflows/{workflow_id}/publish")
async def publish_workflow(workflow_id: UUID):
    """Publish workflow as template."""

@router.post("/workflows/{workflow_id}/fork")
async def fork_workflow(workflow_id: UUID):
    """Create a copy of workflow."""

@router.get("/templates", response_model=List[WorkflowTemplate])
async def list_workflow_templates(
    category: Optional[str] = None,
    search: Optional[str] = None
):
    """Browse workflow template marketplace."""

@router.post("/workflows/validate", response_model=ValidationResult)
async def validate_workflow(definition: Dict[str, Any]):
    """Validate workflow definition without saving."""
```

## 🎨 Frontend Changes

### New Components

```typescript
// webui/src/components/workflow/WorkflowBuilder.tsx
import ReactFlow from 'reactflow';

interface WorkflowBuilderProps {
  workflow?: Workflow;
  onSave: (workflow: Workflow) => void;
}

const WorkflowBuilder: React.FC<WorkflowBuilderProps> = () => {
  // Drag-and-drop node palette
  // Visual flow editor with ReactFlow
  // Property panel for node configuration
  // Workflow validation
  // Save/publish controls

  return (
    <div className="workflow-builder">
      <NodePalette />
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
      >
        <Controls />
        <MiniMap />
        <Background />
      </ReactFlow>
      <PropertyPanel selectedNode={selectedNode} />
    </div>
  );
};

// webui/src/components/workflow/NodePalette.tsx
const NodePalette: React.FC = () => {
  const nodeTypes = [
    { type: 'agent', label: 'Agent Task', icon: <AgentIcon /> },
    { type: 'condition', label: 'Condition', icon: <BranchIcon /> },
    { type: 'loop', label: 'Loop', icon: <LoopIcon /> },
    { type: 'parallel', label: 'Parallel', icon: <ParallelIcon /> },
    { type: 'transform', label: 'Transform', icon: <TransformIcon /> },
  ];

  return (
    <div className="node-palette">
      {nodeTypes.map(node => (
        <DraggableNode key={node.type} {...node} />
      ))}
    </div>
  );
};

// webui/src/components/workflow/ExecutionMonitor.tsx
const ExecutionMonitor: React.FC<{executionId: string}> = () => {
  // Real-time execution visualization
  // Node status indicators
  // Execution timeline
  // Variable inspector
  // Error display
};

// webui/src/components/workflow/WorkflowTemplates.tsx
const WorkflowTemplates: React.FC = () => {
  // Template marketplace browser
  // Category filtering
  // Search and preview
  // One-click import
};
```

### Custom Workflow Nodes

```typescript
// webui/src/components/workflow/nodes/ConditionalNode.tsx
const ConditionalNode: React.FC<NodeProps> = ({ data, selected }) => {
  return (
    <div className={`conditional-node ${selected ? 'selected' : ''}`}>
      <Handle type="target" position={Position.Top} />
      <div className="node-content">
        <Icon name="branch" />
        <span>If: {data.condition}</span>
      </div>
      <Handle type="source" position={Position.Bottom} id="true" />
      <Handle type="source" position={Position.Bottom} id="false" />
    </div>
  );
};

// webui/src/components/workflow/nodes/LoopNode.tsx
const LoopNode: React.FC<NodeProps> = ({ data }) => {
  return (
    <div className="loop-node">
      <Handle type="target" position={Position.Top} />
      <div className="node-content">
        <Icon name="loop" />
        <span>For each: {data.iterator}</span>
        <span>Max: {data.maxIterations}</span>
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};
```

## 🧪 Testing Strategy

### Atomic Tests (Model Layer)
```python
# tests/atomic/test_workflow_models.py
class TestWorkflowModels:
    def test_workflow_versioning(self):
        """Test workflow version tracking."""

    def test_workflow_definition_validation(self):
        """Validate workflow JSON structure."""

    def test_node_connections_integrity(self):
        """Ensure node connections are valid."""

    def test_execution_status_transitions(self):
        """Test valid status transitions."""

    def test_schedule_cron_validation(self):
        """Validate cron expression format."""
```

### Unit Tests (Service Layer)
```python
# tests/unit/test_workflow_engine.py
class TestWorkflowEngine:
    def test_simple_linear_workflow(self):
        """Test basic A->B->C workflow."""

    def test_conditional_branching(self):
        """Test if/then/else logic."""

    def test_loop_execution(self):
        """Test for-each loop with max iterations."""

    def test_parallel_branch_execution(self):
        """Test parallel branch processing."""

    def test_nested_workflows(self):
        """Test workflow calling another workflow."""

    def test_variable_passing(self):
        """Test variable passing between nodes."""

    def test_error_handling_strategies(self):
        """Test retry, skip, fail strategies."""

    def test_workflow_timeout(self):
        """Test workflow timeout handling."""

# tests/unit/test_workflow_scheduler.py
class TestWorkflowScheduler:
    def test_cron_schedule_creation(self):
        """Test creating cron-based schedules."""

    def test_schedule_execution_trigger(self):
        """Test schedule triggers execution."""

    def test_timezone_handling(self):
        """Test timezone conversion for schedules."""

    def test_missed_schedule_handling(self):
        """Test handling of missed scheduled runs."""
```

### Integration Tests (API Layer)
```python
# tests/integration/test_workflow_api.py
class TestWorkflowAPI:
    @pytest.mark.asyncio
    async def test_create_workflow_api(self, client, auth_headers):
        """Test workflow creation via API."""

    @pytest.mark.asyncio
    async def test_execute_workflow_api(self, client, auth_headers):
        """Test workflow execution via API."""

    @pytest.mark.asyncio
    async def test_workflow_execution_streaming(self, client, auth_headers):
        """Test WebSocket streaming of execution."""

    @pytest.mark.asyncio
    async def test_workflow_template_marketplace(self, client):
        """Test template listing and import."""

    @pytest.mark.asyncio
    async def test_workflow_scheduling_api(self, client, auth_headers):
        """Test scheduling workflow execution."""
```

### E2E Tests (Full Workflow)
```python
# tests/e2e/test_workflow_scenarios.py
class TestWorkflowScenarios:
    def test_document_processing_workflow(self):
        """
        Complete document processing workflow:
        1. Create workflow with conditional logic
        2. Upload documents
        3. Execute workflow
        4. Monitor execution progress
        5. Verify output based on conditions
        """

    def test_iterative_analysis_workflow(self):
        """
        Test loop-based iterative analysis:
        1. Create workflow with loop node
        2. Process multiple documents
        3. Aggregate results
        4. Verify iteration limits
        """

    def test_scheduled_report_generation(self):
        """
        Test scheduled workflow execution:
        1. Create report generation workflow
        2. Schedule daily execution
        3. Verify execution at scheduled time
        4. Check output delivery
        """

    def test_error_recovery_workflow(self):
        """
        Test error handling and recovery:
        1. Create workflow with potential failure points
        2. Execute with data causing errors
        3. Verify retry logic
        4. Check fallback paths
        """
```

## 📋 User Stories

### Story 1: Visual Workflow Creation
**As a** business analyst
**I want to** create document processing workflows visually
**So that** I can automate complex analysis without coding

**Acceptance Criteria:**
- [ ] Can drag and drop nodes to create workflow
- [ ] Can connect nodes to define flow
- [ ] Can configure node properties via UI
- [ ] Can validate workflow before saving
- [ ] Can test workflow with sample data

### Story 2: Conditional Logic Implementation
**As a** workflow designer
**I want to** add conditional logic to workflows
**So that** different actions occur based on data values

**Acceptance Criteria:**
- [ ] Can add if/then/else nodes
- [ ] Can define conditions using simple expressions
- [ ] Can nest conditions
- [ ] Can test condition evaluation
- [ ] Visual indication of which branch will execute

### Story 3: Workflow Monitoring
**As a** operations user
**I want to** monitor running workflows in real-time
**So that** I can track progress and identify issues

**Acceptance Criteria:**
- [ ] See real-time execution progress
- [ ] View current node being executed
- [ ] See variables and data flow
- [ ] Identify bottlenecks or failures
- [ ] Can cancel running workflows

### Story 4: Workflow Templates
**As a** new user
**I want to** use pre-built workflow templates
**So that** I can quickly start with common use cases

**Acceptance Criteria:**
- [ ] Browse template marketplace
- [ ] Preview template functionality
- [ ] Import and customize templates
- [ ] Rate and review templates
- [ ] Share my workflows as templates

## 🎯 Milestones

### Milestone 1: Core Engine (Week 1-2)
**Success Criteria:**
- [ ] Workflow definition schema finalized
- [ ] Basic workflow execution engine working
- [ ] Linear workflow execution functional
- [ ] Database schema implemented
- [ ] 90% unit test coverage

**Deliverables:**
- Workflow engine core
- Execution tracking
- Basic API endpoints
- Unit tests

### Milestone 2: Advanced Logic (Week 3-4)
**Success Criteria:**
- [ ] Conditional branching working
- [ ] Loop nodes functional
- [ ] Parallel execution implemented
- [ ] Variable passing between nodes
- [ ] Error handling strategies

**Deliverables:**
- Complete logic nodes
- Advanced execution paths
- Integration tests

### Milestone 3: Visual Builder (Week 5-6)
**Success Criteria:**
- [ ] React Flow integrated
- [ ] Drag-and-drop working
- [ ] Node configuration UI
- [ ] Workflow validation
- [ ] Save/load workflows

**Deliverables:**
- Visual workflow builder
- Node palette
- Property panels
- Frontend tests

### Milestone 4: Monitoring & Scheduling (Week 7-8)
**Success Criteria:**
- [ ] Real-time execution monitoring
- [ ] WebSocket streaming working
- [ ] Cron scheduling functional
- [ ] Template marketplace
- [ ] E2E tests passing

**Deliverables:**
- Execution monitor
- Scheduling system
- Template marketplace
- Complete documentation

## 📈 Success Metrics

### Technical Metrics
- Workflow execution time < 10 seconds for simple flows
- Visual builder load time < 2 seconds
- 99.9% execution reliability
- Support for workflows with 100+ nodes
- WebSocket latency < 50ms

### Business Metrics
- 70% of users create first workflow within 1 hour
- 50% reduction in time to automate processes
- 80% of workflows execute without errors
- 60% template reuse rate

## 🚀 Implementation Phases

### Phase 1: Foundation (Week 1)
- Database schema setup
- Core workflow models
- Basic execution engine
- Simple API endpoints

### Phase 2: Execution Logic (Week 2-3)
- Conditional nodes
- Loop implementation
- Parallel processing
- Variable management

### Phase 3: Visual Builder (Week 4-5)
- React Flow setup
- Node components
- Drag-and-drop
- Property configuration

### Phase 4: Advanced Features (Week 6-7)
- Real-time monitoring
- Scheduling system
- Template marketplace
- WebSocket streaming

### Phase 5: Polish (Week 8)
- Performance optimization
- Error handling
- Documentation
- Testing completion

## 🔗 Dependencies

### Technical Dependencies
- React Flow for visual builder
- Celery for scheduled execution
- Redis for workflow state
- WebSocket support

### Team Dependencies
- Depends on EPIC-001 completion
- Frontend team for visual builder
- DevOps for scheduling infrastructure
- QA for complex workflow testing

## 📝 Notes

### Risks
- Complexity of visual builder UX
- Performance with large workflows
- Scheduling reliability
- Circular dependency detection

### Mitigations
- Use proven React Flow library
- Implement workflow size limits initially
- Use robust scheduler (Celery)
- Add validation for circular dependencies

### Future Enhancements
- AI-powered workflow suggestions
- Workflow performance analytics
- A/B testing for workflows
- Workflow collaboration features
