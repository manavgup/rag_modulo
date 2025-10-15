import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  HomeIcon,
  ChatBubbleLeftRightIcon,
  DocumentIcon,
  UserIcon,
  CogIcon,
  ChartBarIcon,
  UserCircleIcon,
  QuestionMarkCircleIcon,
  XMarkIcon,
  WrenchScrewdriverIcon,
  EllipsisHorizontalCircleIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  MicrophoneIcon,
} from '@heroicons/react/24/outline';
import apiClient from '../../services/apiClient';
import AllChatsModal from '../modals/AllChatsModal';
import { useAuth } from '../../contexts/AuthContext';
import type { Podcast } from '../../services/apiClient';

interface LightweightSidebarProps {
  isExpanded: boolean;
  onClose: () => void;
}

interface Conversation {
  id: string;
  session_name: string;
  message_count: number;
  updated_at: Date;
  is_pinned: boolean;
  is_archived: boolean;
}

const LightweightSidebar: React.FC<LightweightSidebarProps> = ({ isExpanded, onClose }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const [recentConversations, setRecentConversations] = useState<Conversation[]>([]);
  const [recentPodcasts, setRecentPodcasts] = useState<Podcast[]>([]);
  const [isChatExpanded, setIsChatExpanded] = useState(false);
  const [isPodcastsExpanded, setIsPodcastsExpanded] = useState(false);
  const [isAllChatsModalOpen, setIsAllChatsModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isPodcastsLoading, setIsPodcastsLoading] = useState(false);

  // Define functions before useEffect
  const loadRecentPodcasts = useCallback(async () => {
    setIsPodcastsLoading(true);
    try {
      const userId = user?.id || '';
      if (!userId) return;

      const response = await apiClient.listPodcasts(userId);
      // Get the last 10 podcasts
      setRecentPodcasts(response.podcasts.slice(0, 10));
    } catch (error) {
      console.error('Failed to load recent podcasts:', error);
    } finally {
      setIsPodcastsLoading(false);
    }
  }, [user]);

  const loadRecentConversations = async () => {
    setIsLoading(true);
    try {
      const allConversations = await apiClient.getConversations();
      // Get the last 10 conversations
      setRecentConversations(allConversations.slice(0, 10));
    } catch (error) {
      console.error('Failed to load recent conversations:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadRecentConversations();
    loadRecentPodcasts();
  }, [loadRecentPodcasts]);

  const handleSelectConversation = (conversation: Conversation) => {
    // Navigate to search page with session parameter
    navigate(`/search?session=${conversation.id}`);

    // Expand chat menu to show it's active
    setIsChatExpanded(true);

    // Close sidebar on mobile
    if (window.innerWidth < 1024) {
      onClose();
    }
  };

  const toggleChatMenu = () => {
    setIsChatExpanded(!isChatExpanded);
  };

  const togglePodcastsMenu = () => {
    setIsPodcastsExpanded(!isPodcastsExpanded);
  };

  const handleSelectPodcast = (podcast: Podcast) => {
    navigate(`/podcasts/${podcast.podcast_id}`);
    setIsPodcastsExpanded(true);

    if (window.innerWidth < 1024) {
      onClose();
    }
  };

  const navigationItems = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: HomeIcon,
      path: '/dashboard',
    },
    {
      id: 'collections',
      label: 'Collections',
      icon: DocumentIcon,
      path: '/collections',
    },
    {
      id: 'agents',
      label: 'Agents',
      icon: UserIcon,
      path: '/agents',
    },
    {
      id: 'workflows',
      label: 'Workflows',
      icon: CogIcon,
      path: '/workflows',
    },
    {
      id: 'analytics',
      label: 'Analytics',
      icon: ChartBarIcon,
      path: '/analytics',
    },
    {
      id: 'admin',
      label: 'System Configuration',
      icon: WrenchScrewdriverIcon,
      path: '/admin',
    },
  ];

  const bottomItems = [
    {
      id: 'profile',
      label: 'Profile',
      icon: UserCircleIcon,
      path: '/profile',
    },
    {
      id: 'help',
      label: 'Help',
      icon: QuestionMarkCircleIcon,
      path: '/help',
    },
  ];

  const handleNavigate = (path: string) => {
    navigate(path);
    if (window.innerWidth < 1024) {
      onClose();
    }
  };

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <>
      {/* Mobile overlay */}
      {isExpanded && (
        <div
          className="fixed inset-0 bg-gray-100 bg-opacity-50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-16 h-[calc(100vh-4rem)] w-64 bg-white border-r border-gray-20 z-50 transform transition-transform duration-300 ${
          isExpanded ? 'translate-x-0' : '-translate-x-full'
        } lg:translate-x-0 lg:static lg:z-auto`}
      >
        <div className="flex flex-col h-full">
          {/* Mobile close button */}
          <div className="flex justify-end p-4 lg:hidden">
            <button
              onClick={onClose}
              className="p-2 rounded-md hover:bg-gray-20 transition-colors duration-200"
            >
              <XMarkIcon className="w-5 h-5 text-gray-70" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
            {/* Chat Menu with Nested Conversations */}
            <div className="space-y-1">
              <button
                onClick={toggleChatMenu}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-left transition-colors duration-200 ${
                  location.pathname === '/search'
                    ? 'bg-blue-60 text-white'
                    : 'text-gray-70 hover:bg-gray-20 hover:text-gray-100'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <ChatBubbleLeftRightIcon className="w-5 h-5 flex-shrink-0" />
                  <span className="font-medium">Chat</span>
                </div>
                {isChatExpanded ? (
                  <ChevronDownIcon className="w-4 h-4" />
                ) : (
                  <ChevronRightIcon className="w-4 h-4" />
                )}
              </button>

              {/* Nested Conversations */}
              {isChatExpanded && (
                <div className="ml-6 space-y-1">
                  {isLoading ? (
                    <div className="px-3 py-2 text-sm text-gray-60">
                      Loading conversations...
                    </div>
                  ) : (
                    <>
                      {recentConversations.map((conversation) => (
                        <button
                          key={conversation.id}
                          onClick={() => handleSelectConversation(conversation)}
                          className="w-full flex items-center px-3 py-2 rounded-lg text-left transition-colors duration-200 text-gray-70 hover:bg-gray-20 hover:text-gray-100 text-sm"
                        >
                          <span className="truncate">{conversation.session_name}</span>
                        </button>
                      ))}

                      {/* All Chats Option */}
                      <button
                        onClick={() => setIsAllChatsModalOpen(true)}
                        className="w-full flex items-center space-x-2 px-3 py-2 rounded-lg text-left transition-colors duration-200 text-gray-70 hover:bg-gray-20 hover:text-gray-100 text-sm"
                      >
                        <EllipsisHorizontalCircleIcon className="w-4 h-4 flex-shrink-0" />
                        <span>All chats</span>
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>

            {/* Podcasts Menu with Nested Podcasts */}
            <div className="space-y-1">
              <button
                onClick={togglePodcastsMenu}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-left transition-colors duration-200 ${
                  location.pathname.startsWith('/podcasts')
                    ? 'bg-blue-60 text-white'
                    : 'text-gray-70 hover:bg-gray-20 hover:text-gray-100'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <MicrophoneIcon className="w-5 h-5 flex-shrink-0" />
                  <span className="font-medium">Podcasts</span>
                </div>
                {isPodcastsExpanded ? (
                  <ChevronDownIcon className="w-4 h-4" />
                ) : (
                  <ChevronRightIcon className="w-4 h-4" />
                )}
              </button>

              {/* Nested Podcasts */}
              {isPodcastsExpanded && (
                <div className="ml-6 space-y-1">
                  {isPodcastsLoading ? (
                    <div className="px-3 py-2 text-sm text-gray-60">
                      Loading podcasts...
                    </div>
                  ) : (
                    <>
                      {/* All Podcasts Link */}
                      <button
                        onClick={() => handleNavigate('/podcasts')}
                        className={`w-full flex items-center px-3 py-2 rounded-lg text-left transition-colors duration-200 text-sm ${
                          location.pathname === '/podcasts'
                            ? 'bg-blue-50 text-white'
                            : 'text-gray-70 hover:bg-gray-20 hover:text-gray-100'
                        }`}
                      >
                        <span>All Podcasts</span>
                      </button>

                      {/* My Voices Link */}
                      <button
                        onClick={() => handleNavigate('/voices')}
                        className={`w-full flex items-center px-3 py-2 rounded-lg text-left transition-colors duration-200 text-sm ${
                          location.pathname === '/voices'
                            ? 'bg-blue-50 text-white'
                            : 'text-gray-70 hover:bg-gray-20 hover:text-gray-100'
                        }`}
                      >
                        <span>My Voices</span>
                      </button>

                      {/* Recent Podcasts */}
                      {recentPodcasts.length > 0 && (
                        <>
                          <div className="px-3 py-1 text-xs text-gray-60 font-medium">Recent</div>
                          {recentPodcasts.map((podcast) => (
                            <button
                              key={podcast.podcast_id}
                              onClick={() => handleSelectPodcast(podcast)}
                              className="w-full flex flex-col px-3 py-2 rounded-lg text-left transition-colors duration-200 text-gray-70 hover:bg-gray-20 hover:text-gray-100 text-sm"
                            >
                              <span className="truncate">
                                {podcast.title || `Podcast ${podcast.podcast_id.substring(0, 8)}`}
                              </span>
                              <span className={`text-xs ${
                                podcast.status === 'completed' ? 'text-green-50' :
                                podcast.status === 'generating' ? 'text-yellow-50' :
                                podcast.status === 'failed' ? 'text-red-50' :
                                'text-gray-50'
                              }`}>
                                {podcast.status.toUpperCase()}
                              </span>
                            </button>
                          ))}
                        </>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>

            {/* Other Navigation Items */}
            {navigationItems.map((item) => (
              <button
                key={item.id}
                onClick={() => handleNavigate(item.path)}
                className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-left transition-colors duration-200 ${
                  isActive(item.path)
                    ? 'bg-blue-60 text-white'
                    : 'text-gray-70 hover:bg-gray-20 hover:text-gray-100'
                }`}
              >
                <item.icon className="w-5 h-5 flex-shrink-0" />
                <span className="font-medium">{item.label}</span>
              </button>
            ))}
          </nav>

          {/* Bottom navigation */}
          <div className="px-4 py-6 border-t border-gray-20 space-y-2">
            {bottomItems.map((item) => (
              <button
                key={item.id}
                onClick={() => handleNavigate(item.path)}
                className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-left transition-colors duration-200 ${
                  isActive(item.path)
                    ? 'bg-blue-60 text-white'
                    : 'text-gray-70 hover:bg-gray-20 hover:text-gray-100'
                }`}
              >
                <item.icon className="w-5 h-5 flex-shrink-0" />
                <span className="font-medium">{item.label}</span>
              </button>
            ))}
          </div>
        </div>
      </aside>

      {/* All Chats Modal */}
      <AllChatsModal
        isOpen={isAllChatsModalOpen}
        onClose={() => setIsAllChatsModalOpen(false)}
        onSelectConversation={handleSelectConversation}
      />
    </>
  );
};

export default LightweightSidebar;
