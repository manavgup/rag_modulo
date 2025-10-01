import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { useAuth } from './AuthContext';
import { useNotification } from './NotificationContext';

interface WebSocketMessage {
  type: string;
  payload: any;
  timestamp: Date;
}

interface WebSocketContextType {
  isConnected: boolean;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  lastMessage: WebSocketMessage | null;
  sendMessage: (type: string, payload: any) => void;
  subscribe: (eventType: string, callback: (data: any) => void) => () => void;
  reconnect: () => void;
  metrics: {
    messagesReceived: number;
    messagesSent: number;
    connectionUptime: number;
    reconnectAttempts: number;
  };
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

interface WebSocketProviderProps {
  children: React.ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const { user } = useAuth();
  const { addNotification } = useNotification();

  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<WebSocketContextType['connectionStatus']>('disconnected');
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [metrics, setMetrics] = useState({
    messagesReceived: 0,
    messagesSent: 0,
    connectionUptime: 0,
    reconnectAttempts: 0,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const subscribersRef = useRef<Map<string, Set<(data: any) => void>>>(new Map());
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const connectionStartRef = useRef<Date | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // WebSocket URL configuration
  const getWebSocketUrl = useCallback(() => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = process.env.REACT_APP_WS_URL || `${wsProtocol}//${window.location.hostname}:8000`;
    return `${wsHost}/ws?token=${user?.token || ''}`;
  }, [user]);

  // Initialize WebSocket connection
  const connect = useCallback(() => {
    // Disable WebSocket connection until backend is ready
    const WEBSOCKET_ENABLED = process.env.REACT_APP_WEBSOCKET_ENABLED === 'true';
    if (!WEBSOCKET_ENABLED || !user || wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setConnectionStatus('connecting');
    const wsUrl = getWebSocketUrl();

    try {
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setConnectionStatus('connected');
        connectionStartRef.current = new Date();
        setMetrics(prev => ({ ...prev, reconnectAttempts: 0 }));

        // Start ping interval to keep connection alive
        pingIntervalRef.current = setInterval(() => {
          sendMessage('ping', {});
        }, 30000); // Ping every 30 seconds

        // Notify user of successful connection
        if (metrics.reconnectAttempts > 0) {
          addNotification('success', 'Reconnected', 'WebSocket connection restored');
        }
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          message.timestamp = new Date();

          setLastMessage(message);
          setMetrics(prev => ({ ...prev, messagesReceived: prev.messagesReceived + 1 }));

          // Handle ping/pong
          if (message.type === 'pong') {
            return;
          }

          // Notify subscribers
          const subscribers = subscribersRef.current.get(message.type);
          if (subscribers) {
            subscribers.forEach(callback => {
              try {
                callback(message.payload);
              } catch (error) {
                console.error('Subscriber callback error:', error);
              }
            });
          }

          // Handle system messages
          handleSystemMessage(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('error');
        addNotification('error', 'Connection Error', 'WebSocket connection failed');
      };

      wsRef.current.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setIsConnected(false);
        setConnectionStatus('disconnected');

        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
        }

        // Update connection uptime
        if (connectionStartRef.current) {
          const uptime = Date.now() - connectionStartRef.current.getTime();
          setMetrics(prev => ({ ...prev, connectionUptime: prev.connectionUptime + uptime }));
          connectionStartRef.current = null;
        }

        // Auto-reconnect logic
        if (!event.wasClean && user) {
          const reconnectDelay = Math.min(1000 * Math.pow(2, metrics.reconnectAttempts), 30000);
          setMetrics(prev => ({ ...prev, reconnectAttempts: prev.reconnectAttempts + 1 }));

          reconnectTimeoutRef.current = setTimeout(() => {
            console.log(`Attempting to reconnect... (attempt ${metrics.reconnectAttempts + 1})`);
            connect();
          }, reconnectDelay);
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionStatus('error');
    }
  }, [user, getWebSocketUrl, metrics.reconnectAttempts, addNotification]);

  // Send message through WebSocket
  const sendMessage = useCallback((type: string, payload: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const message = JSON.stringify({ type, payload, timestamp: new Date() });
      wsRef.current.send(message);
      setMetrics(prev => ({ ...prev, messagesSent: prev.messagesSent + 1 }));
    } else {
      console.warn('WebSocket is not connected. Message not sent:', type);
    }
  }, []);

  // Subscribe to specific message types
  const subscribe = useCallback((eventType: string, callback: (data: any) => void) => {
    if (!subscribersRef.current.has(eventType)) {
      subscribersRef.current.set(eventType, new Set());
    }
    subscribersRef.current.get(eventType)!.add(callback);

    // Return unsubscribe function
    return () => {
      const subscribers = subscribersRef.current.get(eventType);
      if (subscribers) {
        subscribers.delete(callback);
        if (subscribers.size === 0) {
          subscribersRef.current.delete(eventType);
        }
      }
    };
  }, []);

  // Handle system messages
  const handleSystemMessage = (message: WebSocketMessage) => {
    switch (message.type) {
      case 'notification':
        addNotification(
          message.payload.kind || 'info',
          message.payload.title || 'Notification',
          message.payload.message
        );
        break;

      case 'collection.status':
        // Handle collection status updates
        console.log('Collection status update:', message.payload);
        break;

      case 'search.progress':
        // Handle search progress updates
        console.log('Search progress:', message.payload);
        break;

      case 'chat.message':
        // Handle real-time chat messages
        console.log('New chat message:', message.payload);
        break;

      case 'system.broadcast':
        // Handle system-wide broadcasts
        if (message.payload.important) {
          addNotification('info', 'System Message', message.payload.message);
        }
        break;

      default:
        // Unknown message type
        console.log('Unknown WebSocket message type:', message.type);
    }
  };

  // Manual reconnect
  const reconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    setMetrics(prev => ({ ...prev, reconnectAttempts: 0 }));
    connect();
  }, [connect]);

