# Build: cross-model-review

**Created:** 2026-04-13
**Status:** Phase 1 In Progress
**Deploy:** local — Muddy scripts + dashboard (deploy via SSH after dashboard phases)

## Overview

Automated cross-model code review pipeline using Codex CLI (ChatGPT Plus) to check Claude Code's output, plus Cursor IDE as a visual review surface. Adds a second AI opinion to every phase build and gives Byron eyes on the code — all fully automated in the existing dispatch chain.

## Parallelization Matrix

| Phase | Key Files                                                           | Can Parallel With | Blocked By              |
| ----- | ------------------------------------------------------------------- | ----------------- | ----------------------- |
| 1     | cursor-workspace, cursor-review-focus.sh                            | 2                 | -                       |
| 2     | cross_model_review.py, cross-model-review.sh, adversarial-review.sh | 1                 | -                       |
| 3     | auto-save-session.sh, unified-review-gate.sh                        | -                 | 2 (needs review script) |
| 4     | dashboard index.html, events.mjs, cross-review.mjs                  | -                 | 3 (needs data flowing)  |

## Phases

### Phase 1: Cursor IDE Setup + Auto-Focus Script

**Status:** not_started
**Goal:** Cursor replaces VS Code as daily IDE with BR3-optimized workspace. Auto-focus script opens changed files after each phase build.

**Files:**

- `~/.buildrunner/scripts/cursor-review-focus.sh` (NEW)
- `~/.buildrunner/cursor-workspace.code-workspace` (NEW)

**Blocked by:** None

**Deliverables:**

