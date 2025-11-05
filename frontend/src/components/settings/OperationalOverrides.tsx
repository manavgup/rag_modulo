import React, { useState } from 'react';
import {
  PlusIcon,
  XMarkIcon,
  CheckIcon,
  PencilIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import { useNotification } from '../../contexts/NotificationContext';
import {
  useGlobalConfigs,
  useUserConfigs,
  useCollectionConfigs,
  useCreateConfig,
  useUpdateConfig,
  useToggleConfig,
  useDeleteConfig,
} from '../../hooks/useRuntimeConfig';
import {
  ConfigScope,
  ConfigCategory,
  ConfigValueType,
  RuntimeConfigInput,
  RuntimeConfigOutput,
} from '../../api/runtimeConfigApi';

interface OperationalOverridesProps {
  userId?: string;
  collectionId?: string;
}

const OperationalOverrides: React.FC<OperationalOverridesProps> = ({ userId, collectionId }) => {
  const { addNotification } = useNotification();
  const [activeScope, setActiveScope] = useState<ConfigScope>('GLOBAL');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  // Query hooks
  const { data: globalConfigs, isLoading: globalLoading } = useGlobalConfigs();
  const { data: userConfigs, isLoading: userLoading } = useUserConfigs(userId || '');
  const { data: collectionConfigs, isLoading: collectionLoading } = useCollectionConfigs(collectionId || '');

  // Mutation hooks
  const createConfig = useCreateConfig();
  const updateConfig = useUpdateConfig();
  const toggleConfig = useToggleConfig();
  const deleteConfig = useDeleteConfig();

  // Form state
  const [formData, setFormData] = useState<Partial<RuntimeConfigInput>>({
    scope: 'GLOBAL',
    category: 'SYSTEM',
    config_key: '',
    config_value: { value: '', type: 'str' },
    description: '',
  });

  const getConfigsByScope = () => {
    if (activeScope === 'GLOBAL') return globalConfigs || [];
    if (activeScope === 'USER') return userConfigs || [];
    if (activeScope === 'COLLECTION') return collectionConfigs || [];
    return [];
  };

  const isLoading = globalLoading || userLoading || collectionLoading;
  const configs = getConfigsByScope();

  const handleCreate = async () => {
    try {
      const input: RuntimeConfigInput = {
        scope: formData.scope!,
        category: formData.category!,
        config_key: formData.config_key!,
        config_value: formData.config_value!,
        description: formData.description,
      };

      if (formData.scope === 'USER' && userId) {
        input.user_id = userId;
      }
      if (formData.scope === 'COLLECTION' && collectionId) {
        input.collection_id = collectionId;
      }

      await createConfig.mutateAsync(input);
      addNotification('success', 'Override Created', 'Configuration override has been created successfully.');
      setShowCreateForm(false);
      resetForm();
    } catch (error) {
      addNotification('error', 'Create Error', 'Failed to create configuration override.');
    }
  };

  const handleUpdate = async (id: string, data: Partial<RuntimeConfigInput>) => {
    try {
      await updateConfig.mutateAsync({ id, data });
      addNotification('success', 'Override Updated', 'Configuration override has been updated successfully.');
      setEditingId(null);
    } catch (error) {
      addNotification('error', 'Update Error', 'Failed to update configuration override.');
    }
  };

  const handleToggle = async (id: string, isActive: boolean) => {
    try {
      await toggleConfig.mutateAsync({ id, isActive: !isActive });
      addNotification(
        'success',
        'Override Toggled',
        `Override has been ${!isActive ? 'enabled' : 'disabled'}.`
      );
    } catch (error) {
      addNotification('error', 'Toggle Error', 'Failed to toggle configuration override.');
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this override? This cannot be undone.')) {
      return;
    }

    try {
      await deleteConfig.mutateAsync(id);
      addNotification('success', 'Override Deleted', 'Configuration override has been deleted successfully.');
    } catch (error) {
      addNotification('error', 'Delete Error', 'Failed to delete configuration override.');
    }
  };

  const resetForm = () => {
    setFormData({
      scope: activeScope,
      category: 'SYSTEM',
      config_key: '',
      config_value: { value: '', type: 'str' },
      description: '',
    });
  };

  const parseValue = (config: RuntimeConfigOutput) => {
    const { value, type } = config.config_value;
    if (type === 'bool') return value ? 'true' : 'false';
    if (type === 'list' || type === 'dict') return JSON.stringify(value, null, 2);
    return String(value);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-100">Operational Overrides</h2>
            <p className="text-gray-70 text-sm mt-1">
              Feature flags, emergency overrides, and A/B testing configurations. Changes take effect immediately.
            </p>
          </div>
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="btn-primary flex items-center space-x-2"
          >
            {showCreateForm ? (
              <>
                <XMarkIcon className="w-4 h-4" />
                <span>Cancel</span>
              </>
            ) : (
              <>
                <PlusIcon className="w-4 h-4" />
                <span>Create Override</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Create Form */}
      {showCreateForm && (
        <div className="card p-6">
          <h3 className="text-md font-semibold text-gray-100 mb-4">Create New Override</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-100 mb-2">Scope</label>
              <select
                value={formData.scope}
                onChange={(e) => setFormData({ ...formData, scope: e.target.value as ConfigScope })}
                className="input-field w-full"
              >
                <option value="GLOBAL">Global</option>
                <option value="USER">User</option>
                <option value="COLLECTION">Collection</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-100 mb-2">Category</label>
              <select
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value as ConfigCategory })}
                className="input-field w-full"
              >
                <option value="SYSTEM">System</option>
                <option value="OVERRIDE">Override</option>
                <option value="EXPERIMENT">Experiment</option>
                <option value="PERFORMANCE">Performance</option>
                <option value="LLM">LLM</option>
                <option value="CHUNKING">Chunking</option>
                <option value="RETRIEVAL">Retrieval</option>
                <option value="EMBEDDING">Embedding</option>
                <option value="PIPELINE">Pipeline</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-100 mb-2">Config Key</label>
              <input
                type="text"
                value={formData.config_key}
                onChange={(e) => setFormData({ ...formData, config_key: e.target.value })}
                className="input-field w-full"
                placeholder="enable_new_feature"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-100 mb-2">Value Type</label>
              <select
                value={formData.config_value?.type}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    config_value: { ...formData.config_value!, type: e.target.value as ConfigValueType },
                  })
                }
                className="input-field w-full"
              >
                <option value="str">String</option>
                <option value="int">Integer</option>
                <option value="float">Float</option>
                <option value="bool">Boolean</option>
                <option value="list">List</option>
                <option value="dict">Dictionary</option>
              </select>
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-100 mb-2">Value</label>
              {formData.config_value?.type === 'bool' ? (
                <select
                  value={String(formData.config_value.value)}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      config_value: { ...formData.config_value!, value: e.target.value === 'true' },
                    })
                  }
                  className="input-field w-full"
                >
                  <option value="true">True</option>
                  <option value="false">False</option>
                </select>
              ) : (
                <input
                  type="text"
                  value={formData.config_value?.value || ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      config_value: { ...formData.config_value!, value: e.target.value },
                    })
                  }
                  className="input-field w-full"
                  placeholder={
                    formData.config_value?.type === 'list' || formData.config_value?.type === 'dict'
                      ? 'Enter valid JSON'
                      : 'Enter value'
                  }
                />
              )}
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-100 mb-2">Description (Optional)</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="input-field w-full"
                rows={2}
                placeholder="Describe the purpose of this override..."
              />
            </div>
          </div>

          <div className="flex justify-end space-x-3 mt-4">
            <button onClick={() => setShowCreateForm(false)} className="btn-secondary">
              Cancel
            </button>
            <button
              onClick={handleCreate}
              disabled={!formData.config_key || !formData.config_value?.value}
              className="btn-primary disabled:opacity-50"
            >
              Create Override
            </button>
          </div>
        </div>
      )}

      {/* Scope Tabs */}
      <div className="card p-4">
        <div className="flex space-x-2">
          <button
            onClick={() => setActiveScope('GLOBAL')}
            className={`px-4 py-2 text-sm font-medium rounded-md ${
              activeScope === 'GLOBAL'
                ? 'bg-blue-60 text-white'
                : 'text-gray-70 hover:text-gray-100 hover:bg-gray-20'
            }`}
          >
            Global
          </button>
          {userId && (
            <button
              onClick={() => setActiveScope('USER')}
              className={`px-4 py-2 text-sm font-medium rounded-md ${
                activeScope === 'USER'
                  ? 'bg-blue-60 text-white'
                  : 'text-gray-70 hover:text-gray-100 hover:bg-gray-20'
              }`}
            >
              User
            </button>
          )}
          {collectionId && (
            <button
              onClick={() => setActiveScope('COLLECTION')}
              className={`px-4 py-2 text-sm font-medium rounded-md ${
                activeScope === 'COLLECTION'
                  ? 'bg-blue-60 text-white'
                  : 'text-gray-70 hover:text-gray-100 hover:bg-gray-20'
              }`}
            >
              Collection
            </button>
          )}
        </div>
      </div>

      {/* Overrides Table */}
      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="p-6 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-60 mx-auto"></div>
            <p className="text-gray-70 mt-2">Loading overrides...</p>
          </div>
        ) : configs.length === 0 ? (
          <div className="p-6 text-center">
            <p className="text-gray-70">No overrides configured for this scope.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-30">
              <thead className="bg-gray-10">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-70 uppercase tracking-wider">
                    Key
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-70 uppercase tracking-wider">
                    Category
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-70 uppercase tracking-wider">
                    Value
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-70 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-70 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-30">
                {configs.map((config) => (
                  <tr key={config.id} className={!config.is_active ? 'opacity-50' : ''}>
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-gray-100">{config.config_key}</div>
                      {config.description && (
                        <div className="text-sm text-gray-70">{config.description}</div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-10 text-blue-70">
                        {config.category}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-100">
                        <code className="bg-gray-10 px-2 py-1 rounded">{parseValue(config)}</code>
                      </div>
                      <div className="text-xs text-gray-60 mt-1">Type: {config.config_value.type}</div>
                    </td>
                    <td className="px-6 py-4">
                      <button
                        onClick={() => handleToggle(config.id, config.is_active)}
                        className={`px-3 py-1 text-xs font-medium rounded-full ${
                          config.is_active
                            ? 'bg-green-10 text-green-70 hover:bg-green-20'
                            : 'bg-gray-20 text-gray-70 hover:bg-gray-30'
                        }`}
                      >
                        {config.is_active ? 'Active' : 'Inactive'}
                      </button>
                    </td>
                    <td className="px-6 py-4 text-sm font-medium space-x-2">
                      <button
                        onClick={() => handleDelete(config.id)}
                        className="text-red-50 hover:text-red-70"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default OperationalOverrides;
