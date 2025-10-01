import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  MagnifyingGlassIcon,
  DocumentIcon,
  UserIcon,
  CogIcon,
  ChartBarIcon,
  PlayIcon,
  PauseIcon,
  CheckIcon,
  XMarkIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  ClockIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '../../contexts/AuthContext';
import { useNotification } from '../../contexts/NotificationContext';
import apiClient from '../../services/apiClient';

interface DashboardStats {
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
}

interface RecentActivity {
  id: string;
  type: 'search' | 'workflow' | 'agent' | 'document';
  title: string;
  description: string;
  timestamp: Date;
  status: 'success' | 'error' | 'pending' | 'running';
}

interface QuickStat {
  metric: string;
  value: string;
  change: string;
  trend: 'up' | 'down';
}

interface QuickStatistics {
  documentsProcessedToday: QuickStat;
  searchQueries: QuickStat;
  agentTasksCompleted: QuickStat;
  averageProcessingTime: QuickStat;
  errorRate: QuickStat;
}

interface SystemHealth {
  component: string;
  healthPercentage: number;
}

interface SystemHealthStatus {
  overallStatus: string;
  components: SystemHealth[];
}

const LightweightDashboard: React.FC = () => {
  const { user } = useAuth();
  const { addNotification } = useNotification();
  const navigate = useNavigate();

  const [isLoading, setIsLoading] = useState(true);
  const [stats, setStats] = useState<DashboardStats>({
    totalDocuments: 0,
    totalSearches: 0,
    activeAgents: 0,
    completedWorkflows: 0,
    successRate: 0,
    averageResponseTime: 0,
    documentsTrend: { value: 0, period: '', direction: 'up' },
    searchesTrend: { value: 0, period: '', direction: 'up' },
    successRateTrend: { value: 0, period: '', direction: 'up' },
    responseTimeTrend: { value: 0, period: '', direction: 'up' },
    workflowsTrend: { value: 0, period: '', direction: 'up' },
  });
  const [recentActivity, setRecentActivity] = useState<RecentActivity[]>([]);
  const [quickStats, setQuickStats] = useState<QuickStatistics | null>(null);
  const [systemHealth, setSystemHealth] = useState<SystemHealthStatus | null>(null);

  useEffect(() => {
    const loadDashboardData = async () => {
      setIsLoading(true);
      try {
        // Load all dashboard data from API
        const [statsData, activityData, quickStatsData, systemHealthData] = await Promise.all([
          apiClient.getDashboardStats(),
          apiClient.getRecentActivity(),
          apiClient.getQuickStatistics(),
          apiClient.getSystemHealth()
        ]);

        setStats(statsData);

        // Convert timestamp strings to Date objects
        const formattedActivity: RecentActivity[] = activityData.map(item => ({
          ...item,
          timestamp: new Date(item.timestamp)
        }));
        setRecentActivity(formattedActivity);

        setQuickStats(quickStatsData);
        setSystemHealth(systemHealthData);

        addNotification('success', 'Dashboard Loaded', 'Dashboard data loaded successfully from API.');

      } catch (error) {
        console.error('Error loading dashboard data:', error);
        addNotification('error', 'Loading Error', 'Failed to load dashboard data. Using fallback data.');

        // Fallback to mock data if API fails
        setStats({
          totalDocuments: 0,
          totalSearches: 0,
          activeAgents: 0,
          completedWorkflows: 0,
          successRate: 0,
          averageResponseTime: 0,
          documentsTrend: { value: 0, period: '', direction: 'up' },
          searchesTrend: { value: 0, period: '', direction: 'up' },
          successRateTrend: { value: 0, period: '', direction: 'up' },
          responseTimeTrend: { value: 0, period: '', direction: 'up' },
          workflowsTrend: { value: 0, period: '', direction: 'up' },
        });
        setRecentActivity([]);
        setQuickStats(null);
        setSystemHealth(null);
      } finally {
        setIsLoading(false);
      }
    };

    loadDashboardData();
  }, []);

  const quickActions = [
    {
      id: 'search',
      title: 'Chat with Collections',
      description: 'Chat with your document collections',
      icon: MagnifyingGlassIcon,
      href: '/search',
      color: 'blue',
    },
    {
      id: 'workflows',
      title: 'Workflow Designer',
      description: 'Create and manage workflows',
      icon: CogIcon,
      href: '/workflows',
      color: 'purple',
    },
    {
      id: 'documents',
      title: 'Collections',
      description: 'Manage your document collections',
      icon: DocumentIcon,
      href: '/collections',
      color: 'green',
    },
    {
      id: 'agents',
      title: 'Agent Orchestration',
      description: 'Manage AI agents',
      icon: UserIcon,
      href: '/agents',
      color: 'orange',
    },
    {
      id: 'analytics',
      title: 'Analytics',
      description: 'View usage and performance',
      icon: ChartBarIcon,
      href: '/analytics',
      color: 'teal',
    },
  ];

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckIcon className="w-4 h-4 text-green-50" />;
      case 'error':
        return <XMarkIcon className="w-4 h-4 text-red-50" />;
      case 'running':
        return <PlayIcon className="w-4 h-4 text-blue-60" />;
      case 'pending':
        return <PauseIcon className="w-4 h-4 text-yellow-30" />;
      default:
        return null;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'bg-green-50 text-white';
      case 'error':
        return 'bg-red-50 text-white';
      case 'running':
        return 'bg-blue-60 text-white';
      case 'pending':
        return 'bg-yellow-30 text-gray-100';
      default:
        return 'bg-gray-50 text-white';
    }
  };

  const formatTimeAgo = (date: Date) => {
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));

    if (diffInMinutes < 1) return 'Just now';
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
    if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}h ago`;
    return `${Math.floor(diffInMinutes / 1440)}d ago`;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-60 mx-auto mb-4"></div>
          <p className="text-gray-70">Loading dashboard...</p>
          <p className="text-sm text-gray-50 mt-2">Preparing your workspace...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-10 p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-semibold text-gray-100 mb-2">
          Welcome back, {user?.username}!
        </h1>
        <p className="text-gray-70">Your intelligent document processing workspace</p>
      </div>

      <div className="space-y-8">
        {/* Quick Actions */}
        <div className="card">
          <div className="p-6">
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-gray-100 mb-2">Quick Actions</h2>
              <p className="text-gray-70">Access your most used features</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
              {quickActions.map((action) => (
                <button
                  key={action.id}
                  onClick={() => navigate(action.href)}
                  className="card p-4 hover:border-blue-60 transition-all duration-200 text-left group"
                >
                  <div className="flex items-center space-x-3">
                    <div className="p-2 rounded-lg bg-gray-10 group-hover:bg-blue-60 group-hover:text-white transition-colors duration-200">
                      <action.icon className="w-6 h-6" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-gray-100 text-sm">{action.title}</h3>
                      <p className="text-xs text-gray-70 truncate">{action.description}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Stats Overview */}
          <div className="card">
            <div className="p-6">
              <div className="mb-6">
                <h2 className="text-xl font-semibold text-gray-100 mb-2">System Overview</h2>
                <p className="text-gray-70">Current system status and metrics</p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="card p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-medium text-gray-100">Total Documents</h3>
                    <DocumentIcon className="w-6 h-6 text-gray-60" />
                  </div>
                  <div className="space-y-2">
                    <div className="text-2xl font-semibold text-gray-100">
                      {(stats?.totalDocuments ?? 0).toLocaleString()}
                    </div>
                    <div className={`flex items-center text-sm ${
                      stats?.documentsTrend?.direction === 'up' ? 'text-green-50' : 'text-red-50'
                    }`}>
                      {stats?.documentsTrend?.direction === 'up' ? (
                        <ArrowUpIcon className="w-4 h-4 mr-1" />
                      ) : (
                        <ArrowDownIcon className="w-4 h-4 mr-1" />
                      )}
                      {stats?.documentsTrend?.value ? `+${stats.documentsTrend.value.toFixed(1)}% ${stats.documentsTrend.period}` : '+0% this month'}
                    </div>
                  </div>
                </div>

                <div className="card p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-medium text-gray-100">Total Searches</h3>
                    <MagnifyingGlassIcon className="w-6 h-6 text-gray-60" />
                  </div>
                  <div className="space-y-2">
                    <div className="text-2xl font-semibold text-gray-100">
                      {(stats?.totalSearches ?? 0).toLocaleString()}
                    </div>
                    <div className={`flex items-center text-sm ${
                      stats?.searchesTrend?.direction === 'up' ? 'text-green-50' : 'text-red-50'
                    }`}>
                      {stats?.searchesTrend?.direction === 'up' ? (
                        <ArrowUpIcon className="w-4 h-4 mr-1" />
                      ) : (
                        <ArrowDownIcon className="w-4 h-4 mr-1" />
                      )}
                      {stats?.searchesTrend?.value ? `+${stats.searchesTrend.value.toFixed(1)}% ${stats.searchesTrend.period}` : '+0% this week'}
                    </div>
                  </div>
                </div>

                <div className="card p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-medium text-gray-100">Active Agents</h3>
                    <UserIcon className="w-6 h-6 text-gray-60" />
                  </div>
                  <div className="space-y-2">
                    <div className="text-2xl font-semibold text-gray-100">{stats?.activeAgents ?? 0}</div>
                    <div className="text-sm text-gray-60">
                      {(stats?.activeAgents ?? 0) > 0 ? 'Running' : 'Idle'}
                    </div>
                  </div>
                </div>

                <div className="card p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-medium text-gray-100">Success Rate</h3>
                    <CheckIcon className="w-6 h-6 text-gray-60" />
                  </div>
                  <div className="space-y-2">
                    <div className="text-2xl font-semibold text-gray-100">
                      {((stats?.successRate ?? 0) * 100).toFixed(1)}%
                    </div>
                    <div className={`flex items-center text-sm ${
                      stats?.successRateTrend?.direction === 'up' ? 'text-green-50' : 'text-red-50'
                    }`}>
                      {stats?.successRateTrend?.direction === 'up' ? (
                        <ArrowUpIcon className="w-4 h-4 mr-1" />
                      ) : (
                        <ArrowDownIcon className="w-4 h-4 mr-1" />
                      )}
                      {stats?.successRateTrend?.value ? `+${stats.successRateTrend.value.toFixed(1)}% ${stats.successRateTrend.period}` : '+0% improvement'}
                    </div>
                  </div>
                </div>

                <div className="card p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-medium text-gray-100">Avg Response Time</h3>
                    <ClockIcon className="w-6 h-6 text-gray-60" />
                  </div>
                  <div className="space-y-2">
                    <div className="text-2xl font-semibold text-gray-100">
                      {stats?.averageResponseTime ?? 0}s
                    </div>
                    <div className={`flex items-center text-sm ${
                      stats?.responseTimeTrend?.direction === 'down' ? 'text-green-50' : 'text-red-50'
                    }`}>
                      {stats?.responseTimeTrend?.direction === 'down' ? (
                        <ArrowDownIcon className="w-4 h-4 mr-1" />
                      ) : (
                        <ArrowUpIcon className="w-4 h-4 mr-1" />
                      )}
                      {stats?.responseTimeTrend?.value ? `-${stats.responseTimeTrend.value.toFixed(1)}% ${stats.responseTimeTrend.period}` : '-0% faster'}
                    </div>
                  </div>
                </div>

                <div className="card p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-medium text-gray-100">Completed Workflows</h3>
                    <CogIcon className="w-6 h-6 text-gray-60" />
                  </div>
                  <div className="space-y-2">
                    <div className="text-2xl font-semibold text-gray-100">
                      {stats?.completedWorkflows ?? 0}
                    </div>
                    <div className={`flex items-center text-sm ${
                      stats?.workflowsTrend?.direction === 'up' ? 'text-green-50' : 'text-red-50'
                    }`}>
                      {stats?.workflowsTrend?.direction === 'up' ? (
                        <ArrowUpIcon className="w-4 h-4 mr-1" />
                      ) : (
                        <ArrowDownIcon className="w-4 h-4 mr-1" />
                      )}
                      {stats?.workflowsTrend?.value ? `+${stats.workflowsTrend.value.toFixed(0)} ${stats.workflowsTrend.period}` : '+0 this week'}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Recent Activity */}
          <div className="space-y-8">
            <div className="card">
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-xl font-semibold text-gray-100 mb-2">Recent Activity</h2>
                  </div>
                  <button
                    onClick={() => addNotification('info', 'Refreshed', 'Activity refreshed')}
                    className="btn-ghost flex items-center space-x-2"
                  >
                    <ArrowPathIcon className="w-4 h-4" />
                    <span>Refresh</span>
                  </button>
                </div>
                <div className="space-y-4">
                  {recentActivity.map((activity) => (
                    <div key={activity.id} className="flex items-center justify-between p-3 border border-gray-20 rounded-lg">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3">
                          <div className="flex-1">
                            <h4 className="font-medium text-gray-100 text-sm">{activity.title}</h4>
                            <p className="text-xs text-gray-70">{activity.description}</p>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-3">
                        <div className="flex items-center space-x-2">
                          {getStatusIcon(activity.status)}
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(activity.status)}`}>
                            {activity.status}
                          </span>
                        </div>
                        <span className="text-xs text-gray-70 min-w-0">
                          {activity.timestamp ? formatTimeAgo(activity.timestamp) : 'N/A'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* System Status */}
            <div className="card">
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold text-gray-100">System Status</h2>
                  <div className="flex items-center space-x-2 text-green-50">
                    <CheckIcon className="w-4 h-4" />
                    <span className="text-sm font-medium">{systemHealth?.overallStatus || 'All Systems Operational'}</span>
                  </div>
                </div>
                <div className="space-y-4">
                  {(systemHealth?.components || [
                    { component: 'API Health', healthPercentage: 100 },
                    { component: 'Database', healthPercentage: 95 },
                    { component: 'Storage', healthPercentage: 78 },
                    { component: 'Memory', healthPercentage: 65 },
                  ]).map((status) => (
                    <div key={status.component} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-100">{status.component}</span>
                        <span className="text-sm text-gray-70">{status.healthPercentage}%</span>
                      </div>
                      <div className="w-full bg-gray-20 rounded-full h-2">
                        <div
                          className="bg-blue-60 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${status.healthPercentage}%` }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Stats Table */}
        <div className="card">
          <div className="p-6">
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-gray-100 mb-2">Quick Statistics</h2>
              <p className="text-gray-70">Detailed metrics and performance data</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-10">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-100">Metric</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-100">Value</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-100">Change</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-100">Trend</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-20">
                  {(quickStats ? [
                    quickStats.documentsProcessedToday,
                    quickStats.searchQueries,
                    quickStats.agentTasksCompleted,
                    quickStats.averageProcessingTime,
                    quickStats.errorRate,
                  ].filter(stat => stat && stat.metric) : [
                    { metric: 'Documents Processed Today', value: '0', change: '+0%', trend: 'up' as const },
                    { metric: 'Search Queries', value: '0', change: '+0%', trend: 'up' as const },
                    { metric: 'Agent Tasks Completed', value: '0', change: '+0%', trend: 'up' as const },
                    { metric: 'Average Processing Time', value: '0.0s', change: '+0%', trend: 'up' as const },
                    { metric: 'Error Rate', value: '0.0%', change: '+0%', trend: 'up' as const },
                  ]).filter(row => row && typeof row === 'object').map((row, index) => (
                    <tr key={index} className="hover:bg-gray-10">
                      <td className="px-4 py-3 text-sm text-gray-100">{row.metric}</td>
                      <td className="px-4 py-3 text-sm font-medium text-gray-100">{row.value}</td>
                      <td className="px-4 py-3">
                        <div className={`flex items-center text-sm ${
                          row.change.startsWith('+') ? 'text-green-50' : 'text-red-50'
                        }`}>
                          {row.change.startsWith('+') ? (
                            <ArrowUpIcon className="w-4 h-4 mr-1" />
                          ) : (
                            <ArrowDownIcon className="w-4 h-4 mr-1" />
                          )}
                          {row.change}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className={`flex items-center ${
                          row.trend === 'up' ? 'text-green-50' : 'text-red-50'
                        }`}>
                          {row.trend === 'up' ? (
                            <ArrowUpIcon className="w-4 h-4" />
                          ) : (
                            <ArrowDownIcon className="w-4 h-4" />
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LightweightDashboard;
