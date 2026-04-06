# BuildMonitor Integration Guide

## Overview

The BuildMonitor page component has been created with a 3-zone layout for real-time build monitoring.

## Files Created

### 1. Main Component
**Location**: `/Users/byronhudson/Projects/BuildRunner3/ui/src/pages/BuildMonitor.tsx`

Features:
- 3-zone layout: Header (10%), Canvas (60%), Terminal (30%)
- Resizable panels with drag handles
- Layout persistence via localStorage
- Real-time WebSocket updates
- Elapsed time tracking
- Status indicators

### 2. Styling
**Location**: `/Users/byronhudson/Projects/BuildRunner3/ui/src/styles/BuildMonitor.css`

Features:
- Dark theme matching VS Code aesthetic
- Responsive design (mobile-friendly)
- Smooth panel transitions
- Custom scrollbar styling
- Hover effects and interactions

### 3. State Management
**Location**: `/Users/byronhudson/Projects/BuildRunner3/ui/src/stores/buildStore.ts`

Already existed with:
- Zustand store for build state
- Terminal output management
- WebSocket connection tracking
- Session persistence

## Setup Instructions

### Step 1: Router Integration

Update `src/main.tsx` to add routing:

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import App from './App';
import { BuildMonitor } from './pages/BuildMonitor';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/build/:projectAlias" element={<BuildMonitor />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
```

### Step 2: Navigation

Add navigation to BuildMonitor from your existing components:

```tsx
import { useNavigate } from 'react-router-dom';

function YourComponent() {
  const navigate = useNavigate();

  const startBuildMonitor = (projectAlias: string) => {
    navigate(`/build/${projectAlias}`);
  };

  return (
    <button onClick={() => startBuildMonitor('my-project')}>
      Monitor Build
    </button>
  );
}
```

### Step 3: Initialize Build Session

Before navigating, set the build session in the store:

```tsx
import { useBuildStore } from './stores/buildStore';
import type { BuildSession } from './types/build';

const session: BuildSession = {
  id: 'session-123',
  projectName: 'My Project',
  projectAlias: 'my-project',
  projectPath: '/path/to/project',
  startTime: Date.now(),
  status: 'running',
  components: [],
  features: [],
};

useBuildStore.getState().setSession(session);
navigate(`/build/${session.projectAlias}`);
```

## Features

### Layout Zones

1. **Header (10% height)**
   - Project name
   - Status indicator (color-coded)
   - Elapsed time counter
   - WebSocket connection status

2. **Canvas Zone (60% default, resizable)**
   - Currently shows placeholder with stats
   - Ready for ReactFlow or custom visualization
   - Shows component/feature counts

3. **Terminal Panel (30% default, resizable)**
   - Real-time terminal output
   - Auto-scroll to latest
   - Syntax-highlighted by type (stdout/stderr/info/error/success)
   - Clear button

### Resizable Panels

- Drag the handle between canvas and terminal
- Height range: 40-80% for canvas
- Settings persist to localStorage
- Smooth resize experience

### WebSocket Integration

The component subscribes to these message types:

```typescript
interface WebSocketMessage {
  type: 'session_update' | 'task_update' | 'progress_update';
  // ... additional fields
}
```

Handle in your WebSocket server:
- `session_update`: Full session state updates
- `task_update`: Individual task progress (can include terminal output)
- `progress_update`: Overall build progress

### Terminal Output

Add terminal lines programmatically:

```tsx
import { useBuildStore } from './stores/buildStore';

useBuildStore.getState().addTerminalLine({
  timestamp: Date.now(),
  type: 'stdout',  // 'stdout' | 'stderr' | 'info' | 'error' | 'success'
  content: 'Build started...',
});
```

## Styling Customization

The component uses CSS custom properties. To customize:

```css
/* In your global CSS or BuildMonitor.css */
.build-monitor {
  --bg-primary: #1e1e1e;
  --bg-secondary: #2d2d2d;
  --border-color: #3e3e3e;
  --text-primary: #d4d4d4;
  --text-secondary: #858585;
  --accent-success: #4ec9b0;
  --accent-info: #569cd6;
  --accent-error: #f48771;
}
```

## URL Parameters

The component uses React Router params:

```
/build/:projectAlias
```

Example URLs:
- `/build/ecommerce-app`
- `/build/blog-platform`
- `/build/api-service`

Access in component:
```tsx
const { projectAlias } = useParams<{ projectAlias: string }>();
```

## State Persistence

The component persists:
- Canvas height: `localStorage.getItem('buildmonitor-canvas-height')`
- Build session: Managed by Zustand persist middleware in buildStore

## Future Enhancements

Planned features for the canvas zone:
- ReactFlow-based build visualization
- Component dependency graph
- Real-time file changes
- Code metrics dashboard
- Test results visualization

Planned features for terminal:
- Search/filter terminal output
- Download logs
- Multiple terminal tabs
- Command history
- Terminal input for interactive builds

## TypeScript Types

All types are defined in `/Users/byronhudson/Projects/BuildRunner3/ui/src/types/build.ts`:

```typescript
import type {
  BuildSession,
  Component,
  Feature,
  TerminalLine,
} from './types/build';
```

## Dependencies

The component requires:
- `react` ^18.2.0
- `react-router-dom` ^6.x (newly installed)
- `zustand` ^5.0.8 (existing)

## Testing

To test the component:

1. Start the dev server:
   ```bash
   npm run dev
   ```

2. Navigate to a build URL:
   ```
   http://localhost:5173/build/test-project
   ```

3. The component should render with placeholder content

## Troubleshooting

### Component not rendering
- Ensure router is set up in `main.tsx`
- Check browser console for routing errors
- Verify `react-router-dom` is installed

### WebSocket not connecting
- Check `VITE_WS_URL` environment variable
- Verify WebSocket server is running
- Check browser network tab for WS connection

### Layout not saving
- Check browser localStorage is enabled
- Clear localStorage and refresh if corrupted
- Check browser console for storage errors

## Support

For questions or issues:
1. Check `/Users/byronhudson/Projects/BuildRunner3/ui/src/pages/README.md`
2. Review component source code
3. Check existing components for patterns (Dashboard, LogViewer)
