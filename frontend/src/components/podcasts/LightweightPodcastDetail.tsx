import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeftIcon,
  ArrowDownTrayIcon,
  TrashIcon,
  ShareIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import { useNotification } from '../../contexts/NotificationContext';
import apiClient, { Podcast } from '../../services/apiClient';
import PodcastAudioPlayer from './PodcastAudioPlayer';
import PodcastTranscriptViewer from './PodcastTranscriptViewer';
import PodcastQuestionInjectionModal from './PodcastQuestionInjectionModal';
import PodcastProgressCard from './PodcastProgressCard';

const LightweightPodcastDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addNotification } = useNotification();

  const [podcast, setPodcast] = useState<Podcast | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [isQuestionModalOpen, setIsQuestionModalOpen] = useState(false);
  const [questionTimestamp, setQuestionTimestamp] = useState(0);
  const [showTranscript, setShowTranscript] = useState(true);

  useEffect(() => {
    loadPodcast();

    // Poll for updates if podcast is generating
    const interval = setInterval(() => {
      if (podcast?.status === 'generating' || podcast?.status === 'queued') {
        loadPodcast(true); // Silent reload
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [id, podcast?.status]);

  const loadPodcast = async (silent: boolean = false) => {
    if (!silent) setIsLoading(true);

    try {
      const userId = localStorage.getItem('user_id') || '';
      const podcastData = await apiClient.getPodcast(id!, userId);
      setPodcast(podcastData);
    } catch (error) {
      console.error('Error loading podcast:', error);
      addNotification('error', 'Loading Error', 'Failed to load podcast details.');
      navigate('/podcasts');
    } finally {
      if (!silent) setIsLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this podcast?')) {
      return;
    }

    try {
      const userId = localStorage.getItem('user_id') || '';
      await apiClient.deletePodcast(id!, userId);
      addNotification('success', 'Podcast Deleted', 'Podcast has been deleted successfully.');
      navigate('/podcasts');
    } catch (error) {
      console.error('Error deleting podcast:', error);
      addNotification('error', 'Delete Error', 'Failed to delete podcast.');
    }
  };

  const handleDownload = () => {
    if (!podcast?.audio_url) {
      addNotification('error', 'Download Error', 'Audio URL not available.');
      return;
    }

    try {
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

  const handleShare = async () => {
    const shareUrl = window.location.href;

    if (navigator.share) {
      try {
        await navigator.share({
          title: podcast?.title || 'Podcast',
          text: 'Check out this podcast!',
          url: shareUrl,
        });
        addNotification('success', 'Shared', 'Podcast link shared successfully.');
      } catch (error) {
        console.error('Error sharing:', error);
      }
    } else {
      // Fallback: Copy to clipboard
      navigator.clipboard.writeText(shareUrl);
      addNotification('success', 'Link Copied', 'Podcast link copied to clipboard.');
    }
  };

  const handleTimeUpdate = (time: number) => {
    setCurrentTime(time);
  };

  const handleQuestionClick = (timestamp: number) => {
    setQuestionTimestamp(timestamp);
    setIsQuestionModalOpen(true);
  };

  const handleQuestionInjected = () => {
    addNotification(
      'info',
      'Regenerating Podcast',
      'Your podcast is being regenerated with the new question. This may take a moment.'
    );
    loadPodcast(true);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="w-8 h-8 border-2 border-blue-50 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!podcast) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <p className="text-white mb-4">Podcast not found</p>
          <button
            onClick={() => navigate('/podcasts')}
            className="px-4 py-2 bg-blue-50 hover:bg-blue-40 text-white rounded-lg transition-colors"
          >
            Back to Podcasts
          </button>
        </div>
      </div>
    );
  }

  const isGenerating = podcast.status === 'generating' || podcast.status === 'queued';
  const isCompleted = podcast.status === 'completed';

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Back Button */}
      <button
        onClick={() => navigate('/podcasts')}
        className="flex items-center gap-2 text-gray-50 hover:text-white mb-6 transition-colors"
      >
        <ArrowLeftIcon className="w-5 h-5" />
        Back to Podcasts
      </button>

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white mb-2">
          {podcast.title || `Podcast ${podcast.podcast_id.substring(0, 8)}`}
        </h1>
        <div className="flex items-center gap-3">
          <span className={`px-3 py-1 rounded text-sm font-medium ${
            podcast.status === 'completed' ? 'bg-green-50 text-white' :
            podcast.status === 'failed' ? 'bg-red-50 text-white' :
            podcast.status === 'generating' ? 'bg-yellow-30 text-gray-100' :
            podcast.status === 'queued' ? 'bg-blue-50 text-white' :
            'bg-gray-50 text-white'
          }`}>
            {podcast.status.toUpperCase()}
          </span>
          <span className="text-gray-50">{podcast.duration} minutes</span>
          <span className="text-gray-50">{podcast.format.toUpperCase()}</span>
          {podcast.audio_size_bytes && (
            <span className="text-gray-50">
              {(podcast.audio_size_bytes / (1024 * 1024)).toFixed(2)} MB
            </span>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 mb-6">
        {isCompleted && (
          <>
            <button
              onClick={handleDownload}
              className="flex items-center gap-2 px-4 py-2 bg-blue-50 hover:bg-blue-40 text-white rounded-lg transition-colors"
            >
              <ArrowDownTrayIcon className="w-5 h-5" />
              Download
            </button>
            <button
              onClick={handleShare}
              className="flex items-center gap-2 px-4 py-2 bg-gray-30 hover:bg-gray-40 text-white rounded-lg transition-colors"
            >
              <ShareIcon className="w-5 h-5" />
              Share
            </button>
            <button
              onClick={() => setShowTranscript(!showTranscript)}
              className="flex items-center gap-2 px-4 py-2 bg-gray-30 hover:bg-gray-40 text-white rounded-lg transition-colors"
            >
              <DocumentTextIcon className="w-5 h-5" />
              {showTranscript ? 'Hide' : 'Show'} Transcript
            </button>
          </>
        )}
        <button
          onClick={handleDelete}
          className="flex items-center gap-2 px-4 py-2 bg-red-50 hover:bg-red-40 text-white rounded-lg transition-colors ml-auto"
        >
          <TrashIcon className="w-5 h-5" />
          Delete
        </button>
      </div>

      {/* Content */}
      {isGenerating ? (
        <PodcastProgressCard podcast={podcast} />
      ) : podcast.status === 'failed' ? (
        <div className="bg-red-50 bg-opacity-10 border border-red-50 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-red-50 mb-2">Generation Failed</h2>
          <p className="text-gray-50">
            {podcast.error_message || 'An error occurred during podcast generation.'}
          </p>
        </div>
      ) : isCompleted ? (
        <div className="space-y-6">
          {/* Audio Player */}
          {podcast.audio_url && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-3">Audio Player</h2>
              <PodcastAudioPlayer
                audioUrl={podcast.audio_url}
                onTimeUpdate={handleTimeUpdate}
                onQuestionClick={handleQuestionClick}
              />
            </div>
          )}

          {/* Transcript */}
          {showTranscript && podcast.transcript && (
            <div>
              <h2 className="text-xl font-semibold text-white mb-3">Transcript</h2>
              <PodcastTranscriptViewer
                transcript={podcast.transcript}
                currentTime={currentTime}
              />
            </div>
          )}

          {/* Metadata */}
          <div className="bg-gray-90 border border-gray-30 rounded-lg p-4">
            <h3 className="text-lg font-semibold text-white mb-3">Metadata</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-50">Created:</span>
                <span className="text-white ml-2">
                  {new Date(podcast.created_at).toLocaleString()}
                </span>
              </div>
              <div>
                <span className="text-gray-50">Completed:</span>
                <span className="text-white ml-2">
                  {podcast.completed_at
                    ? new Date(podcast.completed_at).toLocaleString()
                    : 'N/A'}
                </span>
              </div>
              <div>
                <span className="text-gray-50">Collection ID:</span>
                <span className="text-white ml-2">{podcast.collection_id.substring(0, 8)}...</span>
              </div>
              <div>
                <span className="text-gray-50">Podcast ID:</span>
                <span className="text-white ml-2">{podcast.podcast_id.substring(0, 8)}...</span>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {/* Question Injection Modal */}
      <PodcastQuestionInjectionModal
        isOpen={isQuestionModalOpen}
        onClose={() => setIsQuestionModalOpen(false)}
        podcastId={podcast.podcast_id}
        currentTimestamp={questionTimestamp}
        onQuestionInjected={handleQuestionInjected}
      />
    </div>
  );
};

export default LightweightPodcastDetail;
