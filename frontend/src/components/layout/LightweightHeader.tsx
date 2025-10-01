import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  MagnifyingGlassIcon,
  BellIcon,
  UserIcon,
  CogIcon,
  ArrowRightOnRectangleIcon,
  Bars3Icon,
} from '@heroicons/react/24/outline';
import { useAuth } from '../../contexts/AuthContext';
import { useNotification } from '../../contexts/NotificationContext';

interface LightweightHeaderProps {
  user: {
    id: string;
    username: string;
    email: string;
  };
  onMenuClick: () => void;
  isSideNavExpanded: boolean;
}

const LightweightHeader: React.FC<LightweightHeaderProps> = ({ user, onMenuClick, isSideNavExpanded }) => {
  const { logout } = useAuth();
  const { addNotification } = useNotification();
  const navigate = useNavigate();

  const handleSignOut = () => {
    logout();
  };

  return (
    <header className="header-bar h-16 px-6 flex items-center justify-between">
      {/* Left side - Menu button and brand */}
      <div className="flex items-center space-x-4">
        <button
          onClick={onMenuClick}
          className={`p-2 rounded-md hover:bg-gray-80 transition-colors duration-200 ${
            isSideNavExpanded ? 'bg-gray-80' : ''
          }`}
          aria-label="Menu"
        >
          <Bars3Icon className="w-5 h-5 text-white" />
        </button>

        <div className="flex items-center space-x-2">
          <a href="/" className="text-white hover:text-gray-20 transition-colors duration-200">
            <span className="text-lg font-semibold">RAG Modulo</span>
            <span className="ml-2 text-gray-30">Agentic Platform</span>
          </a>
        </div>
      </div>

      {/* Right side - Actions and user menu */}
      <div className="flex items-center space-x-4">
        {/* Search button */}
        <button
          onClick={() => navigate('/search')}
          className="p-2 rounded-md hover:bg-gray-80 transition-colors duration-200"
          aria-label="Search"
        >
          <MagnifyingGlassIcon className="w-5 h-5 text-white" />
        </button>

        {/* Notifications button */}
        <button
          onClick={() => addNotification('info', 'Notifications', 'No new notifications')}
          className="p-2 rounded-md hover:bg-gray-80 transition-colors duration-200 relative"
          aria-label="Notifications"
        >
          <BellIcon className="w-5 h-5 text-white" />
          {/* Notification badge */}
          <span className="absolute -top-1 -right-1 bg-red-50 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
            3
          </span>
        </button>

        {/* User menu */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => navigate('/profile')}
            className="btn-ghost text-white flex items-center space-x-2"
          >
            <UserIcon className="w-4 h-4" />
            <span className="hidden md:inline">Profile</span>
          </button>

          <button
            onClick={() => navigate('/profile')}
            className="btn-ghost text-white flex items-center space-x-2"
          >
            <CogIcon className="w-4 h-4" />
            <span className="hidden md:inline">Settings</span>
          </button>

          <button
            onClick={handleSignOut}
            className="btn-ghost text-white flex items-center space-x-2"
          >
            <ArrowRightOnRectangleIcon className="w-4 h-4" />
            <span className="hidden md:inline">Sign out</span>
          </button>
        </div>

        {/* User avatar */}
        <div className="flex items-center space-x-3 ml-4 pl-4 border-l border-gray-70">
          <div className="w-8 h-8 bg-blue-60 rounded-full flex items-center justify-center">
            <span className="text-white text-sm font-medium">
              {user.username.charAt(0).toUpperCase()}
            </span>
          </div>
          <div className="hidden lg:block">
            <div className="text-white text-sm font-medium">{user.username}</div>
            <div className="text-gray-30 text-xs">{user.email}</div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default LightweightHeader;
