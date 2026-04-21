# Cluster-Max Pre-Cutover Test Plan

**Date:** 2026-04-21 (revised after verify-command validation)
**Goal:** Every deliverable in `BUILD_cluster-max.md` has one concrete, runnable verification before Phase 13 flips the four flags. Tests grouped by phase; cutover blockers marked `[BLOCKER]`; still-missing coverage marked `[GAP]`.

**Canonical flags (default OFF until Phase 13):**

- `BR3_RUNTIME_OLLAMA`, `BR3_CACHE_BREAKPOINTS`, `BR3_ADVERSARIAL_3WAY`, `BR3_AUTO_CONTEXT`

**Dispatch envelope invariant (check every phase):**

- `RuntimeRegistry.execute()` / `execute_async()` is the ONLY path to a runtime. Grep must return 0 for direct `ollama` / `requests.post("http://10.0.1.*")` / `subprocess.*curl.*10.0.1.*` outside `core/runtime/ollama_runtime.py` and `tests/`. The regex below covers all three patterns (the curl branch was missing in the prior revision).

---

## Phase 0 — AGENTS.md Foundations (complete)

- [ ] All 6 AGENTS.md files present: 4 in-repo + 2 staged for remote deploy.
  - `ls -1 AGENTS.md core/cluster/AGENTS.md core/runtime/AGENTS.md ui/dashboard/AGENTS.md ~/.buildrunner/agents-md/jimmy.md ~/.buildrunner/agents-md/otis.md`
- [ ] Combined size ≤24KB; each file ≤8KB.
  - `for f in AGENTS.md core/cluster/AGENTS.md core/runtime/AGENTS.md ui/dashboard/AGENTS.md ~/.buildrunner/agents-md/jimmy.md ~/.buildrunner/agents-md/otis.md; do printf "%s\t" "$f"; wc -c < "$f"; done`
- [ ] Root AGENTS.md ≤100 lines.
  - `wc -l < AGENTS.md` ≤100.
- [ ] All AGENTS.md reference exactly the four canonical flags; no `BR3_GATEWAY_LITELLM`, `BR3_LOCAL_ROUTING`, `BR3_MULTI_MODEL_CONTEXT`, `BR3_CLUSTER_MAX`, `BR3_OVERFLOW`. **[BLOCKER — currently fails: `BR3_GATEWAY_LITELLM` still in root AGENTS.md]**
  - `grep -rE "BR3_(GATEWAY_LITELLM|LOCAL_ROUTING|MULTI_MODEL_CONTEXT|CLUSTER_MAX|OVERFLOW)" AGENTS.md core/cluster/AGENTS.md core/runtime/AGENTS.md ui/dashboard/AGENTS.md ~/.buildrunner/agents-md/jimmy.md ~/.buildrunner/agents-md/otis.md` → expected 0 matches.

## Phase 1 — Below hardware (complete, physical)

- [ ] Both 3090s present on Below.
  - `ssh below 'nvidia-smi --query-gpu=name,memory.total --format=csv,noheader'` shows 2 rows of 3090 @ 24GB each.
- [ ] NVLink active, ≥4 links at non-zero GB/s.
  - `ssh below 'nvidia-smi nvlink --status'` shows ≥4 `Link` rows with `GB/s > 0`.

## Phase 2 — Below dual-GPU activation (complete)

- [ ] `OLLAMA_KEEP_ALIVE=24h` set in systemd env for Ollama.
  - `ssh below 'systemctl show ollama --property=Environment' | grep -c KEEP_ALIVE` → ≥1.
- [ ] 70B benchmark ≥18 tok/s on dual-GPU.
  - `ssh below '~/.buildrunner/scripts/below-benchmark.sh llama3.3:70b'` final tok/s ≥18.
- [ ] `num_ctx=2048 num_gpu=99` is the dual-GPU default in below-route.sh.
  - `grep -c 'num_ctx.*2048\|num_gpu.*99' ~/.buildrunner/scripts/below-route.sh` → ≥2.

## Phase 3 — Jimmy memory backbone (complete)

