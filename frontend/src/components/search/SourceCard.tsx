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

/**
 * SourceCard - Redesigned
 *
 * Displays source documents with prominent document names and confidence scores.
 * Confidence scores are shown as large, prominent percentage badges.
 *
 * Implements GitHub Issue #275 (display source documents with confidence scores)
 * and #285 (improve source document card display).
 */
const SourceCard: React.FC<SourceCardProps> = ({ source }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const score = source.metadata?.score;
  const confidencePercentage = score ? Math.round(score * 100) : null;

  // Confidence badge styling based on score
  const getConfidenceBadgeClass = () => {
    if (!confidencePercentage) return '';
    if (confidencePercentage >= 80) return 'source-confidence-high';
    if (confidencePercentage >= 60) return 'source-confidence-medium';
    return 'source-confidence-low';
  };

  return (
    <div className="source-card">
      <div className="source-card-header">
        {/* Document name - PRIMARY visual element */}
        <div className="source-card-title-section">
          <DocumentTextIcon className="source-card-icon" />
          <h3 className="source-card-title">
            {source.document_name}
          </h3>
        </div>

        {/* Confidence badge - Prominent percentage display */}
        {confidencePercentage !== null && (
          <div className={`source-confidence-badge ${getConfidenceBadgeClass()}`}>
            <span className="source-confidence-value">{confidencePercentage}%</span>
          </div>
        )}
      </div>

      {/* Content preview */}
      <div className="source-card-content">
        <p className="source-card-text">
          {isExpanded ? source.content : `${source.content.substring(0, 200)}${source.content.length > 200 ? '...' : ''}`}
        </p>
      </div>

      {/* Actions footer */}
      <div className="source-card-footer">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="source-card-action"
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
            className="source-card-action"
          >
            <LinkIcon className="w-4 h-4" />
            <span>Source Link</span>
          </a>
        )}
      </div>
    </div>
  );
};

export default SourceCard;
