# Build Monitor State Management Layer

Complete state management implementation for the Build Monitor feature using Zustand, WebSocket client, and architecture parsing utilities.

## Overview

This implementation provides three core modules:

1. **buildStore.ts** - Zustand store for centralized state management
2. **websocketClient.ts** - WebSocket client with auto-reconnect
3. **architectureParser.ts** - PRD parsing and architecture extraction

## Files Created

### 1. `/Users/byronhudson/Projects/BuildRunner3/ui/src/stores/buildStore.ts` (232 lines)

Zustand store managing:
- Build session state
- Component tracking with status
- Feature tracking with tasks
- Terminal output history (max 1000 lines)
- WebSocket connection state
- LocalStorage persistence (session + terminal only)

**Key Features:**
- TypeScript typed with strict type safety
- Persistent storage using `zustand/middleware`
- Selective persistence (excludes WebSocket state)
- Helper selectors for derived state
- Immutable state updates

**Actions:**
```typescript
// Session
setSession(session: BuildSession)
clearSession()
updateSessionStatus(status)

// Components
updateComponent(id, updates)
setComponents(components)
setCurrentComponent(id)

// Features
updateFeature(id, updates)
setFeatures(features)
setCurrentFeature(id)

// Terminal
addTerminalLine(line)
clearTerminal()

// WebSocket
setWebSocketConnected(connected)
setWebSocketReconnecting(reconnecting)
setWebSocketError(error)
```

**Selectors:**
```typescript
selectComponentById(id)
selectFeatureById(id)
selectFeaturesByComponent(componentId)
selectCurrentComponent()
selectCurrentFeature()
selectTerminalLinesByType(type)
```

### 2. `/Users/byronhudson/Projects/BuildRunner3/ui/src/utils/websocketClient.ts` (276 lines)

WebSocket client wrapper with:
- Auto-reconnect with exponential backoff
- Connection state management
- Event-based message handling
- Ping/pong keepalive
- Subscribe/unsubscribe to sessions

**Message Types:**
```typescript
// Incoming
WSComponentUpdate
WSFeatureUpdate
WSTerminalOutput
WSSessionStatus
WSError

// Outgoing
WSSubscribe
WSUnsubscribe
WSPing
```

**API:**
```typescript
const client = new WebSocketClient({
  onMessage: (msg) => {},
  onConnect: () => {},
  onDisconnect: () => {},
  onError: (err) => {},
  onReconnecting: () => {},
  reconnectInterval: 3000,
  maxReconnectAttempts: 5,
  pingInterval: 30000,
});

client.connect(sessionId);
client.disconnect();
client.subscribe(sessionId);
client.unsubscribe();
client.ping();

client.isConnected();
client.getSessionId();
client.getReconnectAttempts();
```

### 3. `/Users/byronhudson/Projects/BuildRunner3/ui/src/utils/architectureParser.ts` (334 lines)

Parses PRD content to extract:
- System architecture components
- Component types (frontend, backend, API, database, service)
- Dependencies between components
- Feature-to-component mappings

**API:**
```typescript
// Parse architecture from PRD
const components = parseArchitecture({
  content: prdMarkdown,
  features: [] // optional
});

// Map features to components
const featureMap = mapFeaturesToComponents(features, components);
```

**Component Detection:**
- Pattern-based keyword matching
- Context-aware type inference
- Implicit dependency detection
- Markdown section parsing

## Usage Examples

### Basic Integration

```typescript
import { useBuildStore } from './stores/buildStore';
import { WebSocketClient } from './utils/websocketClient';

function BuildMonitor({ sessionId }: { sessionId: string }) {
  const {
    session,
    terminalLines,
    websocket,
    updateComponent,
    updateFeature,
    addTerminalLine,
    setWebSocketConnected,
  } = useBuildStore();

  useEffect(() => {
    const ws = new WebSocketClient({
      onMessage: (msg) => {
        if (msg.type === 'component_update') {
          updateComponent(msg.componentId, msg.updates);
        } else if (msg.type === 'terminal_output') {
          addTerminalLine(msg.line);
        }
      },
      onConnect: () => setWebSocketConnected(true),
      onDisconnect: () => setWebSocketConnected(false),
    });

    ws.connect(sessionId);

    return () => ws.disconnect();
  }, [sessionId]);

  return (
    <div>
      <h1>{session?.projectName}</h1>
      <p>Status: {session?.status}</p>
      <p>WebSocket: {websocket.connected ? 'Connected' : 'Disconnected'}</p>

      {/* Render components, features, terminal */}
    </div>
  );
}
```

### Parse Architecture from PRD

```typescript
import { parseArchitecture } from './utils/architectureParser';
import { useBuildStore } from './stores/buildStore';

function InitializeSession() {
  const { setComponents, setSession } = useBuildStore();

  const handlePRDUpload = async (file: File) => {
    const content = await file.text();

    // Parse architecture
    const components = parseArchitecture({ content });

    // Create session
    const session: BuildSession = {
      id: `session-${Date.now()}`,
      projectName: 'My Project',
      projectAlias: 'my-project',
      projectPath: '/path',
      startTime: Date.now(),
      status: 'initializing',
      components,
      features: [],
    };

    setSession(session);
    setComponents(components);
  };

  return <input type="file" onChange={(e) => handlePRDUpload(e.target.files![0])} />;
}
```

