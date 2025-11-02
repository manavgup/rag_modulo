/**
 * Settings API client for accessing application configuration.
 *
 * These settings come from .env and require application restart to change.
 * For runtime-changeable configuration, use runtimeConfigApi instead.
 */

import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

export interface LLMSettings {
  max_new_tokens: number;
  min_new_tokens: number;
  temperature: number;
  top_k: number;
  top_p: number;
  repetition_penalty: number;
  llm_provider: string;
  rag_llm: string;
}

export interface ChunkingSettings {
  chunking_strategy: string;
  min_chunk_size: number;
  max_chunk_size: number;
  chunk_overlap: number;
  semantic_threshold: number;
}

export interface RetrievalSettings {
  retrieval_type: string;
  number_of_results: number;
  vector_weight: number;
  keyword_weight: number;
  enable_reranking: boolean;
  reranker_type: string;
  reranker_top_k: number | null;
}

export interface EmbeddingSettings {
  embedding_model: string;
  embedding_dim: number;
  embedding_batch_size: number;
  embedding_concurrency_limit: number;
}

export interface CoTSettings {
  cot_max_reasoning_depth: number;
  cot_reasoning_strategy: string;
  cot_token_budget_multiplier: number;
}

export interface SystemSettings {
  llm: LLMSettings;
  chunking: ChunkingSettings;
  retrieval: RetrievalSettings;
  embedding: EmbeddingSettings;
  cot: CoTSettings;
  vector_db: string;
  log_level: string;
}

/**
 * Get current system settings from .env configuration.
 *
 * Note: These settings are read-only via API. Changes require updating
 * .env file and restarting the application.
 */
export const getSystemSettings = async (): Promise<SystemSettings> => {
  const response = await axios.get<SystemSettings>(`${API_BASE_URL}/settings`);
  return response.data;
};

export const settingsApi = {
  getSystemSettings,
};
