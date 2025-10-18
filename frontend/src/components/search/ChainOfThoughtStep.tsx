import React from 'react';
import { Document } from '@carbon/icons-react';

interface ChainOfThoughtStepProps {
  step: {
    step_number: number;
    question: string;
    answer: string;
    reasoning?: string;
    sources_used: number;
  };
  isLast: boolean;
}

/**
 * ChainOfThoughtStep
 *
 * Individual step in Chain-of-Thought reasoning display.
 * Shows the question, answer, reasoning, and source count for each step.
 *
 * Implements GitHub Issue #274 (display Chain-of-Thought reasoning steps).
 */
const ChainOfThoughtStep: React.FC<ChainOfThoughtStepProps> = ({ step, isLast }) => {
  return (
    <div className="cot-step">
      {/* Step Header */}
      <div className="cot-step-header">
        <div className="cot-step-number">
          {step.step_number}
        </div>
        <div className="cot-step-title">
          Step {step.step_number}
        </div>
        {step.sources_used > 0 && (
          <div className="cot-step-sources">
            <Document size={16} className="cot-step-sources-icon" />
            <span>{step.sources_used} {step.sources_used === 1 ? 'source' : 'sources'}</span>
          </div>
        )}
      </div>

      {/* Step Content */}
      <div className="cot-step-content">
        <div className="cot-step-section">
          <div className="cot-step-label">Question:</div>
          <div className="cot-step-text">{step.question}</div>
        </div>

        <div className="cot-step-section">
          <div className="cot-step-label">Answer:</div>
          <div className="cot-step-text">{step.answer}</div>
        </div>

        {step.reasoning && (
          <div className="cot-step-section">
            <div className="cot-step-label">Reasoning:</div>
            <div className="cot-step-reasoning">{step.reasoning}</div>
          </div>
        )}
      </div>

      {/* Visual connector to next step */}
      {!isLast && (
        <div className="cot-step-connector">
          <div className="cot-step-connector-line"></div>
          <div className="cot-step-connector-arrow">↓</div>
        </div>
      )}
    </div>
  );
};

export default ChainOfThoughtStep;
