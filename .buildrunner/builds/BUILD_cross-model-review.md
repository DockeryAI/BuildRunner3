# Build: cross-model-review

**Created:** 2026-04-13
**Status:** Phases 1-3 Complete — Phase 3 In Progress
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
| 5     | /2nd skill, /codex-do skill, auto-save-session.sh, /begin skill     | -                 | 2 (needs review engine) |

## Phases

### Phase 1: Cursor IDE Setup + Auto-Focus Script

**Status:** ✅ COMPLETE
**Goal:** Cursor replaces VS Code as daily IDE with BR3-optimized workspace. Auto-focus script opens changed files after each phase build.

**Files:**

- `~/.buildrunner/scripts/cursor-review-focus.sh` (NEW)
- `~/.buildrunner/cursor-workspace.code-workspace` (NEW)

**Blocked by:** None

**Deliverables:**

- [x] Cursor workspace file with BR3 project paths, .buildrunner/ state visible, node_modules/dist excluded
- [x] cursor-review-focus.sh: reads git diff --name-only from last phase, opens all changed files in Cursor via `cursor <file1> <file2> ...` CLI (user uses Cursor's built-in Source Control panel for diff view)
- [x] Hook integration: wire cursor-review-focus.sh as optional post-phase trigger (runs after auto-save-session.sh completes, only on Muddy)
- [x] Cursor settings.json: dark theme, minimap off, diff editor default open, git decorations enabled, Claude Code extension configured
- [x] Verification: Cursor launches, Claude Code terminal works, auto-focus opens correct files after a test commit

**Success Criteria:** After a phase builds, Cursor automatically shows the changed files without Byron doing anything.

### Phase 2: Cross-Model Review Engine

**Status:** ✅ COMPLETE
**Goal:** Python module takes git diff + BUILD spec context, sends to Codex CLI (GPT-4o), returns structured review findings matching adversarial-review.sh JSON format.

**Files:**

- `core/cluster/cross_model_review.py` (NEW)
- `core/cluster/cross_model_review_config.json` (NEW)
- `~/.buildrunner/scripts/cross-model-review.sh` (NEW)
- `~/.buildrunner/scripts/adversarial-review.sh` (MODIFY) — add Codex CLI backend

**Blocked by:** None (different files than Phase 1)

**Deliverables:**

- [x] cross_model_review.py: accepts diff text + spec context, calls Codex CLI (primary) or OpenRouter API `openai/gpt-4o` (fallback), returns JSON array of {finding, severity} matching adversarial-review.sh format
- [x] Multi-backend support: Codex CLI (primary, free with ChatGPT Plus), OpenRouter API (fallback if Codex rate-limited), Below local inference (future — endpoint configurable)
- [x] SHA-based caching: skip review if same commit SHA already reviewed, cache in ~/.buildrunner/cache/cross-reviews/
- [x] Budget tracking for OpenRouter fallback: monthly spend cap (configurable, default $50), reads/writes ~/.buildrunner/logs/cross-review-spend.json
- [x] Structured review prompt: asks for bugs, security issues, architecture concerns, spec compliance — mirrors the 5 adversarial failure modes (requirement conflicts, fabricated APIs, broken execution order, missing edge cases, nonexistent files)
- [x] cross-model-review.sh: shell wrapper that takes same args as adversarial-review.sh (plan_file, project_root), calls Python module, outputs JSON to stdout
- [x] Error handling: Codex CLI timeout (60s), rate limit detection + automatic OpenRouter fallback, malformed response fallback to warning-level finding
- [x] mkdir -p ~/.buildrunner/cache/cross-reviews/ on init (ensure cache dir exists before first write)
- [x] Unit tests: test diff parsing, response parsing, cache hit/miss, budget enforcement, backend fallback
- [x] AMENDMENT: adversarial-review.sh Codex CLI backend — add `--backend codex` flag to adversarial-review.sh. When set, runs the adversarial prompt through Codex CLI locally on Muddy instead of SSH to Otis + `claude --print`. Same JSON output format, same prompt structure. Benefits: true cross-model review (GPT-4o reviewing Claude's plan, not Claude reviewing Claude), runs locally (no SSH auth failures, no 8GB memory limits, no 360s timeout issues), more reliable than Otis. Otis/Claude remains the default backend; `--backend codex` is opt-in. /spec and /amend skills updated to pass `--backend codex` when Otis is unreachable or when cross-model review is preferred.

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

**Status:** ✅ COMPLETE
**Goal:** New dashboard panel showing cross-model review results alongside existing review queue. Review convergence view shows agreement/disagreement between reviewers.

**Files:**

- `~/.buildrunner/dashboard/public/index.html` (MODIFY)
- `~/.buildrunner/dashboard/events.mjs` (MODIFY)
- `~/.buildrunner/dashboard/integrations/cross-review.mjs` (NEW)
- `~/.buildrunner/dashboard/integrations/reviews.mjs` (MODIFY)

**Blocked by:** Phase 3 (needs dispatch data flowing to cross-review.log)

**Deliverables:**

- [x] cross-review.mjs: reads cross-review.log, parses entries, exposes via REST API (/api/cross-reviews, /api/cross-reviews/:sha)
- [x] Dashboard panel: "Cross-Model Review" showing last 10 reviews with status (pass/warn/block), model used, cost, findings expandable
- [x] Review convergence indicator: when Otis adversarial AND cross-model both flag the same area (matched by file path + severity), highlight as high-confidence finding
- [x] Unified review status in existing Review Queue panel: shows combined pass/fail from all sources, not just Otis
- [x] SSE event: cross_review_complete pushed when review finishes, dashboard auto-updates
- [x] Cost tracker widget: running monthly spend on OpenRouter fallback reviews (reads cross-review-spend.json). Shows $0 when Codex CLI handles all reviews.

**Success Criteria:** Dashboard shows cross-model review results in real-time. Review queue shows unified status. Cost tracking visible.

### Phase 5: Codex Power Features — Second Opinion & Delegation _(added: 2026-04-13)_

**Status:** pending
**Goal:** Expose the Phase 2 Codex engine as user-facing workflows that extract the proven second-opinion value beyond automated review.

**Files:**

- `~/.claude/skills/2nd/SKILL.md` (NEW)
- `~/.claude/skills/codex-do/SKILL.md` (NEW)
- `~/.buildrunner/scripts/auto-save-session.sh` (MODIFY — high-risk diff detection)
- `~/.claude/skills/begin/SKILL.md` (MODIFY — plan critique gate)
- `.buildrunner/codex-briefs/` (NEW directory, auto-created)

**Blocked by:** Phase 2 (needs `cross_model_review.py` + Codex CLI auth path)

**Deliverables:**

- [ ] `/2nd` skill — stuck-debug second opinion _(added: 2026-04-13)_. Gathers: goal from current conversation, what Claude has tried (recent Bash/edits/tool calls), full contents of suspect files (not diffs), raw error output + relevant log slices, Claude's current hypothesis stated explicitly, the user's one-line question. Writes brief to `.buildrunner/codex-briefs/<ts>.md`, invokes `codex exec` with repo access, returns a **disagreement diff** (which of Claude's assumptions Codex rejected, what it proposes, confidence). Advisory only — never auto-applies. Research backing: models fix external errors 64.5% more reliably than their own (Zylos, Feb 2026).
- [ ] Plan critique gate in `/begin` _(added: 2026-04-13)_. Before phase execution begins, fire `cross-model-review.sh` against the BUILD spec + architecture plan (not just diffs). Runs in parallel with existing adversarial review. Blocks on blocker-severity findings, warns otherwise. Different model = uncorrelated blind spots on design decisions.
- [ ] Auto-trigger on high-risk diffs _(added: 2026-04-13)_. Pre-commit hook in `auto-save-session.sh` that detects high-risk file patterns (`supabase/migrations/**`, RLS policies, `**/auth/**`, `**/payments/**`, edge functions with DB writes) and auto-fires `/2nd` brief generation + Codex review synchronously (blocking commit on blockers). Never-forget insurance on the changes that matter most.
- [ ] `/codex-do <task>` skill — terminal/DevOps delegation _(added: 2026-04-13)_. For pure shell/CI/deploy/Dockerfile/bash-script work, delegate to Codex CLI instead of Claude. Codex measured 77.3% vs Claude 65.4% on Terminal-Bench 2.0. Skill wraps `codex exec` with project context, streams output, commits on approval. Scope-limited to terminal-shaped tasks — NOT a general execution replacement.
- [ ] `/2nd --adversarial` mode — "convince me I'm wrong" _(added: 2026-04-13)_. Flag on the `/2nd` skill that forces Codex to argue the contrary position on a fix/architecture decision Claude is confident about. Brief framing instructs Codex: "The prior engineer believes X. Assume they are wrong. What did they miss?" Exploits external-attribution bias for maximum pushback. Use on untestable decisions (security tradeoffs, architecture calls).

**Success Criteria:** `/2nd` produces a usable brief + Codex response in < 60s on a stuck-debug case. `/begin` blocks when Codex flags a blocker in the plan critique. Pre-commit hook fires automatically on a migration change without manual invocation. `/codex-do "write a deploy script for X"` produces working shell output. `/2nd --adversarial` returns a substantively contrary read, not agreement.

---

## Out of Scope (Future)

- Below as local review backend (needs 3090 upgrade for quality models)
- Multi-model rotation (cycling GPT-4o / Gemini / Mistral per review for diversity)
- Blind spot profiling (tracking which model catches which bug types over time)
- Cursor agent orchestration (BR3 dispatch system is already more capable)
- Copilot integration (autocomplete for non-coders adds no value)
- Antigravity integration (not stable enough)

## Session Log

[Will be updated by /begin]
