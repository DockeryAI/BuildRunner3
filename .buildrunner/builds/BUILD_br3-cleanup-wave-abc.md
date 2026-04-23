# Build: BR3 Cleanup — Waves A/B/C

```yaml
role-matrix:
  inherit: default-role-matrix
  overrides:
    phases:
      phase_1: { bucket: terminal-build, assigned_node: muddy }
      phase_2: { bucket: backend-build, assigned_node: muddy }
      phase_3: { bucket: backend-build, assigned_node: muddy }
      phase_4: { bucket: architecture, assigned_node: muddy }
      phase_5: { bucket: backend-build, assigned_node: muddy }
      phase_6: { bucket: terminal-build, assigned_node: muddy }
      phase_7: { bucket: terminal-build, assigned_node: muddy }
      phase_8: { bucket: qa, assigned_node: walter }
```

**Created:** 2026-04-23
**Status:** Phases 1-3 Complete — Phase 3 In Progress
**Deploy:** web — `npm run build` (ui/) + `pip install -e .` (core/)
**Source Plan File:** .buildrunner/plans/plan-br3-cleanup-wave-abc.md
**Source Plan SHA:** 9ed95239e047b6dda4aee8d5eefd41c1c873cfb60ee96f1d15e00c447b785665
**Adversarial Review Verdict:** BYPASSED:.buildrunner/bypass-justification.md
**Adversarial Review Timestamp:** 2026-04-23T20:18:33Z
**Prior-State Survey:** .buildrunner/plans/survey-br3-cleanup-wave-abc.md
**Total Phases:** 8

---

## Overview

Apply the 170-finding dead-code / race / duplicate cleanup derived from today's `/dead` run. Stabilize config, serialize concurrency, consolidate duplicated constants, remove dead files and modules, collapse parallel implementations, prune dependencies. Verified by Walter sweep + ship-runner + `/dead` rerun showing ≥80% finding reduction.

**Explicitly deferred:** Wave A1 (Jimmy stabilization — parallel instance owns), Wave D1 (burn-in cases → `burnin-harness` Phase 12), Wave C1/C2/C3 (future specs), ship pipeline rebuild + confidence-tagging rewrite (user pushback).

## Parallelization Matrix

| Phase | Key Files                                                                                      | Can Parallel With | Blocked By                          |
| ----- | ---------------------------------------------------------------------------------------------- | ----------------- | ----------------------------------- |
| 1     | `.env`, governance/autodebug/quality YAMLs, `cluster.json`, ship-config, feature-flags.yaml    | 4                 | —                                   |
| 2     | `core/persistence/*`, `core/cluster/*.py` (race fixes), `lockwood-sourcer.sh`, research_worker | 4                 | —                                   |
| 3     | `core/cluster/*.py` (constants), `log_utils.py` (NEW), `collect-intel.sh`                      | 4                 | 2 (same files in core/cluster/)     |
| 4     | root `.md`/`.png`/`.sql`, `.dispatch-worktrees/`, `.gitignore`                                 | 1, 2, 3, 5, 6, 7  | —                                   |
| 5     | core/ dead modules, ui/src orphans, ~40 F401 imports                                           | 6, 7              | 3 (imports updated first)           |
| 6     | `.buildrunner/hooks`, wrapper scripts, api+ui/api dedup, YAML schema                           | 4, 5, 7           | —                                   |
| 7     | `ui/package.json`, `pyproject.toml`, lockfiles                                                 | 4, 5, 6           | 5 (dead modules first)              |
| 8     | verification (read-only)                                                                       | —                 | 1, 2, 3, 4, 5, 6, 7 (terminal gate) |

## Phases

### Phase 1: Secrets, Config Honesty & Critical Lies

**Status:** ✅ COMPLETE
**Bucket/Node:** terminal-build / muddy
**Files:**

- `.env` (DELETE), `.gitignore` (MODIFY)
- `~/.buildrunner/cluster.json` (MODIFY)
- `.buildrunner/governance/governance.yaml`, `.buildrunner/autodebug.yaml`, `.buildrunner/quality-standards.yaml`, `.buildrunner/behavior.yaml` (MODIFY)
- `~/.buildrunner/scripts/ship/ship-config.yaml` AND/OR `~/.buildrunner/scripts/ship/healing/fix-orchestrator.sh` (MODIFY)
- `~/.claude/settings.json` AND/OR `~/.buildrunner/scripts/autopilot-dispatch-prefix.sh` (MODIFY)
- `~/.buildrunner/config/feature-flags.yaml`, `scripts/post_cutover_smoke.py`, `scripts/runtime-dispatch.sh`, `scripts/load-cluster-flags.sh` (MODIFY)
- `.buildrunner/data.db`, `.buildrunner/telemetry.db`, `.buildrunner/review-findings.jsonl`, `.worktrees` (DELETE or WIRE)
- Intel cron target (Jimmy `claude` install OR Muddy relocation)

**Blocked by:** None
**Deliverables:**