- [ ] Cursor workspace file with BR3 project paths, .buildrunner/ state visible, node_modules/dist excluded
- [ ] cursor-review-focus.sh: reads git diff --name-only from last phase, opens all changed files in Cursor via `cursor <file1> <file2> ...` CLI (user uses Cursor's built-in Source Control panel for diff view)
- [ ] Hook integration: wire cursor-review-focus.sh as optional post-phase trigger (runs after auto-save-session.sh completes, only on Muddy)
- [ ] Cursor settings.json: dark theme, minimap off, diff editor default open, git decorations enabled, Claude Code extension configured
- [ ] Verification: Cursor launches, Claude Code terminal works, auto-focus opens correct files after a test commit

**Success Criteria:** After a phase builds, Cursor automatically shows the changed files without Byron doing anything.

### Phase 2: Cross-Model Review Engine

**Status:** not_started
**Goal:** Python module takes git diff + BUILD spec context, sends to Codex CLI (GPT-4o), returns structured review findings matching adversarial-review.sh JSON format.

**Files:**

- `core/cluster/cross_model_review.py` (NEW)
- `core/cluster/cross_model_review_config.json` (NEW)
- `~/.buildrunner/scripts/cross-model-review.sh` (NEW)
- `~/.buildrunner/scripts/adversarial-review.sh` (MODIFY) — add Codex CLI backend

**Blocked by:** None (different files than Phase 1)

**Deliverables:**

- [ ] cross_model_review.py: accepts diff text + spec context, calls Codex CLI (primary) or OpenRouter API `openai/gpt-4o` (fallback), returns JSON array of {finding, severity} matching adversarial-review.sh format
- [ ] Multi-backend support: Codex CLI (primary, free with ChatGPT Plus), OpenRouter API (fallback if Codex rate-limited), Below local inference (future — endpoint configurable)
- [ ] SHA-based caching: skip review if same commit SHA already reviewed, cache in ~/.buildrunner/cache/cross-reviews/
- [ ] Budget tracking for OpenRouter fallback: monthly spend cap (configurable, default $50), reads/writes ~/.buildrunner/logs/cross-review-spend.json
- [ ] Structured review prompt: asks for bugs, security issues, architecture concerns, spec compliance — mirrors the 5 adversarial failure modes (requirement conflicts, fabricated APIs, broken execution order, missing edge cases, nonexistent files)
- [ ] cross-model-review.sh: shell wrapper that takes same args as adversarial-review.sh (plan_file, project_root), calls Python module, outputs JSON to stdout
- [ ] Error handling: Codex CLI timeout (60s), rate limit detection + automatic OpenRouter fallback, malformed response fallback to warning-level finding
- [ ] mkdir -p ~/.buildrunner/cache/cross-reviews/ on init (ensure cache dir exists before first write)
- [ ] Unit tests: test diff parsing, response parsing, cache hit/miss, budget enforcement, backend fallback
- [ ] AMENDMENT: adversarial-review.sh Codex CLI backend — add `--backend codex` flag to adversarial-review.sh. When set, runs the adversarial prompt through Codex CLI locally on Muddy instead of SSH to Otis + `claude --print`. Same JSON output format, same prompt structure. Benefits: true cross-model review (GPT-4o reviewing Claude's plan, not Claude reviewing Claude), runs locally (no SSH auth failures, no 8GB memory limits, no 360s timeout issues), more reliable than Otis. Otis/Claude remains the default backend; `--backend codex` is opt-in. /spec and /amend skills updated to pass `--backend codex` when Otis is unreachable or when cross-model review is preferred.

**Success Criteria:** `cross-model-review.sh plan.md /project/root` returns JSON findings from Codex/GPT-4o. Same format as adversarial review. Cached on SHA. `adversarial-review.sh --backend codex plan.md /project/root` runs adversarial review through Codex CLI instead of Otis.

### Phase 3: Dispatch Chain Integration + Unified Gate

**Status:** not_started
**Goal:** Cross-model review runs locally on Muddy as background process after commits. Unified review gate collects all three review sources into one report.

**Files:**

- `~/.buildrunner/scripts/auto-save-session.sh` (MODIFY)
- `~/.buildrunner/scripts/unified-review-gate.sh` (NEW)
- `~/.buildrunner/logs/cross-review.log` (NEW, auto-created)

**Blocked by:** Phase 2 (needs cross-model-review.sh to exist)

**Deliverables:**

- [ ] auto-save-session.sh modification: add cross-model-review.sh as LOCAL background process on Muddy (`~/.buildrunner/scripts/cross-model-review.sh "$DIFF" "$PROJECT_ROOT" >> ~/.buildrunner/logs/cross-review.log 2>&1 &`), fire-and-forget alongside existing HTTP dispatches
- [ ] cross-review.log format: timestamp, commit SHA, model used, findings JSON, cost, duration — one entry per review
- [ ] unified-review-gate.sh: collects from three INDEPENDENT sources — Walter test results (via Walter API /api/results/:sha or test_results.db), Otis adversarial (run separately by /begin and /autopilot skills, NOT by auto-save), cross-model (cross-review.log). Each source has its own trigger — the gate READS results, doesn't trigger them.
- [ ] Unified report format: three sections (Tests / Adversarial / Cross-Model), blocker count, overall pass/fail, written to ~/.buildrunner/logs/unified-review.md. Missing sections shown as "pending" or "skipped"
- [ ] Gate logic: if ANY source has a blocker-severity finding, overall status = BLOCKED. Warnings listed but non-blocking.
- [ ] Fallback: if cross-model review times out or fails, gate proceeds with available sources only (degraded but not stuck)

**Success Criteria:** After a commit, cross-model review runs locally in background. Unified gate produces combined report from all available sources. Gate blocks on blockers.

### Phase 4: Dashboard Panel + Review Convergence

**Status:** not_started
**Goal:** New dashboard panel showing cross-model review results alongside existing review queue. Review convergence view shows agreement/disagreement between reviewers.

**Files:**

- `~/.buildrunner/dashboard/public/index.html` (MODIFY)
- `~/.buildrunner/dashboard/events.mjs` (MODIFY)
- `~/.buildrunner/dashboard/integrations/cross-review.mjs` (NEW)
- `~/.buildrunner/dashboard/integrations/reviews.mjs` (MODIFY)

**Blocked by:** Phase 3 (needs dispatch data flowing to cross-review.log)

**Deliverables:**

- [ ] cross-review.mjs: reads cross-review.log, parses entries, exposes via REST API (/api/cross-reviews, /api/cross-reviews/:sha)
- [ ] Dashboard panel: "Cross-Model Review" showing last 10 reviews with status (pass/warn/block), model used, cost, findings expandable
- [ ] Review convergence indicator: when Otis adversarial AND cross-model both flag the same area (matched by file path + severity), highlight as high-confidence finding
- [ ] Unified review status in existing Review Queue panel: shows combined pass/fail from all sources, not just Otis
- [ ] SSE event: cross_review_complete pushed when review finishes, dashboard auto-updates
- [ ] Cost tracker widget: running monthly spend on OpenRouter fallback reviews (reads cross-review-spend.json). Shows $0 when Codex CLI handles all reviews.

**Success Criteria:** Dashboard shows cross-model review results in real-time. Review queue shows unified status. Cost tracking visible.

## Out of Scope (Future)

- Below as local review backend (needs 3090 upgrade for quality models)
- Multi-model rotation (cycling GPT-4o / Gemini / Mistral per review for diversity)
- Blind spot profiling (tracking which model catches which bug types over time)
- Cursor agent orchestration (BR3 dispatch system is already more capable)
- Copilot integration (autocomplete for non-coders adds no value)
- Antigravity integration (not stable enough)

## Session Log

[Will be updated by /begin]
