# Adversarial Review: BUILD_cluster-max.md

## Summary
- BLOCKER: 5
- HIGH: 7
- MEDIUM: 6
- LOW: 2
- Top 3 risks ranked by impact × likelihood
  - `Phase 12` raw mirror leaks `[private]` `decisions.log` content to non-Claude models (`~/.buildrunner/scripts/sync-cluster-context.sh`, lines 1069-1071)
  - `Phase 2` resident-model contract is impossible with `OLLAMA_KEEP_ALIVE=0` (`~/.buildrunner/config/ollama-below.env`, lines 361-365 vs Overview line 10)
  - Wave plan guarantees merge conflicts on shared files (`core/cluster/AGENTS.md`, `~/.buildrunner/scripts/adversarial-review.sh`) in `Wave 3` and `Wave 4` (lines 108-110)

## Findings

### BLOCKER
#### B1. Resident-model contract is impossible under the declared Ollama settings
- **Lens:** Cache-policy holes
- **Phase / file:** Overview, lines 10-10; Phase 2, `~/.buildrunner/config/ollama-below.env`, lines 361-365
- **Failure mode:** The plan promises `llama3.3:70b` and `qwen3:8b` resident simultaneously with “no permanent model swapping,” but `OLLAMA_KEEP_ALIVE=0` unloads models immediately after use, forcing cold reloads and model thrash.
- **Runtime manifestation:** First-token latency spikes, repeated reloads, non-resident models despite successful `ollama list`, and cache/benchmark behavior that never matches the stated steady state.
- **Why current plan misses it:** Phase 2 only verifies env vars exist and models are listed; no gate checks concurrent residency, warm-start latency, or back-to-back calls without unload.

#### B2. Phase 12 leaks `[private]` decisions to Below and Codex through the mirror itself
- **Lens:** Multi-model parity contract weaknesses
- **Phase / file:** Phase 12, `~/.buildrunner/scripts/sync-cluster-context.sh`, lines 1069-1071; Phase 12 constraints, lines 1052-1053
- **Failure mode:** The plan copies raw `~/.buildrunner/decisions.log` to readable mirrors on Otis and Below, while the `[private]` filter is only specified for source extraction. The mirror exposes the full file before filtering.
- **Runtime manifestation:** Non-Claude models can read or be primed from private decision entries, creating an immediate confidentiality breach and parity surface that exceeds the allowed contract.
- **Why current plan misses it:** The review gate checks bundle extraction and file permissions, not mirror contents; the parity test only requires one decision citation, so private-line leakage can ship unnoticed.

#### B3. The parallelization waves guarantee hard merge conflicts on shared files
- **Lens:** Parallelization conflicts
- **Phase / file:** Wave 3/4 plan, lines 108-110; Phase 4, `core/cluster/AGENTS.md`, line 486; Phase 7, `core/cluster/AGENTS.md`, line 694; Phase 5, `~/.buildrunner/scripts/adversarial-review.sh`, line 562 and `core/cluster/AGENTS.md`, line 563; Phase 9, `~/.buildrunner/scripts/adversarial-review.sh`, line 824 and `core/cluster/AGENTS.md`, line 825; Phase 10, `core/cluster/AGENTS.md`, line 895
- **Failure mode:** `Wave 3` runs Phases 4 and 7 in parallel while both edit `core/cluster/AGENTS.md`; `Wave 4` runs Phases 5, 9, and 10 in parallel while all three edit `core/cluster/AGENTS.md`, and Phases 5 and 9 both edit `~/.buildrunner/scripts/adversarial-review.sh`.
- **Runtime manifestation:** Worktrees cannot merge cleanly, AGENTS rules are overwritten or dropped, and the review/arbiter/context integrations stall before cutover.
- **Why current plan misses it:** All review gates are phase-local; nothing validates cross-wave mergeability or reconciles concurrent edits to the same files.

#### B4. The global whitelist rule makes multiple phases impossible to complete as written
- **Lens:** AGENTS.md scope errors
- **Phase / file:** Global guardrail, lines 43-45; Phase 0 files, lines 133-140 and done-when lines 193-194; Phase 1 files, line 211 and done-when lines 319-319; similar `decisions.log` requirements recur in Phases 2-14
- **Failure mode:** The plan says “NEVER touch files outside the per-phase `Files:` whitelist,” but many phases require a `decisions.log` entry even when `decisions.log` is not in the phase whitelist, and Phase 1 has no writable files at all while still requiring a log entry.
- **Runtime manifestation:** The executor either violates the plan’s own guardrail or cannot legally satisfy `Done When`, so phases deadlock on completion criteria.
- **Why current plan misses it:** The phase reviews never target `decisions.log`, so the whitelist violation is structurally invisible to the gates.

