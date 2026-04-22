# Codex-Optimized BUILD Spec: universal-role-routing

**Source Plan File:**    .buildrunner/plans/spec-codex-draft-plan.md
**Source Plan SHA:**     3da6d8f2f927e6857143add94458d856a3045767062d246026994ce44a089d1b
**Adversarial Review Verdict:** BYPASSED:.buildrunner/adversarial-reviews/phase-1-20260422T140715Z.json


**Purpose:** Make the BR3 cluster role matrix universal and non-optional. Every user prompt — spec'd or ad-hoc — is classified, routed, prompt-reshaped, context-bundled, dispatched, reviewed in parallel by Sonnet 4.6 + GPT-5.4, and arbitrated by Opus 4.7 on disagreement in exactly one round with no user escalation.
**Target Users:** Claude Code operators (interactive turns), autopilot phase dispatch, `/spec` / `/amend` / `/spec-codex` / `/amend-codex` planners.
**Tech Stack:** Bash hooks (UserPromptSubmit + PreToolUse), YAML config, Python (cross_model_review refactor, cache policy, metrics), FastAPI on Jimmy (`:4500/context/{model}`), React/Vite UI panel, Anthropic + OpenAI SDKs, Lockwood (SQLite telemetry).
**Codex Model:** GPT-5.4 default. GPT-5.3-Codex for Phase 5 (terminal-heavy hook wiring).
**Effort Level:** Medium default. xHigh on Phase 1 (single source of truth — everything inherits from it), Phase 5 (PreToolUse gate — security boundary), Phase 6 (arbiter correctness — governance), Phase 10 (enforcement flip — irreversible).

---

## Non-Negotiable Rules (applied throughout)

1. **Opus plans are reviewed by Sonnet 4.6 + GPT-5.4 in parallel, exactly one round. Opus 4.7 arbitrates on disagreement and commits the decision. No rebuttal rounds. No escalation to user.** Applies to every plan Opus produces — spec phases, architecture decisions, ad-hoc plans. The arbiter ALWAYS commits a final verdict, even on internal error (fail-safe BLOCK with logged arbiter reasoning).
2. Codex default effort = `medium` (xhigh reserved for security/adversarial review).
3. Opus 4.7 default effort = `xhigh` for planning/coding, `medium` for classification/filter passes.
4. Four-element prompt shape mandatory for every Codex dispatch: Goal / Context / Constraints / Done-When. Missing Done-When → refuse to dispatch.
5. Retrieval-heavy work pinned to Sonnet 4.6 (4.7 regressed 91.9 → 59.2% MRCR).
6. 3-breakpoint cache: static system → static tools → sliding window → dynamic tail. Dynamic content never placed before a breakpoint.
7. No `temperature` / `top_p` / `top_k` / prefills / `budget_tokens` on 4.7 (hard 400). Adaptive thinking with `display: summarized` on every 4.7 call.
8. Escape hatch: `BR3_FORCE_BUILDER=claude` env var for deliberate override, logged to `decisions.log` every use.

---

### Phase 1: Single Source of Truth (Role Matrix Config)

**Goal:** One YAML file defines the entire cluster role matrix; `load-role-matrix.sh` resolves it with inheritance merge; every downstream script reads from the resolved output.
**Effort:** xHigh
**Files:**

- `~/.buildrunner/config/default-role-matrix.yaml` (NEW)
- `~/.buildrunner/scripts/load-role-matrix.sh` (MODIFY — add inheritance merge)
- `~/.buildrunner/scripts/_dispatch-core.sh` (MODIFY — consume resolved matrix)
- `~/.buildrunner/config/role-matrix.schema.json` (NEW — JSON Schema validator)
- `tests/config/test_role_matrix_load.bats` (NEW)

**Blocked by:** None
**Can parallelize:** No (gate for everything else)

### Task 1.1: Author `default-role-matrix.yaml`

- **Goal:** Authoritative YAML capturing every bucket → model → effort → reviewer → arbiter mapping.
- **Context:** Buckets enumerated in Phase 2 (`planning`, `architecture`, `backend-build`, `terminal-build`, `ui-build`, `review`, `classification`, `retrieval`, `qa`). Each bucket names primary builder, reviewers (always Sonnet 4.6 + GPT-5.4 for plans), arbiter (always Opus 4.7), effort, cache-policy name.
- **Constraints:** YAML 1.2. No secrets. Include `version: 1` at top. File permissions `0644`.
- **Done-When:** `python3 -c "import yaml; yaml.safe_load(open('$HOME/.buildrunner/config/default-role-matrix.yaml'))"` exits 0 AND `yq '.buckets | length' $HOME/.buildrunner/config/default-role-matrix.yaml` returns `9`.

### Task 1.2: JSON Schema for the matrix

- **Goal:** Validator catches malformed matrices before any dispatch runs.
- **Context:** Schema constrains bucket names, required fields (`primary`, `reviewers`, `arbiter`, `effort`), allowed models.
- **Constraints:** Draft-07. Reject unknown top-level keys.
- **Done-When:** `python3 -m jsonschema -i $HOME/.buildrunner/config/default-role-matrix.yaml $HOME/.buildrunner/config/role-matrix.schema.json` (after YAML→JSON conversion in a pipe using `os.path.expanduser` in the helper) exits 0; a tampered copy with a missing `arbiter` key exits non-zero.

