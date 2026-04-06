# Progress Tracking UI Components

This document describes the progress tracking components for BuildRunner 3.

## Overview

The progress tracking system consists of three main components that work together to provide real-time visibility into the build process:

1. **ComponentProgress.tsx** - Displays component-level progress
2. **FeatureProgress.tsx** - Shows feature-level progress with task checklists
3. **ProgressSidebar.tsx** - Container that combines both views with tab switching

## Components

### ComponentProgress

**File:** `/ui/src/components/ComponentProgress.tsx`

Displays a list of components with progress bars and status indicators.

**Features:**
- Visual progress bars with color-coded status
- Component type icons (frontend, backend, database, service, API)
- Test passing/failing indicators
- Click-to-highlight in canvas
- Real-time status updates
- File count display
- Error message display

**Props:**
```typescript
interface ComponentProgressProps {
  onComponentClick?: (componentId: string) => void;
  selectedComponentId?: string;
}
```

**Status Colors:**
- Not Started: `#888` (gray)
- In Progress: `#ff9800` (orange)
- Completed: `#4caf50` (green)
- Error: `#f44336` (red)
- Blocked: `#9c27b0` (purple)

**Type Icons:**
- Frontend: 🎨
- Backend: ⚙️
- Database: 🗄️
- Service: 🔧
- API: 🔌

### FeatureProgress

**File:** `/ui/src/components/FeatureProgress.tsx`

Displays a collapsible feature list grouped by component with task checklists.

**Features:**
- Grouped by component (collapsible)
- Priority indicators (high/medium/low)
- Progress bars per feature
- Task checklist with auto-checking
- Estimated vs actual time tracking
- Real-time task completion updates
- Auto-expand on component selection

**Props:**
```typescript
interface FeatureProgressProps {
  selectedComponentId?: string;
  onFeatureClick?: (featureId: string) => void;
}
```

**Priority Colors:**
- High: `#f44336` (red)
- Medium: `#ff9800` (orange)
- Low: `#4caf50` (green)

**Time Display:**
- Shows estimated time for all features
- Shows actual time for completed/in-progress features
- Color-coded: green if under estimate, red if over

### ProgressSidebar

**File:** `/ui/src/components/ProgressSidebar.tsx`

Main container that combines ComponentProgress and FeatureProgress with tab switching.

**Features:**
- Tab switching between Components and Features views
- Maintains selected component state across tabs
- Scrollable content with fixed header
- Responsive design

**Props:**
```typescript
interface ProgressSidebarProps {
  onComponentClick?: (componentId: string) => void;
  onFeatureClick?: (featureId: string) => void;
}
```

## Styling

**File:** `/ui/src/components/ProgressSidebar.css`

Shared styles for all progress components with:
- Fixed sidebar width: `350px`
- Scrollable content area
- Custom scrollbar styling
- Hover effects and transitions
- Responsive adjustments for mobile
- Consistent color scheme matching BuildRunner theme

## Usage

### Basic Integration

```typescript
import { ProgressSidebar } from './components/ProgressSidebar';

function App() {
  const handleComponentClick = (componentId: string) => {
    // Highlight component in canvas
    canvasAPI.highlightComponent(componentId);
  };

  const handleFeatureClick = (featureId: string) => {
    // Navigate to feature details
    router.push(`/features/${featureId}`);
  };

  return (
    <div style={{ display: 'flex' }}>
      <ProgressSidebar
        onComponentClick={handleComponentClick}
        onFeatureClick={handleFeatureClick}
      />
      <MainContent />
    </div>
  );
}
```

### With WebSocket for Real-time Updates

```typescript
import { useWebSocket } from '../hooks/useWebSocket';
import { ProgressSidebar } from './components/ProgressSidebar';

function App() {
  const { lastMessage } = useWebSocket({
    onMessage: (message) => {
      if (message.type === 'task_update') {
        // Components will auto-refresh via their internal intervals
        // Or trigger immediate refresh if using state management
      }
    }
  });

  return <ProgressSidebar ... />;
}
```

