/**
 * Unit tests for MessageMetadataFooter component
 *
 * Testing: PR #630 - Add citations UI components
 * Related Issues: #629 (citations), #283 (token usage), #274 (CoT steps)
 *
 * Tests verify the component correctly displays metadata including:
 * - Sources count
 * - Citations count (new in PR #630)
 * - Reasoning steps count
 * - Token count
 * - Response time
 * - Click handlers for interactive elements
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import MessageMetadataFooter from './MessageMetadataFooter';

describe('MessageMetadataFooter', () => {
  const mockCallbacks = {
    onSourcesClick: jest.fn(),
    onCitationsClick: jest.fn(),
    onStepsClick: jest.fn(),
    onTokensClick: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Basic rendering', () => {
    it('should render sources count', () => {
      render(<MessageMetadataFooter sourcesCount={5} {...mockCallbacks} />);

      expect(screen.getByText('5 sources')).toBeInTheDocument();
    });

    it('should render citations count (PR #630)', () => {
      render(<MessageMetadataFooter citationsCount={3} {...mockCallbacks} />);

      expect(screen.getByText('3 citations')).toBeInTheDocument();
    });

    it('should render reasoning steps count', () => {
      render(<MessageMetadataFooter stepsCount={4} {...mockCallbacks} />);

      expect(screen.getByText('4 steps')).toBeInTheDocument();
    });

    it('should render token count with proper formatting', () => {
      render(<MessageMetadataFooter tokenCount={1234} {...mockCallbacks} />);

      expect(screen.getByText('1,234 tokens')).toBeInTheDocument();
    });

    it('should render response time in seconds', () => {
      render(<MessageMetadataFooter responseTime={2.5} {...mockCallbacks} />);

      expect(screen.getByText('2.5s')).toBeInTheDocument();
    });

    it('should render response time in milliseconds for values < 1 second', () => {
      render(<MessageMetadataFooter responseTime={0.534} {...mockCallbacks} />);

      expect(screen.getByText('534ms')).toBeInTheDocument();
    });

    it('should render all metadata items together', () => {
      render(
        <MessageMetadataFooter
          sourcesCount={5}
          citationsCount={3}
          stepsCount={2}
          tokenCount={1500}
          responseTime={1.2}
          {...mockCallbacks}
        />
      );

      expect(screen.getByText('5 sources')).toBeInTheDocument();
      expect(screen.getByText('3 citations')).toBeInTheDocument();
      expect(screen.getByText('2 steps')).toBeInTheDocument();
      expect(screen.getByText('1,500 tokens')).toBeInTheDocument();
      expect(screen.getByText('1.2s')).toBeInTheDocument();
    });
  });

  describe('Singular vs plural text', () => {
    it('should use singular "source" for 1 source', () => {
      render(<MessageMetadataFooter sourcesCount={1} {...mockCallbacks} />);

      expect(screen.getByText('1 source')).toBeInTheDocument();
      expect(screen.queryByText('1 sources')).not.toBeInTheDocument();
    });

    it('should use plural "sources" for multiple sources', () => {
      render(<MessageMetadataFooter sourcesCount={2} {...mockCallbacks} />);

      expect(screen.getByText('2 sources')).toBeInTheDocument();
    });

    it('should use singular "citation" for 1 citation', () => {
      render(<MessageMetadataFooter citationsCount={1} {...mockCallbacks} />);

      expect(screen.getByText('1 citation')).toBeInTheDocument();
      expect(screen.queryByText('1 citations')).not.toBeInTheDocument();
    });

    it('should use plural "citations" for multiple citations', () => {
      render(<MessageMetadataFooter citationsCount={2} {...mockCallbacks} />);

      expect(screen.getByText('2 citations')).toBeInTheDocument();
    });

    it('should use singular "step" for 1 step', () => {
      render(<MessageMetadataFooter stepsCount={1} {...mockCallbacks} />);

      expect(screen.getByText('1 step')).toBeInTheDocument();
      expect(screen.queryByText('1 steps')).not.toBeInTheDocument();
    });

    it('should use plural "steps" for multiple steps', () => {
      render(<MessageMetadataFooter stepsCount={2} {...mockCallbacks} />);

      expect(screen.getByText('2 steps')).toBeInTheDocument();
    });
  });

  describe('Click handlers', () => {
    it('should call onSourcesClick when sources button is clicked', () => {
      render(<MessageMetadataFooter sourcesCount={5} {...mockCallbacks} />);

      const sourcesButton = screen.getByRole('button', { name: /5 sources/i });
      fireEvent.click(sourcesButton);

      expect(mockCallbacks.onSourcesClick).toHaveBeenCalledTimes(1);
    });

    it('should call onCitationsClick when citations button is clicked (PR #630)', () => {
      render(<MessageMetadataFooter citationsCount={3} {...mockCallbacks} />);

      const citationsButton = screen.getByRole('button', { name: /3 citations/i });
      fireEvent.click(citationsButton);

      expect(mockCallbacks.onCitationsClick).toHaveBeenCalledTimes(1);
    });

    it('should call onStepsClick when steps button is clicked', () => {
      render(<MessageMetadataFooter stepsCount={4} {...mockCallbacks} />);

      const stepsButton = screen.getByRole('button', { name: /4 reasoning steps/i });
      fireEvent.click(stepsButton);

      expect(mockCallbacks.onStepsClick).toHaveBeenCalledTimes(1);
    });

    it('should call onTokensClick when tokens button is clicked', () => {
      render(<MessageMetadataFooter tokenCount={1000} {...mockCallbacks} />);

      const tokensButton = screen.getByRole('button', { name: /1,000 tokens/i });
      fireEvent.click(tokensButton);

      expect(mockCallbacks.onTokensClick).toHaveBeenCalledTimes(1);
    });
  });

  describe('Conditional rendering', () => {
    it('should not render when no metadata is provided', () => {
      const { container } = render(<MessageMetadataFooter {...mockCallbacks} />);

      expect(container.firstChild).toBeNull();
    });

    it('should not render when sourcesCount is 0', () => {
      const { container } = render(<MessageMetadataFooter sourcesCount={0} {...mockCallbacks} />);

      expect(container.firstChild).toBeNull();
    });

    it('should not render when citationsCount is 0', () => {
      const { container } = render(<MessageMetadataFooter citationsCount={0} {...mockCallbacks} />);

      expect(container.firstChild).toBeNull();
    });

    it('should not render sources when sourcesCount is 0 but render others', () => {
      render(<MessageMetadataFooter sourcesCount={0} citationsCount={3} {...mockCallbacks} />);

      expect(screen.queryByText(/sources/i)).not.toBeInTheDocument();
      expect(screen.getByText('3 citations')).toBeInTheDocument();
    });

    it('should not render citations when citationsCount is 0 but render others', () => {
      render(<MessageMetadataFooter sourcesCount={5} citationsCount={0} {...mockCallbacks} />);

      expect(screen.getByText('5 sources')).toBeInTheDocument();
      expect(screen.queryByText(/citations/i)).not.toBeInTheDocument();
    });

    it('should not render steps when stepsCount is undefined', () => {
      render(<MessageMetadataFooter sourcesCount={5} {...mockCallbacks} />);

      expect(screen.queryByText(/steps/i)).not.toBeInTheDocument();
    });

    it('should not render steps when stepsCount is 0', () => {
      render(<MessageMetadataFooter sourcesCount={5} stepsCount={0} {...mockCallbacks} />);

      expect(screen.queryByText(/steps/i)).not.toBeInTheDocument();
    });

    it('should not render tokens when tokenCount is undefined', () => {
      render(<MessageMetadataFooter sourcesCount={5} {...mockCallbacks} />);

      expect(screen.queryByText(/tokens/i)).not.toBeInTheDocument();
    });

    it('should not render tokens when tokenCount is 0', () => {
      render(<MessageMetadataFooter sourcesCount={5} tokenCount={0} {...mockCallbacks} />);

      expect(screen.queryByText(/tokens/i)).not.toBeInTheDocument();
    });

    it('should not render response time when responseTime is undefined', () => {
      render(<MessageMetadataFooter sourcesCount={5} {...mockCallbacks} />);

      expect(screen.queryByText(/ms|s$/)).not.toBeInTheDocument();
    });

    it('should not render response time when responseTime is 0', () => {
      render(<MessageMetadataFooter sourcesCount={5} responseTime={0} {...mockCallbacks} />);

      expect(screen.queryByText(/0ms|0s/)).not.toBeInTheDocument();
    });
  });

  describe('Token count formatting', () => {
    it('should format large token counts with commas', () => {
      render(<MessageMetadataFooter tokenCount={123456} {...mockCallbacks} />);

      expect(screen.getByText('123,456 tokens')).toBeInTheDocument();
    });

    it('should format token count with no commas for < 1000', () => {
      render(<MessageMetadataFooter tokenCount={999} {...mockCallbacks} />);

      expect(screen.getByText('999 tokens')).toBeInTheDocument();
    });

    it('should format token count with comma for >= 1000', () => {
      render(<MessageMetadataFooter tokenCount={1000} {...mockCallbacks} />);

      expect(screen.getByText('1,000 tokens')).toBeInTheDocument();
    });
  });

  describe('Response time formatting', () => {
    it('should format response time < 1s as milliseconds', () => {
      render(<MessageMetadataFooter responseTime={0.123} {...mockCallbacks} />);

      expect(screen.getByText('123ms')).toBeInTheDocument();
    });

    it('should round milliseconds to nearest integer', () => {
      render(<MessageMetadataFooter responseTime={0.9876} {...mockCallbacks} />);

      expect(screen.getByText('988ms')).toBeInTheDocument();
    });

    it('should format response time >= 1s as seconds with 1 decimal', () => {
      render(<MessageMetadataFooter responseTime={3.456} {...mockCallbacks} />);

      expect(screen.getByText('3.5s')).toBeInTheDocument();
    });

    it('should round seconds to 1 decimal place', () => {
      render(<MessageMetadataFooter responseTime={1.0} {...mockCallbacks} />);

      expect(screen.getByText('1.0s')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper aria-label for sources button', () => {
      render(<MessageMetadataFooter sourcesCount={5} {...mockCallbacks} />);

      const button = screen.getByRole('button', { name: 'View 5 sources' });
      expect(button).toBeInTheDocument();
    });

    it('should have proper aria-label for citations button', () => {
      render(<MessageMetadataFooter citationsCount={3} {...mockCallbacks} />);

      const button = screen.getByRole('button', { name: 'View 3 citations' });
      expect(button).toBeInTheDocument();
    });

    it('should have proper aria-label for steps button', () => {
      render(<MessageMetadataFooter stepsCount={2} {...mockCallbacks} />);

      const button = screen.getByRole('button', { name: 'View 2 reasoning steps' });
      expect(button).toBeInTheDocument();
    });

    it('should have proper aria-label for tokens button', () => {
      render(<MessageMetadataFooter tokenCount={1000} {...mockCallbacks} />);

      const button = screen.getByRole('button', { name: 'View token analysis (1,000 tokens)' });
      expect(button).toBeInTheDocument();
    });

    it('should use singular in aria-label for 1 source', () => {
      render(<MessageMetadataFooter sourcesCount={1} {...mockCallbacks} />);

      const button = screen.getByRole('button', { name: 'View 1 source' });
      expect(button).toBeInTheDocument();
    });

    it('should use singular in aria-label for 1 citation', () => {
      render(<MessageMetadataFooter citationsCount={1} {...mockCallbacks} />);

      const button = screen.getByRole('button', { name: 'View 1 citation' });
      expect(button).toBeInTheDocument();
    });

    it('should use singular in aria-label for 1 step', () => {
      render(<MessageMetadataFooter stepsCount={1} {...mockCallbacks} />);

      const button = screen.getByRole('button', { name: 'View 1 reasoning step' });
      expect(button).toBeInTheDocument();
    });

    it('should have button type="button" to prevent form submission', () => {
      render(<MessageMetadataFooter sourcesCount={5} {...mockCallbacks} />);

      const buttons = screen.getAllByRole('button');
      buttons.forEach((button) => {
        expect(button).toHaveAttribute('type', 'button');
      });
    });
  });

  describe('Edge cases', () => {
    it('should handle very large numbers gracefully', () => {
      render(
        <MessageMetadataFooter
          sourcesCount={999}
          citationsCount={999}
          stepsCount={999}
          tokenCount={9999999}
          responseTime={999.9}
          {...mockCallbacks}
        />
      );

      expect(screen.getByText('999 sources')).toBeInTheDocument();
      expect(screen.getByText('999 citations')).toBeInTheDocument();
      expect(screen.getByText('999 steps')).toBeInTheDocument();
      expect(screen.getByText('9,999,999 tokens')).toBeInTheDocument();
      expect(screen.getByText('999.9s')).toBeInTheDocument();
    });

    it('should handle negative response time (edge case)', () => {
      render(<MessageMetadataFooter responseTime={-1} {...mockCallbacks} />);

      // Should not render negative time (filtered by responseTime > 0 check)
      expect(screen.queryByText(/-/)).not.toBeInTheDocument();
    });

    it('should not call click handler if callback is undefined', () => {
      render(<MessageMetadataFooter sourcesCount={5} />);

      const sourcesButton = screen.getByRole('button', { name: /5 sources/i });

      // Should not throw error
      expect(() => fireEvent.click(sourcesButton)).not.toThrow();
    });
  });

  describe('Integration with CitationsAccordion (PR #630)', () => {
    it('should render both sources and citations independently', () => {
      render(
        <MessageMetadataFooter sourcesCount={5} citationsCount={3} onSourcesClick={mockCallbacks.onSourcesClick} onCitationsClick={mockCallbacks.onCitationsClick} />
      );

      expect(screen.getByText('5 sources')).toBeInTheDocument();
      expect(screen.getByText('3 citations')).toBeInTheDocument();
    });

    it('should have separate click handlers for sources and citations', () => {
      render(
        <MessageMetadataFooter sourcesCount={5} citationsCount={3} onSourcesClick={mockCallbacks.onSourcesClick} onCitationsClick={mockCallbacks.onCitationsClick} />
      );

      const sourcesButton = screen.getByRole('button', { name: /5 sources/i });
      const citationsButton = screen.getByRole('button', { name: /3 citations/i });

      fireEvent.click(sourcesButton);
      fireEvent.click(citationsButton);

      expect(mockCallbacks.onSourcesClick).toHaveBeenCalledTimes(1);
      expect(mockCallbacks.onCitationsClick).toHaveBeenCalledTimes(1);
    });
  });
});
