# Plan: br3-memory-repomix-wave

## Purpose

Deliver two complementary capability waves in one BUILD:

1. **Memory enhancements** (A1, A2): enable per-prompt Jimmy retrieval + auto-capture of per-phase lessons-learned into `decisions.log` and Jimmy memory.
2. **Repomix tooling** (B1–B5): install Repomix CLI cluster-wide, register its MCP plugin, wire Tree-sitter compression into `/learn` + `/cluster-research`, and front-load Repomix codemaps on autopilot phase dispatch. Task B5 (Jimmy Tree-sitter chunking) is scoped out to a future BUILD.

## Prior-State Survey

**File:** `.buildrunner/plans/survey-br3-memory-repomix-wave.md`

Survey clean. Prior BUILDs do not collide. Shared surface (`~/.buildrunner/scripts/`, `~/.claude/commands/`, `~/.claude/settings.json`) is all user-scoped — changes apply across every BR3 project. All new behavior is gated on `BR3_*=on/off` env vars with defaults off. Rollback = flip flag.

## Source-of-Truth References

- Hook registry: `~/.claude/settings.json` (SessionStart + UserPromptSubmit arrays)
- Existing per-prompt Jimmy hook: `~/.buildrunner/hooks/auto-context.sh` (gated on `BR3_AUTO_CONTEXT=on`)
- Autopilot posture prefix: `~/.buildrunner/scripts/autopilot-dispatch-prefix.sh` (insertion point: between line 115 EOF and line 117 LLMLingua block)
- Cluster dispatch: `~/.buildrunner/scripts/dispatch-to-node.sh` (posture assembly lines 534-544; post-SSH hook point after line 598)
- Phase completion hook: `~/.buildrunner/scripts/autopilot-phase-hook.sh` (current early-exit lines 18-21 for non-final phases)
- Skills: `~/.claude/commands/learn.md` Step 4 lines 239-249; `~/.claude/commands/cluster-research.md` Step 1 lines 20-32
- Jimmy `/retrieve`: `http://10.0.1.106:8100/retrieve` — POST `{query, top_k, sources}`
- Jimmy memory note: `POST $NODE_URL/api/memory/note` (pattern from `/save` skill)
- Cluster nodes: Muddy (macOS), Lockwood, Walter, Otis, Lomax (macOS), Below (Windows), Jimmy (Linux)

## Out of Scope

- **B5**: Jimmy sub-document Tree-sitter chunking. Deferred — requires re-indexing the research library, Tree-sitter grammar coverage audit, and pipeline rewrite on the Jimmy node. To be planned as `BUILD_jimmy-treesitter-chunking` after phases 1-7 of this spec land and prove value.
- **Repomix in `/research`**: the multi-LLM research pipeline (`/research` Step 4 enrichment) is not edited. The retrieval-library surface is stable; changing it risks the $2/invocation budget cap and adversarial-review flow.
- **Jimmy indexing pipeline** — no writes to `/srv/jimmy/research-library/` in any phase.
- **Change to retrieval-skill model pins** — `/learn`, `/research`, `/cluster-research` stay pinned to Sonnet 4.6 per global CLAUDE.md.

## Phase Outline

### Phase 1: B1 — Install Repomix CLI on all 7 cluster nodes

**Goal:** Every node can run `repomix --compress` on demand.

**Files:**

- `~/.buildrunner/scripts/repomix-cluster-install.sh` (NEW)
- `~/.buildrunner/scripts/repomix-verify-matrix.sh` (NEW)
- `.buildrunner/decisions.log` (APPEND: install matrix)

**Deliverables:**

- [ ] Write `repomix-cluster-install.sh`: per-node SSH loop (Windows Below via PowerShell branch), Node >=20 check, idempotent install, log to `.buildrunner/logs/repomix-install-<node>.log`
- [ ] Write `repomix-verify-matrix.sh`: SSH each node, run `node --version && repomix --version`, emit markdown table
- [ ] Execute install on all 7 nodes
- [ ] Run `repomix --compress --include <a-small-file>` on each node to confirm Tree-sitter works
- [ ] Commit install matrix + one sample compressed output to `decisions.log`

**Success Criteria:** Verify-matrix script reports 7/7 nodes with Node >=20 and `repomix --version` ≥ current stable.

**Rollback:** `ssh <node> "npm uninstall -g repomix"`

---

### Phase 2: B2 — Register Repomix MCP plugin

