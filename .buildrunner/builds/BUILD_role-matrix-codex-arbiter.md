# Build: role-matrix-codex-arbiter

```yaml
role-matrix:
  inherit: default-role-matrix
  overrides:
    phases:
      phase_1: { bucket: terminal-build, assigned_node: muddy, builder: claude }
      phase_2: { bucket: terminal-build, assigned_node: muddy, builder: claude }
      phase_3: { bucket: terminal-build, assigned_node: muddy, builder: claude }
      phase_4: { bucket: backend-build, assigned_node: muddy, builder: claude }
      phase_5: { bucket: backend-build, assigned_node: muddy, builder: claude }
      phase_6: { bucket: terminal-build, assigned_node: muddy, builder: claude }
      phase_7: { bucket: backend-build, assigned_node: muddy, builder: claude }
      phase_8: { bucket: qa, assigned_node: muddy, builder: codex }
```

**Created:** 2026-04-25
**Status:** COMPLETE — All 8 phases arbiter-approved (Phase 8 closed via 2026-04-25 fresh E2E; see `.buildrunner/verify/role-matrix-codex-arbiter.md` and handoff `role-matrix-codex-arbiter-prod-ready.md`).
**Deploy:** operator-tooling — no user-facing deploy; changes live under `~/.buildrunner/scripts/`, BR3 project files, and `core/cluster/cross_model_review.py`.
**Source Plan File:** .buildrunner/plans/plan-role-matrix-codex-arbiter.md
**Source Plan SHA:** 88eca53a794970bf765a55d445811cd9466e3858e403e9021d1614707cdf0d97
**Adversarial Review Verdict:** BYPASSED:.buildrunner/bypass-justification.md
**Adversarial Review Timestamp:** 2026-04-25T15:11:38Z
**Prior-State Survey:** .buildrunner/plans/survey-role-matrix-codex-arbiter.md
**Owner:** byronhudson

## Overview

Make codex the durable default builder for BuildRunner3 and all future projects, with claude (Sonnet) as orchestrator and per-phase reviewer, and Opus 4.7 as final arbiter on disagreement. Resolves the root cause of inline-Opus building: codex's `--sandbox workspace-write --cd $PROJECT_PATH` cannot write home-dir cluster paths, so autopilot Rule 22 deterministically demoted codex→claude on every build with out-of-project files. Solution stack: per-project `.buildrunner/codex-sandbox.toml` + `--add-dir` flag plumbing (the actual codex 0.124.0 CLI surface, not the speculative `-c sandbox_workspace_write.writable_roots` TOML key); per-phase Rule 22 granularity instead of whole-build demotion; codex-side dispatch posture prefix; new per-phase review hook calling `cross_model_review.py --mode phase` with one-revision-then-arbiter cap; project + global default flipped via explicit `br runtime set` CLI (no `/spec-codex` auto-coupling); stale codex alert traced to its real emit site. Bootstrap runs phases 1-7 on claude (the build modifies the very dispatch path); phase 8 explicitly tests codex on a clean project then revisits BUILD_burnin-queue-v2.

## Parallelization Matrix

| Phase | Key Files                                                                                                                                                                                             | Can Parallel With | Blocked By    |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | ------------- |
| 1     | `~/.buildrunner/scripts/runtime-dispatch.sh`, `~/.buildrunner/scripts/lib/codex-sandbox-config.sh` (NEW), `.buildrunner/codex-sandbox.toml` (NEW), `tests/runtime/test_codex_sandbox_loader.sh` (NEW) | 3, 5, 7           | —             |
| 2     | Rule 22 emit site (locate during phase), `lib/codex-sandbox-config.sh` (REUSE)                                                                                                                        | 3, 5, 7           | 1             |
| 3     | `~/.buildrunner/scripts/autopilot-dispatch-prefix-codex.sh` (NEW), `~/.buildrunner/scripts/runtime-dispatch.sh`                                                                                       | 1, 5, 7           | —             |
| 4     | `~/.buildrunner/scripts/autopilot-phase-review-hook.sh` (NEW), phase-loop driver (locate during phase)                                                                                                | —                 | 3, 5          |
| 5     | `core/cluster/cross_model_review.py`, `core/cluster/cross_model_review_config.json`, `tests/cluster/test_cross_model_review_phase_scope.py` (NEW)                                                     | 1, 3, 7           | —             |
| 6     | `.buildrunner/runtime.json`, project-bootstrap template (locate during phase), `~/.claude/skills/spec-codex/SKILL.md`, `~/.buildrunner/scripts/br-runtime.sh` (NEW)                                   | —                 | 1, 2, 3, 4, 5 |
| 7     | TBD per investigation (likely SessionStart hook); `core/runtime/postflight.py:303` confirm/refute                                                                                                     | 1, 3, 5           | —             |
| 8     | `/tmp/codex-flow-test/` (NEW), `.buildrunner/verify/role-matrix-codex-arbiter.md` (NEW), `tests/verify/assert-role-matrix-flow.sh` (NEW)                                                              | —                 | 1-7           |

