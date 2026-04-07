# Build Monitor Implementation Plan

## Overview
Comprehensive build monitoring and execution system for BuildRunner 3.0

## Phase 1: Foundation (Implemented)
- [x] Install dependencies (reactflow, xterm, socket.io-client)
- [x] Create type definitions (build.ts)

## Phase 2: Core Components (In Progress)

### 2.1 BuildMonitor Page
**File:** `ui/src/pages/BuildMonitor.tsx`
- 3-zone layout (header, canvas, terminal)
- State management for build session
- WebSocket connection
- Route: `/build/:projectAlias`

### 2.2 Project Initialization Modal
**File:** `ui/src/components/ProjectInitModal.tsx`
- Alias input and validation
- Project path selection
- Pre-flight checklist
- Directory creation
- BuildRunner installation via API call
- PROJECT_SPEC.md generation from PRD

### 2.3 Architecture Canvas
**File:** `ui/src/components/ArchitectureCanvas.tsx`
- React Flow integration
- Component nodes with status colors
- Dependency edges
- Interactive (click, hover, zoom)
- Auto-layout algorithm
- Real-time status updates

### 2.4 Progress Tracking
**Files:**
- `ui/src/components/ComponentProgress.tsx`
- `ui/src/components/FeatureProgress.tsx`
- Left sidebar with progress bars
- Component and feature lists
- Click to focus in canvas

### 2.5 Terminal Panel
**File:** `ui/src/components/TerminalPanel.tsx`
- xterm.js integration
- WebSocket streaming
- Syntax highlighting
- Search/filter
- Auto-scroll with pause

## Phase 3: Backend Integration

### 3.1 WebSocket Server
**File:** `api/websocket_handler.py`
- FastAPI WebSocket endpoint
- Build session management
- File watcher for `.buildrunner/` directory
- Terminal output streaming
- Component status updates

### 3.2 Build API Endpoints
**File:** `api/build_routes.py`
```
POST /api/build/init - Initialize project
POST /api/build/start - Start build session
GET /api/build/status/:sessionId - Get build status
WS /api/build/stream/:sessionId - WebSocket connection
POST /api/build/pause - Pause build
POST /api/build/resume - Resume build
```

### 3.3 File Watcher
**File:** `core/build/file_watcher.py`
- Monitor `.buildrunner/checkpoints/`
- Monitor `.buildrunner/context/`
- Parse checkpoint files for progress
- Emit events via WebSocket

### 3.4 Project Initializer
**File:** `core/build/project_initializer.py`
- Create directory structure
- Install BuildRunner via subprocess
- Generate PROJECT_SPEC.md from PRD data
- Set up alias mapping
- Initialize git repository

## Phase 4: PRD Builder Integration

### 4.1 Start Build Flow
**File:** `ui/src/components/InteractivePRDBuilder.tsx`
- Add "Start Build" button (after architecture complete)
- Validate PRD completeness
- Launch ProjectInitModal
- Redirect to BuildMonitor

### 4.2 Architecture Extraction
**File:** `ui/src/utils/architectureParser.ts`
- Parse technical architecture from PRD
- Extract components and dependencies
- Generate initial component graph
- Map features to components

## Phase 5: Real-time Updates

### 5.1 Build State Management
**File:** `ui/src/stores/buildStore.ts`
- Zustand store for build state
- WebSocket connection management
- Real-time updates
- Persisted to localStorage

### 5.2 Event Handlers
- Component status changes
- Feature progress updates
- Terminal output streaming
- Error notifications

## Phase 6: Visualizations

### 6.1 Node Renderers
**Files:**
- `ui/src/components/nodes/ComponentNode.tsx`
- Custom React Flow nodes
- Status indicators (colors, icons, animations)
- Progress rings
- Hover tooltips

### 6.2 Layout Engine
**File:** `ui/src/utils/graphLayout.ts`
- Force-directed layout (D3)
- Hierarchical layout option
- Layer-based positioning
- Collision detection

## Phase 7: Polish

### 7.1 Notifications
**File:** `ui/src/components/BuildNotifications.tsx`
- Toast notifications for events
- Sound alerts (optional)
- Browser notifications

### 7.2 Metrics Dashboard
**File:** `ui/src/components/BuildMetrics.tsx`
- Time tracking
- Lines of code counter
- Test coverage
- Build velocity

### 7.3 Error Handling
- Graceful WebSocket reconnection
- Build failure recovery
- User-friendly error messages

## Implementation Order

1. **Day 1-2:** Build Monitor page + basic layout
2. **Day 3-4:** Project Init Modal + API endpoints
3. **Day 5-6:** Architecture Canvas with React Flow
4. **Day 7-8:** Terminal Panel + WebSocket
5. **Day 9-10:** Progress tracking components
6. **Day 11-12:** File watcher + real-time updates
7. **Day 13-14:** PRD Builder integration
8. **Day 15:** Polish + testing

## Files to Create (Total: ~25 files)

### Frontend (15 files)
1. `ui/src/types/build.ts` ✓
2. `ui/src/pages/BuildMonitor.tsx`
3. `ui/src/components/ProjectInitModal.tsx`
4. `ui/src/components/ArchitectureCanvas.tsx`
5. `ui/src/components/ComponentProgress.tsx`
6. `ui/src/components/FeatureProgress.tsx`
7. `ui/src/components/TerminalPanel.tsx`
8. `ui/src/components/BuildNotifications.tsx`
9. `ui/src/components/BuildMetrics.tsx`
10. `ui/src/components/nodes/ComponentNode.tsx`
11. `ui/src/stores/buildStore.ts`
12. `ui/src/utils/architectureParser.ts`
13. `ui/src/utils/graphLayout.ts`
14. `ui/src/styles/BuildMonitor.css`
15. `ui/src/styles/ArchitectureCanvas.css`

### Backend (10 files)
1. `api/build_routes.py`
2. `api/websocket_handler.py`
3. `core/build/project_initializer.py`
4. `core/build/file_watcher.py`
5. `core/build/session_manager.py`
6. `core/build/checkpoint_parser.py`
7. `core/build/terminal_streamer.py`
8. `core/build/architecture_generator.py`
9. `tests/test_build_routes.py`
10. `tests/test_project_initializer.py`

## Current Status
- ✅ Phase 1 complete
- 🔄 Phase 2 in progress (2.1 starting)
- ⏳ Phases 3-7 pending
