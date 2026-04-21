# Cluster-Max Cutover Fix Plan

**Date:** 2026-04-21
**Source:** `.buildrunner/cluster-max-pre-cutover-test-plan.md` execution results
**Goal:** Unblock Phase 13 flag flip; defer Phase 14 self-maintenance until after cutover.

---

## Blocker inventory (from test run)

| Category                                                                                | Count                                                                                                                                  |
| --------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Flag renames not done (BR3_LOCAL_ROUTING, BR3_MULTI_MODEL_CONTEXT, BR3_GATEWAY_LITELLM) | 3 code paths, 37+ refs                                                                                                                 |
| Missing scripts                                                                         | 5 (audit_overflow_refs.py, count-tokens.sh, feature-flags.yaml, rollback script, smoke script)                                         |
| Wave-merges not applied                                                                 | 2 (Phase 4, Phase 5 AGENTS.md snippets)                                                                                                |
| Hook registrations missing                                                              | 2 (UserPromptSubmit, PhaseStart)                                                                                                       |
| Missing test files                                                                      | 7 (autopilot_classifier, cache_policy, summarize_before_escalate, context_bundle, context_router, context_injector, dashboard.spec.ts) |
| Jimmy deploys not done                                                                  | 3 (context API :4500, Otis AGENTS.md scp, context-sync timer)                                                                          |
| Dashboard down                                                                          | 1 (localhost:4400 not serving)                                                                                                         |
| `auto-context.sh` broken                                                                | 1 (emits 0 blocks)                                                                                                                     |

Phase 14 (self-maintenance) is entirely unbuilt but is **not a Phase 13 blocker** per BUILD spec `Blocked by: Phase 13`.

---

## Execution waves

### Wave A — Flag renames (single commit per file, no logic changes)

1. **`BR3_LOCAL_ROUTING` → `BR3_RUNTIME_OLLAMA`** in `~/.buildrunner/scripts/below-route.sh` (3 refs). Verify: `grep -c BR3_LOCAL_ROUTING` → 0; `grep -c BR3_RUNTIME_OLLAMA` → ≥1.
2. **`BR3_MULTI_MODEL_CONTEXT` → `BR3_AUTO_CONTEXT`** across:
   - `api/routes/context.py` (4 refs)
   - `core/cluster/context_bundle.py` (3 refs)
   - `core/cluster/context_router.py` (if present — verify)
   - `core/cluster/context_injector.py` (if present — verify)
   - `~/.buildrunner/scripts/codex-bridge.sh`
   - `~/.buildrunner/scripts/below-route.sh`
   - `core/cluster/AGENTS.md.append-phase12.txt`
   - `~/.buildrunner/agents-md/jimmy.md`
   - `~/.buildrunner/agents-md/otis.md`
     Verify: `git grep -n BR3_MULTI_MODEL_CONTEXT` → 0 outside `.md/.log` historical files.
3. **Remove `BR3_GATEWAY_LITELLM`** from root `AGENTS.md:30`.
4. Update `.buildrunner/cluster-max-pre-cutover-test-plan.md` to strike the now-resolved BLOCKER annotations.

### Wave B — New scripts

5. `scripts/audit_overflow_refs.py` — consumes a file of grep hits for `10.0.1.101/104`, exits 0 if every remaining ref is in an allowed overflow context (dispatch-to-node, node-matrix, cluster.json, overflow classifier) or inside a comment; exits 1 on first raw hardcoded IP outside that whitelist.
6. `~/.buildrunner/scripts/count-tokens.sh --model {claude,codex,ollama}` — reads stdin, shells out to the model-appropriate tokenizer (tiktoken for codex, anthropic-tokenizer for claude, `ollama show --template` or llama-cpp counter for ollama). Prints integer token count. Must not use `wc -c` / 4.
7. `~/.buildrunner/config/feature-flags.yaml` — YAML with `flags: { BR3_RUNTIME_OLLAMA: off, BR3_CACHE_BREAKPOINTS: off, BR3_ADVERSARIAL_3WAY: off, BR3_AUTO_CONTEXT: off }`.
8. `~/.buildrunner/scripts/rollback-cluster-max.sh [--dry-run]` — rewrites feature-flags.yaml setting all 4 to `off`, re-exports env, prints `would flip <name> off` 4× under `--dry-run`.
9. `scripts/post_cutover_smoke.py [--dry --list]` — 5 named checks (`auto_context_block`, `ollama_execute`, `adversarial_3way_findings`, `cache_breakpoints_3`, `dashboard_ws_4_events`). `--list` prints names; `--dry` compiles and self-documents; bare call runs the full suite and prints `5/5 PASS` or `N/5 FAIL: <names>`.