Wave 1 (parallel): {1, 3, 5, 7}. Wave 2 (after 1): {2}. Wave 3 (after 3, 5): {4}. Wave 4 (after all core): {6}. Wave 5: {8}.

## Phases

### Phase 1: Codex sandbox writable-roots plumbing

**Status:** ⏳ PENDING
**Files:**

- `~/.buildrunner/scripts/runtime-dispatch.sh` (MODIFY)
- `~/.buildrunner/scripts/lib/codex-sandbox-config.sh` (NEW)
- `/Users/byronhudson/Projects/BuildRunner3/.buildrunner/codex-sandbox.toml` (NEW)
- `tests/runtime/test_codex_sandbox_loader.sh` (NEW — persistent regression artifact)

**Blocked by:** None
**Deliverables:**

- [ ] Define schema for `.buildrunner/codex-sandbox.toml` with `additional_writable_roots = ["~/.buildrunner/", "~/Library/LaunchAgents/"]` array form.
- [ ] Loader script in `lib/codex-sandbox-config.sh` reads the file (if present), expands `~`, validates each root exists or is a creatable parent, emits one `--add-dir <root>` flag per entry on stdout, exits 0 on success / non-zero on malformed config.
- [ ] `runtime-dispatch.sh` codex branch sources the loader, captures its output into a flag array, and inserts those flags into the `codex exec` invocation BEFORE the existing `--sandbox workspace-write --cd "$PROJECT_PATH"` pair.
- [ ] BR3's `.buildrunner/codex-sandbox.toml` populated with `~/.buildrunner/` and `~/Library/LaunchAgents/` entries.
- [ ] Smoke test: dispatch a no-op codex prompt with the BR3 config; verify the resulting `codex exec` command line contains the expected `--add-dir` flags (capture via shell trace).
- [ ] Verify backward compat: a project without `codex-sandbox.toml` produces a `codex exec` invocation byte-identical to the pre-change baseline.
- [ ] Persistent regression artifact: `tests/runtime/test_codex_sandbox_loader.sh` (NEW) — sourced by CI smoke runs; asserts (a) zero `--add-dir` flags emitted when no config present, (b) expected `--add-dir` count when BR3 config present, (c) malformed config exits non-zero.

**Success Criteria:**

- `bash -x runtime-dispatch.sh codex /Users/byronhudson/Projects/BuildRunner3 /tmp/test-prompt.txt` shows `--add-dir /Users/byronhudson/.buildrunner` and `--add-dir /Users/byronhudson/Library/LaunchAgents` in the codex argv.
- A small test write to `~/.buildrunner/test-write-$$` succeeds when dispatched with the BR3 config; the test file is then cleaned up.
- Running the same dispatch in a project without the config (e.g. `/tmp/sandbox-test-bare`) shows zero `--add-dir` flags.
- `bash tests/runtime/test_codex_sandbox_loader.sh` exits 0.

### Phase 2: Rule 22 — per-phase granularity, sandbox-aware

**Status:** ⏳ PENDING
**Files:**

- Rule 22 emit site (locate during phase) (MODIFY)
- `~/.buildrunner/scripts/lib/codex-sandbox-config.sh` (REUSE from Phase 1)

