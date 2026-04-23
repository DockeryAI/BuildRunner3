# Plan: BR3 Cleanup — Waves A/B/C

**Slug:** `br3-cleanup-wave-abc`
**Source:** Today's `/dead` analysis (~170 findings) + user-provided Wave A/B/C/D cleanup plan.
**Excluded (owned elsewhere):** Wave A1 Jimmy stabilization (parallel instance); Wave D1 burn-in cases (folded into existing `burnin-harness` Phase 12); Wave C1/C2/C3 (deferred to future specs); ship-pipeline rebuild + confidence-tagging rewrite (explicit user pushback).

## Adversarial Review Notes (2026-04-23 consensus)

Codex reviewer flagged several paths as "not present in the tree" — these are **stale-tree artifacts** (verified present at review time): `cli/` (33 items per `ls`), `plugins/` (notion.py/slack.py/github.py), `electron/package.json`, `.dispatch-worktrees/` (11 worktrees), `/api/memory/note` (endpoint returned `{"status":"saved"}` minutes earlier in this session). These findings are noted but do not require plan changes; they reflect a stale context snapshot on the Codex side. Arbiter circuit was open (exactly the race Phase 2 fixes — `arbiter.py:50-66` no-lock pattern), so the verdict defaulted to BLOCK without true arbitration. Bypass executed under the skill's 1-review rule; legitimate fixable findings applied inline above this section.

## Prior-State Survey

**File:** `.buildrunner/plans/survey-br3-cleanup-wave-abc.md`

51 prior BUILDs. Closest precedent: `cluster-library-consolidation` (consolidate-then-delete pattern). Active build `burnin-harness` Phase 12 absorbs Wave D1. Single known-bad legacy state (`adversarial-review.sh.patch-phase5`) addressed in Phase 4. Shared `core/cluster/*.py` surface serialized 2→3→5.

## Purpose

Apply 170-finding cleanup: secrets out of tree, config contradictions resolved, concurrent writers correct, duplicated constants consolidated, dead files/modules removed, parallel implementations collapsed, dependencies pruned. Verified by Walter sweep + ship-runner + `/dead` rerun showing ≥80% finding reduction.

## Tech Stack

Python (`core/`, `cli/`, `api/`), shell (`.buildrunner/scripts/`), TypeScript (`ui/src/`), YAML config, SQLite (WAL), launchd plist.

## Capability Inventory (final state)

1. `.env` not in tree; `.gitignore` complete (env, build/, coverage.json, \*.png at root, .dispatch-worktrees/)
2. Single coverage threshold (90 in `governance.yaml`, others reference)
3. `claude_fix` strategy is honest (implemented or renamed)
4. `cluster.json` Below entry has `vram_required_gib` + `ollama_port`; no 70B decls
5. `BR3_RUNTIME_OLLAMA` deprecated cleanly (zero references outside git history)
6. SQLite uses WAL + busy_timeout=5000 in all multi-writer paths
7. Atomic review lockfile (`open(path, 'x')`); no TOCTOU
8. Arbiter circuit breaker actually trips under concurrent failures
9. `lockwood-sourcer.sh` cannot double-fire (flock + SQLite-backed `_last_checked`)
10. `research_worker` pending queue is line-shift-immune (per-file atomic)
11. One source of truth for: `JIMMY_URL`, `BELOW_HOST`, Ollama port, `qwen3:8b`, `decisions.log` path
12. `collect-intel.sh` no longer calls `claude -p` at stages 1-2 (uses `intel_below_extractor.py`)
13. Root tree clean: only canonical files, no .legacy/.bak/.backup/.patch/screenshots/old build docs
14. Orphan Python modules + UI components deleted; ~40 F401 imports removed
15. One pre-commit hook, one pre-push hook, one runtime-dispatch.sh, one load-role-matrix.sh, one `OpenRouterClient`, one `ProjectManager`, one `prd_builder` router
16. `pin: true` accepted natively by load-role-matrix schema (regex sanitizer removed)
17. `build/` gitignored; stale `post_cutover_smoke.py` archived; rollout-state reflects post-cutover
18. ui/ deps minus 18 unused @radix packages + socket.io + duplicate toast; Python deps clean
19. Walter green; ship-runner all gates pass; `/dead` rerun ≤34 findings

## Parallelization Matrix

| Phase | Can Parallel With | Blocked By                          |
| ----- | ----------------- | ----------------------------------- |
| 1     | 4                 | —                                   |
| 2     | 4                 | —                                   |
| 3     | 4                 | 2 (same files in core/cluster/)     |
| 4     | 1, 2, 3, 5, 6, 7  | —                                   |
| 5     | 6, 7              | 3 (imports updated first)           |
| 6     | 4, 5, 7           | —                                   |
| 7     | 4, 5, 6           | 5 (dead modules first)              |
| 8     | —                 | 1, 2, 3, 4, 5, 6, 7 (terminal gate) |

