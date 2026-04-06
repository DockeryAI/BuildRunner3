# Phase 8 Plan: Dashboard Enhancements

## Tasks

### 8.1 BUILD spec context panel in PlanReviewView
- WHAT: Add `get_build_spec_context()` to `PlanReviewView` in `core/dashboard_views.py`
- WHY: Reviewers need BUILD spec context alongside the plan without visual clutter
- VERIFY: Method returns phase data dict with goal, deliverables, success_criteria keys

### 8.2 Dependency diagram renderer in PlanReviewView
- WHAT: Add `get_dependency_diagram()` to `PlanReviewView` in `core/dashboard_views.py`
- WHY: Visual dependency rendering when present, graceful skip when absent
- VERIFY: Returns list of dependency nodes or empty list when no deps section

### 8.3 Plan comparison diff in PlanReviewView
- WHAT: Add `get_plan_diff()` to `PlanReviewView` in `core/dashboard_views.py`
- WHY: After reject/replan, reviewer needs to see what changed
- VERIFY: Returns diff dict with added, removed, modified task lists

### 8.4 CLI --context flag rendering
- WHAT: Add `--context` flag to `show` command in `cli/dashboard.py`
- WHY: Toggle BUILD spec context display alongside plan review
- VERIFY: Flag accepted, BUILD spec panel renders when flag is set

### 8.5 CLI --diff flag rendering
- WHAT: Add `--diff` flag to `show` command in `cli/dashboard.py`
- WHY: Show colored diff between plan versions after replan
- VERIFY: Flag accepted, diff panel renders with green/red/yellow coloring
