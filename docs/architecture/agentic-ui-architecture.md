# Agentic UI Architecture

**Date**: November 2025
**Status**: Architecture Design
**Version**: 1.0
**Related Documents**:

- [MCP Integration Architecture](./mcp-integration-architecture.md)
- [SearchService Agent Hooks Architecture](./search-agent-hooks-architecture.md)
- [RAG Modulo MCP Server Architecture](./rag-modulo-mcp-server-architecture.md)

## Overview

This document describes the frontend architecture for transforming RAG Modulo into a fully
agentic RAG solution. It covers the React component hierarchy, state management, user
interactions, and integration patterns needed to support:

1. **Agent Configuration** - Per-collection agent assignment and configuration
2. **Artifact Display** - Rendering and downloading agent-generated artifacts
3. **Execution Visibility** - Real-time pipeline stage and agent status indicators
4. **Agent Management** - Dashboard for managing user's agents and viewing analytics

## Current Frontend Architecture

### Existing Components (Reference)

```
frontend/src/components/
├── agents/
│   └── LightweightAgentOrchestration.tsx   # Existing workflow-focused agent UI
├── search/
│   ├── LightweightSearchInterface.tsx      # Main search chat interface
│   ├── ChainOfThoughtAccordion.tsx         # CoT reasoning display
│   ├── SourcesAccordion.tsx                # Document sources
│   ├── CitationsAccordion.tsx              # Citation display
│   └── TokenAnalysisAccordion.tsx          # Token usage metrics
├── collections/
│   ├── LightweightCollections.tsx          # Collection list
│   └── LightweightCollectionDetail.tsx     # Collection settings
└── ui/
    ├── Card.tsx, Button.tsx, Modal.tsx     # Reusable UI components
    └── ...
```

### Design System

- **Framework**: React 18 with TypeScript
- **Styling**: Tailwind CSS with Carbon Design System colors
- **Icons**: Heroicons (@heroicons/react)
- **State**: React hooks + Context (NotificationContext)
- **Routing**: React Router DOM

## New Component Architecture

### Component Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          App Layout                                          │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  LightweightLayout (existing)                                         │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Routes                                                         │  │  │
│  │  │                                                                 │  │  │
│  │  │  /search                                                        │  │  │
│  │  │  └── LightweightSearchInterface (ENHANCED)                      │  │  │
│  │  │      ├── SearchInput                                            │  │  │
│  │  │      ├── MessageList                                            │  │  │
│  │  │      │   └── MessageCard                                        │  │  │
│  │  │      │       ├── ChainOfThoughtAccordion                        │  │  │
│  │  │      │       ├── SourcesAccordion                               │  │  │
│  │  │      │       ├── AgentArtifactsPanel (NEW)                      │  │  │
│  │  │      │       │   └── ArtifactCard (NEW)                         │  │  │
│  │  │      │       └── AgentExecutionIndicator (NEW)                  │  │  │
│  │  │      └── AgentPipelineStatus (NEW)                              │  │  │
│  │  │                                                                 │  │  │
│  │  │  /collections/:id/settings                                      │  │  │
│  │  │  └── LightweightCollectionDetail (ENHANCED)                     │  │  │
│  │  │      └── CollectionAgentsTab (NEW)                              │  │  │
│  │  │          ├── AgentList (NEW)                                    │  │  │
│  │  │          ├── AgentConfigModal (NEW)                             │  │  │
│  │  │          └── AgentMarketplace (NEW)                             │  │  │
│  │  │                                                                 │  │  │
│  │  │  /agents                                                        │  │  │
│  │  │  └── AgentDashboard (NEW)                                       │  │  │
│  │  │      ├── MyAgentsPanel (NEW)                                    │  │  │
│  │  │      ├── AgentAnalytics (NEW)                                   │  │  │
│  │  │      └── AgentAuditLog (NEW)                                    │  │  │
│  │  │                                                                 │  │  │
│  │  │  /agents/marketplace                                            │  │  │
│  │  │  └── AgentMarketplacePage (NEW)                                 │  │  │
│  │  │      ├── AgentCatalog (NEW)                                     │  │  │
│  │  │      └── AgentDetailModal (NEW)                                 │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### File Structure

