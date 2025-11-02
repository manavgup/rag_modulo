import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UserIcon,
  KeyIcon,
  BellIcon,
  ShieldCheckIcon,
  CogIcon,
  PencilIcon,
  CheckIcon,
  XMarkIcon,
  EyeIcon,
  EyeSlashIcon,
  CpuChipIcon,
  AdjustmentsHorizontalIcon,
  DocumentTextIcon,
  ShareIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  StarIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '../../contexts/AuthContext';
import { useNotification } from '../../contexts/NotificationContext';
import { Skeleton } from '../ui/Skeleton';
import {
  usePromptTemplates,
  useCreatePromptTemplate,
  useUpdatePromptTemplate,
  useDeletePromptTemplate,
  useSetDefaultPromptTemplate,
  useLLMParameters,
  useCreateLLMParameters,
  useUpdateLLMParameters,
  useDeleteLLMParameters,
  useSetDefaultLLMParameters,
  usePipelineConfigs,
  useCreatePipelineConfig,
  useUpdatePipelineConfig,
  useDeletePipelineConfig,
  useSetDefaultPipelineConfig,
} from '../../hooks/useUserSettings';
import type { PromptTemplate as APIPromptTemplate, LLMParameters as APILLMParameters, PipelineConfig as APIPipelineConfig } from '../../api/userSettings';

interface LLMProvider {
  id: string;
  name: string;
  type: 'watsonx' | 'openai' | 'anthropic';
  description: string;
  isActive: boolean;
}

// Component-specific display types (transformed from API types)
interface DisplayPromptTemplate {
  id: string;
  name: string;
  type: 'rag_query' | 'question_generation';
  systemPrompt: string;
  templateFormat: string;
  isDefault: boolean;
}

interface UserProfile {
  id: string;
  name: string;
  email: string;
  role: string;
  department?: string;
  joined: Date;
  lastLogin: Date;
  avatar?: string;
  preferences: {
    notifications: {
      email: boolean;
      browser: boolean;
      mobile: boolean;
    };
    theme: 'light' | 'dark' | 'system';
    language: string;
    timezone: string;
  };
  security: {
    twoFactorEnabled: boolean;
    lastPasswordChange: Date;
    sessionTimeout: number;
  };
  aiPreferences: {
    currentProvider: LLMProvider;
    availableProviders: LLMProvider[];
    llmParameters: LLMParameters;
    promptTemplates: PromptTemplate[];
    pipelineConfig: PipelineConfig;
  };
}

