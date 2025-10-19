import React from 'react';
import { Document, Connect, Time, ChartColumn } from '@carbon/icons-react';

interface MessageMetadataFooterProps {
  sourcesCount?: number;
  stepsCount?: number;
  tokenCount?: number;
  responseTime?: number;
  onSourcesClick?: () => void;
  onStepsClick?: () => void;
  onTokensClick?: () => void;
}

/**
 * MessageMetadataFooter
 *
 * Displays clickable inline metadata for assistant messages showing:
 * - Number of source documents used (clickable)
 * - Number of Chain-of-Thought reasoning steps (clickable)
 * - Total tokens used (clickable)
 * - Response time in seconds
 *
 * Addresses GitHub Issues: #283 (token usage), #274 (CoT steps)
 */
const MessageMetadataFooter: React.FC<MessageMetadataFooterProps> = ({
  sourcesCount = 0,
  stepsCount,
  tokenCount,
  responseTime,
  onSourcesClick,
  onStepsClick,
  onTokensClick,
}) => {
  // Only render if there's at least one piece of metadata to show
  const hasMetadata = sourcesCount > 0 || (stepsCount && stepsCount > 0) || tokenCount || responseTime;

  if (!hasMetadata) {
    return null;
  }

  return (
    <div className="message-metadata-footer">
      <div className="metadata-items">
        {sourcesCount > 0 && (
          <button
            className="metadata-item metadata-sources metadata-clickable"
            onClick={onSourcesClick}
            type="button"
            aria-label={`View ${sourcesCount} ${sourcesCount === 1 ? 'source' : 'sources'}`}
          >
            <Document size={16} className="metadata-icon" />
            <span className="metadata-text">
              {sourcesCount} {sourcesCount === 1 ? 'source' : 'sources'}
            </span>
          </button>
        )}

        {stepsCount && stepsCount > 0 && (
          <button
            className="metadata-item metadata-steps metadata-clickable"
            onClick={onStepsClick}
            type="button"
            aria-label={`View ${stepsCount} reasoning ${stepsCount === 1 ? 'step' : 'steps'}`}
          >
            <Connect size={16} className="metadata-icon" />
            <span className="metadata-text">
              {stepsCount} {stepsCount === 1 ? 'step' : 'steps'}
            </span>
          </button>
        )}

        {tokenCount && tokenCount > 0 && (
          <button
            className="metadata-item metadata-tokens metadata-clickable"
            onClick={onTokensClick}
            type="button"
            aria-label={`View token analysis (${tokenCount.toLocaleString()} tokens)`}
          >
            <ChartColumn size={16} className="metadata-icon" />
            <span className="metadata-text">
              {tokenCount.toLocaleString()} tokens
            </span>
          </button>
        )}

        {responseTime && responseTime > 0 && (
          <span className="metadata-item metadata-time">
            <Time size={16} className="metadata-icon" />
            <span className="metadata-text">
              {responseTime < 1 ? `${(responseTime * 1000).toFixed(0)}ms` : `${responseTime.toFixed(1)}s`}
            </span>
          </span>
        )}
      </div>
    </div>
  );
};

export default MessageMetadataFooter;