---

### Phase 1: Secrets, Config Honesty & Critical Lies

**Goal:** No secrets in tree. No config contradictions. Four zero-byte artifacts decided (3 DBs + 1 jsonl). cluster.json reflects reality. Intel cron actually runs.
**Effort:** xHigh (irreversible decisions about config truth)
**Bucket/Node:** terminal-build / muddy
**Blocked by:** None

**Files:**

- `.env` (DELETE from tree), `.gitignore` (MODIFY — add .env)
- `~/.buildrunner/cluster.json` (MODIFY — strip 70B Below model decls; add Below `vram_required_gib`, `ollama_port: 11434`)
- `.buildrunner/governance/governance.yaml` (MODIFY — coverage canonical = 90)
- `.buildrunner/autodebug.yaml`, `.buildrunner/quality-standards.yaml`, `.buildrunner/behavior.yaml` (MODIFY — reference governance; fix `behavior.yaml` invalid values)
- `~/.buildrunner/scripts/ship/ship-config.yaml` AND/OR `~/.buildrunner/scripts/ship/healing/fix-orchestrator.sh` (MODIFY — resolve `claude_fix`)
- `~/.claude/settings.json` AND/OR `~/.buildrunner/scripts/autopilot-dispatch-prefix.sh` (MODIFY — resolve adaptive-thinking contradiction; document choice)
- `~/.buildrunner/config/feature-flags.yaml`, `scripts/post_cutover_smoke.py`, `scripts/runtime-dispatch.sh`, `scripts/load-cluster-flags.sh` (MODIFY — remove `BR3_RUNTIME_OLLAMA`)
- `.buildrunner/data.db`, `.buildrunner/telemetry.db`, `.buildrunner/review-findings.jsonl`, `.worktrees` (DELETE or WIRE — per-file decision)
- Intel cron target (Jimmy `claude` install OR Muddy SSH-write relocation)

**Tasks:**

1. Audit `.env` — confirm all 8 secret keys; rotate any that may have entered git history; remove from tree; add to `.gitignore`; create `.env.example` with placeholders
2. Audit cluster.json consumers for 70B Below model references; strip from cluster.json; add `vram_required_gib` per remaining model; add `ollama_port: 11434` to Below entry
3. Set `governance.yaml:87 coverage_threshold: 90` as canonical; replace numeric values in `autodebug.yaml`, `quality-standards.yaml`, `behavior.yaml` with comments referencing governance.yaml
4. Fix `behavior.yaml`: `verbosity: normal`, `max_retries: 3`, `coverage_threshold: 90`
5. Decide `claude_fix`: implement in fix-orchestrator.sh (preferred — invoke `claude -p` repair prompt) OR rename to `linter_fix` in ship-config.yaml. Document choice in decisions.log
6. Decide adaptive-thinking: remove `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING=1` from settings.json (trust prefix), OR remove the prefix injection (trust env var). Document choice
7. Remove `BR3_RUNTIME_OLLAMA` from feature-flags.yaml + post_cutover_smoke.py; delete the 3 shim sites in runtime-dispatch.sh + load-cluster-flags.sh
8. Triage 4 zero-byte files: per-file decide WIRE (initialize schema, populate) vs DELETE; act
9. Intel cron: `ssh jimmy 'which claude'` first; if missing, install via `npm i -g @anthropic-ai/claude-code` OR move cron from Jimmy to Muddy with SSH-write target. Add preflight `command -v claude || { echo "FATAL: claude not found"; exit 1; }` to every cron script

**Success Criteria:** `git grep -E "(SUPABASE_SERVICE_ROLE|ANTHROPIC_API_KEY|BELOW_PASS)"` returns 0 hits; `grep -r "BR3_RUNTIME_OLLAMA" ~/.buildrunner` returns 0 hits; `cat ~/.buildrunner/cluster.json | jq '.nodes.below.models'` shows no 70B; behavior.yaml validates against `api/config_service.py`.

---

### Phase 2: Concurrency Hardening

**Goal:** All concurrent writers correct. No "database is locked", no review TOCTOU, no sourcer double-invocation, no pending.jsonl line-shift loss.
**Effort:** xHigh (correctness gates)
**Bucket/Node:** backend-build / muddy
**Blocked by:** None (file sets diverge from Phase 1)

**Files:**

