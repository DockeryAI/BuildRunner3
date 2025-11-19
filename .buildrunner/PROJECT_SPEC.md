# PROJECT_SPEC - BuildRunner 3.2

**Project:** BuildRunner v3.2 - Claude Agent Integration + Visual UI
**Generated:** 2025-11-18
**Location:** /Users/byronhudson/Projects/BuildRunner3
**Status:** In Development - Week 7 of v3.2 build plan

---

## Overview

BuildRunner 3.2 adds Claude Code agent integration and visual web UI to the existing modular monolith architecture.

**Current State:**
- **Files:** 590
- **Lines of Code:** 180,993
- **Test Coverage:** 52% → Target: 90%+
- **Languages:** Python
- **Frameworks:** FastAPI, Typer
- **Architecture:** Modular Monolith

**v3.2 New Capabilities:**
- Claude Code `/agent` integration for specialized task execution
- Visual web UI with real-time dashboard
- Project retrofit capability (`br attach`)

---

## Features

### Feature 1: Claude Agent Bridge (Build 7A)
**Priority:** Critical
**Status:** Planned
**Duration:** 2 days

**Description:** Bridge between BuildRunner tasks and Claude Code's native `/agent` command

**Requirements:**
- Dispatch tasks to Claude agents (explore/test/review/refactor/implement)
- Parse agent responses
- Track agent assignments in telemetry
- Handle agent errors gracefully

**Implementation:**
- Create `core/agents/claude_agent_bridge.py`
- Create `cli/agent_commands.py`
- Integrate with `core/orchestrator.py`

**Acceptance Criteria:**
- [ ] Can route tasks to Claude agents
- [ ] Agent responses are parsed correctly
- [ ] Telemetry tracks agent assignments
- [ ] Error handling for failed agents
- [ ] Tests pass (90%+ coverage)

---

### Feature 2: Visual Web UI Foundation (Build 7C)
**Priority:** Critical
**Status:** Planned
**Duration:** 3 days

**Description:** Modern web dashboard for BuildRunner orchestration

**Requirements:**
- FastAPI backend with WebSocket support
- React frontend with TypeScript
- Real-time task status updates
- Agent pool visualization
- Telemetry timeline

**Implementation:**
- Create `api/server.py` (FastAPI)
- Create `api/routes/` (orchestrator, telemetry, agents)
- Create `api/websockets/live_updates.py`
- Create `ui/` (React app with Dashboard, TaskList, AgentPool)

**Acceptance Criteria:**
- [ ] FastAPI backend runs on port 8080
- [ ] WebSocket real-time updates work
- [ ] React dashboard displays task list
- [ ] Agent pool shows active agents
- [ ] Telemetry timeline renders
- [ ] Tests pass (90%+ backend, 85%+ frontend)

---

### Feature 3: Agent Performance Tracking (Build 8B)
**Priority:** High
**Status:** Planned
**Duration:** 2 days

**Description:** Track Claude agent success rates, costs, and quality

**Requirements:**
- Track completion rates per agent type
- Cost tracking (Haiku/Sonnet/Opus routing)
- Quality scores based on test pass rates
- Recommendation engine for task → agent routing

**Implementation:**
- Create `core/agents/metrics.py`
- Create `core/agents/recommender.py`
- Integrate with telemetry system

**Acceptance Criteria:**
- [ ] Tracks success rates per agent
- [ ] Calculates cost per agent type
- [ ] Recommends best agent for task
- [ ] Stores metrics in telemetry DB
- [ ] Tests pass (90%+ coverage)

---

### Feature 4: Multi-Agent Workflows (Build 9A)
**Priority:** High
**Status:** Planned
**Duration:** 2 days

**Description:** Chain multiple agents in workflows (explore → implement → test → review)

**Requirements:**
- Sequential agent execution
- Parallel agent execution for independent tasks
- Result aggregation from multiple agents
- Error recovery and retry logic

**Implementation:**
- Create `core/agents/chains.py`
- Create `core/agents/aggregator.py`
- Update orchestrator for workflow support

**Acceptance Criteria:**
- [ ] Can chain agents sequentially
- [ ] Can run agents in parallel
- [ ] Aggregates results correctly
- [ ] Handles agent failures gracefully
- [ ] Tests pass (90%+ coverage)

---

### Feature 5: UI Analytics Dashboard (Build 9B)
**Priority:** Medium
**Status:** Planned
**Duration:** 2 days

**Description:** Charts and graphs for build analytics

**Requirements:**
- Agent performance charts
- Cost breakdown visualization
- Success rate trends
- Historical comparisons