### Task 1.3: Inheritance merge in `load-role-matrix.sh`

- **Goal:** Spec-level inherit blocks (3-line YAML) merge on top of the default matrix at load time.
- **Context:** Planners (Phase 7) emit `inherit: default-role-matrix` with optional `overrides:`. Loader deep-merges overrides into the default.
- **Constraints:** Deep-merge via `yq eval-all '. as $item ireduce ({}; . * $item)'` or equivalent Python merger. Overrides cannot remove required fields — warn and ignore.
- **Done-When:** A spec with `overrides: {buckets: {ui-build: {effort: xhigh}}}` loads and `effort` for `ui-build` is `xhigh` while all other buckets retain default effort.

### Task 1.4: Resolved matrix cache

- **Goal:** Loader writes resolved matrix to `$HOME/.buildrunner/config/.resolved-role-matrix.json` for all scripts to read.
- **Constraints:** Write atomically (temp + rename). Mode `0600`. Include `resolved_at` timestamp.
- **Done-When:** After any loader run, the cached JSON exists, is valid JSON, and `jq .resolved_at` returns an ISO-8601 string within last 5 seconds.

### Task 1.5: `_dispatch-core.sh` reads resolved matrix

- **Goal:** The dispatch core pulls bucket → model/effort from the cached resolved matrix, not from ad-hoc env vars.
- **Context:** `~/.buildrunner/scripts/_dispatch-core.sh` already exists; this task adds a sourcing step that fails if the cached JSON is missing or stale (>24h).
- **Constraints:** Pre-check file existence before sourcing; exit 2 with clear message if missing. Do NOT fall back to hardcoded defaults.
- **Done-When:** With the cache present, `BUCKET=ui-build _dispatch-core.sh lookup` prints the correct model. With the cache deleted, it exits 2 with `role-matrix cache missing` in stderr.

### Task 1.6: bats tests for loader + merger

- **Done-When:** `bats tests/config/test_role_matrix_load.bats` runs 6+ test cases, all green.

**Phase Success Criteria:** Matrix is loadable, schema-validated, cache-resolved, merge-aware. Dispatch core fails closed without it.

**Rollback:** Additive — delete the new files; `load-role-matrix.sh` reverts via git.

---

### Phase 2: Classifier

**Goal:** Every prompt gets a bucket assignment in <50ms via heuristics, with a Haiku fallback for ambiguous input.
**Effort:** Medium
**Files:**

- `~/.buildrunner/scripts/classify-prompt.sh` (NEW)
- `~/.buildrunner/scripts/lib/classifier-heuristics.sh` (NEW — keyword tables)
- `~/.buildrunner/scripts/lib/classifier-haiku.py` (NEW — fallback)
- `tests/classifier/test_classify_prompt.bats` (NEW)
- `tests/classifier/fixtures/` (NEW — 40 labeled prompts)

**Blocked by:** Phase 1
**Can parallelize:** With Phase 3

### Task 2.1: Bucket heuristic rules

- **Goal:** Regex/keyword matcher returns a bucket from prompt text + file extensions touched.
- **Context:** Buckets: `planning` (plan/spec/design), `architecture` (refactor/restructure/arch), `backend-build` (api/db/edge function), `terminal-build` (shell/cli/script/cron), `ui-build` (tsx/jsx/component/panel/page), `review` (review/audit/check), `classification` (classify/tag/route), `retrieval` (search/find/lookup/recall), `qa` (test/spec/bats/playwright).
- **Constraints:** Bash associative arrays. Return first-match-wins. Emit bucket to stdout.
- **Done-When:** `echo "add a new React component" | classify-prompt.sh` prints `ui-build`; `echo "write a bash cron job" | classify-prompt.sh` prints `terminal-build`. `os.path.expanduser` used in any Python helper invoked (never `.replace('~', '$HOME')`).

### Task 2.2: Ambiguity detection

- **Goal:** If heuristics produce 0 matches or 2+ matches with equal weight, classifier escalates to Haiku.
- **Constraints:** No escalation when a single bucket matches uniquely. Emit debug line to stderr on escalation.
- **Done-When:** `echo "make it better" | classify-prompt.sh` escalates (stderr contains `AMBIGUOUS → haiku`).

### Task 2.3: Haiku fallback

- **Goal:** Haiku 4.5 classifies in ≤200ms with structured JSON output.
- **Context:** Endpoint: Anthropic API `claude-haiku-4-5-20251001`. `max_tokens: 120`. System prompt instructs "Respond with ONLY a single JSON object: `{\"bucket\": \"<name>\"}`. No preamble. No markdown fences."
- **Constraints:** 200ms hard timeout. On timeout, truncation, or non-parseable JSON, fall back to `heuristic_default=planning` and log warning. `medium` effort (classification pass, not coding).
- **Done-When:** Unit test: mocked 250ms Haiku → result is `planning` with `fallback=heuristic_default` in stderr. Mocked truncated JSON (no closing brace) → same fallback. Mocked valid `{"bucket":"ui-build"}` → result `ui-build`.

### Task 2.4: Classifier CLI contract

