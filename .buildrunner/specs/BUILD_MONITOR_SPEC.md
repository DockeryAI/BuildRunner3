# PROJECT SPEC: Build Monitor & Live Execution Dashboard

## Project Overview
**Name:** BuildRunner Build Monitor
**Version:** 1.0.0
**Type:** Full-stack feature addition to BuildRunner 3.0

## Executive Summary
Add comprehensive build monitoring and live execution dashboard to BuildRunner 3.0. Users will be able to visualize project architecture, track build progress in real-time, monitor component status, view live terminal output, and manage builds through an interactive UI.

## Goals
1. Enable visual project architecture representation with interactive diagrams
2. Provide real-time build monitoring with WebSocket updates
3. Stream Claude CLI output to browser for transparency
4. Track component and feature progress with visual indicators
5. Implement project initialization workflow with alias setup
6. Create seamless transition from PRD → Architecture → Build

## Target Users
- Developers using BuildRunner to scaffold new projects
- Teams monitoring automated build processes
- Anyone wanting visibility into AI-assisted development

## Technical Architecture

### Frontend Components (React + TypeScript)

**1. Pages**
- `BuildMonitor.tsx` - Main build monitoring page with 3-zone layout

**2. Core Components**
- `ProjectInitModal.tsx` - Project setup with alias configuration
- `ArchitectureCanvas.tsx` - Interactive component diagram (React Flow)
- `ComponentProgress.tsx` - Component status sidebar
- `FeatureProgress.tsx` - Feature tracking list
- `TerminalPanel.tsx` - Live terminal output (xterm.js)
- `BuildMetrics.tsx` - Real-time metrics dashboard
- `BuildNotifications.tsx` - Toast notifications for events

**3. React Flow Nodes**
- `ComponentNode.tsx` - Custom node for architecture visualization

**4. State Management**
- `buildStore.ts` - Zustand store for build state
- WebSocket connection management
- Real-time state updates

**5. Utilities**
- `architectureParser.ts` - Parse architecture from PRD
- `graphLayout.ts` - Graph layout algorithms
- `websocketClient.ts` - WebSocket client wrapper

### Backend Components (Python + FastAPI)

**1. API Routes**
- `POST /api/build/init` - Initialize project
- `POST /api/build/start` - Start build session
- `GET /api/build/status/:sessionId` - Get build status
- `WS /api/build/stream/:sessionId` - WebSocket connection
- `POST /api/build/pause` - Pause build
- `POST /api/build/resume` - Resume build

**2. Core Modules**
- `project_initializer.py` - Create directories, install BR, generate spec
- `file_watcher.py` - Monitor .buildrunner/ for changes
- `session_manager.py` - Manage build sessions
- `checkpoint_parser.py` - Parse checkpoint files for progress
- `terminal_streamer.py` - Stream terminal output via WebSocket
- `architecture_generator.py` - Generate component graph from PRD

**3. WebSocket Handler**
- `websocket_handler.py` - Manage WebSocket connections
- Broadcast build events
- Handle client subscriptions

