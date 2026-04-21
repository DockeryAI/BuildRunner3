# Cluster-Max Gap Analysis — Pre-Phase-13 Cutover

**Date:** 2026-04-21 (revised after codebase verification)
**Canonical flags:** `BR3_RUNTIME_OLLAMA`, `BR3_CACHE_BREAKPOINTS`, `BR3_ADVERSARIAL_3WAY`, `BR3_AUTO_CONTEXT` (default OFF until Phase 13)
**Status table ground truth:** Phases 0-3, 6-12 complete; Phases 4, 5, 13, 14 not_started.

---

## Cutover Blockers (must fix before flipping flags)

### B1. Phase 4 deliverables partially complete; audit tool missing + wave-merge pending

- **Phase 4 actual deliverables** (per BUILD_cluster-max.md:899–917): hardcoded-IP rewrite audit, `cluster.json` Jimmy node addition, `node-matrix.mjs` 7-worker ranking, `dispatch-to-node.sh`/`_dispatch-core.sh` Jimmy-linux branch, `is_overflow_worker()` helper, `scripts/audit_overflow_refs.py`, staged `AGENTS.md.append-phase4.txt`. **Not** `~/.buildrunner/scripts/cluster-daemon.mjs` — that file exists but its header identifies it as Phase-19 cluster build orchestration, unrelated to Phase-4 overflow routing. The prior revision of this document conflated the two.
- **Present:** `cluster.json` has `jimmy` entry (services: semantic-search, intel, staging). `is_overflow_worker()` classifies lockwood/lomax correctly (verified). `AGENTS.md.append-phase4.txt` is staged.
- **Missing:** `scripts/audit_overflow_refs.py` does not exist — required to prove every remaining `10.0.1.101` reference is overflow-classified. Wave-merge of `AGENTS.md.append-phase4.txt` into live `core/cluster/AGENTS.md` has not run. `.buildrunner/locks/` main-repo skeleton absent (N6).
- **Fix:** author `scripts/audit_overflow_refs.py`; run it against `/tmp/phase4-remaining-101.txt`; wave-merge the staged snippet; create `.buildrunner/locks/` skeleton.
- **Owns:** Phase 4 close-out. Hard blocker for Phase 5 wave-merge and Phase 13.

### B2. Phase 5 status conflict + wave-merge not executed

- Status table says `not_started`; phase body says `COMPLETE (2026-04-20)`.
- `core/cluster/AGENTS.md.append-phase5.txt` exists; not merged into live AGENTS.md.
- `below-route.sh` deliverable checkboxes in the BUILD spec are unchecked.
- **Owns:** Phase 5 cleanup + wave-merge. Hard blocker for Phase 13.

### B3. Non-canonical flag `BR3_LOCAL_ROUTING` gates Phase 5

- `core/cluster/AGENTS.md.append-phase5.txt` and `~/.buildrunner/scripts/below-route.sh:30` gate all below-route skills on `BR3_LOCAL_ROUTING=on`.
- Not in the canonical four. Phase 13 will not flip it.
- **Fix:** alias `BR3_LOCAL_ROUTING` → `BR3_RUNTIME_OLLAMA` in `below-route.sh` + snippet before merge.
- **Owns:** Phase 5.

### B3b. Non-canonical flag `BR3_MULTI_MODEL_CONTEXT` gates Phase 12

- `BUILD_cluster-max.md` lines 1419, 1457, 1474, 1489, 1504 all reference `BR3_MULTI_MODEL_CONTEXT` as the live gate for Phase 12 context parity. It is documented as "default OFF until Phase 13," but Phase 13 only flips the canonical four.
- **Fix:** alias `BR3_MULTI_MODEL_CONTEXT` → `BR3_AUTO_CONTEXT` (or fold into it) in `context_injector.py`, `codex-bridge.sh`, `below-route.sh`, and all staged AGENTS.md snippets before Phase 13.
- **Owns:** Phase 12 cleanup.

### B4. Deleted flag `BR3_GATEWAY_LITELLM` leaks across multiple files

- Root `AGENTS.md:30` still advertises the deleted flag.
- `.buildrunner/cluster-max-pre-cutover-test-plan.md` itself lists `BR3_GATEWAY_LITELLM` as an active BLOCKER probe (meaning the flag name persists in live planning docs, not just the test assertion).
- `BUILD_cluster-max.md` continues to label port 4500 as "gateway" in Phase 0 AGENTS.md (line 547), Phase 3 bootstrap (line 817), and Phase 12 deliverable description (line 1468 "behind gateway"). The worktree name `wave3-gateway` is still present (line 1084).
- Phase 13 Claude Review blocks on stale live instructions.
- **Fix:** supersede-delete the flag from root `AGENTS.md`; rewrite port-4500 labels in BUILD spec from "gateway" to "context-parity"; drop the `wave3-gateway` historical reference.
- **Owns:** Immediate cleanup, not a phase.

