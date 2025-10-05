import React, { useState, useEffect, useCallback } from 'react';
import apiClient, { SuggestedQuestion } from '../../services/apiClient';
import { useNotification } from '../../contexts/NotificationContext';
import { LightBulbIcon, ArrowPathIcon } from '@heroicons/react/24/outline';

interface SuggestedQuestionsProps {
  collectionId: string;
  onQuestionClick: (question: string) => void;
}

const SuggestedQuestions: React.FC<SuggestedQuestionsProps> = ({ collectionId, onQuestionClick }) => {
  const [questions, setQuestions] = useState<SuggestedQuestion[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { addNotification } = useNotification();

  const fetchQuestions = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const fetchedQuestions = await apiClient.getSuggestedQuestions(collectionId);
      setQuestions(fetchedQuestions);
    } catch (err) {
      setError('Failed to load suggested questions.');
      addNotification('error', 'Error', 'Could not fetch suggested questions.');
    } finally {
      setIsLoading(false);
    }
  }, [collectionId, addNotification]);

  useEffect(() => {
    fetchQuestions();
  }, [fetchQuestions]);

  const handleRefresh = () => {
    fetchQuestions();
  };

  if (isLoading) {
    return (
      <div className="p-4 bg-gray-20 rounded-lg animate-pulse">
        <div className="h-4 bg-gray-30 rounded w-1/4 mb-2"></div>
        <div className="flex flex-wrap gap-2">
          <div className="h-8 bg-gray-30 rounded-full w-32"></div>
          <div className="h-8 bg-gray-30 rounded-full w-48"></div>
          <div className="h-8 bg-gray-30 rounded-full w-40"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-10 border border-red-20 rounded-lg text-red-70">
        <p>{error}</p>
        <button
          onClick={handleRefresh}
          className="mt-2 px-3 py-1 bg-red-50 text-white rounded-md hover:bg-red-60 text-sm"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (questions.length === 0) {
    return (
        <div className="p-4 bg-gray-20 rounded-lg">
            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center text-sm font-semibold text-gray-80">
                    <LightBulbIcon className="w-5 h-5 mr-2" />
                    <span>Suggested Questions</span>
                </div>
                <button
                onClick={handleRefresh}
                className="p-1 text-gray-60 hover:text-gray-90"
                title="Refresh suggested questions"
                >
                <ArrowPathIcon className="w-4 h-4" />
                </button>
            </div>
            <p className="text-sm text-gray-60">No suggested questions available at the moment. Questions will be generated automatically after document processing is complete.</p>
      </div>
    );
  }

  return (
    <div className="p-4 bg-gray-20 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center text-sm font-semibold text-gray-80">
          <LightBulbIcon className="w-5 h-5 mr-2" />
          <span>Suggested Questions</span>
        </div>
        <button
          onClick={handleRefresh}
          className="p-1 text-gray-60 hover:text-gray-90"
          title="Refresh suggested questions"
        >
          <ArrowPathIcon className="w-4 h-4" />
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        {questions.map((q) => (
          <button
            key={q.id}
            onClick={() => onQuestionClick(q.question)}
            className="px-3 py-1.5 bg-blue-10 text-blue-70 rounded-full hover:bg-blue-20 text-sm transition-colors"
          >
            {q.question}
          </button>
        ))}
      </div>
    </div>
  );
};

export default SuggestedQuestions;