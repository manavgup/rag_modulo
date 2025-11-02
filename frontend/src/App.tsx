import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './contexts/AuthContext';
import { NotificationProvider } from './contexts/NotificationContext';
import { AgentProvider } from './contexts/AgentContext';
import { WorkflowProvider } from './contexts/WorkflowContext';
import { WebSocketProvider } from './contexts/WebSocketContext';
import LightweightErrorBoundary from './components/common/LightweightErrorBoundary';

// Lightweight Components Only
import LightweightLayout from './components/layout/LightweightLayout';
import LightweightDashboard from './components/dashboard/LightweightDashboard';
import LightweightCollections from './components/collections/LightweightCollections';
import LightweightCollectionDetail from './components/collections/LightweightCollectionDetail';
import LightweightSearchInterface from './components/search/LightweightSearchInterface';
import LightweightAgentOrchestration from './components/agents/LightweightAgentOrchestration';
import LightweightWorkflowDesigner from './components/workflows/LightweightWorkflowDesigner';
import LightweightUserProfile from './components/profile/LightweightUserProfile';
import LightweightSystemConfiguration from './components/settings/LightweightSystemConfiguration';
import LightweightAnalyticsDashboard from './components/analytics/LightweightAnalyticsDashboard';
import LightweightHelpCenter from './components/help/LightweightHelpCenter';
import LightweightLoginPage from './components/auth/LightweightLoginPage';
import LightweightNotFound from './components/errors/LightweightNotFound';
import LightweightPodcasts from './components/podcasts/LightweightPodcasts';
import LightweightPodcastDetail from './components/podcasts/LightweightPodcastDetail';
import VoiceManagement from './components/podcasts/VoiceManagement';

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

const App: React.FC = () => {
  return (
    <LightweightErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <NotificationProvider>
            <WebSocketProvider>
              <AgentProvider>
                <WorkflowProvider>
                  <div className="lightweight-app">
                    <LightweightLayout>
                      <Routes>
                        {/* Auth Routes */}
                        <Route path="/login" element={<LightweightLoginPage />} />

                        {/* Main Application Routes */}
                        <Route path="/" element={<Navigate to="/dashboard" replace />} />
                        <Route path="/dashboard" element={<LightweightDashboard />} />
                        <Route path="/search" element={<LightweightSearchInterface />} />
                        <Route path="/agents" element={<LightweightAgentOrchestration />} />
                        <Route path="/workflows" element={<LightweightWorkflowDesigner />} />
                        <Route path="/workflows/:id" element={<LightweightWorkflowDesigner />} />

                        {/* Collections Routes */}
                        <Route path="/collections" element={<LightweightCollections />} />
                        <Route path="/collections/:id" element={<LightweightCollectionDetail />} />
                        <Route path="/documents" element={<Navigate to="/collections" replace />} />

                        {/* Podcast Routes */}
                        <Route path="/podcasts" element={<LightweightPodcasts />} />
                        <Route path="/podcasts/:id" element={<LightweightPodcastDetail />} />
                        <Route path="/voices" element={<VoiceManagement />} />

                        {/* Configuration Routes */}
                        <Route path="/configuration" element={<LightweightSystemConfiguration />} />

                        {/* User Routes */}
                        <Route path="/profile" element={<LightweightUserProfile />} />
                        <Route path="/settings" element={<LightweightUserProfile />} />

                        {/* Admin Routes */}
                        <Route path="/admin" element={<LightweightSystemConfiguration />} />
                        <Route path="/analytics" element={<LightweightAnalyticsDashboard />} />

                        {/* Help Routes */}
                        <Route path="/help" element={<LightweightHelpCenter />} />
                        <Route path="/support" element={<LightweightHelpCenter />} />

                        {/* 404 Route */}
                        <Route path="/404" element={<LightweightNotFound />} />
                        <Route path="*" element={<LightweightNotFound />} />
                      </Routes>
                    </LightweightLayout>
                  </div>
                </WorkflowProvider>
              </AgentProvider>
            </WebSocketProvider>
          </NotificationProvider>
        </AuthProvider>
      </QueryClientProvider>
    </LightweightErrorBoundary>
  );
};

export default App;