```
frontend/src/
├── components/
│   ├── agents/
│   │   ├── LightweightAgentOrchestration.tsx  # Existing (keep for workflows)
│   │   ├── AgentDashboard.tsx                  # NEW: Main agent management page
│   │   ├── MyAgentsPanel.tsx                   # NEW: User's configured agents
│   │   ├── AgentAnalytics.tsx                  # NEW: Agent usage stats
│   │   ├── AgentAuditLog.tsx                   # NEW: Execution history
│   │   ├── AgentMarketplacePage.tsx            # NEW: Browse available agents
│   │   ├── AgentCatalog.tsx                    # NEW: Grid of available agents
│   │   ├── AgentDetailModal.tsx                # NEW: Agent info and add button
│   │   ├── CollectionAgentsTab.tsx             # NEW: Collection settings tab
│   │   ├── AgentList.tsx                       # NEW: Agents for a collection
│   │   ├── AgentConfigModal.tsx                # NEW: Configure agent settings
│   │   └── AgentPriorityDragDrop.tsx           # NEW: Drag to reorder priority
│   │
│   ├── search/
│   │   ├── LightweightSearchInterface.tsx      # ENHANCED: Add artifact support
│   │   ├── AgentArtifactsPanel.tsx             # NEW: Container for artifacts
│   │   ├── ArtifactCard.tsx                    # NEW: Single artifact display
│   │   ├── ArtifactPreviewModal.tsx            # NEW: Preview images/PDFs
│   │   ├── AgentExecutionIndicator.tsx         # NEW: Per-message agent badges
│   │   └── AgentPipelineStatus.tsx             # NEW: Real-time pipeline stages
│   │
│   └── ui/
│       ├── ProgressSteps.tsx                   # NEW: Pipeline stage indicator
│       └── FileDownloadButton.tsx              # NEW: Base64 download handler
│
├── services/
│   ├── apiClient.ts                            # ENHANCED: Add agent API methods
│   └── agentApiClient.ts                       # NEW: Agent-specific API calls
│
├── types/
│   └── agent.ts                                # NEW: Agent TypeScript interfaces
│
└── contexts/
    └── AgentContext.tsx                        # NEW: Agent state management
```

## New Components Specification

### 1. Search Interface Enhancements

#### AgentArtifactsPanel

Container for displaying agent-generated artifacts within search results.

```typescript
// frontend/src/components/search/AgentArtifactsPanel.tsx

interface AgentArtifact {
  agent_id: string;
  type: 'pptx' | 'pdf' | 'png' | 'mp3' | 'html' | 'txt';
  data: string;  // base64 encoded
  filename: string;
  metadata: Record<string, any>;
}

interface AgentArtifactsPanelProps {
  artifacts: AgentArtifact[];
  isLoading?: boolean;
}

const AgentArtifactsPanel: React.FC<AgentArtifactsPanelProps> = ({
  artifacts,
  isLoading
}) => {
  if (!artifacts?.length && !isLoading) return null;

  return (
    <div className="mt-4 border-t border-gray-20 pt-4">
      <div className="flex items-center space-x-2 mb-3">
        <DocumentIcon className="w-4 h-4 text-purple-60" />
        <h4 className="text-sm font-medium text-gray-100">
          Generated Artifacts ({artifacts.length})
        </h4>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[1, 2].map(i => (
            <Skeleton key={i} className="h-24 rounded-lg" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {artifacts.map((artifact, index) => (
            <ArtifactCard key={index} artifact={artifact} />
          ))}
        </div>
      )}
    </div>
  );
};
```

#### ArtifactCard

Individual artifact display with preview and download actions.

```typescript
// frontend/src/components/search/ArtifactCard.tsx

interface ArtifactCardProps {
  artifact: AgentArtifact;
}

const ArtifactCard: React.FC<ArtifactCardProps> = ({ artifact }) => {
  const [previewOpen, setPreviewOpen] = useState(false);

  const getIcon = () => {
    switch (artifact.type) {
      case 'pptx': return <PresentationChartBarIcon />;
      case 'pdf': return <DocumentTextIcon />;
      case 'png': return <PhotoIcon />;
      case 'mp3': return <MusicalNoteIcon />;
      case 'html': return <CodeBracketIcon />;
      default: return <DocumentIcon />;
    }
  };

  const getLabel = () => {
    switch (artifact.type) {
      case 'pptx': return 'PowerPoint';
      case 'pdf': return 'PDF Report';
      case 'png': return 'Chart';
      case 'mp3': return 'Audio';
      case 'html': return 'HTML';
      default: return 'File';
    }
  };

  const canPreview = ['png', 'pdf'].includes(artifact.type);

  const handleDownload = () => {
    const mimeTypes: Record<string, string> = {
      pptx: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      pdf: 'application/pdf',
      png: 'image/png',
      mp3: 'audio/mpeg',
      html: 'text/html',
      txt: 'text/plain'
    };

    const blob = base64ToBlob(artifact.data, mimeTypes[artifact.type]);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = artifact.filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <div className="bg-gray-10 rounded-lg p-3 hover:bg-gray-20 transition-colors">
        <div className="flex items-center space-x-2 mb-2">
          <div className="p-1.5 bg-purple-10 rounded text-purple-60">
            {getIcon()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-gray-100 truncate">
              {getLabel()}
            </p>
            <p className="text-xs text-gray-60 truncate">
              {artifact.filename}
            </p>
          </div>
        </div>

        <div className="flex space-x-2">
          {canPreview && (
            <button
              onClick={() => setPreviewOpen(true)}
              className="flex-1 text-xs px-2 py-1 bg-gray-20 hover:bg-gray-30 rounded text-gray-100"
            >
              Preview
            </button>
          )}
          <button
            onClick={handleDownload}
            className="flex-1 text-xs px-2 py-1 bg-blue-60 hover:bg-blue-70 rounded text-white"
          >
            Download
          </button>
        </div>

        {artifact.metadata && (
          <p className="text-xs text-gray-60 mt-2">
            {artifact.metadata.slides && `${artifact.metadata.slides} slides`}
            {artifact.metadata.width && `${artifact.metadata.width}x${artifact.metadata.height}`}
          </p>
        )}
      </div>

      {previewOpen && (
        <ArtifactPreviewModal
          artifact={artifact}
          onClose={() => setPreviewOpen(false)}
        />
      )}
    </>
  );
};
```