### Wave C — Wave-merges (direct edits to `core/cluster/AGENTS.md`)

10. Append content of `core/cluster/AGENTS.md.append-phase4.txt` into `core/cluster/AGENTS.md` (adds overflow/is_overflow_worker/jimmy rows). Delete the `.append-phase4.txt` file post-merge.
11. Author `core/cluster/AGENTS.md.append-phase5.txt` (missing — only the Phase 4 one exists) containing below-route.sh + BR3_RUNTIME_OLLAMA contract; then merge. ≤400 bytes. Verify: `grep -c "below-route\|BR3_RUNTIME_OLLAMA" core/cluster/AGENTS.md` ≥2.

### Wave D — Hook wiring + auto-context fix

12. Register `UserPromptSubmit` hook in `~/.claude/settings.json` running `~/.buildrunner/hooks/auto-context.sh`. (`PhaseStart` is not a Claude hook name — acknowledge in BUILD spec that Phase 10 gap B10 resolves as UserPromptSubmit-only; Skip invented schema.)
13. Fix `auto-context.sh`: currently emits 0 `<auto-context>` blocks on real input. Likely cause — tokenizer/reranker call fails silently and script exits without output. Add: (a) `set -eo pipefail`; (b) if tokenizer/reranker unavailable, emit empty `<auto-context/>` block so dispatch doesn't break; (c) unit test: `printf 'how does RLS work\n' | ... | grep -c "<auto-context>"` → ≥1.

### Wave E — Missing tests (author + verify green)

14. `tests/skills/test_autopilot_classifier.py` — classifier routes correctly after Phase 5 changes.
15. `tests/runtime/test_cache_policy.py::test_three_breakpoints` — `cache_policy.py` returns 3 ephemeral breakpoints.
16. `tests/integration/test_summarize_before_escalate.py::test_50kb_diff_shrinks` — 50KB diff → ≤5KB post-summarize.
17. `tests/cluster/test_context_bundle.py` — 5 source types, [private] filter, tokenizer-true budget, exit-2 fail-closed.
18. `tests/cluster/test_context_router.py` — claude=32K/codex=48K/ollama=16K budgets enforced.
19. `tests/runtime/test_context_injector.py` — RuntimeRegistry wrapper injects context on flag=on, pass-through on flag=off.
20. `tests/e2e/cluster-max-dashboard.spec.ts` — Playwright: Jimmy tile, VRAM-red-at-0.5GB-for-35s, 4-panel grid.

### Wave F — Jimmy deploys

21. Deploy context API on Jimmy :4500. Systemd unit `br3-context-api.service` running `uvicorn api.routes.context:app --port 4500` with `BR3_AUTO_CONTEXT=on` only after Phase 13 flip (until then, the endpoint 503s per design). Verify reachable: `curl http://10.0.1.106:4500/context/claude?query=rls&phase=12&skill=review` returns JSON with `budget.tokenizer="claude-v1"`.
22. scp `~/.buildrunner/agents-md/otis.md` → `otis:~/AGENTS.md`. Verify sha256 match.
23. Enable `br3-context-sync.timer` on Jimmy. Verify `systemctl is-enabled` → `enabled`.
24. Seed read-only mirror on Otis and Below: `/srv/br3-context/.buildrunner/decisions.public.log` with 0444; verify `[private]` lines absent.

### Wave G — Dashboard uptime

