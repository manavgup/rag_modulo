import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter as Router } from 'react-router-dom';
import LightweightCollectionDetail from './LightweightCollectionDetail';
import apiClient from '../../services/apiClient';
import { useNotification } from '../../contexts/NotificationContext';

// Mock the API client
jest.mock('../../services/apiClient');
const mockedApiClient = apiClient as jest.Mocked<typeof apiClient>;

// Mock the useNotification hook
jest.mock('../../contexts/NotificationContext', () => ({
  useNotification: jest.fn(),
}));
const mockedUseNotification = useNotification as jest.Mock;

// Mock react-router-dom hooks
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useParams: () => ({ id: '123' }),
  useNavigate: () => jest.fn(),
}));

// Mock window.URL.createObjectURL and revokeObjectURL
const createObjectURL = jest.fn(() => 'mock-blob-url');
const revokeObjectURL = jest.fn();
window.URL.createObjectURL = createObjectURL;
window.URL.revokeObjectURL = revokeObjectURL;

describe('LightweightCollectionDetail', () => {
  const mockCollection = {
    id: '123',
    name: 'Test Collection',
    description: 'Test Description',
    status: 'ready' as const,
    documents: [
      { id: 'doc1', name: 'test-file.pdf', type: 'application/pdf', size: 1024, uploadedAt: new Date(), status: 'ready' as const },
    ],
    createdAt: new Date(),
    updatedAt: new Date(),
    documentCount: 1,
  };

  const addNotification = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockedUseNotification.mockReturnValue({ addNotification });
    mockedApiClient.getCollection.mockResolvedValue(mockCollection);
  });

  it('should handle document download correctly', async () => {
    const mockBlob = new Blob(['test content'], { type: 'application/pdf' });
    mockedApiClient.downloadDocument.mockResolvedValue(mockBlob);

    render(
      <Router>
        <LightweightCollectionDetail />
      </Router>
    );

    // Wait for the component to finish loading
    await waitFor(() => expect(screen.getByRole('heading', { name: /test collection/i })).toBeInTheDocument());

    // Find the download button for the document
    const downloadButton = screen.getByTitle('Download document');
    expect(downloadButton).toBeInTheDocument();

    // Create a spy on document.createElement to check if the link is created
    const linkSpy = jest.spyOn(document, 'createElement');

    // Click the download button
    fireEvent.click(downloadButton);

    // Wait for the download logic to execute
    await waitFor(() => {
      // Check if the API was called correctly
      expect(mockedApiClient.downloadDocument).toHaveBeenCalledWith('123', 'doc1');

      // Check if a blob URL was created
      expect(createObjectURL).toHaveBeenCalledWith(mockBlob);

      // Check if a link element was created for the download
      expect(linkSpy).toHaveBeenCalledWith('a');
    });

    // Check if the success notification was shown
    expect(addNotification).toHaveBeenCalledWith('success', 'Download Started', 'Downloading test-file.pdf...');

    // Restore the spy
    linkSpy.mockRestore();
  });

  it('should show an error notification on download failure', async () => {
    const mockError = new Error('Download failed');
    mockedApiClient.downloadDocument.mockRejectedValue(mockError);

    render(
      <Router>
        <LightweightCollectionDetail />
      </Router>
    );

    await waitFor(() => expect(screen.getByRole('heading', { name: /test collection/i })).toBeInTheDocument());

    // Clear the mock from the initial load notification
    addNotification.mockClear();

    const downloadButton = screen.getByTitle('Download document');
    fireEvent.click(downloadButton);

    await waitFor(() => {
      expect(mockedApiClient.downloadDocument).toHaveBeenCalledWith('123', 'doc1');
    });

    await waitFor(() => {
      expect(addNotification).toHaveBeenCalledWith('error', 'Download Error', 'Failed to download test-file.pdf.');
    });
  });
});