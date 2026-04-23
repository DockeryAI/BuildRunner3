# Build: below-offload-v1

```yaml
role-matrix:
  inherit: default-role-matrix
  overrides:
    phases:
      phase_1: { bucket: backend-build, assigned_node: muddy }
      phase_2: { bucket: terminal-build, assigned_node: muddy }
      phase_3: { bucket: backend-build, assigned_node: muddy }
```

**Created:** 2026-04-22
**Status:** BUILD COMPLETE — All 3 Phases Done
**Deploy:** web — `npm run build && netlify deploy --prod`
**Source Plan File:** .buildrunner/plans/spec-draft-plan.md
**Source Plan SHA:** ab42cfd26b6e84d08ac522e0ab85bb1a2ae7d4810a7109e436ff183f6fcb344a
**Adversarial Review Verdict:** BYPASSED:.buildrunner/bypass-justification.md
**Adversarial Review Timestamp:** 2026-04-23T00:39:30Z

## Overview

Move proven small-model work off Claude/Codex APIs and onto Below (RTX 3090 ×2, qwen3:8b + llama3.3:70b at http://10.0.1.105:11434). Convert nightly intel cron to user-triggered ad-hoc. Insert a Below pre-filter so Opus only synthesizes intel items above a score threshold. Preserve the existing intel_scoring.py 30-min cron contract used in production.

**Firewall (unchanged):** Below pre-filters / summarizes / scores / classifies. Final diagnoses, code, plans, architecture stay on Claude.

## Parallelization Matrix

| Phase | Key Files                                                                                                                  | Can Parallel With | Blocked By                                           |
| ----- | -------------------------------------------------------------------------------------------------------------------------- | ----------------- | ---------------------------------------------------- |
| 1     | runtime-env.sh (NEW), .zshrc (MODIFY), below-route.sh (MODIFY), classifier-haiku.py (MODIFY), stop-when.sh (MODIFY)        | 2                 | None                                                 |
| 2     | crontab (MODIFY), backups/crontab-\*.txt (NEW), intel-run.sh (NEW), intel-run.md (NEW), decisions.log (APPEND)             | 1                 | None                                                 |
| 3     | intel_scoring.py (MODIFY), intel_prefilter.py (NEW), collect-intel.sh (MODIFY), intel-run.sh (MODIFY — `--skip-prefilter`) | None              | Phase 2 (operational: don't rewire while cron lives) |

Recommended execution: Phase 1 ∥ Phase 2, then Phase 3.

## Phases

### Phase 1: Routing Flag Durability + Haiku Swaps

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/runtime-env.sh` (NEW)
- `~/.zshrc` (MODIFY)
- `~/.buildrunner/scripts/below-route.sh` (MODIFY)
- `~/.buildrunner/scripts/lib/classifier-haiku.py` (MODIFY)
- `~/.buildrunner/scripts/stop-when.sh` (MODIFY)
- `~/.bash_profile` (NEW — scope expansion to satisfy DELIV 6 bash-lc durability)

**Blocked by:** None
**Goal:** `BR3_LOCAL_ROUTING=on` durable across interactive AND noninteractive shells. classifier-haiku.py and stop-when.sh both call qwen3:8b on Below via `/api/chat` instead of Anthropic Haiku. Bounded timeouts on every Below call.

**Deliverables:**

- [x] `~/.buildrunner/runtime-env.sh` exists. Exports `BR3_LOCAL_ROUTING=on`, `BELOW_OLLAMA_URL=http://10.0.1.105:11434`, `BELOW_MODEL_FAST=qwen3:8b`, `BELOW_MODEL_HEAVY=llama3.3:70b`. Sets `BR3_RUNTIME_ENV_LOADED=1` sentinel.
- [x] `~/.zshrc` sources runtime-env.sh idempotently (sentinel-guarded).
- [x] `~/.buildrunner/scripts/below-route.sh` sources runtime-env.sh at top, BEFORE the existing flag check at line 41.
- [x] `classifier-haiku.py` no longer references `anthropic.com`, `claude-haiku`, or `ANTHROPIC_API_KEY`. Calls `${BELOW_OLLAMA_URL}/api/chat` with `qwen3:8b`, `format=json`, `options={num_predict:50, temperature:0}`. Reuses existing `BR3_CLASSIFIER_HAIKU_TIMEOUT_MS` (default 3000ms). safe_default behavior unchanged.
- [x] `stop-when.sh` no longer references `claude-haiku` or invokes `claude` CLI for Haiku call. Calls Below via curl with `BR3_STOPWHEN_BELOW_TIMEOUT_S` (default 30s) + connect timeout `BR3_STOPWHEN_BELOW_CONNECT_TIMEOUT_S` (default 5s). INCONCLUSIVE fallback path intact.
- [x] `bash -lc 'env | grep BR3_LOCAL_ROUTING'` shows `=on`.
- [x] `env -i HOME=$HOME PATH=/usr/bin:/bin ~/.buildrunner/scripts/below-route.sh --help` exits 0 (proves below-route.sh self-sources runtime-env even with stripped env).

**Success Criteria:**

- All 7 deliverables checked.
- Sample classifier prompt returns valid bucket from qwen3:8b (or backend-build fallback if Below down).
- Sample stop-when condition returns MET / NOT_MET / INCONCLUSIVE from qwen3:8b (or INCONCLUSIVE if Below down).
- `grep -nE 'anthropic\.com|claude-haiku|ANTHROPIC_API_KEY' ~/.buildrunner/scripts/lib/classifier-haiku.py ~/.buildrunner/scripts/stop-when.sh` returns empty.

### Phase 2: Intel Cron OFF + Ad-Hoc Trigger

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/backups/crontab-<timestamp>.txt` (NEW — pre-edit backup)
- User crontab (MODIFY — remove only the `collect-intel.sh` line)
- `~/.buildrunner/scripts/intel-run.sh` (NEW)
- `~/.claude/commands/intel-run.md` (NEW)
- `.buildrunner/decisions.log` (APPEND)

**Blocked by:** None
**After:** Phase 1 (logical preference, but technically parallelizable — disjoint files)
**Goal:** Nightly cron removed safely (with backup). User triggers intel collection via `/intel-run` command. `--smoke` and `--dry-run` flags supported.

**Deliverables:**

- [x] Pre-edit backup at `~/.buildrunner/backups/crontab-<timestamp>.txt` (non-empty).
- [x] `crontab -l 2>/dev/null | grep -c collect-intel` returns 0.
- [x] All other pre-existing crontab entries preserved (verify via diff against backup).
- [x] `~/.buildrunner/scripts/intel-run.sh` exists, executable. Sources runtime-env.sh. Supports `--dry-run`, `--smoke`, `--phase=N` flags.
- [x] Script preamble prints concrete estimate: "Intel run starting (phases: 1-4). Estimated duration: 8–15 minutes. Estimated Claude API cost: ~120 turns across 4 agentic sessions."
- [x] `intel-run.sh --smoke` pings `http://10.0.1.106:8101/api/intel/items` (Lockwood) and `http://10.0.1.105:11434/api/tags` (Below). Prints PASS/FAIL per check. Exits 0 only if both pass.
- [x] `~/.claude/commands/intel-run.md` exists. `/intel-run` invokes the script.
- [x] `.buildrunner/decisions.log` contains entry: `[2026-04-22] Intel collection moved from nightly cron (3 4 * * *) to ad-hoc /intel-run per user request — scope/cost control. Backup: <path>.`

**Success Criteria:**

- All 8 deliverables checked.
- `/intel-run --smoke` returns exit 0 with PASS for both Lockwood and Below pings.
- `/intel-run --dry-run` runs Phases 1–2 of collect-intel.sh only and exits cleanly.

### Phase 3: Below Pre-Filter for Intel Synthesis (fail-open)

**Status:** ✅ COMPLETE
**Files:**

- `core/cluster/intel_scoring.py` (MODIFY — minimal additive edit only)
- `core/cluster/scripts/intel_prefilter.py` (NEW)
- `core/cluster/scripts/__init__.py` (NEW — required for `python3 -m core.cluster.scripts.intel_prefilter`)
- `core/cluster/scripts/collect-intel.sh` (MODIFY — includes Phase 2.5, Phase 3 filter, and arg parsing scaffold so `--dry-run` / `--phase=N` / `--skip-prefilter` from `intel-run.sh` take effect end-to-end)
- `~/.buildrunner/scripts/intel-run.sh` (MODIFY — `--skip-prefilter` already scaffolded in Phase 2; confirmed)

**Blocked by:** Phase 2 (operational: don't rewire collect-intel.sh while cron may still fire)
**Goal:** Insert Below qwen3:8b scoring pass between collect-intel.sh's collection (Phases 1–2) and synthesis (Phase 3). Fail-open semantics: Below offline flags items as `needs_opus_review = 1` instead of breaking. Phase 3 prompt filters to items above threshold, or override priorities, or flagged, or unscored.

**Deliverables:**

- [x] `intel_scoring.py` `score_intel_items()` no longer breaks on Below offline. Per-item `_flag_needs_opus_review(item_id, "intel")` is called when `_call_below_chat` returns None, then loop continues. Malformed-response branch unchanged.
- [x] Diff to `intel_scoring.py` is additive only (no signature changes, no removed functions). `git diff intel_scoring.py` shows changes only inside `score_intel_items()` body.
- [x] `core/cluster/scripts/intel_prefilter.py` exists. Importable. Runs `asyncio.run(score_intel_items())`. Logs result to `~/.buildrunner/logs/intel-prefilter-<timestamp>.log`. Exits 0 even if some items can't be scored (fail-open).
- [x] `collect-intel.sh` Phase 2.5 invokes `python3 -m core.cluster.scripts.intel_prefilter` between Phase 2 (line ~48) and Phase 3 (line ~51). Stdout appended to LOG_FILE.
- [x] `collect-intel.sh` Phase 3 prompt filters on `(item.score or 0) >= MIN_SCORE OR item.priority IN PRIORITY_OVERRIDE OR item.needs_opus_review == 1 OR item.scored == 0`.
- [x] Defaults documented inline: `BR3_INTEL_MIN_SCORE=6`, `BR3_INTEL_PRIORITY_OVERRIDE=critical,high`.
- [x] `intel-run.sh --skip-prefilter` bypasses Phase 2.5 (escape hatch; honored via `BR3_SKIP_PREFILTER=1` export or the `--skip-prefilter` arg parsed in `collect-intel.sh`).
- [x] Smoke test passes: synthetic items with scores [3, 8] and priorities [low, critical] and flags [0, 1] route correctly per filter rule.

**Success Criteria:**

- All 8 deliverables checked.
- The existing 30-minute scoring cron (`start_scoring_cron` thread) imports cleanly and runs without regression: `python3 -c "from core.cluster.intel_scoring import score_intel_items, start_scoring_cron, _parse_intel_score, _flag_needs_opus_review; print('PASS')"` exits 0.
- A live `/intel-run --dry-run` shows Phase 2.5 output with item-kept-vs-filtered counts.
- Public signature of `score_intel_items` unchanged: `() -> dict`.

## Session Log

[Will be updated by /begin]