**Goal:** Any Claude Code session in BuildRunner3 (including autopilot dispatches) can call Repomix MCP tools.

**Files:**

- `/Users/byronhudson/Projects/BuildRunner3/.claude/settings.json` (NEW — first `mcpServers` block)
- `.buildrunner/decisions.log` (APPEND: MCP registration + sanity check)

**Deliverables:**

- [ ] Create `.claude/settings.json` with `mcpServers.repomix = { command: "npx", args: ["-y", "repomix", "--mcp"] }`
- [ ] Start a fresh Claude Code session; confirm Repomix MCP tools (`pack_codebase`, `grep_repomix_output`, etc.) appear in the tool manifest
- [ ] Run one sanity `pack_codebase` call against a small BR3 subdirectory; verify output
- [ ] If permission prompts fire, add corresponding entries to `.claude/settings.local.json`
- [ ] Document rollback: delete `mcpServers.repomix` block or whole file

**Success Criteria:** Sanity `pack_codebase` returns compressed XML for a test path; no stderr warnings.

---

### Phase 3: A1 — Audit + enable per-prompt Jimmy retrieval

**Goal:** `BR3_AUTO_CONTEXT=on` globally, with verified retrieval quality and bounded failure modes.

**Files:**

- `~/.buildrunner/hooks/auto-context.sh` (MODIFY — harden)
- `~/.buildrunner/scripts/auto-context-quality-probe.sh` (NEW)
- `~/.buildrunner/config/auto-context.env` (NEW — tuning knobs)
- `.buildrunner/decisions.log` (APPEND: probe results, enable decision)

**Deliverables:**

- [ ] Read current `auto-context.sh` end-to-end; document top_k, timeout, dedupe logic in plan artifact
- [ ] Write `auto-context-quality-probe.sh`: submits 10 canned prompts (coding, debug, question, research, admin) against Jimmy; scores relevance of returned snippets via heuristic + LLM judge (Sonnet 4.6, effort medium, ≤$0.30 total)
- [ ] Review probe output; tune `top_k` and dedupe-vs-SessionStart logic in `auto-context.env`
- [ ] Add hard timeout + circuit-breaker: if Jimmy >500ms 3x in a row, skip for remainder of session (state in `/tmp/br3-auto-context-tripped`)
- [ ] Ensure on error, script emits empty `<auto-context>` block and exit 0 — never blocks prompts
- [ ] Flip `BR3_AUTO_CONTEXT=on` in `~/.bashrc` / `~/.zshrc`; log in decisions
- [ ] Add one-line `/rules` reminder about killswitch behavior

**Success Criteria:** Probe scores ≥7/10 on relevance; 100 consecutive prompts in real session show 0 blocks / no latency regression >500ms median.

**Rollback:** Unset `BR3_AUTO_CONTEXT`.

---

### Phase 4: B3 — Wire `repomix --compress` into /learn and /cluster-research

**Goal:** Context assembly in these two skills goes through Repomix compression when 3+ files need loading.

**Files:**

- `~/.claude/commands/learn.md` (MODIFY — Step 4 lines 239-249)
- `~/.claude/commands/cluster-research.md` (MODIFY — Step 1 lines 20-32)
- `.buildrunner/decisions.log` (APPEND: compression delta measurements)

**Deliverables:**

- [ ] Edit `/learn` Step 4: when match count ≥3, invoke `repomix --compress --include "<paths>" --stdout` and feed stdout into context; fallback to per-file Read when `repomix` binary missing (detect via `command -v repomix`)
- [ ] Edit `/cluster-research` Step 1: replace the six explicit `cat` calls with a single `repomix --compress --include <6-file-glob> --stdout`; identical fallback
- [ ] Measure token delta on 3 representative queries (pre- vs post-); target 40-60% reduction
- [ ] Verify model pin stays `claude-sonnet-4-6` on both skills (enforced in edits)
- [ ] Document the dependency on Phase 1 (Repomix CLI must be installed) in the skill file

**Success Criteria:** Both skills pass sanity invocations; token delta ≥40% on at least 2/3 probe queries.

**Rollback:** Revert skill files to prior commit.

---

### Phase 5: A2 — Post-phase lessons-learned hook

**Goal:** Every autopilot phase auto-captures 10-line lessons-learned note to `decisions.log` and Jimmy memory.

**Files:**

