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
  NumberInput,
  Form,
  Loading,
  InlineNotification,
  Select,
  SelectItem,
  Toggle,
  Tag
} from '@carbon/react';
import { Add, Edit, TrashCan, Checkmark } from '@carbon/icons-react';
import { getFullApiUrl, API_ROUTES } from '../../config/config';
import { fetchWithAuthHeader } from '../../services/authService';
import { useAuth } from '../../contexts/AuthContext';

const LLMParameters = () => {
  const { user } = useAuth();
  const [parameters, setParameters] = useState([]);
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentParameter, setCurrentParameter] = useState(null);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    provider_id: '',
    temperature: 0.7,
    max_tokens: 1000,
    top_p: 1,
    frequency_penalty: 0,
    presence_penalty: 0,
    is_default: false,
    stop_sequences: [],
    additional_params: {}
  });

  const getParametersUrl = () => {
    if (!user?.uuid) {
      throw new Error('User not authenticated');
    }
    return API_ROUTES.LLM_PARAMETERS.replace('{userId}', user.uuid);
  };

  const getProviderUrl = () => {
    if (!user?.uuid) {
      throw new Error('User not authenticated');
    }
    return API_ROUTES.PROVIDER_CONFIG.replace('{userId}', user.uuid);
  };

  useEffect(() => {
    if (user) {
      fetchData();
    }
  }, [user]);

  const fetchData = async () => {
    try {
      const [paramsData, providersData] = await Promise.all([
        fetchWithAuthHeader(getFullApiUrl(getParametersUrl())),
        fetchWithAuthHeader(getFullApiUrl(getProviderUrl()))
      ]);

      setParameters(Array.isArray(paramsData) ? paramsData : [paramsData]);
      setProviders(Array.isArray(providersData) ? providersData : [providersData]);
      setError(null);
    } catch (err) {
      setError('Failed to load LLM parameters');
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const url = getFullApiUrl(getParametersUrl());
      const method = currentParameter ? 'PUT' : 'POST';
      const path = currentParameter ? `${url}/${currentParameter.id}` : url;

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
      setError('Failed to save LLM parameters');
      console.error('Error saving parameters:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (parameterId) => {
    if (!window.confirm('Are you sure you want to delete these parameters?')) return;

    setLoading(true);
    try {
      await fetchWithAuthHeader(
        `${getFullApiUrl(getParametersUrl())}/${parameterId}`,
        { method: 'DELETE' }
      );
      await fetchData();
    } catch (err) {
      setError('Failed to delete parameters');
      console.error('Error deleting parameters:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSetDefault = async (parameterId) => {
    setLoading(true);
    try {
      await fetchWithAuthHeader(
        `${getFullApiUrl(getParametersUrl())}/${parameterId}/default`,
        { method: 'PUT' }
      );
      await fetchData();
    } catch (err) {
      setError('Failed to set default parameters');
      console.error('Error setting default parameters:', err);
    } finally {
      setLoading(false);
    }
  };

  const openEditModal = (parameter) => {
    setCurrentParameter(parameter);
    setFormData({
      name: parameter.name,
      provider_id: parameter.provider_id,
      temperature: parameter.temperature,
      max_tokens: parameter.max_tokens,
      top_p: parameter.top_p,
      frequency_penalty: parameter.frequency_penalty,
      presence_penalty: parameter.presence_penalty,
      is_default: parameter.is_default,
      stop_sequences: parameter.stop_sequences || [],
      additional_params: parameter.additional_params || {}
    });
    setIsModalOpen(true);
  };

  const resetForm = () => {
    setFormData({
      name: '',
      provider_id: '',
      temperature: 0.7,
      max_tokens: 1000,
      top_p: 1,
      frequency_penalty: 0,
      presence_penalty: 0,
      is_default: false,
      stop_sequences: [],
      additional_params: {}
    });
    setCurrentParameter(null);
  };

  const headers = [
    { key: 'name', header: 'Name' },
    { key: 'provider', header: 'Provider' },
    { key: 'temperature', header: 'Temperature' },
    { key: 'max_tokens', header: 'Max Tokens' },
    { key: 'type', header: 'Type' },
    { key: 'actions', header: 'Actions' }
  ];

  const getTableRows = () => {
    return parameters.map(param => ({
      ...param,
      id: param.id,
      type: param.user_id ? 'User' : 'System',
      actions: (
        <>
          {param.user_id && (
            <>
              <Button
                kind="ghost"
                size="sm"
                renderIcon={Edit}
                iconDescription="Edit"
                onClick={() => openEditModal(param)}
                style={{ marginRight: '0.5rem' }}
              />
              <Button
                kind="ghost"
                size="sm"
                renderIcon={Checkmark}
                iconDescription="Set as Default"
                onClick={() => handleSetDefault(param.id)}
                style={{ marginRight: '0.5rem' }}
                disabled={param.is_default}
              />
              <Button
                kind="danger--ghost"
                size="sm"
                renderIcon={TrashCan}
                iconDescription="Delete"
                onClick={() => handleDelete(param.id)}
              />
            </>
          )}
          {param.is_default && (
            <Tag type="blue">Default</Tag>
          )}
        </>
      )
    }));
  };

  if (!user) return <Loading description="Please log in..." />;
  if (loading) return <Loading description="Loading LLM parameters..." />;

  return (
    <div className="llm-parameters">
      {error && (
        <InlineNotification
          kind="error"
          title="Error"
          subtitle={error}
          onClose={() => setError(null)}
        />
      )}

      <div className="llm-parameters-header" style={{ margin: '1rem 0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Button
          renderIcon={Add}
          onClick={() => {
            resetForm();
            setIsModalOpen(true);
          }}
        >
          Add Parameters
        </Button>

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
                  <TableCell>{row.cells[2].value}</TableCell>
                  <TableCell>{row.cells[3].value}</TableCell>
                  <TableCell>
                    <Tag type={row.cells[4].value === 'System' ? 'purple' : 'teal'}>
                      {row.cells[4].value}
                    </Tag>
                  </TableCell>
                  <TableCell>{row.cells[5].value}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </DataTable>

      <Modal
        open={isModalOpen}
        modalHeading={currentParameter ? "Edit Parameters" : "Add Parameters"}
        primaryButtonText={currentParameter ? "Save Changes" : "Add Parameters"}
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
            labelText="Parameter Set Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            required
          />

          <Select
            id="provider"
            labelText="Provider"
            value={formData.provider_id}
            onChange={(e) => setFormData({ ...formData, provider_id: e.target.value })}
            required
          >
            <SelectItem value="" text="Choose a provider" />
            {providers.map(provider => (
              <SelectItem key={provider.id} value={provider.id} text={provider.name} />
            ))}
          </Select>

          <NumberInput
            id="temperature"
            label="Temperature"
            min={0}
            max={1}
            step={0.1}
            value={formData.temperature}
            onChange={(e) => setFormData({ ...formData, temperature: parseFloat(e.target.value) })}
          />

          <NumberInput
            id="max_tokens"
            label="Max Tokens"
            min={1}
            step={1}
            value={formData.max_tokens}
            onChange={(e) => setFormData({ ...formData, max_tokens: parseInt(e.target.value) })}
          />

          <NumberInput
            id="top_p"
            label="Top P"
            min={0}
            max={1}
            step={0.1}
            value={formData.top_p}
            onChange={(e) => setFormData({ ...formData, top_p: parseFloat(e.target.value) })}
          />

          <NumberInput
            id="frequency_penalty"
            label="Frequency Penalty"
            min={-2}
            max={2}
            step={0.1}
            value={formData.frequency_penalty}
            onChange={(e) => setFormData({ ...formData, frequency_penalty: parseFloat(e.target.value) })}
          />

          <NumberInput
            id="presence_penalty"
            label="Presence Penalty"
            min={-2}
            max={2}
            step={0.1}
            value={formData.presence_penalty}
            onChange={(e) => setFormData({ ...formData, presence_penalty: parseFloat(e.target.value) })}
          />

          <Toggle
            id="is_default"
            labelText="Set as Default"
            toggled={formData.is_default}
            onToggle={() => setFormData({ ...formData, is_default: !formData.is_default })}
          />
        </Form>
      </Modal>

      <style>
        {`
          .system-config {
            background-color: #f4f4f4;
          }
        `}
      </style>
    </div>
  );
};

export default LLMParameters;
