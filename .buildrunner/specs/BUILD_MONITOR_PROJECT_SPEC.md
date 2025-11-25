# PROJECT SPEC: Build Monitor & Live Execution Dashboard

## Project Overview
**Name:** BuildRunner Build Monitor MVP
**Version:** 1.0.0
**Type:** Full-stack feature addition to BuildRunner 3.0
**Priority:** High
**Complexity:** Complex

## Executive Summary
Build a real-time build monitoring dashboard that visualizes project architecture, tracks build progress, displays live terminal output, and manages build sessions through an interactive UI. This is an MVP implementation focusing on core functionality.

## Goals
1. Enable visual project architecture representation with interactive diagrams
2. Provide real-time build monitoring with WebSocket updates
3. Stream Claude CLI output to browser for transparency
4. Track component and feature progress with visual indicators
5. Implement project initialization workflow with alias setup
6. Create seamless transition from PRD → Architecture → Build

## Technical Architecture

### Frontend Stack
- React 18 + TypeScript
- Zustand for state management
- React Flow for architecture diagrams
- xterm.js for terminal emulation
- socket.io-client for WebSocket
- react-hot-toast for notifications

### Backend Stack
- FastAPI with WebSocket support
- Watchdog for file monitoring
- Pydantic for validation
- asyncio for concurrency

### Database
- In-memory session storage (MVP)
- LocalStorage for UI state persistence

## Features

### Feature 1: Build State Store (Zustand)
**Priority:** High
**Complexity:** Medium (90 min)
**Component:** Frontend State Management

**Description:**
Central Zustand store for all build monitoring state with localStorage persistence.

**Acceptance Criteria:**
- [ ] Create ui/src/stores/buildStore.ts with Zustand
- [ ] BuildSession state with components[] and features[]
- [ ] Terminal lines circular buffer (max 1000 lines)
- [ ] WebSocket connection state tracking
- [ ] LocalStorage persistence with error recovery
- [ ] Actions: setSession, updateComponent, updateFeature, addTerminalLine
- [ ] Proper TypeScript typing from ui/src/types/build.ts
- [ ] Export useBuildStore hook

**Technical Details:**
- Use Zustand persist middleware
- Circular buffer prevents memory leaks
- WebSocket state: disconnected, connecting, connected, reconnecting, error
- Auto-timestamp management for components

**Files:**
- ui/src/stores/buildStore.ts (~300 lines)

### Feature 2: WebSocket Client Utility
**Priority:** High
**Complexity:** Medium (90 min)
**Component:** Frontend Utilities

**Description:**
Robust WebSocket client with auto-reconnect and typed message handling.

**Acceptance Criteria:**
- [ ] Create ui/src/utils/websocketClient.ts
- [ ] Auto-reconnect with exponential backoff (1s, 2s, 4s, 8s, 16s max)
- [ ] Event emitter pattern for 7 message types
- [ ] Keepalive pings every 30s
- [ ] Connection URL: ws://localhost:8080/api/build/stream/:sessionId
- [ ] Handle: connection, component_update, feature_update, checkpoint_update, terminal_output, build_progress, file_change, error
- [ ] Proper TypeScript interfaces
- [ ] Max 10 reconnect attempts

**Technical Details:**
- WebSocketClient class with on/off methods
- Typed message handlers with generics
- Clean disconnect on component unmount

**Files:**
- ui/src/utils/websocketClient.ts (~380 lines)

### Feature 3: Architecture Parser
**Priority:** High
**Complexity:** Medium (90 min)
**Component:** Frontend Utilities

**Description:**
Parse PRD data to extract architecture and generate component graph.

**Acceptance Criteria:**
- [ ] Create ui/src/utils/architectureParser.ts
- [ ] Pattern-based component detection (frontend/backend/database/service/api)
- [ ] Dependency inference rules (Frontend → API → Database)
- [ ] Extract features from PRD and map to components
- [ ] Return { components: Component[], features: Feature[] }
- [ ] Handle missing/malformed PRD sections gracefully

