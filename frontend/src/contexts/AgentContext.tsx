import React, { createContext, useContext, useState, ReactNode } from 'react';

export interface Agent {
  id: string;
  name: string;
  type: 'research' | 'synthesis' | 'validation' | 'planner';
  description: string;
  capabilities: string[];
  status: 'active' | 'inactive' | 'maintenance';
  version: string;
  configuration: Record<string, any>;
  createdAt: Date;
  updatedAt: Date;
}

export interface AgentSession {
  id: string;
  userId: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  context: Record<string, any>;
  startedAt: Date;
  completedAt?: Date;
  errorMessage?: string;
}

export interface AgentTask {
  id: string;
  sessionId: string;
  agentId: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  input: Record<string, any>;
  output?: Record<string, any>;
  startedAt: Date;
  completedAt?: Date;
  errorMessage?: string;
}

interface AgentContextType {
  agents: Agent[];
  sessions: AgentSession[];
  tasks: AgentTask[];
  selectedAgent: Agent | null;
  selectedSession: AgentSession | null;
  isLoading: boolean;

  // Agent Management
  fetchAgents: () => Promise<void>;
  createAgent: (agent: Omit<Agent, 'id' | 'createdAt' | 'updatedAt'>) => Promise<void>;
  updateAgent: (id: string, updates: Partial<Agent>) => Promise<void>;
  deleteAgent: (id: string) => Promise<void>;
  selectAgent: (agent: Agent | null) => void;

  // Session Management
  fetchSessions: () => Promise<void>;
  createSession: (userId: string, context?: Record<string, any>) => Promise<AgentSession>;
  updateSession: (id: string, updates: Partial<AgentSession>) => Promise<void>;
  selectSession: (session: AgentSession | null) => void;

  // Task Management
  fetchTasks: (sessionId?: string) => Promise<void>;
  createTask: (sessionId: string, agentId: string, input: Record<string, any>) => Promise<AgentTask>;
  updateTask: (id: string, updates: Partial<AgentTask>) => Promise<void>;

  // Orchestration
  startOrchestration: (query: string, agents: string[]) => Promise<AgentSession>;
  getOrchestrationStatus: (sessionId: string) => Promise<AgentSession>;
  cancelOrchestration: (sessionId: string) => Promise<void>;
}

const AgentContext = createContext<AgentContextType | undefined>(undefined);

interface AgentProviderProps {
  children: ReactNode;
}

