# Project Spec: Claude 4.7 Optimization Sweep

**Purpose:** Align every CLAUDE.md, skill, and Claude-calling Python module in BR3 with Claude Opus 4.7 best practices and Part 11 of the research library.
**Target Users:** Byron (primary), any dev running BR3 skills or the Python Opus client.
**Tech Stack:** Claude Code skills (markdown), global + project CLAUDE.md, Python (anthropic SDK), bash hooks, Lockwood (persistent memory).

---

## Scope Context (from exploration)

- `core/opus_client.py` still targets `claude-opus-4-20250514` (Opus 4.0, retires June 2026). No deprecated 4.7 params in use today, but `max_tokens=4096` is too low for xhigh, no adaptive thinking set, no effort level, and 3 of 4 methods parse raw JSON instead of using structured outputs.
- `core/opus_handoff.py` has no Anthropic calls — it's a context-prep module. Light edit only.
- `~/.claude/CLAUDE.md` already has the 5 behavioral deltas + finding-vs-filtering. This spec is additive: effort tiers, adaptive-thinking cheatsheet, turn-1 rule, retrieval pins, /effort and /model levers.
- Target skill files live in `~/.claude/commands/*.md` and `~/.claude/skills/*/` (global user scope), not the BR3 repo.

---

### Phase 1: Modernize Python Anthropic client for 4.7

**Goal:** `core/opus_client.py` uses `claude-opus-4-7`, adaptive thinking, effort tiers, structured outputs via a supported SDK path, type-safe content accessors, and right-sized `max_tokens`. Zero deprecated 4.7 params. `core/opus_handoff.py` carries effort/model hints downstream.

**Files:**

- `requirements.txt` or `pyproject.toml` (MODIFY — SDK pin)
- `core/opus_client.py` (MODIFY)
- `core/opus_handoff.py` (MODIFY)
- `tests/test_opus_client_4_7.py` (NEW)

**Blocked by:** None

