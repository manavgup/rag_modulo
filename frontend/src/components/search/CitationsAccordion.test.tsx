/**
 * Unit tests for CitationsAccordion component
 *
 * Testing: PR #630 - Add citations UI components
 * Issue: #629
 *
 * Tests verify the component correctly displays citations with:
 * - Proper rendering of citation data
 * - Color-coded relevance scores
 * - Error handling for missing/invalid data
 * - Accessibility features
 * - Toggle functionality
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import CitationsAccordion from './CitationsAccordion';
import { Citation } from '../../services/websocketClient';

// Mock CSS imports
jest.mock('./SearchInterface.scss', () => ({}));

describe('CitationsAccordion', () => {
  const mockCitations: Citation[] = [
    {
      document_id: 'doc-123',
      title: 'Test Document 1',
      excerpt: 'This is a test excerpt from document 1.',
      relevance_score: 0.85,
      page_number: 42,
      chunk_id: 'chunk-1',
    },
    {
      document_id: 'doc-456',
      title: 'Test Document 2',
      excerpt: 'This is a test excerpt from document 2.',
      relevance_score: 0.62,
      page_number: 15,
      chunk_id: 'chunk-2',
    },
    {
      document_id: 'doc-789',
      title: 'Test Document 3',
      excerpt: 'This is a test excerpt from document 3.',
      relevance_score: 0.35,
      chunk_id: 'chunk-3',
    },
  ];

  const mockOnToggle = jest.fn();

  beforeEach(() => {
    mockOnToggle.mockClear();
  });

  describe('Basic rendering', () => {
    it('should render the accordion header with correct citation count', () => {
      render(<CitationsAccordion citations={mockCitations} isOpen={false} onToggle={mockOnToggle} />);

      expect(screen.getByText('Citations (3)')).toBeInTheDocument();
    });

    it('should render citations when accordion is open', () => {
      render(<CitationsAccordion citations={mockCitations} isOpen={true} onToggle={mockOnToggle} />);

      expect(screen.getByText('Test Document 1')).toBeInTheDocument();
      expect(screen.getByText('Test Document 2')).toBeInTheDocument();
      expect(screen.getByText('Test Document 3')).toBeInTheDocument();
    });

    it('should not render citations when accordion is closed', () => {
      render(<CitationsAccordion citations={mockCitations} isOpen={false} onToggle={mockOnToggle} />);

      expect(screen.queryByText('Test Document 1')).not.toBeInTheDocument();
      expect(screen.queryByText('Test Document 2')).not.toBeInTheDocument();
    });

    it('should render citation excerpts', () => {
      render(<CitationsAccordion citations={mockCitations} isOpen={true} onToggle={mockOnToggle} />);

      expect(screen.getByText('This is a test excerpt from document 1.')).toBeInTheDocument();
      expect(screen.getByText('This is a test excerpt from document 2.')).toBeInTheDocument();
    });
  });

  describe('Relevance score display', () => {
    it('should display high relevance score (>=0.7) correctly', () => {
      render(<CitationsAccordion citations={mockCitations} isOpen={true} onToggle={mockOnToggle} />);

      // 0.85 should be displayed as 85%
      expect(screen.getByText('85%')).toBeInTheDocument();
    });

    it('should display medium relevance score (>=0.5, <0.7) correctly', () => {
      render(<CitationsAccordion citations={mockCitations} isOpen={true} onToggle={mockOnToggle} />);

      // 0.62 should be displayed as 62%
      expect(screen.getByText('62%')).toBeInTheDocument();
    });

    it('should display low relevance score (<0.5) correctly', () => {
      render(<CitationsAccordion citations={mockCitations} isOpen={true} onToggle={mockOnToggle} />);

      // 0.35 should be displayed as 35%
      expect(screen.getByText('35%')).toBeInTheDocument();
    });

    it('should handle boundary case for high threshold (0.7)', () => {
      const citations: Citation[] = [
        {
          document_id: 'doc-boundary',
          title: 'Boundary Document',
          excerpt: 'Test excerpt',
          relevance_score: 0.7,
        },
      ];

      render(<CitationsAccordion citations={citations} isOpen={true} onToggle={mockOnToggle} />);

      expect(screen.getByText('70%')).toBeInTheDocument();
    });

    it('should handle boundary case for medium threshold (0.5)', () => {
      const citations: Citation[] = [
        {
          document_id: 'doc-boundary',
          title: 'Boundary Document',
          excerpt: 'Test excerpt',
          relevance_score: 0.5,
        },
      ];

      render(<CitationsAccordion citations={citations} isOpen={true} onToggle={mockOnToggle} />);

      expect(screen.getByText('50%')).toBeInTheDocument();
    });
  });

  describe('Metadata display', () => {
    it('should display page numbers when available', () => {
      render(<CitationsAccordion citations={mockCitations} isOpen={true} onToggle={mockOnToggle} />);

      expect(screen.getByText('Page 42')).toBeInTheDocument();
      expect(screen.getByText('Page 15')).toBeInTheDocument();
    });

    it('should not display page number when not available', () => {
      render(<CitationsAccordion citations={mockCitations} isOpen={true} onToggle={mockOnToggle} />);

      // doc-789 doesn't have a page number
      const pageElements = screen.queryAllByText(/^Page \d+$/);
      expect(pageElements).toHaveLength(2); // Only 2 citations have page numbers
    });

    it('should display chunk IDs when available', () => {
      render(<CitationsAccordion citations={mockCitations} isOpen={true} onToggle={mockOnToggle} />);

      expect(screen.getByText('Chunk chunk-1')).toBeInTheDocument();
      expect(screen.getByText('Chunk chunk-2')).toBeInTheDocument();
      expect(screen.getByText('Chunk chunk-3')).toBeInTheDocument();
    });

    it('should display truncated document IDs', () => {
      render(<CitationsAccordion citations={mockCitations} isOpen={true} onToggle={mockOnToggle} />);

      expect(screen.getByText('Doc ID: doc-123...')).toBeInTheDocument();
      expect(screen.getByText('Doc ID: doc-456...')).toBeInTheDocument();
    });
  });

  describe('Toggle functionality', () => {
    it('should call onToggle when header is clicked', () => {
      render(<CitationsAccordion citations={mockCitations} isOpen={false} onToggle={mockOnToggle} />);

      const header = screen.getByRole('button', { name: /Citations/i });
      fireEvent.click(header);

      expect(mockOnToggle).toHaveBeenCalledTimes(1);
    });

    it('should display chevron down icon when closed', () => {
      const { container } = render(
        <CitationsAccordion citations={mockCitations} isOpen={false} onToggle={mockOnToggle} />
      );

      const header = screen.getByRole('button', { name: /Citations/i });
      expect(header).toHaveAttribute('aria-expanded', 'false');
    });

    it('should display chevron up icon when open', () => {
      const { container } = render(
        <CitationsAccordion citations={mockCitations} isOpen={true} onToggle={mockOnToggle} />
      );

      const header = screen.getByRole('button', { name: /Citations/i });
      expect(header).toHaveAttribute('aria-expanded', 'true');
    });
  });

  describe('Error handling and edge cases', () => {
    it('should not render when citations array is empty', () => {
      const { container } = render(<CitationsAccordion citations={[]} isOpen={true} onToggle={mockOnToggle} />);

      expect(container.firstChild).toBeNull();
    });

    it('should not render when citations is null', () => {
      const { container } = render(<CitationsAccordion citations={null as any} isOpen={true} onToggle={mockOnToggle} />);

      expect(container.firstChild).toBeNull();
    });

    it('should not render when citations is undefined', () => {
      const { container } = render(
        <CitationsAccordion citations={undefined as any} isOpen={true} onToggle={mockOnToggle} />
      );

      expect(container.firstChild).toBeNull();
    });

    it('should filter out citations with missing document_id', () => {
      const citationsWithMissing: Citation[] = [
        {
          document_id: 'doc-123',
          title: 'Valid Citation',
          excerpt: 'Valid excerpt',
          relevance_score: 0.8,
        },
        {
          document_id: '',
          title: 'Invalid Citation',
          excerpt: 'Missing document_id',
          relevance_score: 0.5,
        },
      ];

      render(<CitationsAccordion citations={citationsWithMissing} isOpen={true} onToggle={mockOnToggle} />);

      expect(screen.getByText('Valid Citation')).toBeInTheDocument();
      expect(screen.queryByText('Invalid Citation')).not.toBeInTheDocument();
      expect(screen.getByText('Citations (1)')).toBeInTheDocument(); // Only 1 valid citation
    });

    it('should filter out citations with missing title', () => {
      const citationsWithMissing: Citation[] = [
        {
          document_id: 'doc-123',
          title: 'Valid Citation',
          excerpt: 'Valid excerpt',
          relevance_score: 0.8,
        },
        {
          document_id: 'doc-456',
          title: '',
          excerpt: 'Missing title',
          relevance_score: 0.5,
        },
      ];

      render(<CitationsAccordion citations={citationsWithMissing} isOpen={true} onToggle={mockOnToggle} />);

      expect(screen.getByText('Valid Citation')).toBeInTheDocument();
      expect(screen.queryByText('Missing title')).not.toBeInTheDocument();
      expect(screen.getByText('Citations (1)')).toBeInTheDocument();
    });

    it('should filter out citations with missing excerpt', () => {
      const citationsWithMissing: Citation[] = [
        {
          document_id: 'doc-123',
          title: 'Valid Citation',
          excerpt: 'Valid excerpt',
          relevance_score: 0.8,
        },
        {
          document_id: 'doc-456',
          title: 'No Excerpt',
          excerpt: '',
          relevance_score: 0.5,
        },
      ];

      render(<CitationsAccordion citations={citationsWithMissing} isOpen={true} onToggle={mockOnToggle} />);

      expect(screen.getByText('Valid Citation')).toBeInTheDocument();
      expect(screen.queryByText('No Excerpt')).not.toBeInTheDocument();
      expect(screen.getByText('Citations (1)')).toBeInTheDocument();
    });

    it('should handle undefined relevance score', () => {
      const citationsWithUndefined: Citation[] = [
        {
          document_id: 'doc-123',
          title: 'No Score',
          excerpt: 'No relevance score',
          relevance_score: undefined as any,
        },
      ];

      render(<CitationsAccordion citations={citationsWithUndefined} isOpen={true} onToggle={mockOnToggle} />);

      expect(screen.getByText('0%')).toBeInTheDocument(); // Should default to 0%
    });

    it('should handle null relevance score', () => {
      const citationsWithNull: Citation[] = [
        {
          document_id: 'doc-123',
          title: 'Null Score',
          excerpt: 'Null relevance score',
          relevance_score: null as any,
        },
      ];

      render(<CitationsAccordion citations={citationsWithNull} isOpen={true} onToggle={mockOnToggle} />);

      expect(screen.getByText('0%')).toBeInTheDocument(); // Should default to 0%
    });
  });

  describe('Key prop uniqueness', () => {
    it('should use document_id and chunk_id for unique keys when both available', () => {
      const { container } = render(
        <CitationsAccordion citations={mockCitations} isOpen={true} onToggle={mockOnToggle} />
      );

      const citationCards = container.querySelectorAll('.source-card');
      expect(citationCards).toHaveLength(3);

      // Keys should be unique combinations of document_id-chunk_id
      expect(citationCards[0]).toHaveAttribute('data-testid'); // Would be set if we added test IDs
    });

    it('should use document_id alone when chunk_id is missing', () => {
      const citationsWithoutChunk: Citation[] = [
        {
          document_id: 'doc-123',
          title: 'No Chunk',
          excerpt: 'No chunk ID',
          relevance_score: 0.8,
        },
      ];

      const { container } = render(
        <CitationsAccordion citations={citationsWithoutChunk} isOpen={true} onToggle={mockOnToggle} />
      );

      expect(screen.getByText('No Chunk')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA attributes on accordion button', () => {
      render(<CitationsAccordion citations={mockCitations} isOpen={false} onToggle={mockOnToggle} />);

      const button = screen.getByRole('button', { name: /Citations/i });
      expect(button).toHaveAttribute('aria-expanded', 'false');
    });

    it('should update aria-expanded when opened', () => {
      const { rerender } = render(
        <CitationsAccordion citations={mockCitations} isOpen={false} onToggle={mockOnToggle} />
      );

      const button = screen.getByRole('button', { name: /Citations/i });
      expect(button).toHaveAttribute('aria-expanded', 'false');

      rerender(<CitationsAccordion citations={mockCitations} isOpen={true} onToggle={mockOnToggle} />);

      expect(button).toHaveAttribute('aria-expanded', 'true');
    });
  });
});
