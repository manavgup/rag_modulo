import React, { createContext, useContext, useState, ReactNode } from 'react';

export interface WorkflowStep {
  id: string;
  type: 'input' | 'process' | 'output' | 'condition' | 'loop';
  name: string;
  description: string;
  configuration: Record<string, any>;
  position: { x: number; y: number };
  connections: string[];
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  steps: WorkflowStep[];
  status: 'draft' | 'published' | 'archived';
  version: string;
  createdAt: Date;
  updatedAt: Date;
  createdBy: string;
}

export interface WorkflowExecution {
  id: string;
  workflowId: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  startedAt: Date;
  completedAt?: Date;
  input: Record<string, any>;
  output?: Record<string, any>;
  errorMessage?: string;
  stepExecutions: StepExecution[];
}

export interface StepExecution {
  id: string;
  stepId: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  startedAt: Date;
  completedAt?: Date;
  input: Record<string, any>;
  output?: Record<string, any>;
  errorMessage?: string;
}

export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  tags: string[];
  workflow: Omit<Workflow, 'id' | 'createdAt' | 'updatedAt' | 'createdBy'>;
  rating: number;
  usageCount: number;
  createdAt: Date;
  createdBy: string;
}

interface WorkflowContextType {
  workflows: Workflow[];
  executions: WorkflowExecution[];
  templates: WorkflowTemplate[];
  selectedWorkflow: Workflow | null;
  selectedExecution: WorkflowExecution | null;
  isLoading: boolean;

  // Workflow Management
  fetchWorkflows: () => Promise<void>;
  createWorkflow: (workflow: Omit<Workflow, 'id' | 'createdAt' | 'updatedAt'>) => Promise<void>;
  updateWorkflow: (id: string, updates: Partial<Workflow>) => Promise<void>;
  deleteWorkflow: (id: string) => Promise<void>;
  selectWorkflow: (workflow: Workflow | null) => void;

  // Step Management
  addStep: (workflowId: string, step: Omit<WorkflowStep, 'id'>) => Promise<void>;
  updateStep: (workflowId: string, stepId: string, updates: Partial<WorkflowStep>) => Promise<void>;
  deleteStep: (workflowId: string, stepId: string) => Promise<void>;
  connectSteps: (workflowId: string, fromStepId: string, toStepId: string) => Promise<void>;
  disconnectSteps: (workflowId: string, fromStepId: string, toStepId: string) => Promise<void>;

  // Execution Management
  fetchExecutions: (workflowId?: string) => Promise<void>;
  executeWorkflow: (workflowId: string, input: Record<string, any>) => Promise<WorkflowExecution>;
  cancelExecution: (executionId: string) => Promise<void>;
  selectExecution: (execution: WorkflowExecution | null) => void;

  // Template Management
  fetchTemplates: () => Promise<void>;
  createTemplate: (template: Omit<WorkflowTemplate, 'id' | 'createdAt' | 'createdBy'>) => Promise<void>;
  instantiateTemplate: (templateId: string) => Promise<Workflow>;
  rateTemplate: (templateId: string, rating: number) => Promise<void>;
}

const WorkflowContext = createContext<WorkflowContextType | undefined>(undefined);

interface WorkflowProviderProps {
  children: ReactNode;
}

