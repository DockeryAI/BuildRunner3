# Build: Setlist — Evidence-Based Planning for BR3

**Created:** 2026-04-06
**Status:** Phases 1,2,3,5 Complete — Phase 4 In Progress
**Deploy:** local — skill files + cluster node updates (deploy nodes via SSH after each phase)

## Overview

Planning system that prevents defects before code is written. Uses The Band for parallel exploration, adversarial review, and test pre-validation. Every technique is backed by measured evidence — no theoretical additions.

**Key research findings driving the design:**

- Lusser's Law: 85% per-step accuracy = 20% success on 10 steps → per-task verification mandatory
- TDAD: context (WHICH tests) > procedure (HOW to test) → 70% regression reduction
- Self-Refine: one pass only, regression at pass 3
- Context rot: degrades at 2,500 words → curated <500 token context, not dumps
- Plan granularity: single-function tasks 87% vs multi-file 19% → decompose everything
- Separate producer/verifier: 87.8% vs 47% test accuracy → adversarial review on different machine

**Research:** `~/Projects/research-library/docs/techniques/ultraplan-cloud-planning.md` (2 sessions, 63 sources)

**READ FIRST:**

1. `~/.buildrunner/scripts/cluster-check.sh` — node discovery
2. `core/cluster/memory_store.py` — Lockwood memory tables
3. `core/cluster/node_semantic.py` — Lockwood semantic search API
4. `core/cluster/node_tests.py` — Walter test runner API
5. `~/.claude/commands/begin.md` — current /begin workflow (9 steps)

**DO NOT:**

- Break existing `/begin` workflow — gates are additive, not replacement
- Require The Band to be online — graceful fallback to local-only everywhere
- Hard-code node IPs — all reads from cluster.json via cluster-check.sh
- Add verbose procedural instructions to the skill — TDAD proved this INCREASES errors
- Use multi-agent synthesis — research shows single-agent synthesis is superior
- Add more than one Self-Refine pass — regression measured at iteration 3

---

## Parallelization Matrix

| Phase | Key Files                                                                | Can Parallel With | Blocked By                  |
| ----- | ------------------------------------------------------------------------ | ----------------- | --------------------------- |
| 1     | `~/.claude/commands/setlist.md`, `~/.claude/docs/setlist-*.md`           | 2, 3, 5           | -                           |
| 2     | `core/cluster/memory_store.py`, `core/cluster/node_semantic.py`          | 1, 3, 5           | -                           |
| 3     | `core/cluster/node_tests.py`                                             | 1, 2, 5           | -                           |
| 4     | `~/.claude/commands/begin.md`, `~/.claude/docs/begin-execution-gates.md` | 2, 3, 5, 6        | - (after 1 logically)       |
| 5     | `~/.buildrunner/scripts/adversarial-review.sh`                           | 1, 2, 3, 4        | -                           |
| 6     | `core/dashboard_views.py`, `cli/dashboard.py`                            | 1, 2, 3, 4, 5     | - (after 1,2,3,5 logically) |

**Optimal execution:** Wave 1 (Phases 1+2+3+5 parallel) → Wave 2 (Phases 4+6 parallel)

---

## Phases

### Phase 1: The Setlist Skill

**Status:** ✅ COMPLETE
**Files:**

- `~/.claude/commands/setlist.md` (NEW)
- `~/.claude/docs/setlist-plan-format.md` (NEW)
- `~/.claude/docs/setlist-explore-lenses.md` (NEW)

**Blocked by:** None

**Deliverables:**

- [x] Skill file implementing the 6-phase Setlist pipeline as Claude orchestration instructions
- [x] Phase 0 (TUNE UP): Query Lockwood `/api/plans/similar` for 2-3 relevant past plan outcomes; read BUILD spec for current phase context; run code health pre-check on target files; curate all context to <500 tokens
- [x] Phase 1 (SOUNDCHECK): Dispatch 1-3 Explore subagents using the defined lenses, scaled by complexity (bug=1, feature=2, refactor=3). Each lens has a specific output template in the lenses doc
- [x] Phase 2 (REHEARSAL): Single-agent synthesis consuming explore results + Lockwood lessons. One Self-Refine pass (generate → critique → revise). Output in plan format doc structure
- [x] Phase 3 (JAM SESSION): Run `adversarial-review.sh` targeting Otis (or local subagent fallback). Query Walter `/api/testmap/baseline` for test map + current pass/fail state. Both parallel
- [x] Phase 4 (SHOWTIME): Present plan + adversarial findings + test baseline. Approve → hand to `/begin`. Revise → targeted re-synthesis. Reject → archive to Lockwood with reason
- [x] Plan format doc defining: WHAT (file + function-level intent) + WHY (requirement satisfied) + VERIFY (specific test from test map) per task. 40-line hard max. Single-function decomposition mandatory
- [x] Explore lenses doc defining three lenses: Feature Trace (data flow), Impact Analysis (callers + dependents + test map), Semantic Similarity (reuse candidates + clone risks). Each with output template
- [x] Complexity classifier: count files in BUILD spec phase → 1-3 files = simple (1 agent), 4-8 = medium (2 agents), 9+ = complex (3 agents)
- [x] Graceful fallback: if Lockwood offline → skip Phase 0 memory query. If Walter offline → skip test map. If Otis offline → run adversarial as local subagent. Skill always works

