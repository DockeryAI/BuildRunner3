# Build: Claude 4.7 Optimization Sweep

**Created:** 2026-04-21
**Status:** Phase 1 Not Started
**Deploy:** python-local — `pytest tests/test_opus_client_4_7.py`
**Source Plan File:** .buildrunner/plans/spec-draft-4-7-optimization.md
**Source Plan SHA:** e677fd7a8f6fd9f864e4bc0a8f4c278b2b1b7524e4b07f89ec1ce2401d621fd5
**Adversarial Review Verdict:** BYPASSED:.buildrunner/bypass-justification.md
**Adversarial Review Timestamp:** 2026-04-21T22:59:13Z

## Overview

Align every CLAUDE.md, skill, and Claude-calling Python module in BR3 with Claude Opus 4.7 best practices and Part 11 of the research library. Covers: Python Anthropic client modernization (adaptive thinking, effort tiers, structured outputs, type-safe content accessors), retrieval-heavy 4.6 pins, global CLAUDE.md posture additions, finding-vs-filtering sweep of audit skills, Claude Code native levers (/effort, /model opusplan), SessionStart banner, and Lockwood measurement loop.

## Parallelization Matrix

| Phase | Key Files                                                                                                                                        | Can Parallel With | Blocked By         |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------- | ------------------ |
| 1     | core/opus_client.py, core/opus_handoff.py, tests/test_opus_client_4_7.py (NEW)                                                                   | 2, 4, 8           | -                  |
| 2     | ~/.claude/commands/learn.md, ~/.claude/commands/research.md, ~/.claude/commands/cluster-research.md                                              | 1, 4, 8           | -                  |
| 3     | ~/.claude/CLAUDE.md                                                                                                                              | -                 | 1, 2 (avoid churn) |
| 4     | ~/.claude/commands/audit*.md, ~/.claude/commands/review.md, ~/.claude/skills/*/SKILL.md (audit)                                                  | 1, 2, 8           | -                  |
| 5     | ~/.claude/commands/spec.md, ~/.claude/commands/begin.md, ~/.claude/commands/autopilot.md, ~/.claude/commands/save.md, ~/.claude/commands/root.md | -                 | 3                  |
| 6     | ~/.buildrunner/scripts/autopilot\*.sh, CLAUDE.md (project)                                                                                       | -                 | 5                  |
| 7     | ~/.buildrunner/scripts/developer-brief.sh                                                                                                        | -                 | 6                  |
| 8     | ~/.buildrunner/scripts/lockwood-metrics.sh (NEW), tests/test_opus_client_4_7.py                                                                  | 1, 2, 4           | -                  |

**Execution waves:** A={1,2,4,8} → B=3 → C=5 → D=6 → E=7. Phase 8 measurement loop runs ongoing.

## Phases

### Phase 1: Modernize Python Anthropic client for 4.7

**Status:** 🚧 in_progress
**Files:**

- core/opus_client.py (MODIFY)
- core/opus_handoff.py (MODIFY)
- tests/test_opus_client_4_7.py (NEW)
- requirements.txt (MODIFY) — pin anthropic SDK version
  **Blocked by:** None
  **Deliverables:**
- [ ] SDK prerequisite: pin anthropic SDK to a version exposing `output_config` (or route via `extra_body={"output_config": {...}}` as interim). Test asserts the pinned version.
- [ ] Update `self.model` from `claude-opus-4-20250514` to `claude-opus-4-7`.
- [ ] Add effort tier config: xhigh default, medium for `validate_spec`, high elsewhere.
- [ ] Replace every `message.content[0].text` with `next((b.text for b in message.content if getattr(b, "type", None) == "text"), "")` at all 4 call sites + any content-parsing helper.
- [ ] Right-size `max_tokens` per method: `pre_fill_spec=16000`, `analyze_requirements=4000`, `generate_design_tokens=4000`, `validate_spec=2000`.
- [ ] Add adaptive thinking config with `display: "summarized"` (not deprecated `thinking: {type: "enabled", budget_tokens: N}`).
- [ ] Switch raw-JSON methods to structured outputs via `output_config` (or `extra_body` interim).
- [ ] Remove any deprecated 4.7 params: `temperature`, `top_p`, `top_k`, `budget_tokens`, assistant prefills.
- [ ] `core/opus_handoff.py`: include `effort` and `model` hints in HandoffPackage so downstream calls inherit posture.
- [ ] Unit test covers: SDK version pin, `ThinkingBlock`-first mock, structured output shape, per-method `max_tokens`.

**Success Criteria:** `pytest tests/test_opus_client_4_7.py` passes. No deprecated params in any `messages.create()` call. Mock with `ThinkingBlock` first in `content[]` returns the text block cleanly.

### Phase 2: Retrieval-heavy 4.6 pin

**Status:** 🚧 in_progress
**Files:**

- ~/.claude/commands/learn.md (MODIFY)
- ~/.claude/commands/research.md (MODIFY)
- ~/.claude/commands/cluster-research.md (MODIFY)
  **Blocked by:** None
  **Deliverables:**
- [ ] Change (not add — these already carry `model: opus` alias) frontmatter to explicit `model: claude-sonnet-4-6` or `claude-opus-4-6` for retrieval-heavy skills, citing long-context regression (91.9→59.2%) and BrowseComp regression (83.7→79.3%).
- [ ] Alias-resolution check: verify `model: opus` resolves to 4.7 in current runtime; document.
- [ ] Add rationale comment in each file pointing to research library Part 11.
- [ ] `/learn` — pin to 4.6 (heavy retrieval from Lockwood).
- [ ] `/research` — pin to 4.6 (web fetch + long-context synthesis).
- [ ] `/cluster-research` — pin to 4.6 (cluster-wide retrieval).
- [ ] Document exception rule in global CLAUDE.md: "retrieval-heavy skills pin 4.6".

**Success Criteria:** Each skill's frontmatter resolves to the 4.6 family. Manual run of `/learn` shows model in response metadata. No skill silently inherits 4.7 for long-context work.

### Phase 3: Global CLAUDE.md 4.7 posture additions

**Status:** not_started
**Files:**

- ~/.claude/CLAUDE.md (MODIFY)
  **Blocked by:** Phase 1, Phase 2 (avoids churn on concurrent rule updates)
  **Deliverables:**
- [ ] Add explicit effort-level block: xhigh default, medium for lint/classification, high for concurrent, max sparingly.
- [ ] Add adaptive-thinking cheatsheet: use `display: "summarized"`, never `budget_tokens` or `thinking: {type: "enabled"}`.
- [ ] Add turn-1 rule: state the work sentence before the first tool call.
- [ ] Add response-length calibration: short questions → direct answer; multi-step work → updates per major change; end-of-turn → 1–2 sentence summary.
- [ ] Add positive-examples rule: show desired form, not forbidden form.
- [ ] Add retrieval pin exception: `/learn`, `/research`, `/cluster-research` use 4.6.
- [ ] Add `task-budgets-2026-03-13` beta header note with 20k-token floor guidance.

**Success Criteria:** Global CLAUDE.md contains all 7 additions as distinct sections. New sessions read them via SessionStart. Spot-check: ask a retrieval question, model selection follows the pin.

### Phase 4: Finding-vs-filtering + anti-laziness sweep for audit/review skills

**Status:** 🚧 in_progress
**Files:**

- ~/.claude/commands/audit.md (MODIFY if exists)
- ~/.claude/commands/review.md (MODIFY if exists)
- ~/.claude/skills/\*/SKILL.md (MODIFY — audit/review ones)
- audit-site.md (SKIP — already carries 4.7 frontmatter)
  **Blocked by:** None
  **Deliverables:**