- [ ] Jimmy at 10.0.1.106 responds on its Phase-3 services (semantic-search + intel + staging). `/context/{model}` on :4500 is a Phase 12 surface and is verified there.
  - `curl -f http://10.0.1.106:8100/health` (semantic-search)
  - `curl -f http://10.0.1.106:8101/health` (intel)
  - `curl -f http://10.0.1.106:8200/health` (staging)
- [ ] `/srv/jimmy/` layout exists (minus `archive/cost-ledger/`, deleted 2026-04-21).
  - `ssh jimmy 'test -d /srv/jimmy/research-library && test -d /srv/jimmy/lancedb && test -d /srv/jimmy/memory && test -d /srv/jimmy/backups/projects && test -d /srv/jimmy/backups/buildrunner-state && test -d /srv/jimmy/backups/git-mirrors && test -d /srv/jimmy/backups/supabase && test -d /srv/jimmy/backups/brlogger && test -d /srv/jimmy/archive/adversarial-reviews && test -d /srv/jimmy/archive/lockwood-pre-migration'`
- [ ] UFW default-deny active.
  - `ssh jimmy 'sudo ufw status | head -3'` shows `Status: active`, `Default: deny (incoming)`.
- [ ] Nightly backup timer enabled.
  - `launchctl list | grep com.br3.nightly-backup` (on Muddy/macOS) shows the job loaded.

## Phase 4 — 7-worker cluster + Jimmy add + overflow role-scoped rewrite **[audit tool + wave-merge pending — BLOCKER]**

Phase 4 is the hardcoded-IP rewrite + Jimmy node add + overflow classifier; it is NOT the cluster-daemon.mjs file (that file is Phase-19 build orchestration, unrelated).

- [ ] **Discovery grep produces the canonical hit list.**
  - `grep -rl "10.0.1.101\|10.0.1.104" ~/.buildrunner/ core/cluster/ > /tmp/phase4-targets.txt && wc -l /tmp/phase4-targets.txt` ≈ 20.
- [ ] `cluster.json` has Jimmy node with the three primary roles.
  - `jq '.nodes.jimmy | .role' ~/.buildrunner/cluster.json` returns non-null. (cluster.json uses `.nodes` as an object keyed by node name, not an array — map/select idiom does not apply.)
  - `jq -r '.nodes.jimmy.services | keys[]' ~/.buildrunner/cluster.json` includes `semantic-search`, `intel`, and either `staging` or `context-parity`.
- [ ] `node-matrix.mjs` returns all 7 workers in ranked order.
  - `node ~/.buildrunner/scripts/node-matrix.mjs --dry-run | jq 'length'` → 7.
- [ ] `dispatch-to-node.sh` + `_dispatch-core.sh` branch on `is_linux_node()` for Jimmy.
  - `bash ~/.buildrunner/scripts/dispatch-to-node.sh --dry-run --node jimmy --task ping` exits 0.
- [ ] `is_overflow_worker()` classifier correct.
  - `bash -c 'source ~/.buildrunner/scripts/_dispatch-core.sh && is_overflow_worker lockwood && is_overflow_worker lomax && ! is_overflow_worker otis'` exits 0.
- [ ] **Overflow audit tool exists + passes.** **[BLOCKER — `scripts/audit_overflow_refs.py` does not exist]**
  - `grep -rn "10.0.1.101" ~/.buildrunner/ core/cluster/ > /tmp/phase4-remaining-101.txt && python scripts/audit_overflow_refs.py /tmp/phase4-remaining-101.txt` exits 0.
- [ ] **Overflow dispatch smoke** — Lockwood still reachable as overflow.
  - `bash ~/.buildrunner/scripts/dispatch-to-node.sh --dry-run --node lockwood --task echo` exits 0.
  - `node ~/.buildrunner/scripts/node-matrix.mjs --include-overflow | jq 'map(select(.name == "lockwood")) | length'` → 1.
- [ ] Cluster-check sees all 7 nodes reachable.
  - `~/.buildrunner/scripts/cluster-check.sh all --dry-run` reports 7 reachable.