- `core/persistence/database.py` (MODIFY)
- `core/cluster/below/semantic_cache.py` (MODIFY)
- `core/cluster/intel_collector.py`, `core/cluster/memory_store.py` (MODIFY)
- `core/cluster/cross_model_review.py` (MODIFY — review lock TOCTOU at L1301-1314)
- `core/cluster/arbiter.py` (MODIFY — circuit-breaker flock at L50-66, L166-190)
- `core/cluster/lockwood-sourcer.sh`, `core/cluster/scripts/com.br3.lockwood-sourcer.plist` (MODIFY)
- `core/cluster/below/research_worker.py` (MODIFY — pending.jsonl atomic queue, L829-841)
- `core/parallel/worker_coordinator.py` (MODIFY — threading.Lock, L118-157)
- `core/persistence/event_storage.py` (MODIFY — rotate lock, L57-68)
- `core/persistence/metrics_db.py` (MODIFY — INSERT OR REPLACE, L116-133)
- `core/cluster/node_semantic.py` (MODIFY — indexing globals lock, L55-58, L654-746)
- `core/cluster/hunt_sourcer.py` (MODIFY — `_last_checked` → SQLite column)
- `tests/test_concurrency_hardening.py` (NEW — race repros)

**Tasks:**

1. Add `PRAGMA journal_mode=WAL` + `PRAGMA busy_timeout=5000` in `database.py:_init_connection()`; mirror in `semantic_cache.py:_ensure_init()`
2. Add `PRAGMA busy_timeout=5000` (after existing WAL set) in `intel_collector.py:_get_intel_db()` and `memory_store.py:_get_db()`
3. Replace `if lock_path.exists(): raise; lock_path.write_text(...)` in `cross_model_review.py:1301-1314` with `try: open(lock_path, 'x') as f: f.write(...) except FileExistsError: raise`
4. Wrap `_load_circuit_state` + `_save_circuit_state` in `arbiter.py` with `fcntl.flock(fd, LOCK_EX)` around the full read-modify-write; release on commit
5. `lockwood-sourcer.sh`: add `exec 9>/tmp/br3-sourcer.lock; flock -n 9 || exit 0` at top. Add `last_checked_at TIMESTAMP` column to `active_hunts` table; migrate `_last_checked` reads/writes to SELECT/UPDATE
6. `research_worker.py:829-841`: replace `pending.jsonl` line-indexed read+remove with per-file directory queue (`pending/<uuid>.json`); read = pick file, process, `os.remove(file)` (atomic on POSIX)
7. Add `threading.Lock()` to `WorkerCoordinator`; protect all `self.workers/task_queue/task_assignments` reads+writes
8. Add `threading.Lock()` to `EventStorage`; protect `save()` method (covers `should_rotate` + `_rotate` + write)
9. Replace SELECT-then-INSERT in `metrics_db.py:save_metric()` with single `INSERT OR REPLACE`
10. Replace `if _indexing: return; _indexing = True` patterns in `node_semantic.py` (both background indexer and research indexer) with `threading.Lock()` acquire/release
11. Write `tests/test_concurrency_hardening.py` — at least one repro per fix (10 concurrent writers; parallel review dispatch; double sourcer launch; concurrent pending.jsonl appends)

**Success Criteria:** `pytest tests/test_concurrency_hardening.py` passes; manual: 10 concurrent writers to `data.db` produce no `database is locked`; parallel `adversarial-review.sh` invocations on same plan produce exactly 1 review JSON.

---

### Phase 3: Constants & Path Consolidation

**Goal:** One source of truth for `JIMMY_URL`, `BELOW_HOST`, Ollama port, `qwen3:8b` model, `decisions.log` path. Fix copy-paste bug. Kill `claude -p` from collect-intel.sh.
**Effort:** High
**Bucket/Node:** backend-build / muddy
**Blocked by:** Phase 2 (same files in core/cluster/\*.py)

**Files:**

- `core/cluster/cluster_config.py` (MODIFY — ensure `get_jimmy_semantic_url`, `get_below_ollama_url`, add `BELOW_MODEL`, `OLLAMA_PORT` constants)
- `core/cluster/log_utils.py` (NEW — `get_decisions_log_path()`, `_append_decision_log(prefix, event, details)`)
- `core/cluster/{delivery_tracker,hunt_sourcer,node_tests,node_staging}.py` (MODIFY — JIMMY_URL dups)
- `core/cluster/below/{embed,schema_classifier,pr_body,semgrep_triage}.py` (MODIFY — BELOW_HOST dups)
- `core/cluster/scripts/intel_below_extractor.py`, `core/cluster/hunt_sources/{bhphoto,newegg}.py`, `core/runtime/ollama_runtime.py` (MODIFY — BELOW_HOST/MODEL dups)
- `core/cluster/{intel_scoring,node_inference,summarizer,arbiter,cross_model_review,context_bundle}.py`, `api/routes/dashboard_stream.py` (MODIFY — qwen3:8b OR decisions.log path)
- `.buildrunner/scripts/developer-brief.sh` (MODIFY)
- `.buildrunner/scripts/collect-intel.sh` (MODIFY — remove claude -p stages 1-2)