#### AgentPipelineStatus

Real-time pipeline stage indicator shown during search.

```typescript
// frontend/src/components/search/AgentPipelineStatus.tsx

type PipelineStage = 'pre_search' | 'search' | 'post_search' | 'generation' | 'response_agents' | 'complete';

interface AgentPipelineStatusProps {
  currentStage: PipelineStage;
  stages: {
    id: PipelineStage;
    label: string;
    agentCount: number;
    status: 'pending' | 'running' | 'completed' | 'error';
    duration?: number;
  }[];
  isVisible: boolean;
}

const AgentPipelineStatus: React.FC<AgentPipelineStatusProps> = ({
  currentStage,
  stages,
  isVisible
}) => {
  if (!isVisible) return null;

  return (
    <div className="bg-blue-10 border border-blue-20 rounded-lg p-4 mb-4">
      <div className="flex items-center space-x-2 mb-3">
        <BoltIcon className="w-4 h-4 text-blue-60 animate-pulse" />
        <span className="text-sm font-medium text-blue-60">
          Agent Pipeline Processing
        </span>
      </div>

      <div className="flex items-center justify-between">
        {stages.map((stage, index) => (
          <React.Fragment key={stage.id}>
            <div className="flex flex-col items-center">
              <div className={`
                w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium
                ${stage.status === 'completed' ? 'bg-green-50 text-white' : ''}
                ${stage.status === 'running' ? 'bg-blue-60 text-white animate-pulse' : ''}
                ${stage.status === 'pending' ? 'bg-gray-20 text-gray-60' : ''}
                ${stage.status === 'error' ? 'bg-red-50 text-white' : ''}
              `}>
                {stage.status === 'completed' ? (
                  <CheckIcon className="w-4 h-4" />
                ) : stage.status === 'running' ? (
                  <ArrowPathIcon className="w-4 h-4 animate-spin" />
                ) : (
                  stage.agentCount
                )}
              </div>
              <span className="text-xs text-gray-70 mt-1 text-center max-w-[80px]">
                {stage.label}
              </span>
              {stage.duration && (
                <span className="text-xs text-gray-60">
                  {stage.duration}ms
                </span>
              )}
            </div>

            {index < stages.length - 1 && (
              <div className={`
                flex-1 h-0.5 mx-2
                ${stages[index + 1].status !== 'pending' ? 'bg-blue-60' : 'bg-gray-20'}
              `} />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};
```

#### AgentExecutionIndicator

Badge showing which agents processed a response.

```typescript
// frontend/src/components/search/AgentExecutionIndicator.tsx

interface AgentExecution {
  agent_id: string;
  agent_name: string;
  stage: 'pre_search' | 'post_search' | 'response';
  duration_ms: number;
  success: boolean;
}

interface AgentExecutionIndicatorProps {
  executions: AgentExecution[];
}

const AgentExecutionIndicator: React.FC<AgentExecutionIndicatorProps> = ({
  executions
}) => {
  if (!executions?.length) return null;

  const [expanded, setExpanded] = useState(false);

  const successCount = executions.filter(e => e.success).length;
  const totalDuration = executions.reduce((sum, e) => sum + e.duration_ms, 0);

  return (
    <div className="mt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center space-x-2 text-xs text-gray-60 hover:text-gray-100"
      >
        <CpuChipIcon className="w-3 h-3" />
        <span>
          {successCount}/{executions.length} agents • {totalDuration}ms
        </span>
        <ChevronDownIcon className={`w-3 h-3 transition-transform ${expanded ? 'rotate-180' : ''}`} />
      </button>

      {expanded && (
        <div className="mt-2 space-y-1 pl-5">
          {executions.map((exec, index) => (
            <div
              key={index}
              className="flex items-center space-x-2 text-xs"
            >
              <span className={`w-1.5 h-1.5 rounded-full ${exec.success ? 'bg-green-50' : 'bg-red-50'}`} />
              <span className="text-gray-70">{exec.agent_name}</span>
              <span className="text-gray-50">({exec.stage})</span>
              <span className="text-gray-60">{exec.duration_ms}ms</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
```

### 2. Collection Agent Configuration

#### CollectionAgentsTab

Tab component for collection settings page to configure agents.

