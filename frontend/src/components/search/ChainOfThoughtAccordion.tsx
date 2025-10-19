import React from 'react';
import { ChevronDown, ChevronUp, Connect } from '@carbon/icons-react';
import './SearchInterface.scss';

/**
 * Security Note: Content from LLM responses is rendered as text content (not HTML).
 * React automatically escapes text content, providing XSS protection.
 * If HTML rendering is needed in the future, use sanitizeHtml() from utils/sanitize.ts
 */

interface ReasoningStep {
  step_number: number;
  question: string;
  intermediate_answer: string;
  reasoning?: string;
  confidence_score?: number;
  sources_used?: number;
}

interface ChainOfThoughtAccordionProps {
  cotOutput: {
    reasoning_steps?: ReasoningStep[];
    final_synthesis?: string;
    [key: string]: any;
  };
  isOpen: boolean;
  onToggle: () => void;
}

const ChainOfThoughtAccordion: React.FC<ChainOfThoughtAccordionProps> = ({ cotOutput, isOpen, onToggle }) => {
  const reasoningSteps = cotOutput?.reasoning_steps || [];
  const finalSynthesis = cotOutput?.final_synthesis;

  return (
    <div className="cot-accordion">
      <button
        className="cot-accordion-header"
        onClick={onToggle}
        aria-expanded={isOpen}
      >
        <div className="cot-accordion-title-section">
          <Connect className="cot-accordion-icon" size={20} />
          <span className="cot-accordion-title">Chain of Thought ({reasoningSteps.length} steps)</span>
        </div>
        {isOpen ? (
          <ChevronUp className="cot-accordion-chevron" size={20} />
        ) : (
          <ChevronDown className="cot-accordion-chevron" size={20} />
        )}
      </button>

      {isOpen && (
        <div className="cot-accordion-content">
          <div className="cot-panel">
            <div className="cot-panel-steps">
              {reasoningSteps.map((step, index) => (
                <React.Fragment key={index}>
                  <div className="cot-step">
                    <div className="cot-step-header">
                      <div className="cot-step-number">{step.step_number}</div>
                      <div className="cot-step-title">{step.question}</div>
                      {step.sources_used && (
                        <div className="cot-step-sources">
                          <span>{step.sources_used} sources</span>
                        </div>
                      )}
                    </div>

                    <div className="cot-step-content">
                      <div className="cot-step-section">
                        <div className="cot-step-label">Answer</div>
                        <div className="cot-step-text">{step.intermediate_answer}</div>
                      </div>

                      {step.reasoning && (
                        <div className="cot-step-section">
                          <div className="cot-step-label">Reasoning</div>
                          <div className="cot-step-reasoning">{step.reasoning}</div>
                        </div>
                      )}

                      {step.confidence_score !== undefined && (
                        <div className="cot-step-section">
                          <div className="cot-step-label">Confidence</div>
                          <div className="cot-step-text">{Math.round(step.confidence_score * 100)}%</div>
                        </div>
                      )}
                    </div>
                  </div>

                  {index < reasoningSteps.length - 1 && (
                    <div className="cot-step-connector">
                      <div className="cot-step-connector-line"></div>
                      <div className="cot-step-connector-arrow">↓</div>
                    </div>
                  )}
                </React.Fragment>
              ))}
            </div>

            {finalSynthesis && (
              <div className="cot-panel-synthesis">
                <div className="cot-panel-synthesis-label">Final Synthesis</div>
                <div className="cot-panel-synthesis-text">{finalSynthesis}</div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ChainOfThoughtAccordion;