### B5. `UserPromptSubmit` / `PhaseStart` hooks not registered in `~/.claude/settings.json`

- Phase 10 deferred hook registration. Current hooks: PreToolUse, SessionStart, PostToolUse, Stop — neither `UserPromptSubmit` nor `PhaseStart` is present.
- `~/.buildrunner/hooks/auto-context.sh` exists but is not wired.
- Phase 13 smoke check 1 (auto-context injection) will fail empty.
- **Owns:** Phase 13 pre-step.

### B6. Phase 12 deferred manual deploys never executed

- `scp otis.md → 10.0.1.103:~/AGENTS.md` — not done. (Source `~/.buildrunner/agents-md/otis.md` is present on Muddy.)
- `systemctl enable br3-context-sync.timer` on Jimmy — not done (ssh confirms `not-found`). `/srv/br3-context/` read-mounts empty.
- Live `/context/{model}` smoke — never run.
- Without the timer, `BR3_AUTO_CONTEXT` fires with an empty bundle.
- **Owns:** Phase 13 deploy window.

### B7. `~/.buildrunner/scripts/rollback-cluster-max.sh` does not exist

- Phase 13 deliverable; file absent.
- **Owns:** Phase 13.

### B8. `scripts/post_cutover_smoke.py` does not exist

- Phase 13 deliverable; file absent. No `5/5 PASS` possible without it.
- **Owns:** Phase 13.

### B9. `~/.buildrunner/config/feature-flags.yaml` does not exist

- Phase 13's verify command `yq ".flags.$f" ~/.buildrunner/config/feature-flags.yaml` has no file to read.
- **Fix:** create file with all four flags defaulting `off`, _then_ flip them in the same phase.
- **Owns:** Phase 13 pre-step.

### B11. `~/.buildrunner/cluster.json` missing Jimmy's context-parity service entry

- `jimmy.services` lists `semantic-search` (8100), `intel` (8101), `staging` (8200). No `context-parity` entry for port 4500 `/context/{model}`.
- `jimmy.description` still contains "cost ledger" among other stale bits — whole description needs a rewrite, not just one phrase.
- Promoted from N5: the test plan's system-wide invariant asserts Jimmy exposes all three services (semantic-search, intel, context-parity); without the JSON entry the invariant fails before any phase runs.
- **Fix:** one JSON edit before Phase 13 pre-steps (add `context-parity` service on 4500 + rewrite description).
- **Owns:** Immediate cleanup, not a phase.

### B10. `BUILD_cluster-max.md` has internal stale references that Claude Review will flag

- Beyond the port-4500 "gateway" labels called out in B4, the BUILD spec's Phase 5 and Phase 12 deliverable sections drive the non-canonical flags in B3/B3b. The spec needs a cleanup pass so that re-running Phase 5/12 verifications don't re-introduce the deleted concepts.
- **Phase 0 still enforces 5 flags.** BUILD line 541–542 requires `grep -c "BR3_" core/cluster/AGENTS.md` ≥5 and line 564 Claude Review demands "all 5 feature flags … encoded." After canonicalising to four, these assertions will silently fail closed or (worse) prompt re-introduction of a non-canonical flag to satisfy the count. Change ≥5 to ≥4; rewrite "all 5" to "all 4" in the review text.
- **Hook event name inconsistent.** BUILD Phase 10 header and deliverable text say `PromptSubmit` (lines 1271, 1273, 1319), but the actual Claude Code hook schema uses `UserPromptSubmit`. The revised test plan and gap-analysis now say `UserPromptSubmit` — align the BUILD spec so all three agree.
- `cost_ledger`, `gateway_client`, `shadow_runner` appear only in tombstone/prohibition notices (Phases 7, 8, 13, 14) — those are fine and should remain.
- **Fix:** single editorial pass on BUILD_cluster-max.md to resolve (a) B3 `BR3_LOCAL_ROUTING` → `BR3_RUNTIME_OLLAMA`, (b) B3b `BR3_MULTI_MODEL_CONTEXT` → `BR3_AUTO_CONTEXT`, (c) Phase-0 5→4 flag count, (d) port-4500 "gateway" labels at lines 547, 817, 1084, 1468, (e) `PromptSubmit` → `UserPromptSubmit`, in one commit before Phase 13.
- **Owns:** Immediate cleanup, not a phase.