```typescript
// frontend/src/components/agents/CollectionAgentsTab.tsx

interface CollectionAgentsTabProps {
  collectionId: string;
}

const CollectionAgentsTab: React.FC<CollectionAgentsTabProps> = ({
  collectionId
}) => {
  const [agents, setAgents] = useState<CollectionAgent[]>([]);
  const [availableAgents, setAvailableAgents] = useState<AgentManifest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingAgent, setEditingAgent] = useState<CollectionAgent | null>(null);
  const { addNotification } = useNotification();

  useEffect(() => {
    loadAgents();
  }, [collectionId]);

  const loadAgents = async () => {
    setIsLoading(true);
    try {
      const [collectionAgents, allAgents] = await Promise.all([
        agentApiClient.getCollectionAgents(collectionId),
        agentApiClient.getAvailableAgents()
      ]);
      setAgents(collectionAgents);
      setAvailableAgents(allAgents);
    } catch (error) {
      addNotification('error', 'Error', 'Failed to load agents');
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleAgent = async (agentConfigId: string, enabled: boolean) => {
    try {
      await agentApiClient.updateAgentConfig(agentConfigId, { enabled });
      setAgents(prev => prev.map(a =>
        a.id === agentConfigId ? { ...a, enabled } : a
      ));
    } catch (error) {
      addNotification('error', 'Error', 'Failed to update agent');
    }
  };

  const handleReorderAgents = async (reorderedAgents: CollectionAgent[]) => {
    try {
      // Update priorities based on new order
      const updates = reorderedAgents.map((agent, index) => ({
        id: agent.id,
        priority: index
      }));
      await agentApiClient.batchUpdatePriorities(updates);
      setAgents(reorderedAgents);
    } catch (error) {
      addNotification('error', 'Error', 'Failed to reorder agents');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-100">Collection Agents</h3>
          <p className="text-sm text-gray-70">
            Configure AI agents that enhance search and generate artifacts
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="btn-primary flex items-center space-x-2"
        >
          <PlusIcon className="w-4 h-4" />
          <span>Add Agent</span>
        </button>
      </div>

      {/* Agent List by Stage */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map(i => <Skeleton key={i} className="h-20" />)}
        </div>
      ) : (
        <>
          {/* Pre-Search Agents */}
          <AgentStageSection
            title="Pre-Search Agents"
            description="Transform queries before vector search"
            stage="pre_search"
            agents={agents.filter(a => a.trigger_stage === 'pre_search')}
            onToggle={handleToggleAgent}
            onEdit={setEditingAgent}
            onReorder={handleReorderAgents}
          />

          {/* Post-Search Agents */}
          <AgentStageSection
            title="Post-Search Agents"
            description="Process retrieved documents before answer generation"
            stage="post_search"
            agents={agents.filter(a => a.trigger_stage === 'post_search')}
            onToggle={handleToggleAgent}
            onEdit={setEditingAgent}
            onReorder={handleReorderAgents}
          />

          {/* Response Agents */}
          <AgentStageSection
            title="Response Agents"
            description="Generate artifacts from search results (runs in parallel)"
            stage="response"
            agents={agents.filter(a => a.trigger_stage === 'response')}
            onToggle={handleToggleAgent}
            onEdit={setEditingAgent}
            onReorder={handleReorderAgents}
          />
        </>
      )}

      {/* Add Agent Modal */}
      {showAddModal && (
        <AgentMarketplaceModal
          availableAgents={availableAgents}
          collectionId={collectionId}
          onAdd={() => {
            loadAgents();
            setShowAddModal(false);
          }}
          onClose={() => setShowAddModal(false)}
        />
      )}

      {/* Edit Agent Modal */}
      {editingAgent && (
        <AgentConfigModal
          agent={editingAgent}
          onSave={() => {
            loadAgents();
            setEditingAgent(null);
          }}
          onClose={() => setEditingAgent(null)}
        />
      )}
    </div>
  );
};
```

#### AgentStageSection

Section component for agents at a specific pipeline stage.