- [ ] Wave-merge applied (Phase 4 overflow/jimmy content is live in `core/cluster/AGENTS.md`). The staging `.append-phase4.txt` file is intentionally deleted post-merge per fix-plan.
  - `grep -c "overflow\|is_overflow_worker\|jimmy" core/cluster/AGENTS.md` ≥ 2.

## Phase 5 — Below skill integration + firewall **[wave-merge pending — BLOCKER]**

- [ ] `below-route.sh` routes 8 skills (begin, autopilot, review, guard, diag, root, dbg, sdb). Flag name is **`BR3_RUNTIME_OLLAMA`** (not `BR3_LOCAL_ROUTING`). **[BLOCKER — currently gated on `BR3_LOCAL_ROUTING`]**
  - `grep -c 'BR3_RUNTIME_OLLAMA' ~/.buildrunner/scripts/below-route.sh` ≥1; `grep -c 'BR3_LOCAL_ROUTING' ~/.buildrunner/scripts/below-route.sh` → 0.
- [ ] `below-route.sh` passes shellcheck.
  - `shellcheck ~/.buildrunner/scripts/below-route.sh` exits 0. (Skip if `shellcheck` not installed — script is visually reviewed in Phase 5 review.)
- [ ] Below firewall: summarizer never produces final code/diagnosis (in-script guard + skill config).
  - `grep -c 'firewall\|summariz' ~/.buildrunner/scripts/below-route.sh` ≥1 **AND** `grep -cE -- "--mode[[:space:]]+(draft|summary)" ~/.buildrunner/scripts/below-route.sh` ≥1 — `--` sentinel required so grep does not parse `--mode` as an option.
- [ ] `below-route.sh` itself exits **2** when Below is offline (flag gate off OR Ollama unreachable). Callers watch for exit 2 and fall back silently to Claude.
  - Gate off: `BR3_RUNTIME_OLLAMA=off bash ~/.buildrunner/scripts/below-route.sh --mode draft "hi"; echo exit=$?` → prints `exit=2`.
  - Below offline: with Ollama stopped, `BR3_RUNTIME_OLLAMA=on bash ~/.buildrunner/scripts/below-route.sh --mode draft "hi"; echo exit=$?` → prints `exit=2` within 5s.
- [ ] Caller-level silent fallback — dispatching `/begin` or `/review` with Below offline falls back to Claude cleanly. Covered by `tests/integration/test_summarize_before_escalate.py::TestBelowOfflineFallback` (unit-test layer; live dispatch is not part of the dry-run surface).
  - `pytest tests/integration/test_summarize_before_escalate.py::TestBelowOfflineFallback -q` passes.
- [ ] Adversarial-review coverage: Phase 5's standalone patch was superseded by Phase 9's 3-way review implementation.
  - `pytest tests/cluster/test_three_way_review.py -q` passes (covers the adversarial-review contract — 28 tests).
- [ ] Autopilot classifier still routes correctly after Phase 5.
  - `pytest tests/skills/test_autopilot_classifier.py -x`.
- [ ] Wave-merge applied (`AGENTS.md.append-phase5.txt` bytes present in live `core/cluster/AGENTS.md`).
  - `grep -c "below-route\|BR3_RUNTIME_OLLAMA" core/cluster/AGENTS.md` ≥2.

## Phase 6 — OllamaRuntime + RuntimeRegistry (complete)

- [ ] `OllamaRuntime` declares `local_inference` capability.
  - `python -c "from core.runtime.ollama_runtime import OllamaRuntime; print('local_inference' in OllamaRuntime().get_capabilities())"` → prints `True`.
- [ ] `create_runtime_registry()` returns a registry with claude, codex, ollama (covered by the shim tests).
  - `pytest tests/cluster/test_runtime_registry_shim.py::test_create_runtime_registry_has_execute -x` passes.
- [ ] `core/runtime/command_capabilities.json` has 4 capability keys (adds `local_inference`).
  - `jq '.capabilities | keys | length' core/runtime/command_capabilities.json` → 4.
