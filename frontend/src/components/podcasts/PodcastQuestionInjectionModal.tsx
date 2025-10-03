import React, { useState } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { useNotification } from '../../contexts/NotificationContext';
import apiClient, { PodcastQuestionInjection } from '../../services/apiClient';

interface PodcastQuestionInjectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  podcastId: string;
  currentTimestamp: number;
  onQuestionInjected?: () => void;
}

const PodcastQuestionInjectionModal: React.FC<PodcastQuestionInjectionModalProps> = ({
  isOpen,
  onClose,
  podcastId,
  currentTimestamp,
  onQuestionInjected,
}) => {
  const { addNotification } = useNotification();
  const [question, setQuestion] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const formatTimestamp = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleSubmit = async () => {
    if (!question.trim()) {
      addNotification('error', 'Validation Error', 'Please enter a question.');
      return;
    }

    setIsSubmitting(true);
    try {
      const userId = localStorage.getItem('user_id') || '';

      const injection: PodcastQuestionInjection = {
        podcast_id: podcastId,
        timestamp_seconds: Math.floor(currentTimestamp),
        question: question.trim(),
        user_id: userId,
      };

      await apiClient.injectQuestion(injection);

      addNotification(
        'success',
        'Question Injected',
        'Your question has been added to the podcast. The podcast will be dynamically regenerated.'
      );

      if (onQuestionInjected) {
        onQuestionInjected();
      }

      setQuestion('');
      onClose();
    } catch (error: any) {
      console.error('Error injecting question:', error);
      addNotification(
        'error',
        'Injection Failed',
        error.response?.data?.detail || 'Failed to inject question into podcast.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-gray-100 rounded-lg shadow-xl w-full max-w-md">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-30">
          <div>
            <h2 className="text-xl font-semibold text-white">Add Question to Podcast</h2>
            <p className="text-sm text-gray-50 mt-1">
              Timestamp: {formatTimestamp(currentTimestamp)}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-50 hover:text-white transition-colors"
          >
            <XMarkIcon className="w-6 h-6" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-white mb-2">
              Your Question
            </label>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              rows={4}
              placeholder="What question would you like to add to the podcast at this point?"
              className="w-full px-4 py-2 bg-gray-90 border border-gray-30 rounded-lg text-white placeholder-gray-50 focus:outline-none focus:border-blue-50 resize-none"
              autoFocus
            />
            <p className="text-xs text-gray-50 mt-1">
              The podcast will be dynamically adjusted to include this question and answer.
            </p>
          </div>

          {/* Info Banner */}
          <div className="bg-blue-50 bg-opacity-10 border border-blue-50 rounded-lg p-3">
            <div className="text-sm text-white">
              <strong>How it works:</strong>
            </div>
            <ul className="text-xs text-gray-50 mt-1 space-y-1 ml-4 list-disc">
              <li>Your question will be inserted at {formatTimestamp(currentTimestamp)}</li>
              <li>The HOST will ask your question</li>
              <li>The EXPERT will provide a detailed answer using RAG</li>
              <li>Audio will be regenerated from this point onwards</li>
              <li>This may take 30-60 seconds</li>
            </ul>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-30">
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="px-4 py-2 text-gray-50 hover:text-white transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={isSubmitting || !question.trim()}
            className="px-6 py-2 bg-blue-50 hover:bg-blue-40 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? 'Adding Question...' : 'Add Question'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default PodcastQuestionInjectionModal;
