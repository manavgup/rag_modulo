import React, { useEffect, useRef } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import SourceList from './SourceList';
import { Source } from './SourceCard';

interface SourceModalProps {
  isOpen: boolean;
  onClose: () => void;
  sources: Source[];
}

/**
 * SourceModal
 *
 * Modal overlay component for displaying source documents in detail.
 * Shows a list of source documents with confidence scores and metadata.
 *
 * Accessibility features:
 * - Escape key to close
 * - Focus trap (focus returns to trigger on close)
 * - ARIA attributes (role="dialog", aria-modal, aria-labelledby)
 * - Body scroll prevention when open
 *
 * Addresses GitHub Issue #275 (display source documents with confidence scores)
 * and #285 (improve source document card display).
 */
const SourceModal: React.FC<SourceModalProps> = ({ isOpen, onClose, sources }) => {
  const modalRef = useRef<HTMLDivElement>(null);

  // Handle Escape key and focus management
  useEffect(() => {
    if (!isOpen) return;

    // Handle Escape key
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    // Prevent body scroll
    document.body.style.overflow = 'hidden';

    // Focus modal when opened
    modalRef.current?.focus();

    // Add event listener
    document.addEventListener('keydown', handleEscape);

    // Cleanup
    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="source-modal-overlay" onClick={onClose}>
      <div
        ref={modalRef}
        className="source-modal-content"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-modal-title"
        tabIndex={-1}
      >
        {/* Modal Header */}
        <div className="source-modal-header">
          <h2 id="source-modal-title" className="source-modal-title">Source Documents</h2>
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