**Locator strategy (primary → fallback):** (1) `grep -rn "out-of-project-files\|Rule 22 forward path\|workspace-write sandbox scoped" ~/.buildrunner/scripts/ ~/.claude/skills/autopilot/`; (2) if absent, `git log -S "out-of-project-files" --all -- ~/.buildrunner/scripts/`; (3) if still absent, `grep -rn "override=" ~/.buildrunner/scripts/`; (4) last resort — introduce `~/.buildrunner/scripts/lib/role-demotion-rules.sh`. `core/cluster/context_router.py` is explicitly NOT a candidate (wrong abstraction layer).

**Blocked by:** Phase 1
**Deliverables:**

- [ ] Locate the actual Rule 22 emit site by searching for `out-of-project-files` and `Rule 22 forward path` strings; document the file path in commit message.
- [ ] Compute per-phase target file set from the BUILD spec's `Files:` block.
- [ ] Compare each path against (project root ∪ `additional_writable_roots`); demote ONLY phases with one or more files outside the union.
- [ ] Decisions-log entry shape: `[autopilot] phase=<N> override=out-of-allowlist offending_path=<first-violator> builder=claude` (one entry per demoted phase).
- [ ] Preserve existing whole-build demotion as the fallback path when no `codex-sandbox.toml` exists (keeps current behavior for non-BR3 projects).

**Success Criteria:**

- Manufactured test build with Phase A targeting in-project + Phase B targeting `~/Library/LaunchAgents/` AND a populated `codex-sandbox.toml` allowlisting `~/Library/LaunchAgents/` → both phases route to codex (no demotion).
- Same test with the allowlist entry REMOVED → only Phase B demotes; Phase A still routes to codex.
- Same test with no `codex-sandbox.toml` at all → whole-build demotion fires (legacy behavior preserved).

### Phase 3: Codex dispatch posture prefix

**Status:** ⏳ PENDING
**Files:**

- `~/.buildrunner/scripts/autopilot-dispatch-prefix-codex.sh` (NEW)
- `~/.buildrunner/scripts/runtime-dispatch.sh` (MODIFY — invoke codex prefix on codex branch)

**Blocked by:** None (independent of Phase 1; composes in Phase 4)
**Deliverables:**

