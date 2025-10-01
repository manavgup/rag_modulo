import React, { useState, useEffect, useRef } from 'react';
import {
  PlusIcon,
  ArrowRightIcon,
  TrashIcon,
  PlayIcon,
  BookmarkIcon,
  EyeIcon,
  CogIcon,
  DocumentTextIcon,
  BoltIcon,
  ChartBarIcon,
  CheckCircleIcon,
  XMarkIcon,
  ArrowPathIcon,
  Square3Stack3DIcon,
} from '@heroicons/react/24/outline';
import { useNotification } from '../../contexts/NotificationContext';

interface WorkflowNode {
  id: string;
  type: 'input' | 'agent' | 'condition' | 'output';
  name: string;
  position: { x: number; y: number };
  config: {
    agentId?: string;
    agentType?: 'researcher' | 'analyzer' | 'synthesizer' | 'validator';
    prompt?: string;
    condition?: string;
    outputFormat?: string;
  };
  connections: string[];
}

interface Agent {
  id: string;
  name: string;
  type: 'researcher' | 'analyzer' | 'synthesizer' | 'validator';
  description: string;
}

interface Workflow {
  id: string;
  name: string;
  description: string;
  nodes: WorkflowNode[];
  createdAt: Date;
  lastModified: Date;
  status: 'draft' | 'published' | 'archived';
}