- `~/.buildrunner/scripts/lessons-learned.sh` (NEW)
- `~/.buildrunner/scripts/autopilot-phase-hook.sh` (MODIFY — replace early-exit at lines 18-21)
- `~/.buildrunner/scripts/dispatch-to-node.sh` (MODIFY — optional post-SSH call after line 598)
- `/Users/byronhudson/Projects/BuildRunner3/CLAUDE.md` (MODIFY — add `BR3_PHASE_LESSONS` to native-levers table)
- `.buildrunner/decisions.log` (APPEND: lessons entries)

**Deliverables:**

- [ ] Write `lessons-learned.sh <phase_num> <total_phases> <project_root> <build_name>`: launch `claude -p` with tight 10-line prompt (effort medium, ~1-2k tokens), pipe output to `echo "$(date -u +%FT%TZ) [lessons] build=$BUILD phase=$N ..." >> $PROJECT/.buildrunner/decisions.log` and `POST $NODE_URL/api/memory/note`
- [ ] Modify `autopilot-phase-hook.sh`: replace unconditional early-exit at lines 18-21 with `if [[ "$BR3_PHASE_LESSONS" == "on" ]]; then lessons-learned.sh "$@"; fi; [[ "$PHASE_NUM" -lt "$TOTAL_PHASES" ]] && exit 0`
- [ ] Confirm Jimmy `api/memory/note` endpoint accepts the payload (smoke test)
- [ ] Add `BR3_PHASE_LESSONS=on/off` row to BuildRunner3 project CLAUDE.md native-levers table
- [ ] Test on a scratch phase — spawn a minimal BUILD with one fake phase, verify lessons entry written in both places
- [ ] Document token cost per phase in decisions.log

**Success Criteria:** Scratch phase run produces valid decisions.log entry + Jimmy note within 90s of phase completion; token cost <3k.

**Rollback:** `unset BR3_PHASE_LESSONS` or revert hook changes.

---

### Phase 6: B4 — Pre-phase Repomix context bundle for autopilot

**Goal:** Autopilot phase prompts get a Repomix-compressed codemap of in-scope files front-loaded into the posture prefix.

**Files:**

- `~/.buildrunner/scripts/autopilot-dispatch-prefix.sh` (MODIFY — insert after line 115 EOF, before line 117 LLMLingua block)
- `~/.buildrunner/scripts/dispatch-to-node.sh` (MODIFY — POSTURE_PREFIX assembly at lines 534-544)
- `~/.buildrunner/scripts/repomix-bundle.sh` (NEW — extract BUILD-spec in-scope files → compressed bundle)
- `/Users/byronhudson/Projects/BuildRunner3/CLAUDE.md` (MODIFY — add `BR3_REPOMIX_BUNDLE` to native-levers table)

**Deliverables:**

- [ ] Write `repomix-bundle.sh <build_spec_path> <phase_num>`: parses `**Files:**` list for the phase, runs `repomix --compress --include <list> --stdout`, returns bundle text
- [ ] Modify `autopilot-dispatch-prefix.sh`: between line 115 (EOF) and line 117 (LLMLingua block), add `if [[ "$BR3_REPOMIX_BUNDLE" == "on" ]] && command -v repomix >/dev/null; then emit bundle from repomix-bundle.sh; fi`
- [ ] Document interaction order with LLMLingua: Repomix runs FIRST (AST-aware compression), then LLMLingua (optional prose compression) processes the already-bundled output. Add rationale comment in script.
- [ ] Add `BR3_REPOMIX_BUNDLE=on/off` row to project CLAUDE.md native-levers table
- [ ] Measure: one real phase dispatch with and without bundle, compare token count + mid-phase file-read count (from transcript)
- [ ] Document rollback (flag off) in script comment header

**Success Criteria:** With flag on, bundle appears in phase prompt; measured phase mid-session file-reads drop by ≥30% on at least 1 phase; no regression in phase success.

**Rollback:** `unset BR3_REPOMIX_BUNDLE`.

---

### Phase 7: Verification — end-to-end integration run

**Goal:** Confirm all 6 enabled features coexist on a real BUILD and measure aggregate impact.

**Files:**

- `.buildrunner/builds/BUILD_br3-repomix-smoke-test.md` (NEW — scratch BUILD, 2 tiny phases)
- `.buildrunner/logs/phase-7-verification.md` (NEW — measurement report)
- `.buildrunner/decisions.log` (APPEND: verification outcome)

**Deliverables:**