#### B5. MS-A2 staging service is unreachable under the firewall the phase itself installs
- **Lens:** Operational/runtime risks
- **Phase / file:** Phase 3, `~/.buildrunner/scripts/ms-a2-bootstrap.sh`, lines 428-429; Phase 3 staging deployment, lines 436-437
- **Failure mode:** Bootstrap opens only ports `8100`, `4500`, and `4400`, but the staging service health check is on `8200`. If the firewall is applied as specified, the service cannot be reached.
- **Runtime manifestation:** `curl http://10.0.1.106:8200/health` fails externally while the service may still appear healthy locally, blocking Phase 3 verification and any staging traffic.
- **Why current plan misses it:** The review gate explicitly checks the wrong open-port set and does not reconcile it against the required `8200` health endpoint.

### HIGH
#### H1. Phase 4 deletes the very Lockwood references needed to keep Lockwood as an overflow worker
- **Lens:** Spec gaps
- **Phase / file:** Phase 4 constraints, lines 493-495; Phase 4 hardcoded-IP rewrite, lines 507-509
- **Failure mode:** The phase says Lockwood must remain active as overflow, but also requires “Lockwood refs → MS-A2” and zero remaining `10.0.1.101` references outside `cluster.json`.
- **Runtime manifestation:** Lockwood remains declared in `cluster.json` yet is no longer reachable by scripts, dispatch, health checks, or warmups that depended on those references.
- **Why current plan misses it:** The gate checks that Lockwood is preserved in config, not that overflow dispatch to Lockwood still functions after the rewrite.

#### H2. Cache-breakpoint rollout requires edits to a file the phase is forbidden to touch
- **Lens:** Cache-policy holes
- **Phase / file:** Phase 8 files, lines 752-759; Phase 8 deliverable, lines 775-776; Phase 7, `core/cluster/gateway_client.py`, lines 691-691
- **Failure mode:** Phase 8 requires wiring cache breakpoints through `gateway_client.py` when `BR3_GATEWAY=on`, but `gateway_client.py` is not in Phase 8’s `Files:` list.
- **Runtime manifestation:** Direct Anthropic path can use the new cache policy while gateway-on traffic stays on the old prompt structure, producing different prompts and lower cache reuse precisely when the flag flips on.
- **Why current plan misses it:** The phase-local file whitelist forbids the required edit, and the integration test is referenced without phase-order protection that guarantees the gateway path is actually updated.

#### H3. Phase 8 can complete without the observability it needs to prove success
- **Lens:** Verification gate weaknesses
- **Phase / file:** Phase 8 blocked-by, lines 743-744; Phase 8 goal, lines 746-748; Phase 8 done-when, lines 793-798; Phase 7 observability goal, lines 681-684 and endpoints lines 712-713
- **Failure mode:** Phase 8 is allowed to proceed without Phase 7, yet its success condition is `>70% cache hit rate`, which depends on the ledger/cache observability Phase 7 introduces.
- **Runtime manifestation:** The phase can be marked done with no trustworthy cache-hit measurement, so cutover proceeds on an unproven cache policy.
- **Why current plan misses it:** No Phase 8 verify command measures cache hits; the success condition is detached from the listed verifications.

#### H4. AGENTS additive-only policy creates a cutover-time contradiction the agent cannot disambiguate
- **Lens:** AGENTS.md scope errors
- **Phase / file:** Global AGENTS rule, lines 57-59; global feature-flag rule, lines 42-42; Phase 13 AGENTS updates, lines 1141-1142
- **Failure mode:** Pre-cutover AGENTS rules say the five flags default OFF until Phase 13. The maintenance rule allows only additive updates. After cutover, the old “default OFF” text remains alongside new “default ON” text.
- **Runtime manifestation:** Agents operating under AGENTS instructions can continue enforcing pre-cutover behavior or produce inconsistent flag handling depending on read order.
- **Why current plan misses it:** Verification is grep-based for presence of cutover text, not semantic consistency of the resulting AGENTS file.

#### H5. The dashboard WebSocket endpoint has no declared owner on port `4500`
- **Lens:** Operational/runtime risks
- **Phase / file:** Phase 7 gateway service, lines 706-708; Phase 11 files, lines 961-969; Phase 11 WebSocket deliverable, lines 987-988
- **Failure mode:** Port `4500` is already the LiteLLM gateway service, but Phase 11 only touches `api/routes/dashboard_stream.py` and no gateway routing/proxy config. Nothing in scope binds or forwards `ws://10.0.1.106:4500/ws`.
- **Runtime manifestation:** Live panels never receive events, or the dashboard connects to the wrong process at `:4500`.
- **Why current plan misses it:** The phase verifies the final socket symptom, but the file scope never includes the service/proxy layer needed to make that route exist.

