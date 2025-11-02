/**
 * RuntimeConfig API client for operational overrides and feature flags.
 *
 * These configurations can be changed at runtime without application restart.
 * Use for feature flags, emergency overrides, A/B testing, and performance tuning.
 */

import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

export type ConfigScope = 'GLOBAL' | 'USER' | 'COLLECTION';
export type ConfigCategory = 'SYSTEM' | 'OVERRIDE' | 'EXPERIMENT' | 'PERFORMANCE' | 'LLM' | 'CHUNKING' | 'RETRIEVAL' | 'EMBEDDING' | 'PIPELINE';
export type ConfigValueType = 'int' | 'float' | 'str' | 'bool' | 'list' | 'dict';

export interface ConfigValue {
  value: any;
  type: ConfigValueType;
}

export interface RuntimeConfigInput {
  scope: ConfigScope;
  category: ConfigCategory;
  config_key: string;
  config_value: ConfigValue;
  user_id?: string;
  collection_id?: string;
  description?: string;
}

export interface RuntimeConfigOutput extends RuntimeConfigInput {
  id: string;
  is_active: boolean;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface EffectiveConfigResponse {
  config_key: string;
  config_value: ConfigValue;
  source_scope: ConfigScope;
  source_id?: string;
  is_active: boolean;
}

/**
 * Create a new runtime configuration override.
 */
export const createConfig = async (input: RuntimeConfigInput): Promise<RuntimeConfigOutput> => {
  const response = await axios.post<RuntimeConfigOutput>(`${API_BASE_URL}/runtime-config`, input);
  return response.data;
};

/**
 * Get a single runtime configuration by ID.
 */
export const getConfig = async (id: string): Promise<RuntimeConfigOutput> => {
  const response = await axios.get<RuntimeConfigOutput>(`${API_BASE_URL}/runtime-config/${id}`);
  return response.data;
};

/**
 * List global runtime configurations.
 */
export const listGlobalConfigs = async (category?: ConfigCategory): Promise<RuntimeConfigOutput[]> => {
  const params = category ? { category } : {};
  const response = await axios.get<RuntimeConfigOutput[]>(`${API_BASE_URL}/runtime-config/global`, { params });
  return response.data;
};

/**
 * List user-specific runtime configurations.
 */
export const listUserConfigs = async (userId: string, category?: ConfigCategory): Promise<RuntimeConfigOutput[]> => {
  const params = category ? { category } : {};
  const response = await axios.get<RuntimeConfigOutput[]>(`${API_BASE_URL}/runtime-config/user/${userId}`, { params });
  return response.data;
};

/**
 * List collection-specific runtime configurations.
 */
export const listCollectionConfigs = async (collectionId: string, category?: ConfigCategory): Promise<RuntimeConfigOutput[]> => {
  const params = category ? { category } : {};
  const response = await axios.get<RuntimeConfigOutput[]>(`${API_BASE_URL}/runtime-config/collection/${collectionId}`, { params });
  return response.data;
};

/**
 * Get effective configuration with hierarchical precedence.
 */
export const getEffectiveConfig = async (
  category: ConfigCategory,
  userId: string,
  collectionId?: string
): Promise<EffectiveConfigResponse[]> => {
  const params: any = { category, user_id: userId };
  if (collectionId) {
    params.collection_id = collectionId;
  }
  const response = await axios.get<EffectiveConfigResponse[]>(`${API_BASE_URL}/runtime-config/effective`, { params });
  return response.data;
};

/**
 * Update a runtime configuration.
 */
export const updateConfig = async (id: string, data: Partial<RuntimeConfigInput>): Promise<RuntimeConfigOutput> => {
  const response = await axios.put<RuntimeConfigOutput>(`${API_BASE_URL}/runtime-config/${id}`, data);
  return response.data;
};

/**
 * Toggle active status of a runtime configuration.
 */
export const toggleConfig = async (id: string, isActive: boolean): Promise<RuntimeConfigOutput> => {
  const response = await axios.patch<RuntimeConfigOutput>(`${API_BASE_URL}/runtime-config/${id}/toggle`, { is_active: isActive });
  return response.data;
};

/**
 * Delete a runtime configuration.
 */
export const deleteConfig = async (id: string): Promise<void> => {
  await axios.delete(`${API_BASE_URL}/runtime-config/${id}`);
};

export const runtimeConfigApi = {
  createConfig,
  getConfig,
  listGlobalConfigs,
  listUserConfigs,
  listCollectionConfigs,
  getEffectiveConfig,
  updateConfig,
  toggleConfig,
  deleteConfig,
};
