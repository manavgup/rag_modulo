/**
 * React Query hooks for Settings API.
 *
 * These hooks provide access to application settings from .env configuration.
 * Settings are cached for 5 minutes and automatically refetched on window focus.
 */

import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { settingsApi, SystemSettings } from '../api/settingsApi';

const QUERY_KEYS = {
  settings: ['settings'] as const,
};

/**
 * Hook to fetch system settings.
 *
 * @example
 * ```tsx
 * const { data: settings, isLoading, error } = useSettings();
 *
 * if (isLoading) return <div>Loading...</div>;
 * if (error) return <div>Error loading settings</div>;
 *
 * return (
 *   <div>
 *     <p>Temperature: {settings.llm.temperature}</p>
 *     <p>Max Tokens: {settings.llm.max_new_tokens}</p>
 *   </div>
 * );
 * ```
 */
export const useSettings = (): UseQueryResult<SystemSettings, Error> => {
  return useQuery({
    queryKey: QUERY_KEYS.settings,
    queryFn: settingsApi.getSystemSettings,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime in React Query v4)
    refetchOnWindowFocus: true,
    refetchOnMount: false,
  });
};
