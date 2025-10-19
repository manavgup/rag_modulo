import React from 'react';
import { ChevronDown, ChevronUp, Document } from '@carbon/icons-react';
import './SearchInterface.scss';

interface Source {
  document_name: string;
  content: string;
  metadata: {
    score?: number;
    [key: string]: any;
  };
}

interface SourcesAccordionProps {
  sources: Source[];
  isOpen: boolean;
  onToggle: () => void;
}

const SourcesAccordion: React.FC<SourcesAccordionProps> = ({ sources, isOpen, onToggle }) => {
  const getConfidenceLevel = (score: number): 'high' | 'medium' | 'low' => {
    if (score >= 0.7) return 'high';
    if (score >= 0.5) return 'medium';
    return 'low';
  };

  const formatConfidence = (score: number): string => {
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
          <Document className="source-accordion-icon" size={20} />
          <span className="source-accordion-title">Sources ({sources.length})</span>
        </div>
        {isOpen ? (
          <ChevronUp className="source-accordion-chevron" size={20} />
        ) : (
          <ChevronDown className="source-accordion-chevron" size={20} />
        )}
      </button>

      {isOpen && (
        <div className="source-accordion-content">
          {sources.map((source, index) => {
            const confidence = source.metadata?.score || 0;
            const confidenceLevel = getConfidenceLevel(confidence);

            return (
              <div key={index} className="source-card">
                <div className="source-card-header">
                  <div className="source-card-title-section">
                    <Document className="source-card-icon" />
                    <h3 className="source-card-title">{source.document_name}</h3>
                  </div>
                  <div className={`source-confidence-badge source-confidence-${confidenceLevel}`}>
                    <span className="source-confidence-value">
                      {formatConfidence(confidence)}
                    </span>
                  </div>
                </div>

                <div className="source-card-content">
                  <p className="source-card-text">
                    {source.content}
                  </p>
                </div>

                {source.metadata && Object.keys(source.metadata).length > 0 && (
                  <div className="source-card-footer">
                    <div className="source-card-metadata">
                      {source.metadata.page_number && (
                        <span className="metadata-tag">Page {source.metadata.page_number}</span>
                      )}
                      {source.metadata.chunk_id && (
                        <span className="metadata-tag">Chunk {source.metadata.chunk_id}</span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default SourcesAccordion;