---

## Cutover-Safe (but worth noting)

### N1. `/context/{model}` endpoint comment still says "behind gateway"

- `api/routes/context.py:3` references the deleted LiteLLM gateway; port 4500 itself is correct.
- **Fix:** trim the comment; no functional impact. (Paired with the B4/B10 label rewrite.)

### N2. BRLogger v3 pipeline is not addressed anywhere in cluster-max

- The 6-component BRLogger stack (BRLogger.tsx, supabaseLogger.ts, vite plugins, devLog.ts, br-listen.mjs) is silent in `BUILD_cluster-max.md`.
- Consequence: once `BR3_RUNTIME_OLLAMA` routes to Below/Jimmy via Python, BRLogger has a blind spot on local inference (it captures Supabase SDK calls, not RuntimeRegistry dispatch).
- Not a cutover-blocker — BRLogger is framework-level, consumed per-project.
- **Track:** add a separate BRLogger-↔-RuntimeRegistry integration note to `.buildrunner/runtime-observability.md`.

### N3. Post-deletion dashboard has no dispatch/flag/cache visibility

- Surviving panels: node-health, overflow-reserve, storage-health, consensus.
- No panel shows: runtime-per-dispatch, dispatch failure rate, cache hit rate, live flag state.
- If Below silently fails under `BR3_RUNTIME_OLLAMA`, only the node-health online/offline tile sees it.
- **Fix (future, not cutover):** add a minimal `dispatch-status` panel in a post-cutover phase if the blind spot bites.

### N4. `tests/e2e/dashboard.spec.ts` tests the wrong dashboard

- Spec asserts `taskList`, `agentPool`, `telemetryTimeline` — generic BR3 app dashboard at port 3000, not the cluster-max panels at 4400.
- Phase 11 marked complete against the wrong target.
- **Fix:** add `tests/e2e/cluster-max-dashboard.spec.ts` that drives `ws://10.0.1.106:4400/ws` and asserts the 4 event types.

### N5. (PROMOTED TO BLOCKER B11 — see below)

### N6. `.buildrunner/locks/phase-<N>/heartbeat` only lives in dispatch-worktrees

- Main repo has no `locks/` directory. Pattern works today because Codex autopilot uses worktrees; Phase 4's daemon needs to create the main-repo structure.
- **Owns:** Phase 4 (tracked alongside B1).

### N7. Pre-commit cluster-guard does NOT collide with BRLogger

- BRLogger posts to Supabase cloud (`VITE_SUPABASE_URL`), never to `10.0.1.*`. No risk today.
- The pre-commit hook at `.git/hooks/pre-commit` additionally calls `~/.buildrunner/scripts/recall-on-tool.sh` and `~/.buildrunner/hooks/bash-guard.sh`; neither is a Phase 13 deliverable, but their interaction with the Phase 13 flag-flip bash commands should be smoke-tested before cutover.
- **Action:** dry-run the rollback + cutover bash commands against the guard before Phase 13 go-live.

---

## Priority execution order for cutover

1. **Immediate cleanup (no phase):** delete `BR3_GATEWAY_LITELLM` from root `AGENTS.md` and rewrite port-4500 "gateway" labels in BUILD spec + Phase-0 flag-count 5→4 + `PromptSubmit`→`UserPromptSubmit` (B4, B10); fix `cluster.json` context-parity entry (B11); fix stale "behind gateway" comment (N1).
2. **Phase 4 close-out:** wave-merge + create `.buildrunner/locks/` skeleton (B1, N6).
3. **Phase 5 finish:** resolve `BR3_LOCAL_ROUTING` → `BR3_RUNTIME_OLLAMA`, wave-merge, flip status table (B2, B3).
4. **Phase 12 finish:** resolve `BR3_MULTI_MODEL_CONTEXT` → `BR3_AUTO_CONTEXT` (B3b).
5. **Phase 13 pre-steps:** create `feature-flags.yaml`, register hooks, run Phase 12 deferred deploys, dry-run pre-commit guard interaction (B5, B6, B9, N7).
6. **Phase 13 deliverables:** write `rollback-cluster-max.sh` + `post_cutover_smoke.py` (B7, B8).
7. **Phase 13 cutover:** flip the four flags, run smoke, update AGENTS.md via supersede.
8. **Phase 14:** self-maintenance timers.
