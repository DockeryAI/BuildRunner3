# ProjectInitModal Usage Guide

## Overview
The `ProjectInitModal` component provides a user-friendly interface for initializing a new BuildRunner project from a PRD (Product Requirements Document).

## Features
- ✅ Project alias validation (lowercase, alphanumeric, hyphens)
- ✅ Project path input with file picker button
- ✅ Real-time form validation
- ✅ Pre-flight checklist with status indicators
- ✅ Loading states during initialization
- ✅ Comprehensive error handling
- ✅ Automatic redirect to `/build/:alias` on success

## Props

```typescript
interface ProjectInitModalProps {
  isOpen: boolean;      // Controls modal visibility
  onClose: () => void;  // Callback when modal is closed
  prdData: any;         // PRD data from the PRD builder
}
```

## Usage Example

```tsx
import { useState } from 'react';
import { ProjectInitModal } from './components/ProjectInitModal';

function MyComponent() {
  const [showModal, setShowModal] = useState(false);
  const [prdData, setPrdData] = useState(null);

  const handleComplete = (projectData) => {
    // Store PRD data from PRD builder or parser
    setPrdData(projectData.parsedPRD);
    setShowModal(true);
  };

  return (
    <div>
      <button onClick={() => setShowModal(true)}>
        Initialize Project
      </button>

      <ProjectInitModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        prdData={prdData}
      />
    </div>
  );
}
```

## Integration with InteractivePRDBuilder

```tsx
<InteractivePRDBuilder
  projectName="My Project"
  projectPath=""
  initialPRD={parsedPRD}
  onSave={() => console.log('PRD saved')}
  onCreateProject={(prdData) => {
    // Show the ProjectInitModal after PRD is ready
    setPRDData(prdData);
    setShowInitModal(true);
  }}
/>

<ProjectInitModal
  isOpen={showInitModal}
  onClose={() => setShowInitModal(false)}
  prdData={prdData}
/>
```

## API Endpoint

The modal makes a POST request to:

```
POST http://localhost:8080/api/build/init
```

Request body:
```json
{
  "alias": "my-project",
  "projectPath": "/Users/username/projects/my-project",
  "prdData": { /* PRD object */ }
}
```

Expected response:
```json
{
  "success": true,
  "message": "Project initialized successfully"
}
```

Error response:
```json
{
  "success": false,
  "error": "Error message here"
}
```

## Validation Rules

### Alias Validation
- Must be 3-50 characters
- Lowercase letters only (a-z)
- Numbers allowed (0-9)
- Hyphens allowed (-)
- Cannot start or end with hyphen
- Auto-converts to lowercase
- Strips invalid characters

### Project Path Validation
- Must be an absolute path
- Unix: starts with `/`
- Windows: starts with drive letter (e.g., `C:\`)

## Pre-flight Checks

The modal runs these automated checks before initialization:

1. **Alias Validation** - Validates format and uniqueness
2. **Path Validation** - Checks path format and accessibility
3. **PRD Verification** - Ensures PRD data is present and valid
4. **API Connection** - Tests connection to BuildRunner API

Each check shows:
- ⏳ Pending
- 🔄 Checking (animated)
- ✓ Success (green)
- ✗ Error (red with message)

## Error Handling

The modal handles these error scenarios:

- **Validation errors** - Shown inline under form fields
- **Network errors** - "Cannot connect to BuildRunner API"
- **Server errors** - Displays server error message
- **Timeout errors** - 30-second timeout with clear message
- **General errors** - User-friendly fallback message

## Styling

The modal uses dark theme styling matching the BuildRunner UI:
- Backdrop blur overlay
- Animated entrance (slide-in)
- Responsive design (mobile-friendly)
- Custom scrollbar styling
- Accessible focus states

## Customization

To customize the API URL, modify the constant:

```typescript
const API_URL = 'http://localhost:8080';
```

For production, use environment variables:

```typescript
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';
```

## Future Enhancements

- [ ] Electron file picker integration
- [ ] Project template selection
- [ ] Git repository initialization option
- [ ] Custom build configuration
- [ ] Project icon/color selection
