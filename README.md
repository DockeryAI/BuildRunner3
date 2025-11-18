# BuildRunner 3.0

**Git-backed governance for AI-assisted development**

BuildRunner 3.0 is a next-generation project management CLI designed specifically for AI-driven development workflows. It eliminates common AI coding frustrations through intelligent systems that ensure completeness, maintain quality, and provide structured guidance.

[![Version](https://img.shields.io/badge/version-3.1.0--alpha.2-blue)](https://github.com/buildrunner/buildrunner)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](tests/)

---

## The Problem

AI-assisted development introduces unique challenges:
- 🔴 **Incomplete Builds** - AI forgets tasks, skips steps, leaves TODOs
- 🔴 **Quality Drift** - No consistency across sessions, varying code quality
- 🔴 **Architecture Chaos** - Specs ignored, patterns violated, standards forgotten
- 🔴 **Context Loss** - Every new session starts from scratch
- 🔴 **Debugging Hell** - Hard to capture errors, reproduce issues, track failures

## The Solution

BuildRunner 3.0 provides **8 intelligent systems** that transform AI development:

### 1. 🎯 Completion Assurance System
**Never ship incomplete projects again**
- Automated gap analysis detects missing features, incomplete implementations
- Task dependency tracking ensures proper build order
- Pre-push validation blocks incomplete code
- Real-time progress tracking with visual STATUS.md

**→** [See Gap Analysis Docs](docs/GAP_ANALYSIS.md)

### 2. ⚡ Code Quality System
**Maintain professional standards automatically**
- Multi-dimensional quality scoring (structure, security, testing, docs)
- Automated linting, formatting, and security scans
- Quality gates in git hooks prevent bad code from landing
- Per-project quality thresholds

**→** [See Code Quality Docs](docs/CODE_QUALITY.md) | [See Behavior Config](docs/BEHAVIOR_CONFIG.md)

### 3. 🏗️ Architecture Drift Prevention
**Keep implementations aligned with specs**
- Architecture guard validates code against PROJECT_SPEC.md
- Automatic detection of spec violations
- Git hooks enforce architectural rules
- Design system consistency validation

**→** [See Architecture Guard Docs](docs/ARCHITECTURE_GUARD.md)

### 4. 🐛 Automated Debugging System
**Capture and pipe errors automatically**
- Auto-pipe command outputs to context
- Error pattern detection and analysis
- Failure analysis across sessions
- Smart retry suggestions

**→** [See Automated Debugging Docs](docs/AUTOMATED_DEBUGGING.md)

### 5. 🎨 Design System with Industry Intelligence
**Generate pixel-perfect designs from industry patterns**
- 8 industry profiles (Healthcare, Fintech, SaaS, E-commerce, etc.)
- 8 use case patterns (Dashboard, Marketplace, CRM, Analytics, etc.)
- Auto-merge profiles with intelligent conflict resolution
- Generate complete Tailwind configs
- Industry compliance requirements (HIPAA, WCAG, etc.)

**→** [See PRD Wizard Docs](docs/PRD_WIZARD.md) | [See Design System Docs](docs/DESIGN_SYSTEM.md)

### 6. 📋 Planning Mode + PRD Integration
**Strategic planning with Opus, tactical execution with Sonnet**
- Interactive PROJECT_SPEC wizard
- Auto-detection of industry and use case
- Opus pre-fills specifications
- Compact handoff packages for model switching
- Bidirectional sync: spec ↔ features.json

**→** [See PRD System Docs](docs/PRD_SYSTEM.md)

### 7. 🔧 Self-Service Execution System
**Intelligent API key management and environment setup**
- Auto-detect required services (Stripe, AWS, Supabase, etc.)
- Smart prompts for credentials
- `.env` generation with validation
- Graceful degradation when services unavailable

**→** [See Self-Service Docs](docs/SELF_SERVICE.md)

### 8. 🎮 Global/Local Behavior Configuration
**Fine-grained control over BuildRunner behavior**
- Global defaults in ~/.buildrunner/config.yaml
- Project overrides in .buildrunner/config.yaml
- Runtime flags for temporary changes
- Config hierarchy: Runtime > Project > Global > Defaults

**→** [See Behavior Config Docs](docs/BEHAVIOR_CONFIG.md)

---

## Quick Start

### Installation

```bash
# Install via pip (recommended)
pip install buildrunner

# Or via Homebrew (macOS)
brew install buildrunner

# Or via Docker
docker pull buildrunner/buildrunner:latest
```

### Initialize a New Project

```bash
# Create new BuildRunner project
br init my-project
cd my-project

# Run the PRD Wizard
br spec wizard

# Start building
br status
```

### 5-Minute Walkthrough

See [docs/QUICKSTART.md](docs/QUICKSTART.md) for a complete tutorial.

---

## v3.1 Status (Build 4E)

**Version:** v3.1.0-alpha ⚠️ Beta - Core components unit-tested, orchestrator integration in progress

BuildRunner v3.1 adds four major system enhancements:

### 🔒 Security Safeguards (Tier 1)
- ✅ **Secret detection** (13 patterns: Anthropic, OpenAI, JWT, AWS, GitHub, etc.)
- ✅ **SQL injection detection** (Python + JavaScript patterns)
- ⚠️ **Pre-commit hooks** (code exists, production validation needed)
- ✅ **73 tests passing** (80% coverage)

**→** [See SECURITY.md](SECURITY.md) for details

### 🎯 Model Routing & Cost Optimization
- ✅ **Heuristic-based complexity estimation** (simple/moderate/complex/critical)
- ⚠️ **AI-powered estimation** (optional, requires API key, not yet integrated)
- ✅ **Model selection logic** (Haiku/Sonnet/Opus)
- ⚠️ **Cost tracking interface** (SQLite persistence in development)

**→** [See ROUTING.md](ROUTING.md) for details

### 📊 Telemetry & Monitoring
- ✅ **Event schemas defined** (16 event types across 5 categories)
- ✅ **Metrics analysis logic** (success rate, latency, cost, errors)
- ⚠️ **Event collection** (needs orchestrator integration)
- ⚠️ **Data persistence** (file rotation available, SQLite in development)

**→** [See TELEMETRY.md](TELEMETRY.md) for details

### ⚡ Parallel Orchestration
- ✅ **Multi-session coordination** (unit tested, 28 tests passing)
- ✅ **File locking with conflict detection** (unit tested)
- ✅ **Worker health monitoring** (unit tested)
- ⚠️ **End-to-end execution** (not yet tested in production)

**→** [See PARALLEL.md](PARALLEL.md) for details

### 📚 Documentation & Guides
- ✅ **Quick start guide** ([docs/QUICKSTART.md](docs/QUICKSTART.md))
- ✅ **Integration guide** ([docs/INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md))
- ✅ **API reference** ([docs/API_REFERENCE.md](docs/API_REFERENCE.md))
- ✅ **E2E tests** (5 comprehensive scenarios)

### ⚠️ Integration Status

**What's Working:**
- Secret detection patterns (13 types)
- SQL injection detection (Python + JS)
- Heuristic-based complexity estimation
- CLI commands (25 total)
- Unit tests (101 tests passing)

**What's In Progress:**
- Security hooks: Production validation needed
- AI-powered estimation: Optional, not yet integrated
- Cost tracking: SQLite persistence in development
- Telemetry collection: Orchestrator integration needed
- Parallel execution: End-to-end testing needed

**Week 1 Goals:** Integration layer, persistence layer, AI integration, E2E testing

---

## Core Features

### Feature-Based Tracking
✅ Replace confusing phase/step models with clear feature tracking
✅ Auto-generate STATUS.md from features.json
✅ Track completion percentage, blockers, and dependencies
✅ Visual progress with rich terminal UI

### Git Hooks & Governance
✅ Pre-commit: Validate features.json, enforce governance rules
✅ Post-commit: Auto-generate STATUS.md, update metrics
✅ Pre-push: Block pushes with incomplete features or violations
✅ Governance as code with checksums

### MCP Integration (Claude Code)
✅ 9 BuildRunner tools exposed via Model Context Protocol
✅ Manage features directly from Claude Code
✅ Run governance checks, generate status reports
✅ Full stdio-based communication

**→** [See MCP Integration Docs](docs/MCP_INTEGRATION.md)

### Optional Integrations
✅ **GitHub**: Sync issues to features, create PRs from CLI
✅ **Notion**: Push STATUS.md and docs to Notion workspace
✅ **Slack**: Build notifications, daily standups, alerts
✅ **Supabase**: Optional cloud persistence and event logging

**→** [See Plugins Docs](docs/PLUGINS.md)

### Migration from BuildRunner 2.0
✅ Automated migration from .runner/ to .buildrunner/
✅ Convert HRPO → features.json
✅ Convert governance.json → governance.yaml
✅ Preserve git history and metadata
✅ Dry-run mode for safe preview

**→** [See Migration Guide](docs/MIGRATION.md)

### Multi-Repo Dashboard
✅ Discover all BuildRunner projects automatically
✅ Aggregate status across multiple repos
✅ Overview, detail, timeline, and alerts views
✅ Health status calculation (healthy/warning/critical)
✅ Rich terminal UI with color coding

**→** [See Dashboard Docs](docs/DASHBOARD.md)

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    BuildRunner 3.0                          │
├────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌──────────────┐   ┌───────────────┐  │
│  │     CLI     │───▶│   FastAPI    │──▶│   Feature     │  │
│  │   (Typer)   │    │   Backend    │   │   Registry    │  │
│  └─────────────┘    └──────────────┘   └───────────────┘  │
│         │                   │                    │          │
│  ┌──────▼─────┐    ┌───────▼────┐   ┌──────────▼──────┐  │
│  │ Git Hooks  │    │MCP Server  │   │   Governance    │  │
│  └────────────┘    └────────────┘   │     Engine      │  │
│                                       └─────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐ │
│  │          Optional Integrations (Graceful Degradation)│ │
│  ├──────────────────────────────────────────────────────┤ │
│  │  GitHub  │  Notion  │  Slack  │  Supabase │ Figma   │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                              │
└────────────────────────────────────────────────────────────┘
```

**→** [See Architecture Docs](docs/ARCHITECTURE.md)

---

## Documentation

### Getting Started
- [Quick Start Guide](docs/QUICKSTART.md) - 5-minute getting started guide (v3.1)
- [Integration Guide](docs/INTEGRATION_GUIDE.md) - Integrate BuildRunner into your project (v3.1)
- [Installation Guide](docs/INSTALLATION.md) - Detailed installation
- [First Project Tutorial](docs/tutorials/FIRST_PROJECT.md) - Complete walkthrough

### v3.1 Systems (Build 4E)
- [Security Guide](SECURITY.md) - Secret detection, SQL injection checks, pre-commit hooks
- [Routing Guide](ROUTING.md) - Model selection and cost optimization
- [Telemetry Guide](TELEMETRY.md) - Monitoring, metrics, and alerts
- [Parallel Orchestration Guide](PARALLEL.md) - Multi-session coordination
- [API Reference](docs/API_REFERENCE.md) - Complete API reference (v3.1)

### Core Systems
- [CLI Reference](docs/CLI.md) - All CLI commands
- [API Reference](docs/API.md) - All API endpoints
- [MCP Integration](docs/MCP_INTEGRATION.md) - Claude Code integration
- [Plugins](docs/PLUGINS.md) - GitHub, Notion, Slack, Supabase

### Enhancement Systems
- [Code Quality System](docs/CODE_QUALITY.md) - Quality gates and scoring
- [Gap Analysis](docs/GAP_ANALYSIS.md) - Completion assurance
- [Architecture Guard](docs/ARCHITECTURE_GUARD.md) - Drift prevention
- [Automated Debugging](docs/AUTOMATED_DEBUGGING.md) - Error capture
- [Design System](docs/DESIGN_SYSTEM.md) - Industry intelligence
- [PRD Wizard](docs/PRD_WIZARD.md) - PROJECT_SPEC creation
- [Self-Service Execution](docs/SELF_SERVICE.md) - Environment setup
- [Behavior Configuration](docs/BEHAVIOR_CONFIG.md) - Global/local config

### Tutorials
- [Design System Guide](docs/tutorials/DESIGN_SYSTEM_GUIDE.md) - Using industry profiles
- [Quality Gates Setup](docs/tutorials/QUALITY_GATES.md) - Setting standards
- [Parallel Builds](docs/tutorials/PARALLEL_BUILDS.md) - Orchestrating builds
- [Completion Assurance](docs/tutorials/COMPLETION_ASSURANCE.md) - Using gap analyzer

### Migration & Tools
- [Migration from BR 2.0](docs/MIGRATION.md) - Upgrade guide
- [Dashboard](docs/DASHBOARD.md) - Multi-repo management
- [Template Catalog](docs/TEMPLATE_CATALOG.md) - Industry + use case profiles

### Contributing
- [CONTRIBUTING.md](CONTRIBUTING.md) - How to contribute
- [Code of Conduct](CODE_OF_CONDUCT.md) - Community guidelines

---

## Example Projects

### Healthcare Dashboard
```bash
cd examples/healthcare-dashboard/
br spec wizard
# Follow prompts, select Healthcare + Dashboard
br status
```

Complete example using healthcare industry profile with dashboard patterns, HIPAA compliance, and patient vitals widgets.

### Fintech API
```bash
cd examples/fintech-api/
br spec wizard
# Follow prompts, select Fintech + API Service
br status
```

API service with security-first design, PCI compliance, and financial transaction handling.

### E-commerce Marketplace
```bash
cd examples/ecommerce-marketplace/
br spec wizard
# Follow prompts, select E-commerce + Marketplace
br status
```

Multi-service project with product catalog, payment processing, and order management.

### SaaS Onboarding Flow
```bash
cd examples/saas-onboarding/
br spec wizard
# Follow prompts, select SaaS + Onboarding
br status
```

Showcase of design system with onboarding patterns, user activation, and trial flows.

---

## CLI Commands

```bash
# Initialize project
br init <project-name>

# PRD Wizard
br spec wizard              # Interactive PROJECT_SPEC creation
br spec sync                # Sync spec to features.json
br spec validate            # Validate spec completeness
br spec confirm             # Lock spec

# Feature management
br feature add <name>       # Add new feature
br feature complete <id>    # Mark feature complete
br feature list             # List all features
br status                   # Show project status
br generate                 # Generate STATUS.md

# Security (v3.1) 🔒
br security check           # Check staged files for security issues
br security scan            # Scan entire project
br security hooks install   # Install pre-commit hooks
br security hooks status    # Check hook installation

# Model Routing (v3.1) 🎯
br routing estimate <task>  # Estimate complexity and recommend model
br routing select <task>    # Select model with constraints
br routing costs            # View cost summary
br routing models           # List available models

# Telemetry (v3.1) 📊
br telemetry summary        # View metrics summary
br telemetry events         # List recent events
br telemetry alerts         # Check for threshold alerts
br telemetry performance    # View performance metrics
br telemetry export <file>  # Export data to CSV

# Parallel Orchestration (v3.1) ⚡
br parallel start <name>    # Start parallel session
br parallel status          # View session status
br parallel dashboard       # Show live dashboard
br parallel list            # List all sessions
br parallel workers         # View worker health

# Design system
br design profile <industry> <use-case>  # Preview design profile
br design research           # Research design patterns

# Migration
br migrate from-v2 <path>   # Migrate from BR 2.0
br migrate rollback         # Rollback migration

# Dashboard
br dashboard show           # Multi-repo dashboard
br dashboard show --watch   # Live dashboard

# Quality & Governance
br quality check            # Run quality analysis
br gaps analyze             # Run gap analysis
br validate                 # Run all validations

# Config
br config set <key> <value> # Set config value
br config get <key>         # Get config value
br config list              # List all config
```

**→** [See Full CLI Reference](docs/CLI.md)

---

## Tech Stack

- **Language**: Python 3.11+
- **CLI Framework**: Typer
- **API Framework**: FastAPI
- **Terminal UI**: Rich
- **Database**: Supabase (PostgreSQL) - optional
- **Git Integration**: GitPython
- **Testing**: pytest + pytest-cov
- **Code Quality**: Black, Ruff, mypy, Bandit

---

## Roadmap

### v3.1 (Q1 2025)
- [ ] Web UI for dashboard
- [ ] Real-time collaboration (multiplayer editing)
- [ ] Visual spec editor
- [ ] AI-powered code reviews

### v3.2 (Q2 2025)
- [ ] Template marketplace
- [ ] Multi-project specs
- [ ] Spec versioning with branches
- [ ] Figma design import

### v3.3 (Q3 2025)
- [ ] Jira/Linear sync
- [ ] GitHub Issues integration
- [ ] Slack bot
- [ ] Auto-update from production metrics

---

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone repository
git clone https://github.com/buildrunner/buildrunner.git
cd buildrunner

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run quality checks
black .
ruff check .
mypy .
```

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Support

- **Documentation**: [https://buildrunner.dev/docs](https://buildrunner.dev/docs)
- **Issues**: [GitHub Issues](https://github.com/buildrunner/buildrunner/issues)
- **Discussions**: [GitHub Discussions](https://github.com/buildrunner/buildrunner/discussions)
- **Discord**: [Join our community](https://discord.gg/buildrunner)

---

## Acknowledgments

Built with ❤️ by the BuildRunner team and contributors.

Special thanks to:
- Anthropic for Claude Code and MCP protocol
- The open-source community for amazing tools and libraries
- Early adopters and beta testers for invaluable feedback

---

**BuildRunner 3.0** - *Because AI shouldn't forget to finish what it started* 🚀