25. Investigate why `:4400` is not serving. Likely the node process crashed or was never started in this session. Start via `~/.buildrunner/scripts/dashboard-start.sh` (author if missing) and add systemd user-unit `br3-dashboard.service` on Muddy with `Restart=on-failure`.
26. WebSocket 4-event smoke: emit node-health + overflow-reserve + storage-health + consensus within 10s of connect.

### Wave H — Nice-to-haves (not Phase 13 blockers)

27. Enable `br3-nightly-backup.timer` on Muddy (Phase 3 gap, non-blocker).
28. Resolve Phase 6 capability naming: code returns `local_inference`; test plan says `local_ready`. Update test plan to `local_inference` (code is source of truth since `test_ollama_runtime.py` 16/16 passes).
29. Leave historical `BR3_GATEWAY*` refs in `decisions.log` (historical tombstones per invariant exclusion `:(exclude).buildrunner/*.log`).

---

## Phase 13 execution (after Waves A–G)

30. Re-run full pre-cutover test plan; all BLOCKERs must clear.
31. Run `post_cutover_smoke.py --dry --list` → prints 5 names.
32. `rollback-cluster-max.sh --dry-run` → 4 "would flip off" lines.
33. Flip 4 flags: edit `feature-flags.yaml` setting each to `on`, commit with `[phase13-flip]` tag.
34. Run `post_cutover_smoke.py` live → `5/5 PASS`.
35. Update AGENTS.md headers: strip `default OFF` language, add `Last updated: Phase 13`.
36. `decisions.log` entry: `Phase 13: cutover complete`.
37. 48-hour soak: no P0/P1 findings in `.buildrunner/review-findings.jsonl`.

## Phase 14 (starts only after Phase 13 soak clean)

38. Author 7 bash scripts + 2 Python modules (model-update, backup-prune, offsite-sync, backup-integrity-check, archive-prune, lancedb-compact, disk-guard; self_health, auto_rebalance).
39. Author 4 tests (`test_self_health`, `test_auto_rebalance`, `test_archive_prune`, `test_lancedb_compact`).
40. Deploy 8 systemd timers on Jimmy (5-min self-health, weekly model-update, 04:30 backup-prune, Sun 05:00 offsite-sync, Sun 06:00 backup-integrity, 04:45 archive-prune, quarterly lancedb-compact, 15-min disk-guard). All `Persistent=true`, all oneshot.
41. Persistent-recovery test: stop `systemd-timesyncd` 6 min; timer fires within 1 min of restart.
42. Update `core/cluster/AGENTS.md` with retention matrix + disk-guard thresholds (≤900 added bytes).

---

## Gate sequence

1. Wave A lands on `main` (flag renames single-commit per file).
2. Wave B lands (5 new scripts authored + shellcheck-clean where applicable).
3. Wave C wave-merges; delete `.append-phase*.txt` files.
4. Wave D hook wire + auto-context fix; verify block emitted.
5. Wave E tests all green.
6. Wave F Jimmy deploys; health endpoints respond.
7. Wave G dashboard up on :4400; WS emits 4 events.
8. Re-run pre-cutover test plan → 0 BLOCKERs.
9. Phase 13 flip + 5/5 smoke + 48h soak.
10. Phase 14 build + deploy.

## Risk register

- **R1:** Flag renames missed in a staged AGENTS snippet → wave-merge lands inconsistent doc. Mitigation: Wave A includes the staged snippets; Wave C reads them post-rename.
- **R2:** `auto-context.sh` fix may depend on Jimmy reranker availability → test must pass with reranker down (empty `<auto-context/>` fallback).
- **R3:** Dashboard restart may expose stale WebSocket state (older connections leak). Mitigation: systemd `Restart=on-failure` + client-side 30s backoff cap already in `app.js`.
- **R4:** Context API on :4500 startup ordering — must start AFTER semantic-search :8100 because it depends on reranker. Add `After=br3-semantic-search.service` in unit file.
- **R5:** `post_cutover_smoke.py` check 3 (adversarial 3-way) may flake on LLM variance — retry once per BR3 E2E policy; single retry documented in smoke script.
