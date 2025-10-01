import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  PlusIcon,
  DocumentIcon,
  CheckIcon,
  ChatBubbleLeftIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { useNotification } from '../../contexts/NotificationContext';
import LightweightCreateCollectionModal from '../modals/LightweightCreateCollectionModal';

// Import the API client and types
import apiClient, { Collection } from '../../services/apiClient';

// Remove local interfaces since we're importing from apiClient
// Types are now imported from apiClient

const LightweightCollections: React.FC = () => {
  const { addNotification } = useNotification();
  const navigate = useNavigate();
  const [collections, setCollections] = useState<Collection[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  useEffect(() => {
    const loadCollections = async () => {
      setIsLoading(true);
      try {
        // REPLACE MOCK DATA WITH REAL API CALL
        const collections = await apiClient.getCollections();

        setCollections(collections);
        addNotification('success', 'Collections Loaded', 'Your collections have been loaded successfully.');
      } catch (error) {
        console.error('Error loading collections:', error);
        addNotification('error', 'Loading Error', 'Failed to load collections.');

        // Fallback to empty array on error
        setCollections([]);
      } finally {
        setIsLoading(false);
      }
    };

    loadCollections();
  }, []);

  const handleCollectionCreated = async (collectionData: { name: string; description?: string }) => {
    try {
      // REAL API CALL FOR COLLECTION CREATION
      const newCollection = await apiClient.createCollection(collectionData);

      setCollections(prev => [...prev, newCollection]);
      setIsCreateModalOpen(false);
      addNotification('success', 'Collection Created', `${newCollection.name} has been created successfully.`);
    } catch (error) {
      console.error('Error creating collection:', error);
      addNotification('error', 'Creation Error', 'Failed to create collection.');
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ready':
      case 'completed':
        return <CheckIcon className="w-5 h-5 text-green-50" />;
      case 'processing':
        return <ClockIcon className="w-5 h-5 text-yellow-30" />;
      case 'error':
        return <XMarkIcon className="w-5 h-5 text-red-50" />;
      case 'warning':
        return <ExclamationTriangleIcon className="w-5 h-5 text-yellow-30" />;
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

  const handleChatWithCollection = (collection: Collection, e: React.MouseEvent) => {
    e.stopPropagation();
    if (collection.status === 'ready' || collection.status === 'completed') {
      addNotification('info', 'Starting Chat', `Opening chat with ${collection.name}`);
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

  const handleViewCollection = (collection: Collection) => {
    navigate(`/collections/${collection.id}`);
  };

  const handleAddCollection = () => {
    setIsCreateModalOpen(true);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-60 mx-auto mb-4"></div>
          <p className="text-gray-70">Loading collections...</p>
          <p className="text-sm text-gray-50 mt-2">Fetching from backend API...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-10 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold text-gray-100 mb-2">My Collections</h1>
          <p className="text-gray-70">Manage and organize your document collections</p>
        </div>
        <button
          onClick={handleAddCollection}
          className="btn-primary flex items-center space-x-2"
        >
          <PlusIcon className="w-5 h-5" />
          <span>Add a collection</span>
        </button>
      </div>

      {/* Collections Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {collections.map((collection) => (
          <div
            key={collection.id}
            onClick={() => handleViewCollection(collection)}
            className="card p-6 cursor-pointer hover:border-blue-60 transition-all duration-200 group"
          >
            {/* Collection Header */}
            <div className="flex items-start justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-100 group-hover:text-blue-60 transition-colors duration-200">
                {collection.name}
              </h3>
              <div className="flex items-center space-x-2">
                {getStatusIcon(collection.status)}
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusBadge(collection.status)}`}>
                  {collection.status}
                </span>
              </div>
            </div>

            {/* Description */}
            {collection.description && (
              <p className="text-gray-70 text-sm mb-4">{collection.description}</p>
            )}

            {/* Documents Preview */}
            <div className="space-y-2 mb-4">
              {collection.documents.slice(0, 3).map((doc) => (
                <div key={doc.id} className="flex items-center space-x-2 text-sm">
                  <DocumentIcon className="w-4 h-4 text-gray-60 flex-shrink-0" />
                  <span className="text-gray-100 truncate">{doc.name}</span>
                </div>
              ))}
              {collection.documentCount > 3 && (
                <div className="text-sm text-gray-70 pl-6">
                  +{collection.documentCount - 3} more documents
                </div>
              )}
            </div>

            {/* Collection Footer */}
            <div className="flex items-center justify-between pt-4 border-t border-gray-20">
              <div className="text-sm text-gray-70">
                <div>{collection.documentCount} documents</div>
                <div>Updated {collection.updatedAt.toLocaleDateString()}</div>
              </div>
              <button
                onClick={(e) => handleChatWithCollection(collection, e)}
                disabled={collection.status !== 'ready'}
                className={`p-2 rounded-lg transition-colors duration-200 ${
                  collection.status === 'ready'
                    ? 'hover:bg-blue-60 hover:text-white text-blue-60'
                    : 'text-gray-40 cursor-not-allowed'
                }`}
                title="Chat with collection"
              >
                <ChatBubbleLeftIcon className="w-5 h-5" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Create Collection Modal */}
      <LightweightCreateCollectionModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCollectionCreated={handleCollectionCreated}
      />
    </div>
  );
};

export default LightweightCollections;
