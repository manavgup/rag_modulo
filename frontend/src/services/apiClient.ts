import axios, { AxiosInstance, AxiosResponse } from 'axios';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || '';

// Valid OpenAI TTS voice IDs
type VoiceId = 'alloy' | 'echo' | 'fable' | 'onyx' | 'nova' | 'shimmer';

interface SearchInput {
  question: string;
  collection_id: string;
  user_id: string;
  config_metadata?: Record<string, any>;
}

interface TokenWarning {
  warning_type: string;
  current_tokens: number;
  limit_tokens: number;
  percentage_used: number;
  message: string;
  severity: 'info' | 'warning' | 'critical';
  suggested_action?: string;
}

interface ChainOfThoughtStep {
  step_number: number;
  question: string;
  answer: string;
  sources_used: number;
  reasoning?: string;
}

interface ChainOfThoughtOutput {
  enabled: boolean;
  total_steps: number;
  steps: ChainOfThoughtStep[];
  final_synthesis?: string;
}

interface SearchResponse {
  answer: string;
  sources?: Array<{
    document_name: string;
    content: string;
    metadata: Record<string, any>;
  }>;
  documents?: Array<{
    document_id?: string;
    id?: string;
    document_name?: string;
    title?: string;
    name?: string;
    content?: string;
    text?: string;
    metadata?: Record<string, any>;
  }>;
  query_results?: Array<{
    chunk: {
      chunk_id: string;
      document_id: string;
      text: string;
      metadata: {
        chunk_number: number;
        page_number: number;
        source: string;
        document_id: string;
        [key: string]: any;
      };
    };
    score: number;
  }>;
  conversation_id?: string;
  metadata?: Record<string, any>;
  token_warning?: TokenWarning;
  cot_output?: ChainOfThoughtOutput;
}

interface Collection {
  id: string;
  name: string;
  description?: string;
  status: 'ready' | 'processing' | 'error' | 'warning' | 'completed';
  documents: CollectionDocument[];
  createdAt: Date;
  updatedAt: Date;
  documentCount: number;
}

interface CollectionDocument {
  id: string;
  name: string;
  type: string;
  size: number;
  uploadedAt: Date;
  status?: 'ready' | 'processing' | 'error' | 'completed';
  chunks?: number;
  vectorized?: boolean;
}

interface User {
  id: string;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  is_active: boolean;
  created_at: Date;
  updated_at: Date;
}

interface PromptTemplate {
  id: string;
  name: string;
  description?: string;
  template_type: 'rag' | 'question_generation';
  content: string;
  is_default: boolean;
  created_by: string;
  created_at: Date;
  updated_at: Date;
}

interface ConversationSession {
  id: string;
  user_id: string;
  collection_id: string;
  session_name: string;
  status: 'active' | 'paused' | 'archived' | 'expired' | 'deleted';
  context_window_size: number;
  max_messages: number;
  is_archived: boolean;
  is_pinned: boolean;
  created_at: Date;
  updated_at: Date;
  metadata: Record<string, any>;
  message_count: number;
}

interface ConversationMessage {
  id: string;
  session_id: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  message_type: 'question' | 'answer' | 'follow_up' | 'clarification' | 'error' | 'system' | 'system_message';
  created_at: Date;
  metadata?: {
    source_documents?: string[];
    search_metadata?: Record<string, any>;
    cot_used?: boolean;
    conversation_aware?: boolean;
    execution_time?: number;
    token_count?: number;
    model_used?: string;
    confidence_score?: number;
    context_length?: number;
  };
  token_count?: number;
  execution_time?: number;
  token_warning?: Record<string, any>;
  sources?: Array<{
    document_name: string;
    content: string;
    metadata: Record<string, any>;
  }>;
}

interface SessionStatistics {
  session_id: string;
  message_count: number;
  user_messages: number;
  assistant_messages: number;
  total_tokens: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  cot_usage_count: number;
  context_enhancement_count: number;
  created_at: Date;
  last_activity: Date;
  metadata: Record<string, any>;
}

interface CreateConversationInput {
  collection_id: string;
  session_name: string;
  context_window_size?: number;
  max_messages?: number;
  is_archived?: boolean;
  is_pinned?: boolean;
  metadata?: Record<string, any>;
}

