# Components - AI Agent Context

## Overview

The components directory contains all React components for the RAG Modulo frontend. Components are organized by feature/domain for better maintainability.

## Component Organization

```
components/
├── layout/            # App layout components (Sidebar, Header)
├── search/            # Search and chat interface
├── collections/       # Collection management
├── modals/            # Modal dialogs
├── dashboard/         # Analytics dashboard
├── auth/              # Authentication components
├── common/            # Shared/reusable components
├── podcasts/          # Podcast features
├── settings/          # User settings
├── profile/           # User profile
├── errors/            # Error display components
├── help/              # Help and documentation
├── agents/            # Agent management (future)
├── analytics/         # Analytics visualization
└── workflows/         # Workflow management (future)
```

## Key Component Categories

### Layout Components (`layout/`)

#### LightweightSidebar.tsx
**Purpose**: Main navigation sidebar

**Features**:
- Nested menu structure
- Dynamic conversation list (last 10)
- "All chats" modal trigger
- Responsive mobile design
- Auto-collapse on mobile

**Key Patterns**:
```typescript
const [isOpen, setIsOpen] = useState(true);
const [conversations, setConversations] = useState([]);

useEffect(() => {
  loadConversations();
}, []);
```

### Search Components (`search/`)

#### LightweightSearchInterface.tsx
**Purpose**: Main chat and search interface

**Features**:
- Message display with user/assistant roles
- Real-time WebSocket messaging
- Fallback to REST API
- Accordion displays (sources, CoT, tokens)
- Auto-scroll to latest message
- URL parameter support for session loading

**Key State**:
```typescript
const [messages, setMessages] = useState([]);
const [currentQuestion, setCurrentQuestion] = useState('');
const [isStreaming, setIsStreaming] = useState(false);
const [selectedCollection, setSelectedCollection] = useState(null);
const [sessionId, setSessionId] = useState(null);
```

### Collection Components (`collections/`)

#### LightweightCollectionDetail.tsx
**Purpose**: Collection details and file management

**Features**:
- Collection metadata display
- File list with status
- Upload/download/delete operations
- Drag-and-drop file upload
- Status indicators (CREATED, PROCESSING, COMPLETED, FAILED)

**API Integration**:
```typescript
const uploadFile = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);

  try {
    await apiClient.uploadDocument(collectionId, formData);
    showNotification('success', 'File uploaded successfully');
    await refreshFiles();
  } catch (error) {
    showNotification('error', 'Upload failed');
  }
};
```

### Modal Components (`modals/`)

#### LightweightCreateCollectionModal.tsx
**Purpose**: Create new collection

**Features**:
- Collection name input
- Privacy toggle
- Validation
- Success/error handling

#### AllChatsModal.tsx
**Purpose**: Browse all conversations

**Features**:
- Search/filter conversations
- Date formatting
- Conversation selection
- Navigate to conversation

### Dashboard Components (`dashboard/`)

#### LightweightDashboard.tsx
**Purpose**: System analytics display

**Features**:
- Statistics cards (collections, users, files, searches)
- Recent activity timeline
- Real-time data updates
- Responsive grid layout

**Data Fetching**:
```typescript
useEffect(() => {
  const fetchStats = async () => {
    try {
      const stats = await apiClient.getDashboardStats();
      const activity = await apiClient.getRecentActivity();
      setStats(stats);
      setActivity(activity);
    } catch (error) {
      showNotification('error', 'Failed to load dashboard');
    }
  };

  fetchStats();
}, []);
```

### Common Components (`common/`)

#### LoadingSpinner.tsx
Reusable loading indicator

#### Button.tsx
Styled button component with variants

#### Card.tsx
Container component for content sections

#### Input.tsx
Form input with validation styling

## Component Patterns

### Standard Component Structure

```typescript
import React, { useState, useEffect } from 'react';
import { apiClient } from '../../services/apiClient';
import { useNotification } from '../../contexts/NotificationContext';

interface ComponentProps {
  id: string;
  onUpdate?: (data: any) => void;
}

export const MyComponent: React.FC<ComponentProps> = ({ id, onUpdate }) => {
  // 1. Hooks
  const { showNotification } = useNotification();

  // 2. State
  const [data, setData] = useState<DataType | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 3. Effects
  useEffect(() => {
    loadData();
  }, [id]);

  // 4. Handlers
  const loadData = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await apiClient.getData(id);
      setData(result);
    } catch (err) {
      const message = err.response?.data?.detail || 'Failed to load data';
      setError(message);
      showNotification('error', message);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (newData: Partial<DataType>) => {
    try {
      const updated = await apiClient.updateData(id, newData);
      setData(updated);
      onUpdate?.(updated);
      showNotification('success', 'Updated successfully');
    } catch (err) {
      showNotification('error', 'Update failed');
    }
  };

  // 5. Render
  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;
  if (!data) return null;

  return (
    <div className="p-4 bg-white rounded shadow">
      <h2 className="text-xl font-bold mb-4">{data.title}</h2>
      <div className="space-y-2">
        {/* Component content */}
      </div>
      <button
        onClick={() => handleUpdate({ status: 'updated' })}
        className="mt-4 bg-blue-500 text-white px-4 py-2 rounded"
      >
        Update
      </button>
    </div>
  );
};
```

### Form Handling Pattern