```typescript
// frontend/src/components/agents/AgentStageSection.tsx

interface AgentStageSectionProps {
  title: string;
  description: string;
  stage: 'pre_search' | 'post_search' | 'response';
  agents: CollectionAgent[];
  onToggle: (id: string, enabled: boolean) => void;
  onEdit: (agent: CollectionAgent) => void;
  onReorder: (agents: CollectionAgent[]) => void;
}

const AgentStageSection: React.FC<AgentStageSectionProps> = ({
  title,
  description,
  stage,
  agents,
  onToggle,
  onEdit,
  onReorder
}) => {
  const stageIcons = {
    pre_search: <FunnelIcon className="w-5 h-5" />,
    post_search: <AdjustmentsHorizontalIcon className="w-5 h-5" />,
    response: <DocumentDuplicateIcon className="w-5 h-5" />
  };

  const stageColors = {
    pre_search: 'bg-yellow-10 text-yellow-60',
    post_search: 'bg-blue-10 text-blue-60',
    response: 'bg-purple-10 text-purple-60'
  };

  return (
    <div className="card p-4">
      <div className="flex items-center space-x-3 mb-4">
        <div className={`p-2 rounded-lg ${stageColors[stage]}`}>
          {stageIcons[stage]}
        </div>
        <div>
          <h4 className="font-medium text-gray-100">{title}</h4>
          <p className="text-sm text-gray-60">{description}</p>
        </div>
      </div>

      {agents.length === 0 ? (
        <div className="text-center py-6 text-gray-60">
          <CubeTransparentIcon className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No agents configured for this stage</p>
        </div>
      ) : (
        <DragDropContext onDragEnd={(result) => {
          if (!result.destination) return;
          const items = Array.from(agents);
          const [reordered] = items.splice(result.source.index, 1);
          items.splice(result.destination.index, 0, reordered);
          onReorder(items);
        }}>
          <Droppable droppableId={stage}>
            {(provided) => (
              <div
                {...provided.droppableProps}
                ref={provided.innerRef}
                className="space-y-2"
              >
                {agents.map((agent, index) => (
                  <Draggable key={agent.id} draggableId={agent.id} index={index}>
                    {(provided, snapshot) => (
                      <div
                        ref={provided.innerRef}
                        {...provided.draggableProps}
                        className={`
                          flex items-center p-3 bg-gray-10 rounded-lg
                          ${snapshot.isDragging ? 'shadow-lg ring-2 ring-blue-60' : ''}
                        `}
                      >
                        <div
                          {...provided.dragHandleProps}
                          className="mr-3 cursor-grab text-gray-40 hover:text-gray-60"
                        >
                          <Bars3Icon className="w-4 h-4" />
                        </div>

                        <div className="flex-1">
                          <p className="font-medium text-gray-100">{agent.name}</p>
                          <p className="text-xs text-gray-60">{agent.description}</p>
                        </div>

                        <div className="flex items-center space-x-3">
                          <span className="text-xs text-gray-50">
                            Priority: {agent.priority}
                          </span>

                          <Switch
                            checked={agent.enabled}
                            onChange={(enabled) => onToggle(agent.id, enabled)}
                            className={`
                              ${agent.enabled ? 'bg-green-50' : 'bg-gray-30'}
                              relative inline-flex h-5 w-9 items-center rounded-full
                            `}
                          >
                            <span
                              className={`
                                ${agent.enabled ? 'translate-x-5' : 'translate-x-1'}
                                inline-block h-3 w-3 transform rounded-full bg-white transition
                              `}
                            />
                          </Switch>

                          <button
                            onClick={() => onEdit(agent)}
                            className="p-1 text-gray-60 hover:text-gray-100"
                          >
                            <CogIcon className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    )}
                  </Draggable>
                ))}
                {provided.placeholder}
              </div>
            )}
          </Droppable>
        </DragDropContext>
      )}
    </div>
  );
};
```

#### AgentConfigModal

Modal for configuring agent-specific settings.

```typescript
// frontend/src/components/agents/AgentConfigModal.tsx

interface AgentConfigModalProps {
  agent: CollectionAgent;
  onSave: () => void;
  onClose: () => void;
}

const AgentConfigModal: React.FC<AgentConfigModalProps> = ({
  agent,
  onSave,
  onClose
}) => {
  const [config, setConfig] = useState(agent.config);
  const [isSaving, setIsSaving] = useState(false);
  const { addNotification } = useNotification();

  // Generate form fields from agent's config schema
  const renderConfigField = (key: string, schema: any) => {
    const value = config.settings?.[key] ?? schema.default;

    switch (schema.type) {
      case 'integer':
        return (
          <div key={key}>
            <label className="block text-sm font-medium text-gray-100 mb-1">
              {schema.title || key}
            </label>
            <input
              type="number"
              min={schema.minimum}
              max={schema.maximum}
              value={value}
              onChange={(e) => setConfig({
                ...config,
                settings: { ...config.settings, [key]: parseInt(e.target.value) }
              })}
              className="input-field w-full"
            />
            {schema.description && (
              <p className="text-xs text-gray-60 mt-1">{schema.description}</p>
            )}
          </div>
        );

      case 'boolean':
        return (
          <div key={key} className="flex items-center justify-between">
            <div>
              <label className="block text-sm font-medium text-gray-100">
                {schema.title || key}
              </label>
              {schema.description && (
                <p className="text-xs text-gray-60">{schema.description}</p>
              )}
            </div>
            <Switch
              checked={value}
              onChange={(checked) => setConfig({
                ...config,
                settings: { ...config.settings, [key]: checked }
              })}
            />
          </div>
        );

      case 'string':
        if (schema.enum) {
          return (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-100 mb-1">
                {schema.title || key}
              </label>
              <select
                value={value}
                onChange={(e) => setConfig({
                  ...config,
                  settings: { ...config.settings, [key]: e.target.value }
                })}
                className="input-field w-full"
              >
                {schema.enum.map((opt: string) => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            </div>
          );
        }
        return (
          <div key={key}>
            <label className="block text-sm font-medium text-gray-100 mb-1">
              {schema.title || key}
            </label>
            <input
              type="text"
              value={value}
              onChange={(e) => setConfig({
                ...config,
                settings: { ...config.settings, [key]: e.target.value }
              })}
              className="input-field w-full"
            />
          </div>
        );

      default:
        return null;
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await agentApiClient.updateAgentConfig(agent.id, { config });
      addNotification('success', 'Saved', 'Agent configuration updated');
      onSave();
    } catch (error) {
      addNotification('error', 'Error', 'Failed to save configuration');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal open onClose={onClose} size="md">
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-100 mb-4">
          Configure {agent.name}
        </h3>

        <div className="space-y-4">
          {/* Agent info */}
          <div className="bg-gray-10 p-3 rounded-lg">
            <p className="text-sm text-gray-70">{agent.description}</p>
            <div className="flex items-center space-x-4 mt-2 text-xs text-gray-60">
              <span>Stage: {agent.trigger_stage}</span>
              <span>Type: {agent.config.type}</span>
            </div>
          </div>

          {/* Dynamic config fields */}
          {agent.config_schema?.properties && (
            <div className="space-y-4">
              {Object.entries(agent.config_schema.properties).map(([key, schema]) =>
                renderConfigField(key, schema)
              )}
            </div>
          )}
        </div>

        <div className="flex justify-end space-x-3 mt-6">
          <button onClick={onClose} className="btn-secondary">
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="btn-primary"
          >
            {isSaving ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </div>
    </Modal>
  );
};
```

