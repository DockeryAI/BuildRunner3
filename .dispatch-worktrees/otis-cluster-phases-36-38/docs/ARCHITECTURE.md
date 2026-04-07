# BuildRunner 3.0 - System Architecture

## Overview

BuildRunner 3.0 is built on a modular architecture with three main layers:

```
┌─────────────────────────────────────────────────────────────┐
│                      Presentation Layer                      │
├─────────────────────────────────────────────────────────────┤
│  CLI (Typer)  │  FastAPI Backend  │  MCP Server (Claude)   │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                        Core Layer                            │
├─────────────────────────────────────────────────────────────┤
│  Feature Registry │ Governance Engine │ PRD System │ Mapper │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                      Integration Layer                       │
├─────────────────────────────────────────────────────────────┤
│  Git Hooks │ GitHub │ Notion │ Slack │ Supabase │ Figma    │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### Feature Registry (`core/feature_registry.py`)
- Central store for all features
- JSON-based persistence
- Version tracking and metrics
- CRUD operations

### Governance Engine (`core/governance.py`)
- YAML-based governance rules
- Checksum verification
- Rule enforcement
- Workflow validation

### PRD System (`core/prd_wizard.py`, `core/prd_parser.py`, `core/prd_mapper.py`)
- Interactive wizard for PROJECT_SPEC creation
- Spec parsing and validation
- Bidirectional sync: spec ↔ features.json
- Design profile merger

### Status Generator (`core/status_generator.py`)
- Auto-generate STATUS.md from features.json
- Template-based rendering
- Progress visualization

## Integration Points

### Git Hooks (`.buildrunner/hooks/`)
- `pre-commit`: Validation and enforcement
- `post-commit`: Auto-generation
- `pre-push`: Completeness checks

### MCP Server (`cli/mcp_server.py`)
- stdio-based communication
- 9 BuildRunner tools exposed
- Feature management via Claude Code

### Optional Plugins (`plugins/`)
- GitHub: Issue sync, PR creation
- Notion: Documentation sync
- Slack: Notifications and standups
- All gracefully degrade when unavailable

## Data Flow

**1. PROJECT_SPEC → features.json:**
```
USER → br spec wizard → PROJECT_SPEC.md → PRD Parser → features.json
```

**2. Feature Completion:**
```
USER → br feature complete → Feature Registry → STATUS.md (auto-generated)
```

**3. Git Hook Validation:**
```
git commit → pre-commit hook → Validate features.json → Allow/Block
```

## Design Principles

1. **Graceful Degradation** - Core works offline, plugins optional
2. **Git as Truth** - All state in Git, optional cloud sync
3. **AI-Native** - Designed for AI workflows
4. **Modular** - Components can be used independently
5. **Extensible** - Plugin architecture for integrations