interface UpdateConversationInput {
  session_name?: string;
  is_archived?: boolean;
  is_pinned?: boolean;
  metadata?: Record<string, any>;
}

// Podcast interfaces
interface VoiceSettings {
  voice_id: string;
  gender?: 'male' | 'female' | 'neutral';
  speed?: number;
  pitch?: number;
  language?: string;
  name?: string;
}

interface PodcastGenerationInput {
  user_id: string;
  collection_id: string;
  duration: 5 | 15 | 30 | 60;
  voice_settings: VoiceSettings;
  title?: string;
  description?: string;
  format: 'mp3' | 'wav' | 'ogg' | 'flac';
  host_voice: string;
  expert_voice: string;
  include_intro?: boolean;
  include_outro?: boolean;
  music_background?: boolean;
}

interface PodcastStepDetails {
  total_turns?: number;
  completed_turns?: number;
  current_speaker?: string;
}

interface Podcast {
  podcast_id: string;
  user_id: string;
  collection_id: string;
  status: 'queued' | 'generating' | 'completed' | 'failed' | 'cancelled';
  duration: 5 | 15 | 30 | 60;
  format: string;
  title?: string;
  audio_url?: string;
  transcript?: string;
  audio_size_bytes?: number;
  error_message?: string;
  progress_percentage: number;
  current_step?: string;
  step_details?: PodcastStepDetails;
  estimated_time_remaining?: number;
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

interface PodcastListResponse {
  podcasts: Podcast[];
  total_count: number;
}

interface PodcastQuestionInjection {
  podcast_id: string;
  timestamp_seconds: number;
  question: string;
  user_id: string;
}

interface SuggestedQuestion {
  id: string;
  collection_id: string;
  question: string;
  created_at: string;
}

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for auth tokens
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('access_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Search API
  async search(searchInput: SearchInput): Promise<SearchResponse> {
    const response: AxiosResponse<SearchResponse> = await this.client.post('/api/search', searchInput);
    return response.data;
  }

  // Collections API
  async getCollections(): Promise<Collection[]> {
    const response: AxiosResponse<any[]> = await this.client.get('/api/collections');
    return response.data.map(collection => ({
      id: collection.id,
      name: collection.name,
      description: collection.description || '',
      status: collection.status || 'ready',
      documents: (collection.files || []).map((file: any) => ({
        id: file.id,
        name: file.filename || file.name,
        type: file.type || 'unknown',
        size: file.size || 0,
        uploadedAt: new Date(file.uploaded_at || file.uploadedAt || new Date()),
        status: file.status || 'ready',
        chunks: file.chunks || 0,
        vectorized: file.vectorized || false
      })),
      createdAt: new Date(collection.created_at || collection.createdAt),
      updatedAt: new Date(collection.updated_at || collection.updatedAt),
      documentCount: (collection.files || []).length
    }));
  }

  async getCollection(id: string): Promise<Collection> {
    const response: AxiosResponse<any> = await this.client.get(`/api/collections/${id}`);
    const collection = response.data;
    return {
      id: collection.id,
      name: collection.name,
      description: collection.description || '',
      status: collection.status || 'ready',
      documents: (collection.files || []).map((file: any) => ({
        id: file.id,
        name: file.filename || file.name,
        type: file.type || 'unknown',
        size: file.size || 0,
        uploadedAt: new Date(file.uploaded_at || file.uploadedAt || new Date()),
        status: file.status || 'ready',
        chunks: file.chunks || 0,
        vectorized: file.vectorized || false
      })),
      createdAt: new Date(collection.created_at || collection.createdAt),
      updatedAt: new Date(collection.updated_at || collection.updatedAt),
      documentCount: (collection.files || []).length
    };
  }

  async createCollection(data: { name: string; description?: string }): Promise<Collection> {
    const response: AxiosResponse<any> = await this.client.post('/api/collections', data);
    const collection = response.data;
    return {
      id: collection.id,
      name: collection.name,
      description: collection.description || '',
      status: collection.status || 'ready',
      documents: (collection.files || []).map((file: any) => ({
        id: file.id,
        name: file.filename || file.name,
        type: file.type || 'unknown',
        size: file.size || 0,
        uploadedAt: new Date(file.uploaded_at || file.uploadedAt || new Date()),
        status: file.status || 'ready',
        chunks: file.chunks || 0,
        vectorized: file.vectorized || false
      })),
      createdAt: new Date(collection.created_at || collection.createdAt),
      updatedAt: new Date(collection.updated_at || collection.updatedAt),
      documentCount: (collection.files || []).length
    };
  }

  async updateCollection(id: string, data: { name?: string; description?: string }): Promise<Collection> {
    const response: AxiosResponse<any> = await this.client.put(`/api/collections/${id}`, data);
    const collection = response.data;
    return {
      id: collection.id,
      name: collection.name,
      description: collection.description || '',
      status: collection.status || 'ready',
      documents: (collection.files || []).map((file: any) => ({
        id: file.id,
        name: file.filename || file.name,
        type: file.type || 'unknown',
        size: file.size || 0,
        uploadedAt: new Date(file.uploaded_at || file.uploadedAt || new Date()),
        status: file.status || 'ready',
        chunks: file.chunks || 0,
        vectorized: file.vectorized || false
      })),
      createdAt: new Date(collection.created_at || collection.createdAt),
      updatedAt: new Date(collection.updated_at || collection.updatedAt),
      documentCount: (collection.files || []).length
    };
  }

  async deleteCollection(id: string): Promise<void> {
    await this.client.delete(`/api/collections/${id}`);
  }

  async getSuggestedQuestions(collectionId: string): Promise<SuggestedQuestion[]> {
    const response: AxiosResponse<SuggestedQuestion[]> = await this.client.get(
      `/api/collections/${collectionId}/questions`
    );
    return response.data;
  }

  // Document API
  async uploadDocuments(collectionId: string, files: File[]): Promise<CollectionDocument[]> {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    const response: AxiosResponse<any[]> = await this.client.post(
      `/api/collections/${collectionId}/documents`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data.map((file: any) => ({
      id: file.id,
      name: file.filename || file.name,
      type: file.type || 'unknown',
      size: file.size || 0,
      uploadedAt: new Date(file.uploaded_at || file.uploadedAt || new Date()),
      status: file.status || 'ready',
      chunks: file.chunks || 0,
      vectorized: file.vectorized || false
    }));
  }

  async deleteDocument(collectionId: string, documentId: string): Promise<void> {
    await this.client.delete(`/api/collections/${collectionId}/documents/${documentId}`);
  }

  // User API
  async getCurrentUser(): Promise<User> {
    // Use the correct auth endpoint that returns user info
    const response: AxiosResponse<any> = await this.client.get('/api/auth/userinfo');

    // The backend should always return valid user info when SKIP_AUTH is enabled
    // If it doesn't, we should fail rather than use hardcoded values
    if (!response.data.uuid && !response.data.sub) {
      throw new Error('Invalid user info received from auth endpoint');
    }

    // Map the auth response to User type
    return {
      id: response.data.uuid || response.data.sub,
      username: response.data.email?.split('@')[0] || response.data.name,
      email: response.data.email,
      first_name: response.data.name?.split(' ')[0],
      last_name: response.data.name?.split(' ').slice(1).join(' '),
      is_active: true,
      created_at: new Date(),
      updated_at: new Date()
    };
  }

  async updateUser(data: { first_name?: string; last_name?: string; email?: string }): Promise<User> {
    const response: AxiosResponse<User> = await this.client.put('/api/users/me', data);
    return {
      ...response.data,
      created_at: new Date(response.data.created_at),
      updated_at: new Date(response.data.updated_at)
    };
  }

  // Templates API
  async getPromptTemplates(): Promise<PromptTemplate[]> {
    const response: AxiosResponse<PromptTemplate[]> = await this.client.get('/api/prompt-templates');
    return response.data.map(template => ({
      ...template,
      created_at: new Date(template.created_at),
      updated_at: new Date(template.updated_at)
    }));
  }

  async createPromptTemplate(data: {
    name: string;
    description?: string;
    template_type: 'rag' | 'question_generation';
    content: string;
  }): Promise<PromptTemplate> {
    const response: AxiosResponse<PromptTemplate> = await this.client.post('/api/prompt-templates', data);
    return {
      ...response.data,
      created_at: new Date(response.data.created_at),
      updated_at: new Date(response.data.updated_at)
    };
  }

  async updatePromptTemplate(id: string, data: {
    name?: string;
    description?: string;
    content?: string;
  }): Promise<PromptTemplate> {
    const response: AxiosResponse<PromptTemplate> = await this.client.put(`/api/prompt-templates/${id}`, data);
    return {
      ...response.data,
      created_at: new Date(response.data.created_at),
      updated_at: new Date(response.data.updated_at)
    };
  }

  async setDefaultTemplate(id: string): Promise<PromptTemplate> {
    const response: AxiosResponse<PromptTemplate> = await this.client.post(`/api/prompt-templates/${id}/set-default`);
    return {
      ...response.data,
      created_at: new Date(response.data.created_at),
      updated_at: new Date(response.data.updated_at)
    };
  }

  async deletePromptTemplate(id: string): Promise<void> {
    await this.client.delete(`/api/prompt-templates/${id}`);
  }

  // Auth API
  async login(username: string, password: string): Promise<{ access_token: string; token_type: string }> {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    const response = await this.client.post('/api/auth/token', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    return response.data;
  }

  async logout(): Promise<void> {
    await this.client.post('/api/auth/logout');
    localStorage.removeItem('access_token');
  }

  // Dashboard API
  async getDashboardStats(): Promise<{
    totalDocuments: number;
    totalSearches: number;
    activeAgents: number;
    completedWorkflows: number;
    successRate: number;
    averageResponseTime: number;
    documentsTrend: {
      value: number;
      period: string;
      direction: 'up' | 'down';
    };
    searchesTrend: {
      value: number;
      period: string;
      direction: 'up' | 'down';
    };
    successRateTrend: {
      value: number;
      period: string;
      direction: 'up' | 'down';
    };
    responseTimeTrend: {
      value: number;
      period: string;
      direction: 'up' | 'down';
    };
    workflowsTrend: {
      value: number;
      period: string;
      direction: 'up' | 'down';
    };
  }> {
    const response = await this.client.get('/api/dashboard/stats');
    return response.data;
  }

  async getRecentActivity(): Promise<Array<{
    id: string;
    type: 'search' | 'workflow' | 'agent' | 'document';
    title: string;
    description: string;
    timestamp: string;
    status: 'success' | 'error' | 'pending' | 'running';
  }>> {
    const response = await this.client.get('/api/dashboard/activity');
    return response.data;
  }

  async getQuickStatistics(): Promise<{
    documentsProcessedToday: {
      metric: string;
      value: string;
      change: string;
      trend: 'up' | 'down';
    };
    searchQueries: {
      metric: string;
      value: string;
      change: string;
      trend: 'up' | 'down';
    };
    agentTasksCompleted: {
      metric: string;
      value: string;
      change: string;
      trend: 'up' | 'down';
    };
    averageProcessingTime: {
      metric: string;
      value: string;
      change: string;
      trend: 'up' | 'down';
    };
    errorRate: {
      metric: string;
      value: string;
      change: string;
      trend: 'up' | 'down';
    };
  }> {
    const response = await this.client.get('/api/dashboard/quick-stats');
    return response.data;
  }

  async getSystemHealth(): Promise<{
    overallStatus: string;
    components: Array<{
      component: string;
      healthPercentage: number;
    }>;
  }> {
    const response = await this.client.get('/api/dashboard/system-health');
    return response.data;
  }

  // Conversations API
  async getConversations(userId?: string, collectionId?: string): Promise<ConversationSession[]> {
    const params = new URLSearchParams();
    if (userId) params.append('user_id', userId);
    if (collectionId) params.append('collection_id', collectionId);

    const response: AxiosResponse<any[]> = await this.client.get(`/api/conversations?${params.toString()}`);
    return response.data.map(conversation => ({
      id: conversation.id,
      user_id: conversation.user_id,
      collection_id: conversation.collection_id,
      session_name: conversation.session_name,
      status: conversation.status,
      context_window_size: conversation.context_window_size,
      max_messages: conversation.max_messages,
      is_archived: conversation.is_archived,
      is_pinned: conversation.is_pinned,
      created_at: new Date(conversation.created_at),
      updated_at: new Date(conversation.updated_at),
      metadata: conversation.metadata || {},
      message_count: conversation.message_count || 0
    }));
  }

  async getConversation(sessionId: string): Promise<ConversationSession> {
    const response: AxiosResponse<any> = await this.client.get(`/api/conversations/${sessionId}`);
    const conversation = response.data;
    return {
      id: conversation.id,
      user_id: conversation.user_id,
      collection_id: conversation.collection_id,
      session_name: conversation.session_name,
      status: conversation.status,
      context_window_size: conversation.context_window_size,
      max_messages: conversation.max_messages,
      is_archived: conversation.is_archived,
      is_pinned: conversation.is_pinned,
      created_at: new Date(conversation.created_at),
      updated_at: new Date(conversation.updated_at),
      metadata: conversation.metadata || {},
      message_count: conversation.message_count || 0
    };
  }

  async createConversation(data: CreateConversationInput): Promise<ConversationSession> {
    const response: AxiosResponse<any> = await this.client.post('/api/conversations', data);
    const conversation = response.data;
    return {
      id: conversation.id,
      user_id: conversation.user_id,
      collection_id: conversation.collection_id,
      session_name: conversation.session_name,
      status: conversation.status,
      context_window_size: conversation.context_window_size,
      max_messages: conversation.max_messages,
      is_archived: conversation.is_archived,
      is_pinned: conversation.is_pinned,
      created_at: new Date(conversation.created_at),
      updated_at: new Date(conversation.updated_at),
      metadata: conversation.metadata || {},
      message_count: conversation.message_count || 0
    };
  }

  async updateConversation(sessionId: string, updates: UpdateConversationInput): Promise<ConversationSession> {
    const response: AxiosResponse<any> = await this.client.put(`/api/conversations/${sessionId}`, updates);
    const conversation = response.data;
    return {
      id: conversation.id,
      user_id: conversation.user_id,
      collection_id: conversation.collection_id,
      session_name: conversation.session_name,
      status: conversation.status,
      context_window_size: conversation.context_window_size,
      max_messages: conversation.max_messages,
      is_archived: conversation.is_archived,
      is_pinned: conversation.is_pinned,
      created_at: new Date(conversation.created_at),
      updated_at: new Date(conversation.updated_at),
      metadata: conversation.metadata || {},
      message_count: conversation.message_count || 0
    };
  }

  async deleteConversation(sessionId: string): Promise<void> {
    await this.client.delete(`/api/conversations/${sessionId}`);
  }

  async getConversationMessages(sessionId: string, limit: number = 50, offset: number = 0): Promise<ConversationMessage[]> {
    const params = new URLSearchParams();
    params.append('limit', limit.toString());
    params.append('offset', offset.toString());

    const response: AxiosResponse<any[]> = await this.client.get(`/api/conversations/${sessionId}/messages?${params.toString()}`);
    return response.data.map(message => ({
      id: message.id,
      session_id: message.session_id,
      content: message.content,
      role: message.role,
      message_type: message.message_type,
      created_at: new Date(message.created_at),
      metadata: message.metadata,
      token_count: message.token_count,
      execution_time: message.execution_time,
      token_warning: message.token_warning,
      sources: message.sources
    }));
  }

  async getConversationStatistics(sessionId: string): Promise<SessionStatistics> {
    const response: AxiosResponse<any> = await this.client.get(`/api/conversations/${sessionId}/statistics`);
    const stats = response.data;
    return {
      session_id: stats.session_id,
      message_count: stats.message_count,
      user_messages: stats.user_messages,
      assistant_messages: stats.assistant_messages,
      total_tokens: stats.total_tokens,
      total_prompt_tokens: stats.total_prompt_tokens,
      total_completion_tokens: stats.total_completion_tokens,
      cot_usage_count: stats.cot_usage_count,
      context_enhancement_count: stats.context_enhancement_count,
      created_at: new Date(stats.created_at),
      last_activity: new Date(stats.last_activity),
      metadata: stats.metadata || {}
    };
  }

  async getConversationSummary(sessionId: string, summaryType: string = 'brief'): Promise<{
    summary: string;
    summary_type: string;
    message_count: number;
    user_messages: number;
    assistant_messages: number;
    session_name: string;
    created_at: string;
    topics: string[];
    total_tokens: number;
    cot_usage_count: number;
    generated_at: string;
  }> {
    const response = await this.client.get(`/api/conversations/${sessionId}/summary?summary_type=${summaryType}`);
    return response.data;
  }

  async exportConversation(sessionId: string, format: string = 'json'): Promise<any> {
    const response = await this.client.post(`/api/conversations/${sessionId}/export`, { export_format: format });
    return response.data;
  }

  async sendConversationMessage(sessionId: string, content: string): Promise<ConversationMessage> {
    const payload = {
      session_id: sessionId,
      content: content,
      role: 'user',
      message_type: 'question'
    };

    const response: AxiosResponse<any> = await this.client.post(`/api/chat/sessions/${sessionId}/process`, payload);
    const message = response.data;

    return {
      id: message.id,
      session_id: message.session_id,
      content: message.content,
      role: message.role,
      message_type: message.message_type,
      created_at: new Date(message.created_at),
      metadata: message.metadata,
      token_count: message.token_count,
      execution_time: message.execution_time,
      token_warning: message.token_warning,
      sources: message.sources
    };
  }

  async archiveConversation(sessionId: string): Promise<ConversationSession> {
    const response: AxiosResponse<any> = await this.client.post(`/api/conversations/${sessionId}/archive`);
    const conversation = response.data;
    return {
      id: conversation.id,
      user_id: conversation.user_id,
      collection_id: conversation.collection_id,
      session_name: conversation.session_name,
      status: conversation.status,
      context_window_size: conversation.context_window_size,
      max_messages: conversation.max_messages,
      is_archived: conversation.is_archived,
      is_pinned: conversation.is_pinned,
      created_at: new Date(conversation.created_at),
      updated_at: new Date(conversation.updated_at),
      metadata: conversation.metadata || {},
      message_count: conversation.message_count || 0
    };
  }

  async restoreConversation(sessionId: string): Promise<ConversationSession> {
    const response: AxiosResponse<any> = await this.client.post(`/api/conversations/${sessionId}/restore`);
    const conversation = response.data;
    return {
      id: conversation.id,
      user_id: conversation.user_id,
      collection_id: conversation.collection_id,
      session_name: conversation.session_name,
      status: conversation.status,
      context_window_size: conversation.context_window_size,
      max_messages: conversation.max_messages,
      is_archived: conversation.is_archived,
      is_pinned: conversation.is_pinned,
      created_at: new Date(conversation.created_at),
      updated_at: new Date(conversation.updated_at),
      metadata: conversation.metadata || {},
      message_count: conversation.message_count || 0
    };
  }

  // Health check
  async healthCheck(): Promise<{ status: string }> {
    const response = await this.client.get('/api/health');
    return response.data;
  }

  // Podcast API
  async generatePodcast(input: PodcastGenerationInput): Promise<Podcast> {
    const response: AxiosResponse<Podcast> = await this.client.post('/api/podcasts/generate', input);
    return response.data;
  }

  async getPodcast(podcastId: string, userId: string): Promise<Podcast> {
    const response: AxiosResponse<Podcast> = await this.client.get(
      `/api/podcasts/${podcastId}?user_id=${userId}`
    );
    return response.data;
  }

  async listPodcasts(userId: string, limit: number = 100, offset: number = 0): Promise<PodcastListResponse> {
    const response: AxiosResponse<PodcastListResponse> = await this.client.get(
      `/api/podcasts/?user_id=${userId}&limit=${limit}&offset=${offset}`
    );
    return response.data;
  }

  async deletePodcast(podcastId: string, userId: string): Promise<void> {
    await this.client.delete(`/api/podcasts/${podcastId}?user_id=${userId}`);
  }

  async injectQuestion(injection: PodcastQuestionInjection): Promise<Podcast> {
    const response: AxiosResponse<Podcast> = await this.client.post(
      `/api/podcasts/${injection.podcast_id}/inject-question`,
      injection
    );
    return response.data;
  }

  async getVoicePreview(voiceId: VoiceId): Promise<Blob> {
    const response: AxiosResponse<Blob> = await this.client.get(
      `/api/podcasts/voice-preview/${voiceId}`,
      {
        responseType: 'blob',
      }
    );
    return response.data;
  }
}

// Create singleton instance
const apiClient = new ApiClient();

export default apiClient;
export type {
  SearchInput,
  SearchResponse,
  Collection,
  CollectionDocument,
  User,
  PromptTemplate,
  ConversationSession,
  ConversationMessage,
  SessionStatistics,
  CreateConversationInput,
  UpdateConversationInput,
  Podcast,
  PodcastGenerationInput,
  PodcastListResponse,
  PodcastQuestionInjection,
  VoiceSettings,
  PodcastStepDetails,
  SuggestedQuestion,
  VoiceId,
};