### 3. Agent Management Dashboard

#### AgentDashboard

Main page for managing user's agents across all collections.

```typescript
// frontend/src/components/agents/AgentDashboard.tsx

const AgentDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'my-agents' | 'analytics' | 'audit'>('my-agents');

  return (
    <div className="min-h-screen bg-gray-10 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-gray-100">Agent Management</h1>
          <p className="text-gray-70">
            Configure and monitor AI agents for your document collections
          </p>
        </div>

        {/* Tabs */}
        <div className="mb-6">
          <nav className="flex space-x-4 border-b border-gray-20">
            {[
              { id: 'my-agents', label: 'My Agents', icon: CubeIcon },
              { id: 'analytics', label: 'Analytics', icon: ChartBarIcon },
              { id: 'audit', label: 'Audit Log', icon: ClipboardDocumentListIcon },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`
                  flex items-center space-x-2 px-4 py-3 text-sm font-medium border-b-2 -mb-px
                  ${activeTab === tab.id
                    ? 'border-blue-60 text-blue-60'
                    : 'border-transparent text-gray-70 hover:text-gray-100'
                  }
                `}
              >
                <tab.icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === 'my-agents' && <MyAgentsPanel />}
        {activeTab === 'analytics' && <AgentAnalytics />}
        {activeTab === 'audit' && <AgentAuditLog />}
      </div>
    </div>
  );
};
```

### 4. Agent Marketplace

#### AgentMarketplacePage

Browse and discover available agents.

```typescript
// frontend/src/components/agents/AgentMarketplacePage.tsx

interface AgentManifest {
  agent_id: string;
  name: string;
  version: string;
  description: string;
  capabilities: string[];
  config_schema: Record<string, any>;
  input_schema: Record<string, any>;
  output_schema: Record<string, any>;
  category: 'pre_search' | 'post_search' | 'response';
  icon?: string;
  author?: string;
  downloads?: number;
}

const AgentMarketplacePage: React.FC = () => {
  const [agents, setAgents] = useState<AgentManifest[]>([]);
  const [filter, setFilter] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [selectedAgent, setSelectedAgent] = useState<AgentManifest | null>(null);

  useEffect(() => {
    loadAgents();
  }, []);

  const loadAgents = async () => {
    const data = await agentApiClient.getAvailableAgents();
    setAgents(data);
  };

  const filteredAgents = agents.filter(agent => {
    const matchesFilter = filter === 'all' || agent.category === filter;
    const matchesSearch = !search ||
      agent.name.toLowerCase().includes(search.toLowerCase()) ||
      agent.description.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const categories = [
    { id: 'all', label: 'All Agents' },
    { id: 'pre_search', label: 'Pre-Search' },
    { id: 'post_search', label: 'Post-Search' },
    { id: 'response', label: 'Response' },
  ];

  return (
    <div className="min-h-screen bg-gray-10 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-gray-100">Agent Marketplace</h1>
          <p className="text-gray-70">
            Discover and add AI agents to enhance your RAG workflows
          </p>
        </div>

        {/* Filters */}
        <div className="flex items-center space-x-4 mb-6">
          <div className="relative flex-1 max-w-md">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-60" />
            <input
              type="text"
              placeholder="Search agents..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input-field w-full pl-10"
            />
          </div>

          <div className="flex space-x-2">
            {categories.map(cat => (
              <button
                key={cat.id}
                onClick={() => setFilter(cat.id)}
                className={`
                  px-3 py-1.5 text-sm rounded-full
                  ${filter === cat.id
                    ? 'bg-blue-60 text-white'
                    : 'bg-gray-20 text-gray-70 hover:bg-gray-30'
                  }
                `}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>

        {/* Agent Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredAgents.map(agent => (
            <div
              key={agent.agent_id}
              className="card p-4 hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => setSelectedAgent(agent)}
            >
              <div className="flex items-start space-x-3">
                <div className="p-2 bg-purple-10 rounded-lg text-purple-60">
                  <CubeIcon className="w-6 h-6" />
                </div>
                <div className="flex-1">
                  <h3 className="font-medium text-gray-100">{agent.name}</h3>
                  <p className="text-xs text-gray-60">v{agent.version}</p>
                </div>
              </div>

              <p className="text-sm text-gray-70 mt-3 line-clamp-2">
                {agent.description}
              </p>

              <div className="flex items-center justify-between mt-4">
                <span className={`
                  px-2 py-0.5 text-xs rounded
                  ${agent.category === 'pre_search' ? 'bg-yellow-10 text-yellow-60' : ''}
                  ${agent.category === 'post_search' ? 'bg-blue-10 text-blue-60' : ''}
                  ${agent.category === 'response' ? 'bg-purple-10 text-purple-60' : ''}
                `}>
                  {agent.category.replace('_', '-')}
                </span>

                <button className="text-sm text-blue-60 hover:text-blue-70">
                  View Details →
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Agent Detail Modal */}
        {selectedAgent && (
          <AgentDetailModal
            agent={selectedAgent}
            onClose={() => setSelectedAgent(null)}
          />
        )}
      </div>
    </div>
  );
};
```

