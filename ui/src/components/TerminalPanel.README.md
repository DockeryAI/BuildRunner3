# TerminalPanel Component

A fully-featured terminal component built with xterm.js for live streaming build output with ANSI color support, filtering, and search capabilities.

## Features

- **xterm.js Terminal**: Full terminal emulation with ANSI color support
- **Live Streaming**: Real-time updates from buildStore with circular buffer (1000 lines max)
- **Auto-scroll**: Automatic scrolling with pause/resume controls (with visual feedback)
- **Filtering**: Filter by log type (info, error, success, all) - rebuilds display instantly
- **Search**: Ctrl+F to search with xterm-addon-search for highlighted matches
- **Copy Support**: Select and copy terminal text with visual confirmation
- **VS Code Theme**: Dark theme matching VS Code's terminal (Fira Code font)
- **Performance**: Efficient rendering with FitAddon and processed lines tracking
- **Connection Status**: Visual indicators for WebSocket connection state
- **Resize Handle**: Visual resize handle at top of panel
- **Responsive**: Mobile-friendly with adaptive controls

## Installation

The required dependencies are already included in package.json:

```json
{
  "dependencies": {
    "xterm": "^5.3.0",
    "xterm-addon-fit": "^0.8.0",
    "xterm-addon-search": "^0.13.0",
    "zustand": "^5.0.8"
  }
}
```

## Usage

### Basic Usage

```tsx
import { TerminalPanel } from './components/TerminalPanel';

function MyComponent() {
  return <TerminalPanel height="500px" />;
}
```

### With WebSocket Integration

```tsx
import { TerminalPanel } from './components/TerminalPanel';
import { useBuildStore } from './stores/buildStore';
import { useWebSocket } from './hooks/useWebSocket';

function BuildMonitor() {
  const addTerminalLine = useBuildStore((state) => state.addTerminalLine);

  useWebSocket({
    onMessage: (message) => {
      // Convert WebSocket message to terminal line
      addTerminalLine({
        timestamp: Date.now(),
        type: 'info',
        content: `Received: ${message.type}`,
      });
    },
  });

  return <TerminalPanel height="600px" />;
}
```

### Adding Terminal Lines

```tsx
import { useBuildStore } from './stores/buildStore';

function MyComponent() {
  const addTerminalLine = useBuildStore((state) => state.addTerminalLine);

  const handleBuildStart = () => {
    addTerminalLine({
      timestamp: Date.now(),
      type: 'success',
      content: 'Build started successfully',
    });
  };

  const handleBuildError = (error: string) => {
    addTerminalLine({
      timestamp: Date.now(),
      type: 'error',
      content: `Build failed: ${error}`,
    });
  };

  return (
    <div>
      <button onClick={handleBuildStart}>Start Build</button>
      <TerminalPanel />
    </div>
  );
}
```

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `height` | `string` | `"400px"` | Height of the terminal panel |

## Store Integration

The TerminalPanel uses the `buildStore` Zustand store:

```tsx
interface BuildState {
  terminalLines: TerminalLine[];
  websocket: WebSocketState;
  addTerminalLine: (line: Omit<TerminalLine, 'id'>) => void;
  clearTerminalLines: () => void;
}

interface WebSocketState {
  status: 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error';
  error?: string;
  lastConnected?: number;
}
```

### TerminalLine Type

```tsx
interface TerminalLine {
  id: string;           // Auto-generated
  timestamp: number;    // Unix timestamp
  type: 'stdout' | 'stderr' | 'info' | 'error' | 'success';
  content: string;      // The actual log message
}
```

## Features

### 1. Filtering

Click filter buttons to show only specific log types:
- **All**: Show all log types
- **Info**: Show only info messages (cyan)
- **Errors**: Show only errors (red)
- **Success**: Show only success messages (green)

### 2. Search (Using SearchAddon)

- Press `Ctrl+F` or click "🔍 Search" button
- Type search term and press Enter to find next match
- Press Shift+Enter to find previous match
- Use ↑/↓ buttons to navigate matches
- Clear search to reset
- Press `Escape` to close search bar
- Search is case-insensitive and highlights matches in the terminal

### 3. Auto-scroll

