import React from 'react';
import { ChevronDown, ChevronUp, BookmarkFilled } from '@carbon/icons-react';
import { Citation } from '../../services/websocketClient';
import './SearchInterface.scss';

interface CitationsAccordionProps {
  citations: Citation[];
  isOpen: boolean;
  onToggle: () => void;
}

const CitationsAccordion: React.FC<CitationsAccordionProps> = ({ citations, isOpen, onToggle }) => {
  const getRelevanceLevel = (score: number): 'high' | 'medium' | 'low' => {
    if (score >= 0.7) return 'high';
    if (score >= 0.5) return 'medium';
    return 'low';
  };

  const formatRelevance = (score: number): string => {
    return `${Math.round(score * 100)}%`;
  };

  return (
    <div className="source-accordion">
      <button
        className="source-accordion-header"
        onClick={onToggle}
        aria-expanded={isOpen}
      >
        <div className="source-accordion-title-section">
          <BookmarkFilled className="source-accordion-icon" size={20} />
          <span className="source-accordion-title">Citations ({citations.length})</span>
        </div>
        {isOpen ? (
          <ChevronUp className="source-accordion-chevron" size={20} />
        ) : (
          <ChevronDown className="source-accordion-chevron" size={20} />
        )}
      </button>

      {isOpen && (
        <div className="source-accordion-content">
          {citations.map((citation, index) => {
            const relevanceLevel = getRelevanceLevel(citation.relevance_score);

            return (
              <div key={index} className="source-card">
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
