# Terminal Panel Integration Guide

## Overview

The TerminalPanel component provides a production-ready terminal interface with xterm.js for live streaming build output.

## Files Created

1. **`/src/stores/buildStore.ts`** - Zustand store for build state management
2. **`/src/components/TerminalPanel.tsx`** - Main terminal component
3. **`/src/components/TerminalPanel.css`** - VS Code-inspired styling
4. **`/src/components/TerminalDemo.tsx`** - Integration example
5. **`/src/components/TerminalPanel.README.md`** - Comprehensive documentation

## Quick Start

### 1. Import and Use

```tsx
import { TerminalPanel } from './components/TerminalPanel';

function MyBuildMonitor() {
  return (
    <div>
      <h1>Build Output</h1>
      <TerminalPanel height="600px" />
    </div>
  );
}
```

### 2. Add Terminal Lines

```tsx
import { useBuildStore } from './stores/buildStore';

function MyComponent() {
  const addTerminalLine = useBuildStore((state) => state.addTerminalLine);

  const logMessage = (type: 'info' | 'error' | 'success', content: string) => {
    addTerminalLine({
      timestamp: Date.now(),
      type,
      content,
    });
  };

  return (
    <button onClick={() => logMessage('success', 'Build completed!')}>
      Complete Build
    </button>
  );
}
```

### 3. WebSocket Integration

```tsx
import { useWebSocket } from './hooks/useWebSocket';
import { useBuildStore } from './stores/buildStore';

function BuildMonitor() {
  const addTerminalLine = useBuildStore((state) => state.addTerminalLine);

  useWebSocket({
    onMessage: (message) => {
      if (message.type === 'terminal_output') {
        addTerminalLine({
          timestamp: Date.now(),
          type: message.level || 'info',
          content: message.content,
        });
      }
    },
  });

  return <TerminalPanel />;
}
```

## Features

### Built-in Controls

- **Filter by type**: Info, Error, Success, All
- **Search**: Ctrl+F or Search button
- **Auto-scroll**: Pause/Resume button
- **Copy**: Select text and click Copy
- **Clear**: Clear all terminal output

### ANSI Color Support

The terminal automatically formats output with colors:
- Errors: Red
- Success: Green
- Info: Cyan
- Stdout: White
- Timestamps: Gray

### Keyboard Shortcuts

- `Ctrl+F` / `Cmd+F`: Open search
- `Escape`: Close search
- `Enter`: Execute search
- `Ctrl+C` / `Cmd+C`: Copy selection

## Store API

```tsx
interface BuildStore {
  // State
  terminalLines: TerminalLine[];
  session: BuildSession | null;
  websocket: WebSocketState;

  // Terminal actions
  addTerminalLine: (line: Omit<TerminalLine, 'id'>) => void;
  clearTerminal: () => void;

  // Session actions
  setSession: (session: BuildSession) => void;
  clearSession: () => void;
  updateSessionStatus: (status: BuildSession['status']) => void;

  // Component/Feature actions
  updateComponent: (id: string, updates: Partial<Component>) => void;
  updateFeature: (id: string, updates: Partial<Feature>) => void;

  // WebSocket actions
  setWebSocketConnected: (connected: boolean) => void;
  setWebSocketError: (error: string | null) => void;
}
```

## TypeScript Types

```tsx
interface TerminalLine {
  id: string;
  timestamp: number;
  type: 'stdout' | 'stderr' | 'info' | 'error' | 'success';
  content: string;
}
```

## Integration Examples

### Example 1: Basic Usage

```tsx
import { TerminalPanel } from './components/TerminalPanel';

export function BuildOutput() {
  return (
    <div className="build-output">
      <h2>Build Logs</h2>
      <TerminalPanel height="500px" />
    </div>
  );
}
```

### Example 2: With Session Management

```tsx
import { TerminalPanel } from './components/TerminalPanel';
import { useBuildStore } from './stores/buildStore';

export function BuildSession() {
  const session = useBuildStore((state) => state.session);
  const clearSession = useBuildStore((state) => state.clearSession);

  if (!session) {
    return <div>No active build session</div>;
  }

  return (
    <div>
      <h2>Session: {session.projectName}</h2>
      <p>Status: {session.status}</p>
      <button onClick={clearSession}>End Session</button>
      <TerminalPanel height="600px" />
    </div>
  );
}
```

### Example 3: Complete Build Monitor

```tsx
import { useEffect } from 'react';
import { TerminalPanel } from './components/TerminalPanel';
import { useBuildStore } from './stores/buildStore';
import { useWebSocket } from './hooks/useWebSocket';

export function CompleteBuildMonitor() {
  const addTerminalLine = useBuildStore((state) => state.addTerminalLine);
  const setWebSocketConnected = useBuildStore((state) => state.setWebSocketConnected);
  const websocket = useBuildStore((state) => state.websocket);

  const { isConnected, lastMessage } = useWebSocket({
    onConnect: () => {
      setWebSocketConnected(true);
      addTerminalLine({
        timestamp: Date.now(),
        type: 'success',
        content: 'Connected to BuildRunner backend',
      });
    },
    onDisconnect: () => {
      setWebSocketConnected(false);
      addTerminalLine({
        timestamp: Date.now(),
        type: 'error',
        content: 'Disconnected from BuildRunner backend',
      });
    },
  });

  useEffect(() => {
    if (!lastMessage) return;

    // Route messages to terminal
    switch (lastMessage.type) {
      case 'build_output':
        addTerminalLine({
          timestamp: Date.now(),
          type: lastMessage.level || 'stdout',
          content: lastMessage.message,
        });
        break;

      case 'error':
        addTerminalLine({
          timestamp: Date.now(),
          type: 'error',
          content: `ERROR: ${lastMessage.message}`,
        });
        break;
    }
  }, [lastMessage, addTerminalLine]);

  return (
    <div className="build-monitor">
      <div className="status-bar">
        <span>Connection: {websocket.connected ? '🟢' : '🔴'}</span>
        {websocket.error && <span className="error">{websocket.error}</span>}
      </div>
      <TerminalPanel height="700px" />
    </div>
  );
}
```

## Performance Notes

- Terminal lines are limited to 1000 most recent entries (configurable in buildStore)
- Uses xterm.js's efficient rendering engine
- FitAddon automatically resizes terminal to container
- State persists to localStorage for session recovery

## Styling Customization

The terminal uses CSS variables for easy theming. Override in your app's CSS:

```css
.terminal-panel {
  --terminal-bg: #1e1e1e;
  --terminal-fg: #d4d4d4;
  --terminal-accent: #0e639c;
}
```

## Testing

Run the included demo:

```tsx
import { TerminalDemo } from './components/TerminalDemo';

function App() {
  return <TerminalDemo />;
}
```

## Next Steps

1. **Connect to WebSocket**: Update the WebSocket message handler to route build output
2. **Customize Filters**: Add custom log types or filtering logic
3. **Add Persistence**: Configure what gets saved to localStorage
4. **Enhance Search**: Add regex support or search history
5. **Add Export**: Allow users to download terminal logs

## Troubleshooting

**Terminal not visible?**
- Ensure container has defined height
- Check that xterm.css is imported

**Lines not appearing?**
- Verify buildStore is properly configured
- Check that addTerminalLine is being called
- Inspect browser console for errors

**Search not working?**
- Ensure Ctrl+F handler is not blocked by parent
- Check that keyboard events are reaching the component

**Performance issues?**
- Reduce line limit in buildStore (default: 1000)
- Clear terminal periodically with clearTerminal()

## License

Part of BuildRunner 3.2 project.