**Implementation:**
- Create `ui/components/Analytics.tsx`
- Add charting library (Recharts)
- Create analytics API endpoints

**Acceptance Criteria:**
- [ ] Performance charts render
- [ ] Cost visualization works
- [ ] Trend analysis displays
- [ ] Export to PDF/CSV
- [ ] Tests pass (85%+ coverage)

---

### Feature 6: Production Features (Build 10A)
**Priority:** High
**Status:** Planned
**Duration:** 2 days

**Description:** Production-ready agent scaling and monitoring

**Requirements:**
- Agent health monitoring
- Automatic failover
- Load balancing across agents
- Resource limits

**Implementation:**
- Create `core/agents/health.py`
- Create `core/agents/load_balancer.py`
- Add monitoring endpoints

**Acceptance Criteria:**
- [ ] Health checks detect failing agents
- [ ] Auto-failover to backup agents
- [ ] Load balances across agent pool
- [ ] Enforces resource limits
- [ ] Tests pass (90%+ coverage)

---

### Feature 7: UI Authentication (Build 10B)
**Priority:** Medium
**Status:** Planned
**Duration:** 2 days

**Description:** User authentication and RBAC for web UI

**Requirements:**
- User login/logout
- Role-based access control
- Settings persistence
- Notification system

**Implementation:**
- Create `api/auth.py`
- Add JWT authentication
- Create login UI component
- Add notification system

**Acceptance Criteria:**
- [ ] Users can login/logout
- [ ] RBAC enforces permissions
- [ ] Settings persist per user
- [ ] Notifications display
- [ ] Tests pass (90%+ coverage)

---

## Technical Requirements

- Python 3.11+ for backend services
- FastAPI for REST API endpoints
- React + TypeScript for web UI
- WebSocket support for real-time updates
- SQLite for telemetry persistence
- Typer for CLI framework
- Claude Code agent integration
- 90%+ test coverage
- Visual debugging capabilities
- Multi-agent coordination

---

## Technical Architecture

**Backend:**
- FastAPI for REST API
- WebSockets for real-time updates
- SQLite for telemetry persistence

**Frontend:**
- React + TypeScript
- Vite for build tooling
- Recharts for visualization
- Axios for API calls

**Agent Integration:**
- Bridge to Claude Code `/agent` command
- No custom agent implementation
- Leverage native Claude capabilities

**Infrastructure:**
- Development: `br ui dev` (port 8080)
- Production: Uvicorn + Nginx

---

## Implementation Timeline

**Week 7: Foundation (Current)**
- ✅ Day 1-2: `br attach` command (COMPLETE)
- ⏳ Day 3-4: Claude agent bridge
- ⏳ Day 5-6: Visual UI foundation
- ⏳ Day 7: Integration → v3.2.0-alpha.1

**Week 8: Intelligence**
- Agent performance tracking
- UI polish (dark mode, mobile responsive)
- Integration → v3.2.0-alpha.2

**Week 9: Coordination**
- Multi-agent workflows
- UI analytics dashboard
- Integration → v3.2.0-alpha.3

**Week 10: Production**
- Agent scaling and monitoring
- UI authentication and RBAC
- Final integration → v3.2.0 Release

---

## Success Metrics

**Agent Integration:**
- [ ] 50%+ speed improvement via parallel agents
- [ ] All task types mapped to Claude agents
- [ ] Cost tracked per agent type
- [ ] 90%+ test coverage

**Visual UI:**
- [ ] Sub-second update latency
- [ ] Mobile responsive (320px - 4K)
- [ ] Dark mode + light mode
- [ ] 85%+ test coverage

**Overall:**
- [ ] Test coverage: 52% → 90%+
- [ ] All v3.2 features complete
- [ ] Production deployment guide
- [ ] Migration guide from v3.1

---

## Commands

```bash
# Agent operations
br agent run <task> --type explore
br agent status
br agent stats

# Visual UI
br ui start    # Launch dashboard
br ui dev      # Development mode
br ui agents   # Agent monitoring view

# Build orchestration
br build start  # Execute this PROJECT_SPEC
br build next   # Next batch of tasks
br build status # Show progress
```

---

## Next Steps

1. **NOW:** Implement Claude Agent Bridge (Build 7A)
2. **NEXT:** Visual UI Foundation (Build 7C)
3. **THEN:** Agent Performance Tracking (Build 8B)
4. **FINALLY:** Multi-Agent Workflows (Build 9A)

---

*Generated by BuildRunner 3.2 - Code Analysis Tool*
*Updated: 2025-11-18*