- [ ] `tests/runtime/test_ollama_runtime.py` covers construction, health, execute, 503 fallback.
  - `pytest tests/runtime/test_ollama_runtime.py -x`.

## Phase 7 — RuntimeRegistry shim + cluster-guard (complete, cost ledger deleted)

- [ ] `execute()` + `execute_async()` pass `cache_control` verbatim.
  - `pytest tests/cluster/test_runtime_registry_shim.py -x` → 9/9 pass.
- [ ] Pre-commit hook blocks all three banned patterns.
  - Fixture: stage a file containing `subprocess.run(["ollama","run","x"])` outside whitelist → `git commit` exits 1 with `[cluster-guard] BLOCKED`.
  - Stage `requests.post("http://10.0.1.106/x")` → same.
  - Stage `subprocess.run("curl http://10.0.1.105/x", shell=True)` → same.
- [ ] **Deletion-is-clean check:** no surviving references to cost_ledger/gateway/BR3_GATEWAY/cluster_metrics outside historical notes. **[BLOCKER]**
  - `git grep -E "cost_ledger|gateway_client|cluster_metrics|BR3_GATEWAY" -- ':!*.md'` → 0 matches.

## Phase 8 — Cache breakpoints + summarizer (complete)

- [ ] `cache_policy.py` returns 3 ephemeral breakpoints.
  - `pytest tests/runtime/test_cache_policy.py::test_three_breakpoints -x`.
- [ ] Hard-truncation of LLM-bound content replaced by summarizer in `cross_model_review.py`.
  - `grep -c "summarize_diff\|summariz" core/cluster/cross_model_review.py` ≥1 (summarizer path integrated).
  - `grep -cE '\[:[0-9]{4,}\]' core/cluster/cross_model_review.py` → 0 (no large-content slice truncation — 2-to-3 digit slices for display/log are allowed).
- [ ] Summarizer shrinks 50KB diff to ≤5KB.
  - `pytest tests/integration/test_summarize_before_escalate.py::test_50kb_diff_shrinks -x`.
- [ ] Breakpoints reach Anthropic/Codex/Ollama unmodified via `RuntimeRegistry.execute()`.
  - Covered by `tests/cluster/test_runtime_registry_shim.py::test_execute_passes_cache_control_verbatim` (no separate `test_cache_policy_routing.py` exists — that filename was invented in the prior revision).

## Phase 9 — 3-way adversarial + Opus arbiter (complete)

- [ ] 3-way review calls claude-sonnet + gpt-5.4 + below deepseek-r1 in parallel; arbiter only fires on disagreement.
  - `pytest tests/cluster/test_three_way_review.py -x`.
- [ ] Arbiter uses Opus 4.7 with `effort=xhigh` (or the pinned thinking budget).
  - `grep -cE "effort.*xhigh|claude-opus-4-7|budget_tokens" core/cluster/arbiter.py` ≥2.
- [ ] Round cap 3; `fix_type` required on every finding; persistent-blocker escalation works.
  - `pytest tests/cluster/test_three_way_review.py::TestRoundCap::test_round_cap_enforced tests/cluster/test_three_way_review.py::TestFixType::test_fix_type_required_claude tests/cluster/test_three_way_review.py::TestFixType::test_fix_type_required_codex tests/cluster/test_three_way_review.py::TestPersistentBlocker::test_persistent_blocker_detected -x` — adjust `TestX::` prefixes to match the actual class names in `test_three_way_review.py` if needed; pytest discovery tolerates either bare function IDs or class-prefixed IDs, but class-prefixed is unambiguous.

## Phase 10 — Auto-context hook + reranker (complete except hooks)

- [ ] `auto-context.sh` exists and produces an `<auto-context>` block on non-trivial input. **Env-var must scope to `bash`, not `printf`.**
  - `printf 'how does RLS work\n' | BR3_AUTO_CONTEXT=on bash ~/.buildrunner/hooks/auto-context.sh | grep -c "<auto-context>"` ≥1.
