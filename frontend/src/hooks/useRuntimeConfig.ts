/**
 * React Query hooks for RuntimeConfig API.
 *
 * These hooks provide access to operational overrides and feature flags.
 * Changes take effect immediately without application restart.
 */

import { useQuery, useMutation, useQueryClient, UseQueryResult, UseMutationResult } from '@tanstack/react-query';
import {
  runtimeConfigApi,
  RuntimeConfigInput,
  RuntimeConfigOutput,
  EffectiveConfigResponse,
  ConfigCategory,
  ConfigScope,
} from '../api/runtimeConfigApi';

const QUERY_KEYS = {
  configs: ['runtime-configs'] as const,
  global: (category?: ConfigCategory) => ['runtime-configs', 'global', category] as const,
  user: (userId: string, category?: ConfigCategory) => ['runtime-configs', 'user', userId, category] as const,
  collection: (collectionId: string, category?: ConfigCategory) => ['runtime-configs', 'collection', collectionId, category] as const,
  effective: (category: ConfigCategory, userId: string, collectionId?: string) =>
    ['runtime-configs', 'effective', category, userId, collectionId] as const,
  single: (id: string) => ['runtime-configs', id] as const,
};

/**
 * Hook to fetch global runtime configurations.
 */
export const useGlobalConfigs = (category?: ConfigCategory): UseQueryResult<RuntimeConfigOutput[], Error> => {
  return useQuery({
    queryKey: QUERY_KEYS.global(category),
    queryFn: () => runtimeConfigApi.listGlobalConfigs(category),
    staleTime: 30 * 1000, // 30 seconds (fresher than Settings)
  });
};

/**
 * Hook to fetch user-specific runtime configurations.
 */
export const useUserConfigs = (
  userId: string,
  category?: ConfigCategory
): UseQueryResult<RuntimeConfigOutput[], Error> => {
  return useQuery({
    queryKey: QUERY_KEYS.user(userId, category),
    queryFn: () => runtimeConfigApi.listUserConfigs(userId, category),
    enabled: !!userId,
    staleTime: 30 * 1000,
  });
};

/**
 * Hook to fetch collection-specific runtime configurations.
 */
export const useCollectionConfigs = (
  collectionId: string,
  category?: ConfigCategory
): UseQueryResult<RuntimeConfigOutput[], Error> => {
  return useQuery({
    queryKey: QUERY_KEYS.collection(collectionId, category),
    queryFn: () => runtimeConfigApi.listCollectionConfigs(collectionId, category),
    enabled: !!collectionId,
    staleTime: 30 * 1000,
  });
};

/**
 * Hook to fetch a single runtime configuration by ID.
 */
export const useRuntimeConfig = (id: string): UseQueryResult<RuntimeConfigOutput, Error> => {
  return useQuery({
    queryKey: QUERY_KEYS.single(id),
    queryFn: () => runtimeConfigApi.getConfig(id),
    enabled: !!id,
    staleTime: 30 * 1000,
  });
};

/**
 * Hook to fetch effective configuration with precedence.
 */
export const useEffectiveConfig = (
  category: ConfigCategory,
  userId: string,
  collectionId?: string
): UseQueryResult<EffectiveConfigResponse[], Error> => {
  return useQuery({
    queryKey: QUERY_KEYS.effective(category, userId, collectionId),
    queryFn: () => runtimeConfigApi.getEffectiveConfig(category, userId, collectionId),
    enabled: !!category && !!userId,
    staleTime: 30 * 1000,
  });
};

/**
 * Hook to create a new runtime configuration.
 */
export const useCreateConfig = (): UseMutationResult<RuntimeConfigOutput, Error, RuntimeConfigInput> => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: runtimeConfigApi.createConfig,
    onSuccess: (data) => {
      // Invalidate all configs
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.configs });

      // Invalidate scope-specific queries
      if (data.scope === 'GLOBAL') {
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.global(data.category) });
      } else if (data.scope === 'USER' && data.user_id) {
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.user(data.user_id, data.category) });
      } else if (data.scope === 'COLLECTION' && data.collection_id) {
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.collection(data.collection_id, data.category) });
      }
    },
  });
};

/**
 * Hook to update an existing runtime configuration.
 */
export const useUpdateConfig = (): UseMutationResult<
  RuntimeConfigOutput,
  Error,
  { id: string; data: Partial<RuntimeConfigInput> }
> => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) => runtimeConfigApi.updateConfig(id, data),
    onSuccess: (_, variables) => {
      // Invalidate specific config
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.single(variables.id) });

      // Invalidate all configs
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.configs });
    },
  });
};

/**
 * Hook to toggle active status of a runtime configuration.
 */
export const useToggleConfig = (): UseMutationResult<
  RuntimeConfigOutput,
  Error,
  { id: string; isActive: boolean }
> => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, isActive }) => runtimeConfigApi.toggleConfig(id, isActive),
    onSuccess: (data, variables) => {
      // Update specific config in cache
      queryClient.setQueryData(QUERY_KEYS.single(variables.id), data);

      // Invalidate all configs
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.configs });
    },
  });
};

/**
 * Hook to delete a runtime configuration.
 */
export const useDeleteConfig = (): UseMutationResult<void, Error, string> => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: runtimeConfigApi.deleteConfig,
    onSuccess: () => {
      // Invalidate all configs
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.configs });
    },
  });
};

/**
 * Hook to get configs by scope with proper typing.
 */
export const useConfigsByScope = (
  scope: ConfigScope,
  userId?: string,
  collectionId?: string,
  category?: ConfigCategory
): UseQueryResult<RuntimeConfigOutput[], Error> => {
  // Always call all hooks (Rules of Hooks)
  const globalQuery = useGlobalConfigs(category);
  const userQuery = useUserConfigs(userId || '', category);
  const collectionQuery = useCollectionConfigs(collectionId || '', category);

  // Create empty query as fallback
  const emptyQuery = useQuery({
    queryKey: ['runtime-configs', 'empty'],
    queryFn: async () => [] as RuntimeConfigOutput[],
    enabled: false,
  });

  // Return appropriate query based on scope
  if (scope === 'GLOBAL') return globalQuery;
  if (scope === 'USER' && userId) return userQuery;
  if (scope === 'COLLECTION' && collectionId) return collectionQuery;

  // Return empty result for invalid scope/params
  return emptyQuery;
};
