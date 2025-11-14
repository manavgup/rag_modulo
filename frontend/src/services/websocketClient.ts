interface TokenWarning {
  warning_type: string;
  current_tokens: number;
  limit_tokens: number;
  percentage_used: number;
  message: string;
  severity: 'info' | 'warning' | 'critical';
  suggested_action?: string;
}

interface ChainOfThoughtStep {
  step_number: number;
  question: string;
  answer: string;
  sources_used: number;
  reasoning?: string;
}

interface ChainOfThoughtOutput {
  enabled: boolean;
  total_steps: number;
  steps: ChainOfThoughtStep[];
  final_synthesis?: string;
}

interface Citation {
  document_id: string;
  title: string;
  excerpt: string;
  page_number?: number;
  relevance_score: number;
  chunk_id?: string;
}

interface ReasoningStep {
  step_number: number;
  thought: string;
  conclusion: string;
  citations: Citation[];
}

interface StructuredAnswerMetadata {
  source_count?: number;
  confidence_threshold?: number;
  reasoning_depth?: number;
  processing_time_ms?: number;
  [key: string]: unknown; // For extensibility with unknown future fields
}

interface StructuredAnswer {
  answer: string;
  confidence: number;
  citations: Citation[];
  reasoning_steps?: ReasoningStep[];
  format_type: 'standard' | 'cot_reasoning' | 'comparative' | 'summary';
  metadata?: StructuredAnswerMetadata;
}

interface SourceMetadata {
  page_number?: number;
  chunk_id?: string;
  document_id?: string;
  relevance_score?: number;
  [key: string]: unknown; // For extensibility
}

interface Source {
  document_name: string;
  content: string;
  metadata: SourceMetadata;
}

interface ChatMessageMetadata {
  conversation_id?: string;
  session_id?: string;
  collection_id?: string;
  response_time_ms?: number;
  execution_time?: number;
  token_analysis?: {
    query_tokens?: number;
    context_tokens?: number;
    response_tokens?: number;
    system_tokens?: number;
    total_this_turn?: number;
    conversation_total?: number;
  };
  [key: string]: unknown; // For extensibility
}


interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  metadata?: ChatMessageMetadata;
  sources?: Source[];
  token_warning?: TokenWarning;
  cot_output?: ChainOfThoughtOutput;
  structured_answer?: StructuredAnswer;
}

interface ConnectionStatus {
  connected: boolean;
  connecting: boolean;
  error?: string;
}

type MessageHandler = (message: ChatMessage) => void;
type StatusHandler = (status: ConnectionStatus) => void;
type TypingHandler = (isTyping: boolean) => void;

class WebSocketClient {
  private ws: WebSocket | null = null;
  private messageHandlers: Set<MessageHandler> = new Set();
  private statusHandlers: Set<StatusHandler> = new Set();
  private typingHandlers: Set<TypingHandler> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private pingInterval: NodeJS.Timeout | null = null;

  constructor(private url: string) {
    this.connect();
  }

  private connect() {
    try {
      this.notifyStatus({ connected: false, connecting: true });

      // Add auth token to WebSocket connection
      const token = localStorage.getItem('access_token');
      const wsUrl = token ? `${this.url}?token=${token}` : this.url;

      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.notifyStatus({ connected: true, connecting: false });
        this.startPing();
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        this.cleanup();
        this.notifyStatus({ connected: false, connecting: false });

        // Attempt to reconnect unless it was a normal closure
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.notifyStatus({
          connected: false,
          connecting: false,
          error: 'Connection error'
        });
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      this.notifyStatus({
        connected: false,
        connecting: false,
        error: 'Failed to connect'
      });
    }
  }

  private cleanup() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }

  private startPing() {
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000); // Ping every 30 seconds
  }

  private scheduleReconnect() {
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
    this.reconnectAttempts++;

    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);

    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private handleMessage(data: any) {
    switch (data.type) {
      case 'chat_message':
        const message: ChatMessage = {
          id: data.id || Date.now().toString(),
          type: data.sender === 'user' ? 'user' : 'assistant',
          content: data.content,
          timestamp: new Date(data.timestamp || Date.now()),
          metadata: data.metadata,
          sources: data.sources,
          token_warning: data.token_warning,
          cot_output: data.cot_output
        };
        console.log('[WebSocket] Received message data:', {
          ...data,
          sources: data.sources ? `${data.sources.length} sources` : 'no sources',
          token_warning: data.token_warning ? 'has token warning' : 'no token warning',
          cot_output: data.cot_output ? `CoT: ${data.cot_output.enabled ? 'enabled' : 'disabled'}` : 'no CoT'
        });
        this.notifyMessage(message);
        break;

      case 'typing_indicator':
        this.notifyTyping(data.is_typing);
        break;

      case 'error':
        console.error('WebSocket error message:', data.message);
        this.notifyStatus({
          connected: true,
          connecting: false,
          error: data.message
        });
        break;

      case 'pong':
        // Handle ping response
        break;

      case 'connection_established':
        // Connection acknowledgment from server
        console.log('WebSocket connection established');
        break;

      default:
        console.warn('Unknown message type:', data.type);
    }
  }

  private notifyMessage(message: ChatMessage) {
    this.messageHandlers.forEach(handler => {
      try {
        handler(message);
      } catch (error) {
        console.error('Error in message handler:', error);
      }
    });
  }

  private notifyStatus(status: ConnectionStatus) {
    this.statusHandlers.forEach(handler => {
      try {
        handler(status);
      } catch (error) {
        console.error('Error in status handler:', error);
      }
    });
  }

  private notifyTyping(isTyping: boolean) {
    this.typingHandlers.forEach(handler => {
      try {
        handler(isTyping);
      } catch (error) {
        console.error('Error in typing handler:', error);
      }
    });
  }

  // Public methods
  sendMessage(content: string, collectionId: string, metadata?: ChatMessageMetadata, sessionId?: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      const message = {
        type: 'chat_message',
        content,
        collection_id: collectionId,
        session_id: sessionId,
        metadata,
        timestamp: new Date().toISOString()
      };
      this.ws.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not connected');
      throw new Error('Connection not available');
    }
  }

  sendTyping(isTyping: boolean) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'typing_indicator',
        is_typing: isTyping
      }));
    }
  }

  // Event handlers
  onMessage(handler: MessageHandler) {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onStatus(handler: StatusHandler) {
    this.statusHandlers.add(handler);
    return () => this.statusHandlers.delete(handler);
  }

  onTyping(handler: TypingHandler) {
    this.typingHandlers.add(handler);
    return () => this.typingHandlers.delete(handler);
  }

  // Connection management
  disconnect() {
    this.cleanup();
    if (this.ws) {
      this.ws.close(1000, 'User initiated disconnect');
      this.ws = null;
    }
  }

  reconnect() {
    this.disconnect();
    this.reconnectAttempts = 0;
    this.connect();
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// Create singleton instance
const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';
const websocketClient = new WebSocketClient(WS_URL);

export default websocketClient;
export type {
  ChatMessage,
  ConnectionStatus,
  Citation,
  StructuredAnswer,
  ReasoningStep,
  ChatMessageMetadata,
  StructuredAnswerMetadata,
  Source,
  SourceMetadata,
};
