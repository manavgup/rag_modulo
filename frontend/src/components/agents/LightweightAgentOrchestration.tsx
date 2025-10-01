import React, { useState, useEffect } from 'react';
import {
  PlayIcon,
  PauseIcon,
  StopIcon,
  CogIcon,
  UserIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  XCircleIcon,
  ChartBarIcon,
  DocumentTextIcon,
  BoltIcon,
  ArrowPathIcon,
  EyeIcon,
  PlusIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import { useNotification } from '../../contexts/NotificationContext';

interface Agent {
  id: string;
  name: string;
  type: 'researcher' | 'analyzer' | 'synthesizer' | 'validator';
  status: 'idle' | 'running' | 'completed' | 'error' | 'paused';
  description: string;
  model: string;
  provider: 'openai' | 'anthropic' | 'watsonx';
  config: {
    temperature: number;
    maxTokens: number;
    systemPrompt: string;
  };
  metrics: {
    tasksCompleted: number;
    avgResponseTime: number;
    successRate: number;
    lastRun: Date | null;
  };
  currentTask?: {
    id: string;
    description: string;
    progress: number;
    startTime: Date;
  };
}

interface Workflow {
  id: string;
  name: string;
  description: string;
  status: 'draft' | 'running' | 'completed' | 'error' | 'paused';
  agents: string[];
  steps: WorkflowStep[];
  createdAt: Date;
  lastRun: Date | null;
  totalRuns: number;
}

interface WorkflowStep {
  id: string;
  name: string;
  agentId: string;
  order: number;
  status: 'pending' | 'running' | 'completed' | 'error';
  input: string;
  output?: string;
  duration?: number;
}

const LightweightAgentOrchestration: React.FC = () => {
  const { addNotification } = useNotification();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [activeTab, setActiveTab] = useState<'agents' | 'workflows' | 'monitor'>('agents');
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateAgent, setShowCreateAgent] = useState(false);

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
          status: 'idle',
          description: 'Specialized in gathering and analyzing research papers and academic content',
          model: 'gpt-4',
          provider: 'openai',
          config: {
            temperature: 0.3,
            maxTokens: 2048,
            systemPrompt: 'You are a research specialist focused on academic papers and scientific literature.',
          },
          metrics: {
            tasksCompleted: 47,
            avgResponseTime: 2340,
            successRate: 94.5,
            lastRun: new Date('2024-01-14T10:30:00'),
          },
        },
        {
          id: '2',
          name: 'Data Analyzer',
          type: 'analyzer',
          status: 'running',
          description: 'Analyzes structured and unstructured data to extract insights',
          model: 'claude-3-sonnet',
          provider: 'anthropic',
          config: {
            temperature: 0.1,
            maxTokens: 4096,
            systemPrompt: 'You are a data analysis expert capable of processing complex datasets.',
          },
          metrics: {
            tasksCompleted: 32,
            avgResponseTime: 1890,
            successRate: 97.2,
            lastRun: new Date(),
          },
          currentTask: {
            id: 'task-123',
            description: 'Analyzing customer feedback trends',
            progress: 67,
            startTime: new Date(Date.now() - 300000),
          },
        },
        {
          id: '3',
          name: 'Content Synthesizer',
          type: 'synthesizer',
          status: 'completed',
          description: 'Combines multiple sources to create comprehensive summaries',
          model: 'watsonx-granite',
          provider: 'watsonx',
          config: {
            temperature: 0.7,
            maxTokens: 3072,
            systemPrompt: 'You synthesize information from multiple sources into coherent summaries.',
          },
          metrics: {
            tasksCompleted: 28,
            avgResponseTime: 3120,
            successRate: 89.7,
            lastRun: new Date('2024-01-14T09:15:00'),
          },
        },
        {
          id: '4',
          name: 'Quality Validator',
          type: 'validator',
          status: 'error',
          description: 'Validates output quality and ensures accuracy standards',
          model: 'gpt-3.5-turbo',
          provider: 'openai',
          config: {
            temperature: 0.2,
            maxTokens: 1024,
            systemPrompt: 'You are a quality assurance specialist focused on accuracy and completeness.',
          },
          metrics: {
            tasksCompleted: 15,
            avgResponseTime: 980,
            successRate: 92.1,
            lastRun: new Date('2024-01-14T08:45:00'),
          },
        },
      ];

      const mockWorkflows: Workflow[] = [
        {
          id: '1',
          name: 'Document Processing Pipeline',
          description: 'End-to-end document analysis and summarization workflow',
          status: 'running',
          agents: ['1', '2', '3', '4'],
          steps: [
            { id: 's1', name: 'Extract Content', agentId: '1', order: 1, status: 'completed', input: 'PDF documents', output: 'Structured text', duration: 2300 },
            { id: 's2', name: 'Analyze Data', agentId: '2', order: 2, status: 'running', input: 'Structured text' },
            { id: 's3', name: 'Synthesize Summary', agentId: '3', order: 3, status: 'pending', input: 'Analysis results' },
            { id: 's4', name: 'Validate Output', agentId: '4', order: 4, status: 'pending', input: 'Summary draft' },
          ],
          createdAt: new Date('2024-01-10'),
          lastRun: new Date(),
          totalRuns: 23,
        },
        {
          id: '2',
          name: 'Research Synthesis',
          description: 'Combines multiple research papers into comprehensive insights',
          status: 'completed',
          agents: ['1', '3'],
          steps: [
            { id: 's5', name: 'Gather Research', agentId: '1', order: 1, status: 'completed', input: 'Query terms', output: 'Research papers', duration: 4500 },
            { id: 's6', name: 'Create Synthesis', agentId: '3', order: 2, status: 'completed', input: 'Research papers', output: 'Comprehensive report', duration: 6200 },
          ],
          createdAt: new Date('2024-01-08'),
          lastRun: new Date('2024-01-13T14:20:00'),
          totalRuns: 8,
        },
      ];

      setAgents(mockAgents);
      setWorkflows(mockWorkflows);
    } catch (error) {
      addNotification('error', 'Loading Error', 'Failed to load agent orchestration data.');
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <PlayIcon className="w-4 h-4 text-blue-60" />;
      case 'completed':
        return <CheckCircleIcon className="w-4 h-4 text-green-50" />;
      case 'error':
        return <XCircleIcon className="w-4 h-4 text-red-50" />;
      case 'paused':
        return <PauseIcon className="w-4 h-4 text-yellow-30" />;
      default:
        return <ClockIcon className="w-4 h-4 text-gray-60" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'bg-blue-10 text-blue-60';
      case 'completed':
        return 'bg-green-10 text-green-50';
      case 'error':
        return 'bg-red-10 text-red-50';
      case 'paused':
        return 'bg-yellow-10 text-yellow-30';
      default:
        return 'bg-gray-10 text-gray-60';
    }
  };

  const getAgentTypeIcon = (type: string) => {
    switch (type) {
      case 'researcher':
        return <DocumentTextIcon className="w-5 h-5" />;
      case 'analyzer':
        return <ChartBarIcon className="w-5 h-5" />;
      case 'synthesizer':
        return <BoltIcon className="w-5 h-5" />;
      case 'validator':
        return <CheckCircleIcon className="w-5 h-5" />;
      default:
        return <UserIcon className="w-5 h-5" />;
    }
  };

  const controlAgent = (agentId: string, action: 'start' | 'pause' | 'stop') => {
    setAgents(prev => prev.map(agent => {
      if (agent.id === agentId) {
        let newStatus: Agent['status'] = agent.status;
        switch (action) {
          case 'start':
            newStatus = 'running';
            break;
          case 'pause':
            newStatus = 'paused';
            break;
          case 'stop':
            newStatus = 'idle';
            break;
        }
        return { ...agent, status: newStatus };
      }
      return agent;
    }));

    addNotification('success', 'Agent Control', `Agent ${action}ed successfully.`);
  };

  const controlWorkflow = (workflowId: string, action: 'start' | 'pause' | 'stop') => {
    setWorkflows(prev => prev.map(workflow => {
      if (workflow.id === workflowId) {
        let newStatus: Workflow['status'] = workflow.status;
        switch (action) {
          case 'start':
            newStatus = 'running';
            break;
          case 'pause':
            newStatus = 'paused';
            break;
          case 'stop':
            newStatus = 'draft';
            break;
        }
        return { ...workflow, status: newStatus };
      }
      return workflow;
    }));

    addNotification('success', 'Workflow Control', `Workflow ${action}ed successfully.`);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-60 mx-auto mb-4"></div>
          <p className="text-gray-70">Loading agent orchestration...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-10 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-gray-100">Agent Orchestration</h1>
            <p className="text-gray-70">Manage AI agents and coordinate complex workflows</p>
          </div>
          <div className="flex space-x-3">
            <button
              onClick={() => setShowCreateAgent(true)}
              className="btn-secondary flex items-center space-x-2"
            >
              <PlusIcon className="w-4 h-4" />
              <span>Create Agent</span>
            </button>
            <button
              onClick={loadData}
              className="btn-secondary flex items-center space-x-2"
            >
              <ArrowPathIcon className="w-4 h-4" />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="mb-6">
          <nav className="flex space-x-8">
            {[
              { id: 'agents', name: 'Agents', icon: UserIcon },
              { id: 'workflows', name: 'Workflows', icon: BoltIcon },
              { id: 'monitor', name: 'Monitor', icon: ChartBarIcon },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center space-x-2 px-3 py-2 text-sm font-medium rounded-md ${
                  activeTab === tab.id
                    ? 'bg-blue-60 text-white'
                    : 'text-gray-70 hover:text-gray-100 hover:bg-gray-20'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                <span>{tab.name}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Agents Tab */}
        {activeTab === 'agents' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Agent List */}
            <div className="lg:col-span-2 space-y-4">
              {agents.map((agent) => (
                <div key={agent.id} className="card p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-blue-10 rounded-lg">
                        {getAgentTypeIcon(agent.type)}
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-100">{agent.name}</h3>
                        <p className="text-sm text-gray-70 capitalize">{agent.type}</p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium flex items-center space-x-1 ${getStatusColor(agent.status)}`}>
                        {getStatusIcon(agent.status)}
                        <span className="capitalize">{agent.status}</span>
                      </span>
                      <button
                        onClick={() => setSelectedAgent(agent)}
                        className="text-gray-60 hover:text-gray-100"
                      >
                        <EyeIcon className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  <p className="text-gray-70 mb-4">{agent.description}</p>

                  {agent.currentTask && (
                    <div className="bg-blue-10 p-3 rounded-lg mb-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-blue-60">Current Task</span>
                        <span className="text-sm text-blue-60">{agent.currentTask.progress}%</span>
                      </div>
                      <p className="text-sm text-blue-60 mb-2">{agent.currentTask.description}</p>
                      <div className="w-full bg-blue-20 rounded-full h-2">
                        <div
                          className="bg-blue-60 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${agent.currentTask.progress}%` }}
                        />
                      </div>
                    </div>
                  )}

                  <div className="grid grid-cols-3 gap-4 mb-4 text-center">
                    <div>
                      <p className="text-lg font-semibold text-gray-100">{agent.metrics.tasksCompleted}</p>
                      <p className="text-xs text-gray-60">Tasks Completed</p>
                    </div>
                    <div>
                      <p className="text-lg font-semibold text-gray-100">{agent.metrics.avgResponseTime}ms</p>
                      <p className="text-xs text-gray-60">Avg Response</p>
                    </div>
                    <div>
                      <p className="text-lg font-semibold text-gray-100">{agent.metrics.successRate}%</p>
                      <p className="text-xs text-gray-60">Success Rate</p>
                    </div>
                  </div>

                  <div className="flex space-x-2">
                    {agent.status === 'idle' && (
                      <button
                        onClick={() => controlAgent(agent.id, 'start')}
                        className="btn-primary flex items-center space-x-2 flex-1"
                      >
                        <PlayIcon className="w-4 h-4" />
                        <span>Start</span>
                      </button>
                    )}
                    {agent.status === 'running' && (
                      <>
                        <button
                          onClick={() => controlAgent(agent.id, 'pause')}
                          className="btn-secondary flex items-center space-x-2 flex-1"
                        >
                          <PauseIcon className="w-4 h-4" />
                          <span>Pause</span>
                        </button>
                        <button
                          onClick={() => controlAgent(agent.id, 'stop')}
                          className="btn-secondary text-red-50 hover:bg-red-50 hover:text-white flex items-center space-x-2 flex-1"
                        >
                          <StopIcon className="w-4 h-4" />
                          <span>Stop</span>
                        </button>
                      </>
                    )}
                    {agent.status === 'paused' && (
                      <>
                        <button
                          onClick={() => controlAgent(agent.id, 'start')}
                          className="btn-primary flex items-center space-x-2 flex-1"
                        >
                          <PlayIcon className="w-4 h-4" />
                          <span>Resume</span>
                        </button>
                        <button
                          onClick={() => controlAgent(agent.id, 'stop')}
                          className="btn-secondary text-red-50 hover:bg-red-50 hover:text-white flex items-center space-x-2 flex-1"
                        >
                          <StopIcon className="w-4 h-4" />
                          <span>Stop</span>
                        </button>
                      </>
                    )}
                    <button className="btn-secondary p-2">
                      <CogIcon className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Agent Details Sidebar */}
            <div className="lg:col-span-1">
              {selectedAgent ? (
                <div className="card p-6 sticky top-6">
                  <h3 className="font-semibold text-gray-100 mb-4">{selectedAgent.name} Details</h3>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-100 mb-1">Model</label>
                      <p className="text-sm text-gray-70">{selectedAgent.model}</p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-100 mb-1">Provider</label>
                      <p className="text-sm text-gray-70 capitalize">{selectedAgent.provider}</p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-100 mb-1">Temperature</label>
                      <p className="text-sm text-gray-70">{selectedAgent.config.temperature}</p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-100 mb-1">Max Tokens</label>
                      <p className="text-sm text-gray-70">{selectedAgent.config.maxTokens}</p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-100 mb-1">System Prompt</label>
                      <p className="text-sm text-gray-70 bg-gray-10 p-2 rounded text-ellipsis">
                        {selectedAgent.config.systemPrompt}
                      </p>
                    </div>

                    {selectedAgent.metrics.lastRun && (
                      <div>
                        <label className="block text-sm font-medium text-gray-100 mb-1">Last Run</label>
                        <p className="text-sm text-gray-70">
                          {selectedAgent.metrics.lastRun.toLocaleString()}
                        </p>
                      </div>
                    )}
                  </div>

                  <button className="btn-secondary w-full mt-4">
                    Edit Configuration
                  </button>
                </div>
              ) : (
                <div className="card p-6 text-center">
                  <UserIcon className="w-12 h-12 text-gray-60 mx-auto mb-4" />
                  <p className="text-gray-70">Select an agent to view details</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Workflows Tab */}
        {activeTab === 'workflows' && (
          <div className="space-y-6">
            {workflows.map((workflow) => (
              <div key={workflow.id} className="card p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="font-semibold text-gray-100 mb-1">{workflow.name}</h3>
                    <p className="text-gray-70 mb-2">{workflow.description}</p>
                    <div className="flex items-center space-x-4 text-sm text-gray-60">
                      <span>{workflow.agents.length} agents</span>
                      <span>{workflow.totalRuns} total runs</span>
                      {workflow.lastRun && (
                        <span>Last run: {workflow.lastRun.toLocaleDateString()}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium flex items-center space-x-1 ${getStatusColor(workflow.status)}`}>
                      {getStatusIcon(workflow.status)}
                      <span className="capitalize">{workflow.status}</span>
                    </span>
                  </div>
                </div>

                {/* Workflow Steps */}
                <div className="mb-4">
                  <h4 className="font-medium text-gray-100 mb-3">Workflow Steps</h4>
                  <div className="space-y-2">
                    {workflow.steps.map((step, index) => (
                      <div key={step.id} className="flex items-center space-x-3 p-3 bg-gray-10 rounded-lg">
                        <div className="flex items-center justify-center w-6 h-6 bg-gray-20 rounded-full text-xs font-medium text-gray-70">
                          {step.order}
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium text-gray-100">{step.name}</p>
                          <p className="text-xs text-gray-60">
                            Agent: {agents.find(a => a.id === step.agentId)?.name}
                          </p>
                        </div>
                        <div className="flex items-center space-x-2">
                          {getStatusIcon(step.status)}
                          {step.duration && (
                            <span className="text-xs text-gray-60">{step.duration}ms</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Workflow Controls */}
                <div className="flex space-x-2">
                  {workflow.status === 'draft' && (
                    <button
                      onClick={() => controlWorkflow(workflow.id, 'start')}
                      className="btn-primary flex items-center space-x-2"
                    >
                      <PlayIcon className="w-4 h-4" />
                      <span>Start Workflow</span>
                    </button>
                  )}
                  {workflow.status === 'running' && (
                    <>
                      <button
                        onClick={() => controlWorkflow(workflow.id, 'pause')}
                        className="btn-secondary flex items-center space-x-2"
                      >
                        <PauseIcon className="w-4 h-4" />
                        <span>Pause</span>
                      </button>
                      <button
                        onClick={() => controlWorkflow(workflow.id, 'stop')}
                        className="btn-secondary text-red-50 hover:bg-red-50 hover:text-white flex items-center space-x-2"
                      >
                        <StopIcon className="w-4 h-4" />
                        <span>Stop</span>
                      </button>
                    </>
                  )}
                  {workflow.status === 'paused' && (
                    <>
                      <button
                        onClick={() => controlWorkflow(workflow.id, 'start')}
                        className="btn-primary flex items-center space-x-2"
                      >
                        <PlayIcon className="w-4 h-4" />
                        <span>Resume</span>
                      </button>
                      <button
                        onClick={() => controlWorkflow(workflow.id, 'stop')}
                        className="btn-secondary text-red-50 hover:bg-red-50 hover:text-white flex items-center space-x-2"
                      >
                        <StopIcon className="w-4 h-4" />
                        <span>Stop</span>
                      </button>
                    </>
                  )}
                  <button className="btn-secondary">
                    View Results
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Monitor Tab */}
        {activeTab === 'monitor' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* System Overview */}
            <div className="card p-6">
              <h3 className="font-semibold text-gray-100 mb-4">System Overview</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center">
                  <p className="text-2xl font-bold text-blue-60">{agents.filter(a => a.status === 'running').length}</p>
                  <p className="text-sm text-gray-70">Active Agents</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-green-50">{workflows.filter(w => w.status === 'running').length}</p>
                  <p className="text-sm text-gray-70">Running Workflows</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-gray-100">{agents.reduce((sum, a) => sum + a.metrics.tasksCompleted, 0)}</p>
                  <p className="text-sm text-gray-70">Total Tasks</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-purple-60">{workflows.reduce((sum, w) => sum + w.totalRuns, 0)}</p>
                  <p className="text-sm text-gray-70">Total Runs</p>
                </div>
              </div>
            </div>

            {/* Recent Activity */}
            <div className="card p-6">
              <h3 className="font-semibold text-gray-100 mb-4">Recent Activity</h3>
              <div className="space-y-3">
                <div className="flex items-center space-x-3 p-2 border border-gray-20 rounded">
                  <CheckCircleIcon className="w-4 h-4 text-green-50" />
                  <div className="flex-1">
                    <p className="text-sm text-gray-100">Research Agent completed task</p>
                    <p className="text-xs text-gray-60">2 minutes ago</p>
                  </div>
                </div>
                <div className="flex items-center space-x-3 p-2 border border-gray-20 rounded">
                  <PlayIcon className="w-4 h-4 text-blue-60" />
                  <div className="flex-1">
                    <p className="text-sm text-gray-100">Document Processing Pipeline started</p>
                    <p className="text-xs text-gray-60">5 minutes ago</p>
                  </div>
                </div>
                <div className="flex items-center space-x-3 p-2 border border-gray-20 rounded">
                  <ExclamationCircleIcon className="w-4 h-4 text-red-50" />
                  <div className="flex-1">
                    <p className="text-sm text-gray-100">Quality Validator encountered error</p>
                    <p className="text-xs text-gray-60">10 minutes ago</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default LightweightAgentOrchestration;