**Technical Details:**
- Regex patterns for component type detection
- Layered dependency inference
- Feature-to-component mapping heuristics

**Files:**
- ui/src/utils/architectureParser.ts (~390 lines)

### Feature 4: BuildMonitor Page
**Priority:** High
**Complexity:** Complex (120 min)
**Component:** Frontend Page

**Description:**
Main monitoring page with 3-zone responsive layout and real-time updates.

**Acceptance Criteria:**
- [ ] Create ui/src/pages/BuildMonitor.tsx
- [ ] Route parameter: useParams() to get projectAlias
- [ ] 3-zone CSS Grid: Header (10%), Canvas (60%), Terminal (30%)
- [ ] Resizable panels with drag handle
- [ ] WebSocket connection on mount
- [ ] Fetch session: GET /api/build/sessions/active?alias=:projectAlias
- [ ] Elapsed time updates every second
- [ ] Loading spinner during initialization
- [ ] Error boundary with retry
- [ ] Save layout to localStorage
- [ ] Clean up WebSocket on unmount

**Technical Details:**
- Use buildStore for state
- WebSocketClient integration
- Header shows: project name, alias, status badge, elapsed time, WebSocket status
- VS Code dark theme colors

**Files:**
- ui/src/pages/BuildMonitor.tsx (~320 lines)
- ui/src/pages/BuildMonitor.css (~300 lines)

### Feature 5: Project Init Modal
**Priority:** High
**Complexity:** Complex (120 min)
**Component:** Frontend Component

**Description:**
Modal for project initialization with validation and API integration.

**Acceptance Criteria:**
- [ ] Create ui/src/components/ProjectInitModal.tsx
- [ ] Props: { isOpen, onClose, prdData }
- [ ] Alias input with validation (^[a-zA-Z0-9_-]+$)
- [ ] Check conflicts: GET /api/build/aliases/:alias
- [ ] Project path input with file picker
- [ ] Pre-flight checklist (animated):
  - ✓ PRD complete
  - ✓ Architecture defined
  - ⏳ Alias available
  - ⏳ Path valid
- [ ] POST /api/build/init on submit
- [ ] Loading state with spinner
- [ ] Error handling with toast notifications
- [ ] Redirect to /build/:alias on success

**Technical Details:**
- Debounce alias validation (300ms)
- Axios for API calls
- react-hot-toast for notifications
- useNavigate() for redirect
- Accessibility: ARIA labels, keyboard nav (Esc to close)

**Files:**
- ui/src/components/ProjectInitModal.tsx (~580 lines)
- ui/src/components/ProjectInitModal.css (~580 lines)

### Feature 6: Architecture Canvas (React Flow)
**Priority:** High
**Complexity:** Complex (120 min)
**Component:** Frontend Component

**Description:**
Interactive architecture diagram using React Flow with real-time updates.

**Acceptance Criteria:**
- [ ] Create ui/src/components/ArchitectureCanvas.tsx
- [ ] Convert components to React Flow nodes
- [ ] Custom ComponentNode with progress ring and status colors
- [ ] Generate edges from dependencies
- [ ] Force-directed layout algorithm (simple physics)
- [ ] Zoom/pan controls + MiniMap
- [ ] Real-time updates from buildStore
- [ ] Click node to show details
- [ ] Status colors: gray (not_started), blue (in_progress), green (completed), red (error), yellow (blocked)
- [ ] Pulsing animation for in_progress

**Technical Details:**
- React Flow v11+
- Custom node type: 'componentNode'
- Type icons: frontend (⚛️), backend (⚙️), database (🗄️), service (🔌), api (🌐)
- Layered layout: Database → Backend → API → Frontend
- Collision detection (200px min spacing)

**Files:**
- ui/src/components/ArchitectureCanvas.tsx (~360 lines)
- ui/src/components/ArchitectureCanvas.css (~440 lines)
- ui/src/components/nodes/ComponentNode.tsx (~170 lines)

