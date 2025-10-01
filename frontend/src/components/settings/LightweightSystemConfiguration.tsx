import React, { useState, useEffect } from 'react';
import {
  CogIcon,
  ServerIcon,
  CircleStackIcon,
  KeyIcon,
  BellIcon,
  ShieldCheckIcon,
  DocumentTextIcon,
  ClockIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  CheckIcon,
  XMarkIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline';
import { useNotification } from '../../contexts/NotificationContext';

interface SystemConfig {
  database: {
    host: string;
    port: number;
    name: string;
    connectionPool: number;
    timeout: number;
    ssl: boolean;
  };
  vectorDb: {
    provider: 'milvus' | 'pinecone' | 'weaviate' | 'chroma';
    host: string;
    port: number;
    collection: string;
    dimensions: number;
    indexType: string;
  };
  llm: {
    defaultProvider: 'openai' | 'anthropic' | 'watsonx';
    apiKeys: {
      openai: string;
      anthropic: string;
      watsonx: string;
    };
    models: {
      chat: string;
      embedding: string;
      completion: string;
    };
    rateLimits: {
      requestsPerMinute: number;
      tokensPerMinute: number;
    };
  };
  security: {
    jwtSecret: string;
    sessionTimeout: number;
    maxLoginAttempts: number;
    passwordPolicy: {
      minLength: number;
      requireUppercase: boolean;
      requireNumbers: boolean;
      requireSymbols: boolean;
    };
    corsOrigins: string[];
  };
  storage: {
    provider: 'local' | 'aws' | 'azure' | 'gcp';
    bucket: string;
    region: string;
    maxFileSize: number;
    allowedTypes: string[];
  };
  monitoring: {
    logLevel: 'debug' | 'info' | 'warn' | 'error';
    metricsEnabled: boolean;
    alerting: {
      email: boolean;
      webhook: string;
      thresholds: {
        errorRate: number;
        responseTime: number;
        diskUsage: number;
      };
    };
  };
}

const LightweightSystemConfiguration: React.FC = () => {
  const { addNotification } = useNotification();
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeSection, setActiveSection] = useState('database');
  const [hasChanges, setHasChanges] = useState(false);
  const [testResults, setTestResults] = useState<{ [key: string]: boolean | null }>({});

  const sections = [
    { id: 'database', name: 'Database', icon: CircleStackIcon },
    { id: 'vectordb', name: 'Vector DB', icon: ServerIcon },
    { id: 'llm', name: 'LLM Providers', icon: DocumentTextIcon },
    { id: 'security', name: 'Security', icon: ShieldCheckIcon },
    { id: 'storage', name: 'Storage', icon: CogIcon },
    { id: 'monitoring', name: 'Monitoring', icon: ChartBarIcon },
  ];

  useEffect(() => {
    const loadConfig = async () => {
      setIsLoading(true);
      try {
        await new Promise(resolve => setTimeout(resolve, 1000));

        const mockConfig: SystemConfig = {
          database: {
            host: 'localhost',
            port: 5432,
            name: 'ragmodulo',
            connectionPool: 10,
            timeout: 30,
            ssl: false,
          },
          vectorDb: {
            provider: 'milvus',
            host: 'localhost',
            port: 19530,
            collection: 'documents',
            dimensions: 1536,
            indexType: 'IVF_FLAT',
          },
          llm: {
            defaultProvider: 'openai',
            apiKeys: {
              openai: 'sk-*********************',
              anthropic: 'sk-ant-***************',
              watsonx: 'watson-***************',
            },
            models: {
              chat: 'gpt-4',
              embedding: 'text-embedding-ada-002',
              completion: 'gpt-3.5-turbo',
            },
            rateLimits: {
              requestsPerMinute: 100,
              tokensPerMinute: 10000,
            },
          },
          security: {
            jwtSecret: '*********************',
            sessionTimeout: 8,
            maxLoginAttempts: 5,
            passwordPolicy: {
              minLength: 8,
              requireUppercase: true,
              requireNumbers: true,
              requireSymbols: false,
            },
            corsOrigins: ['http://localhost:3000', 'https://app.ragmodulo.com'],
          },
          storage: {
            provider: 'local',
            bucket: 'documents',
            region: 'us-east-1',
            maxFileSize: 100,
            allowedTypes: ['.pdf', '.docx', '.txt', '.md'],
          },
          monitoring: {
            logLevel: 'info',
            metricsEnabled: true,
            alerting: {
              email: true,
              webhook: 'https://hooks.slack.com/services/...',
              thresholds: {
                errorRate: 5,
                responseTime: 2000,
                diskUsage: 80,
              },
            },
          },
        };

        setConfig(mockConfig);
      } catch (error) {
        addNotification('error', 'Loading Error', 'Failed to load system configuration.');
      } finally {
        setIsLoading(false);
      }
    };

    loadConfig();
  }, [addNotification]);

  const handleConfigChange = (section: string, field: string, value: any) => {
    setConfig(prev => prev ? {
      ...prev,
      [section]: {
        ...prev[section as keyof SystemConfig],
        [field]: value,
      },
    } : null);
    setHasChanges(true);
  };

  const handleNestedConfigChange = (section: string, nested: string, field: string, value: any) => {
    setConfig(prev => prev ? {
      ...prev,
      [section]: {
        ...(prev[section as keyof SystemConfig] as any),
        [nested]: {
          ...(prev[section as keyof SystemConfig] as any)[nested],
          [field]: value,
        },
      },
    } : null);
    setHasChanges(true);
  };

  const testConnection = async (type: string) => {
    setTestResults(prev => ({ ...prev, [type]: null }));

    await new Promise(resolve => setTimeout(resolve, 2000));

    const success = Math.random() > 0.3;
    setTestResults(prev => ({ ...prev, [type]: success }));

    addNotification(
      success ? 'success' : 'error',
      'Connection Test',
      `${type} connection ${success ? 'successful' : 'failed'}.`
    );
  };

  const saveConfiguration = async () => {
    setIsLoading(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 1500));
      setHasChanges(false);
      addNotification('success', 'Configuration Saved', 'System configuration has been updated successfully.');
    } catch (error) {
      addNotification('error', 'Save Error', 'Failed to save configuration.');
    } finally {
      setIsLoading(false);
    }
  };

  const resetToDefaults = () => {
    if (window.confirm('Are you sure you want to reset all settings to defaults? This cannot be undone.')) {
      window.location.reload();
    }
  };

  if (isLoading && !config) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-60 mx-auto mb-4"></div>
          <p className="text-gray-70">Loading system configuration...</p>
        </div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="min-h-screen bg-gray-10 p-6">
        <div className="max-w-6xl mx-auto text-center">
          <h1 className="text-2xl font-semibold text-gray-100 mb-4">Configuration Not Available</h1>
          <button onClick={() => window.location.reload()} className="btn-primary">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-10 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="card p-6 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-gray-100">System Configuration</h1>
              <p className="text-gray-70">Manage core system settings and integrations</p>
            </div>
            <div className="flex space-x-3">
              {hasChanges && (
                <div className="flex items-center space-x-2 text-yellow-30">
                  <ExclamationTriangleIcon className="w-4 h-4" />
                  <span className="text-sm">Unsaved changes</span>
                </div>
              )}
              <button
                onClick={resetToDefaults}
                className="btn-secondary text-red-50 hover:bg-red-50 hover:text-white"
              >
                Reset to Defaults
              </button>
              <button
                onClick={saveConfiguration}
                disabled={!hasChanges || isLoading}
                className="btn-primary disabled:opacity-50"
              >
                {isLoading ? 'Saving...' : 'Save Configuration'}
              </button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar */}
          <div className="lg:col-span-1">
            <div className="card p-4">
              <nav className="space-y-1">
                {sections.map((section) => (
                  <button
                    key={section.id}
                    onClick={() => setActiveSection(section.id)}
                    className={`w-full flex items-center space-x-3 px-3 py-2 text-sm font-medium rounded-md ${
                      activeSection === section.id
                        ? 'bg-blue-60 text-white'
                        : 'text-gray-70 hover:text-gray-100 hover:bg-gray-20'
                    }`}
                  >
                    <section.icon className="w-4 h-4" />
                    <span>{section.name}</span>
                  </button>
                ))}
              </nav>
            </div>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3">
            {/* Database Configuration */}
            {activeSection === 'database' && (
              <div className="card p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-lg font-semibold text-gray-100">Database Configuration</h2>
                  <button
                    onClick={() => testConnection('database')}
                    className="btn-secondary flex items-center space-x-2"
                  >
                    {testResults.database === null ? (
                      <ClockIcon className="w-4 h-4 animate-spin" />
                    ) : testResults.database ? (
                      <CheckIcon className="w-4 h-4 text-green-50" />
                    ) : (
                      <XMarkIcon className="w-4 h-4 text-red-50" />
                    )}
                    <span>Test Connection</span>
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-100 mb-2">Host</label>
                    <input
                      type="text"
                      value={config.database.host}
                      onChange={(e) => handleConfigChange('database', 'host', e.target.value)}
                      className="input-field w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-100 mb-2">Port</label>
                    <input
                      type="number"
                      value={config.database.port}
                      onChange={(e) => handleConfigChange('database', 'port', parseInt(e.target.value))}
                      className="input-field w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-100 mb-2">Database Name</label>
                    <input
                      type="text"
                      value={config.database.name}
                      onChange={(e) => handleConfigChange('database', 'name', e.target.value)}
                      className="input-field w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-100 mb-2">Connection Pool Size</label>
                    <input
                      type="number"
                      value={config.database.connectionPool}
                      onChange={(e) => handleConfigChange('database', 'connectionPool', parseInt(e.target.value))}
                      className="input-field w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-100 mb-2">Timeout (seconds)</label>
                    <input
                      type="number"
                      value={config.database.timeout}
                      onChange={(e) => handleConfigChange('database', 'timeout', parseInt(e.target.value))}
                      className="input-field w-full"
                    />
                  </div>

                  <div className="flex items-center space-x-3">
                    <input
                      type="checkbox"
                      id="ssl"
                      checked={config.database.ssl}
                      onChange={(e) => handleConfigChange('database', 'ssl', e.target.checked)}
                      className="rounded border-gray-40"
                    />
                    <label htmlFor="ssl" className="text-sm font-medium text-gray-100">
                      Enable SSL
                    </label>
                  </div>
                </div>
              </div>
            )}

            {/* Vector Database Configuration */}
            {activeSection === 'vectordb' && (
              <div className="card p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-lg font-semibold text-gray-100">Vector Database Configuration</h2>
                  <button
                    onClick={() => testConnection('vectordb')}
                    className="btn-secondary flex items-center space-x-2"
                  >
                    {testResults.vectordb === null ? (
                      <ClockIcon className="w-4 h-4 animate-spin" />
                    ) : testResults.vectordb ? (
                      <CheckIcon className="w-4 h-4 text-green-50" />
                    ) : (
                      <XMarkIcon className="w-4 h-4 text-red-50" />
                    )}
                    <span>Test Connection</span>
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-100 mb-2">Provider</label>
                    <select
                      value={config.vectorDb.provider}
                      onChange={(e) => handleConfigChange('vectorDb', 'provider', e.target.value)}
                      className="input-field w-full"
                    >
                      <option value="milvus">Milvus</option>
                      <option value="pinecone">Pinecone</option>
                      <option value="weaviate">Weaviate</option>
                      <option value="chroma">ChromaDB</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-100 mb-2">Host</label>
                    <input
                      type="text"
                      value={config.vectorDb.host}
                      onChange={(e) => handleConfigChange('vectorDb', 'host', e.target.value)}
                      className="input-field w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-100 mb-2">Port</label>
                    <input
                      type="number"
                      value={config.vectorDb.port}
                      onChange={(e) => handleConfigChange('vectorDb', 'port', parseInt(e.target.value))}
                      className="input-field w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-100 mb-2">Collection Name</label>
                    <input
                      type="text"
                      value={config.vectorDb.collection}
                      onChange={(e) => handleConfigChange('vectorDb', 'collection', e.target.value)}
                      className="input-field w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-100 mb-2">Vector Dimensions</label>
                    <input
                      type="number"
                      value={config.vectorDb.dimensions}
                      onChange={(e) => handleConfigChange('vectorDb', 'dimensions', parseInt(e.target.value))}
                      className="input-field w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-100 mb-2">Index Type</label>
                    <select
                      value={config.vectorDb.indexType}
                      onChange={(e) => handleConfigChange('vectorDb', 'indexType', e.target.value)}
                      className="input-field w-full"
                    >
                      <option value="IVF_FLAT">IVF_FLAT</option>
                      <option value="IVF_SQ8">IVF_SQ8</option>
                      <option value="HNSW">HNSW</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* LLM Provider Configuration */}
            {activeSection === 'llm' && (
              <div className="space-y-6">
                <div className="card p-6">
                  <h2 className="text-lg font-semibold text-gray-100 mb-6">LLM Provider Configuration</h2>

                  <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-100 mb-2">Default Provider</label>
                    <select
                      value={config.llm.defaultProvider}
                      onChange={(e) => handleConfigChange('llm', 'defaultProvider', e.target.value)}
                      className="input-field w-full md:w-64"
                    >
                      <option value="openai">OpenAI</option>
                      <option value="anthropic">Anthropic</option>
                      <option value="watsonx">IBM WatsonX</option>
                    </select>
                  </div>

                  <div className="grid grid-cols-1 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-100 mb-2">OpenAI API Key</label>
                      <div className="flex items-center space-x-2">
                        <input
                          type="password"
                          value={config.llm.apiKeys.openai}
                          onChange={(e) => handleNestedConfigChange('llm', 'apiKeys', 'openai', e.target.value)}
                          className="input-field flex-1"
                          placeholder="sk-..."
                        />
                        <button
                          onClick={() => testConnection('openai')}
                          className="btn-secondary px-3 py-2"
                        >
                          Test
                        </button>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-100 mb-2">Anthropic API Key</label>
                      <div className="flex items-center space-x-2">
                        <input
                          type="password"
                          value={config.llm.apiKeys.anthropic}
                          onChange={(e) => handleNestedConfigChange('llm', 'apiKeys', 'anthropic', e.target.value)}
                          className="input-field flex-1"
                          placeholder="sk-ant-..."
                        />
                        <button
                          onClick={() => testConnection('anthropic')}
                          className="btn-secondary px-3 py-2"
                        >
                          Test
                        </button>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-100 mb-2">WatsonX API Key</label>
                      <div className="flex items-center space-x-2">
                        <input
                          type="password"
                          value={config.llm.apiKeys.watsonx}
                          onChange={(e) => handleNestedConfigChange('llm', 'apiKeys', 'watsonx', e.target.value)}
                          className="input-field flex-1"
                          placeholder="watson-..."
                        />
                        <button
                          onClick={() => testConnection('watsonx')}
                          className="btn-secondary px-3 py-2"
                        >
                          Test
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-100 mb-4">Model Configuration</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-100 mb-2">Chat Model</label>
                      <input
                        type="text"
                        value={config.llm.models.chat}
                        onChange={(e) => handleNestedConfigChange('llm', 'models', 'chat', e.target.value)}
                        className="input-field w-full"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-100 mb-2">Embedding Model</label>
                      <input
                        type="text"
                        value={config.llm.models.embedding}
                        onChange={(e) => handleNestedConfigChange('llm', 'models', 'embedding', e.target.value)}
                        className="input-field w-full"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-100 mb-2">Completion Model</label>
                      <input
                        type="text"
                        value={config.llm.models.completion}
                        onChange={(e) => handleNestedConfigChange('llm', 'models', 'completion', e.target.value)}
                        className="input-field w-full"
                      />
                    </div>
                  </div>
                </div>

                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-100 mb-4">Rate Limits</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-100 mb-2">Requests per Minute</label>
                      <input
                        type="number"
                        value={config.llm.rateLimits.requestsPerMinute}
                        onChange={(e) => handleNestedConfigChange('llm', 'rateLimits', 'requestsPerMinute', parseInt(e.target.value))}
                        className="input-field w-full"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-100 mb-2">Tokens per Minute</label>
                      <input
                        type="number"
                        value={config.llm.rateLimits.tokensPerMinute}
                        onChange={(e) => handleNestedConfigChange('llm', 'rateLimits', 'tokensPerMinute', parseInt(e.target.value))}
                        className="input-field w-full"
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Security Configuration */}
            {activeSection === 'security' && (
              <div className="space-y-6">
                <div className="card p-6">
                  <h2 className="text-lg font-semibold text-gray-100 mb-6">Security Configuration</h2>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-100 mb-2">JWT Secret Key</label>
                      <input
                        type="password"
                        value={config.security.jwtSecret}
                        onChange={(e) => handleConfigChange('security', 'jwtSecret', e.target.value)}
                        className="input-field w-full"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-100 mb-2">Session Timeout (hours)</label>
                      <input
                        type="number"
                        value={config.security.sessionTimeout}
                        onChange={(e) => handleConfigChange('security', 'sessionTimeout', parseInt(e.target.value))}
                        className="input-field w-full"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-100 mb-2">Max Login Attempts</label>
                      <input
                        type="number"
                        value={config.security.maxLoginAttempts}
                        onChange={(e) => handleConfigChange('security', 'maxLoginAttempts', parseInt(e.target.value))}
                        className="input-field w-full"
                      />
                    </div>
                  </div>
                </div>

                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-100 mb-4">Password Policy</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-100 mb-2">Minimum Length</label>
                      <input
                        type="number"
                        value={config.security.passwordPolicy.minLength}
                        onChange={(e) => handleNestedConfigChange('security', 'passwordPolicy', 'minLength', parseInt(e.target.value))}
                        className="input-field w-full"
                      />
                    </div>

                    <div className="space-y-3">
                      <div className="flex items-center space-x-3">
                        <input
                          type="checkbox"
                          id="requireUppercase"
                          checked={config.security.passwordPolicy.requireUppercase}
                          onChange={(e) => handleNestedConfigChange('security', 'passwordPolicy', 'requireUppercase', e.target.checked)}
                          className="rounded border-gray-40"
                        />
                        <label htmlFor="requireUppercase" className="text-sm font-medium text-gray-100">
                          Require Uppercase
                        </label>
                      </div>

                      <div className="flex items-center space-x-3">
                        <input
                          type="checkbox"
                          id="requireNumbers"
                          checked={config.security.passwordPolicy.requireNumbers}
                          onChange={(e) => handleNestedConfigChange('security', 'passwordPolicy', 'requireNumbers', e.target.checked)}
                          className="rounded border-gray-40"
                        />
                        <label htmlFor="requireNumbers" className="text-sm font-medium text-gray-100">
                          Require Numbers
                        </label>
                      </div>

                      <div className="flex items-center space-x-3">
                        <input
                          type="checkbox"
                          id="requireSymbols"
                          checked={config.security.passwordPolicy.requireSymbols}
                          onChange={(e) => handleNestedConfigChange('security', 'passwordPolicy', 'requireSymbols', e.target.checked)}
                          className="rounded border-gray-40"
                        />
                        <label htmlFor="requireSymbols" className="text-sm font-medium text-gray-100">
                          Require Symbols
                        </label>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-100 mb-4">CORS Origins</h3>
                  <div className="space-y-2">
                    {config.security.corsOrigins.map((origin, index) => (
                      <div key={index} className="flex items-center space-x-2">
                        <input
                          type="text"
                          value={origin}
                          onChange={(e) => {
                            const newOrigins = [...config.security.corsOrigins];
                            newOrigins[index] = e.target.value;
                            handleConfigChange('security', 'corsOrigins', newOrigins);
                          }}
                          className="input-field flex-1"
                        />
                        <button
                          onClick={() => {
                            const newOrigins = config.security.corsOrigins.filter((_, i) => i !== index);
                            handleConfigChange('security', 'corsOrigins', newOrigins);
                          }}
                          className="btn-secondary text-red-50 hover:bg-red-50 hover:text-white p-2"
                        >
                          <XMarkIcon className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                    <button
                      onClick={() => {
                        const newOrigins = [...config.security.corsOrigins, ''];
                        handleConfigChange('security', 'corsOrigins', newOrigins);
                      }}
                      className="btn-secondary text-green-50 hover:bg-green-50 hover:text-white"
                    >
                      Add Origin
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Storage Configuration */}
            {activeSection === 'storage' && (
              <div className="card p-6">
                <h2 className="text-lg font-semibold text-gray-100 mb-6">Storage Configuration</h2>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-100 mb-2">Storage Provider</label>
                    <select
                      value={config.storage.provider}
                      onChange={(e) => handleConfigChange('storage', 'provider', e.target.value)}
                      className="input-field w-full"
                    >
                      <option value="local">Local Storage</option>
                      <option value="aws">Amazon S3</option>
                      <option value="azure">Azure Blob</option>
                      <option value="gcp">Google Cloud Storage</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-100 mb-2">Bucket/Container Name</label>
                    <input
                      type="text"
                      value={config.storage.bucket}
                      onChange={(e) => handleConfigChange('storage', 'bucket', e.target.value)}
                      className="input-field w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-100 mb-2">Region</label>
                    <input
                      type="text"
                      value={config.storage.region}
                      onChange={(e) => handleConfigChange('storage', 'region', e.target.value)}
                      className="input-field w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-100 mb-2">Max File Size (MB)</label>
                    <input
                      type="number"
                      value={config.storage.maxFileSize}
                      onChange={(e) => handleConfigChange('storage', 'maxFileSize', parseInt(e.target.value))}
                      className="input-field w-full"
                    />
                  </div>
                </div>

                <div className="mt-6">
                  <label className="block text-sm font-medium text-gray-100 mb-2">Allowed File Types</label>
                  <div className="flex flex-wrap gap-2">
                    {config.storage.allowedTypes.map((type, index) => (
                      <div key={index} className="flex items-center space-x-1 bg-gray-20 px-2 py-1 rounded">
                        <span className="text-sm text-gray-100">{type}</span>
                        <button
                          onClick={() => {
                            const newTypes = config.storage.allowedTypes.filter((_, i) => i !== index);
                            handleConfigChange('storage', 'allowedTypes', newTypes);
                          }}
                          className="text-gray-60 hover:text-red-50"
                        >
                          <XMarkIcon className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                  <input
                    type="text"
                    placeholder="Add file type (e.g., .pdf)"
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        const value = (e.target as HTMLInputElement).value.trim();
                        if (value && !config.storage.allowedTypes.includes(value)) {
                          const newTypes = [...config.storage.allowedTypes, value];
                          handleConfigChange('storage', 'allowedTypes', newTypes);
                          (e.target as HTMLInputElement).value = '';
                        }
                      }
                    }}
                    className="input-field w-full mt-2"
                  />
                </div>
              </div>
            )}

            {/* Monitoring Configuration */}
            {activeSection === 'monitoring' && (
              <div className="space-y-6">
                <div className="card p-6">
                  <h2 className="text-lg font-semibold text-gray-100 mb-6">Monitoring Configuration</h2>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-100 mb-2">Log Level</label>
                      <select
                        value={config.monitoring.logLevel}
                        onChange={(e) => handleConfigChange('monitoring', 'logLevel', e.target.value)}
                        className="input-field w-full"
                      >
                        <option value="debug">Debug</option>
                        <option value="info">Info</option>
                        <option value="warn">Warning</option>
                        <option value="error">Error</option>
                      </select>
                    </div>

                    <div className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        id="metricsEnabled"
                        checked={config.monitoring.metricsEnabled}
                        onChange={(e) => handleConfigChange('monitoring', 'metricsEnabled', e.target.checked)}
                        className="rounded border-gray-40"
                      />
                      <label htmlFor="metricsEnabled" className="text-sm font-medium text-gray-100">
                        Enable Metrics Collection
                      </label>
                    </div>
                  </div>
                </div>

                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-100 mb-4">Alerting Configuration</h3>

                  <div className="grid grid-cols-1 gap-6">
                    <div className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        id="emailAlerting"
                        checked={config.monitoring.alerting.email}
                        onChange={(e) => handleNestedConfigChange('monitoring', 'alerting', 'email', e.target.checked)}
                        className="rounded border-gray-40"
                      />
                      <label htmlFor="emailAlerting" className="text-sm font-medium text-gray-100">
                        Enable Email Alerts
                      </label>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-100 mb-2">Webhook URL</label>
                      <input
                        type="url"
                        value={config.monitoring.alerting.webhook}
                        onChange={(e) => handleNestedConfigChange('monitoring', 'alerting', 'webhook', e.target.value)}
                        className="input-field w-full"
                        placeholder="https://hooks.slack.com/services/..."
                      />
                    </div>

                    <div>
                      <h4 className="text-md font-medium text-gray-100 mb-3">Alert Thresholds</h4>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-100 mb-2">Error Rate (%)</label>
                          <input
                            type="number"
                            value={config.monitoring.alerting.thresholds.errorRate}
                            onChange={(e) => handleNestedConfigChange('monitoring', 'alerting', 'thresholds', {
                              ...config.monitoring.alerting.thresholds,
                              errorRate: parseInt(e.target.value)
                            })}
                            className="input-field w-full"
                          />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-100 mb-2">Response Time (ms)</label>
                          <input
                            type="number"
                            value={config.monitoring.alerting.thresholds.responseTime}
                            onChange={(e) => handleNestedConfigChange('monitoring', 'alerting', 'thresholds', {
                              ...config.monitoring.alerting.thresholds,
                              responseTime: parseInt(e.target.value)
                            })}
                            className="input-field w-full"
                          />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-100 mb-2">Disk Usage (%)</label>
                          <input
                            type="number"
                            value={config.monitoring.alerting.thresholds.diskUsage}
                            onChange={(e) => handleNestedConfigChange('monitoring', 'alerting', 'thresholds', {
                              ...config.monitoring.alerting.thresholds,
                              diskUsage: parseInt(e.target.value)
                            })}
                            className="input-field w-full"
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LightweightSystemConfiguration;
