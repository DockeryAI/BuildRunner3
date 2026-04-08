# Build: walter-auto-provision

**Created:** 2026-04-08
**Status:** COMPLETE
**Deploy:** cluster — `~/.buildrunner/scripts/walter-setup.sh` redeploy to 10.0.1.102

## Overview

Walter watches ~/repos/ but nothing creates repos there for new projects. 41 projects in ~/Projects/, only 4 on Walter. auto-save-session.sh pushes fail silently when bare repo doesn't exist. Fix: server-side auto-provision + client-side error surfacing + bulk seed.

## Parallelization Matrix

| Phase | Key Files                                   | Can Parallel With | Blocked By |
| ----- | ------------------------------------------- | ----------------- | ---------- |
| 1     | core/cluster/node_tests.py                  | 2                 | -          |
| 2     | ~/.buildrunner/scripts/auto-save-session.sh | 1                 | -          |
| 3     | ~/.buildrunner/scripts/walter-seed.sh (NEW) | -                 | 1, 2       |

## Phases

### Phase 1: Server-Side Auto-Provision

**Status:** COMPLETE
**Goal:** Walter creates bare repos on demand when it receives requests for unknown projects
**Files:**

- core/cluster/node_tests.py (MODIFY)

**Blocked by:** None
**Deliverables:**

- [x] `_ensure_repo(project_name)` helper — `git init --bare ~/repos/{project}` if directory doesn't exist, returns path
- [x] `POST /api/provision` endpoint — accepts project name, calls `_ensure_repo`, idempotent, returns status
- [x] Modify `/api/run` — when `project` param set and directory missing, call `_ensure_repo` before iterating
- [x] `repo_provisions` table added to `_ensure_tables()` in test_results.db — tracks project, provisioned_at
- [x] Enhance `/api/health` response — add `repo_count` and `watched_repos` list

**Success Criteria:** `POST /api/provision?project=trailsync` creates `~/repos/trailsync` as bare repo. `/api/run?project=newproject` provisions then queues instead of returning error.

---

### Phase 2: Client-Side Error Surfacing

**Status:** COMPLETE
**Goal:** auto-save-session.sh provisions before pushing, surfaces errors instead of swallowing them
**Files:**

- ~/.buildrunner/scripts/auto-save-session.sh (MODIFY)

**Blocked by:** None (different file than Phase 1)
**After:** Phase 1 (needs /api/provision endpoint)
**Deliverables:**

- [x] Before git push: call `$WALTER_URL/api/provision?project=$PROJECT` to ensure bare repo exists on Walter
- [x] Remove `2>/dev/null` from git push (line 54) — redirect stderr to `$WALTER_LOG`
- [x] Remove `&` backgrounding from git push — make synchronous so dispatch only fires after push succeeds
- [x] Add push exit code check — if push fails after provision, log error and skip `/api/run` dispatch
- [x] Parse `/api/run` response — log warning when status is "error"

**Success Criteria:** First commit in any project provisions repo on Walter, pushes code, triggers tests. Failures logged to walter-dispatch.log with context.

---

### Phase 3: Bulk Seed + Verification

**Status:** COMPLETE
**Goal:** All existing projects provisioned on Walter with verification
**Files:**

- ~/.buildrunner/scripts/walter-seed.sh (NEW)

**Blocked by:** Phase 1, Phase 2
**Deliverables:**

- [x] `walter-seed.sh` — reads projects.json AND scans ~/Projects/ for completeness, inits bare repos on Walter for each missing project, pushes HEAD from Muddy
- [x] `--dry-run` flag — reports what would be provisioned without acting
- [x] `--verify` flag — compares ~/Projects/ dirs against Walter ~/repos/, reports gaps
- [x] Run seed for all missing projects (sequential, 1s delay between)
- [x] Verify via `/api/health` watched_repos count matches total projects

**Success Criteria:** `walter-seed.sh --verify` reports zero gaps. `/api/health` shows all projects in watched_repos.

---

## Out of Scope

- Filesystem watcher on Muddy for new projects (currently hook-triggered only)
- Auto-removing deleted projects from Walter
- Multi-branch watching (only `current` ref)
- Selective test filtering per project

## Gates Passed

- 3.7 Adversarial review (Otis) — 3 blockers were false positives from stale Walter repo copy; 4 warnings addressed in deliverables
- 3.8 Architecture validation — external paths flagged (auto-save-session.sh, walter-seed.sh outside project root)

## Session Log

[Will be updated by /begin]
