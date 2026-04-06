# BuildMonitor Page Component

The BuildMonitor page provides a real-time monitoring interface for build sessions with a 3-zone layout optimized for tracking build progress.

## Features

- **3-Zone Layout**:
  - Header (10%): Project name, status indicator, elapsed time, WebSocket connection status
  - Canvas Zone (60% default): Visual build progress area (placeholder for future canvas component)
  - Terminal Panel (30% default): Real-time terminal output with auto-scroll

- **Resizable Panels**: Drag the resize handle between canvas and terminal to adjust heights (40-80% range)
- **Layout Persistence**: Panel sizes are saved to localStorage
- **Real-time Updates**: WebSocket integration for live build status and terminal output
- **Dark Theme**: VS Code aesthetic matching the existing BuildRunner UI

## Usage

### 1. Install Dependencies

The component requires `react-router-dom`:

```bash
npm install react-router-dom
```

### 2. Add Routing to App

Update `src/main.tsx` to include routing:

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

### 3. Navigate to BuildMonitor

Navigate to the BuildMonitor page using the project alias:

```tsx
import { Link } from 'react-router-dom';

// Example link
<Link to="/build/my-project">Monitor Build</Link>

// Or programmatically
import { useNavigate } from 'react-router-dom';

const navigate = useNavigate();
navigate('/build/my-project');
```

## Component Structure

```
/Users/byronhudson/Projects/BuildRunner3/ui/src/
├── pages/
│   └── BuildMonitor.tsx          # Main page component
├── styles/
│   └── BuildMonitor.css          # Component styling
└── stores/
    └── buildStore.ts             # Zustand state management
```

## State Management

The component uses Zustand for state management via `buildStore.ts`:

```tsx
import { useBuildStore } from '../stores/buildStore';

const {
  session,              // Current build session
  terminalLines,        // Terminal output lines
  websocket,           // WebSocket connection state
  setSession,          // Update session
  addTerminalLine,     // Add terminal output
  clearTerminal,       // Clear terminal
} = useBuildStore();
```

## WebSocket Integration

The component subscribes to WebSocket events:

- `session_update`: Update build session data
- `task_update`: Add terminal output lines
- `progress_update`: Update build progress

## Layout Configuration

The layout is configurable via localStorage:

- Key: `buildmonitor-canvas-height`
- Value: Percentage (40-80)
- Default: 60%

## Styling

The component uses a dark theme matching VS Code:

- Background: `#1e1e1e`
- Panel backgrounds: `#2d2d2d`
- Borders: `#3e3e3e`
- Text: `#d4d4d4`
- Accents: `#4ec9b0`, `#569cd6`, `#f48771`

## Future Enhancements

- Replace canvas placeholder with ReactFlow-based build visualization
- Add filtering and search to terminal output
- Add pause/resume controls
- Export terminal logs
- Multiple terminal tabs
- Metrics dashboard in canvas area

## Example

```tsx
// Navigate to build monitor for "ecommerce-app" project
import { useNavigate } from 'react-router-dom';

function StartBuild() {
  const navigate = useNavigate();

  const handleStartBuild = async (projectAlias: string) => {
    // Start build via API
    await startBuild(projectAlias);

    // Navigate to monitor
    navigate(`/build/${projectAlias}`);
  };

  return (
    <button onClick={() => handleStartBuild('ecommerce-app')}>
      Start Build
    </button>
  );
}
```

## Dependencies

- `react` ^18.2.0
- `react-router-dom` ^6.x
- `zustand` ^5.0.8
- Existing: `useWebSocket` hook
- Existing: Build types from `types/build.ts`