### Database Schema
```sql
-- Build Sessions
CREATE TABLE build_sessions (
    id UUID PRIMARY KEY,
    project_name VARCHAR(255),
    project_alias VARCHAR(100),
    project_path TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Components
CREATE TABLE components (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES build_sessions(id),
    name VARCHAR(255),
    type VARCHAR(50),
    status VARCHAR(50),
    progress INTEGER,
    dependencies JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Features
CREATE TABLE features (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES build_sessions(id),
    component_id UUID REFERENCES components(id),
    name VARCHAR(255),
    status VARCHAR(50),
    progress INTEGER,
    tasks JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Features

### Feature 1: Project Initialization Flow
**Priority:** High
**Complexity:** Medium (90 min)

**Description:**
Modal-based project setup that collects alias, validates paths, creates directory structure, installs BuildRunner, and generates PROJECT_SPEC.md from PRD data.

**Acceptance Criteria:**
- [ ] Modal opens when user clicks "Start Build" in PRD Builder
- [ ] Alias input validates format (alphanumeric, dash, underscore)
- [ ] Alias checks for conflicts with existing aliases
- [ ] Project path selection with file browser
- [ ] Pre-flight checklist shows: PRD complete, architecture defined, dependencies mapped
- [ ] Creates project directory structure
- [ ] Installs BuildRunner via pipx
- [ ] Generates PROJECT_SPEC.md from PRD data
- [ ] Sets up alias mapping in ~/.buildrunner/aliases.json
- [ ] Redirects to Build Monitor on success

**Technical Details:**
- Use existing alias_manager.py for alias operations
- Call `pipx install buildrunner` via subprocess
- Generate markdown from PRD state object
- Handle errors gracefully with user-friendly messages

**Files:**
- `ui/src/components/ProjectInitModal.tsx`
- `ui/src/components/ProjectInitModal.css`
- `api/build_routes.py` (new)
- `core/build/project_initializer.py` (new)

### Feature 2: Build Monitor Page & Layout
**Priority:** High
**Complexity:** Complex (120 min)

**Description:**
Main monitoring page with responsive 3-zone layout: header, architecture canvas (center), and sliding terminal panel (bottom).

**Acceptance Criteria:**
- [ ] Route: `/build/:projectAlias`
- [ ] Header shows project name, alias, status indicator
- [ ] Center canvas takes 60% of viewport height
- [ ] Terminal panel slides up from bottom, resizable
- [ ] Drag handles for resizing panels
- [ ] Layout preferences saved to localStorage
- [ ] Responsive design for different screen sizes
- [ ] Keyboard shortcuts (Ctrl+T for terminal, Ctrl+A for architecture)

**Technical Details:**
- React Router for routing
- CSS Grid for layout
- localStorage for preferences
- Keyboard event listeners

**Files:**
- `ui/src/pages/BuildMonitor.tsx`
- `ui/src/styles/BuildMonitor.css`

### Feature 3: Architecture Canvas with React Flow
**Priority:** High
**Complexity:** Complex (120 min)

**Description:**
Interactive architecture diagram showing components as nodes with dependency edges. Nodes display status via colors and update in real-time.

**Acceptance Criteria:**
- [ ] Parses architecture from PRD technical section
- [ ] Creates nodes for each component (Frontend, Backend, Database, Services)
- [ ] Draws edges showing dependencies
- [ ] Node colors indicate status: gray (not started), blue (in progress), green (complete), red (error)
- [ ] Pulsing animation for in-progress nodes
- [ ] Click node to see details
- [ ] Double-click to zoom to node
- [ ] Hover shows metrics (time spent, LOC)
- [ ] Auto-layout with force-directed graph
- [ ] Manual node repositioning (persisted)
- [ ] Zoom/pan controls
- [ ] Minimap in corner

**Technical Details:**
- React Flow v11+
- Custom node components
- D3 force-directed layout for initial positioning
- WebSocket updates trigger node state changes

**Files:**
- `ui/src/components/ArchitectureCanvas.tsx`
- `ui/src/components/ArchitectureCanvas.css`
- `ui/src/components/nodes/ComponentNode.tsx`
- `ui/src/components/nodes/ComponentNode.css`
- `ui/src/utils/graphLayout.ts`
- `ui/src/utils/architectureParser.ts`

### Feature 4: Component & Feature Progress Tracking
**Priority:** High
**Complexity:** Medium (90 min)

**Description:**
Left sidebar showing progress bars for components and collapsible feature lists with task checkboxes.

**Acceptance Criteria:**
- [ ] Component progress bars show 0-100% completion
- [ ] Progress colors match status (blue/green/red)
- [ ] Feature list groups by component
- [ ] Each feature shows task checklist
- [ ] Tasks auto-check as completed
- [ ] Click component/feature to highlight in canvas
- [ ] Estimated vs actual time shown
- [ ] Critical path highlighted

**Technical Details:**
- Parse checkpoint files for completion percentage
- Calculate progress from file creation timestamps
- WebSocket updates for real-time changes

**Files:**
- `ui/src/components/ComponentProgress.tsx`
- `ui/src/components/FeatureProgress.tsx`
- `ui/src/components/ProgressSidebar.css`

### Feature 5: Terminal Panel with Live Streaming
**Priority:** High
**Complexity:** Complex (120 min)

**Description:**
xterm.js-based terminal that streams Claude CLI output in real-time via WebSocket.

**Acceptance Criteria:**
- [ ] Terminal displays Claude CLI output with formatting
- [ ] ANSI color codes rendered correctly
- [ ] Auto-scroll with pause button
- [ ] Search functionality (Ctrl+F)
- [ ] Copy text selection
- [ ] Filter by log level (info, error, success)
- [ ] Timestamps on each line
- [ ] Clear button
- [ ] Export logs to file
- [ ] Terminal resizes with panel

**Technical Details:**
- xterm.js for terminal rendering
- WebSocket for streaming
- Buffer management for large outputs
- Virtual scrolling for performance

**Files:**
- `ui/src/components/TerminalPanel.tsx`
- `ui/src/components/TerminalPanel.css`
- `core/build/terminal_streamer.py`

### Feature 6: WebSocket Server & File Watcher
**Priority:** High
**Complexity:** Complex (120 min)

**Description:**
FastAPI WebSocket server that watches .buildrunner/ directory and broadcasts build events to connected clients.

**Acceptance Criteria:**
- [ ] WebSocket endpoint: `ws://localhost:8080/api/build/stream/:sessionId`
- [ ] Clients can subscribe to build session
- [ ] File watcher monitors .buildrunner/checkpoints/
- [ ] File watcher monitors .buildrunner/context/
- [ ] Parses checkpoint JSON for component status
- [ ] Broadcasts component status changes
- [ ] Broadcasts feature progress updates
- [ ] Streams terminal output line-by-line
- [ ] Handles client disconnections gracefully
- [ ] Reconnection logic on client side
- [ ] Message queue for offline clients

