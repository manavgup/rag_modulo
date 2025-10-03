import React from 'react';
import {
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { Podcast } from '../../services/apiClient';

interface PodcastProgressCardProps {
  podcast: Podcast;
  onCancel?: (podcastId: string) => void;
}

const STEP_LABELS: Record<string, string> = {
  retrieving_content: 'Retrieving content from collection',
  generating_script: 'Generating podcast script',
  parsing_turns: 'Parsing dialogue turns',
  generating_audio: 'Generating multi-voice audio',
  storing_audio: 'Storing audio file',
};

const PodcastProgressCard: React.FC<PodcastProgressCardProps> = ({ podcast, onCancel }) => {
  const getStatusIcon = () => {
    switch (podcast.status) {
      case 'completed':
        return <CheckCircleIcon className="w-6 h-6 text-green-50" />;
      case 'failed':
      case 'cancelled':
        return <XCircleIcon className="w-6 h-6 text-red-50" />;
      case 'queued':
        return <ClockIcon className="w-6 h-6 text-blue-50" />;
      case 'generating':
        return (
          <div className="w-6 h-6 border-2 border-yellow-30 border-t-transparent rounded-full animate-spin" />
        );
      default:
        return null;
    }
  };

  const getStatusBadge = () => {
    switch (podcast.status) {
      case 'completed':
        return 'bg-green-50 text-white';
      case 'failed':
        return 'bg-red-50 text-white';
      case 'cancelled':
        return 'bg-gray-50 text-white';
      case 'queued':
        return 'bg-blue-50 text-white';
      case 'generating':
        return 'bg-yellow-30 text-gray-100';
      default:
        return 'bg-gray-50 text-white';
    }
  };

  const formatTimeRemaining = (seconds: number | undefined) => {
    if (!seconds) return null;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const currentStepLabel = podcast.current_step
    ? STEP_LABELS[podcast.current_step] || podcast.current_step
    : '';

  const showStepDetails = podcast.status === 'generating' && podcast.step_details;

  return (
    <div className="bg-gray-90 border border-gray-30 rounded-lg p-4">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3 flex-1">
          {getStatusIcon()}
          <div className="flex-1">
            <h3 className="text-white font-medium">
              {podcast.title || `Podcast from ${podcast.collection_id.substring(0, 8)}`}
            </h3>
            <div className="flex items-center gap-2 mt-1">
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${getStatusBadge()}`}>
                {podcast.status.toUpperCase()}
              </span>
              <span className="text-xs text-gray-50">{podcast.duration} min</span>
            </div>
          </div>
        </div>

        {podcast.status === 'generating' && onCancel && (
          <button
            onClick={() => onCancel(podcast.podcast_id)}
            className="text-gray-50 hover:text-red-50 text-sm transition-colors"
          >
            Cancel
          </button>
        )}
      </div>

      {/* Progress Bar (for generating/queued) */}
      {(podcast.status === 'generating' || podcast.status === 'queued') && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-50">
              {currentStepLabel || 'Waiting in queue...'}
            </span>
            <span className="text-sm text-white font-medium">
              {podcast.progress_percentage}%
            </span>
          </div>
          <div className="w-full h-2 bg-gray-30 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-300 ${
                podcast.status === 'generating' ? 'bg-yellow-30' : 'bg-blue-50'
              }`}
              style={{ width: `${podcast.progress_percentage}%` }}
            />
          </div>
        </div>
      )}

      {/* Step Details (for audio generation) */}
      {showStepDetails && podcast.current_step === 'generating_audio' && (
        <div className="mb-3 p-3 bg-gray-100 rounded-lg">
          <div className="text-xs text-gray-50 mb-1">Audio Generation Progress</div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-white">
              Turn {podcast.step_details!.completed_turns || 0} of{' '}
              {podcast.step_details!.total_turns || '?'}
            </span>
            {podcast.step_details!.current_speaker && (
              <span className="text-xs text-gray-50">
                Speaker: {podcast.step_details!.current_speaker}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Time Remaining */}
      {podcast.status === 'generating' && podcast.estimated_time_remaining && (
        <div className="flex items-center gap-2 text-sm text-gray-50">
          <ClockIcon className="w-4 h-4" />
          <span>Est. {formatTimeRemaining(podcast.estimated_time_remaining)} remaining</span>
        </div>
      )}

      {/* Error Message */}
      {podcast.status === 'failed' && podcast.error_message && (
        <div className="flex items-start gap-2 p-3 bg-red-50 bg-opacity-10 border border-red-50 rounded-lg">
          <ExclamationTriangleIcon className="w-5 h-5 text-red-50 flex-shrink-0 mt-0.5" />
          <div>
            <div className="text-sm font-medium text-red-50">Generation Failed</div>
            <div className="text-xs text-gray-50 mt-1">{podcast.error_message}</div>
          </div>
        </div>
      )}

      {/* Completed Info */}
      {podcast.status === 'completed' && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-50">
            {podcast.audio_size_bytes
              ? `${(podcast.audio_size_bytes / (1024 * 1024)).toFixed(2)} MB`
              : 'Ready to play'}
          </span>
          <span className="text-green-50">✓ Complete</span>
        </div>
      )}
    </div>
  );
};

export default PodcastProgressCard;
