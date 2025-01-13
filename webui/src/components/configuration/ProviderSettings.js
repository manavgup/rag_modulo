import React, { useState, useEffect } from 'react';
import {
  DataTable,
  Table,
  TableHead,
  TableRow,
  TableHeader,
  TableBody,
  TableCell,
  Button,
  Modal,
  TextInput,
  Form,
  Loading,
  InlineNotification,
  Tag,
  Toggle,
  PasswordInput,
  Link
} from '@carbon/react';
import { Add, Edit, TrashCan, View } from '@carbon/icons-react';
import { getFullApiUrl, API_ROUTES } from '../../config/config';
import { fetchWithAuthHeader } from '../../services/authService';
import { useAuth } from '../../contexts/AuthContext';

const ProviderSettings = () => {
  const { user } = useAuth();
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentProvider, setCurrentProvider] = useState(null);
  const [showSystemProviders, setShowSystemProviders] = useState(true);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    base_url: '',
    api_key: '',
    org_id: '',
    project_id: '',
    is_active: true
  });

  const getProvidersUrl = (providerId = '') => {
    if (!user?.uuid) {
      throw new Error('User not authenticated');
    }
    const baseUrl = API_ROUTES.PROVIDER_CONFIG.replace('{userId}', user.uuid);
    return providerId ? `${baseUrl}/${providerId}` : baseUrl;
  };

  const getProviderModelsUrl = (providerId) => {
    if (!user?.uuid) {
      throw new Error('User not authenticated');
    }
    return API_ROUTES.PROVIDER_MODELS
      .replace('{userId}', user.uuid)
      .replace('{providerId}', providerId);
  };

  useEffect(() => {
    if (user) {
      fetchData();
    }
  }, [user, showSystemProviders]);

  const fetchData = async () => {
    try {
      const [providersResponse, modelsResponse] = await Promise.all([
        fetchWithAuthHeader(
          `${getFullApiUrl(getProvidersUrl())}?${new URLSearchParams({
            include_system: showSystemProviders
          }).toString()}`
        ),
        fetchWithAuthHeader(
          `${getFullApiUrl(getProvidersUrl())}/models`
        )
      ]);

      const providersData = Array.isArray(providersResponse) ? providersResponse : [providersResponse];
      const modelsData = Array.isArray(modelsResponse) ? modelsResponse : [];

      // Enhance providers with their models
      const enhancedProviders = providersData.map(provider => ({
        ...provider,
        models: modelsData.filter(model => model.provider_id === provider.id)
      }));

      setProviders(enhancedProviders);
      setError(null);
    } catch (err) {
      setError('Failed to load LLM providers');
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const url = getFullApiUrl(getProvidersUrl());
      const method = currentProvider ? 'PUT' : 'POST';
      const path = currentProvider ? `${url}/${currentProvider.id}` : url;
      
      await fetchWithAuthHeader(path, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });
      
      await fetchData();
      setIsModalOpen(false);
      resetForm();
    } catch (err) {
      setError('Failed to save LLM provider');
      console.error('Error saving provider:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (providerId) => {
    if (!window.confirm('Are you sure you want to delete this provider?')) return;
    
    setLoading(true);
    try {
      await fetchWithAuthHeader(
        `${getFullApiUrl(getProvidersUrl())}/${providerId}`,
        { method: 'DELETE' }
      );
      await fetchData();
    } catch (err) {
      setError('Failed to delete provider');
      console.error('Error deleting provider:', err);
    } finally {
      setLoading(false);
    }
  };

  const openEditModal = (provider) => {
    setCurrentProvider(provider);
    setFormData({
      name: provider.name,
      base_url: provider.base_url,
      api_key: provider.api_key,
      org_id: provider.org_id || '',
      project_id: provider.project_id || '',
      is_active: provider.is_active
    });
    setIsModalOpen(true);
  };

  const resetForm = () => {
    setFormData({
      name: '',
      base_url: '',
      api_key: '',
      org_id: '',
      project_id: '',
      is_active: true
    });
    setCurrentProvider(null);
  };

  const headers = [
    { key: 'name', header: 'Name' },
    { key: 'base_url', header: 'Base URL' },
    { key: 'org_id', header: 'Organization ID' },
    { key: 'project_id', header: 'Project ID' },
    { key: 'type', header: 'Type' },
    { key: 'models', header: 'Models' },
    { key: 'status', header: 'Status' },
    { key: 'actions', header: 'Actions' }
  ];

  const getTableRows = () => {
    return providers.map(provider => ({
      ...provider,
      id: provider.id,
      type: provider.user_id ? 'User' : 'System',
      models: (
        <Link href="#" onClick={(e) => {
          e.preventDefault();
          // TODO: Add model details view
          console.log('View models for:', provider.name);
        }}>
          {provider.models?.length || 0} models <View size={16} style={{ verticalAlign: 'middle' }} />
        </Link>
      ),
      status: (
        <Tag type={provider.is_active ? 'green' : 'red'}>
          {provider.is_active ? 'Active' : 'Inactive'}
        </Tag>
      ),
      actions: (
        <>
          {provider.user_id && (
            <>
              <Button
                kind="ghost"
                size="sm"
                renderIcon={Edit}
                iconDescription="Edit"
                onClick={() => openEditModal(provider)}
                style={{ marginRight: '0.5rem' }}
              />
              <Button
                kind="danger--ghost"
                size="sm"
                renderIcon={TrashCan}
                iconDescription="Delete"
                onClick={() => handleDelete(provider.id)}
              />
            </>
          )}
        </>
      )
    }));
  };

  if (!user) return <Loading description="Please log in..." />;
  if (loading) return <Loading description="Loading LLM providers..." />;

  return (
    <div className="provider-settings">
      {error && (
        <InlineNotification
          kind="error"
          title="Error"
          subtitle={error}
          onClose={() => setError(null)}
        />
      )}

      <div className="provider-settings-header" style={{ margin: '1rem 0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Button
          renderIcon={Add}
          onClick={() => {
            resetForm();
            setIsModalOpen(true);
          }}
        >
          Add Provider
        </Button>

        <Toggle
          id="show-system-providers"
          labelText="Show System Providers"
          toggled={showSystemProviders}
          onToggle={() => setShowSystemProviders(!showSystemProviders)}
        />
      </div>

      <DataTable rows={getTableRows()} headers={headers}>
        {({
          rows,
          headers,
          getHeaderProps,
          getRowProps,
          getTableProps,
        }) => (
          <Table {...getTableProps()}>
            <TableHead>
              <TableRow>
                {headers.map((header) => (
                  <TableHeader {...getHeaderProps({ header })}>
                    {header.header}
                  </TableHeader>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row) => (
                <TableRow {...getRowProps({ row })} className={!row.user_id ? 'system-config' : ''}>
                  <TableCell>{row.cells[0].value}</TableCell>
                  <TableCell>{row.cells[1].value}</TableCell>
                  <TableCell>{row.cells[2].value || '-'}</TableCell>
                  <TableCell>{row.cells[3].value || '-'}</TableCell>
                  <TableCell>
                    <Tag type={row.cells[4].value === 'System' ? 'purple' : 'teal'}>
                      {row.cells[4].value}
                    </Tag>
                  </TableCell>
                  <TableCell>{row.cells[5].value}</TableCell>
                  <TableCell>{row.cells[6].value}</TableCell>
                  <TableCell>{row.cells[7].value}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </DataTable>

      <Modal
        open={isModalOpen}
        modalHeading={currentProvider ? "Edit Provider" : "Add Provider"}
        primaryButtonText={currentProvider ? "Save Changes" : "Add Provider"}
        secondaryButtonText="Cancel"
        onRequestClose={() => {
          setIsModalOpen(false);
          resetForm();
        }}
        onRequestSubmit={handleSubmit}
      >
        <Form>
          <TextInput
            id="name"
            labelText="Provider Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            required
          />

          <TextInput
            id="base_url"
            labelText="Base URL"
            value={formData.base_url}
            onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
            required
          />

          <PasswordInput
            id="api_key"
            labelText="API Key"
            value={formData.api_key}
            onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
            required
          />

          <TextInput
            id="org_id"
            labelText="Organization ID (Optional)"
            value={formData.org_id}
            onChange={(e) => setFormData({ ...formData, org_id: e.target.value })}
          />

          <TextInput
            id="project_id"
            labelText="Project ID (Optional)"
            value={formData.project_id}
            onChange={(e) => setFormData({ ...formData, project_id: e.target.value })}
          />

          <Toggle
            id="is_active"
            labelText="Active"
            toggled={formData.is_active}
            onToggle={() => setFormData({ ...formData, is_active: !formData.is_active })}
          />
        </Form>
      </Modal>

      <style>
        {`
          .system-config {
            background-color: var(--cds-layer-hover);
          }
        `}
      </style>
    </div>
  );
};

export default ProviderSettings;