### Feature 7: Terminal Panel (xterm.js)
**Priority:** High
**Complexity:** Complex (120 min)
**Component:** Frontend Component

**Description:**
Live terminal output streaming with xterm.js and search/filter.

**Acceptance Criteria:**
- [ ] Create ui/src/components/TerminalPanel.tsx
- [ ] xterm.js with VS Code Dark theme
- [ ] FitAddon for auto-resize
- [ ] SearchAddon for Ctrl+F search
- [ ] Subscribe to buildStore.terminalLines
- [ ] Write new lines as they arrive
- [ ] Auto-scroll with pause button
- [ ] Filter dropdown (All, Info, Error, Success)
- [ ] Copy selection to clipboard
- [ ] Clear button
- [ ] ANSI color support (built-in)
- [ ] Circular buffer (1000 lines)

**Technical Details:**
- Terminal config: Fira Code font, 14px, cursor blink
- Toolbar: auto-scroll toggle, filter, search, clear
- Search bar slides down on Ctrl+F
- Format timestamps for each line
- Status bar: connection, line count, filter, auto-scroll state

**Files:**
- ui/src/components/TerminalPanel.tsx (~370 lines)
- ui/src/components/TerminalPanel.css (~380 lines)

### Feature 8: Progress Sidebar
**Priority:** Medium
**Complexity:** Medium (90 min)
**Component:** Frontend Component

**Description:**
Sidebar with component/feature progress tracking and tabs.

**Acceptance Criteria:**
- [ ] Create ui/src/components/ProgressSidebar.tsx
- [ ] Tabs: "Components" and "Features"
- [ ] ComponentProgress: list with progress bars
- [ ] FeatureProgress: grouped by component, collapsible
- [ ] Click component/feature to highlight in canvas
- [ ] Auto-expand in_progress items
- [ ] Priority badges (high/medium/low)
- [ ] Estimated vs actual time
- [ ] Task checklists
- [ ] Save active tab to localStorage

**Technical Details:**
- buildStore selectors for data
- Keyboard navigation (arrow keys)
- Responsive: 350px desktop, 280px tablet, 60px mobile (icon-only)
- Dark theme with CSS variables

**Files:**
- ui/src/components/ComponentProgress.tsx (~220 lines)
- ui/src/components/FeatureProgress.tsx (~290 lines)
- ui/src/components/ProgressSidebar.tsx (~110 lines)
- ui/src/components/ProgressSidebar.css (~660 lines)

### Feature 9: Build API Routes
**Priority:** High
**Complexity:** Complex (120 min)
**Component:** Backend API

**Description:**
REST API endpoints for build session management.

**Acceptance Criteria:**
- [ ] Create api/routes/build.py with 11 endpoints
- [ ] POST /api/build/init - Initialize project
- [ ] POST /api/build/start - Start build session
- [ ] GET /api/build/status/:sessionId - Get session status
- [ ] POST /api/build/pause - Pause session
- [ ] POST /api/build/resume - Resume session
- [ ] POST /api/build/cancel - Cancel session
- [ ] GET /api/build/sessions - List sessions (filtered)
- [ ] GET /api/build/sessions/active - Get active session by alias
- [ ] GET /api/build/stats - Aggregate statistics
- [ ] DELETE /api/build/sessions/:sessionId - Delete session
- [ ] POST /api/build/cleanup - Remove old sessions
- [ ] Pydantic models for request/response
- [ ] Proper HTTP status codes (200, 201, 400, 404, 500)
- [ ] Error handling with HTTPException

**Technical Details:**
- FastAPI router with prefix="/api/build"
- Integration with session_manager singleton
- Logging with Python logging module
- Type hints throughout

**Files:**
- api/routes/build.py (~700 lines)

### Feature 10: Session Manager
**Priority:** High
**Complexity:** Medium (90 min)
**Component:** Backend Core

**Description:**
Singleton session manager with in-memory storage.

