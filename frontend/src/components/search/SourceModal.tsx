import React from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import SourceList from './SourceList';

interface SourceModalProps {
  isOpen: boolean;
  onClose: () => void;
  sources: Array<{
    document_name: string;
    content: string;
    metadata: Record<string, any>;
  }>;
}

/**
 * SourceModal
 *
 * Modal overlay component for displaying source documents in detail.
 * Shows a list of source documents with confidence scores and metadata.
 *
 * Addresses GitHub Issue #275 (display source documents with confidence scores)
 * and #285 (improve source document card display).
 */
const SourceModal: React.FC<SourceModalProps> = ({ isOpen, onClose, sources }) => {
  if (!isOpen) return null;

  return (
    <div className="source-modal-overlay" onClick={onClose}>
      <div className="source-modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="source-modal-header">
          <h2 className="source-modal-title">Source Documents</h2>
          <button
            onClick={onClose}
            className="source-modal-close"
            aria-label="Close modal"
          >
            <XMarkIcon className="w-6 h-6" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="source-modal-body">
          {sources && sources.length > 0 ? (
            <>
              <div className="source-modal-summary">
                <p className="text-sm text-gray-70">
                  Found <strong>{sources.length}</strong> relevant {sources.length === 1 ? 'source' : 'sources'}
                </p>
              </div>
              <SourceList sources={sources} />
            </>
          ) : (
            <div className="text-center py-8 text-gray-60">
              No sources available for this response.
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="source-modal-footer">
          <button
            onClick={onClose}
            className="btn-secondary"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default SourceModal;
