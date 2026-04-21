# Second Opinion Brief — Cluster-Max Fix Plan Adversarial Review

**Goal:** Unblock the Phase 13 flag-flip cutover for the BR3 `cluster-max` build.
**Question:** After Waves A–G of the fix plan complete, would anything still fail the cutover? Find missing fixes, wave-ordering hazards, invented scripts that don't match the BUILD spec, and hidden dependencies.

## What Was Tried

The fix plan was written after executing the full pre-cutover test plan against the live repo + cluster. Results summary (captured in this conversation):

**Passing:**

- Phase 0 AGENTS.md sizes, Phase 1 GPU + NVLink, Phase 3 Jimmy services, Phase 6 4 capability keys + `test_ollama_runtime.py` 16/16, Phase 7 shim tests 9/9 + deletion-is-clean, Phase 8 summarizer markers, Phase 9 three-way review 28/28 + arbiter Opus 4.7, Phase 12 parity 8/8 + private-leak 9/9 + filter-private works, System-wide RuntimeRegistry invariant + no dead code refs + cluster-guard installed.

**Blockers found:**

- Phase 0: `BR3_GATEWAY_LITELLM` in root AGENTS.md:30; `BR3_MULTI_MODEL_CONTEXT` in jimmy/otis staged AGENTS
- Phase 4: `scripts/audit_overflow_refs.py` missing; wave-merge of Phase 4 snippet not applied
- Phase 5: `BR3_LOCAL_ROUTING` has 3 refs in below-route.sh, `BR3_RUNTIME_OLLAMA` has 0; wave-merge of Phase 5 snippet not applied; `tests/skills/test_autopilot_classifier.py` missing
- Phase 8: `tests/runtime/test_cache_policy.py::test_three_breakpoints` missing; `tests/integration/test_summarize_before_escalate.py::test_50kb_diff_shrinks` missing
- Phase 10: `UserPromptSubmit`+`PhaseStart` not in `~/.claude/settings.json`; `auto-context.sh` emits 0 blocks on real input; `count-tokens.sh` missing
- Phase 11: localhost:4400 not serving; `tests/e2e/cluster-max-dashboard.spec.ts` missing
- Phase 12: 34 `BR3_MULTI_MODEL_CONTEXT` refs in code (api/routes/context.py, core/cluster/context_bundle.py, snippets); Jimmy :4500 not reachable; Otis AGENTS.md not deployed; `br3-context-sync.timer` not enabled; `test_context_bundle.py`, `test_context_router.py`, `test_context_injector.py` all missing
- Phase 13: `~/.buildrunner/config/feature-flags.yaml`, `~/.buildrunner/scripts/rollback-cluster-max.sh`, `scripts/post_cutover_smoke.py` all MISSING
- Phase 14: all 8 timers not deployed; `disk-guard.sh`, `self_health.py`, `auto_rebalance.py` missing; 4 test files missing

**Nuances:**

- Phase 6 capability name mismatch: code returns `local_inference`, test plan said `local_ready`. Test plan was wrong (16/16 ollama tests pass).
- `cluster.json` uses `.nodes.jimmy` (object), test plan used `.nodes[]|map(select(...))` (array form). Jimmy IS present with correct roles.
- `shellcheck` not installed locally.
- Phase 3 Muddy `br3-nightly-backup.timer` not enabled — non-blocker but noted.
- `local_ready` vs `local_inference`: full caps list is `['review', 'analysis', 'plan', 'execution', 'streaming', 'shell', 'browser', 'subagents', 'orchestration_checkpoint', 'cluster_suitable', 'isolated_workspace_only', 'edit_formats', 'json_result', 'local_inference']`.

## Suspect Files

The three primary docs are large — they are included as separate `<<<FILE>>>` blocks below in exact verbatim form. Review them against the fix plan.

Canonical flags that Phase 13 flips: `BR3_RUNTIME_OLLAMA`, `BR3_CACHE_BREAKPOINTS`, `BR3_ADVERSARIAL_3WAY`, `BR3_AUTO_CONTEXT`.

<<<FILE: .buildrunner/cluster-max-fix-plan.md>>>
[see file at that path — full content]

<<<FILE: .buildrunner/cluster-max-pre-cutover-test-plan.md>>>
[see file at that path — full content]

<<<FILE: .buildrunner/builds/BUILD_cluster-max.md (relevant sections: Phase 4, 5, 10, 12, 13, 14)>>>
[see file at that path — full content; 1712 lines]

## Claude's Current Hypothesis

The fix plan groups blockers into 8 waves (A–H). Waves A–G are Phase-13-critical; H is deferred; Phase 14 is scheduled strictly after the 48-hour Phase 13 soak. Ordering rationale:

1. Flag renames first (Wave A) so staged AGENTS snippets consumed by Wave C are already consistent.
2. Scripts (Wave B) before wave-merges (Wave C) because the Phase 5 snippet doesn't exist yet and must be authored.
3. Hook wiring (Wave D) depends on `count-tokens.sh` authored in Wave B.
4. Tests (Wave E) can run after code is in place.
5. Jimmy deploys (Wave F) depend on renamed flags + `br3-context-sync.timer` not blocked by Otis AGENTS drift.
6. Dashboard up (Wave G) is orthogonal but affects smoke check 5.

**Claim:** After Waves A–G, the full pre-cutover test plan should pass with 0 BLOCKERs, and Phase 13 flip + 5/5 smoke + 48h soak becomes executable.

## Request to Codex

Run PASS 1 (FIND) then PASS 2 (CLASSIFY) per the /2nd skill adversarial contract. Ground every finding in the actual file contents. Particular attention to:

1. **Missed blockers** — anything the test plan flagged that the fix plan doesn't address (or addresses incompletely).
2. **Wave-ordering hazards** — commits that land before their dependencies are ready.
3. **Invented scripts/tests** — Wave B item 9 invents `post_cutover_smoke.py` check names; do they match BUILD spec? Wave E tests — do file paths and test IDs match what the test plan names?
4. **Hidden dependencies** — e.g., does `context_router.py` actually exist? `context_injector.py`? Wave E assumes so.
5. **Anything that would still fail cutover** after Waves A–G. E.g., 48-hour soak gate; review-findings.jsonl presence; decisions.log line; AGENTS.md header line count after Phase 13 strips `default OFF` language.
6. **`auto-context.sh` fix hypothesis** — is the `set -eo pipefail` + empty-tag fallback sufficient, or is the real failure mode elsewhere (tokenizer call, reranker connection, stdin handling)?
7. **Phase 14 scope creep risk** — does the plan underweight Phase 14 effort (8 timers, 9 new files, 4 tests)?
