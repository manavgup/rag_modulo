# Reusable UI Components

This directory contains reusable UI components that provide a consistent look and feel across the RAG Modulo frontend application. All components follow Carbon Design System principles with Tailwind CSS styling.

## Components

### Button

A versatile button component with multiple variants, sizes, and states.

**Props:**
- `variant`: 'primary' | 'secondary' | 'ghost' | 'danger' (default: 'primary')
- `size`: 'sm' | 'md' | 'lg' (default: 'md')
- `loading`: boolean (shows loading spinner)
- `icon`: ReactNode (icon element)
- `iconPosition`: 'left' | 'right' (default: 'left')
- `fullWidth`: boolean (makes button full width)
- `disabled`: boolean

**Example:**
```tsx
import { Button } from '@/components/ui';
import { PlusIcon } from '@heroicons/react/24/outline';

<Button variant="primary" size="md" icon={<PlusIcon className="w-5 h-5" />}>
  Create New
</Button>

<Button variant="secondary" loading>
  Saving...
</Button>

<Button variant="danger" fullWidth onClick={handleDelete}>
  Delete
</Button>
```

### Input

A text input component with label, error, and help text support.

**Props:**
- `label`: string (label text)
- `error`: string (error message)
- `helpText`: string (help text below input)
- `icon`: ReactNode (icon on left side)
- `fullWidth`: boolean
- All standard HTML input attributes

**Example:**
```tsx
import { Input } from '@/components/ui';
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline';

<Input
  label="Search"
  placeholder="Search collections..."
  icon={<MagnifyingGlassIcon className="w-5 h-5 text-gray-60" />}
  fullWidth
/>

<Input
  label="Email"
  type="email"
  error="Invalid email address"
  fullWidth
/>
```

### TextArea

A multi-line text input component.

**Props:**
- `label`: string
- `error`: string
- `helpText`: string
- `fullWidth`: boolean
- All standard HTML textarea attributes

**Example:**
```tsx
import { TextArea } from '@/components/ui';

<TextArea
  label="Description"
  placeholder="Enter description..."
  rows={4}
  fullWidth
/>
```

### Select

A dropdown select component.

**Props:**
- `label`: string
- `error`: string
- `helpText`: string
- `options`: SelectOption[] (array of {value, label})
- `placeholder`: string
- `fullWidth`: boolean
- All standard HTML select attributes

**Example:**
```tsx
import { Select } from '@/components/ui';

const options = [
  { value: 'public', label: 'Public' },
  { value: 'private', label: 'Private' },
];

<Select
  label="Visibility"
  options={options}
  placeholder="Select visibility..."
  fullWidth
/>
```

### Modal

A reusable modal/dialog component.

**Props:**
- `isOpen`: boolean (controls visibility)
- `onClose`: () => void (close handler)
- `title`: string (modal title)
- `subtitle`: string (modal subtitle)
- `children`: ReactNode (modal content)
- `footer`: ReactNode (footer content, usually buttons)
- `size`: 'sm' | 'md' | 'lg' | 'xl' (default: 'md')
- `showCloseButton`: boolean (default: true)

**Example:**
```tsx
import { Modal, Button } from '@/components/ui';

<Modal
  isOpen={isOpen}
  onClose={() => setIsOpen(false)}
  title="Create Collection"
  subtitle="Enter collection details"
  footer={
    <>
      <Button variant="secondary" onClick={() => setIsOpen(false)}>
        Cancel
      </Button>
      <Button variant="primary" onClick={handleSubmit}>
        Create
      </Button>
    </>
  }
>
  {/* Modal content */}
</Modal>
```

### Card

A container component for grouping related content.

**Props:**
- `children`: ReactNode
- `padding`: 'none' | 'sm' | 'md' | 'lg' (default: 'md')
- `onClick`: () => void (makes card clickable)
- `hoverable`: boolean (adds hover effect)
- `className`: string

**Example:**
```tsx
import { Card } from '@/components/ui';

<Card padding="lg" hoverable>
  <h3>Collection Name</h3>
  <p>Description...</p>
</Card>

<Card padding="none" onClick={handleClick}>
  <img src="..." />
  <div className="p-4">Content</div>
</Card>
```

### Badge

A small label/tag component for status or categories.

**Props:**
- `children`: ReactNode
- `variant`: 'default' | 'success' | 'warning' | 'error' | 'info' (default: 'default')
- `size`: 'sm' | 'md' | 'lg' (default: 'md')
- `className`: string

**Example:**
```tsx
import { Badge } from '@/components/ui';

<Badge variant="success">Active</Badge>
<Badge variant="warning">Pending</Badge>
<Badge variant="error">Failed</Badge>
<Badge variant="info" size="sm">New</Badge>
```

### FileUpload

A file upload component with drag & drop support.

**Props:**
- `onFilesChange`: (files: UploadedFile[]) => void
- `accept`: string (file types, default: '.pdf,.docx,.txt,.md')
- `multiple`: boolean (default: true)
- `maxSize`: number (max file size in MB, default: 100)
- `label`: string
- `helpText`: string

**Example:**
```tsx
import { FileUpload } from '@/components/ui';

<FileUpload
  label="Upload Documents"
  onFilesChange={(files) => setFiles(files)}
  accept=".pdf,.docx"
  multiple
  maxSize={100}
/>
```

## Usage Guidelines

### Importing Components

```tsx
// Import individual components
import { Button, Input, Modal } from '@/components/ui';

// Or import specific component
import Button from '@/components/ui/Button';
```

### Consistent Styling

All components use Tailwind CSS classes based on the Carbon Design System color palette:
- **Primary Blue**: `blue-60`, `blue-70`
- **Gray Scale**: `gray-10` through `gray-100`
- **Status Colors**: `green-50`, `yellow-30`, `red-50`

### Accessibility

All components include:
- Proper ARIA labels
- Keyboard navigation support
- Focus states
- Screen reader support

### Best Practices

1. **Use semantic variants**: Choose button variants that match their purpose (primary for main actions, secondary for alternatives, danger for destructive actions)

2. **Provide labels**: Always include labels for form inputs to improve accessibility

3. **Show loading states**: Use the `loading` prop on buttons during async operations

4. **Handle errors**: Display error messages using the `error` prop on form components

5. **Be consistent**: Use the same component variants throughout your feature for consistency

## Contributing

When adding new components:
1. Follow the existing patterns and prop naming conventions
2. Support all relevant HTML attributes via spread props
3. Use TypeScript for type safety
4. Include proper documentation in this README
5. Export the component and its types from `index.ts`
