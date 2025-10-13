# Frontend Development

The RAG Modulo frontend is built with React 18 and follows modern best practices for component-based development.

## Tech Stack

- **React 18** - Modern React with hooks and concurrent features
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first CSS framework
- **Carbon Design System** - IBM's design language for consistent UI
- **React Router** - Client-side routing
- **Axios** - HTTP client for API communication

## Project Structure

```
frontend/src/
├── components/
│   ├── ui/              # Reusable UI components
│   ├── modals/          # Modal dialogs
│   ├── podcasts/        # Podcast generation features
│   ├── search/          # Search interface components
│   └── ...
├── contexts/            # React contexts for state management
├── services/            # API clients and services
├── pages/               # Page-level components
├── styles/              # Global styles and Tailwind config
└── utils/               # Utility functions
```

## Getting Started

### Prerequisites

- Node.js 16+ and npm
- Backend services running (see [Installation Guide](../../installation.md))

### Local Development

#### Quick Start (Recommended)

```bash
# One-time setup
make local-dev-setup

# Start infrastructure only (Postgres, Milvus, etc.)
make local-dev-infra

# Start frontend development server with hot-reload
make local-dev-frontend
```

The frontend will be available at [http://localhost:3000](http://localhost:3000)

#### Manual Setup

```bash
cd frontend
npm install
npm run dev
```

### Using Docker

```bash
# Build and run with Docker Compose
make build-all
make run-app
```

## Development Guidelines

### Component Development

#### Using Reusable UI Components

The project includes a comprehensive library of reusable UI components. Always use these instead of creating custom implementations:

```tsx
import { Button, Input, Modal, Card } from '@/components/ui';

function MyComponent() {
  return (
    <Card>
      <Input
        label="Name"
        placeholder="Enter name"
        fullWidth
      />
      <Button variant="primary" onClick={handleSubmit}>
        Submit
      </Button>
    </Card>
  );
}
```

See the [UI Components Guide](ui-components.md) for detailed documentation.

#### Component Best Practices

1. **Use TypeScript** - Define proper interfaces for props
2. **Follow naming conventions** - PascalCase for components, camelCase for functions
3. **Keep components focused** - Single responsibility principle
4. **Use hooks effectively** - Leverage React hooks for state and side effects
5. **Implement error boundaries** - Handle errors gracefully
6. **Add accessibility** - Include ARIA labels and keyboard navigation

### Styling Guidelines

#### Tailwind CSS

Use Tailwind utility classes following the Carbon Design System color palette:

```tsx
// Primary colors
<div className="bg-blue-60 text-white">Primary action</div>

// Gray scale
<div className="bg-gray-10 text-gray-100">Subtle background</div>

// Status colors
<div className="bg-green-50 text-white">Success</div>
<div className="bg-red-50 text-white">Error</div>
<div className="bg-yellow-30 text-gray-100">Warning</div>
```

#### Component Classes

Pre-defined component classes are available in `tailwind.css`:

```tsx
<button className="btn-primary">Primary Button</button>
<input className="input-field" />
<div className="card">Card content</div>
```

**Note:** For new components, prefer using the reusable UI components over these utility classes.

### State Management

#### Local State

Use React hooks for component-local state:

```tsx
const [count, setCount] = useState(0);
const [user, setUser] = useState<User | null>(null);
```

#### Context API

Use React Context for shared state across components:

```tsx
import { useNotification } from '../../contexts/NotificationContext';

function MyComponent() {
  const { addNotification } = useNotification();

  const handleSuccess = () => {
    addNotification('success', 'Operation completed!');
  };
}
```

### API Integration

Use the centralized API client:

```tsx
import apiClient from '../../services/apiClient';

// Fetch collections
const collections = await apiClient.getCollections();

// Create collection
const newCollection = await apiClient.createCollection({
  name: 'My Collection',
  is_private: true
});
```

## Code Quality

### Linting

```bash
# Run ESLint
cd frontend
npm run lint

# Auto-fix issues
npm run lint:fix
```

### Type Checking

```bash
# Check TypeScript errors
npx tsc --noEmit
```

### Testing

```bash
# Run tests
npm test

# Run tests with coverage
npm test -- --coverage
```

## Building for Production

```bash
# Create optimized production build
npm run build

# The build output will be in the `build/` directory
```

## Common Development Tasks

### Adding a New Page

1. Create component in `src/pages/`
2. Add route in your routing configuration
3. Import and use reusable UI components
4. Add TypeScript interfaces for props and state

### Creating a New Feature

1. Plan component structure
2. Create reusable components if needed
3. Implement feature using existing UI components
4. Add API integration if needed
5. Write tests
6. Update documentation

### Debugging

#### React DevTools

Install React DevTools browser extension for component inspection and profiling.

#### Network Debugging

1. Open browser DevTools (F12)
2. Go to Network tab
3. Check API requests and responses
4. Verify request/response payloads

#### Console Logging

```tsx
console.log('Component rendered', { props, state });
console.error('Error occurred', error);
```

## Performance Optimization

### Code Splitting

Use React.lazy for route-based code splitting:

```tsx
const Dashboard = React.lazy(() => import('./pages/Dashboard'));

<Suspense fallback={<Loading />}>
  <Dashboard />
</Suspense>
```

### Memoization

Use React.memo and useMemo to prevent unnecessary re-renders:

```tsx
const ExpensiveComponent = React.memo(({ data }) => {
  return <div>{/* render */}</div>;
});

const memoizedValue = useMemo(() =>
  computeExpensiveValue(data),
  [data]
);
```

## Troubleshooting

### Common Issues

#### Module Resolution Errors

```bash
# Clear caches and restart
rm -rf node_modules/.cache
npm run dev
```

#### TypeScript Errors

```bash
# Clean TypeScript cache
rm -f tsconfig.tsbuildinfo
npx tsc --noEmit
```

#### Port Already in Use

```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

## Resources

- [React Documentation](https://react.dev/)
- [TypeScript Documentation](https://www.typescriptlang.org/docs/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Carbon Design System](https://carbondesignsystem.com/)
- [UI Components Guide](ui-components.md)

## Next Steps

- Review the [UI Components Guide](ui-components.md)
- Check out [Development Workflow](../workflow.md)
- Read [Contributing Guidelines](../contributing.md)