**Acceptance Criteria:**
- [ ] Create ui/core/build/session_manager.py
- [ ] SessionManager singleton class
- [ ] BuildSession dataclass with 7 states: IDLE, INITIALIZING, RUNNING, PAUSED, COMPLETED, FAILED, CANCELLED
- [ ] In-memory sessions dict: Dict[str, BuildSession]
- [ ] Thread-safe operations with locks
- [ ] Methods: create_session, get_session, pause_session, resume_session, cancel_session, delete_session, list_sessions, get_active_session
- [ ] Calculate progress from components
- [ ] Cleanup utilities

**Technical Details:**
- Python 3.10+ with type hints
- dataclass for BuildSession
- threading.Lock for thread safety
- Export session_manager singleton instance

**Files:**
- ui/core/build/__init__.py (~25 lines)
- ui/core/build/session_manager.py (~475 lines)

### Feature 11: WebSocket Handler
**Priority:** High
**Complexity:** Complex (120 min)
**Component:** Backend WebSocket

**Description:**
FastAPI WebSocket server with session-based broadcasting.

**Acceptance Criteria:**
- [ ] Create api/websocket_handler.py
- [ ] Endpoint: @router.websocket("/api/build/stream/{session_id}")
- [ ] ConnectionManager class for active connections
- [ ] Broadcast functions for 8 message types
- [ ] Handle client messages (ping, subscribe, request_status)
- [ ] Graceful disconnect handling
- [ ] Keepalive pings every 30s
- [ ] Session-based broadcasting (only to subscribed clients)

**Technical Details:**
- FastAPI WebSocket support
- asyncio for concurrent connections
- JSON message format
- Error recovery

**Files:**
- api/websocket_handler.py (~460 lines)

### Feature 12: File Watcher & Checkpoint Parser
**Priority:** High
**Complexity:** Complex (120 min)
**Component:** Backend Core

**Description:**
File system monitoring and checkpoint parsing for progress tracking.

**Acceptance Criteria:**
- [ ] Create ui/core/build/file_watcher.py
- [ ] FileWatcher class using Watchdog
- [ ] Monitor .buildrunner/checkpoints/ and context/
- [ ] Debounce changes (100ms)
- [ ] Async callbacks for file events
- [ ] Thread-safe operation
- [ ] Create ui/core/build/checkpoint_parser.py
- [ ] Parse checkpoint JSON files
- [ ] Extract component/feature status and progress
- [ ] Calculate completion percentage
- [ ] Determine build status from phase/completion/errors
- [ ] Return structured updates for WebSocket

**Technical Details:**
- Watchdog Observer pattern
- JSON parsing with error recovery
- Integration with WebSocket broadcaster

**Files:**
- ui/core/build/file_watcher.py (~380 lines)
- ui/core/build/checkpoint_parser.py (~440 lines)

### Feature 13: Project Initializer
**Priority:** High
**Complexity:** Complex (120 min)
**Component:** Backend Core

**Description:**
Project setup automation with directory creation and BuildRunner installation.

**Acceptance Criteria:**
- [ ] Create ui/core/build/project_initializer.py
- [ ] create_project_structure() function
- [ ] Validate alias (alphanumeric, dash, underscore only)
- [ ] Check alias conflicts with alias_manager
- [ ] Create project directory and .buildrunner/ structure
- [ ] Install BuildRunner via pipx (subprocess)
- [ ] Generate PROJECT_SPEC.md from prd_data
- [ ] Register alias with alias_manager
- [ ] Create .gitignore and README.md
- [ ] Initialize git repo
- [ ] Rollback on failure (delete dirs, clear alias)
- [ ] ProjectInitError exception for errors
- [ ] 120s timeout for subprocess

**Technical Details:**
- Python subprocess for pipx install
- Markdown generation from PRD dict
- Error recovery with cleanup
- Logging for each step

**Files:**
- ui/core/build/project_initializer.py (~430 lines)

### Feature 14: Frontend Routing Integration
**Priority:** High
**Complexity:** Simple (60 min)
**Component:** Frontend Integration

