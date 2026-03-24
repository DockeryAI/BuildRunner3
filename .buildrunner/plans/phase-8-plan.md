# Plan: Phase 8 — Terminal Dashboard (`/dash` skill)

## Architecture

- **Global package** at `~/.claude/dashboard/` — installed once, runs everywhere
- `/dash` skill calls `npx tsx ~/.claude/dashboard/src/index.tsx`
- On launch: walks up from `cwd` looking for `.buildrunner/`, errors if not found
- Reads project name from BUILD spec header

## Tasks

### Task A: Package scaffold + parsers (8.1 + 8.2)

- `~/.claude/dashboard/package.json`, `tsconfig.json`, `src/types.ts`
- `src/parsers/buildSpec.ts` — phases, deliverables, status, progress
- `src/parsers/decisions.ts` — timestamped entries with tags
- `src/parsers/features.ts` — feature list with completion metrics
- `src/parsers/locks.ts` — active locks, heartbeat age, staleness
- `src/parsers/plans.ts` — plan content keyed by phase
- `src/parsers/governance.ts` — quality thresholds
- `src/parsers/currentWork.ts` — active status from context/current-work.md
- `src/parsers/orchestration.ts` — batch state
- `src/parsers/index.ts` — barrel export

### Task B: Ink components + layout (8.3 + 8.5 + 8.6)

- `src/stores/dashStore.ts` — zustand store
- `src/components/PhaseMap.tsx` — phase list with status/arrows
- `src/components/DecisionLog.tsx` — last 5 decisions
- `src/components/HealthPanel.tsx` — feature completion, quality gates, stale warnings
- `src/components/StatusBar.tsx` — one-line bottom summary
- `src/components/DetailView.tsx` — expanded panel view
- `src/components/HelpOverlay.tsx` — key bindings help
- `src/App.tsx` — layout grid, keyboard handling

### Task C: File watcher + entry point (8.4)

- `src/watcher.ts` — chokidar setup, file-to-parser mapping
- `src/index.tsx` — findBuildrunnerDir, init, render

### Task D: `/dash` skill (8.7)

- `~/.claude/commands/dash.md` — launcher with install check

## Tests

- Parser tests with fixture data from real .buildrunner/ files
- `src/__tests__/fixtures/` — copied BUILD spec, decisions.log, features.json, etc.

## Execution Order

Sequential: A → B → C → D (all share ~/.claude/dashboard/)
