# BuildRunner v3.2 Plan Update

## Changes Made

### ✅ Created New v3.2 Plan
**File:** `.buildrunner/BUILD_PLAN_V3.2_AGENTS_UI.md`

### ✅ Updated Main Build Plan
**File:** `BUILD_PLAN_V3.1-V3.4_ATOMIC.md`
- Added v3.2 section (Weeks 7-10)
- Placeholder sections for v3.3 and v3.4

---

## v3.2 Feature Summary

### 🤖 Multi-Agent Task Distribution System

**NEW** - Inspired by Claude Code's `/agents` capability

**Agent Types (5 Specialized):**
1. **Coding Agent** - Production code (Sonnet, max 3 concurrent)
2. **Testing Agent** - Test writing (Sonnet, max 2 concurrent)
3. **Security Agent** - Security scanning (Opus, max 1 concurrent)
4. **Documentation Agent** - Technical docs (Haiku, max 2 concurrent)
5. **Refactoring Agent** - Code improvements (Sonnet, max 1 concurrent)

**Key Components:**
- `core/agents/agent_registry.py` - Agent type management
- `core/agents/capabilities.py` - Capability matching
- `core/agents/task_classifier.py` - Intelligent task routing
- `core/agents/pool_manager.py` - Concurrent agent pool
- `core/agents/profiles/*.yaml` - Agent specialization configs

**Benefits:**
- ⚡ **Faster builds**: Parallel specialized execution
- 🎯 **Better quality**: Domain experts for each task type
- 💰 **Cost optimization**: Right model tier for right task (Haiku/Sonnet/Opus)
- 📈 **Scalability**: Dynamic agent scaling

**Integration:**
- Builds on Week 1 Build A (parallel execution foundation)
- Uses telemetry for agent event tracking
- Uses routing for model tier selection per agent
- Orchestrator automatically classifies and routes tasks

---

### 🎨 Visual Web UI

**MOVED** from Week 5-6 → v3.2 (Weeks 7-10)

**Technology Stack:**
- **Backend**: FastAPI + WebSockets (Python)
- **Frontend**: React + TypeScript + Vite
- **Real-time**: WebSocket for live updates
- **API**: RESTful endpoints + WebSocket events

**Features:**
- 📊 **Real-time Dashboard**: Live orchestrator status
- 📝 **Task Management**: View, filter, execute tasks
- 🤖 **Agent Pool Visualization**: Monitor all agent types
- 📈 **Telemetry Timeline**: Event visualization
- 🔄 **Session Monitoring**: Live session tracking
- 📱 **Mobile Responsive**: Works on all devices
- 🌙 **Dark Mode**: Theme support

**Components:**
- `api/server.py` - FastAPI backend
- `api/routes/` - REST endpoints (orchestrator, telemetry, sessions)
- `api/websockets/live_updates.py` - Real-time WebSocket
- `ui/` - React frontend (Dashboard, TaskList, AgentPool, Telemetry)

**URLs:**
- Dashboard: `http://localhost:8080`
- API Docs: `http://localhost:8080/docs`
- WebSocket: `ws://localhost:8080/ws`

---

## Weekly Breakdown

### Week 7: Foundation
**Build 7A:** Agent Type System
- Agent registry and profiles
- Task classification
- Agent pool management
- Orchestrator integration

**Build 7B:** Visual UI Foundation
- FastAPI backend + WebSocket
- React frontend base
- Dashboard components
- Real-time updates

**Build 7C:** Integration → v3.2.0-alpha.1

### Week 8: Intelligence
**Build 8A:** Agent Learning System
- Performance tracking per agent
- Pattern learning
- Capability expansion
- Recommendation engine

**Build 8B:** Advanced UI Features
- Drag-and-drop tasks
- Visual DAG editor
- Dark mode
- Mobile responsive

**Build 8C:** Integration → v3.2.0-alpha.2

