# Phase 6: Dashboard Plan Review — Implementation Plan

## Tasks

### 6.1 PlanReviewView class in dashboard_views.py
- Add `PlanReviewView` class that reads plan files, adversarial findings, and queries cluster APIs
- Methods: `get_task_table_data()`, `get_adversarial_data()`, `get_test_baseline_data()`, `get_historical_data()`, `get_code_health_data()`
- Graceful degradation: catch connection errors for Walter/Lockwood, always show plan + adversarial
- VERIFY: class exists with all methods, returns structured data

### 6.2 Task table rendering in cli/dashboard.py
- Rich table: columns #, WHAT, WHY, VERIFY (with green/red status)
- Parse plan file for tasks with single-function decomposition
- VERIFY: table renders with correct columns

### 6.3 Adversarial findings panel
- Read `.buildrunner/plans/adversarial-*.json`
- Color-coded: red=blocker (sorted top), yellow=warning, dim=note
- VERIFY: panel renders with color coding

### 6.4 Test baseline + Historical outcomes + Code health panels
- Test baseline: file→test mapping with green/red
- Historical: max 3 similar plans from Lockwood, one line each
- Code health: warning bar if file health < 9.5/10
- VERIFY: panels render, graceful when offline

### 6.5 CLI wiring + Actions
- Add `plan` to `--view` choices, add `--history` flag
- Actions: Approve (→ /begin), Revise (per-task comments), Reject (archive to Lockwood)
- VERIFY: `br dashboard show --view plan` works

## Tests
- Unit tests for PlanReviewView data methods
- Unit tests for plan file parsing