### Using Selectors

```typescript
import { useBuildStore, selectCurrentComponent, selectFeaturesByComponent } from './stores/buildStore';

function ComponentDetails({ componentId }: { componentId: string }) {
  const currentComponent = useBuildStore(selectCurrentComponent);
  const features = useBuildStore(selectFeaturesByComponent(componentId));

  return (
    <div>
      <h2>{currentComponent?.name}</h2>
      <p>Status: {currentComponent?.status}</p>
      <p>Progress: {currentComponent?.progress}%</p>

      <h3>Features</h3>
      <ul>
        {features.map(f => (
          <li key={f.id}>{f.name} - {f.status}</li>
        ))}
      </ul>
    </div>
  );
}
```

## Type Definitions

All types are defined in `/Users/byronhudson/Projects/BuildRunner3/ui/src/types/build.ts`:

```typescript
BuildSession
Component
ComponentStatus
Feature
Task
TerminalLine
BuildMetrics
```

## State Persistence

The store automatically persists to localStorage:
- Key: `buildrunner-build-store`
- Persisted: `session`, `terminalLines`
- Excluded: `websocket` state (ephemeral)

Clear persisted state:
```typescript
localStorage.removeItem('buildrunner-build-store');
```

## WebSocket Protocol

**Endpoint:** `ws://localhost:8080/api/build/stream/:sessionId`

**Incoming Messages:**
```json
// Component Update
{
  "type": "component_update",
  "componentId": "frontend",
  "updates": {
    "status": "in_progress",
    "progress": 45
  }
}

// Feature Update
{
  "type": "feature_update",
  "featureId": "auth-login",
  "updates": {
    "status": "completed",
    "progress": 100
  }
}

// Terminal Output
{
  "type": "terminal_output",
  "line": {
    "timestamp": 1234567890,
    "type": "stdout",
    "content": "Building project..."
  }
}

// Session Status
{
  "type": "session_status",
  "status": "running"
}

// Error
{
  "type": "error",
  "message": "Build failed"
}
```

**Outgoing Messages:**
```json
// Subscribe
{
  "type": "subscribe",
  "sessionId": "session-123"
}

// Unsubscribe
{
  "type": "unsubscribe"
}

// Ping
{
  "type": "ping"
}
```

## Testing

Example usage is provided in:
`/Users/byronhudson/Projects/BuildRunner3/ui/src/examples/useBuildMonitor.example.ts`

Run tests:
```bash
npm test
```

Build verification:
```bash
npm run build
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     React Components                     │
│  (BuildMonitor, ComponentCard, TerminalView, etc.)      │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ↓
┌─────────────────────────────────────────────────────────┐
│                   buildStore (Zustand)                   │
│  - session: BuildSession                                 │
│  - terminalLines: TerminalLine[]                         │
│  - websocket: { connected, reconnecting, error }         │
│  - actions: update*, set*, add*                          │
│  - selectors: select*                                    │
└──────────┬────────────────────────────────────┬─────────┘
           │                                    │
           ↓                                    ↓
┌──────────────────────────┐    ┌──────────────────────────┐
│  websocketClient.ts      │    │  architectureParser.ts   │
│  - Auto-reconnect        │    │  - Parse PRD             │
│  - Event handling        │    │  - Extract components    │
│  - Subscribe/ping        │    │  - Detect dependencies   │
└────────┬─────────────────┘    │  - Map features          │
         │                       └──────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│          Backend WebSocket Server (Port 8080)            │
│        ws://localhost:8080/api/build/stream/:id          │
└─────────────────────────────────────────────────────────┘
```

## Best Practices

1. **State Updates**: Always use store actions, never mutate state directly
2. **WebSocket**: Use single client instance per session
3. **Selectors**: Use selectors for derived state to optimize re-renders
4. **Persistence**: Clear persisted state on logout/session end
5. **Error Handling**: Always check websocket.error state
6. **Terminal Lines**: Automatically limited to 1000 most recent lines

## Next Steps

1. Create React components that consume this state
2. Implement backend WebSocket server at `/api/build/stream/:id`
3. Add unit tests for store actions and selectors
4. Add integration tests for WebSocket client
5. Create Storybook stories for UI components

## Dependencies

- `zustand` (^5.0.8) - State management
- `react` (^18.2.0) - UI framework
- TypeScript - Type safety

## File Structure

```
ui/src/
├── stores/
│   └── buildStore.ts          (232 lines)
├── utils/
│   ├── websocketClient.ts     (276 lines)
│   └── architectureParser.ts  (334 lines)
├── types/
│   └── build.ts               (existing)
└── examples/
    └── useBuildMonitor.example.ts  (reference)
```

**Total:** 842 lines of production-ready TypeScript

---

*Created: 2025-01-19*
*Build Monitor State Management Layer v1.0*