**Technical Details:**
- FastAPI WebSocket support
- Watchdog library for file monitoring
- JSON parsing for checkpoints
- asyncio for concurrent connections

**Files:**
- `api/websocket_handler.py`
- `core/build/file_watcher.py`
- `core/build/checkpoint_parser.py`
- `core/build/session_manager.py`

### Feature 7: Build API Endpoints
**Priority:** High
**Complexity:** Medium (90 min)

**Description:**
REST API endpoints for build session management.

**Acceptance Criteria:**
- [ ] POST /api/build/init creates project and installs BR
- [ ] POST /api/build/start launches Claude CLI process
- [ ] GET /api/build/status/:sessionId returns session state
- [ ] POST /api/build/pause sends SIGSTOP to Claude process
- [ ] POST /api/build/resume sends SIGCONT to Claude process
- [ ] All endpoints return consistent JSON responses
- [ ] Error handling with appropriate status codes

**Technical Details:**
- FastAPI route handlers
- Subprocess management for Claude CLI
- Session state stored in memory (dict)
- Could add Redis for production

**Files:**
- `api/build_routes.py`
- `core/build/session_manager.py`

### Feature 8: PRD Builder Integration
**Priority:** High
**Complexity:** Simple (60 min)

**Description:**
Add "Start Build" button to PRD Builder that validates completeness and launches ProjectInitModal.

**Acceptance Criteria:**
- [ ] "Start Build" button appears after architecture section complete
- [ ] Button disabled if PRD incomplete
- [ ] Tooltip shows what's missing
- [ ] Validates: project name, overview, features, technical architecture
- [ ] Clicking opens ProjectInitModal
- [ ] Passes PRD data to modal
- [ ] Redirects to /build/:alias after successful init