## API Integration

### Agent API Client

```typescript
// frontend/src/services/agentApiClient.ts

import apiClient from './apiClient';

export interface AgentManifest {
  agent_id: string;
  name: string;
  version: string;
  description: string;
  capabilities: string[];
  category: 'pre_search' | 'post_search' | 'response';
  config_schema: Record<string, any>;
}

export interface CollectionAgent {
  id: string;
  agent_id: string;
  name: string;
  description: string;
  config: {
    type: 'mcp' | 'builtin';
    context_forge_tool_id?: string;
    settings: Record<string, any>;
  };
  config_schema?: Record<string, any>;
  enabled: boolean;
  trigger_stage: 'pre_search' | 'post_search' | 'response';
  priority: number;
}

export interface AgentExecution {
  id: string;
  agent_id: string;
  agent_name: string;
  collection_id: string;
  trigger_stage: string;
  success: boolean;
  duration_ms: number;
  error?: string;
  created_at: string;
}

const agentApiClient = {
  // Available agents
  getAvailableAgents: async (): Promise<AgentManifest[]> => {
    const response = await apiClient.get('/api/v1/agents/');
    return response.data;
  },

  getAgentsByCapability: async (capability: string): Promise<AgentManifest[]> => {
    const response = await apiClient.get(`/api/v1/agents/capabilities/${capability}`);
    return response.data;
  },

  // User's agent configurations
  getUserAgentConfigs: async (): Promise<CollectionAgent[]> => {
    const response = await apiClient.get('/api/v1/agents/configs');
    return response.data;
  },

  createAgentConfig: async (config: Partial<CollectionAgent>): Promise<CollectionAgent> => {
    const response = await apiClient.post('/api/v1/agents/configs', config);
    return response.data;
  },

  updateAgentConfig: async (
    configId: string,
    updates: Partial<CollectionAgent>
  ): Promise<CollectionAgent> => {
    const response = await apiClient.patch(`/api/v1/agents/configs/${configId}`, updates);
    return response.data;
  },

  deleteAgentConfig: async (configId: string): Promise<void> => {
    await apiClient.delete(`/api/v1/agents/configs/${configId}`);
  },

  // Collection agents
  getCollectionAgents: async (collectionId: string): Promise<CollectionAgent[]> => {
    const response = await apiClient.get(`/api/v1/agents/collections/${collectionId}/agents`);
    return response.data;
  },

  addAgentToCollection: async (
    collectionId: string,
    agentConfigId: string
  ): Promise<void> => {
    await apiClient.post(`/api/v1/agents/collections/${collectionId}/agents`, {
      agent_config_id: agentConfigId
    });
  },

  removeAgentFromCollection: async (
    collectionId: string,
    agentConfigId: string
  ): Promise<void> => {
    await apiClient.delete(
      `/api/v1/agents/collections/${collectionId}/agents/${agentConfigId}`
    );
  },

  batchUpdatePriorities: async (
    updates: { id: string; priority: number }[]
  ): Promise<void> => {
    await apiClient.patch('/api/v1/agents/configs/priorities', { updates });
  },

  // Analytics
  getAgentAnalytics: async (
    agentConfigId?: string,
    dateRange?: { start: string; end: string }
  ): Promise<any> => {
    const params = new URLSearchParams();
    if (agentConfigId) params.append('agent_config_id', agentConfigId);
    if (dateRange) {
      params.append('start', dateRange.start);
      params.append('end', dateRange.end);
    }
    const response = await apiClient.get(`/api/v1/agents/analytics?${params}`);
    return response.data;
  },

  // Audit log
  getAgentExecutions: async (
    options?: {
      agentConfigId?: string;
      collectionId?: string;
      limit?: number;
      offset?: number;
    }
  ): Promise<AgentExecution[]> => {
    const params = new URLSearchParams();
    if (options?.agentConfigId) params.append('agent_config_id', options.agentConfigId);
    if (options?.collectionId) params.append('collection_id', options.collectionId);
    if (options?.limit) params.append('limit', options.limit.toString());
    if (options?.offset) params.append('offset', options.offset.toString());
    const response = await apiClient.get(`/api/v1/agents/executions?${params}`);
    return response.data;
  },
};

export default agentApiClient;
```

