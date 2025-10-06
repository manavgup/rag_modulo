# Frontend - AI Agent Context

## Overview

The frontend is a React 18 application providing the user interface for RAG Modulo. Built with Tailwind CSS for styling, it features a WhatsApp-style chat interface, real-time WebSocket communication, and comprehensive document management capabilities.

## Technology Stack

- **React 18**: Modern React with hooks and concurrent features
- **Tailwind CSS**: Utility-first CSS framework (replaces IBM Carbon Design)
- **React Router v6**: Client-side routing
- **Axios**: HTTP client for API communication
- **WebSocket**: Real-time messaging support
- **Heroicons**: Icon library
- **Headless UI**: Unstyled accessible components

## Directory Structure

```
frontend/
├── src/
│   ├── components/        # React components
│   │   ├── layout/        # Layout components (Sidebar, Header)
│   │   ├── search/        # Search interface
│   │   ├── collections/   # Collection management
│   │   ├── modals/        # Modal dialogs
│   │   ├── dashboard/     # Analytics dashboard
│   │   ├── auth/          # Authentication components
│   │   ├── common/        # Shared components
│   │   └── ...
│   ├── services/          # API & WebSocket clients
│   │   ├── apiClient.ts   # REST API client
│   │   └── websocketClient.ts  # WebSocket client
│   ├── contexts/          # React Context providers
│   │   ├── AuthContext.tsx     # Authentication state
│   │   └── NotificationContext.tsx  # Notifications
│   ├── styles/            # Global styles
│   ├── App.tsx            # Main application component
│   └── index.tsx          # Application entry point
├── public/                # Static assets
├── Dockerfile.frontend    # Production Docker image
├── Dockerfile.dev         # Development Docker image
└── package.json           # Dependencies and scripts
```

## Key Features

### 1. Chat Interface
**Location**: `src/components/search/LightweightSearchInterface.tsx`
- WhatsApp-style conversation UI
- Real-time message streaming via WebSocket
- Fallback to REST API if WebSocket fails
- Message history with user/assistant roles
- Accordion displays for sources, CoT steps, token usage

### 2. Collection Management
**Location**: `src/components/collections/`
- Create, view, update, delete collections
- Upload documents (drag-and-drop support)
- Download/delete individual files
- Collection status tracking (CREATED, PROCESSING, COMPLETED, FAILED)
- File format validation

### 3. Dynamic Navigation
**Location**: `src/components/layout/LightweightSidebar.tsx`
- Nested menu structure
- Last 10 conversations in sidebar
- "All chats" modal for browsing all conversations
- LLM-generated conversation names
- Responsive mobile design with auto-close

### 4. Dashboard Analytics
**Location**: `src/components/dashboard/LightweightDashboard.tsx`
- System-wide statistics (collections, users, files, searches)
- Recent activity timeline
- Real-time data updates
- Responsive grid layout

### 5. Real-time Communication
**Location**: `src/services/websocketClient.ts`
- WebSocket connection management
- Automatic reconnection
- Message queueing during disconnection
- Event-based messaging

## Component Architecture

### Component Structure

```typescript
import React, { useState, useEffect } from 'react';
import { apiClient } from '../../services/apiClient';
import { useNotification } from '../../contexts/NotificationContext';

interface MyComponentProps {
  collectionId: string;
  onUpdate?: () => void;
}

export const MyComponent: React.FC<MyComponentProps> = ({ collectionId, onUpdate }) => {
  const [data, setData] = useState<DataType[]>([]);
  const [loading, setLoading] = useState(false);
  const { showNotification } = useNotification();

  useEffect(() => {
    loadData();
  }, [collectionId]);

  const loadData = async () => {
    try {
      setLoading(true);
      const result = await apiClient.getData(collectionId);
      setData(result);
    } catch (error) {
      showNotification('error', 'Failed to load data');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4">
      {loading ? (
        <div>Loading...</div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {data.map(item => (
            <div key={item.id} className="bg-white p-4 rounded shadow">
              {item.name}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
```

### State Management Pattern

1. **Local State**: `useState` for component-specific state
2. **Context**: React Context for global state (auth, notifications)
3. **URL State**: Query parameters for shareable state

### API Integration Pattern

```typescript
// In component
import { apiClient } from '../../services/apiClient';

const MyComponent = () => {
  const [data, setData] = useState<DataType | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const result = await apiClient.getCollections();
        setData(result);
      } catch (error) {
        console.error('API Error:', error);
      }
    };
    fetchData();
  }, []);

  // ...
};
```

## Key Services

### API Client (`services/apiClient.ts`)

```typescript
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const apiClient = {
  // Collections
  getCollections: () => axios.get(`${API_BASE_URL}/api/v1/collections`),
  createCollection: (data) => axios.post(`${API_BASE_URL}/api/v1/collections`, data),

  // Search
  search: (input) => axios.post(`${API_BASE_URL}/api/v1/search`, input),

  // Conversations
  getConversations: () => axios.get(`${API_BASE_URL}/api/v1/conversations`),
  createSession: (data) => axios.post(`${API_BASE_URL}/api/v1/conversations`, data),

  // Dashboard
  getDashboardStats: () => axios.get(`${API_BASE_URL}/api/v1/dashboard/stats`),
  getRecentActivity: () => axios.get(`${API_BASE_URL}/api/v1/dashboard/activity`),
};
```

### WebSocket Client (`services/websocketClient.ts`)

