import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  PlayIcon,
  TrashIcon,
  ArrowDownTrayIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline';
import { useNotification } from '../../contexts/NotificationContext';
import apiClient, { Podcast } from '../../services/apiClient';
import PodcastProgressCard from './PodcastProgressCard';

const LightweightPodcasts: React.FC = () => {
  const { addNotification } = useNotification();
  const navigate = useNavigate();
  const [podcasts, setPodcasts] = useState<Podcast[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'date' | 'duration'>('date');

  useEffect(() => {
    loadPodcasts();

    // Poll for updates every 5 seconds if there are generating podcasts
    const interval = setInterval(() => {
      const hasGenerating = podcasts.some(p => p.status === 'generating' || p.status === 'queued');
      if (hasGenerating) {
        loadPodcasts(true); // Silent reload
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [podcasts]);

  const loadPodcasts = async (silent: boolean = false) => {
    if (!silent) setIsLoading(true);

    try {
      const userId = localStorage.getItem('user_id') || '';
      const response = await apiClient.listPodcasts(userId);
      setPodcasts(response.podcasts);

      if (!silent) {
        addNotification('success', 'Podcasts Loaded', 'Your podcasts have been loaded successfully.');
      }
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

  const handleDelete = async (podcastId: string, event: React.MouseEvent) => {
    event.stopPropagation();

    if (!window.confirm('Are you sure you want to delete this podcast?')) {
      return;
    }

    try {
      const userId = localStorage.getItem('user_id') || '';
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
    if (filterStatus === 'all') return true;
    return podcast.status === filterStatus;
  });

  const sortedPodcasts = [...filteredPodcasts].sort((a, b) => {
    if (sortBy === 'date') {
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    } else {
      return b.duration - a.duration;
    }
  });

  const statusCounts = {
    all: podcasts.length,
    queued: podcasts.filter(p => p.status === 'queued').length,
    generating: podcasts.filter(p => p.status === 'generating').length,
    completed: podcasts.filter(p => p.status === 'completed').length,
    failed: podcasts.filter(p => p.status === 'failed').length,
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-blue-50 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white mb-2">My Podcasts</h1>
        <p className="text-gray-50">
          Manage and listen to your generated podcasts
        </p>
      </div>

      {/* Filters and Sort */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <FunnelIcon className="w-5 h-5 text-gray-50" />
          <div className="flex gap-2">
            {[
              { key: 'all', label: 'All' },
              { key: 'completed', label: 'Completed' },
              { key: 'generating', label: 'Generating' },
              { key: 'queued', label: 'Queued' },
              { key: 'failed', label: 'Failed' },
            ].map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setFilterStatus(key)}
                className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                  filterStatus === key
                    ? 'bg-blue-50 text-white'
                    : 'bg-gray-90 text-gray-50 hover:text-white'
                }`}
              >
                {label} ({statusCounts[key as keyof typeof statusCounts]})
              </button>
            ))}
          </div>
        </div>

        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as 'date' | 'duration')}
          className="px-3 py-1 bg-gray-90 border border-gray-30 rounded-lg text-white text-sm"
        >
          <option value="date">Sort by Date</option>
          <option value="duration">Sort by Duration</option>
        </select>
      </div>

      {/* Podcasts List */}
      {sortedPodcasts.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-50 mb-4">
            {filterStatus === 'all'
              ? 'No podcasts yet. Generate your first podcast from a collection!'
              : `No ${filterStatus} podcasts found.`
            }
          </p>
          {filterStatus === 'all' && (
            <button
              onClick={() => navigate('/collections')}
              className="px-4 py-2 bg-blue-50 hover:bg-blue-40 text-white rounded-lg transition-colors"
            >
              Go to Collections
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sortedPodcasts.map((podcast) => (
            <div
              key={podcast.podcast_id}
              onClick={() => navigate(`/podcasts/${podcast.podcast_id}`)}
              className="bg-gray-90 border border-gray-30 rounded-lg p-4 hover:border-blue-50 transition-colors cursor-pointer"
            >
              {/* Show progress card for generating/queued podcasts */}
              {(podcast.status === 'generating' || podcast.status === 'queued') ? (
                <PodcastProgressCard podcast={podcast} />
              ) : (
                <>
                  {/* Title and Status */}
                  <div className="mb-3">
                    <h3 className="text-white font-medium mb-1">
                      {podcast.title || `Podcast ${podcast.podcast_id.substring(0, 8)}`}
                    </h3>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        podcast.status === 'completed' ? 'bg-green-50 text-white' :
                        podcast.status === 'failed' ? 'bg-red-50 text-white' :
                        'bg-gray-50 text-white'
                      }`}>
                        {podcast.status.toUpperCase()}
                      </span>
                      <span className="text-xs text-gray-50">{podcast.duration} min</span>
                      <span className="text-xs text-gray-50">{podcast.format.toUpperCase()}</span>
                    </div>
                  </div>

                  {/* Creation Date */}
                  <div className="text-xs text-gray-50 mb-3">
                    {new Date(podcast.created_at).toLocaleDateString()} at{' '}
                    {new Date(podcast.created_at).toLocaleTimeString()}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    {podcast.status === 'completed' && (
                      <>
                        <button
                          onClick={(e) => handlePlay(podcast, e)}
                          className="flex items-center gap-1 px-3 py-1.5 bg-blue-50 hover:bg-blue-40 text-white rounded text-sm transition-colors"
                        >
                          <PlayIcon className="w-4 h-4" />
                          Play
                        </button>
                        <button
                          onClick={(e) => handleDownload(podcast, e)}
                          className="flex items-center gap-1 px-3 py-1.5 bg-gray-30 hover:bg-gray-40 text-white rounded text-sm transition-colors"
                        >
                          <ArrowDownTrayIcon className="w-4 h-4" />
                          Download
                        </button>
                      </>
                    )}
                    <button
                      onClick={(e) => handleDelete(podcast.podcast_id, e)}
                      className="flex items-center gap-1 px-3 py-1.5 bg-red-50 hover:bg-red-40 text-white rounded text-sm transition-colors ml-auto"
                    >
                      <TrashIcon className="w-4 h-4" />
                      Delete
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default LightweightPodcasts;