const LightweightUserProfile: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { addNotification } = useNotification();

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('profile');
  const [isEditing, setIsEditing] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
    showCurrent: false,
    showNew: false,
    showConfirm: false,
  });

  const [editForm, setEditForm] = useState({
    name: '',
    department: '',
  });

  // AI Preferences Modal States
  const [showProviderModal, setShowProviderModal] = useState(false);
  const [showParametersModal, setShowParametersModal] = useState(false);
  const [showTemplatesModal, setShowTemplatesModal] = useState(false);
  const [selectedTemplateIndex, setSelectedTemplateIndex] = useState(0);
  const [isEditingTemplate, setIsEditingTemplate] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<PromptTemplate | null>(null);
  const [showPipelineModal, setShowPipelineModal] = useState(false);

  // React Query hooks for API data
  const userId = user?.id || '';
  const { data: promptTemplates = [], isLoading: templatesLoading, error: templatesError } = usePromptTemplates(userId);
  const { data: llmParameters = [], isLoading: llmParamsLoading, error: llmParamsError } = useLLMParameters(userId);
  const { data: pipelineConfigs = [], isLoading: pipelinesLoading, error: pipelinesError } = usePipelineConfigs(userId);

  const createTemplateMutation = useCreatePromptTemplate(userId);
  const updateTemplateMutation = useUpdatePromptTemplate(userId);
  const deleteTemplateMutation = useDeletePromptTemplate(userId);
  const setDefaultTemplateMutation = useSetDefaultPromptTemplate(userId);

  const createLLMParamsMutation = useCreateLLMParameters(userId);
  const updateLLMParamsMutation = useUpdateLLMParameters(userId);
  const deleteLLMParamsMutation = useDeleteLLMParameters(userId);
  const setDefaultLLMParamsMutation = useSetDefaultLLMParameters(userId);

  const createPipelineMutation = useCreatePipelineConfig(userId);
  const updatePipelineMutation = useUpdatePipelineConfig(userId);
  const deletePipelineMutation = useDeletePipelineConfig(userId);
  const setDefaultPipelineMutation = useSetDefaultPipelineConfig(userId);

  // Convert API templates to component display format (memoized for performance)
  const allTemplates: DisplayPromptTemplate[] = useMemo(
    () =>
      promptTemplates.map(t => ({
        id: t.id,
        name: t.name,
        type: t.template_type.toLowerCase() as 'rag_query' | 'question_generation',
        systemPrompt: t.system_prompt || '',
        templateFormat: t.template_format,
        isDefault: t.is_default,
      })),
    [promptTemplates]
  );

  useEffect(() => {
    const loadProfile = async () => {
      setIsLoading(true);
      try {
        await new Promise(resolve => setTimeout(resolve, 1000));

        const mockProfile: UserProfile = {
          id: user?.id || '1',
          name: (user as any)?.name || 'John Doe',
          email: user?.email || 'john.doe@company.com',
          role: 'Data Scientist',
          department: 'AI Research',
          joined: new Date('2023-03-15'),
          lastLogin: new Date(),
          preferences: {
            notifications: {
              email: true,
              browser: true,
              mobile: false,
            },
            theme: 'light',
            language: 'en',
            timezone: 'UTC-8',
          },
          security: {
            twoFactorEnabled: true,
            lastPasswordChange: new Date('2024-01-01'),
            sessionTimeout: 8,
          },
          aiPreferences: {
            currentProvider: {
              id: 'watsonx-1',
              name: 'WatsonX',
              type: 'watsonx',
              description: 'IBM WatsonX LLM Service',
              isActive: true,
            },
            availableProviders: [
              {
                id: 'watsonx-1',
                name: 'WatsonX',
                type: 'watsonx',
                description: 'IBM WatsonX LLM Service',
                isActive: true,
              },
              {
                id: 'openai-1',
                name: 'OpenAI GPT-4',
                type: 'openai',
                description: 'OpenAI GPT-4 API',
                isActive: false,
              },
              {
                id: 'anthropic-1',
                name: 'Claude',
                type: 'anthropic',
                description: 'Anthropic Claude API',
                isActive: false,
              },
            ],
            llmParameters: {
              temperature: 0.7,
              maxTokens: 2048,
              topP: 0.9,
              topK: 40,
              repetitionPenalty: 1.1,
              stopSequences: ['</response>', '\n\nHuman:'],
            },
            promptTemplates: [
              {
                id: 'rag-template-1',
                name: 'Default RAG Template',
                type: 'rag_query',
                systemPrompt: 'You are a helpful AI assistant specializing in answering questions based on the given context.',
                templateFormat: '{context}\n\n{question}',
                isDefault: true,
              },
              {
                id: 'question-template-1',
                name: 'Question Generation Template',
                type: 'question_generation',
                systemPrompt: 'Generate relevant questions based on the given context.',
                templateFormat: '{context}\n\nGenerate {num_questions} questions.',
                isDefault: true,
              },
            ],
            pipelineConfig: {
              id: 'pipeline-1',
              name: 'Default RAG Pipeline',
              provider: 'WatsonX',
              model: 'granite-13b-chat-v2',
              embeddingModel: 'bge-large-en',
              retrievalLimit: 5,
              isDefault: true,
            },
          },
        };

        setProfile(mockProfile);
        setEditForm({
          name: mockProfile.name,
          department: mockProfile.department || '',
        });
      } catch (error) {
        addNotification('error', 'Loading Error', 'Failed to load profile data.');
      } finally {
        setIsLoading(false);
      }
    };

    loadProfile();
  }, [user, addNotification]);

  const handleSaveProfile = () => {
    if (!profile) return;

    setProfile(prev => prev ? {
      ...prev,
      name: editForm.name,
      department: editForm.department,
    } : null);

    setIsEditing(false);
    addNotification('success', 'Profile Updated', 'Your profile has been saved successfully.');
  };

  const handleCancelEdit = () => {
    if (!profile) return;

    setEditForm({
      name: profile.name,
      department: profile.department || '',
    });
    setIsEditing(false);
  };

  const handlePreferenceChange = (category: string, key: string, value: any) => {
    setProfile(prev => prev ? {
      ...prev,
      preferences: {
        ...prev.preferences,
        [category]: typeof prev.preferences[category as keyof typeof prev.preferences] === 'object'
          ? { ...(prev.preferences[category as keyof typeof prev.preferences] as any), [key]: value }
          : value,
      },
    } : null);
    addNotification('success', 'Preference Updated', 'Your settings have been saved.');
  };

  const handlePasswordChange = () => {
    if (!passwordForm.newPassword || !passwordForm.confirmPassword || !passwordForm.currentPassword) {
      addNotification('error', 'Validation Error', 'Please fill in all password fields.');
      return;
    }

    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      addNotification('error', 'Password Mismatch', 'New passwords do not match.');
      return;
    }

    if (passwordForm.newPassword.length < 8) {
      addNotification('error', 'Weak Password', 'Password must be at least 8 characters long.');
      return;
    }

    setProfile(prev => prev ? {
      ...prev,
      security: {
        ...prev.security,
        lastPasswordChange: new Date(),
      },
    } : null);

    setPasswordForm({
      currentPassword: '',
      newPassword: '',
      confirmPassword: '',
      showCurrent: false,
      showNew: false,
      showConfirm: false,
    });
    setShowPasswordModal(false);
    addNotification('success', 'Password Changed', 'Your password has been updated successfully.');
  };

  const toggleTwoFactor = () => {
    setProfile(prev => prev ? {
      ...prev,
      security: {
        ...prev.security,
        twoFactorEnabled: !prev.security.twoFactorEnabled,
      },
    } : null);

    const status = profile?.security.twoFactorEnabled ? 'disabled' : 'enabled';
    addNotification('success', 'Two-Factor Authentication', `Two-factor authentication has been ${status}.`);
  };

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/lightweight-login');
      addNotification('success', 'Logged Out', 'You have been successfully logged out.');
    } catch (error) {
      addNotification('error', 'Logout Error', 'Failed to log out properly.');
    }
  };

  // Template Management Functions - now using React Query hooks
  // Templates are automatically loaded via usePromptTemplates hook

  const startEditingTemplate = (template: PromptTemplate) => {
    setEditingTemplate({ ...template });
    setIsEditingTemplate(true);
  };

  const cancelEditingTemplate = () => {
    setEditingTemplate(null);
    setIsEditingTemplate(false);
  };

  const saveTemplate = async () => {
    if (!editingTemplate) return;

    try {
      await updateTemplateMutation.mutateAsync({
        templateId: editingTemplate.id,
        template: {
          user_id: userId,
          name: editingTemplate.name,
          template_type: editingTemplate.type.toUpperCase() as any,
          system_prompt: editingTemplate.systemPrompt,
          template_format: editingTemplate.templateFormat,
          input_variables: {},
          is_default: editingTemplate.isDefault,
        },
      });

      setIsEditingTemplate(false);
      setEditingTemplate(null);
      addNotification('success', 'Template Saved', 'Template has been updated successfully.');
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to save template changes.';
      addNotification('error', 'Save Error', errorMessage);
    }
  };

  const setAsDefaultTemplate = async (template: PromptTemplate) => {
    try {
      await setDefaultTemplateMutation.mutateAsync(template.id);
      addNotification('success', 'Default Set', `${template.name} is now the default template.`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to set default template.';
      addNotification('error', 'Update Error', errorMessage);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-60 mx-auto mb-4"></div>
          <p className="text-gray-70">Loading profile...</p>
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="min-h-screen bg-gray-10 p-6">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-2xl font-semibold text-gray-100 mb-4">Profile Not Found</h1>
          <button
            onClick={() => navigate('/lightweight-dashboard')}
            className="btn-primary"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-10 p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="card p-6 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="w-16 h-16 bg-blue-60 rounded-full flex items-center justify-center">
                <UserIcon className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-semibold text-gray-100">{profile.name}</h1>
                <p className="text-gray-70">{profile.role} • {profile.department}</p>
                <p className="text-sm text-gray-60">Joined {profile.joined.toLocaleDateString()}</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="btn-secondary text-red-50 hover:bg-red-50 hover:text-white"
            >
              Sign Out
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="mb-6">
          <nav className="flex space-x-8">
            {[
              { id: 'profile', name: 'Profile', icon: UserIcon },
              { id: 'preferences', name: 'Preferences', icon: CogIcon },
              { id: 'ai', name: 'AI Preferences', icon: CpuChipIcon },
              { id: 'security', name: 'Security', icon: ShieldCheckIcon },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 px-3 py-2 text-sm font-medium rounded-md ${
                  activeTab === tab.id
                    ? 'bg-blue-60 text-white'
                    : 'text-gray-70 hover:text-gray-100 hover:bg-gray-20'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                <span>{tab.name}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === 'profile' && (
          <div className="card p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-gray-100">Profile Information</h2>
              {!isEditing ? (
                <button
                  onClick={() => setIsEditing(true)}
                  className="btn-secondary flex items-center space-x-2"
                >
                  <PencilIcon className="w-4 h-4" />
                  <span>Edit</span>
                </button>
              ) : (
                <div className="flex space-x-2">
                  <button
                    onClick={handleSaveProfile}
                    className="btn-primary flex items-center space-x-2"
                  >
                    <CheckIcon className="w-4 h-4" />
                    <span>Save</span>
                  </button>
                  <button
                    onClick={handleCancelEdit}
                    className="btn-secondary flex items-center space-x-2"
                  >
                    <XMarkIcon className="w-4 h-4" />
                    <span>Cancel</span>
                  </button>
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-100 mb-2">Full Name</label>
                {isEditing ? (
                  <input
                    type="text"
                    value={editForm.name}
                    onChange={(e) => setEditForm(prev => ({ ...prev, name: e.target.value }))}
                    className="input-field w-full"
                  />
                ) : (
                  <p className="text-gray-70 p-3 bg-gray-10 rounded-md">{profile.name}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-100 mb-2">Email</label>
                <p className="text-gray-70 p-3 bg-gray-10 rounded-md">{profile.email}</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-100 mb-2">Role</label>
                <p className="text-gray-70 p-3 bg-gray-10 rounded-md">{profile.role}</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-100 mb-2">Department</label>
                {isEditing ? (
                  <input
                    type="text"
                    value={editForm.department}
                    onChange={(e) => setEditForm(prev => ({ ...prev, department: e.target.value }))}
                    className="input-field w-full"
                  />
                ) : (
                  <p className="text-gray-70 p-3 bg-gray-10 rounded-md">{profile.department}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-100 mb-2">Last Login</label>
                <p className="text-gray-70 p-3 bg-gray-10 rounded-md">{profile.lastLogin.toLocaleString()}</p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'preferences' && (
          <div className="space-y-6">
            {/* Notifications */}
            <div className="card p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center space-x-2">
                <BellIcon className="w-5 h-5" />
                <span>Notifications</span>
              </h3>
              <div className="space-y-4">
                {Object.entries(profile.preferences.notifications).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between">
                    <label className="text-sm font-medium text-gray-100 capitalize">
                      {key} Notifications
                    </label>
                    <input
                      type="checkbox"
                      checked={value}
                      onChange={(e) => handlePreferenceChange('notifications', key, e.target.checked)}
                      className="rounded border-gray-40"
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* Display Settings */}
            <div className="card p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-4">Display Settings</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-gray-100">Theme</label>
                  <select
                    value={profile.preferences.theme}
                    onChange={(e) => handlePreferenceChange('theme', '', e.target.value)}
                    className="input-field w-32"
                  >
                    <option value="light">Light</option>
                    <option value="dark">Dark</option>
                    <option value="system">System</option>
                  </select>
                </div>

                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-gray-100">Language</label>
                  <select
                    value={profile.preferences.language}
                    onChange={(e) => handlePreferenceChange('language', '', e.target.value)}
                    className="input-field w-32"
                  >
                    <option value="en">English</option>
                    <option value="es">Español</option>
                    <option value="fr">Français</option>
                  </select>
                </div>

                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-gray-100">Timezone</label>
                  <select
                    value={profile.preferences.timezone}
                    onChange={(e) => handlePreferenceChange('timezone', '', e.target.value)}
                    className="input-field w-32"
                  >
                    <option value="UTC-8">UTC-8</option>
                    <option value="UTC-5">UTC-5</option>
                    <option value="UTC+0">UTC+0</option>
                    <option value="UTC+1">UTC+1</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'ai' && (
          <div className="space-y-6">
            {/* LLM Provider */}
            <div className="card p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center space-x-2">
                <CpuChipIcon className="w-5 h-5" />
                <span>LLM Provider</span>
              </h3>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-100">{profile.aiPreferences.currentProvider.name}</p>
                  <p className="text-xs text-gray-60">{profile.aiPreferences.currentProvider.description}</p>
                </div>
                <button
                  onClick={() => setShowProviderModal(true)}
                  className="btn-secondary"
                >
                  Configure Provider
                </button>
              </div>
            </div>

            {/* LLM Parameters */}
            <div className="card p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center space-x-2">
                <AdjustmentsHorizontalIcon className="w-5 h-5" />
                <span>LLM Parameters</span>
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
                <div>
                  <p className="text-sm text-gray-70">Temperature</p>
                  <p className="font-medium text-gray-100">{profile.aiPreferences.llmParameters.temperature}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-70">Max Tokens</p>
                  <p className="font-medium text-gray-100">{profile.aiPreferences.llmParameters.maxTokens}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-70">Top P</p>
                  <p className="font-medium text-gray-100">{profile.aiPreferences.llmParameters.topP}</p>
                </div>
              </div>
              <button
                onClick={() => setShowParametersModal(true)}
                className="btn-secondary"
              >
                Adjust Parameters
              </button>
            </div>

            {/* Prompt Templates */}
            <div className="card p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center space-x-2">
                <DocumentTextIcon className="w-5 h-5" />
                <span>Prompt Templates</span>
              </h3>
              <div className="space-y-3 mb-4">
                {templatesLoading ? (
                  <div className="space-y-2">
                    <Skeleton variant="rounded" height="h-16" />
                    <Skeleton variant="rounded" height="h-16" />
                    <Skeleton variant="rounded" height="h-16" width="3/4" />
                  </div>
                ) : templatesError ? (
                  <div className="p-4 bg-red-10 border border-red-20 rounded-lg flex items-start space-x-2">
                    <ExclamationCircleIcon className="w-5 h-5 text-red-50 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-red-50 mb-1">Failed to load templates</p>
                      <p className="text-xs text-red-60">{templatesError.message}</p>
                    </div>
                  </div>
                ) : allTemplates.length === 0 ? (
                  <div className="p-4 bg-gray-10 rounded-lg text-center">
                    <p className="text-sm text-gray-60">No templates found</p>
                  </div>
                ) : (
                  allTemplates.map((template) => (
                    <div key={template.id} className="flex items-center justify-between p-3 bg-gray-10 rounded-md">
                      <div>
                        <p className="text-sm font-medium text-gray-100">{template.name}</p>
                        <p className="text-xs text-gray-60 capitalize">{template.type.replace('_', ' ')}</p>
                      </div>
                      {template.isDefault && (
                        <span className="text-xs bg-blue-60 text-white px-2 py-1 rounded">Default</span>
                      )}
                    </div>
                  ))
                )}
              </div>
              <button
                onClick={() => {
                  setShowTemplatesModal(true);
                  // Templates auto-load via React Query
                }}
                className="btn-secondary"
              >
                Manage Templates
              </button>
            </div>

            {/* Pipeline Configuration */}
            <div className="card p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center space-x-2">
                <ShareIcon className="w-5 h-5" />
                <span>Pipeline Configuration</span>
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <p className="text-sm text-gray-70">Pipeline Name</p>
                  <p className="font-medium text-gray-100">{profile.aiPreferences.pipelineConfig.name}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-70">Model</p>
                  <p className="font-medium text-gray-100">{profile.aiPreferences.pipelineConfig.model}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-70">Embedding Model</p>
                  <p className="font-medium text-gray-100">{profile.aiPreferences.pipelineConfig.embeddingModel}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-70">Retrieval Limit</p>
                  <p className="font-medium text-gray-100">{profile.aiPreferences.pipelineConfig.retrievalLimit}</p>
                </div>
              </div>
              <button
                onClick={() => setShowPipelineModal(true)}
                className="btn-secondary"
              >
                Configure Pipeline
              </button>
            </div>
          </div>
        )}

        {activeTab === 'security' && (
          <div className="space-y-6">
            {/* Password */}
            <div className="card p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center space-x-2">
                <KeyIcon className="w-5 h-5" />
                <span>Password</span>
              </h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-100">Password</p>
                    <p className="text-xs text-gray-60">
                      Last changed: {profile.security.lastPasswordChange.toLocaleDateString()}
                    </p>
                  </div>
                  <button
                    onClick={() => setShowPasswordModal(true)}
                    className="btn-secondary"
                  >
                    Change Password
                  </button>
                </div>
              </div>
            </div>

            {/* Two-Factor Authentication */}
            <div className="card p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-4">Two-Factor Authentication</h3>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-100">Status</p>
                  <p className="text-xs text-gray-60">
                    {profile.security.twoFactorEnabled ? 'Enabled' : 'Disabled'}
                  </p>
                </div>
                <button
                  onClick={toggleTwoFactor}
                  className={`btn-secondary ${
                    profile.security.twoFactorEnabled
                      ? 'text-red-50 hover:bg-red-50 hover:text-white'
                      : 'text-green-50 hover:bg-green-50 hover:text-white'
                  }`}
                >
                  {profile.security.twoFactorEnabled ? 'Disable' : 'Enable'}
                </button>
              </div>
            </div>

            {/* Session Settings */}
            <div className="card p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-4">Session Settings</h3>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-100">Session Timeout</p>
                  <p className="text-xs text-gray-60">{profile.security.sessionTimeout} hours</p>
                </div>
                <select
                  value={profile.security.sessionTimeout}
                  onChange={(e) => {
                    setProfile(prev => prev ? {
                      ...prev,
                      security: { ...prev.security, sessionTimeout: parseInt(e.target.value) },
                    } : null);
                    addNotification('success', 'Settings Updated', 'Session timeout has been updated.');
                  }}
                  className="input-field w-24"
                >
                  <option value={1}>1h</option>
                  <option value={4}>4h</option>
                  <option value={8}>8h</option>
                  <option value={24}>24h</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* Password Change Modal */}
        {showPasswordModal && (
          <div className="fixed inset-0 bg-gray-100 bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-100">Change Password</h2>
                <button
                  onClick={() => setShowPasswordModal(false)}
                  className="text-gray-60 hover:text-gray-100"
                >
                  <XMarkIcon className="w-6 h-6" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-100 mb-2">
                    Current Password
                  </label>
                  <div className="relative">
                    <input
                      type={passwordForm.showCurrent ? 'text' : 'password'}
                      value={passwordForm.currentPassword}
                      onChange={(e) => setPasswordForm(prev => ({ ...prev, currentPassword: e.target.value }))}
                      className="input-field w-full pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setPasswordForm(prev => ({ ...prev, showCurrent: !prev.showCurrent }))}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center"
                    >
                      {passwordForm.showCurrent ? (
                        <EyeSlashIcon className="w-4 h-4 text-gray-60" />
                      ) : (
                        <EyeIcon className="w-4 h-4 text-gray-60" />
                      )}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-100 mb-2">
                    New Password
                  </label>
                  <div className="relative">
                    <input
                      type={passwordForm.showNew ? 'text' : 'password'}
                      value={passwordForm.newPassword}
                      onChange={(e) => setPasswordForm(prev => ({ ...prev, newPassword: e.target.value }))}
                      className="input-field w-full pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setPasswordForm(prev => ({ ...prev, showNew: !prev.showNew }))}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center"
                    >
                      {passwordForm.showNew ? (
                        <EyeSlashIcon className="w-4 h-4 text-gray-60" />
                      ) : (
                        <EyeIcon className="w-4 h-4 text-gray-60" />
                      )}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-100 mb-2">
                    Confirm New Password
                  </label>
                  <div className="relative">
                    <input
                      type={passwordForm.showConfirm ? 'text' : 'password'}
                      value={passwordForm.confirmPassword}
                      onChange={(e) => setPasswordForm(prev => ({ ...prev, confirmPassword: e.target.value }))}
                      className="input-field w-full pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setPasswordForm(prev => ({ ...prev, showConfirm: !prev.showConfirm }))}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center"
                    >
                      {passwordForm.showConfirm ? (
                        <EyeSlashIcon className="w-4 h-4 text-gray-60" />
                      ) : (
                        <EyeIcon className="w-4 h-4 text-gray-60" />
                      )}
                    </button>
                  </div>
                </div>
              </div>

              <div className="flex justify-end space-x-3 mt-6">
                <button
                  onClick={() => setShowPasswordModal(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  onClick={handlePasswordChange}
                  className="btn-primary"
                >
                  Change Password
                </button>
              </div>
            </div>
          </div>
        )}

        {/* LLM Provider Modal */}
        {showProviderModal && (
          <div className="fixed inset-0 bg-gray-100 bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg max-w-2xl w-full max-h-screen overflow-y-auto">
              <div className="p-6 border-b border-gray-20">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-semibold text-gray-100">Configure LLM Provider</h2>
                  <button
                    onClick={() => setShowProviderModal(false)}
                    className="text-gray-60 hover:text-gray-100"
                  >
                    <XMarkIcon className="w-6 h-6" />
                  </button>
                </div>
              </div>
              <div className="p-6">
                <div className="space-y-4">
                  {profile.aiPreferences.availableProviders.map((provider) => (
                    <div
                      key={provider.id}
                      className={`p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                        provider.id === profile.aiPreferences.currentProvider.id
                          ? 'border-blue-60 bg-blue-10'
                          : 'border-gray-20 hover:border-gray-30'
                      }`}
                      onClick={() => {
                        setProfile(prev => prev ? {
                          ...prev,
                          aiPreferences: {
                            ...prev.aiPreferences,
                            currentProvider: provider,
                          },
                        } : null);
                      }}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="font-medium text-gray-100">{provider.name}</h3>
                          <p className="text-sm text-gray-70">{provider.description}</p>
                        </div>
                        {provider.id === profile.aiPreferences.currentProvider.id && (
                          <CheckIcon className="w-5 h-5 text-blue-60" />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="flex justify-end space-x-3 px-6 py-4 border-t border-gray-20">
                <button
                  onClick={() => setShowProviderModal(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    setShowProviderModal(false);
                    addNotification('success', 'Provider Updated', 'LLM provider has been updated successfully.');
                  }}
                  className="btn-primary"
                >
                  Save Changes
                </button>
              </div>
            </div>
          </div>
        )}

        {/* LLM Parameters Modal */}
        {showParametersModal && (
          <div className="fixed inset-0 bg-gray-100 bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg max-w-2xl w-full max-h-screen overflow-y-auto">
              <div className="p-6 border-b border-gray-20">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-semibold text-gray-100">LLM Parameters</h2>
                  <button
                    onClick={() => setShowParametersModal(false)}
                    className="text-gray-60 hover:text-gray-100"
                  >
                    <XMarkIcon className="w-6 h-6" />
                  </button>
                </div>
              </div>
              <div className="p-6 space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-100 mb-2">
                    Temperature: {profile.aiPreferences.llmParameters.temperature}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="2"
                    step="0.1"
                    value={profile.aiPreferences.llmParameters.temperature}
                    onChange={(e) => {
                      setProfile(prev => prev ? {
                        ...prev,
                        aiPreferences: {
                          ...prev.aiPreferences,
                          llmParameters: {
                            ...prev.aiPreferences.llmParameters,
                            temperature: parseFloat(e.target.value),
                          },
                        },
                      } : null);
                    }}
                    className="w-full"
                  />
                  <p className="text-xs text-gray-60 mt-1">Controls randomness in responses (0.0 = deterministic, 2.0 = very random)</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-100 mb-2">Max Tokens</label>
                  <input
                    type="number"
                    min="1"
                    max="8192"
                    value={profile.aiPreferences.llmParameters.maxTokens}
                    onChange={(e) => {
                      setProfile(prev => prev ? {
                        ...prev,
                        aiPreferences: {
                          ...prev.aiPreferences,
                          llmParameters: {
                            ...prev.aiPreferences.llmParameters,
                            maxTokens: parseInt(e.target.value),
                          },
                        },
                      } : null);
                    }}
                    className="input-field w-full"
                  />
                  <p className="text-xs text-gray-60 mt-1">Maximum number of tokens to generate</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-100 mb-2">
                    Top P: {profile.aiPreferences.llmParameters.topP}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={profile.aiPreferences.llmParameters.topP}
                    onChange={(e) => {
                      setProfile(prev => prev ? {
                        ...prev,
                        aiPreferences: {
                          ...prev.aiPreferences,
                          llmParameters: {
                            ...prev.aiPreferences.llmParameters,
                            topP: parseFloat(e.target.value),
                          },
                        },
                      } : null);
                    }}
                    className="w-full"
                  />
                  <p className="text-xs text-gray-60 mt-1">Nucleus sampling parameter</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-100 mb-2">Top K</label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={profile.aiPreferences.llmParameters.topK}
                    onChange={(e) => {
                      setProfile(prev => prev ? {
                        ...prev,
                        aiPreferences: {
                          ...prev.aiPreferences,
                          llmParameters: {
                            ...prev.aiPreferences.llmParameters,
                            topK: parseInt(e.target.value),
                          },
                        },
                      } : null);
                    }}
                    className="input-field w-full"
                  />
                  <p className="text-xs text-gray-60 mt-1">Limits vocabulary to top K tokens</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-100 mb-2">
                    Repetition Penalty: {profile.aiPreferences.llmParameters.repetitionPenalty}
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="2"
                    step="0.1"
                    value={profile.aiPreferences.llmParameters.repetitionPenalty}
                    onChange={(e) => {
                      setProfile(prev => prev ? {
                        ...prev,
                        aiPreferences: {
                          ...prev.aiPreferences,
                          llmParameters: {
                            ...prev.aiPreferences.llmParameters,
                            repetitionPenalty: parseFloat(e.target.value),
                          },
                        },
                      } : null);
                    }}
                    className="w-full"
                  />
                  <p className="text-xs text-gray-60 mt-1">Penalty for repeating tokens</p>
                </div>
              </div>
              <div className="flex justify-end space-x-3 px-6 py-4 border-t border-gray-20">
                <button
                  onClick={() => setShowParametersModal(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    setShowParametersModal(false);
                    addNotification('success', 'Parameters Updated', 'LLM parameters have been updated successfully.');
                  }}
                  className="btn-primary"
                >
                  Save Parameters
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Enhanced Prompt Templates Modal */}
        {showTemplatesModal && (
          <div className="fixed inset-0 bg-gray-100 bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg max-w-6xl w-full max-h-screen overflow-y-auto">
              {/* Header */}
              <div className="p-6 border-b border-gray-20">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-semibold text-gray-100">Template Manager</h2>
                  <button
                    onClick={() => {
                      setShowTemplatesModal(false);
                      setIsEditingTemplate(false);
                      setEditingTemplate(null);
                      setSelectedTemplateIndex(0);
                    }}
                    className="text-gray-60 hover:text-gray-100"
                  >
                    <XMarkIcon className="w-6 h-6" />
                  </button>
                </div>
              </div>

              {templatesLoading ? (
                <div className="p-12 space-y-4">
                  <Skeleton variant="rounded" height="h-12" />
                  <Skeleton variant="rounded" height="h-12" />
                  <Skeleton variant="rounded" height="h-12" />
                </div>
              ) : templatesError ? (
                <div className="p-12 text-center">
                  <div className="flex flex-col items-center space-y-4">
                    <ExclamationCircleIcon className="w-12 h-12 text-red-50" />
                    <div>
                      <p className="text-lg font-medium text-gray-100 mb-2">Failed to load templates</p>
                      <p className="text-sm text-gray-70 mb-4">{templatesError.message}</p>
                      <button
                        onClick={() => window.location.reload()}
                        className="btn-secondary"
                      >
                        Reload Page
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex h-96">
                  {/* Template List Sidebar */}
                  <div className="w-1/3 border-r border-gray-20 p-4 overflow-y-auto">
                    <h3 className="font-medium text-gray-100 mb-4">All Templates ({allTemplates.length})</h3>
                    <div className="space-y-2">
                      {allTemplates.map((template, index) => (
                        <div
                          key={template.id}
                          onClick={() => {
                            setSelectedTemplateIndex(index);
                            setIsEditingTemplate(false);
                            setEditingTemplate(null);
                          }}
                          className={`p-3 rounded-lg cursor-pointer transition-colors ${
                            selectedTemplateIndex === index
                              ? 'bg-blue-60 text-white'
                              : 'bg-gray-10 hover:bg-gray-20'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div>
                              <p className={`text-sm font-medium ${
                                selectedTemplateIndex === index ? 'text-white' : 'text-gray-100'
                              }`}>
                                {template.name}
                              </p>
                              <p className={`text-xs capitalize ${
                                selectedTemplateIndex === index ? 'text-blue-20' : 'text-gray-60'
                              }`}>
                                {template.type.replace('_', ' ')}
                              </p>
                            </div>
                            {template.isDefault && (
                              <StarIcon className={`w-4 h-4 ${
                                selectedTemplateIndex === index ? 'text-yellow-20' : 'text-yellow-40'
                              }`} />
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Template Details Panel */}
                  <div className="flex-1 p-6">
                    {allTemplates.length > 0 && (
                      <>
                        {/* Navigation and Actions */}
                        <div className="flex items-center justify-between mb-6">
                          <div className="flex items-center space-x-2">
                            <button
                              onClick={() => setSelectedTemplateIndex(Math.max(0, selectedTemplateIndex - 1))}
                              disabled={selectedTemplateIndex === 0}
                              className="p-1 rounded hover:bg-gray-20 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              <ChevronLeftIcon className="w-5 h-5 text-gray-60" />
                            </button>
                            <span className="text-sm text-gray-70">
                              {selectedTemplateIndex + 1} of {allTemplates.length}
                            </span>
                            <button
                              onClick={() => setSelectedTemplateIndex(Math.min(allTemplates.length - 1, selectedTemplateIndex + 1))}
                              disabled={selectedTemplateIndex === allTemplates.length - 1}
                              className="p-1 rounded hover:bg-gray-20 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              <ChevronRightIcon className="w-5 h-5 text-gray-60" />
                            </button>
                          </div>
                          <div className="flex space-x-2">
                            {!allTemplates[selectedTemplateIndex]?.isDefault && (
                              <button
                                onClick={() => setAsDefaultTemplate(allTemplates[selectedTemplateIndex])}
                                className="btn-secondary text-sm flex items-center space-x-1"
                              >
                                <StarIcon className="w-4 h-4" />
                                <span>Set as Default</span>
                              </button>
                            )}
                            {!isEditingTemplate ? (
                              <button
                                onClick={() => startEditingTemplate(allTemplates[selectedTemplateIndex])}
                                className="btn-primary text-sm flex items-center space-x-1"
                              >
                                <PencilIcon className="w-4 h-4" />
                                <span>Edit</span>
                              </button>
                            ) : (
                              <>
                                <button
                                  onClick={cancelEditingTemplate}
                                  className="btn-secondary text-sm flex items-center space-x-1"
                                >
                                  <XMarkIcon className="w-4 h-4" />
                                  <span>Cancel</span>
                                </button>
                                <button
                                  onClick={saveTemplate}
                                  className="btn-primary text-sm flex items-center space-x-1"
                                >
                                  <CheckIcon className="w-4 h-4" />
                                  <span>Save</span>
                                </button>
                              </>
                            )}
                          </div>
                        </div>

                        {/* Template Content */}
                        <div className="space-y-6">
                          {/* Header */}
                          <div className="flex items-start justify-between">
                            <div>
                              <h3 className="text-lg font-medium text-gray-100">
                                {allTemplates[selectedTemplateIndex]?.name}
                              </h3>
                              <p className="text-sm text-gray-60 capitalize">
                                {allTemplates[selectedTemplateIndex]?.type.replace('_', ' ')}
                              </p>
                            </div>
                            {allTemplates[selectedTemplateIndex]?.isDefault && (
                              <div className="flex items-center space-x-1 bg-yellow-50 text-yellow-100 px-2 py-1 rounded-full text-xs">
                                <StarIcon className="w-3 h-3" />
                                <span>Current Default</span>
                              </div>
                            )}
                          </div>

                          {/* System Prompt */}
                          <div>
                            <label className="block text-sm font-medium text-gray-100 mb-2">System Prompt</label>
                            {isEditingTemplate && editingTemplate ? (
                              <textarea
                                value={editingTemplate.systemPrompt}
                                onChange={(e) => setEditingTemplate(prev => prev ? { ...prev, systemPrompt: e.target.value } : null)}
                                rows={4}
                                className="input-field w-full resize-none"
                                placeholder="Enter system prompt..."
                              />
                            ) : (
                              <div className="p-4 bg-gray-10 rounded-lg text-sm text-gray-70 min-h-[100px]">
                                {allTemplates[selectedTemplateIndex]?.systemPrompt}
                              </div>
                            )}
                          </div>

                          {/* Template Format */}
                          <div>
                            <label className="block text-sm font-medium text-gray-100 mb-2">Template Format</label>
                            {isEditingTemplate && editingTemplate ? (
                              <textarea
                                value={editingTemplate.templateFormat}
                                onChange={(e) => setEditingTemplate(prev => prev ? { ...prev, templateFormat: e.target.value } : null)}
                                rows={3}
                                className="input-field w-full font-mono text-sm resize-none"
                                placeholder="Enter template format with variables like {context}, {question}..."
                              />
                            ) : (
                              <div className="p-4 bg-gray-10 rounded-lg text-sm text-gray-70 font-mono min-h-[80px]">
                                {allTemplates[selectedTemplateIndex]?.templateFormat}
                              </div>
                            )}
                          </div>

                          {/* Help Text */}
                          <div className="bg-blue-10 p-4 rounded-lg">
                            <h4 className="text-sm font-medium text-blue-70 mb-1">Template Variables</h4>
                            <p className="text-xs text-blue-60">
                              Use variables like <code className="bg-blue-20 px-1 rounded">{'{context}'}</code>, <code className="bg-blue-20 px-1 rounded">{'{question}'}</code>, and <code className="bg-blue-20 px-1 rounded">{'{num_questions}'}</code> in your templates.
                            </p>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              )}

              {/* Footer */}
              <div className="flex justify-between items-center px-6 py-4 border-t border-gray-20">
                <div className="text-sm text-gray-60">
                  {allTemplates.length > 0 && (
                    <>Total: {allTemplates.length} templates • RAG: {allTemplates.filter(t => t.type === 'rag_query').length} • Question Gen: {allTemplates.filter(t => t.type === 'question_generation').length}</>
                  )}
                </div>
                <button
                  onClick={() => {
                    setShowTemplatesModal(false);
                    setIsEditingTemplate(false);
                    setEditingTemplate(null);
                    setSelectedTemplateIndex(0);
                  }}
                  className="btn-primary"
                >
                  Done
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Pipeline Configuration Modal */}
        {showPipelineModal && (
          <div className="fixed inset-0 bg-gray-100 bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg max-w-2xl w-full max-h-screen overflow-y-auto">
              <div className="p-6 border-b border-gray-20">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-semibold text-gray-100">Pipeline Configuration</h2>
                  <button
                    onClick={() => setShowPipelineModal(false)}
                    className="text-gray-60 hover:text-gray-100"
                  >
                    <XMarkIcon className="w-6 h-6" />
                  </button>
                </div>
              </div>
              <div className="p-6 space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-100 mb-2">Pipeline Name</label>
                  <input
                    type="text"
                    value={profile.aiPreferences.pipelineConfig.name}
                    onChange={(e) => {
                      setProfile(prev => prev ? {
                        ...prev,
                        aiPreferences: {
                          ...prev.aiPreferences,
                          pipelineConfig: {
                            ...prev.aiPreferences.pipelineConfig,
                            name: e.target.value,
                          },
                        },
                      } : null);
                    }}
                    className="input-field w-full"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-100 mb-2">LLM Model</label>
                  <select
                    value={profile.aiPreferences.pipelineConfig.model}
                    onChange={(e) => {
                      setProfile(prev => prev ? {
                        ...prev,
                        aiPreferences: {
                          ...prev.aiPreferences,
                          pipelineConfig: {
                            ...prev.aiPreferences.pipelineConfig,
                            model: e.target.value,
                          },
                        },
                      } : null);
                    }}
                    className="input-field w-full"
                  >
                    <option value="granite-13b-chat-v2">Granite 13B Chat v2</option>
                    <option value="granite-20b-multilingual">Granite 20B Multilingual</option>
                    <option value="llama-2-70b-chat">Llama 2 70B Chat</option>
                    <option value="gpt-4">GPT-4</option>
                    <option value="claude-3-sonnet">Claude 3 Sonnet</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-100 mb-2">Embedding Model</label>
                  <select
                    value={profile.aiPreferences.pipelineConfig.embeddingModel}
                    onChange={(e) => {
                      setProfile(prev => prev ? {
                        ...prev,
                        aiPreferences: {
                          ...prev.aiPreferences,
                          pipelineConfig: {
                            ...prev.aiPreferences.pipelineConfig,
                            embeddingModel: e.target.value,
                          },
                        },
                      } : null);
                    }}
                    className="input-field w-full"
                  >
                    <option value="bge-large-en">BGE Large EN</option>
                    <option value="bge-base-en">BGE Base EN</option>
                    <option value="sentence-transformers/all-MiniLM-L6-v2">All-MiniLM-L6-v2</option>
                    <option value="text-embedding-ada-002">OpenAI Ada 002</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-100 mb-2">Retrieval Limit</label>
                  <input
                    type="number"
                    min="1"
                    max="20"
                    value={profile.aiPreferences.pipelineConfig.retrievalLimit}
                    onChange={(e) => {
                      setProfile(prev => prev ? {
                        ...prev,
                        aiPreferences: {
                          ...prev.aiPreferences,
                          pipelineConfig: {
                            ...prev.aiPreferences.pipelineConfig,
                            retrievalLimit: parseInt(e.target.value),
                          },
                        },
                      } : null);
                    }}
                    className="input-field w-full"
                  />
                  <p className="text-xs text-gray-60 mt-1">Number of documents to retrieve for context</p>
                </div>
              </div>
              <div className="flex justify-end space-x-3 px-6 py-4 border-t border-gray-20">
                <button
                  onClick={() => setShowPipelineModal(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    setShowPipelineModal(false);
                    addNotification('success', 'Pipeline Updated', 'Pipeline configuration has been updated successfully.');
                  }}
                  className="btn-primary"
                >
                  Save Configuration
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default LightweightUserProfile;