**Success Criteria:** `/setlist add JWT auth to the payments service` produces a structured plan with decomposed single-function tasks, each with a verify criterion, in under 15 minutes

---

### Phase 2: Plan Memory (Lockwood)

**Status:** ✅ COMPLETE
**Files:**

- `core/cluster/memory_store.py` (MODIFY)
- `core/cluster/node_semantic.py` (MODIFY)

**Blocked by:** None

**Deliverables:**

- [x] New `plan_outcomes` table in memory_store.py:
  ```
  plan_id INTEGER PRIMARY KEY AUTOINCREMENT
  project TEXT NOT NULL
  build_name TEXT NOT NULL
  phase TEXT NOT NULL
  plan_text TEXT NOT NULL
  outcome TEXT NOT NULL (pass/fail/partial)
  accuracy_pct REAL (planned files vs actual files touched)
  drift_notes TEXT
  files_planned TEXT (JSON array)
  files_actual TEXT (JSON array)
  duration_seconds REAL
  timestamp TEXT DEFAULT datetime('now')
  ```
- [x] `record_plan_outcome()` in memory_store.py — stores plan + execution outcome
- [x] `get_recent_plan_outcomes()` in memory_store.py — retrieves recent plans for a project
- [x] Embed plan text into LanceDB via existing CodeRankEmbed model for semantic retrieval
- [x] `search_similar_plans()` in node_semantic.py — vector search for semantically similar past plans, returns top 3 with outcome + accuracy + drift_notes
- [x] API endpoint `POST /api/plans/record` — accepts plan_text, outcome, accuracy, files arrays
- [x] API endpoint `GET /api/plans/similar?query=<text>&project=<name>&limit=3` — returns similar plans with outcomes
- [x] Index: `idx_plans_project` on project column

**Success Criteria:** After recording 3+ plan outcomes, `GET /api/plans/similar?query=auth migration&project=synapse&limit=3` returns relevant past plans ranked by semantic similarity with pass/fail outcomes and accuracy percentages

---

### Phase 3: Test Map (Walter)

**Status:** ✅ COMPLETE
**Files:**

- `core/cluster/node_tests.py` (MODIFY)

**Blocked by:** None

**Deliverables:**

- [x] New `test_file_map` table:
  ```
  id INTEGER PRIMARY KEY AUTOINCREMENT
  project TEXT NOT NULL
  test_file TEXT NOT NULL
  source_file TEXT NOT NULL
  confidence TEXT DEFAULT 'import' (import/convention/manual)
  last_verified TEXT DEFAULT datetime('now')
  ```
- [x] `build_test_map(project)` function — scans test files for: import statements referencing source files, naming conventions (foo.test.ts → foo.ts), and explicit file references. Builds source→test mapping
- [x] `get_test_map(files, project)` — given a list of source files, returns which test files cover them with confidence level
- [x] API endpoint `GET /api/testmap?files=<comma-separated>&project=<name>` — returns `{file: [test_files]}` mapping
- [x] API endpoint `POST /api/testmap/baseline?project=<name>&files=<comma-separated>` — runs the mapped tests, returns `{test_file: "pass"|"fail"|"skip", duration_ms: N}` baseline
- [x] Auto-rebuild: when file hashes change during existing poll cycle, invalidate and rebuild affected map entries
- [x] Index: `idx_testmap_project_source` on (project, source_file)

**Success Criteria:** `GET /api/testmap?files=src/auth/middleware.ts&project=synapse` returns test files that import or reference that source file, with `POST /api/testmap/baseline` confirming their current pass/fail state

---

### Phase 4: Execution Gates in /begin

**Status:** ✅ COMPLETE
**Files:**

