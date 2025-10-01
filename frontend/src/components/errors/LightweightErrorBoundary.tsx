import React, { Component, ErrorInfo, ReactNode } from 'react';
import {
  ExclamationCircleIcon,
  ArrowPathIcon,
  HomeIcon,
  ClipboardDocumentIcon,
} from '@heroicons/react/24/outline';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorId: string;
}

class LightweightErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
    errorId: '',
  };

  public static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
      errorId: Date.now().toString(36) + Math.random().toString(36).substr(2),
    };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({
      error,
      errorInfo,
    });

    // Log error to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('ErrorBoundary caught an error:', error, errorInfo);
    }

    // In production, you would typically send this to your error reporting service
    // Example: sendErrorToService(error, errorInfo, this.state.errorId);
  }

  private handleReload = () => {
    window.location.reload();
  };

  private handleGoHome = () => {
    window.location.href = '/lightweight-dashboard';
  };

  private handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: '',
    });
  };

  private copyErrorDetails = async () => {
    const errorDetails = {
      errorId: this.state.errorId,
      message: this.state.error?.message,
      stack: this.state.error?.stack,
      componentStack: this.state.errorInfo?.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
    };

    try {
      await navigator.clipboard.writeText(JSON.stringify(errorDetails, null, 2));
      // You might want to show a notification here
      alert('Error details copied to clipboard');
    } catch (err) {
      console.error('Failed to copy error details:', err);
    }
  };

  public render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI
      return (
        <div className="min-h-screen bg-gray-10 flex items-center justify-center px-4">
          <div className="max-w-2xl w-full">
            <div className="card p-8 text-center">
              {/* Error Icon */}
              <div className="flex justify-center mb-6">
                <div className="p-4 bg-red-10 rounded-full">
                  <ExclamationCircleIcon className="w-16 h-16 text-red-50" />
                </div>
              </div>

              {/* Error Message */}
              <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-100 mb-4">
                  Oops! Something went wrong
                </h1>
                <p className="text-gray-70 mb-6">
                  We're sorry for the inconvenience. An unexpected error occurred while loading this page.
                  Our team has been notified and is working to fix the issue.
                </p>

                {/* Error ID for support */}
                <div className="bg-gray-10 p-4 rounded-lg mb-6">
                  <p className="text-sm text-gray-70 mb-2">Error ID (for support):</p>
                  <code className="text-sm font-mono text-gray-100 bg-gray-20 px-2 py-1 rounded">
                    {this.state.errorId}
                  </code>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-3 justify-center mb-6">
                <button
                  onClick={this.handleRetry}
                  className="btn-primary flex items-center justify-center space-x-2"
                >
                  <ArrowPathIcon className="w-4 h-4" />
                  <span>Try Again</span>
                </button>
                <button
                  onClick={this.handleReload}
                  className="btn-secondary flex items-center justify-center space-x-2"
                >
                  <ArrowPathIcon className="w-4 h-4" />
                  <span>Reload Page</span>
                </button>
                <button
                  onClick={this.handleGoHome}
                  className="btn-secondary flex items-center justify-center space-x-2"
                >
                  <HomeIcon className="w-4 h-4" />
                  <span>Go Home</span>
                </button>
              </div>

              {/* Error Details (Development only) */}
              {process.env.NODE_ENV === 'development' && this.state.error && (
                <div className="text-left">
                  <details className="mb-4">
                    <summary className="cursor-pointer text-gray-100 font-medium mb-2">
                      Error Details (Development Mode)
                    </summary>
                    <div className="bg-red-10 p-4 rounded-lg space-y-3">
                      <div>
                        <h4 className="font-medium text-red-50 mb-1">Error Message:</h4>
                        <p className="text-sm text-red-60 font-mono">
                          {this.state.error.message}
                        </p>
                      </div>

                      {this.state.error.stack && (
                        <div>
                          <h4 className="font-medium text-red-50 mb-1">Stack Trace:</h4>
                          <pre className="text-xs text-red-60 font-mono bg-red-20 p-3 rounded overflow-x-auto">
                            {this.state.error.stack}
                          </pre>
                        </div>
                      )}

                      {this.state.errorInfo?.componentStack && (
                        <div>
                          <h4 className="font-medium text-red-50 mb-1">Component Stack:</h4>
                          <pre className="text-xs text-red-60 font-mono bg-red-20 p-3 rounded overflow-x-auto">
                            {this.state.errorInfo.componentStack}
                          </pre>
                        </div>
                      )}
                    </div>
                  </details>

                  <button
                    onClick={this.copyErrorDetails}
                    className="btn-secondary text-sm flex items-center space-x-2"
                  >
                    <ClipboardDocumentIcon className="w-4 h-4" />
                    <span>Copy Error Details</span>
                  </button>
                </div>
              )}

              {/* Support Information */}
              <div className="mt-8 p-4 bg-gray-10 rounded-lg">
                <h3 className="font-medium text-gray-100 mb-2">Need Help?</h3>
                <p className="text-sm text-gray-70">
                  If this problem persists, please contact our support team with the error ID above.
                  We'll help you resolve this issue as quickly as possible.
                </p>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Higher-order component for easier usage
export const withErrorBoundary = <P extends object>(
  Component: React.ComponentType<P>,
  fallback?: ReactNode
) => {
  const WrappedComponent = (props: P) => (
    <LightweightErrorBoundary fallback={fallback}>
      <Component {...props} />
    </LightweightErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;
  return WrappedComponent;
};

export default LightweightErrorBoundary;
