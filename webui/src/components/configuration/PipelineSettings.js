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
  Toggle,
  NumberInput
} from '@carbon/react';
import { Add, Edit, TrashCan, Checkmark } from '@carbon/icons-react';
import { getFullApiUrl, API_ROUTES } from '../../config/config';
import { fetchWithAuthHeader } from '../../services/authService';
import { useAuth } from '../../contexts/AuthContext';

const PipelineSettings = () => {
  const { user } = useAuth();
  const [pipelines, setPipelines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentPipeline, setCurrentPipeline] = useState(null);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    retriever_type: 'milvus',  // default retriever
    retriever_config: {
      top_k: 3,
      similarity_threshold: 0.7
    },
    reranker_config: {
      enabled: false,
      model_name: '',
      top_k: 3
    },
    query_rewriter_config: {
      enabled: false,
      strategy: 'basic'
    },
    llm_config: {
      model_id: '',
      max_tokens: 1000,
      temperature: 0.7
    },
    is_default: false
  });

  const getPipelinesUrl = () => {
    if (!user?.uuid) {
      throw new Error('User not authenticated');
    }
    return API_ROUTES.PIPELINES.replace('{userId}', user.uuid);
  };

  useEffect(() => {
    if (user) {
      fetchPipelines();
    }
  }, [user]);

  const fetchPipelines = async () => {
    try {
      const data = await fetchWithAuthHeader(getFullApiUrl(getPipelinesUrl()));
      setPipelines(Array.isArray(data) ? data : [data]);
      setError(null);
    } catch (err) {
      setError('Failed to load pipeline settings');
      console.error('Error fetching pipelines:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const url = getFullApiUrl(getPipelinesUrl());
      const method = currentPipeline ? 'PUT' : 'POST';
      const path = currentPipeline ? `${url}/${currentPipeline.id}` : url;

      await fetchWithAuthHeader(path, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      await fetchPipelines();
      setIsModalOpen(false);
      resetForm();
    } catch (err) {
      setError('Failed to save pipeline settings');
      console.error('Error saving pipeline:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (pipelineId) => {
    if (!window.confirm('Are you sure you want to delete this pipeline?')) return;

    setLoading(true);
    try {
      await fetchWithAuthHeader(
        `${getFullApiUrl(getPipelinesUrl())}/${pipelineId}`,
        { method: 'DELETE' }
      );
      await fetchPipelines();
    } catch (err) {
      setError('Failed to delete pipeline');
      console.error('Error deleting pipeline:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSetDefault = async (pipelineId) => {
    setLoading(true);
    try {
      await fetchWithAuthHeader(
        `${getFullApiUrl(getPipelinesUrl())}/${pipelineId}/default`,
        { method: 'PUT' }
      );
      await fetchPipelines();
    } catch (err) {
      setError('Failed to set default pipeline');
      console.error('Error setting default pipeline:', err);
    } finally {
      setLoading(false);
    }
  };

  const openEditModal = (pipeline) => {
    setCurrentPipeline(pipeline);
    setFormData({
      name: pipeline.name,
      description: pipeline.description || '',
      retriever_type: pipeline.retriever_type,
      retriever_config: pipeline.retriever_config,
      reranker_config: pipeline.reranker_config,
      query_rewriter_config: pipeline.query_rewriter_config,
      llm_config: pipeline.llm_config,
      is_default: pipeline.is_default
    });
    setIsModalOpen(true);
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      retriever_type: 'milvus',
      retriever_config: {
        top_k: 3,
        similarity_threshold: 0.7
      },
      reranker_config: {
        enabled: false,
        model_name: '',
        top_k: 3
      },
      query_rewriter_config: {
        enabled: false,
        strategy: 'basic'
      },
      llm_config: {
        model_id: '',
        max_tokens: 1000,
        temperature: 0.7
      },
      is_default: false
    });
    setCurrentPipeline(null);
  };

  const headers = [
    { key: 'name', header: 'Name' },
    { key: 'description', header: 'Description' },
    { key: 'retriever_type', header: 'Retriever' },
    { key: 'type', header: 'Type' },
    { key: 'actions', header: 'Actions' }
  ];

  const getTableRows = () => {
    return pipelines.map(pipeline => ({
      ...pipeline,
      id: pipeline.id,
      type: pipeline.user_id ? 'User' : 'System',
      actions: (
        <>
          {pipeline.user_id && (
            <>
              <Button
                kind="ghost"
                size="sm"
                renderIcon={Edit}
                iconDescription="Edit"
                onClick={() => openEditModal(pipeline)}
                style={{ marginRight: '0.5rem' }}
              />
              <Button
                kind="ghost"
                size="sm"
                renderIcon={Checkmark}
                iconDescription="Set as Default"
                onClick={() => handleSetDefault(pipeline.id)}
                style={{ marginRight: '0.5rem' }}
                disabled={pipeline.is_default}
              />
              <Button
                kind="danger--ghost"
                size="sm"
                renderIcon={TrashCan}
                iconDescription="Delete"
                onClick={() => handleDelete(pipeline.id)}
              />
            </>
          )}
          {pipeline.is_default && (
            <Tag type="blue">Default</Tag>
          )}
        </>
      )
    }));
  };

  if (!user) return <Loading description="Please log in..." />;
  if (loading) return <Loading description="Loading pipeline settings..." />;

  return (
    <div className="pipeline-settings">
      {error && (
        <InlineNotification
          kind="error"
          title="Error"
          subtitle={error}
          onClose={() => setError(null)}
        />
      )}

      <div className="pipeline-settings-header" style={{ margin: '1rem 0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Button
          renderIcon={Add}
          onClick={() => {
            resetForm();
            setIsModalOpen(true);
          }}
        >
          Add Pipeline
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
        modalHeading={currentPipeline ? "Edit Pipeline" : "Add Pipeline"}
        primaryButtonText={currentPipeline ? "Save Changes" : "Add Pipeline"}
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
            labelText="Pipeline Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            required
          />

          <TextArea
            id="description"
            labelText="Description"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          />

          <Select
            id="retriever_type"
            labelText="Retriever Type"
            value={formData.retriever_type}
            onChange={(e) => setFormData({ ...formData, retriever_type: e.target.value })}
            required
          >
            <SelectItem value="milvus" text="Milvus" />
            <SelectItem value="elasticsearch" text="Elasticsearch" />
            <SelectItem value="chroma" text="Chroma" />
          </Select>

          <NumberInput
            id="retriever_top_k"
            label="Retriever Top K"
            min={1}
            max={20}
            value={formData.retriever_config.top_k}
            onChange={(e) => setFormData({
              ...formData,
              retriever_config: {
                ...formData.retriever_config,
                top_k: parseInt(e.target.value)
              }
            })}
          />

          <NumberInput
            id="similarity_threshold"
            label="Similarity Threshold"
            min={0}
            max={1}
            step={0.1}
            value={formData.retriever_config.similarity_threshold}
            onChange={(e) => setFormData({
              ...formData,
              retriever_config: {
                ...formData.retriever_config,
                similarity_threshold: parseFloat(e.target.value)
              }
            })}
          />

          <Toggle
            id="reranker_enabled"
            labelText="Enable Reranker"
            toggled={formData.reranker_config.enabled}
            onToggle={() => setFormData({
              ...formData,
              reranker_config: {
                ...formData.reranker_config,
                enabled: !formData.reranker_config.enabled
              }
            })}
          />

          {formData.reranker_config.enabled && (
            <>
              <TextInput
                id="reranker_model"
                labelText="Reranker Model"
                value={formData.reranker_config.model_name}
                onChange={(e) => setFormData({
                  ...formData,
                  reranker_config: {
                    ...formData.reranker_config,
                    model_name: e.target.value
                  }
                })}
              />

              <NumberInput
                id="reranker_top_k"
                label="Reranker Top K"
                min={1}
                max={10}
                value={formData.reranker_config.top_k}
                onChange={(e) => setFormData({
                  ...formData,
                  reranker_config: {
                    ...formData.reranker_config,
                    top_k: parseInt(e.target.value)
                  }
                })}
              />
            </>
          )}

          <Toggle
            id="query_rewriter_enabled"
            labelText="Enable Query Rewriter"
            toggled={formData.query_rewriter_config.enabled}
            onToggle={() => setFormData({
              ...formData,
              query_rewriter_config: {
                ...formData.query_rewriter_config,
                enabled: !formData.query_rewriter_config.enabled
              }
            })}
          />

          {formData.query_rewriter_config.enabled && (
            <Select
              id="query_rewriter_strategy"
              labelText="Query Rewriter Strategy"
              value={formData.query_rewriter_config.strategy}
              onChange={(e) => setFormData({
                ...formData,
                query_rewriter_config: {
                  ...formData.query_rewriter_config,
                  strategy: e.target.value
                }
              })}
            >
              <SelectItem value="basic" text="Basic" />
              <SelectItem value="advanced" text="Advanced" />
              <SelectItem value="semantic" text="Semantic" />
            </Select>
          )}

          <TextInput
            id="llm_model"
            labelText="LLM Model ID"
            value={formData.llm_config.model_id}
            onChange={(e) => setFormData({
              ...formData,
              llm_config: {
                ...formData.llm_config,
                model_id: e.target.value
              }
            })}
            required
          />

          <NumberInput
            id="max_tokens"
            label="Max Tokens"
            min={1}
            max={4096}
            value={formData.llm_config.max_tokens}
            onChange={(e) => setFormData({
              ...formData,
              llm_config: {
                ...formData.llm_config,
                max_tokens: parseInt(e.target.value)
              }
            })}
          />

          <NumberInput
            id="temperature"
            label="Temperature"
            min={0}
            max={1}
            step={0.1}
            value={formData.llm_config.temperature}
            onChange={(e) => setFormData({
              ...formData,
              llm_config: {
                ...formData.llm_config,
                temperature: parseFloat(e.target.value)
              }
            })}
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

export default PipelineSettings;