**Tasks:**

1. Add `BELOW_MODEL = "qwen3:8b"` and `OLLAMA_PORT = 11434` to `cluster_config.py`; export `get_below_model()`, `get_ollama_port()` helpers
2. Create `core/cluster/log_utils.py` with `get_decisions_log_path()` (single resolution: repo root via git, fallback `~/Projects/BuildRunner3/.buildrunner/decisions.log`) + `_append_decision_log(prefix, event, details)` using `fcntl.flock` (combines with Phase 2 finding)
3. Replace 4 `JIMMY_URL =` module-level inits with `from core.cluster.cluster_config import get_jimmy_semantic_url`; call at use-site (fixes inner-environ-get bug)
4. Replace 8 `BELOW_HOST =`/`BELOW_OLLAMA_URL =` inits with `get_below_ollama_url()`
5. Replace 7 `qwen3:8b` literals/constants with `get_below_model()` import
6. Migrate 4 `decisions.log` write sites (`arbiter.py:69`, `cross_model_review.py:981`, `context_bundle.py:45`, `dashboard_stream.py:319`) to `_append_decision_log()`
7. `developer-brief.sh`: replace inline `python3 -c` cluster.json read with `python3 -m core.cluster.cluster_config get-node-count` (add CLI entrypoint to module if missing)
8. `collect-intel.sh`: delete `claude -p` invocations at stages 1-2 (lines per current file); replace with `python3 -m core.cluster.scripts.intel_below_extractor`; preserve stage 3 review call

**Success Criteria:** `grep -rn "10.0.1.106:8100" core/ cli/ api/` returns only `cluster_config.py`; `grep -rn "qwen3:8b" core/` returns only `cluster_config.py`; `grep -rn "claude -p" .buildrunner/scripts/collect-intel.sh` returns no stage-1/2 hits.

---

### Phase 4: File & Doc Cleanup

**Goal:** Root directory presentable. Legacy/backup files gone. patch-phase5 resolved. Doc/screenshot clutter archived.
**Effort:** Medium
**Bucket/Node:** architecture / muddy
**Blocked by:** None

**Files:**

- `.legacy`/`.bak`/`.backup` cluster: `~/.buildrunner/scripts/{adversarial-review.sh,auto-review-diff.sh,cross-model-review.sh}.legacy`, `~/.claude/settings.json.bak-1776800810`, `cli/main.py.bak`, `CLAUDE.md.backup-20260320` (DELETE)
- `CLAUDE_backup.md` (RENAME → `.buildrunner/historical/BUILD_3.1_TASK_ORCHESTRATION_COMPLETE.md`)
- `~/.buildrunner/scripts/adversarial-review.sh.patch-phase5` (APPLY or DISCARD; reconcile `.buildrunner/builds/BUILD_cluster-max.md` Phase 5 status)
- `.dispatch-worktrees/` (DELETE all 11 worktrees + 22 stale DBs)
- `docs/archive/` (NEW directory)
- ~40 root `.md` files → `docs/archive/`: `BUILD_*` (×8), `BUILD_MONITOR_*` (×5), `BUILD_PLAN_*` (×3), `FEATURE_*` (×3), `GAP_ANALYSIS*` (×3), `WEBSOCKET_*` (×4), `GEO-*` (×8), `WEEK*_PROMPT*`, `MISSING_SYSTEMS_*` (×2), `SYNAPSE_INTEGRATION_COMPLETE.md`, `FIRST_BUILD.md`, `rollback-test.md`, `RELEASE_NOTES_v3.0.0.md` (non-FINAL), `BUILD_TO_100_COMPLETE.md`, `BUILD_COMPLETION_v3.1.0.md`, `BUILD_3.2_COMPLETE.md`
- `docs/screenshots/` (NEW); 20+ root `.png` → `docs/screenshots/`
- `FIX_RLS_POLICIES.sql`, `COMPLETE_RLS_FIX.sql`, `PROPER_RLS_POLICIES.sql`, `CHECK_RLS_STATUS.sql` (DELETE; keep `PROPER_RLS_POLICIES_V2.sql`)
- `RLS Documentation/` (DELETE — space-named duplicate of `RLS_Documentation/`)
- `.buildrunner/skills-staging/`, `.buildrunner/bypass-justification-*.md` (×4), `.buildrunner/HANDOFF_2025_11_17.md`, `.buildrunner/BUILD_4E_DAY*.md`, `.buildrunner/WEEK1_*.md`, `.buildrunner/WEEK2_*.md` (DELETE or → `.buildrunner/historical/`)
- `.gitignore` (MODIFY — add `.env`, `build/`, `coverage.json`, `*.png` (root only — preserve `docs/screenshots/`), `.dispatch-worktrees/`)
- `coverage.json` (DELETE)