```typescript
const [formData, setFormData] = useState({
  name: '',
  email: '',
  isPrivate: false
});

const [errors, setErrors] = useState<Record<string, string>>({});

const handleChange = (field: string, value: any) => {
  setFormData(prev => ({ ...prev, [field]: value }));
  // Clear error for this field
  setErrors(prev => ({ ...prev, [field]: '' }));
};

const validate = (): boolean => {
  const newErrors: Record<string, string> = {};

  if (!formData.name) newErrors.name = 'Name is required';
  if (!formData.email) newErrors.email = 'Email is required';

  setErrors(newErrors);
  return Object.keys(newErrors).length === 0;
};

const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();

  if (!validate()) return;

  try {
    await apiClient.createItem(formData);
    showNotification('success', 'Created successfully');
  } catch (error) {
    showNotification('error', 'Creation failed');
  }
};
```

### List Display Pattern

```typescript
const MyList: React.FC<{ items: Item[] }> = ({ items }) => {
  if (items.length === 0) {
    return (
      <div className="text-center text-gray-500 py-8">
        No items found
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {items.map(item => (
        <div key={item.id} className="bg-white p-4 rounded shadow hover:shadow-lg transition">
          <h3 className="font-semibold">{item.name}</h3>
          <p className="text-gray-600 text-sm">{item.description}</p>
        </div>
      ))}
    </div>
  );
};
```

### Conditional Rendering Pattern

```typescript
return (
  <div>
    {loading && <LoadingSpinner />}

    {error && <ErrorMessage message={error} />}

    {!loading && !error && data && (
      <div>
        <DataDisplay data={data} />
      </div>
    )}

    {!loading && !error && !data && (
      <div className="text-center text-gray-500">
        No data available
      </div>
    )}
  </div>
);
```

## Tailwind CSS Patterns

### Layout Patterns

```tsx
// Flex column with full height
<div className="flex flex-col h-screen">
  <header className="flex-shrink-0">Header</header>
  <main className="flex-1 overflow-auto">Content</main>
  <footer className="flex-shrink-0">Footer</footer>
</div>

// Centered content
<div className="flex items-center justify-center min-h-screen">
  <div className="max-w-md w-full">Content</div>
</div>

// Grid layout
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {items.map(item => <Card key={item.id} {...item} />)}
</div>
```

### Interactive Elements

```tsx
// Button variants
<button className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded transition">
  Primary
</button>

<button className="border border-gray-300 hover:bg-gray-50 px-4 py-2 rounded transition">
  Secondary
</button>

// Input with focus state
<input
  type="text"
  className="
    border border-gray-300 rounded px-3 py-2 w-full
    focus:outline-none focus:ring-2 focus:ring-blue-500
    transition
  "
/>

// Card with hover
<div className="
  bg-white rounded shadow
  hover:shadow-lg
  transition-shadow duration-200
  cursor-pointer
">
  Content
</div>
```

## Best Practices

### 1. Component Naming
- Use PascalCase: `MyComponent.tsx`
- Descriptive names: `UserProfileCard` not `Card1`
- Prefix with "Lightweight" for new Tailwind components

### 2. File Organization
- One component per file
- Group related components in directories
- Use `index.ts` for clean imports:

```typescript
// components/collections/index.ts
export { LightweightCollectionDetail } from './LightweightCollectionDetail';
export { LightweightCollectionList } from './LightweightCollectionList';
```

### 3. Props Interface
```typescript
// Always define interface for props
interface Props {
  // Required props first
  id: string;
  title: string;

  // Optional props with default values
  variant?: 'primary' | 'secondary';
  onUpdate?: (data: any) => void;

  // Children if needed
  children?: React.ReactNode;
}

// Use destructuring with defaults
const MyComponent: React.FC<Props> = ({
  id,
  title,
  variant = 'primary',
  onUpdate,
  children
}) => {
  // ...
};
```

### 4. Error Boundaries
Wrap components that might fail:

```typescript
import { ErrorBoundary } from 'react-error-boundary';

<ErrorBoundary fallback={<ErrorMessage />}>
  <RiskyComponent />
</ErrorBoundary>
```

### 5. Avoid Unnecessary Re-renders

```typescript
// Memoize callbacks
const handleClick = useCallback(() => {
  doSomething(id);
}, [id]);

// Memoize expensive computations
const sortedItems = useMemo(() => {
  return items.sort((a, b) => a.name.localeCompare(b.name));
}, [items]);

// Memoize components
const MemoizedComponent = React.memo(MyComponent);
```

## Testing Components

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MyComponent } from './MyComponent';

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent title="Test" />);
    expect(screen.getByText('Test')).toBeInTheDocument();
  });

  it('handles user interaction', async () => {
    const handleClick = jest.fn();
    render(<MyComponent onClick={handleClick} />);

    fireEvent.click(screen.getByRole('button'));
    await waitFor(() => {
      expect(handleClick).toHaveBeenCalled();
    });
  });

  it('displays loading state', () => {
    render(<MyComponent loading={true} />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });
});
```

## Component Communication

### Parent to Child
Use props:

```typescript
<ChildComponent data={parentData} onUpdate={handleUpdate} />
```

### Child to Parent
Use callback props:

```typescript
// Parent
const handleUpdate = (newData) => {
  setData(newData);
};

<ChildComponent onUpdate={handleUpdate} />

// Child
<button onClick={() => props.onUpdate(newData)}>Update</button>
```

### Sibling to Sibling
Lift state to parent or use Context:

```typescript
// Via parent
const Parent = () => {
  const [sharedData, setSharedData] = useState(null);

  return (
    <>
      <Child1 data={sharedData} />
      <Child2 onUpdate={setSharedData} />
    </>
  );
};
```

## Related Documentation

- Frontend Overview: `../AGENTS.md`
- Backend API: `../../backend/AGENTS.md`
- Services: `../services/apiClient.ts`
