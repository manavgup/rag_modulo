import React, { useState, useEffect } from 'react';
import apiClient, { SuggestedQuestion } from '../../services/apiClient';
import { useNotification } from '../../contexts/NotificationContext';
import { LightBulbIcon, ArrowPathIcon, ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';

interface SuggestedQuestionsProps {
  collectionId: string;
  onQuestionClick: (question: string) => void;
}

const SuggestedQuestions: React.FC<SuggestedQuestionsProps> = ({ collectionId, onQuestionClick }) => {
  const [questions, setQuestions] = useState<SuggestedQuestion[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const { addNotification } = useNotification();


  useEffect(() => {
    let isMounted = true;

    const fetchQuestionsWithCleanup = async () => {
      if (!isMounted) return;

      setIsLoading(true);
      setError(null);
      try {
        const fetchedQuestions = await apiClient.getSuggestedQuestions(collectionId);
        if (isMounted) {
          setQuestions(fetchedQuestions);
        }
      } catch (err) {
        if (isMounted) {
          const errorMessage = err instanceof Error ? err.message : 'Failed to load suggested questions.';
          console.error('Error fetching suggested questions:', err);
          setError(errorMessage);
          addNotification('error', 'Error', `Could not fetch suggested questions: ${errorMessage}`);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    fetchQuestionsWithCleanup();

    return () => {
      isMounted = false;
    };
  }, [collectionId, addNotification]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      const fetchedQuestions = await apiClient.getSuggestedQuestions(collectionId);
      setQuestions(fetchedQuestions);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load suggested questions.';
      console.error('Error fetching suggested questions:', err);
      setError(errorMessage);
      addNotification('error', 'Error', `Could not fetch suggested questions: ${errorMessage}`);
    } finally {
      setIsRefreshing(false);
    }
  };

  if (isLoading) {
    return (
      <div className="p-4 bg-gray-20 rounded-lg">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center text-sm font-semibold text-gray-80">
            <LightBulbIcon className="w-5 h-5 mr-2" />
            <span>Suggested Questions</span>
          </div>
          <ChevronDownIcon className="w-4 h-4 text-gray-60" />
        </div>
        {isExpanded && (
          <div className="flex flex-wrap gap-2 animate-pulse">
            <div className="h-8 bg-gray-30 rounded-full w-32"></div>
            <div className="h-8 bg-gray-30 rounded-full w-48"></div>
            <div className="h-8 bg-gray-30 rounded-full w-40"></div>
          </div>
        )}
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
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="flex items-center justify-between mb-2 w-full text-left"
            >
                <div className="flex items-center text-sm font-semibold text-gray-80">
                    <LightBulbIcon className="w-5 h-5 mr-2" />
                    <span>Suggested Questions</span>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRefresh();
                    }}
                    disabled={isRefreshing}
                    className={`p-1 text-gray-60 hover:text-gray-90 ${isRefreshing ? 'animate-spin' : ''}`}
                    title="Refresh suggested questions"
                    aria-label="Refresh suggested questions"
                  >
                    <ArrowPathIcon className="w-4 h-4" />
                  </button>
                  {isExpanded ? (
                    <ChevronUpIcon className="w-4 h-4 text-gray-60" />
                  ) : (
                    <ChevronDownIcon className="w-4 h-4 text-gray-60" />
                  )}
                </div>
            </button>
            {isExpanded && (
              <p className="text-sm text-gray-60">No suggested questions available at the moment. Questions will be generated automatically after document processing is complete.</p>
            )}
      </div>
    );
  }

  return (
    <div className="p-4 bg-gray-20 rounded-lg">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center justify-between mb-2 w-full text-left"
      >
        <div className="flex items-center text-sm font-semibold text-gray-80">
          <LightBulbIcon className="w-5 h-5 mr-2" />
          <span>Suggested Questions ({questions.length})</span>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleRefresh();
            }}
            disabled={isRefreshing}
            className={`p-1 text-gray-60 hover:text-gray-90 ${isRefreshing ? 'animate-spin' : ''}`}
            title="Refresh suggested questions"
            aria-label="Refresh suggested questions"
          >
            <ArrowPathIcon className="w-4 h-4" />
          </button>
          {isExpanded ? (
            <ChevronUpIcon className="w-4 h-4 text-gray-60" />
          ) : (
            <ChevronDownIcon className="w-4 h-4 text-gray-60" />
          )}
        </div>
      </button>
      {isExpanded && (
        <div className="flex flex-wrap gap-2">
          {questions.map((q) => (
            <button
              key={q.id}
              onClick={() => onQuestionClick(q.question)}
              className="px-3 py-1.5 bg-blue-10 text-blue-70 rounded-full hover:bg-blue-20 text-sm transition-colors"
              aria-label={`Use suggested question: ${q.question}`}
            >
              {q.question}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default SuggestedQuestions;
