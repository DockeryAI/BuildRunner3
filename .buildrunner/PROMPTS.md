# BuildRunner 3.0 - Claude Execution Prompts

Copy and paste these prompts to kick off each build. Each prompt is self-contained with full context.

---

## WEEK 1 PROMPTS

### 🔨 Build 1A: Feature Registry (Parallel Build)

```
Execute BuildRunner 3.0 - Build 1A: Feature Registry System

Context: Building a new standalone CLI tool to replace BuildRunner 2.0's shell scripts with Python-based feature tracking.

Plan Location: .buildrunner/BUILD_PLAN.md (Section: Build 1A)

Setup:
1. Create git worktree: git worktree add ../br3-feature-registry -b build/week1-feature-registry
2. cd ../br3-feature-registry
3. Install dependencies: pip install pytest pyyaml

Execute all tasks in BUILD_PLAN.md Build 1A section end-to-end:
- Create directory structure (core/, cli/, api/, tests/, docs/, .buildrunner/)
- Build feature registry system with JSON schema
- Implement STATUS.md auto-generator
- Create AI context management: CLAUDE.md + segmented context files
- Implement AIContextManager for persistent AI memory
- Write comprehensive tests (feature registry + AI context)
- Create examples

Acceptance Criteria:
- All tests pass (90%+ coverage)
- features.json CRUD works
- Auto-generated STATUS.md accurate
- CLAUDE.md and context/ structure created
- AIContextManager functional
- Example validates

When complete: Commit all changes, push branch, signal ready for review. DO NOT merge to main.
```

---

### 🔨 Build 1B: Git Governance (Parallel Build)

```
Execute BuildRunner 3.0 - Build 1B: Git Governance System

Context: Building git-backed governance system with rule enforcement and checksum verification for BuildRunner 3.0.

Plan Location: .buildrunner/BUILD_PLAN.md (Section: Build 1B)

Setup:
1. Create git worktree: git worktree add ../br3-governance -b build/week1-governance
2. cd ../br3-governance
3. Install dependencies: pip install pytest pyyaml GitPython

Execute all tasks in BUILD_PLAN.md Build 1B section end-to-end:
- Build governance YAML parser and validator
- Implement rule enforcement engine
- Create checksum verification system
- Write CODING_STANDARDS.md template
- Write comprehensive tests

Acceptance Criteria:
- All tests pass (90%+ coverage)
- Governance YAML loads and validates
- Rule enforcement functional
- Checksums prevent tampering

When complete: Commit all changes, push branch, signal ready for review. DO NOT merge to main.
```

---

### 🔨 Build 1C: Week 1 Integration (Main Branch)

```
Execute BuildRunner 3.0 - Build 1C: Week 1 Integration

Context: Merge parallel builds 1A and 1B, resolve conflicts, test integration.

Plan Location: .buildrunner/BUILD_PLAN.md (Section: Build 1C)

Prerequisites:
- Build 1A complete and reviewed
- Build 1B complete and reviewed

Setup:
1. cd /Users/byronhudson/Projects/BuildRunner3
2. git checkout main

Execute all tasks in BUILD_PLAN.md Build 1C section:
- Merge build/week1-feature-registry
- Merge build/week1-governance
- Run integration tests (feature registry + governance together)
- Resolve any conflicts
- Update README.md
- Tag v3.0.0-alpha.1

Acceptance Criteria:
- All merged code works together
- Integration tests pass
- No merge conflicts
- Alpha 1 tagged

When complete: Push main branch with tag. Clean up worktrees if desired.
```

---

## WEEK 2 PROMPTS

### 🔨 Build 2A: Python CLI (Parallel Build)