**Tasks:**

1. Inventory all `.legacy`/`.bak`/`.backup` files (excluding `.dispatch-worktrees/` which gets nuked separately); confirm with diff vs counterpart; `git rm` each
2. Rename `CLAUDE_backup.md` to `.buildrunner/historical/BUILD_3.1_TASK_ORCHESTRATION_COMPLETE.md` (`mkdir -p` first)
3. patch-phase5 decision: read patch + canonical adversarial-review.sh, decide apply OR discard. If apply: `git apply`. Either way: update `BUILD_cluster-max.md:940,994` status to match reality
4. `git rm -rf .dispatch-worktrees/` (all 11)
5. `mkdir -p docs/archive`; `git mv` ~40 root `.md` files in stale-doc list to `docs/archive/`
6. `mkdir -p docs/screenshots`; `git mv` 20+ root `.png` files
7. Delete 4 of 5 root RLS SQL files; keep V2 only
8. Delete `RLS Documentation/` (space variant)
9. `.buildrunner/historical/` for skills-staging, bypass-justifications, HANDOFF, BUILD_4E_DAY\*, WEEK1/WEEK2 prompt series; OR delete if older than 60 days with no decisions.log reference
10. `.gitignore` add: `.env`, `build/`, `coverage.json`, `/*.png` (root only), `.dispatch-worktrees/`; `git rm --cached coverage.json`. Append every deletion to `decisions.log` with `[DECISION] removed <path> because <reason> on 2026-04-23`

**Success Criteria:** Root `.md` count drops from ~80 to ≤15 (keep canonical project docs: CLAUDE.md, README.md, CHANGELOG.md, SECURITY.md, COMMANDS.md, CONTRIBUTING.md, PROJECT_SPEC.md, PROJECT_SPEC_COMPLETION.md, QUICKSTART.md, AGENTS.md, LICENSE, RESUME_HERE.md, RELEASE_NOTES_v3.0.0_FINAL.md, RELEASE_NOTES_v3.1.0.md, CODE_OF_CONDUCT.md); root `.png` count = 0 (all moved to `docs/screenshots/`); root `.sql` count = 1 (`PROPER_RLS_POLICIES_V2.sql`); `find . -name "*.legacy" -o -name "*.bak" -not -path "*/.dispatch-worktrees/*"` returns empty.

