import React, { useState, useEffect } from 'react';
import { XMarkIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline';
import apiClient from '../../services/apiClient';
import { useNotification } from '../../contexts/NotificationContext';

interface Conversation {
  id: string;
  session_name: string;
  message_count: number;
  updated_at: Date;
  is_pinned: boolean;
  is_archived: boolean;
}

interface AllChatsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectConversation: (conversation: Conversation) => void;
}

const AllChatsModal: React.FC<AllChatsModalProps> = ({ isOpen, onClose, onSelectConversation }) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [filteredConversations, setFilteredConversations] = useState<Conversation[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { addNotification } = useNotification();

  useEffect(() => {
    if (isOpen) {
      loadConversations();
    }
  }, [isOpen]);

  useEffect(() => {
    if (searchQuery.trim() === '') {
      setFilteredConversations(conversations);
    } else {
      const filtered = conversations.filter(conv =>
        conv.session_name.toLowerCase().includes(searchQuery.toLowerCase())
      );
      setFilteredConversations(filtered);
    }
  }, [searchQuery, conversations]);

  const loadConversations = async () => {
    setIsLoading(true);
    try {
      const conversations = await apiClient.getConversations();
      setConversations(conversations);
    } catch (error) {
      console.error('Failed to load conversations:', error);
      addNotification('error', 'Error', 'Failed to load conversations');
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (date: Date) => {
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));

    if (diffInHours < 24) {
      return `${diffInHours} hours ago`;
    } else {
      const diffInDays = Math.floor(diffInHours / 24);
      return `${diffInDays} days ago`;
    }
  };

  const handleSelectConversation = (conversation: Conversation) => {
    onSelectConversation(conversation);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-100 bg-opacity-75 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-20">
          <div>
            <h2 className="text-xl font-semibold text-gray-100">Your chat history</h2>
            <p className="text-sm text-gray-60 mt-1">
              {conversations.length} chats with Claude
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-20 rounded-lg transition-colors"
          >
            <XMarkIcon className="w-5 h-5 text-gray-70" />
          </button>
        </div>

        {/* Search */}
        <div className="p-6 border-b border-gray-20">
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-60" />
            <input
              type="text"
              placeholder="Search your chats..."
              className="w-full pl-10 pr-4 py-2 border border-gray-30 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-60 focus:border-transparent"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        {/* Conversations List */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-60"></div>
            </div>
          ) : filteredConversations.length > 0 ? (
            <div className="space-y-1 p-4">
              {filteredConversations.map((conversation) => (
                <div
                  key={conversation.id}
                  onClick={() => handleSelectConversation(conversation)}
                  className="flex items-center justify-between p-3 hover:bg-gray-10 rounded-lg cursor-pointer transition-colors group"
                >
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-gray-100 truncate group-hover:text-blue-60">
                      {conversation.session_name}
                    </h3>
                    <p className="text-sm text-gray-60 mt-1">
                      Last message {formatDate(conversation.updated_at)}
                    </p>
                  </div>
                  <div className="text-right text-xs text-gray-60 ml-4">
                    {conversation.message_count} messages
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="text-gray-60 text-center">
                <p className="text-lg font-medium">No conversations found</p>
                {searchQuery ? (
                  <p className="text-sm mt-1">Try a different search term</p>
                ) : (
                  <p className="text-sm mt-1">Start a new conversation to get started</p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-20 bg-gray-5">
          <p className="text-xs text-gray-60 text-center">
            Select a conversation to continue chatting
          </p>
        </div>
      </div>
    </div>
  );
};

export default AllChatsModal;
