import React, { useState } from 'react';
import { Copy, Checkmark } from '@carbon/icons-react';

interface CopyButtonProps {
  content: string;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

/**
 * CopyButton Component
 *
 * A reusable button component that copies content to clipboard with visual feedback.
 * Uses the Clipboard API with fallback for older browsers.
 * Styled to match other metadata buttons (sources, tokens, etc.)
 */
const CopyButton: React.FC<CopyButtonProps> = ({
  content,
  className = '',
  size = 'sm'
}) => {
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState(false);

  const iconSize = size === 'sm' ? 16 : size === 'md' ? 20 : 24;

  const handleCopy = async () => {
    try {
      // Try modern Clipboard API first
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(content);
        setCopied(true);
        setError(false);

        // Reset after 2 seconds
        setTimeout(() => setCopied(false), 2000);
      } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = content;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();

        try {
          const successful = document.execCommand('copy');
          if (successful) {
            setCopied(true);
            setError(false);
            setTimeout(() => setCopied(false), 2000);
          } else {
            throw new Error('Copy command failed');
          }
        } finally {
          document.body.removeChild(textArea);
        }
      }
    } catch (err) {
      console.error('Failed to copy:', err);
      setError(true);
      setTimeout(() => setError(false), 2000);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className={`metadata-item metadata-copy metadata-clickable ${className}`}
      type="button"
      title={copied ? 'Copied!' : error ? 'Failed to copy' : 'Copy to clipboard'}
      aria-label={copied ? 'Copied to clipboard' : 'Copy to clipboard'}
    >
      {copied ? (
        <Checkmark size={iconSize} className="metadata-icon" style={{ color: '#24a148' }} />
      ) : error ? (
        <Copy size={iconSize} className="metadata-icon" style={{ color: '#da1e28' }} />
      ) : (
        <Copy size={iconSize} className="metadata-icon" />
      )}
      <span className="metadata-text">
        {copied ? 'Copied!' : 'Copy'}
      </span>
    </button>
  );
};

export default CopyButton;

// Made with Bob