### Enhanced Search Response Schema

```typescript
// frontend/src/types/search.ts

export interface SearchResponse {
  answer: string;
  sources: Source[];
  cot_steps?: CotStep[];

  // NEW: Agent-related fields
  agent_artifacts?: AgentArtifact[];
  agent_executions?: AgentExecution[];
  pipeline_metadata?: {
    pre_search_agents: number;
    post_search_agents: number;
    response_agents: number;
    total_agent_time_ms: number;
  };
}

export interface AgentArtifact {
  agent_id: string;
  type: 'pptx' | 'pdf' | 'png' | 'mp3' | 'html' | 'txt';
  data: string;
  filename: string;
  metadata: Record<string, any>;
}

export interface AgentExecution {
  agent_id: string;
  agent_name: string;
  stage: 'pre_search' | 'post_search' | 'response';
  duration_ms: number;
  success: boolean;
  error?: string;
}
```

## State Management

### AgentContext

Context for managing agent-related state across the application.

```typescript
// frontend/src/contexts/AgentContext.tsx

interface AgentState {
  availableAgents: AgentManifest[];
  userConfigs: CollectionAgent[];
  isLoading: boolean;
  error: string | null;
}

interface AgentContextType extends AgentState {
  loadAvailableAgents: () => Promise<void>;
  loadUserConfigs: () => Promise<void>;
  createConfig: (config: Partial<CollectionAgent>) => Promise<CollectionAgent>;
  updateConfig: (id: string, updates: Partial<CollectionAgent>) => Promise<void>;
  deleteConfig: (id: string) => Promise<void>;
}

const AgentContext = createContext<AgentContextType | null>(null);

export const AgentProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<AgentState>({
    availableAgents: [],
    userConfigs: [],
    isLoading: false,
    error: null
  });

  const loadAvailableAgents = async () => {
    setState(s => ({ ...s, isLoading: true }));
    try {
      const agents = await agentApiClient.getAvailableAgents();
      setState(s => ({ ...s, availableAgents: agents, isLoading: false }));
    } catch (error) {
      setState(s => ({ ...s, error: 'Failed to load agents', isLoading: false }));
    }
  };

  const loadUserConfigs = async () => {
    setState(s => ({ ...s, isLoading: true }));
    try {
      const configs = await agentApiClient.getUserAgentConfigs();
      setState(s => ({ ...s, userConfigs: configs, isLoading: false }));
    } catch (error) {
      setState(s => ({ ...s, error: 'Failed to load configs', isLoading: false }));
    }
  };

  // ... other methods

  return (
    <AgentContext.Provider value={{
      ...state,
      loadAvailableAgents,
      loadUserConfigs,
      createConfig,
      updateConfig,
      deleteConfig
    }}>
      {children}
    </AgentContext.Provider>
  );
};

export const useAgents = () => {
  const context = useContext(AgentContext);
  if (!context) {
    throw new Error('useAgents must be used within AgentProvider');
  }
  return context;
};
```

## Accessibility

### Keyboard Navigation

- All agent cards and buttons are focusable
- Drag-and-drop has keyboard alternatives (up/down arrow keys)
- Modal focus trapping implemented
- Screen reader announcements for status changes

### ARIA Labels

```tsx
// Example: Artifact card
<div
  role="article"
  aria-label={`${artifact.type} artifact: ${artifact.filename}`}
>
  <button
    aria-label={`Download ${artifact.filename}`}
    onClick={handleDownload}
  >
    Download
  </button>
</div>

// Example: Pipeline status
<div
  role="progressbar"
  aria-valuenow={completedStages}
  aria-valuemax={totalStages}
  aria-label="Agent pipeline progress"
>
  ...
</div>
```

## Responsive Design

### Breakpoints

| Breakpoint | Width | Layout Changes |
|------------|-------|----------------|
| Mobile | < 640px | Single column, stacked artifacts |
| Tablet | 640-1024px | 2-column grid, collapsible panels |
| Desktop | > 1024px | 3-column grid, full sidebar |

### Mobile Considerations

- Artifact preview uses full-screen modal on mobile
- Drag-and-drop replaced with move up/down buttons on touch
- Pipeline status collapses to minimal indicator
- Agent config modal is full-screen on mobile

## Performance

### Lazy Loading

- Agent marketplace loads agents in pages of 20
- Artifact preview images loaded on-demand
- Audit log uses virtual scrolling for large lists

### Caching

- Available agents cached for 5 minutes
- User configs cached with SWR for real-time updates
- Artifact data not cached (too large)

### Bundle Optimization

- Agent components code-split by route
- react-beautiful-dnd loaded only when drag-drop needed
- Large icons tree-shaken

## Related Documents

- [MCP Integration Architecture](./mcp-integration-architecture.md)
- [SearchService Agent Hooks Architecture](./search-agent-hooks-architecture.md)
- [RAG Modulo MCP Server Architecture](./rag-modulo-mcp-server-architecture.md)