```typescript
class WebSocketClient {
  private ws: WebSocket | null = null;
  private messageHandlers: Map<string, (data: any) => void> = new Map();

  connect(url: string) {
    this.ws = new WebSocket(url);

    this.ws.onopen = () => console.log('WebSocket connected');
    this.ws.onmessage = (event) => this.handleMessage(event);
    this.ws.onerror = (error) => console.error('WebSocket error:', error);
    this.ws.onclose = () => this.reconnect();
  }

  send(message: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  on(event: string, handler: (data: any) => void) {
    this.messageHandlers.set(event, handler);
  }

  private handleMessage(event: MessageEvent) {
    const data = JSON.parse(event.data);
    const handler = this.messageHandlers.get(data.type);
    if (handler) handler(data);
  }
}
```

## Styling with Tailwind CSS

### Utility Classes

```tsx
// Layout
<div className="flex flex-col h-screen">
  <header className="bg-blue-600 text-white p-4">Header</header>
  <main className="flex-1 overflow-auto p-4">Content</main>
</div>

// Grid
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {items.map(item => (
    <div key={item.id} className="bg-white rounded-lg shadow p-4">
      {item.name}
    </div>
  ))}
</div>

// Buttons
<button className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded transition">
  Click Me
</button>

// Forms
<input
  type="text"
  className="border border-gray-300 rounded px-3 py-2 w-full focus:outline-none focus:ring-2 focus:ring-blue-500"
  placeholder="Enter text"
/>
```

### Responsive Design

```tsx
// Mobile-first approach
<div className="
  w-full             // Full width on mobile
  md:w-1/2           // Half width on tablet
  lg:w-1/3           // Third width on desktop
  p-4                // Padding on all sizes
  md:p-6             // More padding on tablet+
">
  Content
</div>
```

## Common Patterns

### Error Handling

```typescript
import { useNotification } from '../../contexts/NotificationContext';

const MyComponent = () => {
  const { showNotification } = useNotification();

  const handleAction = async () => {
    try {
      await apiClient.performAction();
      showNotification('success', 'Action completed successfully');
    } catch (error) {
      showNotification('error', error.response?.data?.detail || 'Action failed');
      console.error(error);
    }
  };
};
```

### Loading States

```typescript
const [loading, setLoading] = useState(false);

const fetchData = async () => {
  setLoading(true);
  try {
    const data = await apiClient.getData();
    setData(data);
  } finally {
    setLoading(false);
  }
};

return loading ? <LoadingSpinner /> : <DataDisplay data={data} />;
```

### Modal Pattern

```typescript
const [isOpen, setIsOpen] = useState(false);

return (
  <>
    <button onClick={() => setIsOpen(true)}>Open Modal</button>

    {isOpen && (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
        <div className="bg-white rounded-lg p-6 max-w-md w-full">
          <h2 className="text-xl font-bold mb-4">Modal Title</h2>
          <div>Modal content</div>
          <button onClick={() => setIsOpen(false)}>Close</button>
        </div>
      </div>
    )}
  </>
);
```

## Development Commands

```bash
# Development with hot-reload
npm run dev

# Production build
npm run build

# Run tests
npm test

# Dependency management
npm outdated        # Check outdated packages
npm update          # Update packages
npm audit           # Security audit
npm audit fix       # Fix vulnerabilities
```

## Environment Variables

Create `.env.local` for local development:

```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
REACT_APP_ENVIRONMENT=development
```

## Deployment

### Docker Production Build

```bash
# Build production image
docker build -f Dockerfile.frontend -t rag-modulo-frontend .

# Run container
docker run -p 3000:80 rag-modulo-frontend
```

### Environment-Specific Builds

- Development: `Dockerfile.dev` (hot-reload, source maps)
- Production: `Dockerfile.frontend` (optimized, minified)

## Best Practices

### 1. Component Organization
- One component per file
- Group related components in directories
- Use `index.ts` for clean imports

### 2. TypeScript Usage
```typescript
// Define interfaces for props
interface Props {
  title: string;
  count?: number;
  onUpdate: (id: string) => void;
}

// Use type annotations
const MyComponent: React.FC<Props> = ({ title, count = 0, onUpdate }) => {
  // ...
};
```

### 3. Avoid Prop Drilling
Use Context for deeply nested data:

```typescript
// Create context
const DataContext = React.createContext<DataType | null>(null);

// Provider
<DataContext.Provider value={data}>
  <NestedComponents />
</DataContext.Provider>

// Consumer (in deeply nested component)
const data = useContext(DataContext);
```

### 4. Memoization for Performance

```typescript
import { useMemo, useCallback } from 'react';

// Memoize expensive calculations
const expensiveValue = useMemo(() => {
  return computeExpensiveValue(data);
}, [data]);

// Memoize callbacks
const handleClick = useCallback(() => {
  doSomething(id);
}, [id]);
```

## Testing

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import MyComponent from './MyComponent';

test('renders component', () => {
  render(<MyComponent title="Test" />);
  expect(screen.getByText('Test')).toBeInTheDocument();
});

test('handles click', () => {
  const handleClick = jest.fn();
  render(<MyComponent onClick={handleClick} />);

  fireEvent.click(screen.getByRole('button'));
  expect(handleClick).toHaveBeenCalled();
});
```

## Related Documentation

- Components: `src/components/AGENTS.md`
- Backend API: `../backend/AGENTS.md`