- **Goal:** Stable stdin/stdout contract used by the UserPromptSubmit hook.
- **Constraints:** Stdin: raw prompt text. Stdout: single line `<bucket>\n`. Stderr: debug info. Exit 0 on success, 2 on classifier internal error (never on ambiguity — that's a successful fallback).
- **Done-When:** Manpage-style `classify-prompt.sh --help` documents the contract; shellcheck clean.

### Task 2.5: Fixture-based accuracy test

- **Goal:** ≥90% accuracy on the 40 labeled prompts.
- **Constraints:** Fixtures in `tests/classifier/fixtures/labeled.tsv` — `prompt\texpected_bucket`.
- **Done-When:** `bats tests/classifier/test_classify_prompt.bats` passes with accuracy ≥0.90 reported.

**Phase Success Criteria:** Classifier returns bucket for any prompt in <50ms heuristic path, <250ms Haiku-fallback path, with ≥90% accuracy.

**Rollback:** Delete classifier scripts; remove tests.

---

### Phase 3: Four-Element Prompt Injector + Context Bundler

**Goal:** Every dispatched prompt is reshaped into Goal/Context/Constraints/Done-When and augmented with the `/context/{model}` bundle from Jimmy.
**Effort:** Medium
**Files:**

- `~/.buildrunner/scripts/inject-four-element.sh` (NEW)
- `~/.buildrunner/scripts/fetch-context-bundle.sh` (NEW)
- `tests/injector/test_inject_four_element.bats` (NEW)

**Blocked by:** Phase 1, Phase 2
**Can parallelize:** With Phase 2 (tasks within)

### Task 3.1: Injector CLI

- **Goal:** Accept classified-prompt input and produce the four-element reshape.
- **Context:** Unified interface: `inject-four-element.sh --route-file <path>` where the route file is JSON containing `{bucket, prompt, user_message}`. No fd 3, no env-var IPC.
- **Constraints:** If `Done-When` cannot be inferred (ad-hoc chat with no verifiable outcome), inject a placeholder `Done-When: user confirms output in next turn` AND set `requires_user_confirmation: true` in the output JSON.
- **Done-When:** `inject-four-element.sh --route-file tests/fixtures/route1.json` emits JSON with keys `goal`, `context`, `constraints`, `done_when`, `requires_user_confirmation` on stdout.

### Task 3.2: Context bundle fetch

- **Goal:** Retrieve the model-specific bundle from Jimmy's `:4500/context/{model}`.
- **Context:** Jimmy IP resolved dynamically via `~/.buildrunner/scripts/cluster-check.sh memory` — never hardcoded.
- **Constraints:** 3s connect timeout, 5s total timeout. On failure, return empty bundle and log warning (graceful degrade — do not block dispatch).
- **Done-When:** With Jimmy up, `fetch-context-bundle.sh claude-opus-4-7` returns JSON with `cache_breakpoints` array. With Jimmy down (simulated), returns `{"bundle": {}, "error": "unreachable"}` and exits 0.

### Task 3.3: Cache-policy shaping

- **Goal:** Output respects the 3-breakpoint cache structure.
- **Context:** Order enforced: static system → static tools → sliding window → dynamic tail. Dynamic content (user prompt, current task state) is always in the tail.
- **Constraints:** Reject any bundle where dynamic content appears before a breakpoint — log `cache-order violation` and repair by moving to tail.
- **Done-When:** Unit test feeds a malformed bundle; injector emits repaired order AND stderr warning.

### Task 3.4: Refusal on missing Done-When for coder buckets

- **Goal:** For `backend-build`, `terminal-build`, `ui-build`, a Done-When that reduces to a placeholder user-confirmation is a hard refusal, not a soft warning.
- **Constraints:** Exit 10 (distinct from exit 2 classifier error) with `DONE-WHEN MISSING: refuse to dispatch` on stderr. Caller hook translates to user-visible message.
- **Done-When:** `--bucket backend-build --no-done-when` → exit 10. `--bucket planning --no-done-when` → exit 0 with `requires_user_confirmation: true`.

### Task 3.5: Single-terminal behavior

- **Goal:** When the CLI is invoked from a single terminal (no orchestrator), exit 10 is caller-visible rather than silent.
- **Constraints:** Reconciled with Task 3.4 — exit 10 IS the single-terminal refusal signal. No separate exit code.
- **Done-When:** Integration test in an interactive shell: exit 10 produces a red-bordered `REFUSED` message.

### Task 3.6: bats tests

- **Done-When:** `bats tests/injector/test_inject_four_element.bats` — 8+ cases including happy path, context-down, done-when-missing for coder, done-when-missing for planner, cache-order violation.

**Phase Success Criteria:** Every dispatched prompt is four-element shaped with a valid cache-ordered context bundle, or refuses cleanly.

**Rollback:** Delete injector + fetch scripts.

---

### Phase 4: UserPromptSubmit Hook (Front Door)

**Goal:** Every user prompt enters the system via a single hook that classifies, routes, and hands off to the correct builder.
**Effort:** Medium
**Files:**

- `~/.buildrunner/hooks/user-prompt-submit-route.sh` (NEW)
- `~/.claude/settings.json` (MODIFY — register hook)
- `$HOME/.buildrunner/routes/` (NEW dir, mode 0700)
- `tests/hooks/test_user_prompt_submit.bats` (NEW)

**Blocked by:** Phase 2, Phase 3

### Task 4.1: Hook script

- **Goal:** Hook receives prompt text, runs classifier, writes a route file, signals the dispatch core.
- **Constraints:** Stdin is the JSON `UserPromptSubmit` event. Output is a single line on stdout consumed by the client.
- **Done-When:** Given a test fixture event, hook writes `$HOME/.buildrunner/routes/<session-id>.json` containing classifier output + route decision.

### Task 4.2: Route file security

- **Goal:** Route files land in a per-user directory with restrictive perms, atomic writes.
- **Context:** Directory `$HOME/.buildrunner/routes/` created at hook install with mode `0700`. Individual files mode `0600`.
- **Constraints:** Write to `<file>.tmp` then `rename(2)`. Never use `/tmp` (world-readable on shared hosts). Rotate: keep last 200, delete older.
- **Done-When:** `stat -f '%p' $HOME/.buildrunner/routes` returns `40700` (or Linux equivalent); a route file stat returns `100600`. A multi-writer fuzz test produces no corrupted files.

### Task 4.3: Hook registration

- **Goal:** `~/.claude/settings.json` registers the hook under `UserPromptSubmit` without clobbering existing entries.
- **Constraints:** Idempotent install — re-running the installer merges by matcher identity. Preserve user's other hooks.
- **Done-When:** `jq '.hooks.UserPromptSubmit | length' ~/.claude/settings.json` ≥1 and contains the new matcher object.

### Task 4.4: Escape hatch

- **Goal:** `BR3_FORCE_BUILDER=claude` bypasses routing and dispatches to Claude directly.
- **Constraints:** Every bypass logs a decision-log line `[DECISION] BR3_FORCE_BUILDER=claude override — <timestamp>` via `br decision log`. Hook still emits the route file for observability (marked `override: true`).
- **Done-When:** With env var set, route file contains `override: true` and decisions.log has a new entry.

### Task 4.5: Hook tests

- **Done-When:** `bats tests/hooks/test_user_prompt_submit.bats` — 6+ cases green, including override path, Jimmy-down, classifier-error (exit-safe, never breaks the user's turn).

**Phase Success Criteria:** Every prompt produces a route file; hook never breaks the user's turn (fails open with warning on internal error).

**Rollback:** Remove hook registration from settings.json; the hook script staying on disk is harmless.

---

### Phase 5: PreToolUse Gate (Writer Tools)

**Goal:** Edit/Write/NotebookEdit are blocked when the route selects a non-Claude builder, forcing Claude to delegate rather than edit directly.
**Effort:** xHigh (security boundary)
**Codex Model:** GPT-5.3-Codex (terminal-heavy task wiring)
**Files:**

- `~/.buildrunner/hooks/pre-tool-use-gate.sh` (NEW)
- `~/.claude/settings.json` (MODIFY)
- `tests/hooks/test_pre_tool_use_gate.bats` (NEW)

**Blocked by:** Phase 4

### Task 5.1: Gate for Edit/Write/NotebookEdit — fail-CLOSED

- **Goal:** When the current session's route file names a non-Claude primary, writer tools are blocked with a clear delegation message.
- **Context:** Route file at `$HOME/.buildrunner/routes/<session-id>.json`. Fail-CLOSED on missing route file for these three writer tools (never silently allow the edit — missing route means something is wrong upstream).
- **Constraints:** Exit non-zero with structured `BLOCKED: route=<bucket> builder=<model>; dispatch via <route>` on stderr. Allow Read/Glob/Grep/Bash etc. to pass freely.
- **Done-When:** Fixture: route file says `builder=gpt-5.4` → Edit call blocked. Route file missing → Edit call blocked (fail-closed). Route file says `builder=claude` → Edit allowed.

### Task 5.2: Route files live in `$HOME/.buildrunner/routes/` (not `/tmp`)

- **Goal:** Gate looks for route files only in the per-user directory.
- **Constraints:** No `/tmp` fallback path. If path resolution fails, fail-closed.
- **Done-When:** `grep -rn "/tmp" ~/.buildrunner/hooks/pre-tool-use-gate.sh` returns zero hits.

### Task 5.3: Allow-list for safe writer paths

- **Goal:** Certain paths are always allowed (decisions.log, route files themselves, scheduled_tasks.lock). Editing these does not represent delegated-build work.
- **Constraints:** Allow-list in a single const at top of the script. Any change requires a comment with justification.
- **Done-When:** Test: route=ui-build attempting to write `.buildrunner/decisions.log` → allowed. Attempting to write `src/components/X.tsx` → blocked.

### Task 5.4: Override surface

- **Goal:** `BR3_FORCE_BUILDER=claude` makes the gate pass-through.
- **Constraints:** Same as Phase 4 — bypass logged to decisions.log.
- **Done-When:** Unit test confirms override path logs and allows the edit.

### Task 5.5: Hook registration

- **Constraints:** Register under `PreToolUse` with matcher `tool in (Edit, Write, NotebookEdit)`. Do not match all tools (performance + confusing UX).
- **Done-When:** `jq '.hooks.PreToolUse[] | select(.matcher | contains("Edit,Write,NotebookEdit"))'` returns the new matcher.

### Task 5.6: Gate tests

- **Done-When:** `bats tests/hooks/test_pre_tool_use_gate.bats` — 10+ cases green. No `/tmp` paths anywhere in tests or script.

**Phase Success Criteria:** Writer tools cannot proceed without a matching route file; Claude is forced to delegate for non-Claude buckets.

**Rollback:** Unregister matcher from settings.json; Edit/Write/NotebookEdit return to unrestricted.

---

### Phase 6: Cross-Model Review — One Round, Opus Arbitrates, No User Escalation

**Goal:** Every Opus-produced plan is reviewed by Sonnet 4.6 + GPT-5.4 in parallel, one round. On disagreement, Opus 4.7 arbitrates and commits the final verdict. No rebuttal rounds, no user escalation, arbiter always commits even on internal error.
**Effort:** xHigh
**Files:**

- `core/cluster/cross_model_review.py` (MODIFY — large refactor)
- `core/cluster/arbiter.py` (NEW — extracted arbiter logic)
- `core/cluster/review_verdict.py` (NEW — verdict schema + writer)
- `tests/review/test_one_round.py` (NEW)
- `tests/review/test_arbiter_always_commits.py` (NEW)
- `tests/review/test_structural_removal.py` (NEW)

**Blocked by:** Phase 1

### Task 6.1: Remove rebuttal rounds AND refactor all callers

- **Goal:** Delete `_run_rebuttal` and every code path (`rebuttal_round`, retry loops, `escalate_to_user`) that referenced it. Refactor `run_three_way_review` (currently at `core/cluster/cross_model_review.py:1683`) to no longer call `_run_rebuttal`.
- **Context:** Current layout: `_run_rebuttal` at line 1276, `run_three_way_review` at line 1683 calls it. Removing the callee without refactoring the caller produces `NameError` at runtime. This task explicitly refactors the caller.
- **Constraints:** `run_three_way_review` new shape: (a) run parallel two-way review, (b) detect disagreement, (c) if disagreement, call `arbiter.arbitrate(...)`, (d) commit verdict. No second pass. Any remaining reference to `_run_rebuttal`, `rebuttal_round`, `retry`, or `escalate_to_user` is a structural defect — grep must return zero hits in `core/cluster/`.
- **Done-When:** `grep -rn "_run_rebuttal\|rebuttal_round\|escalate_to_user" core/cluster/` returns zero hits. `pytest tests/review/test_structural_removal.py` passes — proves `run_three_way_review` imports and runs without `NameError` on a fixture plan.

### Task 6.2: Arbiter ALWAYS commits a verdict

- **Goal:** Arbiter error paths commit a final verdict with logged arbiter reasoning, not a bare BLOCK.
- **Context:** Non-Negotiable Rule #1 requires "Opus arbitrates and commits" — even on Opus API error, we commit a verdict stamped `verdict: BLOCK, reason: arbiter-error, fallback_logic: <which rule fired>`. No silent BLOCKs.
- **Constraints:** Implement circuit breaker: 3 consecutive Opus errors within 60s trip the breaker; while tripped, commit `BLOCK` with `reason: circuit_open` and require human reset (decision-log entry). Outside the breaker, arbiter retries once (Opus-native, in-call) and if that also errors, commits `BLOCK` with `reason: arbiter-error` plus last Opus response payload captured for debugging.
- **Done-When:** `pytest tests/review/test_arbiter_always_commits.py` — cases: (a) Opus 500 → verdict committed with `reason: arbiter-error`, (b) 3 consecutive errors → breaker open, next call commits `reason: circuit_open`, (c) successful arbitration → verdict has full arbiter reasoning text.

### Task 6.3: Parallel reviewers — Sonnet 4.6 + GPT-5.4

- **Goal:** Reviewers run concurrently via asyncio, both must return (or timeout) before arbitration.
- **Constraints:** 60s timeout per reviewer. Partial results (one reviewer timed out) → treat timed-out reviewer as abstention; arbiter commits on remaining reviewer's findings. Never hang on a slow reviewer.
- **Done-When:** Unit test: mocked Sonnet 30s + mocked GPT-5.4 65s → arbiter runs with Sonnet findings only; verdict has `reviewers: [sonnet-4-6], gpt-5-4: timeout`.

### Task 6.4: One-round guard (mechanical)

- **Goal:** `cross_model_review.py --mode plan` refuses to run a second review on the same plan within the same skill invocation.
- **Context:** Skill-level lockfile `~/.buildrunner/locks/review-<plan-hash>.lock`. `BR3_REVIEW_ALLOW_RERUN=1` is the ONLY way to bypass, and it is reserved for human operators (never set by skills).
- **Constraints:** Lockfile removed on skill exit (trap). Violating the guard exits 3 with `ONE-REVIEW-PER-PLAN: rerun not permitted` on stderr.
- **Done-When:** Integration test: two consecutive `--mode plan` calls with identical plan hash → second exits 3. With `BR3_REVIEW_ALLOW_RERUN=1`, second succeeds.

### Task 6.5: BLOCK verdict halts the build

- **Goal:** When the committed verdict is BLOCK, the build halts and the reason is logged. The hook-enforced gate (from the spec-codex skill) reads the verdict and refuses the commit.
- **Constraints:** Verdict file written to `.buildrunner/adversarial-reviews/phase-<N>-<timestamp>.json` includes top-level `pass: <bool>`, `blockers: [...]`, `arbiter_reasoning: <str>`. On BLOCK, `require-adversarial-review.sh` exits non-zero and blocks `git commit`.
- **Done-When:** E2E test: mocked BLOCK verdict → `git commit -m "phase X"` is rejected by the PreToolUse commit gate with `BLOCKED: adversarial review returned pass=false` on stderr.

### Task 6.6: Verdict schema

- **Goal:** `review_verdict.py` defines the single canonical JSON shape.
- **Constraints:** Fields: `pass: bool`, `verdict: enum[PASS, BLOCK]`, `reviewers: [{name, findings, duration_ms, status}]`, `arbiter: {reasoning, duration_ms, status}`, `circuit_state`, `plan_hash`, `review_round: 1` (always), `escalated: false` (always — rule #1).
- **Done-When:** Pydantic model validates a happy-path verdict and rejects `review_round: 2` or `escalated: true`.

**Phase Success Criteria:** Parallel review, single round, arbiter always commits, BLOCK halts build. No `NameError` on any code path. Grep confirms no rebuttal/retry/escalate references remain.

**Rollback:** Revert `core/cluster/cross_model_review.py` via git; arbiter + verdict files deletable (additive).

---

### Phase 7: Planner Inheritance (`/spec`, `/amend`, `/spec-codex`, `/amend-codex`)

**Goal:** Planners emit a 3-line `inherit:` block instead of a full matrix; `load-role-matrix.sh` (Phase 1) merges.
**Effort:** Medium
**Files:**

- `~/.claude/commands/spec.md` (MODIFY)
- `~/.claude/commands/amend.md` (MODIFY)
- `~/.claude/commands/spec-codex.md` (MODIFY)
- `~/.claude/commands/amend-codex.md` (MODIFY)
- `~/.buildrunner/docs/planner-inherit.md` (NEW — reference)

**Blocked by:** Phase 1

### Task 7.1: `/spec` emits inherit block

- **Constraints:** The generated BUILD spec's header includes `role-matrix:\n  inherit: default-role-matrix\n  overrides: {}`. Overrides empty by default; user can fill after review.
- **Done-When:** `grep -n "inherit: default-role-matrix" .buildrunner/builds/BUILD_<test>.md` returns the line.

### Task 7.2: `/amend` preserves inherit block

- **Constraints:** Amend never regenerates the role-matrix block; leaves user edits intact.
- **Done-When:** Diff between pre-amend and post-amend BUILD spec shows no change in the role-matrix header.

### Task 7.3: `/spec-codex` uses Codex-optimized defaults via the same inherit

- **Constraints:** Same 3-line header. Overrides in the generated spec flip default effort to Codex-medium where appropriate.
- **Done-When:** Generated header contains `inherit: default-role-matrix` AND the overrides reflect Codex defaults.

### Task 7.4: `/amend-codex` preserves the inherit block

- **Done-When:** Same as Task 7.2.

### Task 7.5: Visible deprecation notice on legacy matrix blocks

- **Goal:** When a planner sees an old-style inline full matrix in a spec, it prints a deprecation banner as the FIRST LINE of user-facing output (not just the skill body) and offers to convert.
- **Context:** User-visible means stdout of the skill run — this is what the user reads in the terminal. Banner appears before any other output, not buried in skill context.
- **Constraints:** Banner: `DEPRECATED: inline role-matrix found in <path>; reply "convert" to replace with inherit block.` Print on line 1 of stdout.
- **Done-When:** Feeding a legacy spec → skill's first stdout line starts with `DEPRECATED:`.

### Task 7.6: Reference doc

- **Done-When:** `planner-inherit.md` documents the 3-line format with one worked example and the override schema.

**Phase Success Criteria:** All four planners emit/preserve the inherit block; legacy specs trigger a visible deprecation notice.

**Rollback:** Revert the four `.md` skills via git.

---

### Phase 8: Context Bundling + Cache Policy

**Goal:** Canonical cache-policy module plus Jimmy-side `/context/{model}` bundle endpoint, wired to every dispatch.
**Effort:** Medium
**Files:**

- `core/runtime/cache_policy.py` (NEW)
- `core/runtime/__init__.py` (NEW or VERIFY)
- `api/routes/context.py` (MODIFY — `/context/{model}` uses cache_policy)
- `tests/runtime/test_cache_policy.py` (NEW)

**Blocked by:** Phase 3

### Task 8.1: `cache_policy.py` module

- **Goal:** Canonical module that knows the 3-breakpoint shape.
- **Context:** Lives at `core/runtime/cache_policy.py` (runtime concern, not cluster concern). Exposes `shape_bundle(model, static_system, static_tools, sliding_window, dynamic_tail) -> dict` with keys `cache_breakpoints: [i0, i1, i2]` and `segments: [...]`.
- **Constraints:** Pure function. No I/O. No side effects. Type-hinted. Pydantic for validation.
- **Done-When:** `pytest tests/runtime/test_cache_policy.py` — 8+ cases green including malformed inputs.

### Task 8.2: `/context/{model}` uses cache_policy

- **Goal:** The FastAPI handler on Jimmy for `GET /context/{model}` returns a bundle shaped by `cache_policy.shape_bundle`.
- **Constraints:** Handler imports the module. No inline breakpoint logic in the route file.
- **Done-When:** `curl http://10.0.1.106:4500/context/claude-opus-4-7` returns JSON with `cache_breakpoints` array of length 3.

### Task 8.3: No duplicate cache logic elsewhere

- **Goal:** Grep confirms no other module defines cache breakpoints.
- **Constraints:** The ONLY canonical path is `core/runtime/cache_policy.py`. Any stale `core/cluster/cache_policy.py` reference in this repo is a defect — the task fixes references to point at the canonical path.
- **Done-When:** `grep -rn "cache_breakpoints" core/ api/ --include="*.py" | grep -v "core/runtime/cache_policy.py"` returns only CALLERS (imports), not alternative definitions.

### Task 8.4: Injector wiring

- **Goal:** `inject-four-element.sh` (Phase 3) calls `fetch-context-bundle.sh` which hits `/context/{model}` and gets a cache-shaped bundle.
- **Done-When:** Integration test: injector output for `backend-build` includes a `cache_breakpoints` array sourced from the live endpoint.

**Phase Success Criteria:** Bundles are cache-shaped by one canonical module; duplicates removed; injector consumes the live endpoint.

**Rollback:** Revert `api/routes/context.py`; delete new runtime module.

---

### Phase 9: Observability — Metrics + Routing Panel

**Goal:** Every dispatch logs route/builder/bucket/effort/tokens/latency/done-when-outcome to Lockwood; a live UI panel shows the stream.
**Effort:** Medium
**Files:**

- `core/runtime/metrics_schema.py` (NEW)
- `api/routes/metrics.py` (NEW)
- `~/.buildrunner/scripts/lockwood-metrics.sh` (MODIFY — add route/builder/bucket fields)
- `~/.buildrunner/dashboard/public/routing-panel.html` (NEW — matches active vanilla dashboard)
- `~/.buildrunner/dashboard/public/routing-panel.mjs` (NEW)
- `~/.buildrunner/dashboard/events.mjs` (MODIFY — register /routing feed)
- `tests/runtime/test_metrics_schema.py` (NEW)

**Blocked by:** Phase 6

### Task 9.1: Metrics schema

- **Goal:** Canonical Pydantic schema for every dispatch telemetry record.
- **Context:** NEW module at `core/runtime/metrics_schema.py`. Fields: `timestamp`, `session_id`, `bucket`, `builder`, `model`, `effort`, `prompt_tokens`, `output_tokens`, `latency_ms`, `done_when_passed: bool`, `verdict: enum[passed, blocked, overridden]`, `override_reason?`.
- **Constraints:** Pydantic. Frozen model. No I/O.
- **Done-When:** `pytest tests/runtime/test_metrics_schema.py` — schema validates a happy-path record and rejects records missing `done_when_passed`.

### Task 9.2: Metrics POST endpoint

- **Goal:** `POST /api/metrics/dispatch` on Muddy's API accepts a metrics record and persists it to Lockwood.
- **Context:** NEW route file `api/routes/metrics.py`. Persists via existing Lockwood SQLite bridge.
- **Constraints:** 202 Accepted on successful enqueue; never block the dispatch on telemetry failure (fail-open for observability writes).
- **Done-When:** `curl -X POST` with a valid record returns 202; a later `GET` lists it.

### Task 9.3: `lockwood-metrics.sh` writes route fields

- **Constraints:** MODIFY to add `bucket`, `builder`, `model`, `effort`, `route_file_path` columns to the emitted record.
- **Done-When:** `lockwood-metrics.sh` invocation produces a record with all 5 new fields populated.

### Task 9.4: Dispatch integration

- **Goal:** `_dispatch-core.sh` posts a metrics record after every completed dispatch.
- **Constraints:** Fire-and-forget background post (no dispatch latency impact). Log failures but do not retry inline.
- **Done-When:** Integration test: one dispatch → one metrics record in Lockwood within 2s.

### Task 9.5: Routing panel UI (active vanilla dashboard)

- **Goal:** Live table showing the last 50 dispatches with bucket/builder/effort/latency/done-when outcome.
- **Context:** NEW page in the ACTIVE dashboard at `~/.buildrunner/dashboard/public/routing-panel.html` + `routing-panel.mjs`. Matches existing vanilla-JS dashboard style (no React build step in that project). Dark theme via existing `dashboard.css`.
- **Constraints:** Polls `/api/metrics/dispatch?limit=50` every 5s via `fetch`. No framework dependencies beyond what the dashboard already has. Restrained aesthetic — matches existing panels.
- **Done-When:** Page renders the table with 50 rows when the endpoint has data; `node --test tests/dashboard/test_routing_panel.mjs` covers empty/populated/error states via jsdom.

### Task 9.6: Panel integration into dashboard nav

- **Constraints:** Add nav entry in `events.mjs` router so `/routing` serves the new page. Do not replace existing panels.
- **Done-When:** `curl http://localhost:<dashboard-port>/routing` returns 200 with the new HTML; Playwright spec in `~/.buildrunner/dashboard/tests/` confirms the nav link is clickable and renders rows.

**Phase Success Criteria:** Every dispatch persisted with bucket/builder/effort; live UI panel shows the stream.

**Rollback:** Delete new metrics schema + route + panel files; revert `lockwood-metrics.sh`.

---

### Phase 10: Rollout + Enforcement Flip (Irreversible)

**Goal:** Move from watch-only to enforcement after a 7-day watch period, ≤10% miss rate, and all Phase 5 tests green.
**Effort:** xHigh
**Files:**

- `~/.buildrunner/config/rollout-state.yaml` (NEW)
- `~/.buildrunner/scripts/flip-enforcement.sh` (NEW)
- `.buildrunner/decisions.log` (MODIFY — flip entry)
- `tests/rollout/test_flip_enforcement.bats` (NEW)

**Blocked by:** Phase 9

### Task 10.1: Rollout state file

- **Constraints:** YAML: `mode: watch-only | enforcing`, `started_at: <iso8601>`, `flipped_at: <iso8601 | null>`, `miss_rate_24h: <float>`, `authorized_by: <name>`.
- **Done-When:** File created in `watch-only` mode with `started_at` = now; schema validated.

### Task 10.2: Miss-rate calculator

- **Goal:** Compute 24h miss rate from Lockwood metrics (dispatches where `verdict: blocked` but user overrode).
- **Constraints:** Pure SQL + small Python shim. No network I/O.
- **Done-When:** Unit test feeds synthetic dispatch rows; calculator returns expected rate within 0.1%.

### Task 10.3: `flip-enforcement.sh` gate

- **Goal:** Script refuses to flip unless all three gates pass: miss_rate ≤10% AND Phase 5 tests green AND ≥7 days elapsed since `started_at`.
- **Context:** The 7-day watch period is the safety gate. An operator running `flip-enforcement.sh` on day 1 must be refused unless an explicit `--override-watch-period` flag is passed AND a decision-log entry is recorded with justification.
- **Constraints:** Compute elapsed = `now - started_at`. If `elapsed < 7d`, exit non-zero with `WATCH-PERIOD: <days-remaining> days remain; use --override-watch-period with written justification`. Override path requires `--justification "<text>"` and writes it to decisions.log.
- **Done-When:** Test cases: (a) day 1, no override → exit non-zero with `WATCH-PERIOD`, (b) day 8, miss rate 5%, tests green → flip succeeds, (c) day 8, miss rate 15% → exit non-zero with `MISS-RATE`, (d) day 1 with `--override-watch-period --justification "..."` → flip succeeds and decisions.log has the entry.

### Task 10.4: Flip writes `flipped_at` and updates mode

- **Constraints:** Atomic YAML write.
- **Done-When:** Post-flip file shows `mode: enforcing` and a fresh `flipped_at` timestamp.

### Task 10.5: Rollback path

- **Goal:** `flip-enforcement.sh --rollback` moves back to `watch-only` with a logged reason.
- **Constraints:** Requires `--reason "<text>"`. Writes decisions.log entry.
- **Done-When:** Rollback test returns state to `watch-only` and logs the reason.

### Task 10.6: bats tests

- **Done-When:** `bats tests/rollout/test_flip_enforcement.bats` — 8+ cases green covering all gate combinations.

**Phase Success Criteria:** Flip only succeeds when all three gates are green or an explicit logged override fires; rollback path verified.

**Rollback:** `flip-enforcement.sh --rollback --reason "<why>"`; route files still land, hooks still classify — the gate just stops blocking.

---

## Out of Scope (Future)

- Cross-session route learning (adapt bucket heuristics from confirmed outcomes).
- Multi-tenant route file isolation (assumes single-user workstation today).
- Automatic rollback on miss-rate regression post-flip.
- UI-driven matrix editing (YAML edit only for now).

---

## Parallelization Matrix

| Phase | Key Files                                        | Can Parallel  | Blocked By |
| ----- | ------------------------------------------------ | ------------- | ---------- |
| 1     | default-role-matrix.yaml, loader                 | No (gate)     | —          |
| 2     | classify-prompt.sh                               | With Phase 3  | 1          |
| 3     | inject-four-element.sh                           | With Phase 2  | 1          |
| 4     | user-prompt-submit-route.sh                      | No            | 2, 3       |
| 5     | pre-tool-use-gate.sh                             | No            | 4          |
| 6     | cross_model_review.py, arbiter.py                | With Phase 7  | 1          |
| 7     | spec.md, amend.md, spec-codex.md, amend-codex.md | With Phase 6  | 1          |
| 8     | cache_policy.py, context route                   | With Phase 9  | 3          |
| 9     | metrics_schema.py, RoutingPanel.tsx              | With Phase 8  | 6          |
| 10    | flip-enforcement.sh, rollout-state.yaml          | No (terminal) | 9          |

---

**Total Phases:** 10
**xHigh Phases:** 1, 5, 6, 10
**Max tasks per phase:** 6 (Codex one-loop sizing)
**Structural fixes applied:** removal of `_run_rebuttal` refactors `run_three_way_review` explicitly (no `NameError`); cache policy canonicalised at `core/runtime/cache_policy.py`; route files live under `$HOME/.buildrunner/routes/` (never `/tmp`); `os.path.expanduser` used anywhere `~` is resolved; 7-day watch-period gate enforced by elapsed-time check; Haiku fallback `max_tokens=120` with JSON-only system prompt and truncation fallback; arbiter always commits a verdict (Rule #1 compliant) with circuit breaker.