- [ ] New script accepts flags: `--effort low|medium|high|xhigh` (default `medium` for codex per fixit skill — codex defaults differ from CLAUDE.md's claude-side `xhigh` mandate; `xhigh` for codex is documented as anti-pattern in fixit), `--model gpt-5.5|gpt-5.4|gpt-5.3-codex` (default gpt-5.5), `--phase-weight light|heavy|hardest` (default heavy). Document the codex-vs-claude effort split in the script header so the divergence from CLAUDE.md is intentional and discoverable.
- [ ] Emits markdown header documenting: turn-1 preamble rule, sandbox flag presence (apply_patch otherwise rejected), one-revision rule, per-phase context paths via `--add-dir`.
- [ ] Plan-mode trigger when phase-weight=hardest (mirrors claude prefix).
- [ ] Reads env: `BR3_CODEX_MODEL`, `BR3_CODEX_EFFORT`, `BR3_CODEX_PHASE_WEIGHT` for autopilot overrides.
- [ ] `runtime-dispatch.sh` codex branch invokes the prefix and prepends its output to `${PROMPT_CONTENT}` (sequencing: posture → context-bridge → user prompt).

**Success Criteria:**

- `autopilot-dispatch-prefix-codex.sh --effort medium --model gpt-5.5` prints a non-empty markdown block with the required sections.
- A codex dispatch shows the new posture header at the top of the prompt; `BR3_CODEX_EFFORT=high` env override changes the effort line in the rendered header.

### Phase 4: Per-phase review hook (NEW hook)

**Status:** ⏳ PENDING
**Files:**

- `~/.buildrunner/scripts/autopilot-phase-review-hook.sh` (NEW)
- Phase-loop driver — locate during phase (MODIFY — add invocation point)

**Locator strategy (primary → fallback):** (1) `grep -rn "phase_complete\|phase advance\|next phase\|PHASE_NUM=" ~/.buildrunner/scripts/`; (2) inspect `~/.buildrunner/scripts/build-sidecar.sh` and `~/.buildrunner/scripts/autopilot-phase-hook.sh` for the per-phase tail; (3) if no single driver exists, integrate at `runtime-dispatch.sh` exit since every phase dispatch flows through it.

**Blocked by:** Phase 3, Phase 5
**Deliverables:**

- [ ] Hook signature: `$0 <build_id> <phase_n> <diff_path> <success_criteria_path>`; exit 0 = advance phase, exit 1 = block phase.
- [ ] Step A: invoke `python3 -m core.cluster.cross_model_review --mode phase` (Phase 5's new mode) directly — there is no `cross-model-review.sh` wrapper in the tree; do NOT introduce one. Sonnet is the reviewer; capture verdict from JSON stdout.
- [ ] Step B: on `reject`, re-dispatch the same phase prompt to codex with reviewer findings appended as `## Reviewer Findings` block; revision_count increments to 1.
- [ ] Step C: on second `reject` after revision, invoke Opus 4.7 arbiter via cross_model_review.py's new arbiter path with both diffs + both reviews; arbiter verdict is final and unappealable.
- [ ] Hard cap: revision_count > 1 short-circuits to arbiter (no infinite revision loops).
- [ ] Decisions-log entries: one per step, format `phase-review build=<id> phase=<N> revision=<count> verdict=<approve|reject|arbiter-approve|arbiter-reject>`.
- [ ] Phase-loop driver invokes this hook after every phase completion (before advancement), regardless of phase being final.

**Success Criteria:**

- Manufactured test phase whose diff intentionally violates a Success Criteria bullet → reviewer rejects, codex revises, reviewer approves, hook exits 0; decisions.log shows three entries (verdict=reject, revision=1, verdict=approve).
- Manufactured test where reviewer rejects both initial and revised → arbiter is invoked exactly once; final verdict recorded; phase advances or aborts per arbiter.
- Hook returns exit 0 for any phase whose initial review approves (no revision spawned, no arbiter invoked).

### Phase 5: cross_model_review.py — phase-scoped revision tracking

**Status:** ⏳ PENDING
**Files:**

- `core/cluster/cross_model_review.py` (MODIFY)
- `core/cluster/cross_model_review_config.json` (MODIFY)
- `tests/cluster/test_cross_model_review_phase_scope.py` (NEW)

**Blocked by:** None (independent; needed by Phase 4)
**Deliverables:**

- [ ] Add `--mode phase` argparse flag distinct from `--mode plan`; routing dispatches to a new `_run_phase_review` function.
- [ ] Phase-scoped cache key (canonical): the triple `(build_id, phase_n, revision_count)`. Tracking-file naming uses the triple plus a short `diff_sha256[:12]` suffix for human-readable disambiguation, but the triple alone is the idempotency key — a force-retry on the same triple returns the cached verdict regardless of diff content. Tracking files written under `.buildrunner/cluster-reviews/phase/`.
- [ ] Idempotency: same triple → cached verdict returned; triple with `revision_count+1` → fresh review (cache miss by construction, since the triple differs).
- [ ] Update `SUPPORTED_CODEX_VERSION_MAX` in `cross_model_review.py` to accommodate codex 0.124.0 (current installed version). Either bump to `(0, 200, 0)` as a forward-permissive bound or (preferred) replace the strict tuple gate with a min-only check + warn-on-unknown-major. Document the choice in commit message.
- [ ] Arbiter call site: when reviewer disagrees and revision_count == 1, escalate to model from config `cross_model_review_config.json` (key `phase_arbiter_model`, default `claude-opus-4-7`).
- [ ] Tests in `tests/cluster/test_cross_model_review_phase_scope.py`: idempotency within triple; non-collision across revisions; arbiter only fires on second reject; plan-mode behavior preserved; codex version-gate accepts 0.124.0.
- [ ] Plan-mode contract: zero changes to `--mode plan` argv, hash shape, or tracking-file location. Verified by an existing plan-mode test still passing.

**Success Criteria:**

- `pytest tests/cluster/test_cross_model_review_phase_scope.py -v` passes all new tests.
- Existing plan-mode tests pass without modification.
- A manual `cross_model_review.py --mode phase --build-id test --phase 1 --revision 0 --diff /tmp/d.patch --criteria /tmp/c.md` produces a verdict and writes to `.buildrunner/cluster-reviews/phase/test-phase1-rev0-<sha>.json`.

### Phase 6: Runtime defaults — codex everywhere via config

**Status:** ⏳ PENDING
**Files:**

- `/Users/byronhudson/Projects/BuildRunner3/.buildrunner/runtime.json` (MODIFY)
- Project-bootstrap skill template — locate during phase (likely `~/.claude/skills/init/SKILL.md` or BR3's `init` script) (MODIFY)
- `~/.claude/skills/spec-codex/SKILL.md` if present, else `~/.claude/skills/spec/SKILL.md` codex branch — locate via `find ~/.claude/skills -name SKILL.md -exec grep -l "spec-codex\|/spec-codex" {} +` (MODIFY — add reminder, NOT auto-write)
- `~/.buildrunner/scripts/br-runtime.sh` (NEW or MODIFY — adds `br runtime set <codex|claude>` subcommand)

**Blocked by:** Phases 1, 2, 3, 4, 5
**Deliverables:**

- [ ] Flip BR3's `.buildrunner/runtime.json` to `{"schema_version": "br3.runtime.config.v1", "default_runtime": "codex"}`.
- [ ] Locate project-bootstrap entry point. Update its `runtime.json` template to emit `default_runtime: codex` for new projects. If BR3 has no init skill yet, document which skill should own this and create a stub.
- [ ] Modify `/spec-codex` SKILL.md: remove any text that proposes auto-modifying `runtime.json`; add a one-line operator reminder ("project default is `<current>`; run `br runtime set codex` to switch") printed when current default is not codex.
- [ ] Add `br runtime set <codex|claude>` subcommand: writes `.buildrunner/runtime.json` atomically (temp file + rename), preserves schema_version, prints old and new value.
- [ ] No changes to `core/runtime/config.py` runtime-resolution semantics — file remains the single source of truth.
- [ ] Rollback procedure documented in commit message and as comment in `br-runtime.sh`: if codex builds fail post-flip, `br runtime set claude` reverts atomically; no migrations or stateful side-effects to undo. Operator can cycle freely between values.

**Success Criteria:**

- BR3's `runtime.json` reads `codex` after Phase 6.
- `br runtime set claude` then `br runtime set codex` round-trips cleanly with atomic writes (no partial files visible during).
- `/spec-codex` invocation in a fresh project shows the reminder line and does NOT modify `runtime.json`.
- New-project bootstrap creates `runtime.json` with codex when run on a tmp dir.

### Phase 7: Stale codex alert — find the real source

**Status:** ⏳ PENDING
**Files:**

- Discovered during phase. Likely candidates: SessionStart hook script (location TBD), `core/runtime/postflight.py:303` (per codex review, likely NOT the source), dashboard alert endpoint, brief generator.

**Blocked by:** None (investigation phase)
**Deliverables:**

- [ ] Trace the literal alert string `codex: last=error error=RuntimeError` to its emit point. Use `grep -rn` across `~/.buildrunner/`, `~/.claude/`, BR3 project, dashboard sources.
- [ ] Document the actual emit site (file:line) in commit message.
- [ ] Confirm or refute codex's claim that `core/runtime/postflight.py:303` already treats missing files as "no signal" — read the function, write the verdict in the commit.
- [ ] At the actual emit site, add a freshness check: drop the alert when the last codex run was older than `BR3_CODEX_ALERT_TTL_SECONDS` (default 86400 / 24h) OR no recent run exists.
- [ ] Verify a fresh shell session post-fix shows no false codex RuntimeError.

**Success Criteria:**

- The "codex: last=error error=RuntimeError" line no longer appears in the SessionStart brief when no recent codex run has failed within the TTL window.
- A new actual codex failure within TTL DOES still surface as an alert (regression check — don't suppress real errors).
- Commit message documents which file the bug actually lived in (whether postflight.py or elsewhere).

### Phase 8: E2E verification — clean project + burnin retest

**Status:** ⏳ PENDING
**Files:**

- `/tmp/codex-flow-test/` (NEW — throwaway test project; project-root-only files)
- `/Users/byronhudson/Projects/BuildRunner3/.buildrunner/verify/role-matrix-codex-arbiter.md` (NEW — verification report)
- `tests/verify/assert-role-matrix-flow.sh` (NEW — automated assertion script)

**Bucket:** qa · **Node:** muddy · **Builder:** codex (this phase explicitly tests codex; runs on muddy because the burnin retest reads/writes Muddy-relative paths under `~/.buildrunner/scripts/burnin/`, and the `/tmp/codex-flow-test/` scratch project is also local to muddy)

**Blocked by:** Phases 1-7
**Deliverables:**

- [ ] `mkdir -p /Users/byronhudson/Projects/BuildRunner3/.buildrunner/verify` (parent directory for the verification report — must exist before Write).
- [ ] Bootstrap `/tmp/codex-flow-test/`: `git init`, write a tiny BUILD spec with two phases — phase 1 = trivial pass (write a file with expected content), phase 2 = forced reviewer rejection (intentionally violates a Success Criteria bullet to trigger the revision→arbiter path).
- [ ] Run autopilot end-to-end on the test project. Capture decisions.log; assert: `builder=codex` on both phases, `phase-review` entries showing the rejection→revision→approval flow on phase 2.
- [ ] Re-attempt BUILD_burnin-queue-v2 phase 3 with codex+writable-roots config. Assert: codex writes to `~/.buildrunner/scripts/burnin/lib/worker.sh` succeed, no Rule 22 demotion fires, phase-review hook engages.
- [ ] Write `.buildrunner/verify/role-matrix-codex-arbiter.md` with: test-project decisions.log excerpts, burnin retest excerpts, screenshot of dashboard build view, verdict (PASS|FAIL|PARTIAL).
- [ ] Automated assertion script `tests/verify/assert-role-matrix-flow.sh` (NEW): grep-based assertions over the captured decisions.log — fails non-zero if any of (a) `builder=codex` count per phase ≠ 1, (b) `verdict=approve` missing on phase 1, (c) full `reject → revise → (approve|arbiter-*)` chain missing on phase 2. Run after the autopilot e2e completes; non-zero exit blocks Phase 8 success.
- [ ] Cleanup `/tmp/codex-flow-test/` after capturing evidence.

**Success Criteria:**

- Test project decisions.log: at least one `builder=codex` entry per phase, exactly one `verdict=approve` entry per phase, exactly one `verdict=arbiter-*` entry on phase 2.
- BUILD_burnin-queue-v2 phase 3 dispatch attempts on codex without Rule 22 override; if it fails, verification report names the failure cause.
- Verification report committed to BR3 with verdict line in the first 10 lines.
- `bash tests/verify/assert-role-matrix-flow.sh` exits 0 against the captured decisions.log.

## Out of Scope

- Restructuring BR3's home-directory paths into the project root.
- Adopting `--dangerously-bypass-approvals-and-sandbox` mode at any tier.
- Auto-mutation of `runtime.json` from `/spec-codex` (decoupling enforced per codex's coupling-violation finding).
- Multi-arbiter or N-round (>1) review loops; hard cap is one revision then arbiter.
- Migrating already-completed builds to codex retroactively. New default applies forward only.
- Updating CLAUDE.md operator docs about the new flow (defer to Phase 8 verification report; can be a follow-up build).
- Migrating `~/.buildrunner/scripts/*` into the BR3 project's git tree. Those scripts are intentionally cluster-wide infrastructure shared across every project on this machine; pulling them into project-versioned files is a separate architectural decision out of scope here. Accepted constraint: the home-dir scripts edited by this build are validated by Phase 8's e2e flow rather than by per-line review in git history.
