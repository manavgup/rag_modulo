# Reusable UI Components

The RAG Modulo frontend provides a comprehensive library of reusable UI components that establish a consistent design language across the application. All components follow Carbon Design System principles with Tailwind CSS styling.

## Overview

The UI component library is located in `frontend/src/components/ui/` and includes:

- **Button** - Versatile button with multiple variants
- **Input** - Text input with label and validation
- **TextArea** - Multi-line text input
- **Select** - Dropdown select component
- **Modal** - Reusable modal/dialog
- **Card** - Container component
- **Badge** - Status labels and tags
- **FileUpload** - Drag & drop file upload

## Installation

Components are automatically available in the project. Simply import what you need:

```tsx
import { Button, Input, Modal, Card } from '@/components/ui';
```

## Components

### Button

A versatile button component with multiple variants, sizes, and states.

#### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `variant` | `'primary'` \| `'secondary'` \| `'ghost'` \| `'danger'` | `'primary'` | Button style variant |
| `size` | `'sm'` \| `'md'` \| `'lg'` | `'md'` | Button size |
| `loading` | `boolean` | `false` | Shows loading spinner |
| `icon` | `ReactNode` | - | Icon element |
| `iconPosition` | `'left'` \| `'right'` | `'left'` | Icon position |
| `fullWidth` | `boolean` | `false` | Makes button full width |
| `disabled` | `boolean` | `false` | Disables the button |

#### Examples

```tsx
import { Button } from '@/components/ui';
import { PlusIcon } from '@heroicons/react/24/outline';

// Primary button with icon
<Button variant="primary" icon={<PlusIcon className="w-5 h-5" />}>
  Create New
</Button>

// Loading state
<Button variant="secondary" loading>
  Saving...
</Button>

// Danger button with full width
<Button variant="danger" fullWidth onClick={handleDelete}>
  Delete
</Button>

// Ghost button (minimal style)
<Button variant="ghost" size="sm">
  Cancel
</Button>
```

### Input

A text input component with label, error, and help text support.

#### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `label` | `string` | - | Label text |
| `error` | `string` | - | Error message |
| `helpText` | `string` | - | Help text below input |
| `icon` | `ReactNode` | - | Icon on left side |
| `fullWidth` | `boolean` | `false` | Makes input full width |

Plus all standard HTML input attributes.

#### Examples

```tsx
import { Input } from '@/components/ui';
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline';

// Search input with icon
<Input
  label="Search"
  placeholder="Search collections..."
  icon={<MagnifyingGlassIcon className="w-5 h-5 text-gray-60" />}
  fullWidth
/>

// Input with validation error
<Input
  label="Email"
  type="email"
  error="Invalid email address"
  fullWidth
/>

// Input with help text
<Input
  label="Username"
  helpText="Choose a unique username"
  fullWidth
/>
```

### TextArea

A multi-line text input component.

#### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `label` | `string` | - | Label text |
| `error` | `string` | - | Error message |
| `helpText` | `string` | - | Help text below textarea |
| `fullWidth` | `boolean` | `false` | Makes textarea full width |

Plus all standard HTML textarea attributes.

#### Example

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

#### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `label` | `string` | - | Label text |
| `error` | `string` | - | Error message |
| `helpText` | `string` | - | Help text below select |
| `options` | `SelectOption[]` | - | Array of options |
| `placeholder` | `string` | - | Placeholder text |
| `fullWidth` | `boolean` | `false` | Makes select full width |

#### Example

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

#### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `isOpen` | `boolean` | - | Controls visibility |
| `onClose` | `() => void` | - | Close handler |
| `title` | `string` | - | Modal title |
| `subtitle` | `string` | - | Modal subtitle |
| `children` | `ReactNode` | - | Modal content |
| `footer` | `ReactNode` | - | Footer content |
| `size` | `'sm'` \| `'md'` \| `'lg'` \| `'xl'` | `'md'` | Modal size |
| `showCloseButton` | `boolean` | `true` | Shows close button |

#### Example

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
  <Input label="Name" fullWidth />
</Modal>
```

### Card

A container component for grouping related content.

#### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `children` | `ReactNode` | - | Card content |
| `padding` | `'none'` \| `'sm'` \| `'md'` \| `'lg'` | `'md'` | Padding size |
| `onClick` | `() => void` | - | Makes card clickable |
| `hoverable` | `boolean` | `false` | Adds hover effect |
| `className` | `string` | - | Additional classes |

#### Examples

```tsx
import { Card } from '@/components/ui';

// Card with content
<Card padding="lg" hoverable>
  <h3>Collection Name</h3>
  <p>Description...</p>
</Card>

// Clickable card with no padding
<Card padding="none" onClick={handleClick}>
  <img src="..." alt="Preview" />
  <div className="p-4">Content</div>
</Card>
```

### Badge

A small label/tag component for status or categories.

#### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `children` | `ReactNode` | - | Badge content |
| `variant` | `'default'` \| `'success'` \| `'warning'` \| `'error'` \| `'info'` | `'default'` | Badge style |
| `size` | `'sm'` \| `'md'` \| `'lg'` | `'md'` | Badge size |
| `className` | `string` | - | Additional classes |

#### Examples

```tsx
import { Badge } from '@/components/ui';

