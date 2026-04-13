# Build: Cross-Model Review Pipeline + Cursor Visibility

**Purpose:** Add automated cross-model code review (GPT-4o via OpenRouter) into BR3's dispatch chain, and set up Cursor as the visual review surface — giving Byron eyes on every phase build without copy-pasting anything.

**Target Users:** Byron (solo builder, non-coder, needs visibility into what AI builds)

**Tech Stack:** Python (OpenRouter API), Node.js (dashboard integration), Shell (dispatch chain), Cursor IDE

---

## Phase 1: Cursor IDE Setup + Auto-Focus Script

**Goal:** Cursor replaces VS Code as daily IDE with a BR3-optimized workspace and an auto-focus script that opens changed files after each phase.

**Files:**

- `~/.buildrunner/scripts/cursor-review-focus.sh` (NEW) — post-phase hook that opens changed files in Cursor's diff view
- `~/.buildrunner/cursor-workspace.code-workspace` (NEW) — BR3 workspace config with recommended panel layout, excluded paths, and review-focused settings

**Blocked by:** None

**Deliverables:**

- [ ] Cursor workspace file with BR3 project paths, .buildrunner/ state visible, node_modules/dist excluded
- [ ] cursor-review-focus.sh: reads git diff --name-only from last phase, opens all changed files in Cursor via `cursor <file1> <file2> ...` CLI (opens files directly; user uses Cursor's built-in Source Control panel for diff view)
- [ ] Hook integration: wire cursor-review-focus.sh as optional post-phase trigger (runs after auto-save-session.sh completes, only on Muddy)
- [ ] Cursor settings.json: dark theme, minimap off, diff editor default open, git decorations enabled, Claude Code extension configured
- [ ] Verification: Cursor launches, Claude Code terminal works, auto-focus opens correct files after a test commit

**Success Criteria:** After a phase builds, Cursor automatically shows the changed files in diff view without Byron doing anything.

---

## Phase 2: Cross-Model Review Engine

**Goal:** A Python module that takes a git diff + BUILD spec context, sends it to a non-Claude model via OpenRouter, and returns structured review findings in the same JSON format as adversarial-review.sh.

**Files:**

- `core/cluster/cross_model_review.py` (NEW) — review engine: diff parsing, API call, response parsing, caching
- `core/cluster/cross_model_review_config.json` (NEW) — model selection, budget cap, prompt templates
- `~/.buildrunner/scripts/cross-model-review.sh` (NEW) — shell wrapper matching adversarial-review.sh interface

**Blocked by:** None (different files than Phase 1)

**Deliverables:**

- [ ] cross_model_review.py: accepts diff text + spec context, calls OpenRouter API (model ID: `openai/gpt-4o` — OpenRouter uses provider-prefixed IDs), returns JSON array of {finding, severity} matching adversarial-review.sh format
- [ ] Multi-backend support: OpenRouter API (primary), Codex CLI (if available, free with ChatGPT Pro), Below local inference (future — endpoint configurable)
- [ ] SHA-based caching: skip review if same commit SHA already reviewed, cache in ~/.buildrunner/cache/cross-reviews/
- [ ] Budget tracking: monthly spend cap (configurable, default $50), reads/writes ~/.buildrunner/logs/cross-review-spend.json
- [ ] Structured review prompt: asks for bugs, security issues, architecture concerns, spec compliance — mirrors the 5 adversarial failure modes
- [ ] cross-model-review.sh: shell wrapper that takes same args as adversarial-review.sh (plan_file, project_root), calls Python module, outputs JSON to stdout
- [ ] Error handling: OpenRouter timeout (30s), rate limit retry (1x), malformed response fallback to warning-level finding
- [ ] Unit tests: test diff parsing, response parsing, cache hit/miss, budget enforcement

**Success Criteria:** `cross-model-review.sh plan.md /project/root` returns JSON findings from GPT-4o. Same format as adversarial review. Cached on SHA. Under budget cap.

---

## Phase 3: Dispatch Chain Integration + Unified Gate

**Goal:** Wire cross-model review into auto-save-session.sh as a local background process on Muddy (not a cluster node dispatch). Build a unified review gate that collects from all three review sources into one report.

**Files:**

- `~/.buildrunner/scripts/auto-save-session.sh` (MODIFY) — add cross-model review as local background process alongside existing Walter/Lockwood/Lomax HTTP dispatches
- `~/.buildrunner/scripts/unified-review-gate.sh` (NEW) — collects results from all review sources, generates combined report
- `~/.buildrunner/logs/cross-review.log` (NEW, auto-created) — cross-model review results

**Blocked by:** Phase 2 (needs cross-model-review.sh to exist)

**Deliverables:**

- [ ] auto-save-session.sh modification: add cross-model-review.sh as a LOCAL background process on Muddy (not an HTTP dispatch to a node — runs `~/.buildrunner/scripts/cross-model-review.sh "$DIFF" "$PROJECT_ROOT" >> ~/.buildrunner/logs/cross-review.log 2>&1 &`), fire-and-forget alongside existing HTTP dispatches
- [ ] cross-review.log format: timestamp, commit SHA, model used, findings JSON, cost, duration — one entry per review
- [ ] unified-review-gate.sh: collects from three INDEPENDENT sources: Walter test results (via Walter API /api/results/:sha or test_results.db), Otis adversarial (run separately by /begin and /autopilot skills, NOT by auto-save), cross-model (cross-review.log). Each source has its own trigger — the gate READS results, doesn't trigger them.
- [ ] Unified report format: three sections (Tests / Adversarial / Cross-Model), blocker count, overall pass/fail, written to ~/.buildrunner/logs/unified-review.md. Missing sections shown as "pending" or "skipped" (not all three run on every commit)
- [ ] Gate logic: if ANY source has a blocker-severity finding, overall status = BLOCKED. Warnings listed but non-blocking.
- [ ] Fallback: if cross-model review times out or fails, gate proceeds with available sources only (degraded but not stuck)
- [ ] mkdir -p ~/.buildrunner/cache/cross-reviews/ in cross-model-review.sh init (ensure cache dir exists before first write)

**Success Criteria:** After a commit, cross-model review runs locally in background. Unified gate can be invoked to collect all available review results into one report. Gate blocks on blockers from any source.

---

## Phase 4: Dashboard Panel + Review Convergence

**Goal:** New dashboard panel showing cross-model review results alongside existing review queue. Review convergence view shows agreement/disagreement between reviewers.

**Files:**

- `~/.buildrunner/dashboard/public/index.html` (MODIFY) — add Cross-Model Review panel
- `~/.buildrunner/dashboard/events.mjs` (MODIFY) — add SSE event type for cross-model reviews
- `~/.buildrunner/dashboard/integrations/cross-review.mjs` (NEW) — data source for cross-model review results
- `~/.buildrunner/dashboard/integrations/reviews.mjs` (MODIFY) — integrate unified gate into existing review approval flow

**Blocked by:** Phase 3 (needs dispatch data flowing to cross-review.log)

**Deliverables:**

- [ ] cross-review.mjs: reads cross-review.log, parses entries, exposes via REST API (/api/cross-reviews, /api/cross-reviews/:sha)
- [ ] Dashboard panel: "Cross-Model Review" showing last 10 reviews with status (pass/warn/block), model used, cost, findings expandable
- [ ] Review convergence indicator: when Otis adversarial AND cross-model both flag the same area, highlight as high-confidence finding
- [ ] Unified review status in existing Review Queue panel: shows combined pass/fail from all sources, not just Otis
- [ ] SSE event: cross_review_complete pushed when review finishes, dashboard auto-updates
- [ ] Cost tracker widget: running monthly spend on cross-model reviews (reads cross-review-spend.json)

**Success Criteria:** Dashboard shows cross-model review results in real-time. Review queue shows unified status. User can see cost tracking.

---

## Out of Scope (Future)

- Below as local review backend (needs 3090 upgrade for quality models)
- Multi-model rotation (cycling GPT-4o / Gemini / Mistral per review for diversity)
- Blind spot profiling (tracking which model catches which bug types over time)
- Cursor agent orchestration (BR3's dispatch system is already more capable)
- Copilot integration (autocomplete for non-coders adds no value)
- Antigravity (not ready, stability issues)

---

## Parallelization Matrix

| Phase | Key Files                                          | Can Parallel With | Blocked By              |
| ----- | -------------------------------------------------- | ----------------- | ----------------------- |
| 1     | cursor-workspace, cursor-review-focus.sh           | 2                 | -                       |
| 2     | cross_model_review.py, cross-model-review.sh       | 1                 | -                       |
| 3     | auto-save-session.sh, unified-review-gate.sh       | -                 | 2 (needs review script) |
| 4     | dashboard index.html, events.mjs, cross-review.mjs | -                 | 3 (needs data flowing)  |

**Phases 1 and 2 can run in parallel.** Phases 3 and 4 are sequential after Phase 2.

---

**Total Phases:** 4
**Parallelizable:** Phase 1 + Phase 2 simultaneously
**Estimated cost impact:** ~$5-15/mo OpenRouter API (GPT-4o reviews), $20/mo Cursor Pro, $0 if Codex CLI works as review backend
