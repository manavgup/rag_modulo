import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  PlayIcon,
  TrashIcon,
  ArrowDownTrayIcon,
  PlusIcon,
  ChatBubbleLeftRightIcon,
  DocumentTextIcon,
  FolderIcon,
  DocumentIcon,
  MicrophoneIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { useNotification } from '../../contexts/NotificationContext';
import { useAuth } from '../../contexts/AuthContext';
import apiClient, { Podcast, Collection } from '../../services/apiClient';
import PodcastProgressCard from './PodcastProgressCard';
import PodcastGenerationModal from './PodcastGenerationModal';

const LightweightPodcasts: React.FC = () => {
  const { addNotification } = useNotification();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [podcasts, setPodcasts] = useState<Podcast[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingCollections, setIsLoadingCollections] = useState(true);
  const [filterTab, setFilterTab] = useState<'all' | 'in-progress' | 'completed' | 'favorites'>('all');
  const [isGenerateModalOpen, setIsGenerateModalOpen] = useState(false);
  const [selectedCollectionForGeneration, setSelectedCollectionForGeneration] = useState<{id: string; name: string} | null>(null);
  const [pollingInterval, setPollingInterval] = useState(5000); // Start with 5 seconds

  useEffect(() => {
    loadPodcasts();
    loadCollections();
  }, []);

  // Compute IDs of generating podcasts to avoid unnecessary re-renders
  const generatingPodcastIds = useMemo(() => {
    return podcasts
      .filter(p => p.status === 'generating' || p.status === 'queued')
      .map(p => p.podcast_id)
      .join(',');
  }, [podcasts]);

  // Separate useEffect for polling generating podcasts with exponential backoff
  useEffect(() => {
    const hasGenerating = generatingPodcastIds.length > 0;

    if (!hasGenerating) {
      // Reset polling interval when no podcasts are generating
      setPollingInterval(5000);
      return;
    }

    const interval = setInterval(() => {
      loadPodcasts(true); // Silent reload

      // Exponential backoff: 5s -> 10s -> 30s -> 60s (max)
      setPollingInterval(prev => {
        if (prev < 10000) return 10000;  // 5s -> 10s
        if (prev < 30000) return 30000;  // 10s -> 30s
        if (prev < 60000) return 60000;  // 30s -> 60s
        return 60000; // Stay at 60s max
      });
    }, pollingInterval);

    return () => clearInterval(interval);
  }, [generatingPodcastIds, pollingInterval]);

  const loadPodcasts = async (silent: boolean = false) => {
    if (!silent) setIsLoading(true);

    try {
      const userId = user?.id || '';
      const response = await apiClient.listPodcasts(userId);
      setPodcasts(response.podcasts);
    } catch (error) {
      console.error('Error loading podcasts:', error);
      if (!silent) {
        addNotification('error', 'Loading Error', 'Failed to load podcasts.');
      }
      setPodcasts([]);
    } finally {
      if (!silent) setIsLoading(false);
    }
  };

  const loadCollections = async () => {
    setIsLoadingCollections(true);
    try {
      const collectionsData = await apiClient.getCollections();
      setCollections(collectionsData);
    } catch (error) {
      console.error('Error loading collections:', error);
      addNotification(
        'error',
        'Collections Load Error',
        'Failed to load collections. Please refresh the page or contact support if the problem persists.'
      );
      setCollections([]);
    } finally {
      setIsLoadingCollections(false);
    }
  };

  const handleGenerateFromCollection = (collection: Collection) => {
    setSelectedCollectionForGeneration({ id: collection.id, name: collection.name });
    setIsGenerateModalOpen(true);
  };

  const handleDelete = async (podcastId: string, event: React.MouseEvent) => {
    event.stopPropagation();

    if (!window.confirm('Are you sure you want to delete this podcast?')) {
      return;
    }

    try {
      const userId = user?.id || '';
      await apiClient.deletePodcast(podcastId, userId);
      setPodcasts(prev => prev.filter(p => p.podcast_id !== podcastId));
      addNotification('success', 'Podcast Deleted', 'Podcast has been deleted successfully.');
    } catch (error) {
      console.error('Error deleting podcast:', error);
      addNotification('error', 'Delete Error', 'Failed to delete podcast.');
    }
  };

  const handleDownload = async (podcast: Podcast, event: React.MouseEvent) => {
    event.stopPropagation();

    if (!podcast.audio_url) {
      addNotification('error', 'Download Error', 'Audio URL not available.');
      return;
    }

    try {
      // Trigger download
      const link = document.createElement('a');
      link.href = podcast.audio_url;
      link.download = `${podcast.title || 'podcast'}.${podcast.format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      addNotification('success', 'Download Started', 'Your podcast is being downloaded.');
    } catch (error) {
      console.error('Error downloading podcast:', error);
      addNotification('error', 'Download Error', 'Failed to download podcast.');
    }
  };

  const handlePlay = (podcast: Podcast, event: React.MouseEvent) => {
    event.stopPropagation();
    navigate(`/podcasts/${podcast.podcast_id}`);
  };

  const filteredPodcasts = podcasts.filter(podcast => {
    if (filterTab === 'all') return true;
    if (filterTab === 'in-progress') {
      return podcast.status === 'generating' || podcast.status === 'queued';
    }
    if (filterTab === 'completed') {
      return podcast.status === 'completed';
    }
    if (filterTab === 'favorites') {
      // For now, show all completed podcasts as potential favorites
      // In the future, this could check a favorites flag
      return podcast.status === 'completed';
    }
    return true;
  });

  const sortedPodcasts = [...filteredPodcasts].sort((a, b) => {
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  const statusCounts = {
    all: podcasts.length,
    'in-progress': podcasts.filter(p => p.status === 'generating' || p.status === 'queued').length,
    completed: podcasts.filter(p => p.status === 'completed').length,
    favorites: podcasts.filter(p => p.status === 'completed').length, // Placeholder
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-60 mx-auto mb-4"></div>
          <p className="text-gray-70">Loading podcasts...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-10 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold text-gray-100 mb-2">My Podcasts</h1>
          <p className="text-gray-70">
            Generate and manage AI-powered podcasts from your collections
          </p>
        </div>
        <button
          onClick={() => setIsGenerateModalOpen(true)}
          className="btn-primary flex items-center space-x-2"
        >
          <PlusIcon className="w-5 h-5" />
          <span>Generate Podcast</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-4 mb-6 border-b border-gray-20">
        {[
          { key: 'all' as const, label: 'All Podcasts' },
          { key: 'in-progress' as const, label: 'In Progress' },
          { key: 'completed' as const, label: 'Completed' },
          { key: 'favorites' as const, label: 'Favorites' },
        ].map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setFilterTab(key)}
            className={`px-4 py-2 text-sm font-medium transition-colors relative ${
              filterTab === key
                ? 'text-blue-60'
                : 'text-gray-70 hover:text-gray-100'
            }`}
          >
            {label}
            {filterTab === key && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-60" />
            )}
          </button>
        ))}
      </div>

      {/* Podcasts List or Empty State */}
      {sortedPodcasts.length === 0 ? (
        filterTab === 'all' && podcasts.length === 0 ? (
          /* Comprehensive Empty State */
          <div className="flex justify-center items-center min-h-[600px] py-10">
            <div className="max-w-4xl w-full text-center">
              {/* Empty Icon */}
              <div className="text-7xl mb-6 opacity-50">
                <MicrophoneIcon className="w-24 h-24 mx-auto text-gray-50" />
              </div>

              {/* Title & Description */}
              <h2 className="text-3xl font-semibold text-gray-100 mb-4">No podcasts yet</h2>
              <p className="text-gray-70 text-lg mb-10 max-w-2xl mx-auto leading-relaxed">
                Transform your document collections into engaging AI-powered podcasts.
                Select a collection and generate your first podcast to get started.
              </p>

              {/* Collections or No Collections State */}
              {isLoadingCollections ? (
                <div className="text-gray-50">Loading collections...</div>
              ) : collections.length > 0 ? (
                <div>
                  {/* Collection Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 max-w-3xl mx-auto">
                    {collections.slice(0, 3).map((collection) => (
                      <div
                        key={collection.id}
                        className="card p-6 cursor-pointer hover:border-blue-60 transition-all duration-200 group text-left"
                        onClick={() => handleGenerateFromCollection(collection)}
                      >
                        <div className="mb-4">
                          <FolderIcon className="w-8 h-8 text-gray-70 mb-3" />
                        </div>
                        <div className="mb-4">
                          <div className="text-gray-100 font-semibold mb-1 group-hover:text-blue-60 transition-colors duration-200">{collection.name}</div>
                          <div className="text-sm text-gray-70">
                            {collection.documentCount} document{collection.documentCount !== 1 ? 's' : ''} •{' '}
                            Updated {new Date(collection.updatedAt).toLocaleDateString()}
                          </div>
                        </div>
                        <button
                          className="btn-primary w-full text-sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleGenerateFromCollection(collection);
                          }}
                        >
                          Generate Podcast
                        </button>
                      </div>
                    ))}
                  </div>

                  {/* Primary Actions */}
                  <div className="flex gap-4 justify-center mb-12">
                    <button
                      onClick={() => {
                        setSelectedCollectionForGeneration(null);
                        setIsGenerateModalOpen(true);
                      }}
                      className="btn-primary flex items-center space-x-2"
                    >
                      <MicrophoneIcon className="w-5 h-5" />
                      <span>Choose Collection & Generate</span>
                    </button>
                    <button
                      onClick={() => navigate('/collections')}
                      className="btn-secondary flex items-center space-x-2"
                    >
                      <FolderIcon className="w-5 h-5" />
                      <span>Manage Collections</span>
                    </button>
                  </div>
                </div>
              ) : (
                /* No Collections State */
                <div>
                  <div className="bg-yellow-50 bg-opacity-10 border border-yellow-50 rounded-lg p-6 mb-8 max-w-2xl mx-auto">
                    <div className="flex items-start gap-4">
                      <ExclamationTriangleIcon className="w-8 h-8 text-yellow-50 flex-shrink-0 mt-1" />
                      <div className="text-left">
                        <h3 className="text-lg font-semibold text-yellow-50 mb-2">No Collections Found</h3>
                        <p className="text-yellow-40 leading-relaxed">
                          You need at least one collection with documents to generate a podcast.
                          Create a collection and upload your documents first.
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-center mb-12">
                    <button
                      onClick={() => navigate('/collections')}
                      className="btn-primary flex items-center space-x-2"
                    >
                      <FolderIcon className="w-5 h-5" />
                      <span>Create Your First Collection</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          /* Simple Empty State for Filtered Tabs */
          <div className="text-center py-12">
            <p className="text-gray-70 mb-4">
              No {filterTab === 'in-progress' ? 'in progress' : filterTab} podcasts found.
            </p>
          </div>
        )
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sortedPodcasts.map((podcast) => (
            <div
              key={podcast.podcast_id}
              onClick={() => navigate(`/podcasts/${podcast.podcast_id}`)}
              className="card p-6 cursor-pointer hover:border-blue-60 transition-all duration-200 group"
            >
              {/* Show progress card for generating/queued podcasts */}
              {(podcast.status === 'generating' || podcast.status === 'queued') ? (
                <PodcastProgressCard podcast={podcast} />
              ) : (
                <>
                  {/* Title and Status */}
                  <div className="mb-4">
                    <h3 className="text-lg font-semibold text-gray-100 group-hover:text-blue-60 transition-colors duration-200 mb-2">
                      {podcast.title || `Podcast ${podcast.podcast_id.substring(0, 8)}`}
                    </h3>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        podcast.status === 'completed' ? 'bg-green-50 text-white' :
                        podcast.status === 'failed' ? 'bg-red-50 text-white' :
                        'bg-gray-50 text-white'
                      }`}>
                        {podcast.status.toUpperCase()}
                      </span>
                      <span className="text-xs text-gray-70">{podcast.duration} min</span>
                      <span className="text-xs text-gray-70">{podcast.format.toUpperCase()}</span>
                    </div>
                  </div>

                  {/* Creation Date */}
                  <div className="text-sm text-gray-70 mb-4">
                    {new Date(podcast.created_at).toLocaleDateString()} at{' '}
                    {new Date(podcast.created_at).toLocaleTimeString()}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 flex-wrap pt-4 border-t border-gray-20">
                    {podcast.status === 'completed' && (
                      <>
                        <button
                          onClick={(e) => handlePlay(podcast, e)}
                          className="btn-primary flex items-center space-x-1 text-sm"
                        >
                          <PlayIcon className="w-4 h-4" />
                          <span>Play</span>
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/podcasts/${podcast.podcast_id}?tab=chat`);
                          }}
                          className="btn-ghost flex items-center space-x-1 text-sm"
                        >
                          <ChatBubbleLeftRightIcon className="w-4 h-4" />
                          <span>Chat</span>
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/podcasts/${podcast.podcast_id}?tab=transcript`);
                          }}
                          className="btn-ghost flex items-center space-x-1 text-sm"
                        >
                          <DocumentTextIcon className="w-4 h-4" />
                          <span>Transcript</span>
                        </button>
                      </>
                    )}
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Getting Started Guide - Always Shown */}
      <div className="mt-12 bg-white border border-gray-20 rounded-lg p-8 max-w-5xl mx-auto shadow-sm">
        <h3 className="text-xl font-semibold text-gray-100 mb-6 flex items-center justify-center gap-2">
          <span>🚀</span>
          Getting Started
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            {
              number: 1,
              title: 'Upload Documents',
              description: 'Add PDFs, docs, or text files to your collections',
              icon: <DocumentIcon className="w-6 h-6" />
            },
            {
              number: 2,
              title: 'Generate Podcast',
              description: 'AI creates engaging audio discussions from your content',
              icon: <MicrophoneIcon className="w-6 h-6" />
            },
            {
              number: 3,
              title: 'Interact & Refine',
              description: 'Ask questions to dynamically update your podcasts',
              icon: <ChatBubbleLeftRightIcon className="w-6 h-6" />
            }
          ].map((tip) => (
            <div key={tip.number} className="flex items-start gap-4 text-left">
              <div className="w-10 h-10 bg-blue-60 text-white rounded-full flex items-center justify-center font-bold flex-shrink-0">
                {tip.number}
              </div>
              <div>
                <div className="text-gray-100 font-semibold mb-1">{tip.title}</div>
                <div className="text-sm text-gray-70 leading-relaxed">{tip.description}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Podcast Generation Modal */}
      <PodcastGenerationModal
        isOpen={isGenerateModalOpen}
        onClose={() => {
          setIsGenerateModalOpen(false);
          setSelectedCollectionForGeneration(null);
        }}
        collectionId={selectedCollectionForGeneration?.id}
        collectionName={selectedCollectionForGeneration?.name}
        onPodcastCreated={() => {
          setIsGenerateModalOpen(false);
          setSelectedCollectionForGeneration(null);
          loadPodcasts();
        }}
      />
    </div>
  );
};

export default LightweightPodcasts;