```
Execute BuildRunner 3.0 - Build 2A: Python CLI Commands

Context: Building full CLI interface for BuildRunner 3.0 with commands like 'br init', 'br feature add', etc.

Plan Location: .buildrunner/BUILD_PLAN.md (Section: Build 2A)

Setup:
1. Create git worktree: git worktree add ../br3-cli -b build/week2-cli
2. cd ../br3-cli
3. Install dependencies: pip install click pytest rich

Execute all tasks in BUILD_PLAN.md Build 2A section end-to-end:
- Setup CLI framework with Click/Typer
- Implement all br commands (init, feature add/complete/list, status, generate, sync)
- Add shorthand aliases (h, n, r, p, s, c)
- Add rich formatting for beautiful output
- Write comprehensive tests
- Document in docs/CLI.md

Acceptance Criteria:
- All commands work end-to-end
- Help text clear
- Rich formatting professional
- 85%+ test coverage

When complete: Commit all changes, push branch, signal ready for review. DO NOT merge to main.
```

---

### 🔨 Build 2B: FastAPI Backend (Parallel Build)

```
Execute BuildRunner 3.0 - Build 2B: FastAPI Backend

Context: Building REST API for BuildRunner 3.0 with Supabase integration.

Plan Location: .buildrunner/BUILD_PLAN.md (Section: Build 2B)

Setup:
1. Create git worktree: git worktree add ../br3-api -b build/week2-api
2. cd ../br3-api
3. Install dependencies: pip install fastapi uvicorn pytest httpx python-dotenv

Execute all tasks in BUILD_PLAN.md Build 2B section end-to-end:
- Setup FastAPI app with all endpoints (/health, /features, /sync, /governance, /metrics)
- Create Pydantic models
- Implement Supabase client
- Add CORS and environment config
- Write API tests
- Generate OpenAPI docs

Acceptance Criteria:
- All endpoints functional
- OpenAPI docs auto-generated
- Error handling robust
- 85%+ test coverage

When complete: Commit all changes, push branch, signal ready for review. DO NOT merge to main.
```

---

### 🔨 Build 2C: Week 2 Integration (Main Branch)

```
Execute BuildRunner 3.0 - Build 2C: Week 2 Integration

Context: Merge CLI and API builds, test end-to-end integration.

Plan Location: .buildrunner/BUILD_PLAN.md (Section: Build 2C)

Prerequisites:
- Build 2A complete and reviewed
- Build 2B complete and reviewed

Setup:
1. cd to main repo
2. git checkout main

Execute all tasks in BUILD_PLAN.md Build 2C section:
- Merge build/week2-cli
- Merge build/week2-api
- Test CLI + API integration (e.g., 'br init' calls API endpoints)
- Update installation docs
- Tag v3.0.0-alpha.2

Acceptance Criteria:
- CLI + API work together
- Integration tests pass
- Alpha 2 tagged

When complete: Push main with tag.
```

---

## WEEK 3 PROMPTS

### 🔨 Build 3A: Git Hooks + MCP (Parallel Build)

```
Execute BuildRunner 3.0 - Build 3A: Git Hooks + MCP Integration

Context: Adding git hooks for auto-validation and MCP server for Claude Code integration.

Plan Location: .buildrunner/BUILD_PLAN.md (Section: Build 3A)

Setup:
1. Create git worktree: git worktree add ../br3-integrations-core -b build/week3-git-mcp
2. cd ../br3-integrations-core
3. Install dependencies: pip install GitPython pytest

Execute all tasks in BUILD_PLAN.md Build 3A section end-to-end:
- Create git hooks (pre-commit, post-commit, pre-push)
- Implement MCP server exposing BuildRunner tools
- Test MCP integration with Claude Code
- Write comprehensive tests
- Document in docs/MCP_INTEGRATION.md

Acceptance Criteria:
- Git hooks install automatically
- MCP server exposes tools correctly
- Claude Code can manage features via MCP
- 85%+ test coverage

When complete: Commit all changes, push branch, signal ready for review. DO NOT merge to main.
```

---

### 🔨 Build 3B: Optional Integrations (Parallel Build)