- [x] `.env` removed from tree, added to `.gitignore`, secret-rotation audit logged
- [x] `cluster.json` Below entry loses 70B decls, gains `vram_required_gib` + `ollama_port: 11434`
- [x] Coverage threshold unified (90 canonical in governance.yaml; others reference)
- [x] `behavior.yaml` invalid values fixed
- [x] `claude_fix` strategy contradiction resolved (implement OR rename)
- [x] Adaptive-thinking contradiction resolved (document choice)
- [x] `BR3_RUNTIME_OLLAMA` fully removed (flag registry + 3 shim sites + smoke test)
- [x] 4 zero-byte artifacts triaged (per-file decision)
- [x] Intel cron preflight check added; `claude: command not found` resolved

### Phase 2: Concurrency Hardening

**Status:** ✅ COMPLETE
**Bucket/Node:** backend-build / muddy
**Files:**

- `core/persistence/{database,event_storage,metrics_db}.py` (MODIFY)
- `core/cluster/below/semantic_cache.py` (MODIFY)
- `core/cluster/{intel_collector,memory_store,cross_model_review,arbiter,node_semantic,hunt_sourcer}.py` (MODIFY)
- `core/cluster/lockwood-sourcer.sh`, `core/cluster/scripts/com.br3.lockwood-sourcer.plist` (MODIFY)
- `core/cluster/below/research_worker.py` (MODIFY)
- `core/parallel/worker_coordinator.py` (MODIFY)
- `tests/test_concurrency_hardening.py` (NEW)

**Blocked by:** None
**Deliverables:**

- [x] SQLite WAL + busy_timeout=5000 in database.py + semantic_cache.py; busy_timeout added to intel_collector + memory_store
- [x] Review lockfile → atomic `open(path, 'x')` in cross_model_review.py:1301
- [x] Arbiter circuit-breaker wrapped in `fcntl.flock` LOCK_EX
- [x] lockwood-sourcer adds `flock`; `_last_checked` migrated to SQLite column
- [x] research_worker pending.jsonl → atomic per-file queue
- [x] WorkerCoordinator + EventStorage + node_semantic indexing protected with threading.Lock
- [x] metrics_db → single INSERT OR REPLACE
- [x] Concurrency test suite repros the old races and demonstrates the fix

### Phase 3: Constants & Path Consolidation

**Status:** 🚧 in_progress
**Bucket/Node:** backend-build / muddy
**Files:**

- `core/cluster/cluster_config.py` (MODIFY)
- `core/cluster/log_utils.py` (NEW)
- 4 JIMMY_URL sites, 8 BELOW_HOST sites, 7 qwen3:8b sites, 4 decisions.log sites (MODIFY)
- `.buildrunner/scripts/developer-brief.sh`, `.buildrunner/scripts/collect-intel.sh` (MODIFY)

**Blocked by:** Phase 2 (same files in core/cluster/\*.py)
**Deliverables:**

- [ ] All JIMMY_URL, BELOW_HOST, Ollama port, qwen3:8b constants route through `cluster_config.py`
- [ ] Copy-paste bug (`os.environ.get("JIMMY_URL", os.environ.get("JIMMY_URL", ...))`) eliminated
- [ ] `get_decisions_log_path()` + `_append_decision_log()` helpers in `log_utils.py`; 4 sites migrated with flock
- [ ] `developer-brief.sh` uses Python module CLI
- [ ] `collect-intel.sh` stages 1-2 migrated to `intel_below_extractor.py`
- [ ] `grep -r "10.0.1.106:8100" core/ cli/ api/` returns only `cluster_config.py`

### Phase 4: File & Doc Cleanup

**Status:** ✅ COMPLETE
**Bucket/Node:** architecture / muddy
**Files:**

- `.legacy`/`.bak`/`.backup` cluster (DELETE)
- `CLAUDE_backup.md` (RENAME)
- `adversarial-review.sh.patch-phase5` (APPLY or DISCARD)
- `.dispatch-worktrees/` (DELETE)
- `docs/archive/` (NEW)
- `docs/screenshots/` (NEW)
- 4 of 5 root RLS SQL files (DELETE; keep V2)
- `RLS Documentation/` (DELETE — space-named dup)
- `.buildrunner/{skills-staging, bypass-justification-*, HANDOFF, BUILD_4E_DAY*, WEEK*}` (ARCHIVE or DELETE)
- `.gitignore` (MODIFY)

**Blocked by:** None
**Deliverables:**

- [x] 10+ `.legacy`/`.bak`/`.backup` files deleted
- [x] `CLAUDE_backup.md` renamed and relocated
- [x] `patch-phase5` resolved; `BUILD_cluster-max.md` status reconciled
- [x] `.dispatch-worktrees/` purged (22 stale DBs gone)
- [x] Root `.md` proliferation archived (~40 files)
- [x] Root PNGs moved to `docs/screenshots/`
- [x] Only `PROPER_RLS_POLICIES_V2.sql` remains at root; duplicate RLS Documentation dir deleted
- [x] `.gitignore` covers: `.env`, `build/`, `coverage.json`, `/*.png`, `.dispatch-worktrees/`
- [x] Every deletion logged to `decisions.log`

### Phase 5: Dead Module & Import Removal

**Status:** not_started
**Bucket/Node:** backend-build / muddy
**Files:**

