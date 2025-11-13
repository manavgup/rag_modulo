import React from 'react';
import { ChevronDown, ChevronUp, BookmarkFilled } from '@carbon/icons-react';
import { Citation } from '../../services/websocketClient';
import './SearchInterface.scss';

interface CitationsAccordionProps {
  citations: Citation[];
  isOpen: boolean;
  onToggle: () => void;
}

// Relevance score thresholds for color-coding
const RELEVANCE_THRESHOLDS = {
  HIGH: 0.7,
  MEDIUM: 0.5,
} as const;

/**
 * CitationsAccordion
 *
 * Displays a collapsible accordion with citations from structured answers.
 * Shows relevance scores with color-coded badges (high/medium/low) and document metadata.
 *
 * Features:
 * - Color-coded confidence badges based on relevance score
 * - Document metadata (title, page number, excerpt)
 * - Clean, accessible design with Carbon icons
 * - Keyboard navigation support
 *
 * @param citations - Array of citation objects with document metadata and relevance scores
 * @param isOpen - Whether the accordion is expanded
 * @param onToggle - Callback function when accordion is toggled
 *
 * @example
 * ```tsx
 * <CitationsAccordion
 *   citations={citations}
 *   isOpen={showCitations}
 *   onToggle={() => setShowCitations(!showCitations)}
 * />
 * ```
 *
 * @related Issue #629 - Citations feature
 */
const CitationsAccordion: React.FC<CitationsAccordionProps> = ({ citations, isOpen, onToggle }) => {
  /**
   * Determines the relevance level (high/medium/low) based on the relevance score.
   * @param score - Relevance score (0-1), undefined/null defaults to 'low'
   * @returns Relevance level for CSS class naming
   */
  const getRelevanceLevel = (score: number | undefined): 'high' | 'medium' | 'low' => {
    // Handle undefined/null scores
    if (score === undefined || score === null) return 'low';
    if (score >= RELEVANCE_THRESHOLDS.HIGH) return 'high';
    if (score >= RELEVANCE_THRESHOLDS.MEDIUM) return 'medium';
    return 'low';
  };

  /**
   * Formats the relevance score as a percentage string.
   * @param score - Relevance score (0-1)
   * @returns Formatted percentage string
   */
  const formatRelevance = (score: number | undefined): string => {
    if (score === undefined || score === null) return '0%';
    return `${Math.round(score * 100)}%`;
  };

  // Validate citations array
  if (!citations || citations.length === 0) {
    return null;
  }

  // Filter out invalid citations (missing required fields)
  const validCitations = citations.filter(
    (citation) => citation && citation.document_id && citation.title && citation.excerpt
  );

  // If no valid citations after filtering, don't render
  if (validCitations.length === 0) {
    return null;
  }

  return (
    <div className="source-accordion">
      <button
        className="source-accordion-header"
        onClick={onToggle}
        aria-expanded={isOpen}
      >
        <div className="source-accordion-title-section">
          <BookmarkFilled className="source-accordion-icon" size={20} />
          <span className="source-accordion-title">Citations ({validCitations.length})</span>
        </div>
        {isOpen ? (
          <ChevronUp className="source-accordion-chevron" size={20} />
        ) : (
          <ChevronDown className="source-accordion-chevron" size={20} />
        )}
      </button>

      {isOpen && (
        <div className="source-accordion-content">
          {validCitations.map((citation) => {
            const relevanceLevel = getRelevanceLevel(citation.relevance_score);
            // Use document_id and chunk_id for unique key (fallback to document_id only)
            const uniqueKey = citation.chunk_id
              ? `${citation.document_id}-${citation.chunk_id}`
              : citation.document_id;

            return (
              <div key={uniqueKey} className="source-card">
                <div className="source-card-header">
                  <div className="source-card-title-section">
                    <BookmarkFilled className="source-card-icon" />
                    <h3 className="source-card-title">{citation.title}</h3>
                  </div>
                  <div className={`source-confidence-badge source-confidence-${relevanceLevel}`}>
                    <span className="source-confidence-value">
                      {formatRelevance(citation.relevance_score)}
                    </span>
                  </div>
                </div>

                <div className="source-card-content">
                  <p className="source-card-text">
                    {citation.excerpt}
                  </p>
                </div>

                <div className="source-card-footer">
                  <div className="source-card-metadata">
                    {citation.page_number && (
                      <span className="metadata-tag">Page {citation.page_number}</span>
                    )}
                    {citation.chunk_id && (
                      <span className="metadata-tag">Chunk {citation.chunk_id}</span>
                    )}
                    <span className="metadata-tag metadata-tag-muted">
                      Doc ID: {citation.document_id.substring(0, 8)}...
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default CitationsAccordion;