**Sequencing note:** `core/rls_aware.py` contains a string literal referencing `PROPER_RLS_POLICIES.sql`. That module is deleted in Phase 5. Phase 4 RLS SQL deletion is safe either way — if Phase 4 lands first, `rls_aware.py` continues to reference a deleted file for its short remaining life until Phase 5 removes it; no runtime consumer of `rls_aware.py` will fire in that window (it's a documentation-guidance helper, not a hot path).

---

### Phase 5: Dead Module & Import Removal

**Goal:** 8 orphan Python modules deleted. 5 orphan UI components deleted. ~40 F401 imports removed. Dead stubs gone. Phase 13/14 mislabel fixed.
**Effort:** xHigh (multi-file deletion + import audit)
**Bucket/Node:** backend-build / muddy
**Blocked by:** Phase 3 (imports updated first)

**Files:**

- `core/feature_discovery.py`, `core/migration_mapper.py`, `core/rls_aware.py`, `core/completeness_validator.py`, `core/storybook_generator.py`, `core/visual_regression.py`, `core/opus_handoff.py`, `ui_terminal.py` (DELETE)
- `plugins/notion.py`, `plugins/slack.py`, `plugins/github.py` (DELETE unless wired in this phase — choose; if delete, remove `plugins/__init__.py` references)
- `ui/src/components/{TerminalDemo,PRDEditorV2,PRDChatInterface,PRDMarkdownPreview,MonacoPRDEditor}.tsx` (DELETE) + their CSS
- `ui/src/pages/BuildMonitor.tsx` (ROUTE in `App.tsx` OR DELETE — choose)
- `ui/src/components/ProgressSidebar.example.tsx`, `ui/src/examples/useBuildMonitor.example.ts` (DELETE)
- F401 cleanup: `cli/main.py:24-28`, `cli/build_commands.py:23,25,17,18`, `cli/design_commands.py:9`, `cli/parallel_commands.py:7,12,13`, `cli/telemetry_commands.py:11,16`, `cli/routing_commands.py:11,16`, `cli/security_commands.py:18,19`, `cli/agent_commands.py:13,24`, `cli/parallel_build_commands.py:17`, `api/main.py:8,18`, `api/websocket_handler.py:6`, `api/routes/build.py:6`, `api/routes/analytics.py:12,17`, `core/auto_debug.py:16,21`, `core/batch_optimizer.py:13,14`, `core/adaptive_planner.py:19`, `core/dashboard_views.py:19`, `core/feature_discovery_v2.py:16`, `core/prd_integration.py:22,23`, `core/planning_mode.py:8`, `core/governance.py:9`, `core/governance_enforcer.py:11`, `core/cluster/cross_model_review.py:1347,1349`, `core/runtime/runtime_registry.py:257`
- Dead stubs: `core/auto_debug.py:945` `_check_quality_full()` + caller `:652`; `api/main.py:299` `average_resolution_time` field
- `.buildrunner/scripts/activate-all-systems.sh:705` (FIX label)
- Zero-byte `__init__.py`: `hooks/__init__.py`, `api/services/__init__.py`, `core/cluster/scripts/__init__.py` (DELETE — keep tests/\* per pytest discovery)
- `.worktrees`, `.buildrunner/review-findings.jsonl` (DELETE)

**Tasks:**

1. Pre-delete audit for each of 8 orphan core modules — `grep -rn "from core\.<module> import\|import core\.<module>" cli/ api/ core/ plugins/ hooks/ tests/` — verify zero production import sites outside tests; for `core/rls_aware.py` specifically, also `grep -rn "inject_rls_awareness\|RLSDocumentationGuide\|get_rls_context" .` (Codex flagged this module as live; /dead analysis said orphan — this step resolves the disagreement). `git rm` only after audit clears
2. Plugin decision: wire (`br notify` CLI subcommand) OR delete; act per choice
3. Delete 5 orphan UI components + associated CSS; `git rm`
4. BuildMonitor decision: route in `ui/src/App.tsx` (add `<Route path="/build-monitor">`) OR delete; act
5. Delete `*.example.tsx` and `*.example.ts` from production src tree
6. Run `ruff check --select F401,F841` on cli/, api/, core/ — auto-fix what's safe; manually verify the others against the audit list
7. Remove `_check_quality_full()` and its caller line in `auto_debug.py`; remove `average_resolution_time=None` field + TODO from `api/main.py:299`
8. `activate-all-systems.sh`: change `Phase 13:` label at L705 to `Phase 14:`
9. Delete 3 zero-byte non-package `__init__.py`; delete `.worktrees` (file), `.buildrunner/review-findings.jsonl` (file)
10. Verify: `python -c "import core; import cli; import api"` succeeds; `cd ui && npm run build` succeeds

**Success Criteria:** `ruff check --select F401 cli/ api/ core/` reports 0 errors; `npm run build` in ui/ passes; deleted modules' names no longer match in `grep -rn "from core.feature_discovery import\|import core.feature_discovery" .`.

---

### Phase 6: Competing Implementations Merge

**Goal:** One pre-commit hook, one pre-push hook (with auto-appended ship-gate), one runtime-dispatch.sh, one load-role-matrix.sh, one dispatch-to-otis wrapper, one OpenRouterClient, one ProjectManager, one prd_builder router. YAML `pin: true` accepted natively.
**Effort:** xHigh (irreversible consolidation; touches load-bearing dispatch surfaces)
**Bucket/Node:** terminal-build / muddy
**Blocked by:** None (file sets diverge from Phase 3/5)

**Files:**

- `.buildrunner/hooks/{pre-commit,pre-commit-composed,pre-commit-enforced,pre-push,pre-push-composed,pre-push-enforced}` (CONSOLIDATE: keep enforced variants; delete others)
- `.buildrunner/hooks/pre-push.d/50-ship-gate.sh` (PRESERVE — auto-append after consolidation)
- `.buildrunner/scripts/install-hooks.sh` + `install-enforced-hooks.sh` (MERGE)
- `scripts/runtime-dispatch.sh` + `~/.buildrunner/scripts/runtime-dispatch.sh` (RECONCILE — rename project version with clear scope; document in both files' headers)
- `scripts/load-role-matrix.sh` + `~/.buildrunner/scripts/load-role-matrix.sh` (MIGRATE callers to global canonical; DELETE project version; verify `resolve-dispatch-node.py` still works)
- `.buildrunner/scripts/dispatch-to-otis.sh`, `.buildrunner/scripts/dispatch-phase-to-otis.sh` (DELETE one — pick `dispatch-phase-to-otis.sh` (matches `dispatch-to-node.sh` arg order); update callers)
- `api/openrouter_client.py` + `ui/api/openrouter_client.py` (CONSOLIDATE → keep `api/openrouter_client.py` with both methods; update `ui/api/routes/prd_builder.py` import)
- `api/project_manager.py` + `ui/api/project_manager.py` (CONSOLIDATE → `api/project_manager.py` with optional lightweight mode)
- `api/routes/prd_builder.py` + `ui/api/routes/prd_builder.py` (CONSOLIDATE → keep `api/routes/prd_builder.py`; remove `ui/api/routes/`)
- `.buildrunner/scripts/load-role-matrix.sh` (MODIFY — add `pin` to schema)
- `.buildrunner/scripts/resolve-dispatch-node.py` (MODIFY — remove regex sanitizer at L101-126)
- `build/` (DELETE; add to `.gitignore`)
- `scripts/post_cutover_smoke.py` (MOVE → `scripts/archive/`)
- `.buildrunner/rollout-state.yaml` (MODIFY — set `flipped_at` to actual cutover date 2026-04-21; update `mode`)

**Tasks:**

1. Diff `pre-commit` vs `pre-commit-composed` vs `pre-commit-enforced`; collapse to `pre-commit-enforced` only; delete other two; update `install-hooks.sh` to install enforced + auto-link `50-ship-gate.sh`
2. Same for `pre-push` variants; preserve `pre-push.d/50-ship-gate.sh` integration
3. Merge `install-hooks.sh` + `install-enforced-hooks.sh` into a single installer that installs only the enforced variants (no `--standard` mode); ensure `pre-push.d/50-ship-gate.sh` is auto-linked/appended after install
4. Rename `scripts/runtime-dispatch.sh` → `scripts/runtime-dispatch-project.sh`; add header comment "DISTINCT from ~/.buildrunner/scripts/runtime-dispatch.sh — project-local Python entrypoint only"; mirror header in global version
5. Audit callers of `scripts/load-role-matrix.sh`; migrate each to `~/.buildrunner/scripts/load-role-matrix.sh`; delete project version
6. Delete `dispatch-to-otis.sh`; update any callers to use `dispatch-phase-to-otis.sh` arg order; document in script header
7. Move `OpenRouterClient` from `ui/api/openrouter_client.py` into `api/openrouter_client.py` (add `parse_project_description()` method); delete `ui/api/openrouter_client.py`; update `ui/api/routes/prd_builder.py` import
8. Same consolidation for `ProjectManager` (add lightweight mode)
9. Same consolidation for `prd_builder.py` route file; verify FastAPI registers correctly
10. Add `pin: true` (boolean, optional) to load-role-matrix.sh YAML schema (python3 + yaml.safe_load path); remove regex sanitizer in resolve-dispatch-node.py:101-126; verify burnin/lib/conditions.sh `yq` path still works; archive `post_cutover_smoke.py`; reconcile rollout-state.yaml `flipped_at: 2026-04-21T00:00:00Z, mode: enforced`; `git rm -rf build/`; `.gitignore` add `build/`

**Success Criteria:** `ls .buildrunner/hooks/pre-commit*` returns exactly `pre-commit-enforced`; `ls .buildrunner/hooks/pre-push*` returns exactly `pre-push-enforced` (+ `pre-push.d/`); test pre-push triggers ship-gate; `find . -path "*/runtime-dispatch.sh"` shows clearly-named files; `pin: true` round-trip verified by running `~/.buildrunner/scripts/load-role-matrix.sh <test-spec-with-pin>` and confirming the resolved output preserves the `pin` field (create test fixture as part of task 10; no regex sanitizer invoked).

**Sequencing note:** Phase 6's "disambiguate" pass on dual `runtime-dispatch.sh` files documents the distinction via header comments rather than physically deleting one — the two serve different callers (project-local Python entrypoint vs infra-level dispatcher). Full physical merge is deferred to a future cluster-infrastructure spec where caller migration can happen under test.

---

### Phase 7: Dependency Hygiene

**Goal:** Unused deps removed. Duplicate packages deduped. `pydantic` declared explicitly. npm lock clean.
**Effort:** Medium
**Bucket/Node:** terminal-build / muddy
**Blocked by:** Phase 5 (dead-module deletion may eliminate dep consumers)

**Files:**

- `ui/package.json` + `ui/package-lock.json` (MODIFY)
- `electron/package.json` (MODIFY — remove `electron-reload` if still commented out)
- `pyproject.toml` (MODIFY)
- `requirements-api.txt` (MODIFY)
- `core/cluster/below/semantic_cache.py` (MAYBE MODIFY — wire `import sqlite_vec` if keeping the dep)

**Tasks:**

1. Decide @radix-ui: full removal (preferred — `ui/src/components/ui/` is `.gitkeep`-only, shadcn never populated) OR generate shadcn wrappers. Document choice
2. Remove all 18 `@radix-ui/*` packages from `ui/package.json` (per choice above); also `socket.io-client`; resolve toast double-decl by keeping `react-hot-toast`
3. Remove `electron-reload` from `electron/package.json` if `main.js` line 11-14 still has the require commented out
4. Python: remove `pyperclip` (zero callers); remove direct `websockets==12.0` from `requirements-api.txt` (uvicorn[standard] covers it)
5. Move `notion-client` + 4× `opentelemetry-instrumentation-*` from `pyproject.toml` `[project.dependencies]` to `[project.optional-dependencies]` (group: `plugins`, `telemetry`)
6. Add `pydantic>=2.0` to `pyproject.toml` `[project.dependencies]`
7. Decide `sqlite-vec`: wire (add `import sqlite_vec; sqlite_vec.load(conn)` in `semantic_cache.py:_ensure_init()`) OR remove from `requirements-api.txt`
8. `npm dedupe` in `ui/`; add `overrides` field (npm 8+ native, NOT Yarn `resolutions`) to `ui/package.json` for `react-is: 18.x`, `commander: 8.x`, `brace-expansion: 2.x`; regenerate `package-lock.json`
9. Verify build: `cd ui && npm install && npm run build`; verify Python imports: `pip install -e . && python -c "import core, cli, api; print('ok')"` (no separate test file — smoke import only)
10. Confirm bundle size delta (expected ≥1.5MB drop in `node_modules/@radix-ui/`)

**Success Criteria:** `npm ls @radix-ui/react-slot` shows single version; `npm ls react-is` shows single version; `pip check` clean; `du -sh ui/node_modules` decreases vs baseline; ui build still passes.

---

### Phase 8: Verification & Sentinel Sweep

**Goal:** Walter validates. Ship-runner all gates pass. `/dead` rerun shows ≥80% finding reduction. No regressions.
**Effort:** High (cross-system verification)
**Bucket/Node:** qa / walter
**Blocked by:** 1, 2, 3, 4, 5, 6, 7

**Files:** read-only verification

**Tasks:**

1. Walter sentinel sweep — run on the consolidated branch; require green
2. `~/.buildrunner/scripts/ship/ship-runner.sh --fast` — all gates green; if blocked, fix and re-run
3. Smoke-test 5 touched scripts manually: `adversarial-review.sh` (consensus mode), `cross_model_review.py --mode plan`, `ship-runner.sh --dry-run`, `dispatch-to-node.sh otis test`, `lockwood-sourcer.sh` (one cycle)
4. Re-run `/dead` skill; confirm ≤34 findings (≥80% reduction from 170 baseline); save delta to Jimmy via `/api/memory/note`
5. Verify dashboard loads; verify no import errors in browser console; verify api/server.py boots
6. Audit `decisions.log` — every deletion in Phase 4/5 has a corresponding `[DECISION] removed <path>` entry; if missing, append now
7. Save final rollup note to Jimmy: `topic: br3-cleanup-wave-abc COMPLETE — N findings remaining`

**Success Criteria:** Walter green; ship-runner all gates pass; `/dead` rerun ≤34 findings; dashboard loads cleanly; decisions.log audit complete.

---

## Out of Scope (deferred to other specs)

- Wave A1 — Jimmy stabilization (parallel instance owns)
- Wave C1 — Real job queue (SQLite-backed) → future spec `br3-job-queue`
- Wave C2 — Skills portability audit (80 skills) → future spec `br3-skills-portable`
- Wave C3 — BR3 framework-vs-consumer split → future spec
- Wave D1 — Burn-in cases for BR3 scripts → existing `burnin-harness` Phase 12
- Ship pipeline rebuild (user pushback — working as designed)
- Confidence-tagging rewrite (user pushback — load-bearing differentiator)
- `governance.yaml:174-185 quality.thresholds.overall: 50→70` raise (separate Walter-gated migration)
