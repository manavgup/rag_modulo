/**
 * API client for user settings (Prompt Templates, LLM Parameters, Pipelines)
 */

import axios, { AxiosError } from 'axios';

const API_BASE = '/api/users';

// ============================================================================
// Validation Utilities
// ============================================================================

/**
 * Validates that userId is a non-empty string
 * @throws {Error} If userId is invalid
 */
function validateUserId(userId: string): void {
  if (!userId || typeof userId !== 'string' || userId.trim().length === 0) {
    throw new Error('Invalid user ID: userId must be a non-empty string');
  }
}

/**
 * Validates UUID format (basic check)
 */
function isValidUUID(str: string): boolean {
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  return uuidRegex.test(str);
}

/**
 * Enhanced error handling wrapper for API calls
 */
async function handleApiCall<T>(apiCall: () => Promise<T>): Promise<T> {
  try {
    return await apiCall();
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<{ detail?: string; message?: string }>;

      // Handle specific HTTP status codes
      if (axiosError.response) {
        const { status, data } = axiosError.response;
        const message = data?.detail || data?.message || axiosError.message;

        switch (status) {
          case 400:
            throw new Error(`Bad Request: ${message}`);
          case 401:
            throw new Error('Unauthorized: Please log in to access this resource');
          case 403:
            throw new Error('Forbidden: You do not have permission to perform this action');
          case 404:
            throw new Error(`Not Found: ${message || 'The requested resource was not found'}`);
          case 409:
            throw new Error(`Conflict: ${message || 'A resource with this name already exists'}`);
          case 422:
            throw new Error(`Validation Error: ${message || 'The provided data is invalid'}`);
          case 429:
            throw new Error('Too Many Requests: Please wait a moment before trying again');
          case 500:
            throw new Error('Server Error: The server encountered an error. Please try again later');
          case 502:
          case 503:
          case 504:
            throw new Error('Service Unavailable: The service is temporarily unavailable. Please try again later');
          default:
            throw new Error(`API Error (${status}): ${message || 'An unexpected error occurred'}`);
        }
      }

      // Handle network errors
      if (axiosError.request) {
        throw new Error('Network Error: Unable to connect to the server. Please check your internet connection');
      }
    }

    // Re-throw if it's already an Error
    if (error instanceof Error) {
      throw error;
    }

    // Fallback for unknown errors
    throw new Error(`Unexpected Error: ${String(error)}`);
  }
}

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
    validateUserId(userId);
    return handleApiCall(async () => {
      const response = await axios.get(`${API_BASE}/${userId}/prompt-templates`);
      return response.data;
    });
  },

  /**
   * Create a new prompt template
   */
  async create(userId: string, template: PromptTemplateInput): Promise<PromptTemplate> {
    validateUserId(userId);
    if (!template.name || !template.template_type) {
      throw new Error('Template name and type are required');
    }
    return handleApiCall(async () => {
      const response = await axios.post(`${API_BASE}/${userId}/prompt-templates`, template);
      return response.data;
    });
  },

  /**
   * Update an existing prompt template
   */
  async update(userId: string, templateId: string, template: Partial<PromptTemplateInput>): Promise<PromptTemplate> {
    validateUserId(userId);
    if (!templateId || typeof templateId !== 'string' || templateId.trim().length === 0) {
      throw new Error('Invalid template ID: templateId must be a non-empty string');
    }
    return handleApiCall(async () => {
      const response = await axios.put(`${API_BASE}/${userId}/prompt-templates/${templateId}`, template);
      return response.data;
    });
  },

  /**
   * Delete a prompt template
   */
  async delete(userId: string, templateId: string): Promise<boolean> {
    validateUserId(userId);
    if (!templateId || typeof templateId !== 'string' || templateId.trim().length === 0) {
      throw new Error('Invalid template ID: templateId must be a non-empty string');
    }
    return handleApiCall(async () => {
      const response = await axios.delete(`${API_BASE}/${userId}/prompt-templates/${templateId}`);
      return response.data;
    });
  },

  /**
   * Set a template as the default for its type
   */
  async setDefault(userId: string, templateId: string): Promise<PromptTemplate> {
    validateUserId(userId);
    if (!templateId || typeof templateId !== 'string' || templateId.trim().length === 0) {
      throw new Error('Invalid template ID: templateId must be a non-empty string');
    }
    return handleApiCall(async () => {
      const response = await axios.put(`${API_BASE}/${userId}/prompt-templates/${templateId}/default`);
      return response.data;
    });
  },

  /**
   * Get templates by type
   */
  async getByType(userId: string, templateType: string): Promise<PromptTemplate | null> {
    validateUserId(userId);
    if (!templateType || typeof templateType !== 'string') {
      throw new Error('Invalid template type: templateType must be a non-empty string');
    }
    return handleApiCall(async () => {
      const response = await axios.get(`${API_BASE}/${userId}/prompt-templates/type/${templateType}`);
      return response.data;
    });
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
    validateUserId(userId);
    return handleApiCall(async () => {
      const response = await axios.get(`${API_BASE}/${userId}/llm-parameters`);
      return response.data;
    });
  },

  /**
   * Create new LLM parameters
   */
  async create(userId: string, parameters: LLMParametersInput): Promise<LLMParameters> {
    validateUserId(userId);
    if (!parameters.provider_name || !parameters.model_id) {
      throw new Error('Provider name and model ID are required');
    }
    return handleApiCall(async () => {
      const response = await axios.post(`${API_BASE}/${userId}/llm-parameters`, parameters);
      return response.data;
    });
  },

  /**
   * Update existing LLM parameters
   */
  async update(userId: string, parameterId: string, parameters: Partial<LLMParametersInput>): Promise<LLMParameters> {
    validateUserId(userId);
    if (!parameterId || typeof parameterId !== 'string' || parameterId.trim().length === 0) {
      throw new Error('Invalid parameter ID: parameterId must be a non-empty string');
    }
    return handleApiCall(async () => {
      const response = await axios.put(`${API_BASE}/${userId}/llm-parameters/${parameterId}`, parameters);
      return response.data;
    });
  },

  /**
   * Delete LLM parameters
   */
  async delete(userId: string, parameterId: string): Promise<boolean> {
    validateUserId(userId);
    if (!parameterId || typeof parameterId !== 'string' || parameterId.trim().length === 0) {
      throw new Error('Invalid parameter ID: parameterId must be a non-empty string');
    }
    return handleApiCall(async () => {
      const response = await axios.delete(`${API_BASE}/${userId}/llm-parameters/${parameterId}`);
      return response.data;
    });
  },

  /**
   * Set parameters as default
   */
  async setDefault(userId: string, parameterId: string): Promise<LLMParameters> {
    validateUserId(userId);
    if (!parameterId || typeof parameterId !== 'string' || parameterId.trim().length === 0) {
      throw new Error('Invalid parameter ID: parameterId must be a non-empty string');
    }
    return handleApiCall(async () => {
      const response = await axios.put(`${API_BASE}/${userId}/llm-parameters/${parameterId}/default`);
      return response.data;
    });
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
    validateUserId(userId);
    return handleApiCall(async () => {
      const response = await axios.get(`${API_BASE}/${userId}/pipelines`);
      return response.data;
    });
  },

  /**
   * Create a new pipeline configuration
   */
  async create(userId: string, config: PipelineConfigInput): Promise<PipelineConfig> {
    validateUserId(userId);
    if (!config.name) {
      throw new Error('Pipeline name is required');
    }
    return handleApiCall(async () => {
      const response = await axios.post(`${API_BASE}/${userId}/pipelines`, config);
      return response.data;
    });
  },

  /**
   * Update an existing pipeline configuration
   */
  async update(userId: string, pipelineId: string, config: Partial<PipelineConfigInput>): Promise<PipelineConfig> {
    validateUserId(userId);
    if (!pipelineId || typeof pipelineId !== 'string' || pipelineId.trim().length === 0) {
      throw new Error('Invalid pipeline ID: pipelineId must be a non-empty string');
    }
    return handleApiCall(async () => {
      const response = await axios.put(`${API_BASE}/${userId}/pipelines/${pipelineId}`, config);
      return response.data;
    });
  },

  /**
   * Delete a pipeline configuration
   */
  async delete(userId: string, pipelineId: string): Promise<boolean> {
    validateUserId(userId);
    if (!pipelineId || typeof pipelineId !== 'string' || pipelineId.trim().length === 0) {
      throw new Error('Invalid pipeline ID: pipelineId must be a non-empty string');
    }
    return handleApiCall(async () => {
      const response = await axios.delete(`${API_BASE}/${userId}/pipelines/${pipelineId}`);
      return response.data;
    });
  },

  /**
   * Set pipeline as default
   */
  async setDefault(userId: string, pipelineId: string): Promise<PipelineConfig> {
    validateUserId(userId);
    if (!pipelineId || typeof pipelineId !== 'string' || pipelineId.trim().length === 0) {
      throw new Error('Invalid pipeline ID: pipelineId must be a non-empty string');
    }
    return handleApiCall(async () => {
      const response = await axios.put(`${API_BASE}/${userId}/pipelines/${pipelineId}/default`);
      return response.data;
    });
  },
};
