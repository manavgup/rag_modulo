import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ExclamationTriangleIcon,
  HomeIcon,
  ArrowLeftIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';

const LightweightNotFound: React.FC = () => {
  const navigate = useNavigate();

  const goHome = () => {
    navigate('/lightweight-dashboard');
  };

  const goBack = () => {
    window.history.back();
  };

  const suggestedLinks = [
    { name: 'Dashboard', path: '/lightweight-dashboard', icon: HomeIcon },
    { name: 'Collections', path: '/lightweight-collections', icon: MagnifyingGlassIcon },
    { name: 'Search', path: '/lightweight-search', icon: MagnifyingGlassIcon },
  ];

  return (
    <div className="min-h-screen bg-gray-10 flex items-center justify-center px-4">
      <div className="max-w-lg w-full text-center">
        {/* Error Icon */}
        <div className="flex justify-center mb-6">
          <div className="p-4 bg-yellow-10 rounded-full">
            <ExclamationTriangleIcon className="w-16 h-16 text-yellow-30" />
          </div>
        </div>

        {/* Error Message */}
        <div className="mb-8">
          <h1 className="text-6xl font-bold text-gray-100 mb-4">404</h1>
          <h2 className="text-2xl font-semibold text-gray-100 mb-3">Page Not Found</h2>
          <p className="text-gray-70 mb-6">
            The page you're looking for doesn't exist or has been moved.
            Don't worry, you can find what you're looking for using the links below.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center mb-8">
          <button
            onClick={goHome}
            className="btn-primary flex items-center justify-center space-x-2"
          >
            <HomeIcon className="w-4 h-4" />
            <span>Go to Dashboard</span>
          </button>
          <button
            onClick={goBack}
            className="btn-secondary flex items-center justify-center space-x-2"
          >
            <ArrowLeftIcon className="w-4 h-4" />
            <span>Go Back</span>
          </button>
        </div>

        {/* Suggested Links */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-100 mb-4">Try these instead:</h3>
          <div className="space-y-2">
            {suggestedLinks.map((link) => (
              <button
                key={link.path}
                onClick={() => navigate(link.path)}
                className="w-full flex items-center justify-center space-x-2 p-3 text-gray-70 hover:text-gray-100 hover:bg-gray-10 rounded-lg transition-colors"
              >
                <link.icon className="w-4 h-4" />
                <span>{link.name}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Additional Help */}
        <div className="mt-6 text-sm text-gray-60">
          <p>
            Still having trouble? Try using the search function or{' '}
            <button
              onClick={() => navigate('/lightweight-help')}
              className="text-blue-60 hover:text-blue-70 underline"
            >
              visit our help center
            </button>
            .
          </p>
        </div>
      </div>
    </div>
  );
};

export default LightweightNotFound;
