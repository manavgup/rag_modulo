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
import { useAuth } from '../../contexts/AuthContext';
import apiClient, { Podcast } from '../../services/apiClient';
import PodcastAudioPlayer from './PodcastAudioPlayer';
import PodcastTranscriptViewer from './PodcastTranscriptViewer';
import PodcastQuestionInjectionModal from './PodcastQuestionInjectionModal';
import PodcastProgressCard from './PodcastProgressCard';

const LightweightPodcastDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addNotification } = useNotification();
  const { user } = useAuth();

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
      const userId = user?.id || '';
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
      const userId = user?.id || '';
      await apiClient.deletePodcast(id!, userId);
      addNotification('success', 'Podcast Deleted', 'Podcast has been deleted successfully.');
      navigate('/podcasts');
    } catch (error) {
      console.error('Error deleting podcast:', error);
      addNotification('error', 'Delete Error', 'Failed to delete podcast.');
    }
  };

  const handleDownload = async () => {
    if (!podcast?.audio_url || !id) {
      addNotification('error', 'Download Error', 'Audio URL not available.');
      return;
    }

    try {
      // Get the auth token
      const token = localStorage.getItem('token') || 'dev-bypass-auth';

      // Fetch the audio file with authentication
      const response = await fetch(podcast.audio_url, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Get the blob data
      const blob = await response.blob();

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${podcast.title || 'podcast'}.${podcast.format}`;
      document.body.appendChild(link);
      link.click();

      // Cleanup
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

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

  const handleChapterClick = (startTime: number) => {
    // Seek the audio player to the specified time
    const audioElement = document.querySelector('audio') as HTMLAudioElement;
    if (audioElement) {
      audioElement.currentTime = startTime;
      setCurrentTime(startTime);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-10">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-60 mx-auto mb-4"></div>
          <p className="text-gray-70">Loading podcast...</p>
        </div>
      </div>
    );
  }

  if (!podcast) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-10">
        <div className="text-center">
          <p className="text-gray-100 mb-4">Podcast not found</p>
          <button
            onClick={() => navigate('/podcasts')}
            className="btn-primary"
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
    <div className="min-h-screen bg-gray-10 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Back Button */}
        <button
          onClick={() => navigate('/podcasts')}
          className="flex items-center space-x-2 text-gray-70 hover:text-gray-100 mb-6 transition-colors"
        >
          <ArrowLeftIcon className="w-5 h-5" />
          <span>Back to Podcasts</span>
        </button>

        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-semibold text-gray-100 mb-2">
            {podcast.title || `Podcast ${podcast.podcast_id.substring(0, 8)}`}
          </h1>
          <div className="flex items-center gap-3">
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
              podcast.status === 'completed' ? 'bg-green-50 text-white' :
              podcast.status === 'failed' ? 'bg-red-50 text-white' :
              podcast.status === 'generating' ? 'bg-yellow-30 text-gray-100' :
              podcast.status === 'queued' ? 'bg-blue-60 text-white' :
              'bg-gray-50 text-white'
            }`}>
              {podcast.status.toUpperCase()}
            </span>
            <span className="text-sm text-gray-70">{podcast.duration} minutes</span>
            <span className="text-sm text-gray-70">{podcast.format.toUpperCase()}</span>
            {podcast.audio_size_bytes && (
              <span className="text-sm text-gray-70">
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
                className="bg-blue-60 hover:bg-blue-70 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
              >
                <ArrowDownTrayIcon className="w-5 h-5" />
                <span>Download</span>
              </button>
              <button
                onClick={handleShare}
                className="border border-gray-30 hover:border-gray-50 text-gray-100 px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
              >
                <ShareIcon className="w-5 h-5" />
                <span>Share</span>
              </button>
              <button
                onClick={() => setShowTranscript(!showTranscript)}
                className="border border-gray-30 hover:border-gray-50 text-gray-100 px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
              >
                <DocumentTextIcon className="w-5 h-5" />
                <span>{showTranscript ? 'Hide' : 'Show'} Transcript</span>
              </button>
            </>
          )}
          <button
            onClick={handleDelete}
            className="flex items-center space-x-2 px-4 py-2 bg-red-50 hover:bg-red-40 text-white rounded-md transition-colors ml-auto"
          >
            <TrashIcon className="w-5 h-5" />
            <span>Delete</span>
          </button>
        </div>

        {/* Content */}
        {isGenerating ? (
          <PodcastProgressCard podcast={podcast} />
        ) : podcast.status === 'failed' ? (
          <div className="bg-red-50 bg-opacity-10 border border-red-50 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-red-50 mb-2">Generation Failed</h2>
            <p className="text-gray-70">
              {podcast.error_message || 'An error occurred during podcast generation.'}
            </p>
          </div>
        ) : isCompleted ? (
          <div className="space-y-6">
            {/* Two-Column Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column - Audio Player & Transcript */}
              <div className="lg:col-span-2 space-y-6">
                {/* Audio Player */}
                {podcast.audio_url && (
                  <div className="card p-6">
                    <h2 className="text-xl font-semibold text-gray-100 mb-4">Audio Player</h2>
                    <PodcastAudioPlayer
                      audioUrl={podcast.audio_url}
                      onTimeUpdate={handleTimeUpdate}
                      onQuestionClick={handleQuestionClick}
                    />
                  </div>
                )}

                {/* Transcript */}
                {showTranscript && podcast.transcript && (
                  <div className="card p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h2 className="text-xl font-semibold text-gray-100">Transcript</h2>
                      <button
                        onClick={() => setShowTranscript(false)}
                        className="text-sm text-gray-70 hover:text-gray-100 transition-colors"
                      >
                        Hide Transcript
                      </button>
                    </div>
                    <PodcastTranscriptViewer
                      transcript={podcast.transcript}
                      currentTime={currentTime}
                    />
                  </div>
                )}
              </div>

              {/* Right Column - Chapters, Key Points, Metadata */}
              <div className="space-y-6">
                {/* Chapters */}
                <div className="card p-6">
                  <h3 className="text-lg font-medium text-gray-100 mb-4">Chapters</h3>
                  <div className="space-y-3">
                    <div
                      className="p-3 border border-blue-60 rounded-lg bg-blue-60 bg-opacity-10 cursor-pointer hover:bg-blue-60 hover:bg-opacity-20 transition-colors"
                      onClick={() => handleChapterClick(0)}
                    >
                      <div className="text-sm text-blue-60 font-medium">00:00 - 01:00</div>
                      <div className="text-gray-100 text-sm">Introduction & Welcome</div>
                    </div>
                    <div
                      className="p-3 border border-gray-30 rounded-lg hover:border-gray-50 transition-colors cursor-pointer"
                      onClick={() => handleChapterClick(60)}
                    >
                      <div className="text-sm text-gray-70">01:00 - 02:30</div>
                      <div className="text-gray-100 text-sm">IBM's Technology Stack Overview</div>
                    </div>
                    <div
                      className="p-3 border border-gray-30 rounded-lg hover:border-gray-50 transition-colors cursor-pointer"
                      onClick={() => handleChapterClick(150)}
                    >
                      <div className="text-sm text-gray-70">02:30 - 04:00</div>
                      <div className="text-gray-100 text-sm">Strategic Evolution</div>
                    </div>
                    <div
                      className="p-3 border border-gray-30 rounded-lg hover:border-gray-50 transition-colors cursor-pointer"
                      onClick={() => handleChapterClick(240)}
                    >
                      <div className="text-sm text-gray-70">04:00 - 06:00</div>
                      <div className="text-gray-100 text-sm">Future Investments & Focus Areas</div>
                    </div>
                  </div>
                </div>

                {/* Key Points */}
                <div className="card p-6">
                  <div className="flex items-center mb-4">
                    <div className="w-5 h-5 mr-2 text-yellow-60">💡</div>
                    <h3 className="text-lg font-medium text-gray-100">Key Points</h3>
                  </div>
                  <div className="space-y-3 text-sm">
                    <div className="flex items-start">
                      <span className="text-blue-60 font-medium mr-2">1.</span>
                      <span className="text-gray-100">
                        IBM offers comprehensive technology stack including hybrid cloud, AI, and quantum computing
                      </span>
                    </div>
                    <div className="flex items-start">
                      <span className="text-blue-60 font-medium mr-2">2.</span>
                      <span className="text-gray-100">
                        Strategic shift from hardware to hybrid cloud and AI services
                      </span>
                    </div>
                    <div className="flex items-start">
                      <span className="text-blue-60 font-medium mr-2">3.</span>
                      <span className="text-gray-100">
                        Red Hat acquisition was pivotal for hybrid cloud leadership
                      </span>
                    </div>
                    <div className="flex items-start">
                      <span className="text-blue-60 font-medium mr-2">4.</span>
                      <span className="text-gray-100">
                        Future focus on quantum computing, trustworthy AI, and hybrid cloud
                      </span>
                    </div>
                  </div>
                </div>

                {/* Metadata */}
                <div className="card p-6">
                  <div className="flex items-center mb-4">
                    <div className="w-5 h-5 mr-2 text-blue-60">📊</div>
                    <h3 className="text-lg font-medium text-gray-100">Metadata</h3>
                  </div>
                  <div className="space-y-3 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-70">Format</span>
                      <span className="text-gray-100">MP3</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-70">Bitrate</span>
                      <span className="text-gray-100">128 kbps</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-70">Duration</span>
                      <span className="text-gray-100">
                        {Math.round((podcast.duration || 0) / 60)} minutes
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-70">Collection</span>
                      <span className="text-gray-100">{podcast.collection_name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-70">Voices</span>
                      <span className="text-gray-100">
                        {podcast.host_voice} & {podcast.expert_voice}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-70">Created</span>
                      <span className="text-gray-100">
                        {new Date(podcast.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-70">Size</span>
                      <span className="text-gray-100">
                        {podcast.audio_size_bytes ? `${(podcast.audio_size_bytes / 1024 / 1024).toFixed(1)} MB` : 'N/A'}
                      </span>
                    </div>
                  </div>
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
    </div>
  );
};

export default LightweightPodcastDetail;