const LightweightWorkflowDesigner: React.FC = () => {
  const { addNotification } = useNotification();
  const canvasRef = useRef<HTMLDivElement>(null);
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [availableAgents, setAvailableAgents] = useState<Agent[]>([]);
  const [selectedNode, setSelectedNode] = useState<WorkflowNode | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [workflowName, setWorkflowName] = useState('');
  const [workflowDescription, setWorkflowDescription] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 1000));

      const mockAgents: Agent[] = [
        {
          id: '1',
          name: 'Research Agent',
          type: 'researcher',
          description: 'Specialized in gathering and analyzing research papers',
        },
        {
          id: '2',
          name: 'Data Analyzer',
          type: 'analyzer',
          description: 'Analyzes structured and unstructured data',
        },
        {
          id: '3',
          name: 'Content Synthesizer',
          type: 'synthesizer',
          description: 'Combines multiple sources into summaries',
        },
        {
          id: '4',
          name: 'Quality Validator',
          type: 'validator',
          description: 'Validates output quality and accuracy',
        },
      ];

      const mockWorkflow: Workflow = {
        id: '1',
        name: 'New Workflow',
        description: 'Design your workflow here',
        nodes: [
          {
            id: 'input-1',
            type: 'input',
            name: 'Input',
            position: { x: 100, y: 200 },
            config: {},
            connections: [],
          },
          {
            id: 'output-1',
            type: 'output',
            name: 'Output',
            position: { x: 600, y: 200 },
            config: { outputFormat: 'json' },
            connections: [],
          },
        ],
        createdAt: new Date(),
        lastModified: new Date(),
        status: 'draft',
      };

      setAvailableAgents(mockAgents);
      setWorkflow(mockWorkflow);
    } catch (error) {
      addNotification('error', 'Loading Error', 'Failed to load workflow designer data.');
    } finally {
      setIsLoading(false);
    }
  };

  const getNodeIcon = (type: string, agentType?: string) => {
    switch (type) {
      case 'input':
        return <Square3Stack3DIcon className="w-5 h-5" />;
      case 'output':
        return <DocumentTextIcon className="w-5 h-5" />;
      case 'condition':
        return <BoltIcon className="w-5 h-5" />;
      case 'agent':
        switch (agentType) {
          case 'researcher':
            return <DocumentTextIcon className="w-5 h-5" />;
          case 'analyzer':
            return <ChartBarIcon className="w-5 h-5" />;
          case 'synthesizer':
            return <BoltIcon className="w-5 h-5" />;
          case 'validator':
            return <CheckCircleIcon className="w-5 h-5" />;
          default:
            return <CogIcon className="w-5 h-5" />;
        }
      default:
        return <CogIcon className="w-5 h-5" />;
    }
  };

  const getNodeColor = (type: string) => {
    switch (type) {
      case 'input':
        return 'bg-green-10 border-green-50 text-green-50';
      case 'output':
        return 'bg-blue-10 border-blue-60 text-blue-60';
      case 'condition':
        return 'bg-yellow-10 border-yellow-30 text-yellow-30';
      case 'agent':
        return 'bg-purple-10 border-purple-60 text-purple-60';
      default:
        return 'bg-gray-10 border-gray-60 text-gray-100';
    }
  };

  const addNode = (type: WorkflowNode['type'], agentId?: string) => {
    if (!workflow) return;

    const agent = agentId ? availableAgents.find(a => a.id === agentId) : null;
    const newNode: WorkflowNode = {
      id: `${type}-${Date.now()}`,
      type,
      name: agent ? agent.name : type.charAt(0).toUpperCase() + type.slice(1),
      position: { x: 300, y: 150 },
      config: {
        agentId: agent?.id,
        agentType: agent?.type,
      },
      connections: [],
    };

    setWorkflow(prev => prev ? {
      ...prev,
      nodes: [...prev.nodes, newNode],
      lastModified: new Date(),
    } : null);

    addNotification('success', 'Node Added', `${newNode.name} node added to workflow.`);
  };

  const deleteNode = (nodeId: string) => {
    if (!workflow) return;

    setWorkflow(prev => prev ? {
      ...prev,
      nodes: prev.nodes.filter(node => node.id !== nodeId).map(node => ({
        ...node,
        connections: node.connections.filter(id => id !== nodeId),
      })),
      lastModified: new Date(),
    } : null);

    if (selectedNode?.id === nodeId) {
      setSelectedNode(null);
    }

    addNotification('success', 'Node Deleted', 'Node removed from workflow.');
  };

  const connectNodes = (fromId: string, toId: string) => {
    if (!workflow) return;

    setWorkflow(prev => prev ? {
      ...prev,
      nodes: prev.nodes.map(node => {
        if (node.id === fromId && !node.connections.includes(toId)) {
          return { ...node, connections: [...node.connections, toId] };
        }
        return node;
      }),
      lastModified: new Date(),
    } : null);
  };

  const updateNodePosition = (nodeId: string, position: { x: number; y: number }) => {
    if (!workflow) return;

    setWorkflow(prev => prev ? {
      ...prev,
      nodes: prev.nodes.map(node =>
        node.id === nodeId ? { ...node, position } : node
      ),
      lastModified: new Date(),
    } : null);
  };

  const updateNodeConfig = (nodeId: string, config: Partial<WorkflowNode['config']>) => {
    if (!workflow) return;

    setWorkflow(prev => prev ? {
      ...prev,
      nodes: prev.nodes.map(node =>
        node.id === nodeId ? { ...node, config: { ...node.config, ...config } } : node
      ),
      lastModified: new Date(),
    } : null);
  };

  const handleMouseDown = (e: React.MouseEvent, nodeId: string) => {
    e.preventDefault();
    const node = workflow?.nodes.find(n => n.id === nodeId);
    if (!node) return;

    setIsDragging(true);
    setDragOffset({
      x: e.clientX - node.position.x,
      y: e.clientY - node.position.y,
    });
    setSelectedNode(node);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging || !selectedNode || !canvasRef.current) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const newX = e.clientX - rect.left - dragOffset.x;
    const newY = e.clientY - rect.top - dragOffset.y;

    updateNodePosition(selectedNode.id, {
      x: Math.max(0, Math.min(newX, rect.width - 150)),
      y: Math.max(0, Math.min(newY, rect.height - 80)),
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const saveWorkflow = async () => {
    if (!workflow) return;

    try {
      await new Promise(resolve => setTimeout(resolve, 1000));

      const updatedWorkflow: Workflow = {
        ...workflow,
        name: workflowName || workflow.name,
        description: workflowDescription || workflow.description,
        lastModified: new Date(),
        status: 'published',
      };

      setWorkflow(updatedWorkflow);
      setShowSaveDialog(false);
      setWorkflowName('');
      setWorkflowDescription('');
      addNotification('success', 'Workflow Saved', 'Your workflow has been saved successfully.');
    } catch (error) {
      addNotification('error', 'Save Error', 'Failed to save workflow.');
    }
  };

  const executeWorkflow = () => {
    if (!workflow || workflow.nodes.length < 2) {
      addNotification('warning', 'Incomplete Workflow', 'Please add at least input and output nodes.');
      return;
    }

    addNotification('info', 'Workflow Execution', 'Workflow execution started. Check the monitor for progress.');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-60 mx-auto mb-4"></div>
          <p className="text-gray-70">Loading workflow designer...</p>
        </div>
      </div>
    );
  }

  if (!workflow) {
    return (
      <div className="min-h-screen bg-gray-10 p-6">
        <div className="max-w-6xl mx-auto text-center">
          <h1 className="text-2xl font-semibold text-gray-100 mb-4">Workflow Not Found</h1>
          <button onClick={loadData} className="btn-primary">
            Create New Workflow
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-10 flex">
      {/* Sidebar - Toolbox */}
      <div className="w-64 bg-white border-r border-gray-20 p-4">
        <h2 className="text-lg font-semibold text-gray-100 mb-4">Workflow Toolbox</h2>

        {/* Basic Nodes */}
        <div className="mb-6">
          <h3 className="text-sm font-medium text-gray-100 mb-3">Basic Nodes</h3>
          <div className="space-y-2">
            <button
              onClick={() => addNode('input')}
              className="w-full flex items-center space-x-3 p-3 text-left border border-gray-20 rounded-lg hover:bg-gray-10"
            >
              <div className="p-1 bg-green-10 rounded">
                <Square3Stack3DIcon className="w-4 h-4 text-green-50" />
              </div>
              <span className="text-sm text-gray-100">Input</span>
            </button>

            <button
              onClick={() => addNode('output')}
              className="w-full flex items-center space-x-3 p-3 text-left border border-gray-20 rounded-lg hover:bg-gray-10"
            >
              <div className="p-1 bg-blue-10 rounded">
                <DocumentTextIcon className="w-4 h-4 text-blue-60" />
              </div>
              <span className="text-sm text-gray-100">Output</span>
            </button>

            <button
              onClick={() => addNode('condition')}
              className="w-full flex items-center space-x-3 p-3 text-left border border-gray-20 rounded-lg hover:bg-gray-10"
            >
              <div className="p-1 bg-yellow-10 rounded">
                <BoltIcon className="w-4 h-4 text-yellow-30" />
              </div>
              <span className="text-sm text-gray-100">Condition</span>
            </button>
          </div>
        </div>

        {/* Agent Nodes */}
        <div className="mb-6">
          <h3 className="text-sm font-medium text-gray-100 mb-3">AI Agents</h3>
          <div className="space-y-2">
            {availableAgents.map((agent) => (
              <button
                key={agent.id}
                onClick={() => addNode('agent', agent.id)}
                className="w-full flex items-center space-x-3 p-3 text-left border border-gray-20 rounded-lg hover:bg-gray-10"
              >
                <div className="p-1 bg-purple-10 rounded">
                  {getNodeIcon('agent', agent.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-100 truncate">{agent.name}</p>
                  <p className="text-xs text-gray-60 truncate">{agent.description}</p>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Workflow Actions */}
        <div className="space-y-2">
          <button
            onClick={() => setShowSaveDialog(true)}
            className="btn-primary w-full flex items-center justify-center space-x-2"
          >
            <BookmarkIcon className="w-4 h-4" />
            <span>Save Workflow</span>
          </button>

          <button
            onClick={executeWorkflow}
            className="btn-secondary w-full flex items-center justify-center space-x-2"
          >
            <PlayIcon className="w-4 h-4" />
            <span>Execute</span>
          </button>
        </div>
      </div>

      {/* Main Canvas Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-gray-20 p-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-gray-100">{workflow.name}</h1>
              <p className="text-sm text-gray-70">{workflow.description}</p>
            </div>
            <div className="flex items-center space-x-2 text-sm text-gray-60">
              <span>Status: {workflow.status}</span>
              <span>•</span>
              <span>Last modified: {workflow.lastModified.toLocaleString()}</span>
            </div>
          </div>
        </div>

        {/* Canvas */}
        <div className="flex-1 overflow-hidden">
          <div
            ref={canvasRef}
            className="relative w-full h-full bg-gray-10 cursor-crosshair"
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          >
            {/* Render Connections */}
            <svg className="absolute inset-0 pointer-events-none" style={{ zIndex: 1 }}>
              {workflow.nodes.map((node) =>
                node.connections.map((connectionId) => {
                  const targetNode = workflow.nodes.find(n => n.id === connectionId);
                  if (!targetNode) return null;

                  const startX = node.position.x + 75;
                  const startY = node.position.y + 40;
                  const endX = targetNode.position.x + 75;
                  const endY = targetNode.position.y + 40;

                  return (
                    <g key={`${node.id}-${connectionId}`}>
                      <line
                        x1={startX}
                        y1={startY}
                        x2={endX}
                        y2={endY}
                        stroke="#6B7280"
                        strokeWidth="2"
                        markerEnd="url(#arrowhead)"
                      />
                    </g>
                  );
                })
              )}
              <defs>
                <marker
                  id="arrowhead"
                  markerWidth="10"
                  markerHeight="7"
                  refX="9"
                  refY="3.5"
                  orient="auto"
                >
                  <polygon points="0 0, 10 3.5, 0 7" fill="#6B7280" />
                </marker>
              </defs>
            </svg>

            {/* Render Nodes */}
            {workflow.nodes.map((node) => (
              <div
                key={node.id}
                className={`absolute w-32 h-20 border-2 rounded-lg cursor-move select-none ${
                  getNodeColor(node.type)
                } ${selectedNode?.id === node.id ? 'ring-2 ring-blue-60' : ''}`}
                style={{
                  left: node.position.x,
                  top: node.position.y,
                  zIndex: selectedNode?.id === node.id ? 10 : 2,
                }}
                onMouseDown={(e) => handleMouseDown(e, node.id)}
                onClick={() => setSelectedNode(node)}
              >
                <div className="p-2 h-full flex flex-col items-center justify-center text-center">
                  {getNodeIcon(node.type, node.config.agentType)}
                  <p className="text-xs font-medium mt-1 truncate w-full">{node.name}</p>
                  {node.type === 'agent' && (
                    <p className="text-xs opacity-75 truncate w-full">{node.config.agentType}</p>
                  )}
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteNode(node.id);
                  }}
                  className="absolute -top-2 -right-2 w-5 h-5 bg-red-50 text-white rounded-full flex items-center justify-center text-xs hover:bg-red-60"
                >
                  <XMarkIcon className="w-3 h-3" />
                </button>
              </div>
            ))}

            {/* Help Text */}
            {workflow.nodes.length === 2 && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="bg-white p-6 rounded-lg shadow-lg border border-gray-20 max-w-md text-center">
                  <BoltIcon className="w-12 h-12 text-gray-60 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-gray-100 mb-2">Design Your Workflow</h3>
                  <p className="text-gray-70 mb-4">
                    Drag AI agents from the sidebar to create your workflow. Connect nodes by clicking and dragging between them.
                  </p>
                  <div className="flex justify-center space-x-2 text-sm text-gray-60">
                    <span>• Add agents</span>
                    <span>• Connect nodes</span>
                    <span>• Configure settings</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Properties Panel */}
      {selectedNode && (
        <div className="w-80 bg-white border-l border-gray-20 p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-100">Node Properties</h3>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-gray-60 hover:text-gray-100"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-100 mb-2">Name</label>
              <input
                type="text"
                value={selectedNode.name}
                onChange={(e) => updateNodeConfig(selectedNode.id, { ...selectedNode.config })}
                className="input-field w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-100 mb-2">Type</label>
              <p className="text-sm text-gray-70 bg-gray-10 p-2 rounded capitalize">{selectedNode.type}</p>
            </div>

            {selectedNode.type === 'agent' && selectedNode.config.agentType && (
              <div>
                <label className="block text-sm font-medium text-gray-100 mb-2">Agent Type</label>
                <p className="text-sm text-gray-70 bg-gray-10 p-2 rounded capitalize">{selectedNode.config.agentType}</p>
              </div>
            )}

            {selectedNode.type === 'agent' && (
              <div>
                <label className="block text-sm font-medium text-gray-100 mb-2">Prompt</label>
                <textarea
                  value={selectedNode.config.prompt || ''}
                  onChange={(e) => updateNodeConfig(selectedNode.id, { prompt: e.target.value })}
                  placeholder="Enter custom prompt for this agent..."
                  className="input-field w-full h-24 resize-none"
                />
              </div>
            )}

            {selectedNode.type === 'condition' && (
              <div>
                <label className="block text-sm font-medium text-gray-100 mb-2">Condition</label>
                <textarea
                  value={selectedNode.config.condition || ''}
                  onChange={(e) => updateNodeConfig(selectedNode.id, { condition: e.target.value })}
                  placeholder="Define condition logic..."
                  className="input-field w-full h-20 resize-none"
                />
              </div>
            )}

            {selectedNode.type === 'output' && (
              <div>
                <label className="block text-sm font-medium text-gray-100 mb-2">Output Format</label>
                <select
                  value={selectedNode.config.outputFormat || 'json'}
                  onChange={(e) => updateNodeConfig(selectedNode.id, { outputFormat: e.target.value })}
                  className="input-field w-full"
                >
                  <option value="json">JSON</option>
                  <option value="text">Plain Text</option>
                  <option value="markdown">Markdown</option>
                  <option value="csv">CSV</option>
                </select>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-100 mb-2">Connections</label>
              <div className="space-y-1">
                {selectedNode.connections.length > 0 ? (
                  selectedNode.connections.map((connectionId) => {
                    const connectedNode = workflow.nodes.find(n => n.id === connectionId);
                    return connectedNode ? (
                      <div key={connectionId} className="flex items-center justify-between p-2 bg-gray-10 rounded">
                        <span className="text-sm text-gray-100">{connectedNode.name}</span>
                        <button
                          onClick={() => {
                            setWorkflow(prev => prev ? {
                              ...prev,
                              nodes: prev.nodes.map(node =>
                                node.id === selectedNode.id
                                  ? { ...node, connections: node.connections.filter(id => id !== connectionId) }
                                  : node
                              ),
                            } : null);
                          }}
                          className="text-red-50 hover:text-red-60"
                        >
                          <TrashIcon className="w-3 h-3" />
                        </button>
                      </div>
                    ) : null;
                  })
                ) : (
                  <p className="text-sm text-gray-60">No connections</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Save Dialog */}
      {showSaveDialog && (
        <div className="fixed inset-0 bg-gray-100 bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-semibold text-gray-100 mb-4">Save Workflow</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-100 mb-2">Workflow Name</label>
                <input
                  type="text"
                  value={workflowName}
                  onChange={(e) => setWorkflowName(e.target.value)}
                  placeholder={workflow.name}
                  className="input-field w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-100 mb-2">Description</label>
                <textarea
                  value={workflowDescription}
                  onChange={(e) => setWorkflowDescription(e.target.value)}
                  placeholder={workflow.description}
                  className="input-field w-full h-20 resize-none"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => setShowSaveDialog(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={saveWorkflow}
                className="btn-primary"
              >
                Save Workflow
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LightweightWorkflowDesigner;