export const WorkflowProvider: React.FC<WorkflowProviderProps> = ({ children }) => {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [executions, setExecutions] = useState<WorkflowExecution[]>([]);
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null);
  const [selectedExecution, setSelectedExecution] = useState<WorkflowExecution | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Mock data for UI-first development
  const mockTemplates: WorkflowTemplate[] = [
    {
      id: '1',
      name: 'Document Analysis Pipeline',
      description: 'Complete document processing and analysis workflow',
      category: 'Document Processing',
      tags: ['analysis', 'document', 'nlp'],
      workflow: {
        name: 'Document Analysis Pipeline',
        description: 'Complete document processing and analysis workflow',
        steps: [
          {
            id: 'step1',
            type: 'input',
            name: 'Document Input',
            description: 'Upload and validate documents',
            configuration: { allowed_formats: ['pdf', 'docx', 'txt'] },
            position: { x: 100, y: 100 },
            connections: ['step2'],
          },
          {
            id: 'step2',
            type: 'process',
            name: 'Text Extraction',
            description: 'Extract text from documents',
            configuration: { extraction_method: 'pymupdf' },
            position: { x: 300, y: 100 },
            connections: ['step3'],
          },
          {
            id: 'step3',
            type: 'process',
            name: 'Chunking',
            description: 'Split text into manageable chunks',
            configuration: { chunk_size: 1000, overlap: 200 },
            position: { x: 500, y: 100 },
            connections: ['step4'],
          },
          {
            id: 'step4',
            type: 'process',
            name: 'Embedding Generation',
            description: 'Generate vector embeddings',
            configuration: { model: 'sentence-transformers' },
            position: { x: 700, y: 100 },
            connections: ['step5'],
          },
          {
            id: 'step5',
            type: 'output',
            name: 'Store Results',
            description: 'Store processed data',
            configuration: { database: 'milvus' },
            position: { x: 900, y: 100 },
            connections: [],
          },
        ],
        status: 'published',
        version: '1.0.0',
      },
      rating: 4.5,
      usageCount: 150,
      createdAt: new Date('2024-01-01'),
      createdBy: 'system',
    },
    {
      id: '2',
      name: 'Multi-Agent RAG Query',
      description: 'Complex query processing using multiple agents',
      category: 'Agent Orchestration',
      tags: ['agents', 'rag', 'query'],
      workflow: {
        name: 'Multi-Agent RAG Query',
        description: 'Complex query processing using multiple agents',
        steps: [
          {
            id: 'step1',
            type: 'input',
            name: 'Query Input',
            description: 'Receive user query',
            configuration: { max_length: 1000 },
            position: { x: 100, y: 100 },
            connections: ['step2'],
          },
          {
            id: 'step2',
            type: 'process',
            name: 'Research Agent',
            description: 'Gather relevant information',
            configuration: { agent_type: 'research' },
            position: { x: 300, y: 50 },
            connections: ['step4'],
          },
          {
            id: 'step3',
            type: 'process',
            name: 'Validation Agent',
            description: 'Validate information quality',
            configuration: { agent_type: 'validation' },
            position: { x: 300, y: 150 },
            connections: ['step4'],
          },
          {
            id: 'step4',
            type: 'process',
            name: 'Synthesis Agent',
            description: 'Combine and synthesize results',
            configuration: { agent_type: 'synthesis' },
            position: { x: 500, y: 100 },
            connections: ['step5'],
          },
          {
            id: 'step5',
            type: 'output',
            name: 'Response Output',
            description: 'Return final response',
            configuration: { format: 'markdown' },
            position: { x: 700, y: 100 },
            connections: [],
          },
        ],
        status: 'published',
        version: '1.0.0',
      },
      rating: 4.8,
      usageCount: 89,
      createdAt: new Date('2024-01-15'),
      createdBy: 'system',
    },
  ];

  const fetchWorkflows = async (): Promise<void> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      setWorkflows([]);
    } catch (error) {
      console.error('Error fetching workflows:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const createWorkflow = async (workflowData: Omit<Workflow, 'id' | 'createdAt' | 'updatedAt'>): Promise<void> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      const newWorkflow: Workflow = {
        ...workflowData,
        id: Math.random().toString(36).substr(2, 9),
        createdAt: new Date(),
        updatedAt: new Date(),
      };
      setWorkflows(prev => [...prev, newWorkflow]);
    } catch (error) {
      console.error('Error creating workflow:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const updateWorkflow = async (id: string, updates: Partial<Workflow>): Promise<void> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      setWorkflows(prev => prev.map(workflow =>
        workflow.id === id
          ? { ...workflow, ...updates, updatedAt: new Date() }
          : workflow
      ));
    } catch (error) {
      console.error('Error updating workflow:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const deleteWorkflow = async (id: string): Promise<void> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      setWorkflows(prev => prev.filter(workflow => workflow.id !== id));
    } catch (error) {
      console.error('Error deleting workflow:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const selectWorkflow = (workflow: Workflow | null): void => {
    setSelectedWorkflow(workflow);
  };

  const addStep = async (workflowId: string, stepData: Omit<WorkflowStep, 'id'>): Promise<void> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      const newStep: WorkflowStep = {
        ...stepData,
        id: Math.random().toString(36).substr(2, 9),
      };
      setWorkflows(prev => prev.map(workflow =>
        workflow.id === workflowId
          ? { ...workflow, steps: [...workflow.steps, newStep], updatedAt: new Date() }
          : workflow
      ));
    } catch (error) {
      console.error('Error adding step:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const updateStep = async (workflowId: string, stepId: string, updates: Partial<WorkflowStep>): Promise<void> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      setWorkflows(prev => prev.map(workflow =>
        workflow.id === workflowId
          ? {
              ...workflow,
              steps: workflow.steps.map(step =>
                step.id === stepId ? { ...step, ...updates } : step
              ),
              updatedAt: new Date()
            }
          : workflow
      ));
    } catch (error) {
      console.error('Error updating step:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const deleteStep = async (workflowId: string, stepId: string): Promise<void> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      setWorkflows(prev => prev.map(workflow =>
        workflow.id === workflowId
          ? {
              ...workflow,
              steps: workflow.steps.filter(step => step.id !== stepId),
              updatedAt: new Date()
            }
          : workflow
      ));
    } catch (error) {
      console.error('Error deleting step:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const connectSteps = async (workflowId: string, fromStepId: string, toStepId: string): Promise<void> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      setWorkflows(prev => prev.map(workflow =>
        workflow.id === workflowId
          ? {
              ...workflow,
              steps: workflow.steps.map(step =>
                step.id === fromStepId
                  ? { ...step, connections: [...step.connections, toStepId] }
                  : step
              ),
              updatedAt: new Date()
            }
          : workflow
      ));
    } catch (error) {
      console.error('Error connecting steps:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const disconnectSteps = async (workflowId: string, fromStepId: string, toStepId: string): Promise<void> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      setWorkflows(prev => prev.map(workflow =>
        workflow.id === workflowId
          ? {
              ...workflow,
              steps: workflow.steps.map(step =>
                step.id === fromStepId
                  ? { ...step, connections: step.connections.filter(id => id !== toStepId) }
                  : step
              ),
              updatedAt: new Date()
            }
          : workflow
      ));
    } catch (error) {
      console.error('Error disconnecting steps:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const fetchExecutions = async (workflowId?: string): Promise<void> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      setExecutions([]);
    } catch (error) {
      console.error('Error fetching executions:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const executeWorkflow = async (workflowId: string, input: Record<string, any>): Promise<WorkflowExecution> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 1000));
      const newExecution: WorkflowExecution = {
        id: Math.random().toString(36).substr(2, 9),
        workflowId,
        status: 'running',
        startedAt: new Date(),
        input,
        stepExecutions: [],
      };
      setExecutions(prev => [...prev, newExecution]);
      return newExecution;
    } catch (error) {
      console.error('Error executing workflow:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const cancelExecution = async (executionId: string): Promise<void> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      setExecutions(prev => prev.map(execution =>
        execution.id === executionId
          ? { ...execution, status: 'cancelled', completedAt: new Date() }
          : execution
      ));
    } catch (error) {
      console.error('Error cancelling execution:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const selectExecution = (execution: WorkflowExecution | null): void => {
    setSelectedExecution(execution);
  };

  const fetchTemplates = async (): Promise<void> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      setTemplates(mockTemplates);
    } catch (error) {
      console.error('Error fetching templates:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const createTemplate = async (templateData: Omit<WorkflowTemplate, 'id' | 'createdAt' | 'createdBy'>): Promise<void> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      const newTemplate: WorkflowTemplate = {
        ...templateData,
        id: Math.random().toString(36).substr(2, 9),
        createdAt: new Date(),
        createdBy: 'current-user',
      };
      setTemplates(prev => [...prev, newTemplate]);
    } catch (error) {
      console.error('Error creating template:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const instantiateTemplate = async (templateId: string): Promise<Workflow> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      const template = templates.find(t => t.id === templateId);
      if (!template) {
        throw new Error('Template not found');
      }
      const newWorkflow: Workflow = {
        ...template.workflow,
        id: Math.random().toString(36).substr(2, 9),
        createdAt: new Date(),
        updatedAt: new Date(),
        createdBy: 'current-user',
      };
      setWorkflows(prev => [...prev, newWorkflow]);
      return newWorkflow;
    } catch (error) {
      console.error('Error instantiating template:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const rateTemplate = async (templateId: string, rating: number): Promise<void> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      setTemplates(prev => prev.map(template =>
        template.id === templateId
          ? { ...template, rating: (template.rating + rating) / 2 }
          : template
      ));
    } catch (error) {
      console.error('Error rating template:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const value: WorkflowContextType = {
    workflows,
    executions,
    templates,
    selectedWorkflow,
    selectedExecution,
    isLoading,
    fetchWorkflows,
    createWorkflow,
    updateWorkflow,
    deleteWorkflow,
    selectWorkflow,
    addStep,
    updateStep,
    deleteStep,
    connectSteps,
    disconnectSteps,
    fetchExecutions,
    executeWorkflow,
    cancelExecution,
    selectExecution,
    fetchTemplates,
    createTemplate,
    instantiateTemplate,
    rateTemplate,
  };

  return (
    <WorkflowContext.Provider value={value}>
      {children}
    </WorkflowContext.Provider>
  );
};

export const useWorkflow = (): WorkflowContextType => {
  const context = useContext(WorkflowContext);
  if (context === undefined) {
    throw new Error('useWorkflow must be used within a WorkflowProvider');
  }
  return context;
};
