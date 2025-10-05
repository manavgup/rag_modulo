import React, { useState } from 'react';
import { ChevronDownIcon, ChevronUpIcon, DocumentTextIcon, LinkIcon } from '@heroicons/react/24/outline';

export interface Source {
  document_name: string;
  content: string;
  metadata: {
    score?: number;
    url?: string;
    [key: string]: any;
  };
}

interface SourceCardProps {
  source: Source;
}

const SourceCard: React.FC<SourceCardProps> = ({ source }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const score = source.metadata?.score;
  const scoreColor =
    score && score >= 0.8
      ? 'bg-green-100 text-green-800'
      : score && score >= 0.6
      ? 'bg-yellow-100 text-yellow-800'
      : 'bg-red-100 text-red-800';

  return (
    <div className="bg-gray-10 border border-gray-200 rounded-lg p-4 transition-all duration-300 ease-in-out hover:shadow-md">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2">
            <DocumentTextIcon className="w-5 h-5 text-gray-500" />
            <h4 className="font-semibold text-gray-800 text-sm break-words">
              {source.document_name}
            </h4>
          </div>
        </div>
        {score && (
          <div className={`ml-2 px-2 py-0.5 text-xs font-medium rounded-full ${scoreColor}`}>
            Score: {score.toFixed(2)}
          </div>
        )}
      </div>

      <div className="mt-3 text-sm text-gray-600">
        <p className="line-clamp-3">{source.content}</p>
      </div>

      <div className="mt-4 flex items-center justify-between">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center space-x-1 text-sm text-blue-600 hover:text-blue-800"
        >
          {isExpanded ? (
            <>
              <ChevronUpIcon className="w-4 h-4" />
              <span>Show Less</span>
            </>
          ) : (
            <>
              <ChevronDownIcon className="w-4 h-4" />
              <span>Show More</span>
            </>
          )}
        </button>
        {source.metadata.url && (
            <a
                href={source.metadata.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center space-x-1 text-sm text-gray-500 hover:text-blue-600"
            >
                <LinkIcon className="w-4 h-4" />
                <span>Source Link</span>
            </a>
        )}
      </div>

      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <h5 className="text-xs font-semibold text-gray-500 uppercase mb-2">Full Text</h5>
          <pre className="text-sm text-gray-700 whitespace-pre-wrap bg-gray-50 p-3 rounded-md">
            {source.content}
          </pre>
        </div>
      )}
    </div>
  );
};

export default SourceCard;