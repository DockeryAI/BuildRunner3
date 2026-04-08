# Draft Plan: Walter Auto-Provision

## Problem Statement

Walter watches ~/repos/ but nothing creates repos there for new projects. 41 projects in ~/Projects/, only 4 on Walter (BuildRunner3, Synapse, research-library, workfloDock). auto-save-session.sh pushes to ssh://10.0.1.102/~/repos/$PROJECT but if the bare repo doesn't exist, the push fails silently (2>/dev/null, backgrounded with &). Walter's /api/run only iterates existing directories — unknown projects return "no matching projects found" which gets logged but never surfaced.

## Scope

### In Scope

- Server-side auto-provision on Walter (create bare repos on demand)
- Client-side error surfacing in auto-save-session.sh
- Bulk seed of all existing projects to Walter
- Provision logging and verification

### Out of Scope

- Auto-discovery of new ~/Projects/ directories without a commit hook (filesystem watcher on Muddy)
- Removing projects from Walter when deleted locally
- Multi-branch watching (currently only watches `current` ref)
- Selective test filtering per project (some projects may not have vitest)
- Changes to Walter's test execution logic (vitest/playwright) — that already works

## Technical Approach

### Server-Side (node_tests.py)

- Add `_ensure_repo(project_name)` helper — runs `git init --bare ~/repos/{project}` if missing, returns path
- Add `POST /api/provision` endpoint — accepts project name, calls \_ensure_repo, returns status. Idempotent.
- Modify `/api/run` — when project param is set and directory doesn't exist, call \_ensure_repo so bare repo is ready for the next push
- New SQLite table `repo_provisions` to track when repos were provisioned
- Log watched repo count on each watch loop cycle

### Client-Side (auto-save-session.sh)

- Before git push: call `/api/provision?project=$PROJECT` to ensure bare repo exists (one HTTP call, idempotent)
- Remove `2>/dev/null` from git push — redirect stderr to walter-dispatch.log
- Remove backgrounding `&` from git push — make synchronous so dispatch only fires after push succeeds
- Add push exit code check — log error and skip /api/run if push fails
- Parse /api/run response for error status

### Bulk Seed (walter-seed.sh — NEW)

- Read projects.json, SSH to Walter, git init --bare for each missing repo
- Push current HEAD from Muddy for each
- --dry-run and --verify flags
- Run against all 37 missing projects

## Files

### MODIFY

- `core/cluster/node_tests.py` — add /api/provision endpoint, \_ensure_repo helper, modify /api/run, add repo_provisions table
- `~/.buildrunner/scripts/auto-save-session.sh` — pre-push provision call, error surfacing, synchronous push

### CREATE (NEW)

- `~/.buildrunner/scripts/walter-seed.sh` — bulk provisioning script

## Phases

### Phase 1: Server-Side Auto-Provision

**Files:** core/cluster/node_tests.py (MODIFY)
**Deliverables:**

- [ ] \_ensure_repo(project_name) helper — git init --bare if missing
- [ ] POST /api/provision endpoint — idempotent, returns status
- [ ] Modify /api/run — auto-provision when project param set and dir missing
- [ ] repo_provisions SQLite table
- [ ] Watch loop repo count logging

### Phase 2: Client-Side Error Surfacing

**Files:** ~/.buildrunner/scripts/auto-save-session.sh (MODIFY)
**Deliverables:**

- [ ] Pre-push /api/provision call
- [ ] Remove 2>/dev/null from git push, log stderr
- [ ] Remove & backgrounding, make push synchronous
- [ ] Push exit code check
- [ ] /api/run error response parsing

### Phase 3: Bulk Seed + Verification

**Files:** ~/.buildrunner/scripts/walter-seed.sh (NEW)
**Deliverables:**

- [ ] walter-seed.sh reads projects.json, inits bare repos
- [ ] --dry-run flag
- [ ] --verify flag
- [ ] Run seed for all 37 missing projects
- [ ] Verify via /api/health repo count

## Parallelization Matrix

| Phase | Key Files                  | Can Parallel With | Blocked By |
| ----- | -------------------------- | ----------------- | ---------- |
| 1     | core/cluster/node_tests.py | 2                 | -          |
| 2     | auto-save-session.sh       | 1                 | -          |
| 3     | walter-seed.sh (NEW)       | -                 | 1, 2       |

## Risk Assessment

| Risk                                                     | Mitigation                                                              |
| -------------------------------------------------------- | ----------------------------------------------------------------------- |
| Bare repo init on Walter fails (disk space, permissions) | \_ensure_repo checks disk space, returns clear error                    |
| Synchronous push slows down commit hook                  | Push has 10s timeout — worst case adds 10s to hook                      |
| Seed script overwhelms Walter with 37 inits              | Sequential init with 1s delay between                                   |
| Projects without vitest spam Walter with failures        | Walter already handles this — returns "no test runner found" gracefully |
