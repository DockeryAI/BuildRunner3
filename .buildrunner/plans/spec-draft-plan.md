# Draft Plan: below-offload-v1 (REWRITE — addresses adversarial blockers)

**Created:** 2026-04-22
**Author:** Claude (audit + adversarial-review-corrected)
**Source:** Below offload audit + adversarial review of v1 draft

## Purpose

Move proven small-model work off Claude/Codex APIs and onto Below (RTX 3090 ×2, 64 GB RAM, qwen3:8b + llama3.3:70b live at http://10.0.1.105:11434). Convert nightly intel cron to user-triggered ad-hoc. Insert a Below pre-filter so Opus only synthesizes intel items above a score threshold. Preserve the existing intel_scoring.py 30-min cron contract used in production.

**Firewall (unchanged):** Below pre-filters / summarizes / scores / classifies. Final diagnoses, code, plans, architecture stay on Claude.

## Ground-Truth File Inventory (verified by Read)

- `~/.buildrunner/scripts/lib/classifier-haiku.py` — exists, uses `call_anthropic()` (line 107), already has `BR3_CLASSIFIER_HAIKU_TIMEOUT_MS` env-driven timeout (default 3000ms), already has mock-response support, falls back to `safe_default("backend-build")` on any error
- `~/.buildrunner/scripts/stop-when.sh` — exists, uses `claude -p ... --model claude-haiku-4-5-20251001` (line 63), 40k char context cap, INCONCLUSIVE fallback already in place
- `~/.buildrunner/scripts/below-route.sh` — uses `runtime-dispatch.sh` (not direct Ollama), gates on `BR3_LOCAL_ROUTING=on` (line 41), exits 2 when off
- `~/.buildrunner/scripts/classify-prompt.sh` — calls classifier-haiku.py at line 78, falls back to "backend-build" if helper missing or exits non-zero
- `core/cluster/intel_scoring.py` — has async `_call_below_chat()` (line 50, uses `/api/chat`), `_build_intel_prompt()` (line 117), `_parse_intel_score()` (line 144) returning `{score, priority, category, summary}` where `score = round((relevance + urgency + actionability) / 3)` clamped 1–10. Public batch entry point: `score_intel_items()` (line 359, async, reads `scored = 0` from DB and scores via Below). On Below offline: `break`s out of the loop with `stats["errors"] += 1` — items stay `scored = 0`. Has `_flag_needs_opus_review(item_id, "intel")` for malformed responses
- `core/cluster/scripts/collect-intel.sh` — 4 `claude -p` phases. Phase 3 (line 53) is the high-token spend: reads ALL unreviewed items via `:8101/api/intel/items`, writes opus_synthesis + br3_improvement for each
- `crontab` — `3 4 * * * /Users/byronhudson/Projects/BuildRunner3/core/cluster/scripts/collect-intel.sh`
- Below `/api/tags` confirms: qwen3:8b, llama3.3:70b, qwen2.5:14b, deepseek-r1:70b, nomic-embed-text loaded
- Lockwood intel API at `http://10.0.1.106:8101/api/intel/items` — handles intel item CRUD

## Adversarial Review Disposition

The 2026-04-22 23:16 review produced 7 blockers, 14 warnings, 7 notes (verdict BLOCK from open arbiter circuit). All addressed below:

| Blocker                                                           | Resolution                                                                                                                                                                                                    |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `score_intel_item` (singular) doesn't exist                       | Phase 3 calls existing batch `score_intel_items()` synchronously instead. No new public API needed.                                                                                                           |
| Phase 3 needs per-item bash invocation; intel_scoring is batch DB | Phase 3 invokes `python3 -m core.cluster.scripts.intel_prefilter` (NEW thin wrapper that runs `score_intel_items()` once). Bash never calls per-item.                                                         |
| `classifier-haiku.py` not in project tree                         | False positive — file IS at `~/.buildrunner/scripts/lib/classifier-haiku.py` (global, not per-project). Plan path is correct.                                                                                 |
| Phase 1 modifies missing classifier file                          | Same false positive — file exists.                                                                                                                                                                            |
| Phase 3 verify command imports nonexistent function               | Verify command rewritten to import `score_intel_items` (plural, existing) and call it via asyncio.                                                                                                            |
| Routing flag not durable for noninteractive shells                | New: `~/.buildrunner/scripts/below-route.sh` sources `~/.buildrunner/runtime-env.sh` at top BEFORE the flag check. Same source line added to all new entrypoint scripts.                                      |
| Below scoring `break`s on offline (not fail-open)                 | Phase 3 includes minimal edit to `score_intel_items()`: on Below offline, flag remaining unscored items with `needs_opus_review = 1` and CONTINUE (no break). Improves the existing 30-min cron behavior too. |

| Warning                                                         | Resolution                                                                                                                                                                           |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `priority >= medium` is ambiguous                               | Replaced with explicit set membership: `priority IN ('critical', 'high')` as override regardless of score.                                                                           |
| `relevance >= 7` doesn't exist in scoring output                | Replaced with `score >= 6` (composite score 1–10 returned by `_parse_intel_score`). Default 6 = mid-range. Env var: `BR3_INTEL_MIN_SCORE`.                                           |
| Phase 3 verify uses `--smoke` flag never required in Phase 2    | Phase 2 deliverables now explicitly require `--smoke` and `--dry-run` flags on intel-run.sh.                                                                                         |
| Intel-run.sh "same env as cron" too vague                       | Replaced with explicit env list: sources runtime-env.sh, exports BELOW_OLLAMA_URL, sets PATH explicitly, no other env required.                                                      |
| collect-intel.sh per-item invocation deferred                   | Resolved upfront: Phase 3 inserts a single Python wrapper invocation between Phase 2 and Phase 3 of collect-intel.sh. No per-item bash logic.                                        |
| Below offline → all items flagged → routes to Opus = no savings | Acknowledged trade-off. When Below is offline, fail-open is correct (Opus reviews everything). Documented as intended behavior. Telemetry tracks Below uptime.                       |
| stop-when.sh INCONCLUSIVE forever stalls loops                  | Already-existing INCONCLUSIVE behavior; callers already handle. Phase 1 doesn't change that contract; only the underlying model call changes.                                        |
| classifier uses `/api/generate` while intel uses `/api/chat`    | Standardized: classifier and stop-when both use `/api/chat` (matches intel_scoring.py, simpler payload).                                                                             |
| Crontab backup promised but no deliverable                      | Added explicit deliverable: `crontab -l > ~/.buildrunner/backups/crontab-$(date +%Y%m%d-%H%M%S).txt` BEFORE any edit.                                                                |
| `~N` placeholder in preamble                                    | Preamble now uses concrete estimate: "8–15 minutes, ~120 Claude turns".                                                                                                              |
| BR3*INTEL_MIN*\* defaults not stated                            | Defaults declared: `BR3_INTEL_MIN_SCORE=6`, `BR3_INTEL_PRIORITY_OVERRIDE=critical,high`.                                                                                             |
| `--dry-run` support assumed                                     | Added to Phase 2 deliverables.                                                                                                                                                       |
| Phase 1 below-route.sh subcommand `log-summary` not grounded    | Verification rewritten to use the actual contract: `BR3_LOCAL_ROUTING=on below-route.sh --model qwen3:8b "test prompt"` exits 0.                                                     |
| No timeout budget for Below calls in classifier/stop-when       | Both swaps use explicit timeouts: classifier reuses `BR3_CLASSIFIER_HAIKU_TIMEOUT_MS` (default 3000ms); stop-when uses new `BR3_STOPWHEN_BELOW_TIMEOUT_S` (default 30s, connect 5s). |
| Phase 2 marked parallel with Phase 1 but needs Phase 1 env      | Phase 2's intel-run.sh sources runtime-env.sh independently. No execution-order dep on Phase 1. Both can parallel.                                                                   |

| Note                                           | Resolution                                                                                                                                       |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `launchctl list` won't show Python-thread cron | Verification rewritten to assert via Python: `python3 -c "from core.cluster.intel_scoring import _scoring_cron_loop; print('ok')"` (importable). |
| Plan misstated dedup model as nomic-embed      | Corrected: dedup uses `BELOW_MODEL` env var (default qwen3:8b) via `/api/embed`. nomic-embed-text is loaded but not the default for embed calls. |
| home-dir artifacts not "in tree"               | Acknowledged — global scripts live in `~/.buildrunner/`, not the project. All paths verified by Read in this session.                            |

---

## Out of Scope (Future)

- Replacing Phases 1–2 / Phase 4 of collect-intel.sh (web access + auto-act stay on Claude — firewall).
- Replacing the Opus arbiter in adversarial review (firewall).
- Pre-filtering intel via embeddings dedup (already exists in scoring path; not changed here).
- Migrating /diag /dbg /sdb /root /begin /autopilot /review /guard skills off Claude — these auto-unlock the moment Phase 1's routing flag flips. Verifying each is its own follow-up build.

---

### Phase 1: Routing Flag Durability + Haiku Swaps

**Goal:** `BR3_LOCAL_ROUTING=on` is durable across interactive AND noninteractive shells. classifier-haiku.py and stop-when.sh both call qwen3:8b on Below via `/api/chat` instead of Anthropic Haiku. All four flag-gated below-route paths return success.

**Files:**

- `~/.buildrunner/runtime-env.sh` (NEW) — single source of truth for BR3 runtime env vars (BR3_LOCAL_ROUTING, BELOW_OLLAMA_URL, BELOW_MODEL_FAST, BELOW_MODEL_HEAVY)
- `~/.zshrc` (MODIFY) — idempotent `[ -f ~/.buildrunner/runtime-env.sh ] && . ~/.buildrunner/runtime-env.sh` line; guarded against double-include with sentinel `BR3_RUNTIME_ENV_LOADED`
- `~/.buildrunner/scripts/below-route.sh` (MODIFY) — add same source line at line 32 (BEFORE the flag check at line 37); makes flag durable for any noninteractive caller (cron, dispatch, agents)
- `~/.buildrunner/scripts/lib/classifier-haiku.py` (MODIFY) — replace `call_anthropic()` body with `call_below_chat()`: POST to `${BELOW_OLLAMA_URL}/api/chat` with model qwen3:8b, format=json, stream=false, options={num_predict:50, temperature:0}. Reuse existing `BR3_CLASSIFIER_HAIKU_TIMEOUT_MS` (default 3000ms) for `urllib.request.urlopen` timeout. Output contract unchanged: stdout = single bucket name. Mock support unchanged. safe_default behavior unchanged ("backend-build" on any error).
- `~/.buildrunner/scripts/stop-when.sh` (MODIFY) — replace the `claude -p ... --model claude-haiku-4-5-20251001` line (~63) with curl POST to `${BELOW_OLLAMA_URL}/api/chat`, model qwen3:8b, format=json. New env vars: `BR3_STOPWHEN_BELOW_TIMEOUT_S` (default 30s), `BR3_STOPWHEN_BELOW_CONNECT_TIMEOUT_S` (default 5s). Output parsing unchanged. INCONCLUSIVE fallback unchanged.

**Blocked by:** None.

**Deliverables:**

- [ ] `~/.buildrunner/runtime-env.sh` exists, exports `BR3_LOCAL_ROUTING=on`, `BELOW_OLLAMA_URL=http://10.0.1.105:11434`, `BELOW_MODEL_FAST=qwen3:8b`, `BELOW_MODEL_HEAVY=llama3.3:70b`. Sets `BR3_RUNTIME_ENV_LOADED=1` sentinel.
- [ ] `~/.zshrc` sources runtime-env.sh idempotently (sentinel-guarded — sourcing twice is a no-op).
- [ ] `~/.buildrunner/scripts/below-route.sh` sources runtime-env.sh at top (line ~32), BEFORE the existing flag check.
- [ ] `classifier-haiku.py` no longer references `anthropic.com`, `claude-haiku`, or `ANTHROPIC_API_KEY`. Calls `${BELOW_OLLAMA_URL}/api/chat` with qwen3:8b, format=json. Timeout from existing env var. safe_default fallback unchanged.
- [ ] `stop-when.sh` no longer references `claude-haiku` or `claude` CLI for the Haiku call. Calls Below via curl with bounded timeouts. INCONCLUSIVE fallback path intact.
- [ ] `bash -lc 'env | grep BR3_LOCAL_ROUTING'` shows `=on` after Phase 1 completes (proves shell sourcing works).
- [ ] `env -i HOME=$HOME PATH=$PATH ~/.buildrunner/scripts/below-route.sh --help' exits 0 (proves below-route.sh self-sources runtime-env even with stripped env).

**Success Criteria:**

- All 7 deliverables checked.
- Sample classifier prompt returns a valid bucket from qwen3:8b (or backend-build fallback if Below is down).
- Sample stop-when condition returns MET / NOT_MET / INCONCLUSIVE from qwen3:8b (or INCONCLUSIVE if Below is down).

**Verification Commands:**

```bash
# Env durability — interactive AND noninteractive
bash -lc 'env | grep BR3_LOCAL_ROUTING' | grep -q '=on' && echo PASS || echo FAIL
env -i HOME=$HOME PATH=/usr/bin:/bin bash -c '. ~/.buildrunner/runtime-env.sh && env | grep BR3_LOCAL_ROUTING' | grep -q '=on' && echo PASS || echo FAIL

# Below-route flag check now passes from stripped env
env -i HOME=$HOME PATH=/usr/bin:/bin ~/.buildrunner/scripts/below-route.sh --help >/dev/null 2>&1 && echo PASS || echo FAIL

# Classifier — no Anthropic deps remaining
grep -nE 'anthropic\.com|claude-haiku|ANTHROPIC_API_KEY' ~/.buildrunner/scripts/lib/classifier-haiku.py && echo FAIL || echo PASS

# Classifier returns a valid bucket via Below
echo "fix typo in button label" | python3 ~/.buildrunner/scripts/lib/classifier-haiku.py | grep -E '^(planning|architecture|backend-build|terminal-build|ui-build|review|classification|retrieval|qa)$' && echo PASS || echo FAIL

# Stop-when — no Haiku deps
grep -nE 'claude-haiku|--model claude' ~/.buildrunner/scripts/stop-when.sh && echo FAIL || echo PASS

# Stop-when returns MET/NOT_MET/INCONCLUSIVE
TMP_CTX=$(mktemp); echo "All tests passing" > "$TMP_CTX"
~/.buildrunner/scripts/stop-when.sh "tests are passing" "$TMP_CTX" | grep -E '^(MET|NOT_MET|INCONCLUSIVE)$' && echo PASS || echo FAIL
rm -f "$TMP_CTX"
```

**Can parallelize within phase:** Yes — runtime-env, classifier, stop-when, and below-route source-line edit touch disjoint files.
**Can parallelize with Phase 2:** Yes — disjoint files.

---

### Phase 2: Intel Cron OFF + Ad-Hoc Trigger

**Goal:** Nightly `3 4 * * *` collect-intel cron removed (with backup). New `~/.buildrunner/scripts/intel-run.sh` and `/intel-run` slash command let the user trigger collection manually. `--dry-run` and `--smoke` flags supported for verification.

**Files:**

- `~/.buildrunner/backups/crontab-<timestamp>.txt` (NEW — backup before edit)
- User crontab (MODIFY — remove only the `collect-intel.sh` line; preserve all others)
- `~/.buildrunner/scripts/intel-run.sh` (NEW) — manual trigger; sources runtime-env.sh; supports `--dry-run` (don't run Phases 3–4) and `--smoke` (run only Phase 0, a 30-second self-test that pings Lockwood + Below and exits)
- `~/.claude/commands/intel-run.md` (NEW) — slash command shell; invokes `~/.buildrunner/scripts/intel-run.sh "$@"`
- `.buildrunner/decisions.log` (APPEND) — record schedule change with rationale

**Blocked by:** None.

**Deliverables:**

- [ ] Pre-edit backup exists at `~/.buildrunner/backups/crontab-<timestamp>.txt`
- [ ] `crontab -l 2>/dev/null | grep -c collect-intel` returns 0
- [ ] All other pre-existing crontab entries are preserved (verify by diff against backup)
- [ ] `~/.buildrunner/scripts/intel-run.sh` exists, executable (chmod +x), sources runtime-env.sh, supports `--dry-run`, `--smoke`, `--phase=N` flags
- [ ] Script preamble prints concrete estimate: "Intel run starting (phases: 1-4). Estimated duration: 8–15 minutes. Estimated Claude API cost: ~120 turns across 4 agentic sessions."
- [ ] `intel-run.sh --smoke` pings `http://10.0.1.106:8101/api/intel/items` and `http://10.0.1.105:11434/api/tags`, prints "PASS" or "FAIL" per check, exits 0 only if both pass
- [ ] `~/.claude/commands/intel-run.md` exists; `/intel-run` invokes the script
- [ ] `.buildrunner/decisions.log` contains line: `[2026-04-22] Intel collection moved from nightly cron (3 4 * * *) to ad-hoc /intel-run per user request — scope/cost control. Backup: <path>.`

**Success Criteria:**

- All 8 deliverables checked.
- `/intel-run --smoke` returns exit 0 with PASS for both Lockwood and Below pings.
- `/intel-run --dry-run` runs Phase 1–2 only and exits cleanly.

**Verification Commands:**

```bash
crontab -l 2>/dev/null | grep -c collect-intel | grep -q '^0$' && echo PASS || echo FAIL
ls ~/.buildrunner/backups/crontab-*.txt 2>/dev/null | head -1 | xargs -I{} test -s {} && echo PASS || echo FAIL
test -x ~/.buildrunner/scripts/intel-run.sh && echo PASS || echo FAIL
test -f ~/.claude/commands/intel-run.md && echo PASS || echo FAIL
~/.buildrunner/scripts/intel-run.sh --smoke 2>&1 | tail -5
grep -c "Intel collection moved from nightly cron" .buildrunner/decisions.log | awk '$1>=1{print "PASS"} $1<1{print "FAIL"}'
```

**Can parallelize with Phase 1:** Yes — disjoint files.
**Blocks Phase 3:** Yes — Phase 3 modifies collect-intel.sh and we don't want cron firing during edit.

---

### Phase 3: Below Pre-Filter for Intel Synthesis (fail-open)

**Goal:** Insert a Below qwen3:8b scoring pass between collect-intel.sh's collection (Phases 1–2) and synthesis (Phase 3). Modify `intel_scoring.py` minimally so Below offline flags items as `needs_opus_review = 1` instead of breaking the loop. Modify collect-intel.sh's Phase 3 prompt to filter to items with `score >= BR3_INTEL_MIN_SCORE` OR `priority IN ('critical','high')` OR `needs_opus_review = 1` OR `scored = 0`.

**Files:**

- `core/cluster/intel_scoring.py` (MODIFY — minimal additive edit) — in `score_intel_items()`, replace the `break` on Below offline with: flag the current item with `needs_opus_review = 1`, log warning, `continue`. The 30-min cron benefits too (today: items sit unscored forever; after: they get flagged and Opus eventually picks them up).
- `core/cluster/scripts/intel_prefilter.py` (NEW) — thin wrapper. Imports `score_intel_items` from `core.cluster.intel_scoring` and runs `asyncio.run(score_intel_items())`. Logs result to `~/.buildrunner/logs/intel-prefilter-<timestamp>.log`. Exits 0 even if some items can't be scored (those are flagged, fail-open).
- `core/cluster/scripts/collect-intel.sh` (MODIFY) — insert "Phase 2.5: Below pre-filter" between Phase 2 and Phase 3 (~line 49–50). New step runs `python3 -m core.cluster.scripts.intel_prefilter`. Modify Phase 3's claude prompt (line 53–71): change `[print(...) for i in items if not i.get(\"opus_reviewed\")]` to filter on `(item.get('score') or 0) >= MIN_SCORE OR item.get('priority') in PRIORITY_OVERRIDE OR item.get('needs_opus_review') == 1 OR item.get('scored') == 0`. MIN_SCORE and PRIORITY_OVERRIDE read from env with documented defaults.
- `~/.buildrunner/scripts/intel-run.sh` (MODIFY — small follow-up from Phase 2) — add `--skip-prefilter` flag that bypasses Phase 2.5 (escape hatch).

**Blocked by:** Phase 2 (must run after cron is disabled — operational safety).

**Deliverables:**

- [ ] `intel_scoring.py` `score_intel_items()` no longer breaks on Below offline. Per-item `_flag_needs_opus_review(item_id, "intel")` is called when `_call_below_chat` returns None, then loop continues. The malformed-response branch (already calls \_flag_needs_opus_review) unchanged.
- [ ] Diff to `intel_scoring.py` is additive only (no signature changes, no removed functions). `git diff intel_scoring.py` shows only changes inside the body of `score_intel_items()`.
- [ ] `core/cluster/scripts/intel_prefilter.py` exists. Importable. Runs end-to-end against the live DB.
- [ ] `collect-intel.sh` Phase 2.5 invokes `intel_prefilter` between Phase 2 (line 48) and Phase 3 (line 51). Logs to LOG_FILE.
- [ ] `collect-intel.sh` Phase 3 prompt filters on `score >= BR3_INTEL_MIN_SCORE` (default 6) OR `priority IN ('critical','high')` OR `needs_opus_review = 1` OR `scored = 0`.
- [ ] Defaults documented inline in collect-intel.sh: `BR3_INTEL_MIN_SCORE=6`, `BR3_INTEL_PRIORITY_OVERRIDE=critical,high`.
- [ ] `intel-run.sh --skip-prefilter` bypasses Phase 2.5.
- [ ] Smoke test: with a synthetic intel item where Below scores it score=3, the Phase 3 filter excludes it. With score=8, included. With needs_opus_review=1, included. With scored=0, included.

**Success Criteria:**

- All 8 deliverables checked.
- The existing 30-minute scoring cron (`start_scoring_cron` thread) imports cleanly and runs without regression: `python3 -c "from core.cluster.intel_scoring import score_intel_items, start_scoring_cron, _parse_intel_score; print('contract preserved')"` exits 0.
- A live `/intel-run --dry-run` (which now runs Phases 1, 2, 2.5 only) shows Phase 2.5 output with item-kept-vs-filtered counts.

**Verification Commands:**

```bash
# Contract preserved — all public symbols importable
python3 -c "from core.cluster.intel_scoring import score_intel_items, start_scoring_cron, _parse_intel_score, _flag_needs_opus_review; print('PASS')" || echo FAIL

# Diff is additive — score_intel_items still exists with same signature
python3 -c "import inspect; from core.cluster.intel_scoring import score_intel_items; sig=inspect.signature(score_intel_items); print('PASS' if str(sig)=='() -> dict' else f'FAIL sig={sig}')"

# intel_prefilter wrapper exists and is callable
python3 -m core.cluster.scripts.intel_prefilter --help 2>&1 | head -3

# collect-intel.sh has Phase 2.5
grep -c "Phase 2.5\|intel_prefilter" /Users/byronhudson/Projects/BuildRunner3/core/cluster/scripts/collect-intel.sh | awk '$1>=2{print "PASS"} $1<2{print "FAIL"}'

# Phase 3 prompt filters on score, not on opus_reviewed alone
grep -E "score.*MIN_SCORE|BR3_INTEL_MIN_SCORE|needs_opus_review" /Users/byronhudson/Projects/BuildRunner3/core/cluster/scripts/collect-intel.sh | head -5

# 30-min cron thread still importable + startable (no live thread side-effect — just attribute check)
python3 -c "from core.cluster.intel_scoring import start_scoring_cron; print('PASS' if callable(start_scoring_cron) else 'FAIL')"

# Smoke: synthetic items in/out
python3 -c "
import os
os.environ['BR3_INTEL_MIN_SCORE'] = '6'
items = [
    {'id': 1, 'score': 3, 'priority': 'low',     'scored': 1, 'needs_opus_review': 0},  # filtered
    {'id': 2, 'score': 8, 'priority': 'low',     'scored': 1, 'needs_opus_review': 0},  # kept
    {'id': 3, 'score': 2, 'priority': 'critical','scored': 1, 'needs_opus_review': 0},  # kept (priority override)
    {'id': 4, 'score': 1, 'priority': 'low',     'scored': 1, 'needs_opus_review': 1},  # kept (flagged)
    {'id': 5, 'score': None, 'priority': None,   'scored': 0, 'needs_opus_review': 0},  # kept (unscored)
]
MIN = int(os.environ['BR3_INTEL_MIN_SCORE'])
OVR = set(os.environ.get('BR3_INTEL_PRIORITY_OVERRIDE', 'critical,high').split(','))
kept = [i for i in items if (i.get('score') or 0) >= MIN or i.get('priority') in OVR or i.get('needs_opus_review') == 1 or i.get('scored') == 0]
assert [i['id'] for i in kept] == [2,3,4,5], f'FAIL kept={[i[\"id\"] for i in kept]}'
print('PASS')
"
```

**Can parallelize:** No — must follow Phase 2.

---

## Parallelization Matrix

| Phase | Key Files                                                                                                                  | Can Parallel With | Blocked By                                           |
| ----- | -------------------------------------------------------------------------------------------------------------------------- | ----------------- | ---------------------------------------------------- |
| 1     | runtime-env.sh (NEW), .zshrc (MODIFY), below-route.sh (MODIFY), classifier-haiku.py (MODIFY), stop-when.sh (MODIFY)        | 2                 | None                                                 |
| 2     | crontab (MODIFY), backups/crontab-\*.txt (NEW), intel-run.sh (NEW), intel-run.md (NEW), decisions.log (APPEND)             | 1                 | None                                                 |
| 3     | intel_scoring.py (MODIFY), intel_prefilter.py (NEW), collect-intel.sh (MODIFY), intel-run.sh (MODIFY — `--skip-prefilter`) | None              | Phase 2 (operational: don't rewire while cron lives) |

Recommended execution: Phase 1 ∥ Phase 2, then Phase 3.

---

## Risks & Mitigations

| Risk                                                                                                                      | Mitigation                                                                                                                                                                  |
| ------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Below offline → classifier returns "backend-build" for everything                                                         | Existing safe_default behavior; same as today's failure mode when Anthropic API is down. Telemetry on classifier output distribution catches degradation.                   |
| Below offline → stop-when returns INCONCLUSIVE forever                                                                    | Caller behavior unchanged from today (existing INCONCLUSIVE path). Documented in stop-when.sh inline comments.                                                              |
| Below offline during intel pre-filter → all items flagged needs_opus_review → Opus reviews everything anyway → no savings | Acknowledged. Fail-open is the correct trade. Below uptime telemetry tracked separately. The savings are conditional on Below being up.                                     |
| Routing flag in runtime-env.sh + .zshrc not picked up by Claude Code session                                              | below-route.sh self-sources runtime-env.sh at top, independent of caller's env. Tested by stripped-env verification command above.                                          |
| Crontab edit deletes unrelated entries                                                                                    | Pre-edit backup is a hard deliverable. Edit uses `grep -v collect-intel.sh \| crontab -` (line removal, not full rewrite).                                                  |
| intel_scoring.py edit breaks the 30-min cron                                                                              | Edit is additive only (replace `break` with `_flag_needs_opus_review + continue`). Public signatures unchanged. Verified by import test in Phase 3 verification.            |
| Phase 3 filter too aggressive → important items skipped                                                                   | Override list `priority IN ('critical','high')` always pass through. Default threshold 6/10 is intentionally generous (above mid). User can tune via `BR3_INTEL_MIN_SCORE`. |
| qwen3:8b returns malformed JSON for classifier                                                                            | `format=json` constrains. On parse error: existing `safe_default("invalid_json")` returns "backend-build" (current behavior).                                               |
| qwen3:8b times out / hangs                                                                                                | Bounded timeouts on all swaps (3000ms classifier, 30s stop-when, 60s intel scoring). No path is unbounded.                                                                  |
| `--skip-prefilter` becomes the default by accident                                                                        | Defaults are pre-filter ON. Flag is opt-out only. Documented in `--help`.                                                                                                   |

---

## Total Phases: 3

## Parallelizable: Phase 1 ∥ Phase 2; Phase 3 sequential after Phase 2

## Estimated wall-clock: ~3 hours (Phase 1 ~45 min, Phase 2 ~30 min, Phase 3 ~90 min including testing)