### Week 9: Coordination
**Build 9A:** Agent Collaboration
- Multi-agent workflows
- Agent handoffs (coding → testing → security)
- Conflict resolution
- Result merging

**Build 9B:** UI Analytics Dashboard
- Build analytics
- Agent performance charts
- Cost visualization
- Success metrics

**Build 9C:** Integration → v3.2.0-alpha.3

### Week 10: Production
**Build 10A:** Agent Production Features
- Auto-scaling
- Health monitoring
- Failover
- Load balancing

**Build 10B:** UI Production Polish
- User authentication
- RBAC
- Settings persistence
- Notifications

**Build 10C:** Final Integration → v3.2.0 Release

---

## Architecture Integration

### How Multi-Agent Leverages Existing Systems

**From v3.1 Week 1 (Build A - Integration Layer):**
```
✅ Telemetry System → Tracks agent assignments and completions
✅ Routing System → Selects model tier per agent type
✅ Parallel Execution → Foundation for agent pool management
```

**New in v3.2:**
```
🆕 Agent Registry → Maps task types to agent specializations
🆕 Task Classifier → Routes tasks to best agent
🆕 Agent Pool → Manages concurrent specialized agents
🆕 Collaboration → Multi-agent workflows
```

**Visual UI Integration:**
```
FastAPI ↔ Orchestrator → Live status
WebSocket ↔ Telemetry → Real-time events
React UI ↔ Agent Pool → Agent visualization
Dashboard ↔ Sessions → Session monitoring
```

---

## Success Criteria

### Multi-Agent System
- [ ] 5+ specialized agent types registered
- [ ] 90%+ accurate task classification
- [ ] Support 10+ concurrent agents
- [ ] Agent learning improves recommendations over time
- [ ] 30%+ cost reduction through smart model routing
- [ ] Test coverage: 90%+

### Visual UI
- [ ] Real-time WebSocket updates (< 1s latency)
- [ ] React frontend with TypeScript
- [ ] Mobile responsive (320px - 4K)
- [ ] Dark mode + light mode
- [ ] Complete REST API documentation
- [ ] Frontend test coverage: 85%+
- [ ] Backend test coverage: 90%+

### Integration
- [ ] Agents visible in UI dashboard
- [ ] Live agent assignments displayed
- [ ] Telemetry captures all agent events
- [ ] UI can trigger agent-specific tasks
- [ ] WebSocket broadcasts agent state changes

---

## Migration from Original Plan

### What Changed

**Original Plan (BUILD_PLAN_ORCHESTRATED.md):**
- Week 5-6: Web UI Dashboard (Tier 2)
- No multi-agent system

**Updated Plan (v3.2):**
- Week 7-10: Multi-Agent + Visual UI together
- Builds on stronger foundation (v3.1 telemetry, routing, parallel)
- More comprehensive UI (not just dashboard)

### Why the Change

**Multi-Agent System:**
- Natural evolution of parallel execution
- Inspired by Claude Code's `/agents` capability
- Significant performance and cost benefits
- Addresses "how to use agents in BuildRunner" question

**Visual UI Timing:**
- Moved later to build on solid foundation
- Integrates with multi-agent system
- More features than original plan
- Production-ready (auth, scaling, analytics)

---

## Next Steps

1. ✅ Complete v3.1 Weeks 1-6 as currently planned
2. ✅ Execute v3.2 Week 7-10 per new plan
3. ⏳ Define v3.3 (Weeks 11-15) after v3.2 learnings
4. ⏳ Define v3.4 (Weeks 16-20) after v3.3 learnings

---

## Files Modified

- ✅ Created: `.buildrunner/BUILD_PLAN_V3.2_AGENTS_UI.md`
- ✅ Updated: `BUILD_PLAN_V3.1-V3.4_ATOMIC.md`
- ✅ Created: `.buildrunner/PLAN_UPDATE_V3.2.md` (this file)

---

**Plan updated:** 2025-01-18
**BuildRunner version:** 3.1.0 (in development)
**Target v3.2.0 release:** Week 10 completion