- 8 orphan core modules (DELETE after audit)
- 3 plugin modules (DELETE unless wired)
- 5 orphan UI components + BuildMonitor.tsx decision + example files (DELETE)
- ~40 F401 import fixes across cli/, api/, core/
- Dead stubs (\_check_quality_full, average_resolution_time)
- `.buildrunner/scripts/activate-all-systems.sh:705` (FIX label)
- 3 zero-byte non-package `__init__.py` (DELETE)

**Blocked by:** Phase 3
**Deliverables:**

- [ ] Pre-delete caller audit clears for each orphan module (resolves Codex/dead disagreement on `rls_aware.py`)
- [ ] 8 orphan core Python modules deleted
- [ ] Plugin decision executed (wire or delete)
- [ ] 5+ orphan UI components deleted; BuildMonitor decision executed
- [ ] ~40 F401 imports removed (`ruff check --select F401` clean on cli/, api/, core/)
- [ ] Dead stubs removed or implemented
- [ ] Phase 13→14 label fixed
- [ ] `python -c "import core, cli, api"` succeeds; `npm run build` passes

### Phase 6: Competing Implementations Merge

**Status:** 🚧 in_progress
**Bucket/Node:** terminal-build / muddy
**Files:**

- `.buildrunner/hooks/{pre-commit*,pre-push*}` (CONSOLIDATE)
- `.buildrunner/scripts/install*-hooks.sh` (MERGE)
- `scripts/runtime-dispatch.sh` + `~/.buildrunner/scripts/runtime-dispatch.sh` (DISAMBIGUATE)
- `scripts/load-role-matrix.sh` project version (DELETE; migrate callers to global)
- `dispatch-to-otis.sh` / `dispatch-phase-to-otis.sh` (DELETE one; fix arg order)
- `api/openrouter_client.py` + `ui/api/openrouter_client.py` (CONSOLIDATE)
- `api/project_manager.py` + `ui/api/project_manager.py` (CONSOLIDATE)
- `api/routes/prd_builder.py` + `ui/api/routes/prd_builder.py` (CONSOLIDATE)
- `load-role-matrix.sh` schema (MODIFY — add `pin`); `resolve-dispatch-node.py` (REMOVE regex sanitizer)
- `build/` (DELETE + gitignore); `post_cutover_smoke.py` (ARCHIVE); `rollout-state.yaml` (RECONCILE)

**Blocked by:** None
**Deliverables:**

- [ ] Pre-commit → only `pre-commit-enforced` remains
- [ ] Pre-push → only `pre-push-enforced` (+ auto-appended `pre-push.d/50-ship-gate.sh`) remains
- [ ] Single installer script (enforced-only; no `--standard` mode)
- [ ] `runtime-dispatch.sh` disambiguated via header comments
- [ ] `load-role-matrix.sh` project version deleted; all callers migrated
- [ ] `dispatch-to-otis` arg-order bug resolved
- [ ] 3 pairs of api/ui-api modules consolidated
- [ ] `pin: true` accepted natively by load-role-matrix; regex sanitizer removed; fixture round-trip verified
- [ ] `build/` gitignored + deleted; `post_cutover_smoke.py` archived; `rollout-state.yaml` reflects post-cutover

### Phase 7: Dependency Hygiene

**Status:** not_started
**Bucket/Node:** terminal-build / muddy
**Files:**

- `ui/package.json` + `ui/package-lock.json` (MODIFY)
- `electron/package.json` (MODIFY)
- `pyproject.toml` (MODIFY)
- `requirements-api.txt` (MODIFY)
- `core/cluster/below/semantic_cache.py` (MAYBE MODIFY)

**Blocked by:** Phase 5
**Deliverables:**

- [ ] 18 @radix-ui packages removed (or shadcn generated — choice documented)
- [ ] `socket.io-client` + duplicate toast dep removed
- [ ] `pyperclip`, direct `websockets` removed
- [ ] `notion-client` + 4× OTel instrumentations moved to `[project.optional-dependencies]`
- [ ] `pydantic>=2` declared explicitly
- [ ] `sqlite-vec` decision executed (wire or remove)
- [ ] npm `overrides` (not Yarn `resolutions`) for react-is, commander, brace-expansion; `npm dedupe` clean
- [ ] `ui/` build passes; `python -c "import core, cli, api"` smoke passes

### Phase 8: Verification & Sentinel Sweep

**Status:** not_started
**Bucket/Node:** qa / walter
**Files:** read-only verification
**Blocked by:** 1, 2, 3, 4, 5, 6, 7
**Deliverables:**

- [ ] Walter sentinel sweep green
- [ ] `ship-runner.sh --fast` all gates pass
- [ ] `/dead` rerun ≤34 findings (≥80% reduction vs 170 baseline); delta saved to Jimmy
- [ ] Dashboard loads clean; 5 touched scripts smoke-pass (adversarial-review, cross_model_review, ship-runner, dispatch-to-node, lockwood-sourcer)
- [ ] `decisions.log` audit complete (every Phase 4/5 deletion logged)
- [ ] Final rollup note saved to Jimmy

## Session Log

[Will be updated by /begin]
