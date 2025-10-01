import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeftIcon,
  PlusIcon,
  DocumentIcon,
  TrashIcon,
  ArrowDownTrayIcon,
  ChatBubbleLeftIcon,
  Cog6ToothIcon,
  ShareIcon,
  EyeIcon,
  CheckIcon,
  XMarkIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';
import { useNotification } from '../../contexts/NotificationContext';

// Import the API client and types
import apiClient, { Collection, CollectionDocument } from '../../services/apiClient';

// Use CollectionDocument type from apiClient instead of local CollectionFile
type CollectionFile = CollectionDocument;

const LightweightCollectionDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addNotification } = useNotification();

  const [collection, setCollection] = useState<Collection | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<CollectionFile[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filesToUpload, setFilesToUpload] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    const loadCollection = async () => {
      if (!id) {
        addNotification('error', 'Invalid Collection', 'No collection ID provided.');
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      try {
        // REAL API CALL TO GET COLLECTION DETAILS
        const collectionData = await apiClient.getCollection(id);

        setCollection(collectionData);
        addNotification('success', 'Collection Loaded', 'Collection details loaded successfully.');
      } catch (error) {
        console.error('Error loading collection:', error);
        addNotification('error', 'Loading Error', 'Failed to load collection details.');
        setCollection(null);
      } finally {
        setIsLoading(false);
      }
    };

    loadCollection();
  }, [id, addNotification]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ready':
      case 'completed':
        return <CheckIcon className="w-4 h-4 text-green-50" />;
      case 'processing':
        return <ClockIcon className="w-4 h-4 text-yellow-30" />;
      case 'error':
        return <XMarkIcon className="w-4 h-4 text-red-50" />;
      case 'warning':
        return <ExclamationTriangleIcon className="w-4 h-4 text-yellow-30" />;
      default:
        return null;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ready':
      case 'completed':
        return 'bg-green-50 text-white';
      case 'processing':
        return 'bg-yellow-30 text-gray-100';
      case 'error':
        return 'bg-red-50 text-white';
      case 'warning':
        return 'bg-yellow-30 text-gray-100';
      default:
        return 'bg-gray-50 text-white';
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleFileSelect = (file: CollectionFile) => {
    setSelectedFiles(prev =>
      prev.includes(file)
        ? prev.filter(f => f.id !== file.id)
        : [...prev, file]
    );
  };

  const handleDeleteSelected = async () => {
    if (selectedFiles.length === 0 || !collection) return;

    try {
      // Delete each selected file via API
      await Promise.all(
        selectedFiles.map(file =>
          apiClient.deleteDocument(collection.id, file.id)
        )
      );

      // Update local state
      setCollection(prev => prev ? {
        ...prev,
        documents: prev.documents.filter(doc => !selectedFiles.some(selected => selected.id === doc.id)),
        documentCount: prev.documentCount - selectedFiles.length
      } : null);

      setSelectedFiles([]);
      addNotification('success', 'Files Deleted', `${selectedFiles.length} file(s) deleted successfully.`);
    } catch (error) {
      console.error('Error deleting files:', error);
      addNotification('error', 'Delete Error', 'Failed to delete selected files.');
    }
  };

  const handleDeleteDocument = async (document: CollectionFile) => {
    if (!collection) return;

    try {
      await apiClient.deleteDocument(collection.id, document.id);

      // Update local state
      setCollection(prev => prev ? {
        ...prev,
        documents: prev.documents.filter(doc => doc.id !== document.id),
        documentCount: prev.documentCount - 1
      } : null);

      // Remove from selected files if it was selected
      setSelectedFiles(prev => prev.filter(file => file.id !== document.id));
      addNotification('success', 'Document Deleted', `${document.name} deleted successfully.`);
    } catch (error) {
      console.error('Error deleting document:', error);
      addNotification('error', 'Delete Error', `Failed to delete ${document.name}.`);
    }
  };

  const handleDownloadDocument = async (file: CollectionFile) => {
    try {
      // Create a temporary download link
      const downloadUrl = `${process.env.REACT_APP_BACKEND_URL || ''}/api/collections/${collection?.id}/documents/${file.id}/download`;

      // Create temporary link element and trigger download
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = file.name;
      link.style.display = 'none';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      addNotification('success', 'Download Started', `Downloading ${file.name}...`);
    } catch (error) {
      console.error('Error downloading document:', error);
      addNotification('error', 'Download Error', `Failed to download ${file.name}.`);
    }
  };

  const handleViewDocument = (document: CollectionFile) => {
    // For now, show document details in a notification
    // TODO: Implement proper document preview modal
    addNotification('info', 'Document Info', `${document.name} - ${formatFileSize(document.size)} - ${document.chunks || 0} chunks`);
  };

  const handleChatWithCollection = () => {
    if (collection?.status === 'ready' || collection?.status === 'completed') {
      navigate('/search', {
        state: {
          collectionId: collection.id,
          collectionName: collection.name,
          collectionDescription: collection.description
        }
      });
    } else {
      addNotification('warning', 'Collection Not Ready', 'This collection is not ready for chatting yet.');
    }
  };

  const handleFileSelection = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    setFilesToUpload(files);
  };

  const handleUpload = async () => {
    if (filesToUpload.length === 0 || !collection) {
      addNotification('warning', 'No Files Selected', 'Please select files to upload.');
      return;
    }

    setIsUploading(true);
    try {
      // REAL API CALL FOR FILE UPLOAD
      const uploadedDocuments = await apiClient.uploadDocuments(collection.id, filesToUpload);

      // Update collection with new documents
      setCollection(prev => prev ? {
        ...prev,
        documents: [...prev.documents, ...uploadedDocuments],
        documentCount: prev.documentCount + uploadedDocuments.length
      } : null);

      setFilesToUpload([]);
      setIsUploadModalOpen(false);
      addNotification('success', 'Upload Complete', `${uploadedDocuments.length} file(s) uploaded successfully.`);
    } catch (error) {
      console.error('Error uploading files:', error);
      addNotification('error', 'Upload Error', 'Failed to upload files.');
    } finally {
      setIsUploading(false);
    }
  };

  const closeUploadModal = () => {
    setIsUploadModalOpen(false);
    setFilesToUpload([]);
  };

  const filteredDocuments = collection?.documents.filter(doc =>
    doc.name.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-60 mx-auto mb-4"></div>
          <p className="text-gray-70">Loading collection details...</p>
          <p className="text-sm text-gray-50 mt-2">Fetching from backend API...</p>
        </div>
      </div>
    );
  }

  if (!collection) {
    return (
      <div className="min-h-screen bg-gray-10 p-6">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-2xl font-semibold text-gray-100 mb-4">Collection Not Found</h1>
          <button
            onClick={() => navigate('/lightweight-collections')}
            className="btn-primary"
          >
            Back to Collections
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-10 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Breadcrumb */}
        <nav className="flex items-center space-x-2 text-sm text-gray-70 mb-6">
          <button
            onClick={() => navigate('/lightweight-collections')}
            className="hover:text-blue-60"
          >
            Collections
          </button>
          <span>/</span>
          <span className="text-gray-100">{collection.name}</span>
        </nav>

        {/* Header */}
        <div className="card p-6 mb-6">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center space-x-3 mb-2">
                <button
                  onClick={() => navigate('/lightweight-collections')}
                  className="btn-ghost p-2"
                >
                  <ArrowLeftIcon className="w-5 h-5" />
                </button>
                <h1 className="text-2xl font-semibold text-gray-100">{collection.name}</h1>
                <div className="flex items-center space-x-2">
                  {getStatusIcon(collection.status)}
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusBadge(collection.status)}`}>
                    {collection.status}
                  </span>
                </div>
              </div>
              {collection.description && (
                <p className="text-gray-70 mb-4">{collection.description}</p>
              )}
              <div className="flex items-center space-x-6 text-sm text-gray-70">
                <span>{collection.documentCount} documents</span>
                <span>Created {collection.createdAt.toLocaleDateString()}</span>
                <span>Updated {collection.updatedAt.toLocaleDateString()}</span>
              </div>
            </div>
            <div className="flex space-x-2">
              <button
                onClick={handleChatWithCollection}
                disabled={collection.status !== 'ready' && collection.status !== 'completed'}
                className="btn-primary flex items-center space-x-2 disabled:opacity-50"
              >
                <ChatBubbleLeftIcon className="w-4 h-4" />
                <span>Chat</span>
              </button>
              <button className="btn-secondary flex items-center space-x-2">
                <ShareIcon className="w-4 h-4" />
                <span>Share</span>
              </button>
              <button className="btn-secondary">
                <Cog6ToothIcon className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Documents Table */}
        <div className="card">
          <div className="p-6 border-b border-gray-20">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-100">Documents</h2>
              <button
                onClick={() => setIsUploadModalOpen(true)}
                className="btn-primary flex items-center space-x-2"
              >
                <PlusIcon className="w-4 h-4" />
                <span>Add Documents</span>
              </button>
            </div>

            {/* Search and Batch Actions */}
            <div className="flex items-center justify-between mt-4">
              <div className="flex items-center space-x-4">
                <div className="relative">
                  <MagnifyingGlassIcon className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-60" />
                  <input
                    type="text"
                    placeholder="Search documents..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="input-field pl-10"
                  />
                </div>
              </div>
              {selectedFiles.length > 0 && (
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-70">{selectedFiles.length} selected</span>
                  <button
                    onClick={handleDeleteSelected}
                    className="btn-secondary text-red-50 hover:bg-red-50 hover:text-white flex items-center space-x-2"
                  >
                    <TrashIcon className="w-4 h-4" />
                    <span>Delete</span>
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-10">
                <tr>
                  <th className="px-6 py-3 text-left">
                    <input
                      type="checkbox"
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedFiles(filteredDocuments);
                        } else {
                          setSelectedFiles([]);
                        }
                      }}
                      checked={selectedFiles.length === filteredDocuments.length && filteredDocuments.length > 0}
                      className="rounded border-gray-40"
                    />
                  </th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-100">Name</th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-100">Type</th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-100">Size</th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-100">Status</th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-100">Chunks</th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-100">Uploaded</th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-100">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-20">
                {filteredDocuments.map((doc) => (
                  <tr key={doc.id} className="hover:bg-gray-10">
                    <td className="px-6 py-4">
                      <input
                        type="checkbox"
                        checked={selectedFiles.includes(doc)}
                        onChange={() => handleFileSelect(doc)}
                        className="rounded border-gray-40"
                      />
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-3">
                        <DocumentIcon className="w-5 h-5 text-gray-60 flex-shrink-0" />
                        <span className="text-sm font-medium text-gray-100">{doc.name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-70">{doc.type}</td>
                    <td className="px-6 py-4 text-sm text-gray-70">{formatFileSize(doc.size)}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-2">
                        {getStatusIcon(doc.status || 'ready')}
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusBadge(doc.status || 'ready')}`}>
                          {doc.status || 'ready'}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-70">
                      {doc.chunks || 0}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-70">
                      {doc.uploadedAt.toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex space-x-1">
                        <button
                          onClick={() => handleViewDocument(doc)}
                          className="p-1 hover:bg-gray-20 rounded"
                          title="View document details"
                        >
                          <EyeIcon className="w-4 h-4 text-gray-60" />
                        </button>
                        <button
                          onClick={() => handleDownloadDocument(doc)}
                          className="p-1 hover:bg-gray-20 rounded"
                          title="Download document"
                        >
                          <ArrowDownTrayIcon className="w-4 h-4 text-gray-60" />
                        </button>
                        <button
                          onClick={() => handleDeleteDocument(doc)}
                          className="p-1 hover:bg-gray-20 rounded hover:bg-red-10"
                          title="Delete document"
                        >
                          <TrashIcon className="w-4 h-4 text-gray-60 hover:text-red-50" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Upload Modal */}
        {isUploadModalOpen && (
          <div className="fixed inset-0 bg-gray-100 bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-100">Upload Documents</h2>
                <button
                  onClick={() => setIsUploadModalOpen(false)}
                  className="text-gray-60 hover:text-gray-100"
                >
                  <XMarkIcon className="w-6 h-6" />
                </button>
              </div>

              <div className="border-2 border-dashed border-gray-30 rounded-lg p-8 text-center">
                <DocumentIcon className="w-12 h-12 text-gray-60 mx-auto mb-4" />
                <p className="text-gray-100 mb-2">Drag and drop files here</p>
                <p className="text-sm text-gray-70 mb-4">or click to select files</p>
                <input
                  type="file"
                  multiple
                  className="hidden"
                  id="file-upload"
                  onChange={handleFileSelection}
                />
                <label htmlFor="file-upload" className="btn-primary cursor-pointer">
                  Select Files
                </label>
              </div>

              {/* Selected Files Preview */}
              {filesToUpload.length > 0 && (
                <div className="mt-4">
                  <h3 className="text-sm font-medium text-gray-100 mb-2">
                    Selected Files ({filesToUpload.length})
                  </h3>
                  <div className="max-h-32 overflow-y-auto space-y-2">
                    {filesToUpload.map((file, index) => (
                      <div key={index} className="flex items-center justify-between p-2 bg-gray-10 rounded">
                        <div className="flex items-center space-x-2">
                          <DocumentIcon className="w-4 h-4 text-gray-60" />
                          <span className="text-sm text-gray-100 truncate">{file.name}</span>
                        </div>
                        <span className="text-xs text-gray-70">
                          {(file.size / 1024 / 1024).toFixed(2)} MB
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex justify-end space-x-3 mt-6">
                <button
                  onClick={closeUploadModal}
                  className="btn-secondary"
                  disabled={isUploading}
                >
                  Cancel
                </button>
                <button
                  onClick={handleUpload}
                  className="btn-primary"
                  disabled={isUploading || filesToUpload.length === 0}
                >
                  {isUploading ? 'Uploading...' : 'Upload'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default LightweightCollectionDetail;