#### H6. The parity test is materially weaker than the parity claim
- **Lens:** Multi-model parity contract weaknesses
- **Phase / file:** Phase 12 goal, lines 1022-1024; Phase 12 parity test, lines 1075-1076
- **Failure mode:** The goal promises equal access to logs, memory, and research, but the test only requires one `decisions.log` citation and one research citation. A broken log surface or broken memory retrieval still passes.
- **Runtime manifestation:** Codex/Below appear “parity-complete” while missing recent logs, memory tables, or build-history context that Claude still effectively has.
- **Why current plan misses it:** The only explicit parity assertion ignores logs, memory DBs, build history, and equivalence of evidence quality.

#### H7. Phase 14 promises recurring maintenance without any scheduling artifacts in scope
- **Lens:** Operational/runtime risks
- **Phase / file:** Phase 14 files, lines 1180-1185; Phase 14 deliverables, lines 1195-1205
- **Failure mode:** The plan promises checks every 5 minutes, daily cost alerts, and weekly model updates, but only a single `.service` file is listed. No `.timer` units or cron entries are in the phase scope.
- **Runtime manifestation:** Health checks run once or not at the intended cadence; cost alerts and model updates never execute on schedule.
- **Why current plan misses it:** The review gate only checks code behavior and that the service is enabled, not that recurring execution is actually scheduled.

### MEDIUM
#### M1. Phase 0 size-budget verification undercounts AGENTS files
- **Lens:** AGENTS.md scope errors
- **Phase / file:** Phase 0 files, lines 135-140; Phase 0 done-when, lines 189-190
- **Failure mode:** The combined-size check uses `find . -name AGENTS.md`, which excludes `~/.buildrunner/agents-md/ms-a2.md` and `~/.buildrunner/agents-md/otis.md`.
- **Runtime manifestation:** The plan can report total AGENTS size under budget while the staged remote files push the real total over the silent-truncation guardrail.
- **Why current plan misses it:** The automated size command cannot see two of the six required AGENTS artifacts.

#### M2. The NVLink “≥30% speedup” requirement is not actually testable from the listed benchmark
- **Lens:** Untestable success criteria
- **Phase / file:** Phase 2, `~/.buildrunner/scripts/below-benchmark.sh`, lines 367-368
- **Failure mode:** A speedup claim needs a baseline without NVLink or with a single-GPU path, but the plan only specifies one benchmark on the final system.
- **Runtime manifestation:** The benchmark can hit raw tok/s targets yet never establish whether NVLink contributed the required speedup.
- **Why current plan misses it:** The verification only checks absolute tok/s, not comparative speedup.

#### M3. `below-verify.sh` is required to prove a BIOS setting with no defined machine-readable source
- **Lens:** Untestable success criteria
- **Phase / file:** Phase 2, `~/.buildrunner/scripts/below-verify.sh`, lines 359-360; Phase 1 BIOS settings, lines 231-236
- **Failure mode:** The script must validate “Above 4G Decoding,” but the plan never defines an observable command or artifact for that BIOS state.
- **Runtime manifestation:** The script either stubs the check, hardcodes success, or emits false confidence until GPU addressing issues appear later.
- **Why current plan misses it:** Exit-code and `shellcheck` validation only prove the script runs, not that it can determine the BIOS setting.

#### M4. Token budgets are validated with byte counts, not model-token counts
- **Lens:** Per-model budget validation
- **Phase / file:** Phase 10 constraints, lines 900-903 and verify line 912; Phase 12 per-model budgets, lines 1048-1049 and verify line 1062
- **Failure mode:** `wc -c <= 4096` validates bytes, not tokens, and the Phase 12 token ceilings likewise lack a specified tokenizer. Byte-safe payloads can still exceed token budgets badly.
- **Runtime manifestation:** Prompts pass phase verification but later get truncated, rejected, or degrade model quality due to real token overruns.
- **Why current plan misses it:** The gates trust byte counts or self-reported token totals instead of tokenizer-verified counts per target model.

#### M5. The cost-ledger schema has two different contracts in the same phase
- **Lens:** Spec gaps
- **Phase / file:** Phase 7, `core/cluster/cost_ledger.py`, lines 710-711; Phase 7 AGENTS update, lines 716-717
- **Failure mode:** The JSONL schema lists 11 fields, while the AGENTS contract says “10 fields.” Downstream code cannot tell which contract to implement against.
- **Runtime manifestation:** Dashboard and alerting code disagree on the ledger shape and fail when the first real line is parsed.
- **Why current plan misses it:** The review asks whether schema matches contract, but the plan itself contains conflicting contracts.

