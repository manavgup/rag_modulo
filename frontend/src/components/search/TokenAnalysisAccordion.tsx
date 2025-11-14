import React from 'react';
import { ChevronDown, ChevronUp, ChartColumn } from '@carbon/icons-react';
import './SearchInterface.scss';

interface TokenAnalysis {
  query_tokens?: number;
  context_tokens?: number;
  response_tokens?: number;
  system_tokens?: number;
  total_this_turn?: number;
  conversation_total?: number;
}

interface TokenAnalysisAccordionProps {
  tokenAnalysis: TokenAnalysis;
  isOpen: boolean;
  onToggle: () => void;
}

const TokenAnalysisAccordion: React.FC<TokenAnalysisAccordionProps> = ({ tokenAnalysis, isOpen, onToggle }) => {
  const formatNumber = (num?: number): string => {
    return (num ?? 0).toLocaleString();
  };

  const calculatePercentage = (value?: number): number => {
    if (!tokenAnalysis.total_this_turn || tokenAnalysis.total_this_turn === 0) return 0;
    return Math.round(((value ?? 0) / tokenAnalysis.total_this_turn) * 100);
  };

  return (
    <div className="token-accordion">
      <button
        className="token-accordion-header"
        onClick={onToggle}
        aria-expanded={isOpen}
      >
        <div className="token-accordion-title-section">
          <ChartColumn className="token-accordion-icon" size={20} />
          <span className="token-accordion-title">
            Token Analysis ({formatNumber(tokenAnalysis.total_this_turn)} tokens)
          </span>
        </div>
        {isOpen ? (
          <ChevronUp className="token-accordion-chevron" size={20} />
        ) : (
          <ChevronDown className="token-accordion-chevron" size={20} />
        )}
      </button>

      {isOpen && (
        <div className="token-accordion-content">
          <div className="token-usage-panel token-usage-info">
            <div className="token-usage-header">
              <h4 className="token-usage-title">This Turn Breakdown</h4>
            </div>

            <div className="token-usage-stats">
              <div className="token-usage-stat">
                <div className="token-usage-stat-label">Query Tokens</div>
                <div className="token-usage-stat-value">
                  {formatNumber(tokenAnalysis.query_tokens)}
                  <span className="token-usage-stat-percentage">
                    ({calculatePercentage(tokenAnalysis.query_tokens)}%)
                  </span>
                </div>
              </div>

              <div className="token-usage-stat">
                <div className="token-usage-stat-label">Context Tokens</div>
                <div className="token-usage-stat-value">
                  {formatNumber(tokenAnalysis.context_tokens)}
                  <span className="token-usage-stat-percentage">
                    ({calculatePercentage(tokenAnalysis.context_tokens)}%)
                  </span>
                </div>
              </div>

              <div className="token-usage-stat">
                <div className="token-usage-stat-label">Response Tokens</div>
                <div className="token-usage-stat-value">
                  {formatNumber(tokenAnalysis.response_tokens)}
                  <span className="token-usage-stat-percentage">
                    ({calculatePercentage(tokenAnalysis.response_tokens)}%)
                  </span>
                </div>
              </div>

              <div className="token-usage-stat">
                <div className="token-usage-stat-label">System Tokens</div>
                <div className="token-usage-stat-value">
                  {formatNumber(tokenAnalysis.system_tokens)}
                  <span className="token-usage-stat-percentage">
                    ({calculatePercentage(tokenAnalysis.system_tokens)}%)
                  </span>
                </div>
              </div>

              <div className="token-usage-stat">
                <div className="token-usage-stat-label">Total This Turn</div>
                <div className="token-usage-stat-value">
                  {formatNumber(tokenAnalysis.total_this_turn)}
                </div>
              </div>

              <div className="token-usage-stat">
                <div className="token-usage-stat-label">Conversation Total</div>
                <div className="token-usage-stat-value">
                  {formatNumber(tokenAnalysis.conversation_total)}
                </div>
              </div>
            </div>

            {/* Progress bar showing token usage */}
            <div className="token-usage-progress-container">
              <div
                className="token-usage-progress-bar"
                style={{
                  width: `${Math.min(
                    100,
                    ((tokenAnalysis.total_this_turn ?? 0) / (tokenAnalysis.conversation_total || 1)) * 100
                  )}%`,
                }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TokenAnalysisAccordion;
