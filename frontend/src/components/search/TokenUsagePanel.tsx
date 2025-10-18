import React from 'react';
import { ExclamationTriangleIcon, InformationCircleIcon } from '@heroicons/react/24/outline';

interface TokenUsagePanelProps {
  tokenWarning: {
    current_tokens: number;
    limit_tokens: number;
    percentage_used: number;
    severity: 'info' | 'warning' | 'critical';
    message: string;
    suggested_action?: string;
    warning_type: string;
  };
}

/**
 * TokenUsagePanel
 *
 * Displays token usage with progress bar and warnings.
 * Implements GitHub Issue #283 (token usage visualization).
 */
const TokenUsagePanel: React.FC<TokenUsagePanelProps> = ({ tokenWarning }) => {
  const getSeverityColor = () => {
    switch (tokenWarning.severity) {
      case 'critical': return 'token-usage-critical';
      case 'warning': return 'token-usage-warning';
      default: return 'token-usage-info';
    }
  };

  return (
    <div className={`token-usage-panel ${getSeverityColor()}`}>
      {/* Header */}
      <div className="token-usage-header">
        <h4 className="token-usage-title">Token Usage</h4>
        {tokenWarning.severity === 'critical' && <ExclamationTriangleIcon className="w-5 h-5" />}
        {tokenWarning.severity === 'warning' && <ExclamationTriangleIcon className="w-5 h-5" />}
        {tokenWarning.severity === 'info' && <InformationCircleIcon className="w-5 h-5" />}
      </div>

      {/* Progress Bar */}
      <div className="token-usage-progress-container">
        <div className="token-usage-progress-bar" style={{ width: `${Math.min(tokenWarning.percentage_used, 100)}%` }}></div>
      </div>

      {/* Stats Grid */}
      <div className="token-usage-stats">
        <div className="token-usage-stat">
          <span className="token-usage-stat-label">Current:</span>
          <span className="token-usage-stat-value">{tokenWarning.current_tokens.toLocaleString()}</span>
        </div>
        <div className="token-usage-stat">
          <span className="token-usage-stat-label">Limit:</span>
          <span className="token-usage-stat-value">{tokenWarning.limit_tokens.toLocaleString()}</span>
        </div>
        <div className="token-usage-stat">
          <span className="token-usage-stat-label">Usage:</span>
          <span className="token-usage-stat-value">{tokenWarning.percentage_used.toFixed(1)}%</span>
        </div>
      </div>

      {/* Message */}
      <div className="token-usage-message">
        <InformationCircleIcon className="w-4 h-4" />
        <span>{tokenWarning.message}</span>
      </div>

      {/* Suggested Action */}
      {tokenWarning.suggested_action && (
        <div className="token-usage-suggestion">
          <strong>Suggestion:</strong> {tokenWarning.suggested_action}
        </div>
      )}
    </div>
  );
};

export default TokenUsagePanel;