export const AgentProvider: React.FC<AgentProviderProps> = ({ children }) => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [sessions, setSessions] = useState<AgentSession[]>([]);
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [selectedSession, setSelectedSession] = useState<AgentSession | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Mock data for UI-first development
  const mockAgents: Agent[] = [
    {
      id: '1',
      name: 'Research Agent',
      type: 'research',
      description: 'Specialized in document research and information gathering',
      capabilities: ['document_search', 'information_extraction', 'source_validation'],
      status: 'active',
      version: '1.0.0',
      configuration: { max_results: 10, confidence_threshold: 0.8 },
      createdAt: new Date('2024-01-01'),
      updatedAt: new Date('2024-01-15'),
    },
    {
      id: '2',
      name: 'Synthesis Agent',
      type: 'synthesis',
      description: 'Combines information from multiple sources into coherent responses',
      capabilities: ['information_synthesis', 'response_generation', 'coherence_check'],
      status: 'active',
      version: '1.0.0',
      configuration: { max_length: 1000, style: 'professional' },
      createdAt: new Date('2024-01-01'),
      updatedAt: new Date('2024-01-15'),
    },
    {
      id: '3',
      name: 'Validation Agent',
      type: 'validation',
      description: 'Validates responses for accuracy and completeness',
      capabilities: ['fact_checking', 'completeness_validation', 'accuracy_assessment'],
      status: 'active',
      version: '1.0.0',
      configuration: { strict_mode: true, require_sources: true },
      createdAt: new Date('2024-01-01'),
      updatedAt: new Date('2024-01-15'),
    },
    {
      id: '4',
      name: 'Task Planner',
      type: 'planner',
      description: 'Plans and coordinates multi-step tasks',
      capabilities: ['task_planning', 'workflow_coordination', 'resource_allocation'],
      status: 'active',
      version: '1.0.0',
      configuration: { max_steps: 10, parallel_execution: true },
      createdAt: new Date('2024-01-01'),
      updatedAt: new Date('2024-01-15'),
    },
  ];

  const fetchAgents = async (): Promise<void> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      setAgents(mockAgents);
    } catch (error) {
      console.error('Error fetching agents:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const createAgent = async (agentData: Omit<Agent, 'id' | 'createdAt' | 'updatedAt'>): Promise<void> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      const newAgent: Agent = {
        ...agentData,
        id: Math.random().toString(36).substr(2, 9),
        createdAt: new Date(),
        updatedAt: new Date(),
      };
      setAgents(prev => [...prev, newAgent]);
    } catch (error) {
      console.error('Error creating agent:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const updateAgent = async (id: string, updates: Partial<Agent>): Promise<void> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      setAgents(prev => prev.map(agent =>
        agent.id === id
          ? { ...agent, ...updates, updatedAt: new Date() }
          : agent
      ));
    } catch (error) {
      console.error('Error updating agent:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const deleteAgent = async (id: string): Promise<void> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      setAgents(prev => prev.filter(agent => agent.id !== id));
    } catch (error) {
      console.error('Error deleting agent:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const selectAgent = (agent: Agent | null): void => {
    setSelectedAgent(agent);
  };

  const fetchSessions = async (): Promise<void> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      setSessions([]);
    } catch (error) {
      console.error('Error fetching sessions:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const createSession = async (userId: string, context: Record<string, any> = {}): Promise<AgentSession> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      const newSession: AgentSession = {
        id: Math.random().toString(36).substr(2, 9),
        userId,
        status: 'pending',
        context,
        startedAt: new Date(),
      };
      setSessions(prev => [...prev, newSession]);
      return newSession;
    } catch (error) {
      console.error('Error creating session:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const updateSession = async (id: string, updates: Partial<AgentSession>): Promise<void> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      setSessions(prev => prev.map(session =>
        session.id === id ? { ...session, ...updates } : session
      ));
    } catch (error) {
      console.error('Error updating session:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const selectSession = (session: AgentSession | null): void => {
    setSelectedSession(session);
  };

  const fetchTasks = async (sessionId?: string): Promise<void> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      setTasks([]);
    } catch (error) {
      console.error('Error fetching tasks:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const createTask = async (sessionId: string, agentId: string, input: Record<string, any>): Promise<AgentTask> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      const newTask: AgentTask = {
        id: Math.random().toString(36).substr(2, 9),
        sessionId,
        agentId,
        status: 'pending',
        input,
        startedAt: new Date(),
      };
      setTasks(prev => [...prev, newTask]);
      return newTask;
    } catch (error) {
      console.error('Error creating task:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const updateTask = async (id: string, updates: Partial<AgentTask>): Promise<void> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      setTasks(prev => prev.map(task =>
        task.id === id ? { ...task, ...updates } : task
      ));
    } catch (error) {
      console.error('Error updating task:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const startOrchestration = async (query: string, agents: string[]): Promise<AgentSession> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 1000));
      const session = await createSession('current-user', { query, agents });
      return session;
    } catch (error) {
      console.error('Error starting orchestration:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const getOrchestrationStatus = async (sessionId: string): Promise<AgentSession> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      const session = sessions.find(s => s.id === sessionId);
      if (!session) {
        throw new Error('Session not found');
      }
      return session;
    } catch (error) {
      console.error('Error getting orchestration status:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const cancelOrchestration = async (sessionId: string): Promise<void> => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 500));
      await updateSession(sessionId, { status: 'failed', errorMessage: 'Cancelled by user' });
    } catch (error) {
      console.error('Error cancelling orchestration:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const value: AgentContextType = {
    agents,
    sessions,
    tasks,
    selectedAgent,
    selectedSession,
    isLoading,
    fetchAgents,
    createAgent,
    updateAgent,
    deleteAgent,
    selectAgent,
    fetchSessions,
    createSession,
    updateSession,
    selectSession,
    fetchTasks,
    createTask,
    updateTask,
    startOrchestration,
    getOrchestrationStatus,
    cancelOrchestration,
  };

  return (
    <AgentContext.Provider value={value}>
      {children}
    </AgentContext.Provider>
  );
};

export const useAgent = (): AgentContextType => {
  const context = useContext(AgentContext);
  if (context === undefined) {
    throw new Error('useAgent must be used within an AgentProvider');
  }
  return context;
};
