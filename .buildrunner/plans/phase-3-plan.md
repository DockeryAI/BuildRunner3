# Plan: Phase 3 — Playwright MCP + Claude Code Hooks

## Tasks

### 3.1: Create .mcp.json with Playwright MCP server config

- New file at project root, stdio transport, npx @playwright/mcp@latest

### 3.2: Add MCP tool permissions to settings.local.json

- Restrict to 8 core Playwright tools
- Merge with existing permissions

### 3.3: Add Stop hook for E2E test gate

- agent type, low effort, terse prompt
- stop_hook_active guard prevents infinite loops

### 3.4: Add compact-matcher SessionStart hook

- Re-injects test status after context compaction

### 3.5: Create /pw-test slash command

- Explore-then-write pattern, XML structure, 2-3 multishot examples

## Tests

TDD Gate: SKIP — config files and skill templates, no testable code.