- [ ] Pre-edit audit: glob for audit/review skill files, skip any already carrying `model: claude-opus-4-7` frontmatter.
- [ ] For each remaining file: add explicit two-pass instruction — "Pass 1: produce complete unfiltered finding list. Pass 2: apply severity/priority filter as a distinct step."
- [ ] Add anti-laziness clause: "do not stop early on first matching finding; exhaust the scoped surface before filtering".
- [ ] Add finding-template block: `{id, severity, category, file:line, evidence, fix}`.
- [ ] Add scope-enumeration step before any findings: list every file/surface the audit will cover.
- [ ] Add fail-closed rule: if a finding cannot be categorized, emit it as `severity: unknown` rather than drop it.
- [ ] Add parallel-subagent directive for cross-file audits: "dispatch N parallel subagents for X, Y, Z".
- [ ] Explicit effort: xhigh for findings-pass, medium for filtering-pass.
- [ ] Verify: run any one audit skill end-to-end and confirm Pass 1 and Pass 2 appear as distinct outputs.

**Success Criteria:** Every audit/review skill has two-pass instruction. No skill merges finding + filtering in one breath. Test run of one audit produces unfiltered list first, filtered list second.

### Phase 5: High-traffic skill 4.7 sweep (non-audit)

**Status:** not_started
**Files:**