- [ ] Trivial-prompt skip: slash commands do not inject context.
  - `printf '/save\n' | BR3_AUTO_CONTEXT=on bash ~/.buildrunner/hooks/auto-context.sh | grep -c "<auto-context>"` → 0.
- [ ] `count-tokens.sh` tokenizer-true budget enforcement.
  - `printf 'hello world\n' | bash ~/.buildrunner/scripts/count-tokens.sh --model claude` → prints `2` (±1).
- [ ] Reranker returns within budget.
  - `curl -s -X POST http://10.0.1.106:8100/rerank -H 'Content-Type: application/json' -d '{"query":"rls","candidates":["row level security","postgres rls policy","authentication flow","database indexing","edge function"],"limit":3}' -o /dev/null -w '%{time_total}\n'` — median over 50 runs <0.5s.
- [ ] **`UserPromptSubmit` hook registered in `~/.claude/settings.json`.** (Note: `PhaseStart` was historically listed but is NOT a Claude hook event — removed per gap-analysis B10. `UserPromptSubmit` covers the auto-context injection intent.)
  - `jq '.hooks | keys' ~/.claude/settings.json` contains `"UserPromptSubmit"`.

## Phase 11 — Dashboard @ 4400 (complete, 4 panels)

- [ ] HTTP serve: `curl http://10.0.1.106:4400/` returns 200 with `<title>Cluster Max Dashboard</title>`. (Dashboard is hosted on Jimmy, not Muddy — Muddy's `:4400` serves a different product.)
- [ ] WebSocket accepts connections and emits all 4 event types.
  - `wscat -c ws://10.0.1.106:4400/ws` → receives `node-health`, `overflow-reserve`, `storage-health`, `consensus` within 10s.
- [ ] No React/framework deps.
  - `grep -rE "react|vue|svelte|from ['\"]/node_modules" ui/dashboard/` → 0 matches.
- [ ] Exponential backoff capped at 30s (in BACKOFF_SCHEDULE).
  - `grep -E "BACKOFF_SCHEDULE.*30000|30000.*BACKOFF" ui/dashboard/app.js` returns ≥1 line (precise — avoids matching the unrelated `HEARTBEAT_TIMEOUT_MS = 30000`).
- [ ] Jimmy tile shows LanceDB query depth + reranker queue + context-API p95.
  - Manual Playwright snapshot: `playwright test tests/e2e/cluster-max-dashboard.spec.ts` **[BLOCKER — spec not yet written; current `tests/e2e/dashboard.spec.ts` tests the wrong dashboard]**.
- [ ] VRAM headroom gauge on Below goes red at <1GB for >30s.
  - Fixture inject VRAM=0.5GB; assert DOM class `ok-fill-red` on tile within 35s.
- [ ] `ui/dashboard/AGENTS.md` registered-panel table lists exactly 4 panels; no routing-ledger/cost-cache rows.
  - `grep -c "routing-ledger\|cost-cache" ui/dashboard/AGENTS.md` → 0.

## Phase 12 — Multi-model context parity (complete except Otis deploy + timer)

- [ ] `/context/{model}` returns tokenizer-true budget for each of claude/codex/ollama.
  - `curl 'http://10.0.1.106:4500/context/claude?query=rls&phase=12&skill=review' | jq '.budget'` → `{limit:32000, used:<=32000, tokenizer:"claude-v1"}` (NOT `bytes`).
  - Same for `codex` (limit 48000) and `ollama` (limit 16000).
- [ ] Flag name is `BR3_AUTO_CONTEXT` (not `BR3_MULTI_MODEL_CONTEXT`). **[BLOCKER — currently gated on `BR3_MULTI_MODEL_CONTEXT` in `context_injector.py`, `codex-bridge.sh`, `below-route.sh`, and staged AGENTS.md snippets]**
  - `git grep -n "BR3_MULTI_MODEL_CONTEXT"` → 0 matches outside historical markdown.
- [ ] Parity test: each model cites ≥1 item from each of the 5 source types.
  - `pytest tests/cluster/test_multi_model_parity.py -x`.
- [ ] `[private]` filter at mirror AND at extraction.
  - `pytest tests/cluster/test_no_private_leak.py -x`.
- [ ] `filter-private-decisions.sh` strips `[private]` lines end-to-end.
  - `printf '%s\n' '[public] ok' '[private] secret' | bash ~/.buildrunner/scripts/filter-private-decisions.sh | grep -c '\[private\]'` → 0.
- [ ] **[GAP]** Unit coverage for `context_bundle.py` / `context_router.py` / `context_injector.py` exists. Currently only end-to-end parity + leak tests exist.
  - `ls tests/cluster/test_context_bundle.py tests/cluster/test_context_router.py tests/runtime/test_context_injector.py 2>&1` — all three files should exist before Phase 13. Alternative: document in BUILD spec that parity + leak tests are the only intended coverage and delete these deliverables.
- [ ] Otis AGENTS.md deployed (sha256 matches).
  - `ssh otis 'shasum -a 256 ~/AGENTS.md'` == `shasum -a 256 ~/.buildrunner/agents-md/otis.md`. (Otis is macOS; `shasum -a 256` not `sha256sum`.)
- [ ] **`br3-context-sync.timer` enabled on Jimmy. [BLOCKER — currently not done]**
  - `ssh jimmy 'systemctl is-enabled br3-context-sync.timer'` == `enabled`.
- [ ] Mirror populated with read-only bits on Otis.
  - `ssh otis 'ls ~/br3-context/.buildrunner/'` shows `decisions.public.log`, NOT `decisions.log`; permissions `-r--r--r--`. (Mirror lives under `~` because macOS SIP blocks `/srv` writes on Otis.)
- [ ] Below mirror — documented architectural gap (not a Phase 13 blocker).
  - Below is a Windows host without rsync/SSH-pubkey support, so the 5-min sync targets Otis only. Below retrieves context live via `/context/ollama` on Jimmy :4500 (the offline-fast mirror is an Otis-only optimization).

## Phase 13 — Direct cutover + post-cutover smoke **[not started — BLOCKER]**

### Pre-flip checks

- [ ] `~/.buildrunner/config/feature-flags.yaml` exists with all four flags defaulting `off`.
  - `yq '.flags | keys' ~/.buildrunner/config/feature-flags.yaml` → `[BR3_ADVERSARIAL_3WAY, BR3_AUTO_CONTEXT, BR3_CACHE_BREAKPOINTS, BR3_RUNTIME_OLLAMA]` (go-yq v4 syntax; if `yq` is python-yq, use `yq -r '.flags | keys'`).
- [ ] `rollback-cluster-max.sh --dry-run` exits 0 and lists four flag-off actions.
  - `bash ~/.buildrunner/scripts/rollback-cluster-max.sh --dry-run | grep -c 'would flip.*off'` → 4.
- [ ] `post_cutover_smoke.py --dry` compiles and self-documents its 5 checks.
  - `python scripts/post_cutover_smoke.py --dry --list` prints 5 named checks.
- [ ] Pre-commit cluster-guard does not reject Phase 13 bash flip commands.
  - Dry-run: stage `feature-flags.yaml` with all four flags flipped `on`, `git commit --dry-run -m "phase13 flip"` exits 0.

### Flip

- [ ] All four flags set to `on`.
  - `for f in BR3_RUNTIME_OLLAMA BR3_CACHE_BREAKPOINTS BR3_ADVERSARIAL_3WAY BR3_AUTO_CONTEXT; do yq ".flags.$f" ~/.buildrunner/config/feature-flags.yaml; done` → four `on`.

### Post-flip smoke (the 5/5 in `post_cutover_smoke.py`)

- [ ] Check 1 — `BR3_AUTO_CONTEXT`: `/begin` run produces an `<auto-context>` block in the dispatched prompt.
- [ ] Check 2 — `BR3_RUNTIME_OLLAMA`: at least one `RuntimeRegistry.execute()` call returns a `runtime="ollama"` result with 200.
- [ ] Check 3 — `BR3_ADVERSARIAL_3WAY`: `/review` generates findings from claude-sonnet + gpt-5.4 (+ arbiter Opus on disagreement).
- [ ] Check 4 — `BR3_CACHE_BREAKPOINTS`: dispatched prompt payload contains 3 `cache_control:{type:"ephemeral"}` breakpoints.
- [ ] Check 5 — Dashboard `/ws` emits all 4 event types within the smoke window.
  - `python scripts/post_cutover_smoke.py` → `5/5 PASS`.

### Supersede + decisions.log

- [ ] `grep -c "default OFF" AGENTS.md core/cluster/AGENTS.md` → 0.
- [ ] `grep -cE "Last updated:.*Phase 13" AGENTS.md core/cluster/AGENTS.md` → 2.
- [ ] `grep -c "Phase 13: cutover complete" .buildrunner/decisions.log` ≥1.

### 48-hour soak

- [ ] Zero P0/P1 review findings filed in 48 h.
  - `cat .buildrunner/review-findings.jsonl | jq -r 'select(.severity=="P0" or .severity=="P1") | .id' | wc -l` → 0.

## Phase 14 — Self-maintenance (8 timers) **[not started]**

- [ ] 8 timers enabled + active on Jimmy (self-health, model-update, backup-prune, offsite-sync, backup-integrity, archive-prune, lancedb-compact, disk-guard).
  - `ssh jimmy 'systemctl list-timers --all | grep -cE "br3-(self-health|model-update|backup-prune|offsite-sync|backup-integrity|archive-prune|lancedb-compact|disk-guard)\\.timer"'` → 8.
- [ ] No service runs an internal `time.sleep` cadence loop — all are oneshot+timer.
  - `ssh jimmy 'for svc in br3-self-health br3-model-update br3-backup-prune br3-offsite-sync br3-backup-integrity br3-archive-prune br3-lancedb-compact br3-disk-guard; do systemctl cat $svc.service | grep -E "^Type="; done'` → all `Type=oneshot`.
- [ ] Persistent-recovery test: stop `systemd-timesyncd` 6 min, restart, expect next `br3-self-health` fire within 1 min.
  - `ssh jimmy 'sudo systemctl stop systemd-timesyncd && sleep 360 && sudo systemctl start systemd-timesyncd && sleep 60 && systemctl list-timers --all | grep br3-self-health'` shows a `next` within 1 min.
- [ ] `self_health.py` unit coverage.
  - `pytest tests/cluster/test_self_health.py -x`. **[GAP — test file does not exist; deliverable of Phase 14]**
- [ ] Auto-rebalance no-silent-drop.
  - `pytest tests/cluster/test_auto_rebalance.py::test_no_silent_drop -x`. **[GAP — test file does not exist]**
- [ ] Model-update tok/s gate (±10%) enforced.
  - `BR3_MOCK_BENCHMARK=17 bash ~/.buildrunner/scripts/model-update.sh llama3.3:70b --dry-run` → exits 0 (within 10% of 18 tok/s baseline).
  - `BR3_MOCK_BENCHMARK=14 bash ~/.buildrunner/scripts/model-update.sh llama3.3:70b --dry-run` → exits 1 (22% drop — below gate).
- [ ] Disk-guard WARN/CRIT/PAGE all verified on fixtures.
  - `BR3_MOCK_DISK_PCT=82 bash ~/.buildrunner/scripts/disk-guard.sh --dry-run | grep -c WARN` ≥1.
  - `BR3_MOCK_DISK_PCT=93 bash ~/.buildrunner/scripts/disk-guard.sh --dry-run | grep -c CRIT` ≥1.
  - `BR3_MOCK_DISK_PCT=97 bash ~/.buildrunner/scripts/disk-guard.sh --dry-run | grep -c PAGE` ≥1; `ssh jimmy 'test -f /srv/jimmy/status/backups-paused'`.
- [ ] Archive-prune never deletes raw before compressed bundle is fsync'd.
  - `pytest tests/cluster/test_archive_prune.py::test_no_raw_delete_before_compress -x`. **[GAP — test file does not exist]**
- [ ] LanceDB compact aborts on row-count regression.
  - `pytest tests/cluster/test_lancedb_compact.py::test_rowcount_guard -x`. **[GAP — test file does not exist]**
- [ ] All 7 maintenance shell scripts pass shellcheck.
  - `shellcheck ~/.buildrunner/scripts/model-update.sh ~/.buildrunner/scripts/backup-prune.sh ~/.buildrunner/scripts/offsite-sync.sh ~/.buildrunner/scripts/backup-integrity-check.sh ~/.buildrunner/scripts/archive-prune.sh ~/.buildrunner/scripts/lancedb-compact.sh ~/.buildrunner/scripts/disk-guard.sh` exits 0.

---

## System-wide invariants (run on every branch and in CI)

- [ ] RuntimeRegistry is the only dispatch path (matches the envelope invariant at top of doc — covers `subprocess.*ollama`, `requests.*10.0.1.*`, AND `subprocess.*curl.*10.0.1.*`).
  - `git grep -nE "subprocess\.(run|call|Popen).*\bollama\b|subprocess\.(run|call|Popen).*curl.*10\.0\.1\.|requests\.(post|get|put|delete|patch)\s*\(\s*['\"]http://10\.0\.1\." -- ':(exclude)core/runtime/ollama_runtime.py' ':(exclude)tests/' ':(exclude)*.md'` → 0.
- [ ] No cost_ledger / gateway / shadow / divergence / cost_alerts code — markdown + BUILD spec + adversarial-review archives explicitly excluded so historical-note tombstones don't cause false failures.
  - `git grep -nE "cost_ledger|gateway_client|cluster_metrics|shadow_runner|run_shadow_command|compute_shadow_metrics|BR3_GATEWAY|cost_alerts" -- ':(exclude)*.md' ':(exclude).buildrunner/builds/*' ':(exclude).buildrunner/adversarial-reviews/*' ':(exclude).buildrunner/*.log'` → 0.
- [ ] All AGENTS.md files under their size caps.
  - `for f in AGENTS.md core/cluster/AGENTS.md core/runtime/AGENTS.md ui/dashboard/AGENTS.md ~/.buildrunner/agents-md/jimmy.md ~/.buildrunner/agents-md/otis.md; do printf "%s\t" "$f"; wc -c < "$f"; done` — each ≤8KB; combined ≤24KB.
- [ ] `~/.buildrunner/cluster.json` enumerates 6 nodes + master; Jimmy has services for semantic-search(8100), intel(8101), context-parity(4500).
  - `jq '.nodes.jimmy.services' ~/.buildrunner/cluster.json` lists all three.
- [ ] Cluster-guard hook is installed as `.git/hooks/pre-commit`.
  - `readlink .git/hooks/pre-commit` → `../../.buildrunner/hooks/pre-commit-cluster-guard` (or `test -x .git/hooks/pre-commit` if copied).

---

## Order of execution (gate sequence)

1. System-wide invariants pass on `main`.
2. Phase 0 + Phase 1 + Phase 2 + Phase 3 verify clean.
3. Phase 4 wave-merge + `.buildrunner/locks/` skeleton + `audit_overflow_refs.py` + overflow fixture.
4. Phase 5 wave-merge + `BR3_LOCAL_ROUTING` → `BR3_RUNTIME_OLLAMA` rename; Phase 5 tests green.
5. Phase 12 `BR3_MULTI_MODEL_CONTEXT` → `BR3_AUTO_CONTEXT` rename; context\_\* unit tests authored or deliverables removed.
6. Phase 6 + Phase 7 + Phase 8 + Phase 9 + Phase 10 + Phase 11 verify clean.
7. Phase 12 deferred manual deploys executed (Otis scp + Jimmy timer).
8. Phase 13 pre-flip checks pass.
9. Phase 13 flag flip + 5/5 smoke.
10. 48-hour soak with zero P0/P1.
11. Phase 14 timers enable + tests (including authoring the 4 missing `test_*.py` files).