```
Execute BuildRunner 3.0 - Build 3B: Optional Integrations

Context: Building optional plugins for GitHub, Notion, Slack integration.

Plan Location: .buildrunner/BUILD_PLAN.md (Section: Build 3B)

Setup:
1. Create git worktree: git worktree add ../br3-integrations-optional -b build/week3-optional
2. cd ../br3-integrations-optional
3. Install dependencies: pip install PyGithub notion-client pytest

Execute all tasks in BUILD_PLAN.md Build 3B section end-to-end:
- Create plugins/github.py (issue sync, PR creation)
- Create plugins/notion.py (doc sync)
- Create plugins/slack.py (notifications)
- Ensure graceful degradation without plugins
- Write tests
- Document in docs/PLUGINS.md

Acceptance Criteria:
- Plugins work when configured
- System works without plugins
- Configuration clear
- 80%+ test coverage

When complete: Commit all changes, push branch, signal ready for review. DO NOT merge to main.
```

---

### 🔨 Build 3C: Week 3 Integration (Main Branch)

```
Execute BuildRunner 3.0 - Build 3C: Week 3 Integration

Context: Merge integrations, test full workflow with MCP.

Plan Location: .buildrunner/BUILD_PLAN.md (Section: Build 3C)

Prerequisites:
- Build 3A complete and reviewed
- Build 3B complete and reviewed

Setup:
1. cd to main repo
2. git checkout main

Execute all tasks in BUILD_PLAN.md Build 3C section:
- Merge build/week3-git-mcp
- Merge build/week3-optional
- Test full workflow with MCP enabled
- Update integration docs
- Tag v3.0.0-beta.1

Acceptance Criteria:
- All integrations work
- MCP functional with Claude
- Beta 1 ready

When complete: Push main with tag.
```

---

## WEEK 4 PROMPTS

### 🔨 Build 4A: Migration Tools (Parallel Build)

```
Execute BuildRunner 3.0 - Build 4A: Migration Tools

Context: Building tools to migrate BuildRunner 2.0 projects to 3.0 format.

Plan Location: .buildrunner/BUILD_PLAN.md (Section: Build 4A)

Setup:
1. Create git worktree: git worktree add ../br3-migration -b build/week4-migration
2. cd ../br3-migration
3. Install dependencies: pip install pytest

Execute all tasks in BUILD_PLAN.md Build 4A section end-to-end:
- Create 'br migrate from-v2' command
- Parse old .runner/ structure and convert to features.json
- Handle edge cases (missing data, corrupt configs)
- Preserve git history
- Test on real BR 2.0 project
- Document in docs/MIGRATION.md

Acceptance Criteria:
- BR 2.0 projects migrate successfully
- No data loss
- Git history preserved
- 85%+ test coverage

When complete: Commit all changes, push branch, signal ready for review. DO NOT merge to main.
```

---

### 🔨 Build 4B: Multi-Repo Dashboard (Parallel Build)

```
Execute BuildRunner 3.0 - Build 4B: Multi-Repo Dashboard

Context: Building terminal dashboard to view status across all BuildRunner projects.

Plan Location: .buildrunner/BUILD_PLAN.md (Section: Build 4B)

Setup:
1. Create git worktree: git worktree add ../br3-dashboard -b build/week4-dashboard
2. cd ../br3-dashboard
3. Install dependencies: pip install rich pytest

Execute all tasks in BUILD_PLAN.md Build 4B section end-to-end:
- Create 'br dashboard' command
- Scan for all BR projects on system
- Aggregate status (completion %, blockers, activity)
- Build rich terminal UI with tables, progress bars
- Write tests
- Document in docs/DASHBOARD.md

Acceptance Criteria:
- Dashboard shows multiple projects accurately
- UI clear and professional
- 80%+ test coverage

When complete: Commit all changes, push branch, signal ready for review. DO NOT merge to main.
```

---

### 🔨 Build 4C: Week 4 Integration (Main Branch)

```
Execute BuildRunner 3.0 - Build 4C: Week 4 Integration

Context: Merge migration and dashboard, test on real projects.

Plan Location: .buildrunner/BUILD_PLAN.md (Section: Build 4C)

Prerequisites:
- Build 4A complete and reviewed
- Build 4B complete and reviewed

Setup:
1. cd to main repo
2. git checkout main

Execute all tasks in BUILD_PLAN.md Build 4C section:
- Merge build/week4-migration
- Merge build/week4-dashboard
- Test migration on actual BR 2.0 project
- Test dashboard with multiple projects
- Tag v3.0.0-beta.2

Acceptance Criteria:
- Migration works on real projects
- Dashboard functional
- Beta 2 ready

When complete: Push main with tag.
```