**Technical Details:**
- Add button to InteractivePRDBuilder.tsx
- Validation function checks PRD completeness
- React Router navigation

**Files:**
- `ui/src/components/InteractivePRDBuilder.tsx` (modify)
- `ui/src/utils/prdValidator.ts` (new)

### Feature 9: Real-time Notifications
**Priority:** Medium
**Complexity:** Simple (60 min)

**Description:**
Toast notifications for build events with optional sound and browser notifications.

**Acceptance Criteria:**
- [ ] Toast appears for: component complete, test pass/fail, build error
- [ ] Toasts auto-dismiss after 5 seconds
- [ ] Click toast to dismiss early
- [ ] Option to enable sound alerts
- [ ] Option to enable browser notifications
- [ ] Notification preferences saved

**Technical Details:**
- Use react-hot-toast library
- Browser Notification API
- Web Audio API for sounds

**Files:**
- `ui/src/components/BuildNotifications.tsx`
- `ui/src/utils/notificationManager.ts`

### Feature 10: Build Metrics Dashboard
**Priority:** Medium
**Complexity:** Simple (60 min)

**Description:**
Real-time metrics panel showing build statistics.

**Acceptance Criteria:**
- [ ] Shows total/completed components
- [ ] Shows total/completed features
- [ ] Shows elapsed time
- [ ] Shows estimated time remaining
- [ ] Shows lines of code written
- [ ] Shows tests written/passing
- [ ] Metrics update in real-time
- [ ] Expandable details panel

**Technical Details:**
- Calculate from checkpoint data
- WebSocket updates
- Simple card-based layout

**Files:**
- `ui/src/components/BuildMetrics.tsx`
- `ui/src/components/BuildMetrics.css`

## Dependencies

### Frontend
- reactflow@11.x - Interactive diagrams
- xterm@5.x - Terminal emulation
- xterm-addon-fit - Terminal fitting
- socket.io-client@4.x - WebSocket client
- zustand@4.x - State management
- react-hot-toast - Notifications

### Backend
- fastapi@0.104+ - API framework
- websockets@12.x - WebSocket support
- watchdog@3.x - File system monitoring
- python-socketio@5.x - Socket.IO server

## Testing Requirements

### Unit Tests
- [ ] architectureParser.ts - Parse PRD architecture
- [ ] graphLayout.ts - Layout algorithm
- [ ] project_initializer.py - Project setup
- [ ] checkpoint_parser.py - Parse checkpoints
- [ ] file_watcher.py - File monitoring

### Integration Tests
- [ ] Build initialization flow end-to-end
- [ ] WebSocket connection and messaging
- [ ] File watcher triggers status updates
- [ ] Terminal streaming

### E2E Tests
- [ ] Complete flow: PRD → Init → Build → Monitor
- [ ] User can pause/resume build
- [ ] Architecture canvas updates in real-time

## Security Considerations
- Validate project paths to prevent directory traversal
- Sanitize terminal output to prevent XSS
- Rate limit WebSocket connections
- Authenticate WebSocket connections (future)
- Validate alias names to prevent conflicts

## Performance Requirements
- Page load time < 2 seconds
- WebSocket message latency < 100ms
- Terminal renders 60fps with streaming
- Architecture canvas handles 50+ nodes smoothly
- File watcher detects changes within 1 second

## Deployment
- Frontend: Electron app (already configured)
- Backend: FastAPI server on localhost:8080
- No external dependencies required
- Works offline

## Success Metrics
- Users can visualize project architecture
- Real-time updates feel instant (<100ms latency)
- Terminal output is readable and searchable
- Build monitoring reduces anxiety about AI progress
- 90%+ of builds complete successfully with monitoring

## Future Enhancements (v2.0)
- Multi-project monitoring (dashboard view)
- Build history and playback
- Team collaboration features
- Cloud deployment option
- Integration with CI/CD pipelines
- AI-powered issue detection
- Performance profiling
- Cost tracking for API usage