### With State Management Store

```typescript
// Create a build store (example with Zustand)
import create from 'zustand';

interface BuildStore {
  components: Component[];
  features: Feature[];
  updateComponent: (id: string, updates: Partial<Component>) => void;
  updateFeature: (id: string, updates: Partial<Feature>) => void;
}

const useBuildStore = create<BuildStore>((set) => ({
  components: [],
  features: [],
  updateComponent: (id, updates) =>
    set((state) => ({
      components: state.components.map((c) =>
        c.id === id ? { ...c, ...updates } : c
      ),
    })),
  updateFeature: (id, updates) =>
    set((state) => ({
      features: state.features.map((f) =>
        f.id === id ? { ...f, ...updates } : f
      ),
    })),
}));

// Use in components
const components = useBuildStore((state) => state.components);
```

## Data Models

### Component

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

### Feature

```typescript
interface Feature {
  id: string;
  name: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  component: string; // Component ID
  status: ComponentStatus;
  progress: number; // 0-100
  tasks: Task[];
  estimatedTime: number; // in minutes
  actualTime?: number; // in minutes
}
```

### Task

```typescript
interface Task {
  id: string;
  name: string;
  completed: boolean;
  timestamp?: number;
}
```

## TODO: Integration Steps

1. **Create Build Store** (if not exists)
   - Replace mock data with real API calls or store subscriptions
   - Implement WebSocket integration for real-time updates

2. **Connect to Backend API**
   - Update `loadComponents()` to fetch from actual API
   - Update `loadFeatures()` to fetch from actual API
   - Subscribe to build events

3. **Implement Canvas Highlighting**
   - Connect `onComponentClick` to canvas highlighting logic
   - Add visual feedback when components are selected

4. **Add Feature Details View**
   - Connect `onFeatureClick` to feature detail panel or modal
   - Show full feature information and task details

5. **Performance Optimization**
   - Consider virtualization for large component/feature lists
   - Implement debouncing for frequent updates
   - Add memoization for expensive renders

## File Structure

```
/ui/src/components/
├── ComponentProgress.tsx      # Component progress list
├── FeatureProgress.tsx        # Feature progress list with tasks
├── ProgressSidebar.tsx        # Main sidebar container
├── ProgressSidebar.css        # Shared styles
├── ProgressSidebar.example.tsx # Example integration
├── Progress/
│   └── index.ts              # Export all progress components
└── PROGRESS_COMPONENTS.md    # This file
```

## Customization

### Changing Colors

Edit `/ui/src/components/ProgressSidebar.css`:

```css
/* Status colors */
.component-item.selected {
  border-color: #YOUR_COLOR;
}

/* Progress bar colors */
.progress-bar-fill {
  background-color: #YOUR_COLOR;
}
```

### Changing Sidebar Width

Edit `.progress-sidebar` in CSS:

```css
.progress-sidebar {
  width: 400px; /* Change from 350px */
}
```

### Changing Refresh Interval

Edit component files:

```typescript
// Change from 3000ms to desired interval
const interval = setInterval(loadComponents, 5000);
```

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

Uses modern CSS features:
- CSS Grid
- CSS Flexbox
- Custom scrollbar styling (webkit only)
- CSS transitions and animations

## Testing

Components include mock data for development and testing. To test:

1. Import and render in your app
2. Mock data will be displayed automatically
3. Test click handlers by adding console.logs
4. Verify responsive behavior at different screen sizes

## Accessibility

- Semantic HTML structure
- ARIA labels where needed
- Keyboard navigation support
- Color contrast meets WCAG AA standards
- Focus indicators on interactive elements

## Performance Notes

- Components refresh every 3 seconds by default
- Consider implementing virtual scrolling for 100+ items
- Use React.memo() for list items if performance issues occur
- WebSocket integration recommended for production use

---

**Created:** 2025-11-19
**Author:** BuildRunner AI
**Version:** 1.0.0
