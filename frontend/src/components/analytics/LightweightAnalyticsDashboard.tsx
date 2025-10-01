import React, { useState, useEffect } from 'react';
import {
  ChartBarIcon,
  DocumentIcon,
  UserGroupIcon,
  ClockIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  CalendarIcon,
  FunnelIcon,
  ArrowPathIcon,
  EyeIcon,
} from '@heroicons/react/24/outline';
import { useNotification } from '../../contexts/NotificationContext';

interface AnalyticsData {
  overview: {
    totalDocuments: number;
    totalCollections: number;
    totalUsers: number;
    totalQueries: number;
    documentsChange: number;
    collectionsChange: number;
    usersChange: number;
    queriesChange: number;
  };
  usage: {
    daily: Array<{
      date: string;
      queries: number;
      uploads: number;
      users: number;
    }>;
    popular: Array<{
      name: string;
      queries: number;
      change: number;
    }>;
  };
  performance: {
    responseTime: {
      avg: number;
      p95: number;
      p99: number;
    };
    successRate: number;
    errorRate: number;
    uptime: number;
  };
  storage: {
    totalSize: number;
    usedSize: number;
    documentsByType: Array<{
      type: string;
      count: number;
      size: number;
    }>;
  };
}

const LightweightAnalyticsDashboard: React.FC = () => {
  const { addNotification } = useNotification();
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [dateRange, setDateRange] = useState('7d');
  const [refreshing, setRefreshing] = useState(false);

  const dateRangeOptions = [
    { value: '24h', label: 'Last 24 Hours' },
    { value: '7d', label: 'Last 7 Days' },
    { value: '30d', label: 'Last 30 Days' },
    { value: '90d', label: 'Last 90 Days' },
  ];

  useEffect(() => {
    loadAnalytics();
  }, [dateRange]);

  const loadAnalytics = async () => {
    setIsLoading(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 1500));

      const mockAnalytics: AnalyticsData = {
        overview: {
          totalDocuments: 1247,
          totalCollections: 23,
          totalUsers: 45,
          totalQueries: 8934,
          documentsChange: 12.5,
          collectionsChange: 8.2,
          usersChange: -2.1,
          queriesChange: 23.7,
        },
        usage: {
          daily: [
            { date: '2024-01-08', queries: 234, uploads: 12, users: 34 },
            { date: '2024-01-09', queries: 298, uploads: 8, users: 41 },
            { date: '2024-01-10', queries: 356, uploads: 15, users: 38 },
            { date: '2024-01-11', queries: 412, uploads: 22, users: 42 },
            { date: '2024-01-12', queries: 389, uploads: 18, users: 45 },
            { date: '2024-01-13', queries: 445, uploads: 9, users: 39 },
            { date: '2024-01-14', queries: 478, uploads: 11, users: 43 },
          ],
          popular: [
            { name: 'Research Papers Collection', queries: 1234, change: 15.2 },
            { name: 'Legal Documents', queries: 856, change: -3.4 },
            { name: 'Technical Manuals', queries: 642, change: 8.7 },
            { name: 'Marketing Materials', queries: 423, change: 12.1 },
            { name: 'Internal Documentation', queries: 298, change: -1.2 },
          ],
        },
        performance: {
          responseTime: {
            avg: 245,
            p95: 832,
            p99: 1247,
          },
          successRate: 98.7,
          errorRate: 1.3,
          uptime: 99.8,
        },
        storage: {
          totalSize: 500000000000, // 500GB
          usedSize: 347500000000, // 347.5GB
          documentsByType: [
            { type: 'PDF', count: 734, size: 234000000000 },
            { type: 'DOCX', count: 342, size: 89000000000 },
            { type: 'TXT', count: 156, size: 18500000000 },
            { type: 'MD', count: 89, size: 6000000000 },
          ],
        },
      };

      setAnalytics(mockAnalytics);
    } catch (error) {
      addNotification('error', 'Loading Error', 'Failed to load analytics data.');
    } finally {
      setIsLoading(false);
    }
  };

  const refreshData = async () => {
    setRefreshing(true);
    await loadAnalytics();
    setRefreshing(false);
    addNotification('success', 'Data Refreshed', 'Analytics data has been updated.');
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  };

  const getChangeIcon = (change: number) => {
    if (change > 0) {
      return <ArrowUpIcon className="w-4 h-4 text-green-50" />;
    } else if (change < 0) {
      return <ArrowDownIcon className="w-4 h-4 text-red-50" />;
    }
    return null;
  };

  const getChangeColor = (change: number) => {
    if (change > 0) return 'text-green-50';
    if (change < 0) return 'text-red-50';
    return 'text-gray-60';
  };

  if (isLoading && !analytics) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-60 mx-auto mb-4"></div>
          <p className="text-gray-70">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="min-h-screen bg-gray-10 p-6">
        <div className="max-w-6xl mx-auto text-center">
          <h1 className="text-2xl font-semibold text-gray-100 mb-4">Analytics Not Available</h1>
          <button onClick={loadAnalytics} className="btn-primary">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-10 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-gray-100">Analytics Dashboard</h1>
            <p className="text-gray-70">System performance and usage insights</p>
          </div>
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2">
              <FunnelIcon className="w-4 h-4 text-gray-60" />
              <select
                value={dateRange}
                onChange={(e) => setDateRange(e.target.value)}
                className="input-field w-40"
              >
                {dateRangeOptions.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={refreshData}
              disabled={refreshing}
              className="btn-secondary flex items-center space-x-2 disabled:opacity-50"
            >
              <ArrowPathIcon className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Overview Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="card p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-70 mb-1">Total Documents</p>
                <p className="text-2xl font-semibold text-gray-100">
                  {formatNumber(analytics.overview.totalDocuments)}
                </p>
                <div className="flex items-center space-x-1 mt-1">
                  {getChangeIcon(analytics.overview.documentsChange)}
                  <span className={`text-sm ${getChangeColor(analytics.overview.documentsChange)}`}>
                    {Math.abs(analytics.overview.documentsChange)}%
                  </span>
                </div>
              </div>
              <div className="p-3 bg-blue-10 rounded-full">
                <DocumentIcon className="w-6 h-6 text-blue-60" />
              </div>
            </div>
          </div>

          <div className="card p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-70 mb-1">Collections</p>
                <p className="text-2xl font-semibold text-gray-100">
                  {analytics.overview.totalCollections}
                </p>
                <div className="flex items-center space-x-1 mt-1">
                  {getChangeIcon(analytics.overview.collectionsChange)}
                  <span className={`text-sm ${getChangeColor(analytics.overview.collectionsChange)}`}>
                    {Math.abs(analytics.overview.collectionsChange)}%
                  </span>
                </div>
              </div>
              <div className="p-3 bg-green-10 rounded-full">
                <ChartBarIcon className="w-6 h-6 text-green-60" />
              </div>
            </div>
          </div>

          <div className="card p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-70 mb-1">Active Users</p>
                <p className="text-2xl font-semibold text-gray-100">
                  {analytics.overview.totalUsers}
                </p>
                <div className="flex items-center space-x-1 mt-1">
                  {getChangeIcon(analytics.overview.usersChange)}
                  <span className={`text-sm ${getChangeColor(analytics.overview.usersChange)}`}>
                    {Math.abs(analytics.overview.usersChange)}%
                  </span>
                </div>
              </div>
              <div className="p-3 bg-purple-10 rounded-full">
                <UserGroupIcon className="w-6 h-6 text-purple-60" />
              </div>
            </div>
          </div>

          <div className="card p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-70 mb-1">Total Queries</p>
                <p className="text-2xl font-semibold text-gray-100">
                  {formatNumber(analytics.overview.totalQueries)}
                </p>
                <div className="flex items-center space-x-1 mt-1">
                  {getChangeIcon(analytics.overview.queriesChange)}
                  <span className={`text-sm ${getChangeColor(analytics.overview.queriesChange)}`}>
                    {Math.abs(analytics.overview.queriesChange)}%
                  </span>
                </div>
              </div>
              <div className="p-3 bg-orange-10 rounded-full">
                <ArrowTrendingUpIcon className="w-6 h-6 text-orange-60" />
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Usage Chart */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-100 mb-4">Daily Usage</h2>
            <div className="space-y-4">
              {analytics.usage.daily.map((day, index) => (
                <div key={day.date} className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="w-2 h-2 bg-blue-60 rounded-full"></div>
                    <span className="text-sm text-gray-70">
                      {new Date(day.date).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric'
                      })}
                    </span>
                  </div>
                  <div className="flex items-center space-x-6 text-sm">
                    <div className="text-right">
                      <p className="text-gray-100 font-medium">{day.queries}</p>
                      <p className="text-gray-60">Queries</p>
                    </div>
                    <div className="text-right">
                      <p className="text-gray-100 font-medium">{day.uploads}</p>
                      <p className="text-gray-60">Uploads</p>
                    </div>
                    <div className="text-right">
                      <p className="text-gray-100 font-medium">{day.users}</p>
                      <p className="text-gray-60">Users</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Popular Collections */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-100 mb-4">Popular Collections</h2>
            <div className="space-y-3">
              {analytics.usage.popular.map((collection, index) => (
                <div key={collection.name} className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="flex items-center justify-center w-6 h-6 bg-gray-20 rounded text-xs font-medium text-gray-70">
                      {index + 1}
                    </div>
                    <span className="text-sm text-gray-100">{collection.name}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-medium text-gray-100">
                      {formatNumber(collection.queries)}
                    </span>
                    <div className="flex items-center space-x-1">
                      {getChangeIcon(collection.change)}
                      <span className={`text-xs ${getChangeColor(collection.change)}`}>
                        {Math.abs(collection.change)}%
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Performance Metrics */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-100 mb-4">Performance Metrics</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-70">Average Response Time</span>
                <span className="text-sm font-medium text-gray-100">
                  {analytics.performance.responseTime.avg}ms
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-70">95th Percentile</span>
                <span className="text-sm font-medium text-gray-100">
                  {analytics.performance.responseTime.p95}ms
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-70">99th Percentile</span>
                <span className="text-sm font-medium text-gray-100">
                  {analytics.performance.responseTime.p99}ms
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-70">Success Rate</span>
                <div className="flex items-center space-x-2">
                  <div className="w-16 h-2 bg-gray-20 rounded-full">
                    <div
                      className="h-full bg-green-50 rounded-full"
                      style={{ width: `${analytics.performance.successRate}%` }}
                    ></div>
                  </div>
                  <span className="text-sm font-medium text-gray-100">
                    {analytics.performance.successRate}%
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-70">Error Rate</span>
                <div className="flex items-center space-x-2">
                  <div className="w-16 h-2 bg-gray-20 rounded-full">
                    <div
                      className="h-full bg-red-50 rounded-full"
                      style={{ width: `${analytics.performance.errorRate * 10}%` }}
                    ></div>
                  </div>
                  <span className="text-sm font-medium text-gray-100">
                    {analytics.performance.errorRate}%
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-70">Uptime</span>
                <div className="flex items-center space-x-2">
                  <div className="w-16 h-2 bg-gray-20 rounded-full">
                    <div
                      className="h-full bg-blue-60 rounded-full"
                      style={{ width: `${analytics.performance.uptime}%` }}
                    ></div>
                  </div>
                  <span className="text-sm font-medium text-gray-100">
                    {analytics.performance.uptime}%
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Storage Usage */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-100 mb-4">Storage Usage</h2>

            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-70">Used Storage</span>
                <span className="text-sm font-medium text-gray-100">
                  {formatBytes(analytics.storage.usedSize)} / {formatBytes(analytics.storage.totalSize)}
                </span>
              </div>
              <div className="w-full h-3 bg-gray-20 rounded-full">
                <div
                  className="h-full bg-blue-60 rounded-full"
                  style={{ width: `${(analytics.storage.usedSize / analytics.storage.totalSize) * 100}%` }}
                ></div>
              </div>
              <p className="text-xs text-gray-60 mt-1">
                {((analytics.storage.usedSize / analytics.storage.totalSize) * 100).toFixed(1)}% used
              </p>
            </div>

            <div className="space-y-3">
              <h3 className="text-sm font-medium text-gray-100">Documents by Type</h3>
              {analytics.storage.documentsByType.map((type) => (
                <div key={type.type} className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 bg-blue-40 rounded"></div>
                    <span className="text-sm text-gray-70">{type.type}</span>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-100">{type.count} files</p>
                    <p className="text-xs text-gray-60">{formatBytes(type.size)}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* System Health */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-gray-100 mb-4">System Health Overview</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-3 bg-green-10 rounded-full flex items-center justify-center">
                <div className="w-8 h-8 bg-green-50 rounded-full"></div>
              </div>
              <h3 className="text-sm font-medium text-gray-100 mb-1">System Status</h3>
              <p className="text-sm text-green-50">All Systems Operational</p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-3 bg-blue-10 rounded-full flex items-center justify-center">
                <ClockIcon className="w-8 h-8 text-blue-60" />
              </div>
              <h3 className="text-sm font-medium text-gray-100 mb-1">Last Update</h3>
              <p className="text-sm text-gray-70">{new Date().toLocaleTimeString()}</p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-3 bg-purple-10 rounded-full flex items-center justify-center">
                <EyeIcon className="w-8 h-8 text-purple-60" />
              </div>
              <h3 className="text-sm font-medium text-gray-100 mb-1">Monitoring</h3>
              <p className="text-sm text-green-50">Active</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LightweightAnalyticsDashboard;
