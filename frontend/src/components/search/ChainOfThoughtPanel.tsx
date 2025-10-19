import React from 'react';
import ChainOfThoughtStep from './ChainOfThoughtStep';

/**
 * Security Note: Content from LLM responses is rendered as text content (not HTML).
 * React automatically escapes text content, providing XSS protection.
 * If HTML rendering is needed in the future, use sanitizeHtml() from utils/sanitize.ts
 */

interface ChainOfThoughtPanelProps {
  cotOutput: {
    enabled: boolean;
    steps: Array<{
      step_number: number;
      question: string;
      answer: string;
      reasoning?: string;
      sources_used: number;
    }>;
    total_steps: number;
    final_synthesis?: string;
  };
}

/**
 * ChainOfThoughtPanel
 *
 * Container for displaying Chain-of-Thought reasoning steps.
 * Shows all reasoning steps with visual connectors and final synthesis.
 *
 * Implements GitHub Issue #274 (display Chain-of-Thought reasoning steps).
 */
const ChainOfThoughtPanel: React.FC<ChainOfThoughtPanelProps> = ({ cotOutput }) => {
  if (!cotOutput.enabled || cotOutput.steps.length === 0) {
    return null;
  }

  return (
    <div className="cot-panel">
      {/* Panel Header */}
      <div className="cot-panel-header">
        <h4 className="cot-panel-title">Reasoning Process</h4>
        <span className="cot-panel-count">
          {cotOutput.total_steps} {cotOutput.total_steps === 1 ? 'step' : 'steps'}
        </span>
      </div>

      {/* Steps */}
      <div className="cot-panel-steps">
        {cotOutput.steps.map((step, index) => (
          <ChainOfThoughtStep
            key={`step-${step.step_number}`}
            step={step}
            isLast={index === cotOutput.steps.length - 1}
          />
        ))}
      </div>

      {/* Final Synthesis */}
      {cotOutput.final_synthesis && (
        <div className="cot-panel-synthesis">
          <div className="cot-panel-synthesis-label">Final Synthesis:</div>
          <div className="cot-panel-synthesis-text">{cotOutput.final_synthesis}</div>
        </div>
      )}
    </div>
  );
};

export default ChainOfThoughtPanel;