- [ ] Create `BUILD_br3-repomix-smoke-test.md`: 2 phases, one terminal-build (touches a throwaway script), one architecture (touches a doc)
- [ ] Run with all flags on: `BR3_AUTO_CONTEXT=on BR3_PHASE_LESSONS=on BR3_REPOMIX_BUNDLE=on`
- [ ] Capture: per-prompt auto-context latency, per-phase bundle size, per-phase lessons entry, any hook stderr
- [ ] Write verification report comparing token/latency vs a baseline dry-run with all flags off
- [ ] Decide: any flag defaults worth flipping to `on` globally? Document decision in report
- [ ] Clean up scratch BUILD spec after verification

**Success Criteria:** All three flags fire without error on smoke-test BUILD; latency regression <1s/phase; lessons entries captured on both phases; bundle reduces phase prompt tokens by ≥20%.

**Rollback:** Individual flags unset.

---

### Phase 8 (placeholder): B5 — Jimmy Tree-sitter chunking

**Status:** out_of_scope — separate BUILD to be planned as `BUILD_jimmy-treesitter-chunking` after Phases 1-7 land and ≥2 weeks of production usage confirms value.

**Rationale for deferral:** B5 re-writes the Jimmy indexing pipeline, requires Tree-sitter grammar coverage audit for Python/TS/JS/Go, mandates full re-index of `/srv/jimmy/research-library/`, and carries downtime risk for `/retrieve`. Phases 1-7 provide the external Repomix crutch — if that proves sufficient, B5 may be descoped entirely.

## Parallelization Matrix

| Phase | Key Files                                                                        | Can Parallel With        | Blocked By                             |
| ----- | -------------------------------------------------------------------------------- | ------------------------ | -------------------------------------- |
| 1     | `~/.buildrunner/scripts/repomix-cluster-install.sh`                              | 3                        | —                                      |
| 2     | `/Users/byronhudson/Projects/BuildRunner3/.claude/settings.json`                 | 3                        | 1 (needs CLI on Muddy)                 |
| 3     | `~/.buildrunner/hooks/auto-context.sh`, `~/.buildrunner/config/auto-context.env` | 1, 2, 4, 5 (independent) | —                                      |
| 4     | `~/.claude/commands/learn.md`, `~/.claude/commands/cluster-research.md`          | 5                        | 1                                      |
| 5     | `~/.buildrunner/scripts/lessons-learned.sh`, `autopilot-phase-hook.sh`           | 4                        | —                                      |
| 6     | `~/.buildrunner/scripts/autopilot-dispatch-prefix.sh`, `repomix-bundle.sh`       | —                        | 1, 5 (benefits from lessons telemetry) |
| 7     | scratch BUILD, logs                                                              | —                        | 1, 2, 3, 4, 5, 6                       |

## Risk Register

- **A1 bad retrieval quality** → blocks enabling. Mitigation: Phase 3 probe gate; skill stays at `BR3_AUTO_CONTEXT=off` if probe fails.
- **B1 Node <20 on some node** → install fails. Mitigation: script checks `node --version` per node, reports before attempting install; user can decide to upgrade Node on offending node as separate work.
- **B2 MCP permission prompts** → runtime friction. Mitigation: pre-add permissions to `.claude/settings.local.json` during Phase 2.
- **B3 skill length regression** → Sonnet 4.6 retrieval skill currently at long-context pin; adding Repomix branch must not push prompt >2k tokens. Mitigation: Phase 4 tracks skill token length before/after.
- **B4 collision with LLMLingua** → double-compression could strip structure. Mitigation: Phase 6 documents order (Repomix first, LLMLingua optional) and tests both.
- **A2 lessons-learned slop** → low-signal entries pollute decisions.log. Mitigation: prompt is constrained to 10 lines + specific categories (what was hard, what to warn next agent, key insight); if probe on scratch phase produces fluff, tune prompt or disable.
- **Hook latency stacking** → multiple UserPromptSubmit hooks + SessionStart hook + PostToolUse hooks can degrade UX. Mitigation: Phase 7 measures aggregate latency; A1 circuit-breaker; all new hooks have hard timeouts.

## Rollback Summary

All new behavior is feature-flagged:

- `BR3_AUTO_CONTEXT=off` — kills A1
- `BR3_PHASE_LESSONS=off` — kills A2
- `BR3_REPOMIX_BUNDLE=off` — kills B4
- Revert `~/.claude/commands/learn.md` and `cluster-research.md` — kills B3
- Delete `mcpServers.repomix` from `.claude/settings.json` — kills B2
- `npm uninstall -g repomix` per node — kills B1
