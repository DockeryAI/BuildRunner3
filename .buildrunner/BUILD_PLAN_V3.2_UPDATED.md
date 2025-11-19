# BuildRunner 3.2 - Claude Agent Integration + Project Retrofit

**Version:** v3.2.0
**Duration:** Weeks 7-10 (4 weeks)
**Focus:** Claude Code `/agent` integration + Attach existing projects
**Strategy:** Parallel builds → Integration → Tag

---

## Overview

### 🤖 Feature 1: Claude Code Agent Integration

**Use Claude Code's native `/agent` capabilities instead of building custom agent pool:**

- Leverage `/agent explore`, `/agent test`, `/agent review`, `/agent refactor`
- Bridge BuildRunner tasks to Claude agents
- Track agent performance and costs
- Parallel agent execution via Claude Code

**Benefits:**
- ✅ No duplicate implementation
- ✅ Automatic model selection by Claude
- ✅ Native Claude Code workflow integration
- ✅ Access to future Claude agent improvements

### 🔧 Feature 2: `br attach` - Retrofit Existing Projects

**Attach BuildRunner to codebases that already exist:**

```bash
br attach --analyze      # Scan code, generate PROJECT_SPEC
br attach --minimal      # Just add .buildrunner/ structure
br attach --security     # Security scanning only
br attach --full         # Complete integration
```

**Capabilities:**
- Codebase analysis (10+ languages/frameworks)
- Auto-generate PROJECT_SPEC from code structure
- Incremental adoption (choose features you want)
- Works with monorepos and microservices

### 🎨 Feature 3: Visual Web UI

**Modern dashboard with agent monitoring:**
- Real-time Claude agent tracking
- Task → Agent assignments
- Agent performance metrics
- Cost breakdown by agent type

---

## Week 7: Foundation

### Build 7A - Claude Agent Bridge [Priority 1]
**Branch:** `build/v3.2-claude-agents`
**Duration:** 3 days

**Components:**

1. **Claude Agent Bridge** (`core/agents/claude_agent_bridge.py`)
   - Dispatch tasks to Claude Code agents
   - Agent type mapping (explore/test/review/refactor/implement)
   - Response parsing
   - Error handling

2. **Agent Commands** (`cli/agent_commands.py`)
   ```bash
   br agent run <task> --type explore
   br agent status
   br agent stats
   ```

3. **Integration with Orchestrator** (`core/orchestrator.py`)
   - Auto-route tasks to appropriate agents
   - Parallel agent execution
   - Track agent assignments in telemetry

### Build 7B - Attach Command [Priority 1 - BUILD NOW]
**Branch:** `build/v3.2-attach`
**Duration:** 3 days

**Components:**

1. **Codebase Analyzer** (`core/analyzer/codebase_analyzer.py`)
   - Language detection (Python, JS, TS, Go, Rust, Java, etc.)
   - Framework detection (Django, Flask, FastAPI, React, Vue, Next.js)
   - Architecture pattern detection (MVC, microservices, monolith)
   - Feature extraction from code structure
   - API endpoint discovery
   - Database schema detection
   - Test coverage analysis

2. **Spec Generator** (`core/analyzer/spec_generator.py`)
   - Generate PROJECT_SPEC from codebase analysis
   - Extract features from routes, services, models
   - Infer priorities from code complexity
   - Generate acceptance criteria from tests
   - Map dependencies

3. **Attach Command** (`cli/attach_commands.py`)
   ```bash
   br attach --analyze      # Full analysis + spec
   br attach --minimal      # Just .buildrunner/
   br attach --security     # Security only
   br attach --full         # Everything
   ```

4. **Integration Modes**
   - Minimal: Create `.buildrunner/` structure only
   - Security: Add pre-commit hooks, scan secrets
   - Analyze: Generate PROJECT_SPEC from code
   - Full: Security + Telemetry + Routing + Spec

### Build 7C - Visual UI Foundation
**Branch:** `build/v3.2-visual-ui`
**Duration:** 2 days

**Components:**

1. **FastAPI Backend** (`api/server.py`)
   - REST endpoints for orchestrator data
   - WebSocket for real-time updates
   - Agent status endpoints

2. **React Dashboard** (`ui/`)
   - Dashboard layout
   - Task list
   - Agent pool visualization
   - Telemetry timeline

### Build 7D - Week 7 Integration
**Location:** `main` branch
**Duration:** 1 day

- Merge all Week 7 builds
- Integration testing
- Tag v3.2.0-alpha.1

---

## Week 8: Intelligence

