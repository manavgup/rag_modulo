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
  TextArea,
  Form,
  Loading,
  InlineNotification,
  Select,
  SelectItem,
  Tag,
  Toggle
} from '@carbon/react';
import { Add, Edit, TrashCan, Checkmark } from '@carbon/icons-react';
import { getFullApiUrl, API_ROUTES } from '../../config/config';
import { fetchWithAuthHeader } from '../../services/authService';
import { useAuth } from '../../contexts/AuthContext';

const PromptTemplates = () => {
  const { user } = useAuth();
  const [templates, setTemplates] = useState([]);
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentTemplate, setCurrentTemplate] = useState(null);
  const [newVariable, setNewVariable] = useState('');

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    provider: '',
    provider_config_id: '',
    description: '',
    system_prompt: '',
    context_prefix: 'Context:\n',
    query_prefix: 'Question:\n',
    answer_prefix: 'Answer:\n',
    is_default: false,
    input_variables: [],
    template_format: ''
  });

  const getTemplatesUrl = () => {
    if (!user?.uuid) {
      throw new Error('User not authenticated');
    }
    return API_ROUTES.PROMPT_TEMPLATES.replace('{userId}', user.uuid);
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
      const [templatesData, providersData] = await Promise.all([
        fetchWithAuthHeader(getFullApiUrl(getTemplatesUrl())),
        fetchWithAuthHeader(getFullApiUrl(getProviderUrl()))
      ]);

      setTemplates(Array.isArray(templatesData) ? templatesData : [templatesData]);
      setProviders(Array.isArray(providersData) ? providersData : [providersData]);
      setError(null);
    } catch (err) {
      setError('Failed to load prompt templates');
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const url = getFullApiUrl(getTemplatesUrl());
      const method = currentTemplate ? 'PUT' : 'POST';
      const path = currentTemplate ? `${url}/${currentTemplate.id}` : url;
      
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
      setError('Failed to save prompt template');
      console.error('Error saving template:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (templateId) => {
    if (!window.confirm('Are you sure you want to delete this template?')) return;
    
    setLoading(true);
    try {
      await fetchWithAuthHeader(
        `${getFullApiUrl(getTemplatesUrl())}/${templateId}`,
        { method: 'DELETE' }
      );
      await fetchData();
    } catch (err) {
      setError('Failed to delete template');
      console.error('Error deleting template:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSetDefault = async (templateId) => {
    setLoading(true);
    try {
      await fetchWithAuthHeader(
        `${getFullApiUrl(getTemplatesUrl())}/${templateId}/default`,
        { method: 'PUT' }
      );
      await fetchData();
    } catch (err) {
      setError('Failed to set default template');
      console.error('Error setting default template:', err);
    } finally {
      setLoading(false);
    }
  };

  const openEditModal = (template) => {
    setCurrentTemplate(template);
    setFormData({
      name: template.name,
      provider: template.provider,
      provider_config_id: template.provider_config_id,
      description: template.description || '',
      system_prompt: template.system_prompt,
      context_prefix: template.context_prefix,
      query_prefix: template.query_prefix,
      answer_prefix: template.answer_prefix,
      is_default: template.is_default,
      input_variables: template.input_variables || [],
      template_format: template.template_format || ''
    });
    setIsModalOpen(true);
  };

  const resetForm = () => {
    setFormData({
      name: '',
      provider: '',
      provider_config_id: '',
      description: '',
      system_prompt: '',
      context_prefix: 'Context:\n',
      query_prefix: 'Question:\n',
      answer_prefix: 'Answer:\n',
      is_default: false,
      input_variables: [],
      template_format: ''
    });
    setCurrentTemplate(null);
    setNewVariable('');
  };

  const addVariable = () => {
    if (newVariable && !formData.input_variables.includes(newVariable)) {
      setFormData({
        ...formData,
        input_variables: [...formData.input_variables, newVariable]
      });
      setNewVariable('');
    }
  };

  const removeVariable = (variable) => {
    setFormData({
      ...formData,
      input_variables: formData.input_variables.filter(v => v !== variable)
    });
  };

  const headers = [
    { key: 'name', header: 'Name' },
    { key: 'provider', header: 'Provider' },
    { key: 'description', header: 'Description' },
    { key: 'type', header: 'Type' },
    { key: 'actions', header: 'Actions' }
  ];

  const getTableRows = () => {
    return templates.map(template => ({
      ...template,
      id: template.id,
      type: template.user_id ? 'User' : 'System',
      actions: (
        <>
          {template.user_id && (
            <>
              <Button
                kind="ghost"
                size="sm"
                renderIcon={Edit}
                iconDescription="Edit"
                onClick={() => openEditModal(template)}
                style={{ marginRight: '0.5rem' }}
              />
              <Button
                kind="ghost"
                size="sm"
                renderIcon={Checkmark}
                iconDescription="Set as Default"
                onClick={() => handleSetDefault(template.id)}
                style={{ marginRight: '0.5rem' }}
                disabled={template.is_default}
              />
              <Button
                kind="danger--ghost"
                size="sm"
                renderIcon={TrashCan}
                iconDescription="Delete"
                onClick={() => handleDelete(template.id)}
              />
            </>
          )}
          {template.is_default && (
            <Tag type="blue">Default</Tag>
          )}
        </>
      )
    }));
  };

  if (!user) return <Loading description="Please log in..." />;
  if (loading) return <Loading description="Loading prompt templates..." />;

  return (
    <div className="prompt-templates">
      {error && (
        <InlineNotification
          kind="error"
          title="Error"
          subtitle={error}
          onClose={() => setError(null)}
        />
      )}

      <div className="prompt-templates-header" style={{ margin: '1rem 0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Button
          renderIcon={Add}
          onClick={() => {
            resetForm();
            setIsModalOpen(true);
          }}
        >
          Add Template
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
                  <TableCell>
                    <Tag type={row.cells[3].value === 'System' ? 'purple' : 'teal'}>
                      {row.cells[3].value}
                    </Tag>
                  </TableCell>
                  <TableCell>{row.cells[4].value}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </DataTable>

      <Modal
        open={isModalOpen}
        modalHeading={currentTemplate ? "Edit Template" : "Add Template"}
        primaryButtonText={currentTemplate ? "Save Changes" : "Add Template"}
        secondaryButtonText="Cancel"
        onRequestClose={() => {
          setIsModalOpen(false);
          resetForm();
        }}
        onRequestSubmit={handleSubmit}
        size="lg"
      >
        <Form>
          <TextInput
            id="name"
            labelText="Template Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            required
          />

          <Select
            id="provider"
            labelText="Provider"
            value={formData.provider}
            onChange={(e) => setFormData({ ...formData, provider: e.target.value })}
            required
          >
            <SelectItem value="" text="Choose a provider" />
            {providers.map(provider => (
              <SelectItem key={provider.id} value={provider.provider_name} text={provider.provider_name} />
            ))}
          </Select>

          <Select
            id="provider_config"
            labelText="Provider Configuration"
            value={formData.provider_config_id}
            onChange={(e) => setFormData({ ...formData, provider_config_id: e.target.value })}
            required
          >
            <SelectItem value="" text="Choose a provider configuration" />
            {providers
              .filter(p => p.provider_name === formData.provider)
              .map(provider => (
                <SelectItem key={provider.id} value={provider.id} text={provider.name} />
              ))
            }
          </Select>

          <TextArea
            id="description"
            labelText="Description"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          />

          <TextArea
            id="system_prompt"
            labelText="System Prompt"
            value={formData.system_prompt}
            onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
            required
          />

          <TextInput
            id="context_prefix"
            labelText="Context Prefix"
            value={formData.context_prefix}
            onChange={(e) => setFormData({ ...formData, context_prefix: e.target.value })}
            required
          />

          <TextInput
            id="query_prefix"
            labelText="Query Prefix"
            value={formData.query_prefix}
            onChange={(e) => setFormData({ ...formData, query_prefix: e.target.value })}
            required
          />

          <TextInput
            id="answer_prefix"
            labelText="Answer Prefix"
            value={formData.answer_prefix}
            onChange={(e) => setFormData({ ...formData, answer_prefix: e.target.value })}
            required
          />

          <div style={{ marginTop: '1rem' }}>
            <TextInput
              id="new_variable"
              labelText="Add Input Variable"
              value={newVariable}
              onChange={(e) => setNewVariable(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  addVariable();
                }
              }}
            />
            <Button
              kind="ghost"
              size="sm"
              onClick={addVariable}
              style={{ marginTop: '0.5rem' }}
            >
              Add Variable
            </Button>
          </div>

          {formData.input_variables.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', margin: '1rem 0' }}>
              {formData.input_variables.map((variable) => (
                <Tag
                  key={variable}
                  filter
                  onClose={() => removeVariable(variable)}
                >
                  {variable}
                </Tag>
              ))}
            </div>
          )}

          <TextArea
            id="template_format"
            labelText="Template Format"
            value={formData.template_format}
            onChange={(e) => setFormData({ ...formData, template_format: e.target.value })}
            placeholder="Example: Explain {topic}, focusing on {aspect}"
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

export default PromptTemplates;
