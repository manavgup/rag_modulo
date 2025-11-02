/**
 * API client for user settings (Prompt Templates, LLM Parameters, Pipelines)
 */

import axios from 'axios';

const API_BASE = '/api/users';

// ============================================================================
// Types
// ============================================================================

export interface PromptTemplate {
  id: string;
  user_id: string;
  name: string;
  template_type: 'RAG_QUERY' | 'QUESTION_GENERATION' | 'PODCAST_GENERATION' | 'RERANKING' | 'COT_REASONING' | 'CUSTOM';
  system_prompt: string | null;
  template_format: string;
  input_variables: Record<string, any>;
  example_inputs?: Record<string, any>;
  context_strategy?: any;
  max_context_length?: number;
  stop_sequences?: string[];
  validation_schema?: any;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface PromptTemplateInput {
  user_id: string;
  name: string;
  template_type: string;
  system_prompt?: string;
  template_format: string;
  input_variables: Record<string, any>;
  example_inputs?: Record<string, any>;
  context_strategy?: any;
  max_context_length?: number;
  stop_sequences?: string[];
  validation_schema?: any;
  is_default?: boolean;
}

export interface LLMParameters {
  id: string;
  user_id: string;
  provider_name: string;
  model_id: string;
  temperature: number;
  max_tokens: number;
  top_p: number;
  top_k?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
  stop_sequences?: string[];
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface LLMParametersInput {
  user_id: string;
  provider_name: string;
  model_id: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  top_k?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
  stop_sequences?: string[];
  is_default?: boolean;
}

export interface PipelineConfig {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  is_default: boolean;
  retrieval_config: any;
  reranking_config?: any;
  generation_config?: any;
  created_at: string;
  updated_at: string;
}

export interface PipelineConfigInput {
  user_id: string;
  name: string;
  description?: string;
  is_default?: boolean;
  retrieval_config: any;
  reranking_config?: any;
  generation_config?: any;
}

// ============================================================================
// Prompt Templates API
// ============================================================================

export const promptTemplatesApi = {
  /**
   * Get all prompt templates for a user
   */
  async getAll(userId: string): Promise<PromptTemplate[]> {
    const response = await axios.get(`${API_BASE}/${userId}/prompt-templates`);
    return response.data;
  },

  /**
   * Create a new prompt template
   */
  async create(userId: string, template: PromptTemplateInput): Promise<PromptTemplate> {
    const response = await axios.post(`${API_BASE}/${userId}/prompt-templates`, template);
    return response.data;
  },

  /**
   * Update an existing prompt template
   */
  async update(userId: string, templateId: string, template: Partial<PromptTemplateInput>): Promise<PromptTemplate> {
    const response = await axios.put(`${API_BASE}/${userId}/prompt-templates/${templateId}`, template);
    return response.data;
  },

  /**
   * Delete a prompt template
   */
  async delete(userId: string, templateId: string): Promise<boolean> {
    const response = await axios.delete(`${API_BASE}/${userId}/prompt-templates/${templateId}`);
    return response.data;
  },

  /**
   * Set a template as the default for its type
   */
  async setDefault(userId: string, templateId: string): Promise<PromptTemplate> {
    const response = await axios.put(`${API_BASE}/${userId}/prompt-templates/${templateId}/default`);
    return response.data;
  },

  /**
   * Get templates by type
   */
  async getByType(userId: string, templateType: string): Promise<PromptTemplate | null> {
    const response = await axios.get(`${API_BASE}/${userId}/prompt-templates/type/${templateType}`);
    return response.data;
  },
};

// ============================================================================
// LLM Parameters API
// ============================================================================

export const llmParametersApi = {
  /**
   * Get all LLM parameters for a user
   */
  async getAll(userId: string): Promise<LLMParameters[]> {
    const response = await axios.get(`${API_BASE}/${userId}/llm-parameters`);
    return response.data;
  },

  /**
   * Create new LLM parameters
   */
  async create(userId: string, parameters: LLMParametersInput): Promise<LLMParameters> {
    const response = await axios.post(`${API_BASE}/${userId}/llm-parameters`, parameters);
    return response.data;
  },

  /**
   * Update existing LLM parameters
   */
  async update(userId: string, parameterId: string, parameters: Partial<LLMParametersInput>): Promise<LLMParameters> {
    const response = await axios.put(`${API_BASE}/${userId}/llm-parameters/${parameterId}`, parameters);
    return response.data;
  },

  /**
   * Delete LLM parameters
   */
  async delete(userId: string, parameterId: string): Promise<boolean> {
    const response = await axios.delete(`${API_BASE}/${userId}/llm-parameters/${parameterId}`);
    return response.data;
  },

  /**
   * Set parameters as default
   */
  async setDefault(userId: string, parameterId: string): Promise<LLMParameters> {
    const response = await axios.put(`${API_BASE}/${userId}/llm-parameters/${parameterId}/default`);
    return response.data;
  },
};

// ============================================================================
// Pipeline Configuration API
// ============================================================================

export const pipelineConfigApi = {
  /**
   * Get all pipeline configurations for a user
   */
  async getAll(userId: string): Promise<PipelineConfig[]> {
    const response = await axios.get(`${API_BASE}/${userId}/pipelines`);
    return response.data;
  },

  /**
   * Create a new pipeline configuration
   */
  async create(userId: string, config: PipelineConfigInput): Promise<PipelineConfig> {
    const response = await axios.post(`${API_BASE}/${userId}/pipelines`, config);
    return response.data;
  },

  /**
   * Update an existing pipeline configuration
   */
  async update(userId: string, pipelineId: string, config: Partial<PipelineConfigInput>): Promise<PipelineConfig> {
    const response = await axios.put(`${API_BASE}/${userId}/pipelines/${pipelineId}`, config);
    return response.data;
  },

  /**
   * Delete a pipeline configuration
   */
  async delete(userId: string, pipelineId: string): Promise<boolean> {
    const response = await axios.delete(`${API_BASE}/${userId}/pipelines/${pipelineId}`);
    return response.data;
  },

  /**
   * Set pipeline as default
   */
  async setDefault(userId: string, pipelineId: string): Promise<PipelineConfig> {
    const response = await axios.put(`${API_BASE}/${userId}/pipelines/${pipelineId}/default`);
    return response.data;
  },
};