- Automatically scrolls to bottom when new lines arrive
- Click "⏸ Pause" to stop auto-scrolling (button becomes active/highlighted)
- Click "▶ Resume" to re-enable auto-scrolling
- Auto-scroll state persists across terminal operations

### 4. Copy Selection

- Select text in the terminal with your mouse
- Click "📋 Copy" button to copy selection to clipboard
- Shows a brief "Copied to clipboard!" notification
- Clipboard API used for secure copy operation

### 5. Clear Terminal

- Click "🗑 Clear" button to clear all terminal output
- This clears both the xterm display and the buildStore
- Resets processed lines tracking

## ANSI Color Support

The terminal automatically formats log lines with ANSI colors:

```
[TIMESTAMP] [TYPE] Message content
```

- **Timestamp**: Gray (`\x1b[90m`)
- **Error/Stderr**: Red (`\x1b[31m`)
- **Success**: Green (`\x1b[32m`)
- **Info**: Cyan (`\x1b[36m`)
- **Stdout**: White (`\x1b[37m`)

You can also include ANSI color codes directly in the content:

```tsx
addTerminalLine({
  timestamp: Date.now(),
  type: 'info',
  content: '\x1b[33mWarning:\x1b[0m This is yellow text',
});
```

## Theming

The terminal uses a VS Code-inspired dark theme. To customize colors, edit `TerminalPanel.tsx`:

```tsx
const terminal = new Terminal({
  theme: {
    background: '#1e1e1e',
    foreground: '#d4d4d4',
    cursor: '#d4d4d4',
    // ... more theme options
  },
});
```

## Performance

The terminal implements several performance optimizations:

1. **Line Limit**: Only stores last 1000 lines in buildStore
2. **Efficient Rendering**: Uses xterm.js's optimized rendering
3. **Lazy Updates**: Only re-renders when terminalLines change
4. **FitAddon**: Automatically resizes to container

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+F` / `Cmd+F` | Toggle search bar |
| `Escape` | Close search bar |
| `Enter` | Find next match |
| `Shift+Enter` | Find previous match |
| `Ctrl+C` / `Cmd+C` | Copy selection (native browser support) |

## Example: Complete Integration

See `TerminalDemo.tsx` for a complete example of integrating TerminalPanel with WebSocket updates.

```tsx
import { TerminalDemo } from './components/TerminalDemo';

function App() {
  return <TerminalDemo />;
}
```

## Styling

The component includes comprehensive CSS in `TerminalPanel.css`. Key classes:

- `.terminal-panel`: Main container
- `.terminal-header`: Header with title and controls
- `.terminal-container`: xterm.js container
- `.terminal-search`: Search bar
- `.terminal-status`: Status bar with connection info

## Browser Compatibility

- Chrome/Edge: Full support
- Firefox: Full support
- Safari: Full support
- Mobile: Limited (terminal interactions best on desktop)

## Troubleshooting

### Terminal not fitting container

Make sure the container has a defined height:

```tsx
<TerminalPanel height="500px" />
```

### Lines not appearing

Check that you're using the correct store method:

```tsx
const addTerminalLine = useBuildStore((state) => state.addTerminalLine);
```

### Search not working

Ensure keyboard event listeners are properly attached. The component handles this automatically.

### Colors not showing

Verify ANSI codes are properly formatted and xterm's theme is configured.

## Advanced Usage

### Custom Line Formatting

Modify `formatTerminalLine` in `TerminalPanel.tsx`:

```tsx
const formatTerminalLine = (line: TerminalLine): string => {
  const timestamp = new Date(line.timestamp).toLocaleTimeString();
  // Add custom formatting here
  return `${timestamp} - ${line.content}`;
};
```

### Persistence

The buildStore uses Zustand's persist middleware, so terminal lines are saved to localStorage and restored on page reload.

To disable persistence, modify `buildStore.ts`:

```tsx
export const useBuildStore = create<BuildStore>()(
  // Remove persist() wrapper
  (set) => ({ /* ... */ })
);
```

## Contributing

When modifying the TerminalPanel:

1. Test with various log types
2. Test search and filter combinations
3. Verify ANSI colors render correctly
4. Check auto-scroll behavior
5. Test keyboard shortcuts
6. Verify mobile responsiveness
