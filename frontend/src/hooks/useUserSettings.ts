/**
 * React Query hooks for user settings (Prompt Templates, LLM Parameters, Pipelines)
 */

import { useQuery, useMutation, useQueryClient, UseQueryResult, UseMutationResult } from '@tanstack/react-query';
import {
  promptTemplatesApi,
  llmParametersApi,
  pipelineConfigApi,
  PromptTemplate,
  PromptTemplateInput,
  LLMParameters,
  LLMParametersInput,
  PipelineConfig,
  PipelineConfigInput,
} from '../api/userSettings';

// ============================================================================
// Query Keys
// ============================================================================

export const QUERY_KEYS = {
  promptTemplates: (userId: string) => ['prompt-templates', userId],
  llmParameters: (userId: string) => ['llm-parameters', userId],
  pipelineConfigs: (userId: string) => ['pipeline-configs', userId],
};

// ============================================================================
// Prompt Templates Hooks
// ============================================================================

/**
 * Hook to fetch all prompt templates for a user
 */
export function usePromptTemplates(userId: string): UseQueryResult<PromptTemplate[], Error> {
  return useQuery({
    queryKey: QUERY_KEYS.promptTemplates(userId),
    queryFn: () => promptTemplatesApi.getAll(userId),
    enabled: !!userId,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
  });
}

/**
 * Hook to create a new prompt template
 */
export function useCreatePromptTemplate(userId: string): UseMutationResult<PromptTemplate, Error, PromptTemplateInput> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (template: PromptTemplateInput) => promptTemplatesApi.create(userId, template),
    onSuccess: () => {
      // Invalidate and refetch prompt templates
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.promptTemplates(userId) });
    },
  });
}

/**
 * Hook to update a prompt template
 */
export function useUpdatePromptTemplate(userId: string): UseMutationResult<
  PromptTemplate,
  Error,
  { templateId: string; template: Partial<PromptTemplateInput> }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ templateId, template }) => promptTemplatesApi.update(userId, templateId, template),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.promptTemplates(userId) });
    },
  });
}

/**
 * Hook to delete a prompt template
 */
export function useDeletePromptTemplate(userId: string): UseMutationResult<boolean, Error, string> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (templateId: string) => promptTemplatesApi.delete(userId, templateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.promptTemplates(userId) });
    },
  });
}

/**
 * Hook to set a template as default
 */
export function useSetDefaultPromptTemplate(userId: string): UseMutationResult<PromptTemplate, Error, string> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (templateId: string) => promptTemplatesApi.setDefault(userId, templateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.promptTemplates(userId) });
    },
  });
}

// ============================================================================
// LLM Parameters Hooks
// ============================================================================

/**
 * Hook to fetch all LLM parameters for a user
 */
export function useLLMParameters(userId: string): UseQueryResult<LLMParameters[], Error> {
  return useQuery({
    queryKey: QUERY_KEYS.llmParameters(userId),
    queryFn: () => llmParametersApi.getAll(userId),
    enabled: !!userId,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
}

/**
 * Hook to create new LLM parameters
 */
export function useCreateLLMParameters(userId: string): UseMutationResult<LLMParameters, Error, LLMParametersInput> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (parameters: LLMParametersInput) => llmParametersApi.create(userId, parameters),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.llmParameters(userId) });
    },
  });
}

/**
 * Hook to update LLM parameters
 */
export function useUpdateLLMParameters(userId: string): UseMutationResult<
  LLMParameters,
  Error,
  { parameterId: string; parameters: Partial<LLMParametersInput> }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ parameterId, parameters }) => llmParametersApi.update(userId, parameterId, parameters),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.llmParameters(userId) });
    },
  });
}

/**
 * Hook to delete LLM parameters
 */
export function useDeleteLLMParameters(userId: string): UseMutationResult<boolean, Error, string> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (parameterId: string) => llmParametersApi.delete(userId, parameterId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.llmParameters(userId) });
    },
  });
}

/**
 * Hook to set LLM parameters as default
 */
export function useSetDefaultLLMParameters(userId: string): UseMutationResult<LLMParameters, Error, string> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (parameterId: string) => llmParametersApi.setDefault(userId, parameterId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.llmParameters(userId) });
    },
  });
}

// ============================================================================
// Pipeline Configuration Hooks
// ============================================================================

/**
 * Hook to fetch all pipeline configurations for a user
 */
export function usePipelineConfigs(userId: string): UseQueryResult<PipelineConfig[], Error> {
  return useQuery({
    queryKey: QUERY_KEYS.pipelineConfigs(userId),
    queryFn: () => pipelineConfigApi.getAll(userId),
    enabled: !!userId,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
}

/**
 * Hook to create a new pipeline configuration
 */
export function useCreatePipelineConfig(userId: string): UseMutationResult<PipelineConfig, Error, PipelineConfigInput> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (config: PipelineConfigInput) => pipelineConfigApi.create(userId, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.pipelineConfigs(userId) });
    },
  });
}

/**
 * Hook to update a pipeline configuration
 */
export function useUpdatePipelineConfig(userId: string): UseMutationResult<
  PipelineConfig,
  Error,
  { pipelineId: string; config: Partial<PipelineConfigInput> }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ pipelineId, config }) => pipelineConfigApi.update(userId, pipelineId, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.pipelineConfigs(userId) });
    },
  });
}

/**
 * Hook to delete a pipeline configuration
 */
export function useDeletePipelineConfig(userId: string): UseMutationResult<boolean, Error, string> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (pipelineId: string) => pipelineConfigApi.delete(userId, pipelineId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.pipelineConfigs(userId) });
    },
  });
}

/**
 * Hook to set a pipeline as default
 */
export function useSetDefaultPipelineConfig(userId: string): UseMutationResult<PipelineConfig, Error, string> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (pipelineId: string) => pipelineConfigApi.setDefault(userId, pipelineId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.pipelineConfigs(userId) });
    },
  });
}