**Description:**
Add BuildMonitor route to main app routing.

**Acceptance Criteria:**
- [ ] Add route to ui/src/main.tsx or ui/src/App.tsx
- [ ] Route path: /build/:projectAlias
- [ ] Element: <BuildMonitor />
- [ ] Import BuildMonitor component
- [ ] Verify routing works

**Technical Details:**
- React Router v6
- Protected route (optional for MVP)

**Files:**
- ui/src/main.tsx or ui/src/App.tsx (modify)

### Feature 15: API Server Integration
**Priority:** High
**Complexity:** Simple (60 min)
**Component:** Backend Integration

**Description:**
Integrate build routes and WebSocket into API server.

**Acceptance Criteria:**
- [ ] Import build router in api/server.py
- [ ] Import WebSocket router
- [ ] Include build router: app.include_router(build_router)
- [ ] Include WebSocket router: app.include_router(ws_router)
- [ ] Verify endpoints appear in OpenAPI docs

**Technical Details:**
- FastAPI router inclusion
- No prefix conflicts

**Files:**
- api/server.py (modify)

### Feature 16: PRD Builder "Start Build" Button
**Priority:** Medium
**Complexity:** Simple (60 min)
**Component:** Frontend Integration

**Description:**
Add "Start Build" button to PRD Builder that opens ProjectInitModal.

**Acceptance Criteria:**
- [ ] Add "Start Build" button to InteractivePRDBuilder.tsx
- [ ] Button appears after architecture section complete
- [ ] Button disabled if PRD incomplete
- [ ] Tooltip shows what's missing
- [ ] Validate: project name, overview, features, architecture
- [ ] onClick opens ProjectInitModal
- [ ] Pass prdData to modal
- [ ] Redirect happens in modal

**Technical Details:**
- Validation function checks PRD completeness
- useState for modal open/close
- Button in header or actions area

**Files:**
- ui/src/components/InteractivePRDBuilder.tsx (modify)

## Dependencies

### Frontend (npm)
```json
{
  "reactflow": "^11.11.4",
  "xterm": "^5.5.0",
  "xterm-addon-fit": "^0.10.0",
  "xterm-addon-search": "^0.15.0",
  "socket.io-client": "^4.7.5",
  "zustand": "^5.0.8",
  "react-hot-toast": "^2.4.1"
}
```

### Backend (pip)
```
fastapi>=0.104.0
websockets>=12.0
watchdog>=3.0.0
python-socketio>=5.0
```

## Testing Requirements

### Unit Tests
- [ ] buildStore state transitions
- [ ] architectureParser with various PRD formats
- [ ] WebSocket message handling
- [ ] session_manager CRUD operations
- [ ] checkpoint_parser JSON parsing

### Integration Tests
- [ ] Build initialization flow end-to-end
- [ ] WebSocket connection and messaging
- [ ] File watcher triggers updates
- [ ] Terminal streaming

### E2E Tests (Optional for MVP)
- [ ] Complete flow: PRD → Init → Build → Monitor
- [ ] Pause/resume build
- [ ] Architecture canvas updates

## Security Considerations
- Validate project paths (prevent directory traversal)
- Sanitize terminal output (xterm handles XSS)
- Rate limit WebSocket connections (future)
- Validate alias names
- No authentication in MVP (add in v2.0)

## Performance Requirements
- Page load time < 2 seconds
- WebSocket message latency < 100ms
- Terminal renders 60fps
- Canvas handles 50+ nodes smoothly
- File watcher detects changes within 1 second

## Success Metrics
- Users can visualize project architecture
- Real-time updates feel instant (<100ms)
- Terminal output is readable and searchable
- Build monitoring reduces anxiety about AI progress
- 90%+ of builds complete successfully with monitoring

## Future Enhancements (v2.0)
- Multi-project dashboard
- Build history and playback
- Team collaboration
- Cloud deployment
- AI-powered issue detection
- Performance profiling
- Cost tracking