- ~/.claude/commands/spec.md (MODIFY)
- ~/.claude/commands/begin.md (MODIFY)
- ~/.claude/commands/autopilot.md (MODIFY)
- ~/.claude/commands/save.md (MODIFY)
- ~/.claude/commands/root.md (MODIFY)
  **Blocked by:** Phase 3 (skills reference CLAUDE.md rules)
  **Deliverables:**
- [ ] Each skill: explicit effort tier in frontmatter or prose preamble.
- [ ] Each skill: explicit parallelism directive where parallel work exists ("run these N reads/writes in parallel").
- [ ] Remove any redundant "double-check your work" phrasing — 4.7 self-verifies; redundant verification causes over-revision.
- [ ] Each skill with a tone component: explicit `<tone>` block (not tone-by-example).
- [ ] Each skill: convert any implicit "use judgment" heuristic into literal rules with stated exceptions.
- [ ] Each skill: state stop-condition explicitly (what "done" means for the skill).
- [ ] Verify: open each skill in a fresh session and confirm the posture reads correctly.

**Success Criteria:** All 5 high-traffic skills pass the 4.7 literal-reading test. No implicit heuristics remain. Manual spot-check of each skill's first run matches expected behavior.

### Phase 6: Claude Code native levers + autopilot wiring

**Status:** not_started
**Files:**

- ~/.buildrunner/scripts/autopilot\*.sh (MODIFY)
- CLAUDE.md (project root) (MODIFY)
  **Blocked by:** Phase 5
  **Deliverables:**
- [ ] Wire `/effort xhigh` default into autopilot dispatch scripts.
- [ ] Wire `/model opusplan` (Opus plans, Sonnet executes) for planning-heavy phases.
- [ ] Add `ultrathink — ...` prefix for hardest steps (explicitly documented trigger phrases).
- [ ] Project CLAUDE.md: add operator-level note documenting the native levers.
- [ ] Verify: run autopilot on a throwaway phase, confirm effort and model selection propagate.

**Success Criteria:** Autopilot dispatches with explicit effort+model params. Project CLAUDE.md documents the levers. Lockwood records model/effort metadata per phase.

### Phase 7: SessionStart posture banner + autopilot cost bounds

**Status:** not_started
**Files:**

- ~/.buildrunner/scripts/developer-brief.sh (MODIFY)
  **Blocked by:** Phase 6
  **Deliverables:**
- [ ] Add posture banner to developer brief: model (4.7 default, 4.6 retrieval pin), effort (xhigh default), adaptive thinking (summarized), retrieval pins list.
- [ ] Add token-inflation note: 1.0–1.35× on new tokenizer, right-size estimates.
- [ ] Add cost-bounds note for autopilot: per-phase token ceiling and warn threshold.
- [ ] Add deprecated-params reminder: temperature/top_p/top_k/budget_tokens/prefills forbidden.
- [ ] Add retrieval-regression reminder: long-context 91.9→59.2%, BrowseComp 83.7→79.3%, fast mode 4.6-only.
- [ ] Verify: next `/save` shows the banner. Confirm no regression in existing brief fields.

**Success Criteria:** SessionStart hook emits the posture banner. Autopilot dispatches respect cost bounds. Developer-brief smoke test passes.

### Phase 8: Lockwood measurement loop

**Status:** not_started
**Files:**

- ~/.buildrunner/scripts/lockwood-metrics.sh (NEW)
- tests/test_opus_client_4_7.py (MODIFY — reference metrics)
  **Blocked by:** None
  **Deliverables:**
- [ ] Script records per-call: model, effort, method, input tokens, output tokens, thinking tokens, latency, success/fail.
- [ ] POST to Lockwood `/api/metrics/opus` (create endpoint if missing).
- [ ] Wire `core/opus_client.py` to emit metrics after each call.
- [ ] Daily rollup query: avg latency by (model, effort, method); p95.
- [ ] Drift detection: if latency or token count drifts >20% over 7-day rolling window, flag.
- [ ] Document query commands in script header.

**Success Criteria:** 7 days after deploy, `br metrics opus` prints model/effort/method breakdown. Drift flags surface in SessionStart when tripped.

## Session Log

[Will be updated by /begin]