<Badge variant="success">Active</Badge>
<Badge variant="warning">Pending</Badge>
<Badge variant="error">Failed</Badge>
<Badge variant="info" size="sm">New</Badge>
```

### FileUpload

A file upload component with drag & drop support.

#### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `onFilesChange` | `(files: UploadedFile[]) => void` | - | File change handler |
| `accept` | `string` | `'.pdf,.docx,.txt,.md'` | Accepted file types |
| `multiple` | `boolean` | `true` | Allow multiple files |
| `maxSize` | `number` | `100` | Max file size in MB |
| `label` | `string` | - | Label text |
| `helpText` | `string` | - | Help text |

#### Example

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

## Design System

### Color Palette

All components use the Carbon Design System color palette via Tailwind CSS:

#### Primary Colors
- `blue-60` - Primary actions
- `blue-70` - Primary hover state
- `blue-10` - Primary background

#### Gray Scale
- `gray-10` through `gray-100` - Neutral colors
- Higher numbers = darker colors

#### Status Colors
- `green-50` - Success states
- `yellow-30` - Warning states
- `red-50` - Error/danger states
- `blue-60` - Info states

### Typography

Components use these text sizes:
- `text-xs` - 12px
- `text-sm` - 14px
- `text-base` - 16px
- `text-lg` - 18px
- `text-xl` - 20px

### Spacing

Consistent spacing using Tailwind scale:
- `p-2` - 8px padding
- `p-4` - 16px padding
- `p-6` - 24px padding
- `gap-3` - 12px gap
- `space-y-4` - 16px vertical spacing

## Accessibility

All components include:

- **ARIA Labels** - Screen reader support
- **Keyboard Navigation** - Tab, Enter, Escape support
- **Focus States** - Visible focus indicators
- **Color Contrast** - WCAG AA compliant
- **Semantic HTML** - Proper element usage

## Best Practices

### 1. Use Semantic Variants

Choose button variants that match their purpose:

```tsx
// ✅ Good
<Button variant="primary">Save</Button>
<Button variant="secondary">Cancel</Button>
<Button variant="danger">Delete</Button>

// ❌ Avoid
<Button variant="primary">Cancel</Button>
<Button variant="secondary">Delete</Button>
```

### 2. Provide Labels

Always include labels for form inputs:

```tsx
// ✅ Good
<Input label="Email" type="email" />

// ❌ Avoid
<Input type="email" placeholder="Email" />
```

### 3. Show Loading States

Use loading prop during async operations:

```tsx
// ✅ Good
<Button loading={isSubmitting}>Submit</Button>

// ❌ Avoid
<Button disabled={isSubmitting}>
  {isSubmitting ? 'Loading...' : 'Submit'}
</Button>
```

### 4. Handle Errors

Display error messages using the error prop:

```tsx
// ✅ Good
<Input
  label="Email"
  value={email}
  error={emailError}
  onChange={handleEmailChange}
/>

// ❌ Avoid
<>
  <Input label="Email" value={email} />
  {emailError && <span className="text-red-500">{emailError}</span>}
</>
```

### 5. Be Consistent

Use the same components throughout your feature:

```tsx
// ✅ Good - Using reusable components
import { Button, Input, Modal } from '@/components/ui';

// ❌ Avoid - Mixing custom and reusable
import { Button } from '@/components/ui';
<button className="custom-btn">Click</button> // Don't mix
```

## Migration Guide

### From Custom Buttons

**Before:**
```tsx
<button className="btn-primary">Click me</button>
<button className="btn-secondary">Cancel</button>
```

**After:**
```tsx
import { Button } from '@/components/ui';

<Button variant="primary">Click me</Button>
<Button variant="secondary">Cancel</Button>
```

### From Custom Inputs

**Before:**
```tsx
<input
  type="text"
  className="input-field w-full"
  placeholder="Enter name"
/>
```

**After:**
```tsx
import { Input } from '@/components/ui';

<Input
  label="Name"
  placeholder="Enter name"
  fullWidth
/>
```

### From Custom Modals

**Before:**
```tsx
<div className="modal-overlay">
  <div className="modal-content">
    <h2>Title</h2>
    {/* content */}
  </div>
</div>
```

**After:**
```tsx
import { Modal } from '@/components/ui';

<Modal
  isOpen={isOpen}
  onClose={onClose}
  title="Title"
>
  {/* content */}
</Modal>
```

## TypeScript Support

All components are fully typed with TypeScript:

```tsx
import type { ButtonProps, ButtonVariant } from '@/components/ui';

// Props are typed
const MyButton: React.FC<{ variant: ButtonVariant }> = ({ variant }) => {
  return <Button variant={variant}>Click</Button>;
};

// Exported types
type UploadedFile = {
  id: string;
  name: string;
  size: number;
  type: string;
  status: 'pending' | 'uploading' | 'complete' | 'error';
  progress: number;
  file: File;
};
```

## Contributing

When adding new components to the UI library:

1. Follow existing patterns and prop naming conventions
2. Support all relevant HTML attributes via spread props
3. Use TypeScript for type safety
4. Include proper JSDoc documentation
5. Export the component and its types from `index.ts`
6. Add comprehensive documentation with examples
7. Test accessibility features

## Examples

See the `LightweightCreateCollectionModal` component for a complete example of using multiple UI components together:

`frontend/src/components/modals/LightweightCreateCollectionModal.tsx`

This modal demonstrates:
- Modal component with footer
- Input component with validation
- Button components with variants
- FileUpload component with drag & drop
- Proper TypeScript typing
- Error handling
- Loading states

## Resources

- [Component Source Code](https://github.com/manavgup/rag_modulo/tree/main/frontend/src/components/ui)
- [Carbon Design System](https://carbondesignsystem.com/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Heroicons](https://heroicons.com/) - Icon library
- [React Documentation](https://react.dev/)
