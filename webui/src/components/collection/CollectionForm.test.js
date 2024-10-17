import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CollectionForm from './collection/CollectionForm';
import { AuthProvider } from 'src/contexts/AuthContext';
import { createCollectionWithDocuments, getUserCollections } from 'src/api/collection_api';

// Mock the API functions
jest.mock('../api/api', () => ({
  createCollectionWithDocuments: jest.fn(),
  getUserCollections: jest.fn(),
}));

// Mock the AuthContext
jest.mock('../contexts/AuthContext', () => ({
  AuthProvider: ({ children }) => children,
  useAuth: () => ({ user: { uuid: 'test-uuid' }, loading: false }),
}));

describe('CollectionForm', () => {
  beforeEach(() => {
    getUserCollections.mockResolvedValue({ collections: [] });
  });

  test('renders CollectionForm component', () => {
    render(<CollectionForm />);
    expect(screen.getByText('Create New Collection')).toBeInTheDocument();
  });

  test('validates collection name', async () => {
    render(<CollectionForm />);
    const nameInput = screen.getByLabelText('Collection Name');
    
    userEvent.type(nameInput, 'ab');
    await waitFor(() => {
      expect(screen.getByText('Collection name must be at least 3 characters long.')).toBeInTheDocument();
    });

    userEvent.clear(nameInput);
    userEvent.type(nameInput, 'Valid Name');
    await waitFor(() => {
      expect(screen.queryByText('Collection name must be at least 3 characters long.')).not.toBeInTheDocument();
    });
  });

  test('shows error when no files are selected', async () => {
    render(<CollectionForm />);
    const submitButton = screen.getByText('Create Collection');
    
    fireEvent.click(submitButton);
    await waitFor(() => {
      expect(screen.getByText('Please add at least one file to the collection.')).toBeInTheDocument();
    });
  });

  test('shows confirmation dialog when form is valid', async () => {
    render(<CollectionForm />);
    const nameInput = screen.getByLabelText('Collection Name');
    const fileInput = screen.getByLabelText('Drag and drop files here or click to upload');

    userEvent.type(nameInput, 'Test Collection');
    const file = new File(['hello'], 'hello.pdf', {type: 'application/pdf'});
    userEvent.upload(fileInput, file);

    const submitButton = screen.getByText('Create Collection');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Confirm Collection Creation')).toBeInTheDocument();
    });
  });

  test('creates collection when confirmed', async () => {
    createCollectionWithDocuments.mockResolvedValue({ success: true });

    render(<CollectionForm />);
    const nameInput = screen.getByLabelText('Collection Name');
    const fileInput = screen.getByLabelText('Drag and drop files here or click to upload');

    userEvent.type(nameInput, 'Test Collection');
    const file = new File(['hello'], 'hello.pdf', {type: 'application/pdf'});
    userEvent.upload(fileInput, file);

    const submitButton = screen.getByText('Create Collection');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Confirm Collection Creation')).toBeInTheDocument();
    });

    const confirmButton = screen.getByText('Create');
    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(createCollectionWithDocuments).toHaveBeenCalled();
    });
    
    await waitFor(() => {
      expect(screen.getByText('Collection Created')).toBeInTheDocument();
    });
  });
});