**Deliverables (addresses adversarial review blockers #1 and #2):**

- [ ] **SDK prerequisite.** Installed `anthropic` SDK v0.74.1 does not expose `output_config` on `messages.create()`. Either pin to a SDK version that does OR route the parameter via `extra_body={"output_config": {...}}` as the interim path. Document the chosen path at the top of `opus_client.py`.
- [ ] Replace `self.model = "claude-opus-4-20250514"` with env-override-capable default `claude-opus-4-7`, plus `opusplan` alias support.
- [ ] Apply `output_config={"effort": <tier>}` (or `extra_body` equivalent — see prerequisite) on all 4 `messages.create()` call sites.
- [ ] Set per-method effort tiers: `pre_fill_spec` → xhigh, `analyze_requirements` → high, `generate_design_tokens` → high, `validate_spec` → **medium** (classification/completeness check per effort guidance).
- [ ] Add `thinking={"type":"adaptive","display":"summarized"}` to all 4 call sites.
- [ ] **Type-safe content accessor.** Replace every `message.content[0].text` with `next((b.text for b in message.content if getattr(b, "type", None) == "text"), "")`. Adaptive thinking puts `ThinkingBlock` first in `content[]` — positional indexing will crash. Apply at all 4 call sites and any helper that parses message content.
- [ ] Right-size `max_tokens`: `pre_fill_spec` 16000 (typical spec is 2–8k output), `analyze_requirements` 4096, `generate_design_tokens` 4096, `validate_spec` 2048. Document rationale inline. Do not use 64000 — oversized ceilings add cost without quality gain under the 1.0–1.35× tokenizer inflation.
- [ ] Switch `analyze_requirements`, `generate_design_tokens`, `validate_spec` to structured outputs via the SDK path chosen in the prerequisite (Pydantic schemas); drop `json.loads`.
- [ ] Add `effort_tier` and `model_hint` fields to `HandoffPackage` in opus_handoff.py.
- [ ] Write `tests/test_opus_client_4_7.py` asserting: no `temperature`/`top_p`/`top_k`/`budget_tokens`/prefill keys; effort and thinking present; content accessor handles `ThinkingBlock`-first responses via a mock; model resolves to `claude-opus-4-7` by default; SDK version pin holds; smoke-run against staging key returns valid JSON shapes.

**Success Criteria:** Tests green. Smoke run produces valid `PROJECT_SPEC.md` and JSON payloads. No deprecated params. No `content[0].text` usage remains. SDK version pinned and asserted by tests.

**Can parallelize:** Yes, with Phases 2, 3, 4, 5, 8 — no overlapping files.

---

### Phase 2: Retrieval-heavy 4.6 pin

**Goal:** Retrieval-heavy commands stay on 4.6 to avoid 4.7's long-context regression (91.9 → 59.2%) and BrowseComp drop. `/switch` warns before flipping them.

**Files:**

- `~/.claude/commands/learn.md` (MODIFY)
- `~/.claude/commands/research.md` (MODIFY)
- `~/.claude/commands/cluster-research.md` (MODIFY)
- `~/.claude/commands/switch.md` (MODIFY)
- `~/.buildrunner/scripts/research-search.sh` (MODIFY — if it routes to Claude)
- `~/.claude/CLAUDE.md` (MODIFY — add retrieval-pinned section)

**Blocked by:** None

**Deliverables (addresses adversarial review note about `opus` alias):**

- [ ] Enumerate retrieval-heavy commands + their current frontmatter model value; confirm whether the `opus` alias in current frontmatter resolves to 4.7 or 4.6 on this account.
- [ ] **Change** (not add) frontmatter in `/learn` from the existing value (likely `model: opus`) to explicit `model: claude-opus-4-6`.
- [ ] Same verb for `/research`.
- [ ] Same verb for `/cluster-research`.
- [ ] Update `/switch` to read a pinned list and warn when a user tries to flip a pinned command to 4.7.
- [ ] Add "Retrieval-pinned commands" section to global CLAUDE.md with the regression rationale (91.9→59.2% long-context, 83.7→79.3% BrowseComp, fast mode 4.6-only).
- [ ] Audit `research-search.sh` and any Python retrieval helpers; ensure none call 4.7.

**Success Criteria:** `/learn`, `/research`, `/cluster-research` run on 4.6. `/switch` prints a warning on pinned flip. CLAUDE.md lists pinned commands.

**Can parallelize:** Yes, with Phases 1, 4, 8. Blocks Phase 3 (same CLAUDE.md file).

---

### Phase 3: Global CLAUDE.md 4.7 posture additions

**Goal:** Global CLAUDE.md carries explicit effort tiers, adaptive-thinking phrasing, turn-1 rule, response-length rule, positive-examples rule, and Claude Code native lever docs.

**Files:**

- `~/.claude/CLAUDE.md` (MODIFY)

**Blocked by:** Phase 2 (same file — sequential edit, not parallel)

**Deliverables:**

- [ ] Add "Effort Levels" block: xhigh default for agentic; medium for lint-grade; high for concurrent sessions; max only for genuinely hard problems
- [ ] Add adaptive-thinking phrase cheatsheet: "think carefully, harder than it looks" / "respond directly, prioritize speed"
- [ ] Add "Turn-1 Requirements" rule: intent + constraints + acceptance criteria + file paths must appear on first turn
- [ ] Add "Response Length Calibration" rule: if long output needed, state word/section counts explicitly
- [ ] Add "Positive Examples Over NEVER" rule with 1–2 examples of the rewrite
- [ ] Document `/effort xhigh` and `/model opusplan` levers (not the deep wiring — that's Phase 6)
- [ ] Cross-link to the Phase 2 retrieval-pinned list

**Success Criteria:** CLAUDE.md reads cleanly end-to-end. No section exceeds 12 lines. All new rules are stated as rules, not suggestions.

**Can parallelize:** With Phases 1, 4, 8 after Phase 2 completes.

---

### Phase 4: Finding-vs-filtering + anti-laziness sweep for audit/review skills

**Goal:** Every audit/review skill produces an unfiltered finding pass first, then applies severity/priority as a second explicit pass. Anti-laziness phrasing removed everywhere.

**Files:**

- `~/.claude/commands/review.md` (MODIFY)
- `~/.claude/commands/audit-site.md` (MODIFY)
- `~/.claude/commands/gaps.md` (MODIFY)
- `~/.claude/commands/dead.md` (MODIFY)
- `~/.claude/commands/fixplan.md` (MODIFY)
- (`research-audit.md` is owned by Phase 2; skip here)
- (`security-review` is a Claude-Code-provided plugin skill with no user-owned file at `~/.claude/commands/security-review.md`; we cannot edit it directly. Document the finding-vs-filtering pattern in `~/.claude/CLAUDE.md` under "Security review usage" so the plugin skill is invoked with explicit two-pass instruction from the user side.)

**Blocked by:** None

**Deliverables (addresses adversarial review notes about already-swept skills + plugin-scope security-review):**

- [ ] **Pre-edit audit.** Check each of the 5 target skill files for existing 4.7 frontmatter (e.g. `audit-site.md` already carries `model: claude-opus-4-7, effort: xhigh, thinking: {type: adaptive, display: summarized}, max_tokens: 64000`). Skip frontmatter edits on skills already compliant; apply the two-pass and anti-laziness edits only to skill body.
- [ ] Two-pass finding → filtering in `/review`.
- [ ] Same in `/audit-site`.
- [ ] Same in `/gaps`.
- [ ] Same in `/dead`.
- [ ] Same in `/fixplan`.
- [ ] Document the same two-pass pattern for `/security-review` (plugin skill, no user-owned file) in `~/.claude/CLAUDE.md` so invocations instruct it explicitly.
- [ ] Strip "CRITICAL: MUST" anti-laziness phrasing across these 5 files; replace with calm positive instruction.
- [ ] Reorder prompt structure: long docs at top of the skill body, query/output format at bottom, across these 5 files.

**Success Criteria:** Each of the 6 skills contains two explicitly labeled passes ("Pass 1: Findings" and "Pass 2: Filtering"). No `CRITICAL: MUST` strings remain in these files.

**Can parallelize:** Yes, with Phases 1, 2, 3, 5, 8.

---

### Phase 5: High-traffic skill 4.7 sweep (non-audit)

**Goal:** Execution/planning/debug skills declare effort tier, use positive examples, spell out subagent fan-out, and preserve roy-concise + security rules.

**Files:**

- `~/.claude/commands/begin.md` (MODIFY)
- `~/.claude/commands/autopilot.md` (MODIFY)
- `~/.claude/commands/spec.md` (MODIFY)
- `~/.claude/commands/brief.md` (MODIFY)
- `~/.claude/commands/root.md` (MODIFY)
- `~/.claude/commands/diag.md` (MODIFY)
- `~/.claude/skills/br3-frontend-design/SKILL.md` (MODIFY)
- `~/.claude/skills/br3-planning/SKILL.md` (MODIFY)

**Blocked by:** None

**Deliverables:**

- [ ] Add explicit effort tier header to each of the 8 skill files
- [ ] Convert NEVER/DON'T phrasing to positive examples across all 8
- [ ] Add explicit subagent fan-out statements where parallelism genuinely helps (`/root`, `/diag`, `/spec` exploration)
- [ ] Reorder prompt structure: long docs top, query/output bottom
- [ ] Strip `CRITICAL: MUST` anti-laziness phrasing
- [ ] Preserve roy-concise profile and security rules — run a diff review pass after edits
- [ ] Smoke-invoke each skill with a trivial input; confirm no regressions

**Success Criteria:** All 8 skills declare an effort tier in frontmatter or a "Posture" block. Smoke invocations behave as before. Security rules and roy-concise remain intact.

**Can parallelize:** Yes, with Phases 1, 2, 3, 4, 8. Blocks Phases 6, 7 (same skill files).

---

### Phase 6: Claude Code native levers + autopilot wiring

**Goal:** `/autopilot` planning phase uses `opusplan` alias. `/root` and `/diag` use `ultrathink —` on the single hardest step. CLAUDE.md documents the pattern.

**Files:**

- `~/.claude/commands/autopilot.md` (MODIFY)
- `~/.claude/commands/root.md` (MODIFY)
- `~/.claude/commands/diag.md` (MODIFY)
- `~/.claude/CLAUDE.md` (MODIFY)

**Blocked by:** Phase 3 (CLAUDE.md), Phase 5 (autopilot/root/diag skill files)

**Deliverables:**

- [ ] Wire autopilot planning phase to `/model opusplan` (Opus plans, Sonnet executes) with fallback if alias unavailable
- [ ] Add `ultrathink — ...` pattern for the single hardest reasoning step in `/root`
- [ ] Same in `/diag` (not every step — only the hardest)
- [ ] Document the `/effort` and `/model opusplan` usage patterns in CLAUDE.md with a concrete 2-line example
- [ ] Verify graceful fallback when `opusplan` alias is unavailable on the active account

**Success Criteria:** `/autopilot` planning completes via opusplan in a smoke run. `/root` and `/diag` invoke ultrathink on the designated step. CLAUDE.md example is runnable as written.

**Can parallelize:** With Phases 1, 4, 8 after Phases 3 and 5 complete.

---

### Phase 7: SessionStart posture banner + autopilot cost bounds

**Goal:** Every session opens with an effort/model/thinking banner. `/autopilot` runs cost-bounded via `task-budgets-2026-03-13` beta.

**Files:**

- `~/.buildrunner/scripts/developer-brief.sh` (MODIFY)
- `~/.claude/commands/begin.md` (MODIFY)
- `~/.claude/commands/autopilot.md` (MODIFY)

**Blocked by:** Phase 5 (begin.md, autopilot.md), Phase 6 (autopilot.md)

**Deliverables:**

- [ ] Extend SessionStart hook to detect task class (planning / execution / debug / audit) and declare effort tier
- [ ] Emit a one-line banner: `effort: <tier> · model: claude-opus-4-7 · thinking: adaptive` at session start
- [ ] Same banner at `/begin` start
- [ ] Same banner at `/autopilot` start
- [ ] Opt `/autopilot` into the `task-budgets-2026-03-13` beta header with a 20k-token floor for cost-bounded agentic loops
- [ ] Optional: task-completion sound notification (Stage 7 stretch item)

**Success Criteria:** Banner appears at next session start. `/autopilot` run shows the beta header in its first API call. Optional sound fires at end-of-task if enabled.

**Can parallelize:** With Phases 1, 4, 8 after Phases 5 and 6 complete.

---

### Phase 8: Lockwood measurement loop

**Goal:** Every skill run logs effort tier + outcome quality + token count to Lockwood. A 2-week review surfaces over- and under-spends.

**Files:**

- `~/.buildrunner/scripts/log-skill-run.sh` (NEW)
- `~/.buildrunner/scripts/effort-review-report.sh` (NEW)
- `~/.buildrunner/hooks/skill-end.sh` (NEW)
- Lockwood schema migration for new fields (NEW)

**Blocked by:** None (data-capture only; doesn't edit skill bodies)

**Deliverables:**

- [ ] Define Lockwood schema fields: `skill_name`, `effort_tier`, `outcome_quality`, `token_count`, `duration_ms`, `timestamp`
- [ ] Build `log-skill-run.sh` that POSTs one row per skill run to Lockwood
- [ ] Wire `skill-end.sh` hook to call `log-skill-run.sh`
- [ ] Build `effort-review-report.sh` with three queries: over-spend on max, under-spend on medium, where xhigh earned its keep
- [ ] Schedule a 2-week recurring review via `/schedule` or cron
- [ ] Write a short manual review runbook (what to look at, when to retune tiers)

**Success Criteria:** One Lockwood row per skill invocation. Report script outputs three ranked lists. Schedule is active.

**Can parallelize:** Yes, with every other phase — no file overlap.

---

## Out of Scope (Future)

- Rewriting the full `/opus` skill to pull effort levels from a shared config file (current skill already synthesizes research well enough).
- Migrating the BR3 frontend to Claude Agent SDK.
- Extending effort logging to non-skill Claude calls (e.g. raw API scripts outside `/skills`).
- Auto-retune of effort tiers from Lockwood data (first pass is manual review).
- Project-level CLAUDE.md edits beyond roy-concise preservation (profile handles that scope).

---

## Parallelization Matrix

| Phase | Key Files                                                                                                      | Can Parallel With   | Blocked By                     |
| ----- | -------------------------------------------------------------------------------------------------------------- | ------------------- | ------------------------------ |
| 1     | `core/opus_client.py`, `core/opus_handoff.py`, new tests                                                       | 2, 4, 5, 8          | —                              |
| 2     | `learn.md`, `research.md`, `cluster-research.md`, `switch.md`, `research-search.sh`, `CLAUDE.md`               | 1, 4, 5, 8          | —                              |
| 3     | `~/.claude/CLAUDE.md`                                                                                          | 1, 4, 5, 8          | 2 (same CLAUDE.md)             |
| 4     | `review.md`, `security-review.md`, `audit-site.md`, `gaps.md`, `dead.md`, `fixplan.md`                         | 1, 2, 3, 5, 8       | —                              |
| 5     | `begin.md`, `autopilot.md`, `spec.md`, `brief.md`, `root.md`, `diag.md`, `br3-frontend-design`, `br3-planning` | 1, 2, 3, 4, 8       | —                              |
| 6     | `autopilot.md`, `root.md`, `diag.md`, `CLAUDE.md`                                                              | 1, 4, 8             | 3 (CLAUDE.md), 5 (skill files) |
| 7     | `session-start.sh`, `begin.md`, `autopilot.md`                                                                 | 1, 4, 8             | 5, 6                           |
| 8     | new scripts + Lockwood schema                                                                                  | 1, 2, 3, 4, 5, 6, 7 | —                              |

**Execution order (reconciled with parallelization matrix — addresses adversarial review note about sequencing):**

- Wave A (run simultaneously): Phases **1, 2, 4, 8**. No file overlap between them.
- Wave B: Phase **3** after Phase 2 releases CLAUDE.md.
- Wave C: Phase **5** after Wave B (nominal sequencing for session posture, not file-blocked — can overlap Wave B if skill files don't touch CLAUDE.md).
- Wave D: Phase **6** after Phases 3 and 5 complete (overlapping files).
- Wave E: Phase **7** after Phases 5 and 6 complete (overlapping files).
- Phase 8 continues as an ongoing measurement loop throughout and after.

User's stated priority (Stage 3 first, then 4, then 1, then 6) is honored inside Wave A — the actual build order there can be 1 → 2 → 4 in sequence if a single operator is running the sweep, but nothing prevents parallel execution by multiple operators or worktrees.

---

**Total Phases:** 8
**Parallelizable today:** Phases 1, 2, 4, 8 simultaneously. After 2: Phase 3. After 2 and skill-file freezes: Phase 5. After 3+5: Phase 6. After 5+6: Phase 7.
