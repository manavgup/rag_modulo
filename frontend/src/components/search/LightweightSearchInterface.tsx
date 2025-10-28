import React, { useState, useEffect, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  PaperAirplaneIcon,
  LinkIcon,
} from '@heroicons/react/24/outline';
import { useNotification } from '../../contexts/NotificationContext';
import MessageMetadataFooter from './MessageMetadataFooter';
import SourceModal from './SourceModal';
import SourcesAccordion from './SourcesAccordion';
import ChainOfThoughtAccordion from './ChainOfThoughtAccordion';
import TokenAnalysisAccordion from './TokenAnalysisAccordion';
import './SearchInterface.scss';

// Import API client and WebSocket client
import apiClient, { Collection, CollectionDocument, ConversationSession, CreateConversationInput } from '../../services/apiClient';
import websocketClient, { ChatMessage as WSChatMessage, ConnectionStatus } from '../../services/websocketClient';

// Use ChatMessage from WebSocket client
type ChatMessage = WSChatMessage;

const LightweightSearchInterface: React.FC = () => {
  const { addNotification } = useNotification();
  const location = useLocation();
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedCollection, setSelectedCollection] = useState('all');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [showSources, setShowSources] = useState<{ [key: string]: boolean }>({});
  const [showTokens, setShowTokens] = useState<{ [key: string]: boolean }>({});
  const [showCoT, setShowCoT] = useState<{ [key: string]: boolean }>({});
  const [sourceModalOpen, setSourceModalOpen] = useState<string | null>(null);
  const [sourceModalSources, setSourceModalSources] = useState<any[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({ connected: false, connecting: false });
  const [isTyping, setIsTyping] = useState(false);
  const [currentCollectionId, setCurrentCollectionId] = useState<string>('');
  const [currentCollectionName, setCurrentCollectionName] = useState<string>('');

  // Message referencing state
  const [referencedMessage, setReferencedMessage] = useState<ChatMessage | null>(null);

  // Summary state
  const [showSummaryModal, setShowSummaryModal] = useState(false);
  const [conversationSummary, setConversationSummary] = useState<any>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);

  // Conversation management state
  const [conversations, setConversations] = useState<ConversationSession[]>([]);
  const [currentConversation, setCurrentConversation] = useState<ConversationSession | null>(null);
  const [showNewConversationModal, setShowNewConversationModal] = useState(false);
  const [newConversationName, setNewConversationName] = useState('');

  // Load specific conversation - wrapped in useCallback to fix exhaustive-deps
  const loadSpecificConversation = useCallback(async (sessionId: string) => {
    try {
      const conversation = await apiClient.getConversation(sessionId);
      setCurrentConversation(conversation);
      setCurrentCollectionId(conversation.collection_id);

      // Load messages for this conversation
      const messages = await apiClient.getConversationMessages(sessionId);
      const formattedMessages: ChatMessage[] = messages.map(msg => ({
        id: msg.id,
        content: msg.content,
        type: msg.role === 'user' ? 'user' : 'assistant',
        timestamp: msg.created_at,
        sources: msg.sources,
        metadata: msg.metadata
      }));
      setMessages(formattedMessages);

      // Load collection info
      try {
        const collection = await apiClient.getCollection(conversation.collection_id);
        setCurrentCollectionName(collection.name);
        setSelectedCollection(conversation.collection_id);
      } catch (error) {
        // Collection load failed - non-critical, continue
      }
    } catch (error) {
      addNotification('error', 'Error', 'Failed to load conversation');
    }
  }, [addNotification]);

  // Load collection data from location state (passed from collections page)
  useEffect(() => {
    if (location.state) {
      const { collectionId, collectionName, newConversation } = location.state as {
        collectionId?: string;
        collectionName?: string;
        newConversation?: boolean;
      };

      if (collectionId && collectionName) {
        setCurrentCollectionId(collectionId);
        setCurrentCollectionName(collectionName);
        setSelectedCollection(collectionId);

        // If newConversation flag is set, clear any existing conversation
        if (newConversation) {
          setCurrentConversation(null);
          setMessages([]);
          localStorage.removeItem(`lastConversation_${collectionId}`);
          addNotification('info', 'New Conversation', `Starting fresh conversation with ${collectionName}`);
        } else {
          addNotification('info', 'Collection Loaded', `Now chatting with ${collectionName}`);
        }
      }
    }
  }, [location.state, addNotification]);

  // Check for session parameter in URL
  useEffect(() => {
    const urlParams = new URLSearchParams(location.search);
    const sessionId = urlParams.get('session');

    if (sessionId) {
      loadSpecificConversation(sessionId);
    }
  }, [location.search, loadSpecificConversation]);

  // Load conversations for current collection
  useEffect(() => {
    const loadConversations = async () => {
      if (!currentCollectionId || currentCollectionId === 'all') return;

      try {
        const conversationsData = await apiClient.getConversations(undefined, currentCollectionId);
        setConversations(conversationsData);

        // Check if we're in "new conversation" mode from location state
        const isNewConversationMode = location.state?.newConversation === true;

        // Only auto-load conversation if NOT in new conversation mode
        if (!isNewConversationMode) {
          // Try to restore last selected conversation from localStorage
          const lastConversationId = localStorage.getItem(`lastConversation_${currentCollectionId}`);
          let conversationToSelect = null;

          if (lastConversationId) {
            conversationToSelect = conversationsData.find(c => c.id === lastConversationId);
          }

          // If no stored conversation or it doesn't exist, select the first one
          if (!conversationToSelect && conversationsData.length > 0) {
            conversationToSelect = conversationsData[0];
          }

          // If no current conversation is selected, load the selected conversation
          if (!currentConversation && conversationToSelect) {
            setCurrentConversation(conversationToSelect);
            // Store the selection for persistence
            localStorage.setItem(`lastConversation_${currentCollectionId}`, conversationToSelect.id);

            // Load messages for this conversation
            const messages = await apiClient.getConversationMessages(conversationToSelect.id);
            // Convert to ChatMessage format
            const chatMessages: ChatMessage[] = messages.map(msg => ({
              id: msg.id,
              type: msg.role === 'user' ? 'user' : 'assistant',
              content: msg.content,
              timestamp: new Date(msg.created_at),
              sources: msg.sources,
              metadata: msg.metadata,
              token_warning: msg.token_warning as any,
            }));
            setMessages(chatMessages);
          }
        }
      } catch (error) {
        addNotification('error', 'Loading Error', 'Failed to load conversations.');
      }
    };

    loadConversations();
  }, [currentCollectionId, addNotification, currentConversation, location.state?.newConversation]);

  // Load collections and set up WebSocket connection
  useEffect(() => {
    const loadCollections = async () => {
      try {
        const collectionsData = await apiClient.getCollections();
        // Create a proper "All Collections" entry
        const allCollectionsEntry: Collection = {
          id: 'all',
          name: 'All Collections',
          description: 'Virtual collection containing all documents',
          status: 'ready',
          documents: [],
          createdAt: new Date(),
          updatedAt: new Date(),
          documentCount: 0
        };
        const formattedCollections = [
          allCollectionsEntry,
          ...collectionsData
        ];
        setCollections(formattedCollections);
      } catch (error) {
        addNotification('error', 'Loading Error', 'Failed to load collections.');
      }
    };

    loadCollections();

    // Set up WebSocket event handlers
    const unsubscribeMessage = websocketClient.onMessage((message: ChatMessage) => {
      setMessages(prev => [...prev, message]);
      setIsLoading(false);
    });

    const unsubscribeStatus = websocketClient.onStatus((status: ConnectionStatus) => {
      setConnectionStatus(status);
      if (status.connected) {
        addNotification('success', 'Connected', 'WebSocket connection established.');
      } else if (status.error) {
        addNotification('error', 'Connection Error', status.error);
      }
    });

    const unsubscribeTyping = websocketClient.onTyping((typing: boolean) => {
      setIsTyping(typing);
    });

    return () => {
      unsubscribeMessage();
      unsubscribeStatus();
      unsubscribeTyping();
    };
  }, [addNotification]);

  const handleRestApiSearch = async (query: string, collectionId: string, conversation?: ConversationSession | null) => {
    try {
      // Get user ID from auth endpoint
      let userId: string;

      try {
        const currentUser = await apiClient.getCurrentUser();
        userId = currentUser.id;
      } catch (authError) {
        // If auth fails, the search will likely fail too, but let's try anyway
        // The backend should handle the auth properly
        throw new Error('Authentication required. Please ensure you are logged in.');
      }

      let searchResponse: any;

      // Use the passed conversation or fall back to state
      const activeConversation = conversation || currentConversation;

      // Use conversation endpoint if we have an active conversation (saves messages)
      if (activeConversation) {
        const conversationMessage = await apiClient.sendConversationMessage(activeConversation.id, query);

        // Convert conversation message response to search response format
        // Note: conversation endpoint returns sources directly, not query_results
        searchResponse = {
          answer: conversationMessage.content,
          sources: conversationMessage.sources || [],
          documents: conversationMessage.sources?.map((source: any) => ({
            document_name: source.document_name,
            content: source.content,
            metadata: source.metadata
          })) || [],
          // Don't include query_results from conversation endpoint
          metadata: conversationMessage.metadata,
          token_warning: conversationMessage.token_warning,
          cot_output: conversationMessage.metadata?.search_metadata?.cot_output
        };
      } else {
        // Fallback to stateless search (does not save conversation)
        searchResponse = await apiClient.search({
          question: query,
          collection_id: collectionId,
          user_id: userId,
          config_metadata: {
            timestamp: new Date().toISOString(),
            source: 'rest_api',
            cot_enabled: true,
            show_cot_steps: true,
            referenced_message: referencedMessage ? {
              id: referencedMessage.id,
              content: referencedMessage.content,
              timestamp: referencedMessage.timestamp.toISOString(),
              type: referencedMessage.type
            } : undefined
          }
        });
      }

      // Map API response to ChatMessage format - handle both query_result and documents/sources
      let sources: Array<{
        document_name: string;
        content: string;
        metadata: Record<string, any>;
      }> = [];

      // Prioritize query_results as they contain chunk-specific information with page numbers
      if (searchResponse.query_results && Array.isArray(searchResponse.query_results) && searchResponse.query_results.length > 0) {
        // Create a mapping of document_id to document_name from the documents array
        // Since DocumentMetadata doesn't have document_id, we'll create a mapping based on the order
        // This is a temporary solution until the backend provides better document_id mapping
        const docIdToNameMap = new Map<string, string>();

        if (searchResponse.documents && searchResponse.documents.length > 0) {
          // Get all unique document IDs from query results
          const uniqueDocIds: string[] = Array.from(new Set(searchResponse.query_results.map((r: any) => r.chunk.document_id as string)));

          // Map document IDs to document names (using order as a heuristic)
          uniqueDocIds.forEach((docId, index) => {
            if (searchResponse.documents && index < searchResponse.documents.length) {
              const doc = searchResponse.documents[index];
              if (doc && doc.document_name) {
                docIdToNameMap.set(docId, doc.document_name);
              }
            }
          });
        }

        // Use query_results chunks - contains chunk-specific information with page numbers
        sources = searchResponse.query_results.map((result: any) => {
          // Try to get document name from our mapping
          let documentName = 'Unknown Document';
          if (docIdToNameMap.has(result.chunk.document_id)) {
            documentName = docIdToNameMap.get(result.chunk.document_id)!;
          } else {
            // Fallback: use the first document name as a default
            const firstDoc = searchResponse.documents?.[0];
            if (firstDoc && firstDoc.document_name) {
              documentName = firstDoc.document_name;
            }
          }

          // Finally, check collections lookup
          if (documentName === 'Unknown Document') {
            const collection = collections.find(c => c.id === collectionId);
            const document = collection?.documents?.find((d: CollectionDocument) => d.id === result.chunk.document_id);
            if (document?.name) {
              documentName = document.name;
            }
          }

          // Clean up the document name (remove file extension for display)
          const cleanDocumentName = documentName.replace(/\.(pdf|txt|docx?|md)$/i, '');

          return {
            document_name: `${cleanDocumentName} (Page ${result.chunk.metadata.page_number || 'Unknown'})`,
            content: result.chunk.text,
            metadata: {
              ...result.chunk.metadata,
              score: result.score,
              chunk_id: result.chunk.chunk_id,
              document_id: result.chunk.document_id,
              original_document_name: documentName
            }
          };
        });
      } else if (searchResponse.documents && Array.isArray(searchResponse.documents)) {
        // Fallback to documents format (may lack chunk-specific page numbers)
        sources = searchResponse.documents.map((doc: any, index: number) => {
          // Try to extract document name and page number from the document
          const documentName = doc.document_name || doc.title || doc.name || `Document ${index + 1}`;
          const pageNumber = doc.page_number || doc.metadata?.page_number || 'Unknown';
          const content = doc.content || doc.text || doc.chunk_text || '';

          return {
            document_name: `${documentName} (Page ${pageNumber})`,
            content: content,
            metadata: {
              ...doc.metadata,
              page_number: pageNumber,
              document_id: doc.document_id || doc.id,
              score: doc.score || doc.relevance_score
            }
          };
        });
      } else if (searchResponse.sources) {
        // Use existing sources format
        sources = searchResponse.sources;
      }

      // Add assistant response to messages
      const assistantMessage: ChatMessage = {
        id: Date.now().toString(),
        type: 'assistant',
        content: searchResponse.answer,
        timestamp: new Date(),
        sources: sources,
        metadata: searchResponse.metadata,
        token_warning: searchResponse.token_warning,
        cot_output: searchResponse.cot_output,
      };

      setMessages(prev => [...prev, assistantMessage]);
      setIsLoading(false);
      addNotification('success', 'Search Complete', 'Search completed successfully via REST API.');
    } catch (error) {
      setIsLoading(false);
      throw error;
    }
  };

  // Conversation management functions
  const createNewConversation = async () => {
    if (!newConversationName.trim() || !currentCollectionId || currentCollectionId === 'all') {
      addNotification('warning', 'Invalid Input', 'Please enter a conversation name and select a collection.');
      return;
    }

    try {
      const conversationData: CreateConversationInput = {
        collection_id: currentCollectionId,
        session_name: newConversationName.trim(),
        context_window_size: 4000,
        max_messages: 50,
        is_archived: false,
        is_pinned: false,
        metadata: {
          created_from: 'search_interface',
          collection_name: currentCollectionName
        }
      };

      const newConversation = await apiClient.createConversation(conversationData);
      setConversations(prev => [newConversation, ...prev]);
      setCurrentConversation(newConversation);

      // Store the new conversation for persistence
      if (currentCollectionId) {
        localStorage.setItem(`lastConversation_${currentCollectionId}`, newConversation.id);
      }

      setMessages([]); // Clear messages for new conversation
      setNewConversationName('');
      setShowNewConversationModal(false);
      addNotification('success', 'Conversation Created', `Created new conversation: ${newConversation.session_name}`);
    } catch (error) {
      addNotification('error', 'Creation Error', 'Failed to create new conversation.');
    }
  };

  const switchToConversation = async (conversation: ConversationSession) => {
    if (currentConversation?.id === conversation.id) return;

    try {
      setCurrentConversation(conversation);

      // Store the selection for persistence across browser sessions
      if (currentCollectionId) {
        localStorage.setItem(`lastConversation_${currentCollectionId}`, conversation.id);
      }

      // Load messages for this conversation
      const messages = await apiClient.getConversationMessages(conversation.id);
      const chatMessages: ChatMessage[] = messages.map(msg => ({
        id: msg.id,
        type: msg.role === 'user' ? 'user' : 'assistant',
        content: msg.content,
        timestamp: new Date(msg.created_at),
        sources: msg.sources,
        metadata: msg.metadata,
        token_warning: msg.token_warning as any,
      }));
      setMessages(chatMessages);
      addNotification('info', 'Conversation Switched', `Switched to ${conversation.session_name}`);
    } catch (error) {
      addNotification('error', 'Switch Error', 'Failed to switch conversation.');
    }
  };

  // eslint-disable-next-line @typescript-eslint/no-unused-vars, no-unused-vars
  const deleteConversation = async (conversationId: string) => {
    try {
      await apiClient.deleteConversation(conversationId);
      setConversations(prev => prev.filter(c => c.id !== conversationId));

      // If we deleted the current conversation, switch to another or clear
      if (currentConversation?.id === conversationId) {
        const remaining = conversations.filter(c => c.id !== conversationId);
        if (remaining.length > 0) {
          await switchToConversation(remaining[0]);
        } else {
          setCurrentConversation(null);
          setMessages([]);
        }
      }
      addNotification('success', 'Conversation Deleted', 'Conversation deleted successfully.');
    } catch (error) {
      addNotification('error', 'Delete Error', 'Failed to delete conversation.');
    }
  };

  const loadConversationSummary = async (conversationId: string, summaryType: string = 'brief') => {
    setSummaryLoading(true);
    try {
      const summary = await apiClient.getConversationSummary(conversationId, summaryType);
      setConversationSummary(summary);
      setShowSummaryModal(true);
      addNotification('success', 'Summary Generated', `Generated ${summaryType} summary for conversation.`);
    } catch (error) {
      addNotification('error', 'Summary Error', 'Failed to generate conversation summary.');
    } finally {
      setSummaryLoading(false);
    }
  };

  // eslint-disable-next-line @typescript-eslint/no-unused-vars, no-unused-vars
  const exportConversation = async (conversationId: string, format: string = 'json') => {
    try {
      const exportData = await apiClient.exportConversation(conversationId, format);

      // Create blob and download
      const blob = new Blob([JSON.stringify(exportData, null, 2)], {
        type: format === 'json' ? 'application/json' : 'text/plain'
      });

      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `conversation-${conversationId}-${new Date().toISOString().split('T')[0]}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      addNotification('success', 'Export Complete', `Conversation exported as ${format.toUpperCase()}.`);
    } catch (error) {
      addNotification('error', 'Export Error', 'Failed to export conversation.');
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!query.trim()) {
      addNotification('warning', 'Empty Query', 'Please enter a search query.');
      return;
    }

    // WebSocket connection is optional - we can fall back to REST API

    const collectionId = currentCollectionId || selectedCollection;
    if (!collectionId || collectionId === 'all') {
      addNotification('warning', 'No Collection Selected', 'Please select a specific collection to chat with.');
      return;
    }

    // Ensure we have a conversation for this collection
    let activeConversation = currentConversation;
    if (!currentConversation) {
      // Create a new conversation automatically
      try {
        const conversationData: CreateConversationInput = {
          collection_id: collectionId,
          session_name: `Chat with ${currentCollectionName || 'Collection'} - ${new Date().toLocaleTimeString()}`,
          context_window_size: 4000,
          max_messages: 50,
          is_archived: false,
          is_pinned: false,
          metadata: {
            created_from: 'auto_search',
            collection_name: currentCollectionName
          }
        };

        const newConversation = await apiClient.createConversation(conversationData);
        activeConversation = newConversation;  // Use local variable
        setCurrentConversation(newConversation);
        setConversations(prev => [newConversation, ...prev]);
        addNotification('info', 'Conversation Created', `Created new conversation for your chat.`);
      } catch (error) {
        addNotification('error', 'Conversation Error', 'Failed to create conversation. Using temporary session.');
      }
    }

    setIsLoading(true);

    // Add user message locally
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: query,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);

    // Clear the referenced message after sending
    const wasReferencing = referencedMessage !== null;
    if (wasReferencing) {
      setReferencedMessage(null);
    }

    setQuery('');

    try {
      // Primary method: REST API (more reliable)
      await handleRestApiSearch(query, collectionId, activeConversation);
    } catch (restError) {
      // Fallback to WebSocket if available
      if (connectionStatus.connected) {
        try {
          websocketClient.sendMessage(query, collectionId, {
            selectedCollection: collectionId,
            timestamp: new Date().toISOString()
          }, currentConversation?.id);
        } catch (wsError) {
          addNotification('error', 'Search Error', 'Both REST API and WebSocket search failed. Please try again.');
          setIsLoading(false);
        }
      } else {
        addNotification('error', 'Search Error', 'Search failed and no WebSocket connection available. Please try again.');
        setIsLoading(false);
      }
    }
  };

  const toggleSources = (messageId: string) => {
    setShowSources(prev => ({
      ...prev,
      [messageId]: !prev[messageId]
    }));
  };

  const toggleTokens = (messageId: string) => {
    setShowTokens(prev => ({
      ...prev,
      [messageId]: !prev[messageId]
    }));
  };

  const toggleCoT = (messageId: string) => {
    setShowCoT(prev => ({
      ...prev,
      [messageId]: !prev[messageId]
    }));
  };

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Fixed Header */}
      <div className="sticky top-0 z-10 bg-white border-b border-gray-200 px-4 py-3">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-gray-900">
              {currentCollectionName || 'Chat with Documents'}
            </h1>
          </div>
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${connectionStatus.connected ? 'bg-green-500' : connectionStatus.connecting ? 'bg-yellow-500' : 'bg-gray-400'}`}></div>
            <span className="text-xs text-gray-500">
              {connectionStatus.connected ? 'Connected' : connectionStatus.connecting ? 'Connecting...' : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-6 py-6 space-y-6">
                {messages.map((message) => (
                  <div key={message.id} className="py-4">
                    <div className="max-w-7xl mx-auto">
                      {/* Referenced message indicator */}
                      {referencedMessage?.id === message.id && (
                        <div className="mb-2 p-2 bg-yellow-10 border border-yellow-30 rounded-md max-w-3xl">
                          <div className="flex items-center space-x-2 text-xs text-yellow-70">
                            <LinkIcon className="w-3 h-3" />
                            <span>This message is being referenced</span>
                          </div>
                        </div>
                      )}

                      {/* Message content and accordions stacked vertically */}
                      <div className="space-y-4">
                        {/* Main message content */}
                        <div className="max-w-3xl">
                          <div className="prose max-w-none text-gray-900">
                            {message.type === 'assistant' ? (
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {message.content}
                              </ReactMarkdown>
                            ) : (
                              <div className="whitespace-pre-wrap">{message.content}</div>
                            )}
                          </div>

                          {/* Message Metadata Footer with Click Handlers */}
                          {message.type === 'assistant' && (
                            <MessageMetadataFooter
                              sourcesCount={message.sources?.length || 0}
                              stepsCount={message.cot_output?.steps?.length || message.cot_output?.total_steps}
                              tokenCount={message.metadata?.token_analysis?.total_this_turn || message.token_warning?.current_tokens}
                              responseTime={message.metadata?.execution_time}
                              onSourcesClick={() => toggleSources(message.id)}
                              onStepsClick={() => toggleCoT(message.id)}
                              onTokensClick={() => toggleTokens(message.id)}
                            />
                          )}
                        </div>

                        {/* Accordions below message - Only show when opened */}
                        {message.type === 'assistant' && (showSources[message.id] || showCoT[message.id] || showTokens[message.id]) && (
                          <div className="space-y-2">
                            {/* Sources Accordion - Only render when open */}
                            {showSources[message.id] && message.sources && message.sources.length > 0 && (
                              <SourcesAccordion
                                sources={message.sources}
                                isOpen={true}
                                onToggle={() => toggleSources(message.id)}
                              />
                            )}

                            {/* Chain of Thought Accordion - Only render when open */}
                            {showCoT[message.id] && message.cot_output && message.cot_output.steps && message.cot_output.steps.length > 0 && (
                              <ChainOfThoughtAccordion
                                cotOutput={message.cot_output}
                                isOpen={true}
                                onToggle={() => toggleCoT(message.id)}
                              />
                            )}

                            {/* Token Analysis Accordion - Only render when open */}
                            {showTokens[message.id] && message.metadata?.token_analysis && (
                              <TokenAnalysisAccordion
                                tokenAnalysis={message.metadata.token_analysis}
                                isOpen={true}
                                onToggle={() => toggleTokens(message.id)}
                              />
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}

                {isLoading && (
                  <div className="bg-gray-50 py-6">
                    <div className="max-w-3xl mx-auto px-4">
                      <div className="flex items-center space-x-2">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-900"></div>
                        <span className="text-gray-600">
                          {isTyping ? 'Assistant is typing...' : 'Searching your collections...'}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
        </div>
      </div>

      {/* Fixed Input Area */}
      <div className="sticky bottom-0 bg-white border-t border-gray-200 px-4 py-4">
        <div className="max-w-3xl mx-auto">
                {/* Referenced message indicator */}
                {referencedMessage && (
                  <div className="mb-3 p-3 bg-blue-10 border border-blue-20 rounded-md">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <LinkIcon className="w-4 h-4 text-blue-60" />
                        <div>
                          <div className="text-sm font-medium text-blue-70">Referencing message:</div>
                          <div className="text-xs text-blue-60 truncate max-w-md">
                            "{referencedMessage.content.substring(0, 80)}..."
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => setReferencedMessage(null)}
                        className="text-blue-50 hover:text-blue-70"
                        title="Clear reference"
                      >
                        ×
                      </button>
                    </div>
                  </div>
                )}

                <form onSubmit={handleSearch} className="flex items-end space-x-3">
                  <div className="flex-1 flex items-center bg-white rounded-md px-4 py-3 border border-gray-300 focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500">
                    <input
                      type="text"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder={referencedMessage ? "Ask a follow-up question..." : "Ask a question about your documents..."}
                      disabled={isLoading}
                      className="flex-1 bg-transparent outline-none text-gray-900 placeholder-gray-400 disabled:opacity-50"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={isLoading || !query.trim()}
                    className="bg-blue-600 text-white rounded-md px-4 py-3 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <PaperAirplaneIcon className="w-5 h-5" />
                  </button>
                </form>
        </div>
      </div>

        {/* New Conversation Modal */}
        {showNewConversationModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
              <h3 className="text-lg font-semibold text-gray-100 mb-4">New Conversation</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-100 mb-1">
                    Conversation Name
                  </label>
                  <input
                    type="text"
                    value={newConversationName}
                    onChange={(e) => setNewConversationName(e.target.value)}
                    placeholder="Enter conversation name..."
                    className="input-field w-full"
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        createNewConversation();
                      } else if (e.key === 'Escape') {
                        setShowNewConversationModal(false);
                        setNewConversationName('');
                      }
                    }}
                  />
                </div>
                <div>
                  <p className="text-sm text-gray-60">
                    Collection: <span className="font-medium">{currentCollectionName}</span>
                  </p>
                </div>
              </div>
              <div className="flex justify-end space-x-3 mt-6">
                <button
                  onClick={() => {
                    setShowNewConversationModal(false);
                    setNewConversationName('');
                  }}
                  className="px-4 py-2 text-gray-60 hover:text-gray-100 border border-gray-30 rounded-md hover:bg-gray-10"
                >
                  Cancel
                </button>
                <button
                  onClick={createNewConversation}
                  disabled={!newConversationName.trim()}
                  className="btn-primary px-4 py-2 disabled:opacity-50"
                >
                  Create
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Source Modal */}
        <SourceModal
          isOpen={sourceModalOpen !== null}
          onClose={() => {
            setSourceModalOpen(null);
            setSourceModalSources([]);
          }}
          sources={sourceModalSources}
        />

      {/* Conversation Summary Modal */}
      {showSummaryModal && conversationSummary && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-2xl mx-4 max-h-[80vh] overflow-y-auto">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-100">
                  Conversation Summary: {conversationSummary.session_name}
                </h3>
                <button
                  onClick={() => {
                    setShowSummaryModal(false);
                    setConversationSummary(null);
                  }}
                  className="text-gray-60 hover:text-gray-100"
                >
                  ×
                </button>
              </div>

              <div className="space-y-4">
                {/* Summary Stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-10 rounded-md">
                  <div className="text-center">
                    <div className="text-lg font-semibold text-gray-100">{conversationSummary.message_count}</div>
                    <div className="text-xs text-gray-60">Total Messages</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-semibold text-gray-100">{conversationSummary.user_messages}</div>
                    <div className="text-xs text-gray-60">Questions</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-semibold text-gray-100">{conversationSummary.total_tokens?.toLocaleString() || 0}</div>
                    <div className="text-xs text-gray-60">Total Tokens</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-semibold text-gray-100">{conversationSummary.cot_usage_count || 0}</div>
                    <div className="text-xs text-gray-60">CoT Reasoning</div>
                  </div>
                </div>

                {/* Summary Type Selector */}
                <div className="flex space-x-2">
                  {['brief', 'detailed', 'key_points'].map((type) => (
                    <button
                      key={type}
                      onClick={() => loadConversationSummary(currentConversation?.id || '', type)}
                      className={`px-3 py-1 text-sm rounded ${
                        conversationSummary.summary_type === type
                          ? 'bg-blue-60 text-white'
                          : 'bg-gray-20 text-gray-70 hover:bg-gray-30'
                      }`}
                      disabled={summaryLoading}
                    >
                      {type.charAt(0).toUpperCase() + type.slice(1).replace('_', ' ')}
                    </button>
                  ))}
                </div>

                {/* Summary Content */}
                <div className="p-4 bg-gray-10 rounded-md">
                  <h4 className="font-medium text-gray-100 mb-2">
                    {conversationSummary.summary_type === 'key_points' ? 'Key Points' : 'Summary'}
                  </h4>
                  <div className="text-sm text-gray-70 whitespace-pre-wrap">
                    {summaryLoading ? (
                      <div className="flex items-center space-x-2">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-60"></div>
                        <span>Generating summary...</span>
                      </div>
                    ) : (
                      conversationSummary.summary
                    )}
                  </div>
                </div>

                {/* Topics */}
                {conversationSummary.topics && conversationSummary.topics.length > 0 && (
                  <div>
                    <h4 className="font-medium text-gray-100 mb-2">Topics Discussed</h4>
                    <div className="flex flex-wrap gap-2">
                      {conversationSummary.topics.map((topic: string, index: number) => (
                        <span
                          key={index}
                          className="px-2 py-1 bg-blue-10 text-blue-70 text-xs rounded-full"
                        >
                          {topic}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Metadata */}
                <div className="text-xs text-gray-50 pt-2 border-t border-gray-20">
                  <div>Created: {new Date(conversationSummary.created_at).toLocaleDateString()}</div>
                  <div>Summary generated: {new Date(conversationSummary.generated_at).toLocaleString()}</div>
                </div>
              </div>

              <div className="flex justify-end mt-6">
                <button
                  onClick={() => {
                    setShowSummaryModal(false);
                    setConversationSummary(null);
                  }}
                  className="px-4 py-2 bg-gray-20 text-gray-70 rounded-md hover:bg-gray-30"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
    </div>
  );
};

export default LightweightSearchInterface;
