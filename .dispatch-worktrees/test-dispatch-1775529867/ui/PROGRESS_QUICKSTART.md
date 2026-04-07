# Progress UI Quick Start Guide

## 🚀 Quick Integration (5 minutes)

### 1. Import the Component

```typescript
import { ProgressSidebar } from './components/ProgressSidebar';
```

### 2. Add to Your Layout

```typescript
function App() {
  return (
    <div style={{ display: 'flex', height: '100vh' }}>
      <ProgressSidebar
        onComponentClick={(id) => console.log('Component:', id)}
        onFeatureClick={(id) => console.log('Feature:', id)}
      />
      <YourMainContent />
    </div>
  );
}
```

### 3. That's It!

The sidebar now displays:
- ✅ Component progress with status
- ✅ Feature progress with tasks
- ✅ Real-time updates (mock data)
- ✅ Click handlers for integration

## 📁 Files Created

```
/ui/src/components/
├── ComponentProgress.tsx      ← Component list view
├── FeatureProgress.tsx        ← Feature list view
├── ProgressSidebar.tsx        ← Main container
└── ProgressSidebar.css        ← Shared styles
```

## 🎨 What You Get

### Components Tab
- List of all components
- Progress bars (0-100%)
- Status badges (not started, in progress, completed, error, blocked)
- Type icons (🎨 frontend, ⚙️ backend, 🗄️ database, etc.)
- Test status (✓ passing, ✗ failing)
- File counts
- Click to highlight

### Features Tab
- Grouped by component
- Collapsible groups
- Priority indicators (🔴 high, 🟡 medium, 🟢 low)
- Task checklists with auto-checking
- Time tracking (estimated vs actual)
- Progress bars per feature

## 🔌 Connect Real Data (Next Step)

### Option 1: WebSocket (Recommended)

```typescript
import { useWebSocket } from './hooks/useWebSocket';

function App() {
  const { lastMessage } = useWebSocket({
    onMessage: (msg) => {
      // Components auto-refresh on updates
    }
  });

  return <ProgressSidebar ... />;
}
```

### Option 2: State Store

```typescript
// Create buildStore.ts
import create from 'zustand';

interface BuildStore {
  components: Component[];
  features: Feature[];
  // ... methods
}

export const useBuildStore = create<BuildStore>(...);

// In ComponentProgress.tsx, replace mock data:
const components = useBuildStore((state) => state.components);
```

### Option 3: API Polling

```typescript
// Already implemented! Just replace the mock data in:
// - ComponentProgress.tsx: loadComponents()
// - FeatureProgress.tsx: loadFeatures()

const loadComponents = async () => {
  const data = await fetch('/api/components').then(r => r.json());
  setComponents(data);
};
```

## 🎯 Event Handlers

### Highlight Component in Canvas

```typescript
<ProgressSidebar
  onComponentClick={(componentId) => {
    // Your canvas highlighting code
    canvasAPI.highlightComponent(componentId);
  }}
/>
```

### Show Feature Details

```typescript
<ProgressSidebar
  onFeatureClick={(featureId) => {
    // Your feature detail modal/panel
    setSelectedFeature(featureId);
    openFeatureModal();
  }}
/>
```

## 📊 Data Models

### Component

```typescript
{
  id: 'comp-1',
  name: 'Dashboard UI',
  type: 'frontend', // 'frontend' | 'backend' | 'database' | 'service' | 'api'
  status: 'in_progress', // 'not_started' | 'in_progress' | 'completed' | 'error' | 'blocked'
  progress: 65, // 0-100
  dependencies: ['comp-1'],
  files: ['Dashboard.tsx', 'Dashboard.css'],
  testsPass: true,
  startTime: 1234567890,
  endTime: 1234567890,
  error: 'Optional error message'
}
```

### Feature

```typescript
{
  id: 'feat-1',
  name: 'Task List View',
  description: 'Display tasks in a sortable, filterable list',
  priority: 'high', // 'high' | 'medium' | 'low'
  component: 'comp-2', // Component ID
  status: 'in_progress',
  progress: 70,
  tasks: [
    { id: 'task-1', name: 'Create component', completed: true, timestamp: 1234567890 },
    { id: 'task-2', name: 'Add tests', completed: false }
  ],
  estimatedTime: 150, // minutes
  actualTime: 120 // minutes (optional)
}
```

## 🎨 Customization

### Change Sidebar Width

```css
/* In ProgressSidebar.css */
.progress-sidebar {
  width: 400px; /* Change from 350px */
}
```

### Change Colors

```css
/* Status colors */
.component-item.selected {
  border-color: #YOUR_COLOR;
}

/* Progress bars */
.progress-bar-fill {
  background-color: #YOUR_COLOR;
}
```

### Change Refresh Rate

```typescript
// In ComponentProgress.tsx or FeatureProgress.tsx
const interval = setInterval(loadComponents, 5000); // Change from 3000ms
```

## 📚 Full Documentation

See `/ui/src/components/PROGRESS_COMPONENTS.md` for:
- Complete API reference
- Advanced integration patterns
- Performance optimization tips
- Accessibility features
- Browser compatibility

## 🐛 Troubleshooting

### Components not showing?
- Check console for errors
- Verify data format matches Component interface
- Check if `loadComponents()` is being called

### Styles not applied?
- Verify `ProgressSidebar.css` is imported
- Check for CSS conflicts in your app
- Try adding `!important` for testing

### Real-time updates not working?
- Check WebSocket connection
- Verify polling interval is set
- Check browser console for errors

## 💡 Tips

- Start with mock data to test layout
- Add click handlers gradually
- Use browser DevTools to inspect state
- Test responsive behavior at 350px+ width
- Check color contrast in your theme

## 📞 Support

- Documentation: `/ui/src/components/PROGRESS_COMPONENTS.md`
- Examples: `/ui/src/components/ProgressSidebar.example.tsx`
- Summary: `/ui/src/components/PROGRESS_UI_SUMMARY.md`

---

**Ready to use! Just import and render.**