  // Initialize connection when user is available
  useEffect(() => {
    if (user) {
      connect();
    }

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [user, connect]);

  // Update connection uptime periodically
  useEffect(() => {
    const interval = setInterval(() => {
      if (connectionStartRef.current && isConnected) {
        const uptime = Date.now() - connectionStartRef.current.getTime();
        setMetrics(prev => ({ ...prev, connectionUptime: uptime }));
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [isConnected]);

  const value: WebSocketContextType = {
    isConnected,
    connectionStatus,
    lastMessage,
    sendMessage,
    subscribe,
    reconnect,
    metrics,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};

// Helper hook for common subscriptions
export const useWebSocketSubscription = (
  eventType: string,
  callback: (data: any) => void,
  deps: React.DependencyList = []
) => {
  const { subscribe } = useWebSocket();

  useEffect(() => {
    const unsubscribe = subscribe(eventType, callback);
    return unsubscribe;
  }, [eventType, subscribe, ...deps]);
};

// Helper hook for collection status updates
export const useCollectionStatus = (collectionId?: string) => {
  const [status, setStatus] = useState<any>(null);

  useWebSocketSubscription('collection.status', (data) => {
    if (!collectionId || data.collectionId === collectionId) {
      setStatus(data);
    }
  }, [collectionId]);

  return status;
};

// Helper hook for real-time chat messages
export const useChatMessages = (sessionId?: string) => {
  const [messages, setMessages] = useState<any[]>([]);

  useWebSocketSubscription('chat.message', (data) => {
    if (!sessionId || data.sessionId === sessionId) {
      setMessages(prev => [...prev, data]);
    }
  }, [sessionId]);

  return messages;
};

// Helper hook for search progress
export const useSearchProgress = (searchId?: string) => {
  const [progress, setProgress] = useState<any>(null);

  useWebSocketSubscription('search.progress', (data) => {
    if (!searchId || data.searchId === searchId) {
      setProgress(data);
    }
  }, [searchId]);

  return progress;
};
