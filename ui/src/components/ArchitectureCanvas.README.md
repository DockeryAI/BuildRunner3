# Architecture Canvas Component

Interactive architecture visualization using React Flow to display project components, their dependencies, and build status in real-time.

## Files Created

1. **ArchitectureCanvas.tsx** - Main canvas component
2. **nodes/ComponentNode.tsx** - Custom node component for displaying components
3. **ArchitectureCanvas.css** - Complete styling with dark theme

## Features

- **Visual Component Graph**: Displays components as nodes with their dependencies as edges
- **Real-time Status Updates**: Components change color based on status (not_started, in_progress, completed, error, blocked)
- **Progress Indicators**: Circular progress rings around each component showing completion percentage
- **Pulsing Animation**: In-progress components pulse to draw attention
- **Force-Directed Layout**: Automatic positioning using physics simulation for optimal graph layout
- **Interactive Controls**:
  - Zoom/pan controls
  - Minimap for navigation
  - Re-layout button to recalculate positions
  - Fit view to see all components
- **Rich Tooltips**: Hover over components to see detailed information
- **Test Status Badges**: Visual indicator for passing/failing tests
- **Component Type Icons**: Visual distinction between frontend, backend, database, service, and API components

## Integration

### Add to WorkspaceUI

Add an "Architecture" tab to the workspace:

```tsx
// In WorkspaceUI.tsx
import { ArchitectureCanvas } from './ArchitectureCanvas';

// Update TabType
type TabType = 'command' | 'prd' | 'interactive-prd' | 'logs' | 'architecture';

// Add tab button in tab-navigation
<button
  className={`tab-btn ${activeTab === 'architecture' ? 'active' : ''}`}
  onClick={() => setActiveTab('architecture')}
>
  🏗️ Architecture
</button>

// Add tab content in workspace-body
{activeTab === 'architecture' && (
  <div className="tab-content" style={{ height: 'calc(100vh - 200px)' }}>
    <ArchitectureCanvas />
  </div>
)}
```

### Add to Dashboard

Add as a new panel in the Dashboard component:

```tsx
// In Dashboard.tsx
import { ArchitectureCanvas } from './ArchitectureCanvas';

// Add new tab option
const [activeTab, setActiveTab] = useState<'tasks' | 'agents' | 'telemetry' | 'architecture'>('tasks');

// Add tab button
<button
  className={`tab ${activeTab === 'architecture' ? 'active' : ''}`}
  onClick={() => setActiveTab('architecture')}
>
  Architecture
</button>

// Add tab content
{activeTab === 'architecture' && (
  <div style={{ height: '600px' }}>
    <ArchitectureCanvas />
  </div>
)}
```

### Standalone Usage

Use as a standalone page:

```tsx
import { ArchitectureCanvas } from './components/ArchitectureCanvas';

function ArchitecturePage() {
  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <ArchitectureCanvas />
    </div>
  );
}
```

## Data Flow

The component subscribes to the `buildStore` Zustand store:

```tsx
const session = useBuildStore((state) => state.session);
```

It automatically updates when:
- Components are added or updated
- Component status changes
- Progress updates occur
- Dependencies change

## Updating Components

Components are updated through the buildStore:

```tsx
// Update a single component
useBuildStore.getState().updateComponent('component-id', {
  status: 'in_progress',
  progress: 45,
});

// Update entire session
useBuildStore.getState().setSession({
  id: 'session-1',
  projectName: 'My Project',
  // ... other session data
  components: [
    {
      id: 'frontend-1',
      name: 'User Dashboard',
      type: 'frontend',
      status: 'in_progress',
      progress: 60,
      dependencies: ['backend-1'],
      files: ['src/Dashboard.tsx', 'src/Dashboard.css'],
      testsPass: true,
    },
    {
      id: 'backend-1',
      name: 'API Server',
      type: 'backend',
      status: 'completed',
      progress: 100,
      dependencies: ['database-1'],
      files: ['api/server.py', 'api/routes.py'],
      testsPass: true,
    },
    // ... more components
  ],
});
```

## Component Data Structure

```typescript
interface Component {
  id: string;
  name: string;
  type: 'frontend' | 'backend' | 'database' | 'service' | 'api';
  status: 'not_started' | 'in_progress' | 'completed' | 'error' | 'blocked';
  progress: number; // 0-100
  dependencies: string[]; // Component IDs
  files: string[];
  testsPass: boolean;
  startTime?: number;
  endTime?: number;
  error?: string;
}
```

## Styling Customization

The component uses CSS custom properties for easy theming. Modify `ArchitectureCanvas.css`:

```css
/* Change status colors */
.component-node {
  /* not_started */ --color-not-started: #64748b;
  /* in_progress */ --color-in-progress: #3b82f6;
  /* completed */   --color-completed: #22c55e;
  /* error */       --color-error: #ef4444;
  /* blocked */     --color-blocked: #f59e0b;
}

/* Change canvas background */
.architecture-canvas,
.react-flow {
  background: #0f172a; /* Dark mode */
}
```

## Force-Directed Layout

The component uses a physics-based layout algorithm that:

1. **Repulsion**: Pushes nodes apart to prevent overlap
2. **Attraction**: Pulls dependent nodes together
3. **Center Gravity**: Keeps the graph centered
4. **Boundary Constraints**: Prevents nodes from going off-screen

Adjust layout parameters in `ArchitectureCanvas.tsx`:

```typescript
const REPULSION_FORCE = 1000;  // Higher = more spread out
const ATTRACTION_FORCE = 0.001; // Higher = dependencies closer
const DAMPING = 0.9;            // Higher = less movement
const ITERATIONS = 100;         // More = better layout, slower
```

## Performance Considerations

- The layout calculation runs in a timeout to prevent UI blocking
- Shows loading state during layout calculation
- React Flow handles viewport virtualization for large graphs
- Memoized components prevent unnecessary re-renders

## Future Enhancements

Potential improvements (not yet implemented):

1. **Detail Panel**: Click a node to show detailed component information in a side panel
2. **Filtering**: Filter by status, type, or search by name
3. **Grouping**: Group related components by feature or domain
4. **Time Travel**: Scrub through build history to see how the architecture evolved
5. **Export**: Export the graph as PNG/SVG
6. **Collaborative Cursors**: Show where team members are looking
7. **Annotations**: Add notes and comments to components

## Example Integration

Full example with WebSocket updates:

```tsx
import { useEffect } from 'react';
import { useBuildStore } from '../stores/buildStore';
import { ArchitectureCanvas } from './ArchitectureCanvas';
import io from 'socket.io-client';

function BuildMonitorPage() {
  useEffect(() => {
    const socket = io('http://localhost:8080');

    socket.on('component_update', (data) => {
      useBuildStore.getState().updateComponent(data.componentId, {
        status: data.status,
        progress: data.progress,
      });
    });

    socket.on('build_session_update', (session) => {
      useBuildStore.getState().setSession(session);
    });

    return () => socket.disconnect();
  }, []);

  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <ArchitectureCanvas />
    </div>
  );
}
```

## Dependencies

Required packages (already in package.json):
- `reactflow@^11.11.4` - React Flow library for graph visualization
- `zustand@^5.0.8` - State management
- `react@^18.2.0` - React framework

No additional dependencies needed!
