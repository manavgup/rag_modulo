import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import AgentList from './AgentList';
import apiClient from '../../services/apiClient';
import { Agent } from '../../services/apiClient';

// Mock the apiClient
jest.mock('../../services/apiClient');
const mockedApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe('AgentList', () => {
  const collectionId = 'test-collection-id';

  it('shows a loading state initially', () => {
    mockedApiClient.getAgents.mockImplementationOnce(() => new Promise(() => {})); // Never resolves
    render(<AgentList collectionId={collectionId} />);
    expect(screen.getByText(/loading agents.../i)).toBeInTheDocument();
  });

  it('displays a list of agents on successful fetch', async () => {
    const mockAgents: Agent[] = [
      { id: 'agent-1', name: 'Web Search', description: 'Performs a web search.' },
      { id: 'agent-2', name: 'Data Analyzer', description: 'Analyzes structured data.' },
    ];
    mockedApiClient.getAgents.mockResolvedValueOnce(mockAgents);

    render(<AgentList collectionId={collectionId} />);

    await waitFor(() => {
      expect(screen.getByText('Web Search')).toBeInTheDocument();
      expect(screen.getByText('Performs a web search.')).toBeInTheDocument();
      expect(screen.getByText('Data Analyzer')).toBeInTheDocument();
    });
  });

  it('displays an error message when the fetch fails', async () => {
    mockedApiClient.getAgents.mockRejectedValueOnce(new Error('API Error'));

    render(<AgentList collectionId={collectionId} />);

    await waitFor(() => {
      expect(screen.getByText(/failed to fetch agents/i)).toBeInTheDocument();
    });
  });

  it('displays a message when no agents are available', async () => {
    mockedApiClient.getAgents.mockResolvedValueOnce([]);

    render(<AgentList collectionId={collectionId} />);

    await waitFor(() => {
      expect(screen.getByText(/no agents available/i)).toBeInTheDocument();
    });
  });
});