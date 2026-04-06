# Phase 7 Plan: Dashboard — Execution Monitor

## Tasks

### 7.1 ExecutionMonitorView class

- WHAT: New class in `core/dashboard_views.py` reading progress.json, plan files, file state
- WHY: Phase 7 deliverable — execution progress view
- VERIFY: Class instantiates and get_execution_data() returns structured dict

### 7.2 Task progress with verify results

- WHAT: `get_task_progress()` — reads progress.json for tasks_done/tasks_total, consecutive failure count
- WHY: Lusser's Law dashboard — every unverified step compounds
- VERIFY: Returns task list with verify status and failure count

### 7.3 Session metrics bar

- WHAT: `get_session_metrics()` — interaction count (of 70), elapsed time (of 35 min), compaction count, threshold colors
- WHY: Human sees when to checkpoint before context degrades
- VERIFY: Returns metrics with color thresholds at 80%/100%

### 7.4 Drift indicator

- WHAT: `get_drift_data()` — compares files_planned vs files_actual, returns drift percentage
- WHY: Spots divergence from plan in real-time
- VERIFY: Returns drift percentage when files diverge

### 7.5 Affected files preview

- WHAT: `get_affected_files()` — for each planned file: exists, last modified, line count
- WHY: Spots stale assumptions (deleted/missing files)
- VERIFY: Returns file info dict with exists/modified/lines

### 7.6 CLI exec view rendering

- WHAT: `_render_exec_monitor()` in `cli/dashboard.py` + add "exec" to --view choices
- WHY: `br dashboard show --view exec` command
- VERIFY: CLI renders without errors

### 7.7 Tests

- WHAT: Unit tests for ExecutionMonitorView
- WHY: Validate all data methods
- VERIFY: All tests pass