- `~/.claude/commands/begin.md` (MODIFY)
- `~/.claude/docs/begin-execution-gates.md` (NEW)

**Blocked by:** None
**After:** Phase 1 (logically — gates reference setlist plan format)

**Deliverables:**

- [x] Detect setlist plan: if `.buildrunner/plans/phase-*-plan.md` contains setlist format (tasks with VERIFY criteria), activate execution gates
- [x] Per-task verification loop: after implementing each task, run its VERIFY criterion. Pass → proceed to next task. Fail → present three options: (1) fix the issue and re-verify, (2) checkpoint and replan from this task, (3) skip this task with a note
- [x] Two-consecutive-failure circuit breaker: if two tasks fail verification in a row, automatically checkpoint — save completed tasks + remaining plan to Lockwood, present fresh-context replan option
- [x] Session boundary tracking: count tool-use interactions since `/begin` started. At 70 interactions, present status check — show completed/remaining tasks, offer to continue or checkpoint
- [x] Time tracking: record start time. At 35 minutes, present the same status check
- [x] Context capacity advisory: if context compaction has occurred, note it and recommend checkpointing for remaining complex tasks
- [x] Post-execution recording: after all tasks complete (or on checkpoint), call Lockwood `POST /api/plans/record` with plan text, outcome, accuracy (files planned vs files actually changed), and any drift notes
- [x] Execution gates doc: the rules, triggers, and rationale (Lusser's Law reference, TDAD reference). Keep under 40 lines — it's a reference doc, not a novel

**Success Criteria:** During a 6-task plan, a failing VERIFY on task 3 stops execution and presents fix/replan/skip. Two consecutive failures trigger automatic checkpoint with fresh-context replan option. Plan outcome recorded to Lockwood on completion

---

### Phase 5: Adversarial Review Dispatch

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/scripts/adversarial-review.sh` (NEW)

**Blocked by:** None

**Deliverables:**

- [x] Shell script accepting: plan file path, project root path, optional target node (default: Otis)
- [x] If Otis online: SSH to Otis, sync relevant source files via rsync, launch `claude --print` with adversarial prompt + plan text, capture output, return to caller
- [x] If Otis offline: output a local adversarial prompt that the setlist skill runs as a subagent
- [x] Adversarial prompt targets the measured failure modes: requirement conflicts (43.53% of hallucinations), fabricated APIs (20.41%), broken execution order, missing edge cases, files that don't exist
- [x] Hard 3-minute timeout (`timeout 180` on SSH command). Adversarial loops have diminishing returns — survivability over completeness
- [x] Output format: JSON array of `{finding: "text", severity: "blocker|warning|note"}`. Blockers must be addressed before approval. Warnings are advisory. Notes are informational
- [x] Exit codes: 0 = review complete (findings in stdout), 1 = timeout/error (fallback message in stderr)

**Success Criteria:** `./adversarial-review.sh plan.md /path/to/project` returns findings within 3 minutes. Correctly identifies a deliberately planted fabricated API reference in a test plan

---

### Phase 6: Dashboard — Plan Review

**Status:** ✅ COMPLETE
**Files:**

- `core/dashboard_views.py` (MODIFY)
- `cli/dashboard.py` (MODIFY)

**Blocked by:** None
**After:** Phases 1, 2, 3, 5 (renders their outputs)

**Design principle:** The dashboard is the human verification gate. 50% of test-passing AI code would be rejected by maintainers (METR). The dashboard arms the reviewer with exactly what they need for a fast, informed approve/reject decision. Nothing more.

**Deliverables:**

- [x] New `PlanReviewView` class in dashboard_views.py — reads latest plan from `.buildrunner/plans/`, adversarial findings from `.buildrunner/plans/adversarial-*.json`, queries Walter and Lockwood APIs
- [x] **Task table:** Rich table — columns: #, WHAT (file + function intent), WHY (requirement), VERIFY (test name + current green/red status). Every row is a single-function task
- [x] **Adversarial findings panel:** Color-coded below task table. Red = blocker (sort to top, must address). Yellow = warning. Dim = note
- [x] **Test baseline panel:** Files → tests mapping with green/red pass/fail state. If a test is already failing pre-implementation, flag it prominently
- [x] **Historical outcomes panel:** Max 3 similar past plans from Lockwood. One line each: summary, outcome, accuracy %, one-line lesson. No full plan text
- [x] **Code health flags:** Warning bar at top if any planned file has health < 9.5/10
- [x] **Actions:** Approve (→ `/begin`), Revise (→ per-task comment prompts, one re-synthesis), Reject (→ reason prompt, archive to Lockwood)
- [x] **Per-task comments on Revise:** Each task row gets optional comment input. Comments become targeted revision instructions. One comment per task, not arbitrary inline positions
- [x] CLI: `br dashboard show --view plan` for full review, `--view plan --history` for past plans table
- [x] Graceful degradation: Walter offline → skip test panel. Lockwood offline → skip history. Plan + adversarial always shown

**Success Criteria:** `br dashboard show --view plan` displays plan with task table, adversarial findings (color-coded), test baseline (green/red), historical outcomes, and code health flags. Revise action collects per-task comments

---

### Phase 7: Dashboard — Execution Monitor

**Status:** ✅ COMPLETE
**Files:**

- `core/dashboard_views.py` (MODIFY)
- `cli/dashboard.py` (MODIFY)

**Blocked by:** Phase 6 (same files — extends PlanReviewView)
**After:** Phase 4 (renders execution gate data)

**Deliverables:**

- [x] **Execution progress view:** Task N of M progress bar. Each completed task shows verify result (green check / red X). Consecutive failure count displayed prominently. This is the Lusser's Law dashboard — every unverified step compounds
- [x] **Session metrics bar:** Interaction count (of 70 limit), elapsed time (of 35 min limit), compaction count. Yellow at 80%, red at 100%. Human sees when to checkpoint before context poisons
- [x] **Drift indicator:** If files touched during execution diverge from planned files, show drift percentage in real-time
- [x] **Affected files preview:** For each file in the plan, show: exists (yes/no), last modified date, line count. Spots stale assumptions ("plan targets auth.ts but that file was deleted")
- [x] CLI: `br dashboard show --view exec` for live execution progress

**Success Criteria:** `br dashboard show --view exec` shows task completion progress with verify results, session metrics with color-coded limits, and drift percentage during `/begin` execution

---

### Phase 8: Dashboard — Enhancements

**Status:** ✅ COMPLETE
**Files:**

- `core/dashboard_views.py` (MODIFY)
- `cli/dashboard.py` (MODIFY)

**Blocked by:** Phase 7 (same files)
**After:** Phases 6, 7

**Deliverables:**

- [x] **BUILD spec context panel:** Toggle with `--context` flag. Shows current BUILD spec phase (goal, deliverables, success criteria) alongside the plan. Hidden by default to reduce visual density
- [x] **Dependency diagram render:** If plan includes a dependency section, render as Rich tree or flow diagram. Don't require — render if present, skip if absent
- [x] **Plan comparison diff:** When current plan is a revision (after reject/replan), show what changed vs previous version. Green = added tasks, red = removed, yellow = modified. Only shown when previous plan exists for same phase
- [x] CLI: `br dashboard show --view plan --context` for BUILD spec side-by-side, `--view plan --diff` for plan comparison

**Success Criteria:** `--context` shows BUILD spec phase alongside plan. `--diff` shows colored diff between current and previous plan version when a previous exists

---

## Parallelization Matrix

| Phase | Key Files                                                                | Can Parallel With | Blocked By                  |
| ----- | ------------------------------------------------------------------------ | ----------------- | --------------------------- |
| 1     | `~/.claude/commands/setlist.md`, `~/.claude/docs/setlist-*.md`           | 2, 3, 5           | -                           |
| 2     | `core/cluster/memory_store.py`, `core/cluster/node_semantic.py`          | 1, 3, 5           | -                           |
| 3     | `core/cluster/node_tests.py`                                             | 1, 2, 5           | -                           |
| 4     | `~/.claude/commands/begin.md`, `~/.claude/docs/begin-execution-gates.md` | 2, 3, 5           | - (after 1 logically)       |
| 5     | `~/.buildrunner/scripts/adversarial-review.sh`                           | 1, 2, 3, 4        | -                           |
| 6     | `core/dashboard_views.py`, `cli/dashboard.py`                            | -                 | - (after 1,2,3,5 logically) |
| 7     | `core/dashboard_views.py`, `cli/dashboard.py`                            | -                 | 6 (same files)              |
| 8     | `core/dashboard_views.py`, `cli/dashboard.py`                            | -                 | 7 (same files)              |

**Optimal execution:**

- **Wave 1:** Phases 1, 2, 3, 5 (all parallel — zero file conflicts)
- **Wave 2:** Phases 4, 6 (parallel — different files)
- **Wave 3:** Phase 7, then Phase 8 (sequential — same files)

---

## Session Log

[Will be updated by /begin]