### Build 8A - Smart Code Analysis
**Branch:** `build/v3.2-analysis`

**Components:**

1. **Framework Detector** (`core/analyzer/framework_detector.py`)
   - Auto-detect web frameworks
   - Identify build tools
   - Find config files
   - Extract project metadata

2. **Architecture Analyzer** (`core/analyzer/architecture_analyzer.py`)
   - Detect patterns (MVC, Clean, Hexagonal)
   - Map service boundaries
   - Identify dependencies
   - Generate architecture diagrams

3. **Feature Extractor** (`core/analyzer/feature_extractor.py`)
   - Parse routes → features
   - Analyze services → capabilities
   - Map models → data structures
   - Extract business logic

### Build 8B - Agent Performance Tracking
**Branch:** `build/v3.2-agent-tracking`

**Components:**

1. **Agent Metrics** (`core/agents/metrics.py`)
   - Track agent success rates
   - Cost per agent type
   - Average completion time
   - Quality scores

2. **Recommendation Engine** (`core/agents/recommender.py`)
   - Suggest best agent for task
   - Learn from past assignments
   - Optimize for cost vs speed vs quality

### Build 8C - UI Polish
**Branch:** `build/v3.2-ui-polish`

- Dark mode
- Mobile responsive
- Drag-drop task management
- Visual DAG editor

---

## Week 9: Coordination

### Build 9A - Multi-Agent Workflows
**Branch:** `build/v3.2-workflows`

**Components:**

1. **Agent Chains** (`core/agents/chains.py`)
   - Sequential workflows (explore → implement → test → review)
   - Parallel execution
   - Conditional routing
   - Error recovery

2. **Result Aggregation** (`core/agents/aggregator.py`)
   - Merge agent outputs
   - Resolve conflicts
   - Generate summary reports

### Build 9B - Migration Assistant
**Branch:** `build/v3.2-migrate`

**Components:**

1. **CI/CD Importer** (`core/migrate/ci_importer.py`)
   - Import GitHub Actions
   - Import CircleCI configs
   - Convert to BuildRunner tasks

2. **Tool Migration** (`core/migrate/tool_migrator.py`)
   - Migrate from Make, npm scripts
   - Convert to BuildRunner workflows

### Build 9C - UI Analytics
**Branch:** `build/v3.2-analytics`

- Build analytics charts
- Agent performance graphs
- Cost visualization
- Success metrics

---

## Week 10: Production

### Build 10A - Agent Production Features
**Branch:** `build/v3.2-agent-prod`

- Agent health monitoring
- Automatic failover
- Load balancing
- Resource limits

### Build 10B - UI Production Polish
**Branch:** `build/v3.2-ui-prod`

- User authentication
- RBAC
- Settings persistence
- Notification system

### Build 10C - Final Integration
**Location:** `main` branch

- Complete v3.2.0 release
- Performance benchmarks
- Migration guide
- Tag v3.2.0

---

## Success Criteria

### Claude Agent Integration
- ✅ Map all task types to Claude `/agent` commands
- ✅ 50%+ speed improvement via parallel agents
- ✅ Agent responses parsed and tracked
- ✅ Cost tracking per agent type

### Attach Command
- ✅ Analyzes 10+ languages/frameworks
- ✅ Generates accurate PROJECT_SPEC (80%+ accuracy)
- ✅ Supports incremental adoption modes
- ✅ Works with monorepos and microservices
- ✅ Test coverage: 90%+

### Visual UI
- ✅ Shows active Claude agents
- ✅ Real-time task → agent assignments
- ✅ Agent performance dashboard
- ✅ Sub-second update latency

---

## Commands

```bash
# Attach to existing project
br attach --analyze          # Full analysis + spec generation
br attach --minimal          # Just add BuildRunner structure
br attach --security         # Security scanning only
br attach --full             # Complete integration

# Agent operations (via Claude bridge)
br agent run <task> --type explore
br agent status              # Show active Claude agents
br agent stats               # Performance metrics

# Visual UI
br ui start                  # Launch dashboard
br ui agents                 # Agent monitoring view
```

---

## Implementation Priority

**IMMEDIATE (Week 7):**
1. ✅ Attach command (so we can use it on BuildRunner3 itself!)
2. ✅ Claude agent bridge
3. ✅ Visual UI foundation

**NEXT (Week 8-9):**
4. Smart code analysis
5. Agent performance tracking
6. Multi-agent workflows

**FINAL (Week 10):**
7. Production features
8. UI polish
9. v3.2.0 release

---

**Updated:** 2025-11-18
**Status:** Ready to build - Starting with Build 7B (Attach)