---

## WEEK 5 PROMPTS

### 🔨 Build 5A: Documentation + Examples

```
Execute BuildRunner 3.0 - Build 5A: Documentation + Examples

Context: Final documentation polish and example projects for v3.0.0 release.

Plan Location: .buildrunner/BUILD_PLAN.md (Section: Build 5A)

Setup:
1. cd to main repo
2. git checkout main

Execute all tasks in BUILD_PLAN.md Build 5A section:
- Write comprehensive README.md
- Create QUICKSTART.md (5-minute guide)
- Complete all docs/ (ARCHITECTURE, CLI, API, MCP, PLUGINS, MIGRATION, DASHBOARD, CONTRIBUTING)
- Create example projects in examples/ (web app, API service, multi-service)
- Record demo video/GIF
- Write release notes

Acceptance Criteria:
- All features documented
- Examples work
- Onboarding smooth

When complete: Commit and push.
```

---

### 🔨 Build 5B: Package + Deploy

```
Execute BuildRunner 3.0 - Build 5B: Package + Deploy

Context: Setup packaging for PyPI, Homebrew, Docker and CI/CD automation.

Plan Location: .buildrunner/BUILD_PLAN.md (Section: Build 5B)

Setup:
1. cd to main repo
2. git checkout main

Execute all tasks in BUILD_PLAN.md Build 5B section:
- Setup pyproject.toml for PyPI
- Create GitHub Actions (test on PR, auto-publish on tag)
- Create Homebrew formula
- Create Dockerfile (optional)
- Test all installation methods (pip, brew, docker)
- Setup versioning automation

Acceptance Criteria:
- Package installs cleanly
- All install methods work
- CI/CD functional

When complete: Commit and push.
```

---

### 🔨 Build 5C: Release v3.0.0

```
Execute BuildRunner 3.0 - Build 5C: Release v3.0.0

Context: Final testing, tagging, and publishing BuildRunner 3.0.0 to the world.

Plan Location: .buildrunner/BUILD_PLAN.md (Section: Build 5C)

Setup:
1. cd to main repo
2. git checkout main

Execute all tasks in BUILD_PLAN.md Build 5C section:
- Final testing sweep
- Update CHANGELOG.md
- Tag v3.0.0
- Publish to PyPI
- Create GitHub release
- Announce

Acceptance Criteria:
- v3.0.0 live on PyPI
- GitHub release published
- Documentation live

When complete: Celebrate. BuildRunner 3.0 is shipped.
```

---

## QUICK REFERENCE

### Week 1 (Foundation)
1. **Build 1A** (parallel): Feature Registry
2. **Build 1B** (parallel): Git Governance
3. **Build 1C** (merge): Integration → Tag alpha.1

### Week 2 (Commands + API)
1. **Build 2A** (parallel): Python CLI
2. **Build 2B** (parallel): FastAPI Backend
3. **Build 2C** (merge): Integration → Tag alpha.2

### Week 3 (Integrations)
1. **Build 3A** (parallel): Git Hooks + MCP
2. **Build 3B** (parallel): Optional Plugins
3. **Build 3C** (merge): Integration → Tag beta.1

### Week 4 (Migration + Dashboard)
1. **Build 4A** (parallel): Migration Tools
2. **Build 4B** (parallel): Multi-Repo Dashboard
3. **Build 4C** (merge): Integration → Tag beta.2

### Week 5 (Polish + Ship)
1. **Build 5A**: Documentation + Examples
2. **Build 5B**: Package + Deploy
3. **Build 5C**: Release v3.0.0

---

## Usage Instructions

1. Copy the prompt for the build you want to execute
2. Paste into Claude Code
3. Claude will execute the entire build autonomously
4. Review the PR when Claude signals completion
5. Approve and move to next build

For parallel builds (A + B), you can run them in separate Claude instances simultaneously.