#### M6. Shadow validation does not exercise the shell-hook and UI paths that are actually cut over
- **Lens:** Verification gate weaknesses
- **Phase / file:** Phase 13 deliverables, lines 1131-1140; Phase 10 hook files, lines 889-897; Phase 11 dashboard files, lines 963-969
- **Failure mode:** `shadow_runner.py` can shadow runtime calls, but it does not cover `below-route.sh`, `codex-bridge.sh`, `auto-context.sh`, dashboard streaming, or port-level integration that Phase 13 flips on.
- **Runtime manifestation:** Shadow divergence looks acceptable for seven days, then `/begin`, context hooks, or dashboard streaming fail immediately after cutover.
- **Why current plan misses it:** The 7-day shadow report measures runtime outputs, not the non-runtime code paths that are also enabled by the flag flip.

### LOW
#### L1. Phase 0 AGENTS artifact count is internally inconsistent
- **Lens:** AGENTS.md scope errors
- **Phase / file:** Phase 0 goal, lines 129-129; Phase 0 files, lines 135-140; Phase 0 done-when, lines 189-189
- **Failure mode:** The goal says one root file plus four scoped sub-AGENTS, the files list contains five scoped subfiles, and the done-when expects six total files.
- **Runtime manifestation:** Review scope and size-budget discussions are easy to misapply because the artifact count changes across the phase text.
- **Why current plan misses it:** No gate reconciles the declared count against the actual file list.

#### L2. Phase 3 names the data-migration script two different ways
- **Lens:** Spec gaps
- **Phase / file:** Parallelization matrix, line 91; Phase 3 files and deliverables, lines 410-410 and 438-439
- **Failure mode:** The matrix calls the file `sync-lockwood-data.sh`, but the phase defines `migrate-lockwood-data.sh`.
- **Runtime manifestation:** Review targets, worktree expectations, or operator handoff can point at the wrong artifact.
- **Why current plan misses it:** The review trigger pattern `ms-a2-*.sh` does not include the migration script name at all, so the mismatch is easy to overlook.

## Contradictions Between Phases
- `Overview` says `llama3.3:70b` and `qwen3:8b` stay resident simultaneously with “no permanent model swapping” (line 10), but `Phase 2` sets `OLLAMA_KEEP_ALIVE=0` in `~/.buildrunner/config/ollama-below.env` (lines 361-365), which guarantees unload/swap behavior.
- `Phase 6` says “NEVER add an Ollama-specific code path outside `ollama_runtime.py`” (line 636), but `Phase 5` introduces `~/.buildrunner/scripts/below-route.sh` as a direct Ollama caller (lines 556, 574-575) and `Phase 12` expands that same script again (lines 1034, 1065-1066).
- `Phase 4` requires Lockwood to remain as an overflow worker (line 493), but the same phase requires “Lockwood refs → MS-A2” and zero remaining `10.0.1.101` references outside `cluster.json` (lines 507-509).
- Global AGENTS maintenance says updates are additive only (line 57), while the global feature-flag rule says all five flags default OFF until `Phase 13` (line 42) and `Phase 13` then appends that all five default ON (lines 1135-1142), leaving contradictory live instructions in the same AGENTS scope.
- `Phase 7` dedicates port `4500` to `br3-gateway.service` (lines 706-707), while `Phase 11` expects a dashboard WebSocket at `ws://10.0.1.106:4500/ws` (lines 987-988) without putting any gateway/proxy change in scope.

## Verdict
- Ship-ready: no
- If no: minimum changes (≤7 bullets)
  - Reconcile the resident-model requirement with the `Phase 2` Ollama environment so the stated serving model is physically possible.
  - Remove the raw mirror path that exposes `[private]` `decisions.log` content to Below and Codex, or the parity surface remains a security breach.
  - Rework the execution waves so no parallel phase co-edits `core/cluster/AGENTS.md` or `~/.buildrunner/scripts/adversarial-review.sh`.
  - Align every phase whitelist with its required artifacts, especially `decisions.log`, or the plan remains impossible to complete under its own guardrails.
  - Resolve the MS-A2 port map inconsistencies around `8200` and `4500/ws` so the declared services are reachable.
  - Make cache/parity/budget success criteria measurable with the dependencies they actually require, not with grep/byte-count proxies.
  - Add explicit scheduling ownership for `Phase 14` recurring maintenance tasks so self-health, cost alerts, and model updates can actually run.
