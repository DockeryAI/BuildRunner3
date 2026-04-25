# Build: br3-memory-repomix-wave

```yaml
role-matrix:
  inherit: default-role-matrix
  overrides:
    phases:
      phase_1: { bucket: terminal-build, assigned_node: muddy }
      phase_2: { bucket: terminal-build, assigned_node: muddy }
      phase_3: { bucket: terminal-build, assigned_node: muddy }
      phase_4: { bucket: architecture, assigned_node: muddy }
      phase_5: { bucket: terminal-build, assigned_node: muddy }
      phase_6: { bucket: terminal-build, assigned_node: muddy }
      phase_7: { bucket: qa, assigned_node: muddy }
```

**Created:** 2026-04-24
**Status:** pending
**Deploy:** web — `npm run build && npm run deploy`
**Source Plan File:** .buildrunner/plans/plan-br3-memory-repomix-wave.md
**Source Plan SHA:** 46efc4f9eda2ff0c27c2e70766ce478975fb9700cb451b2460a518a65402e233
**Adversarial Review Verdict:** BYPASSED:.buildrunner/bypass-justification.md
**Adversarial Review Timestamp:** 2026-04-24T13:37:28Z
**Prior-State Survey:** .buildrunner/plans/survey-br3-memory-repomix-wave.md

## Overview

Two complementary capability waves in one BUILD: (A) memory enhancements — per-prompt Jimmy retrieval + post-phase lessons capture; (B) Repomix tooling — cluster-wide CLI install, MCP plugin registration, compression wired into `/learn` and `/cluster-research`, and pre-phase Repomix codemaps front-loaded into autopilot dispatch. All behaviors are feature-flagged (`BR3_*=on/off`, default off) with instant rollback. Jimmy Tree-sitter sub-document chunking (B5) is explicitly deferred to a future BUILD.

## Parallelization Matrix

| Phase | Key Files                                                                                                                                                                                     | Can Parallel With | Blocked By    |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | ------------- |
| 1     | `~/.buildrunner/scripts/repomix-cluster-install.sh` (NEW), `~/.buildrunner/scripts/repomix-verify-matrix.sh` (NEW)                                                                            | 3                 | —             |
| 2     | `.claude/settings.json` (NEW)                                                                                                                                                                 | 3                 | 1 (Muddy CLI) |
| 3     | `~/.buildrunner/hooks/auto-context.sh` (MODIFY), `~/.buildrunner/config/auto-context.env` (NEW), `~/.buildrunner/scripts/auto-context-quality-probe.sh` (NEW)                                 | 1, 2, 4, 5        | —             |
| 4     | `~/.claude/commands/learn.md` (MODIFY), `~/.claude/commands/cluster-research.md` (MODIFY)                                                                                                     | 5                 | 1             |
| 5     | `~/.buildrunner/scripts/lessons-learned.sh` (NEW), `~/.buildrunner/scripts/autopilot-phase-hook.sh` (MODIFY), `CLAUDE.md` (MODIFY)                                                            | 4                 | —             |
| 6     | `~/.buildrunner/scripts/autopilot-dispatch-prefix.sh` (MODIFY), `~/.buildrunner/scripts/repomix-bundle.sh` (NEW), `~/.buildrunner/scripts/dispatch-to-node.sh` (MODIFY), `CLAUDE.md` (MODIFY) | —                 | 1, 5          |
| 7     | `.buildrunner/builds/BUILD_br3-repomix-smoke-test.md` (NEW, scratch), `.buildrunner/logs/phase-7-verification.md` (NEW)                                                                       | —                 | 1,2,3,4,5,6   |

**Parallelizable:** {1, 3}, {1, 3, 5}, {4, 5}. Phase 7 is final verification.

## Phases

### Phase 1: B1 — Install Repomix CLI on all 7 cluster nodes

**Status:** not_started
**Files:**

- `~/.buildrunner/scripts/repomix-cluster-install.sh` (NEW)
- `~/.buildrunner/scripts/repomix-verify-matrix.sh` (NEW)
- `.buildrunner/decisions.log` (APPEND)

**Blocked by:** None

**Pre-validation (completed 2026-04-24):** Node ≥20 confirmed on all 7 nodes (Muddy 24.10, Lockwood 25.9, Walter 22.22, Otis 22.22, Lomax 25.9, Jimmy 22.22, Below 22.11 — installed fresh). Repomix 1.13.1 installed + smoke-tested on Below; Tree-sitter compression confirmed working on Windows.

**Below (Windows) SSH env cache quirk:** Windows sshd service caches PATH at service install time; `Restart-Service` does not refresh it until reboot. Scripts targeting Below must wrap commands in a PowerShell PATH refresh — this is the canonical pattern:

```
ssh below 'powershell -NoProfile -Command "$env:PATH = [Environment]::GetEnvironmentVariable(\"PATH\",\"Machine\") + \";\" + [Environment]::GetEnvironmentVariable(\"PATH\",\"User\"); <your-command>"'
```

Also required on Below: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` (already set) so `.ps1` shims like `repomix.ps1` run.

**Deliverables:**

- [ ] `repomix-cluster-install.sh`: per-node SSH loop with Node ≥20 check; Windows Below branch uses the PowerShell PATH-refresh wrapper documented above; idempotent; logs to `.buildrunner/logs/repomix-install-<node>.log`
- [ ] `repomix-verify-matrix.sh`: emits markdown table (`node | node_version | repomix_version`); for Below, uses the same PowerShell wrapper
- [ ] Install executed on 6 remaining nodes (Muddy, Lockwood, Walter, Otis, Lomax, Jimmy — Below already installed)
- [ ] Sanity: `repomix --compress --include <small-file> --stdout` runs on each node without error
- [ ] Install matrix + sample compressed output appended to `.buildrunner/decisions.log`

**Success Criteria:** Verify matrix reports 7/7 nodes with Node ≥20 and a working `repomix` binary.

**Rollback:** `ssh <node> "npm uninstall -g repomix"`. On Below: `ssh below 'powershell -NoProfile -Command "npm uninstall -g repomix"'` (with PATH wrapper).

---

### Phase 2: B2 — Register Repomix MCP plugin

**Status:** not_started
**Files:**

- `/Users/byronhudson/Projects/BuildRunner3/.claude/settings.json` (NEW)
- `.buildrunner/decisions.log` (APPEND)

**Blocked by:** Phase 1 (CLI must exist on Muddy)

**Deliverables:**

- [ ] Create project `.claude/settings.json` with `mcpServers.repomix = {"command": "npx", "args": ["-y", "repomix", "--mcp"]}`
- [ ] Open fresh session; confirm MCP tools (`pack_codebase`, `grep_repomix_output`, `read_repomix_output`, etc.) appear in tool manifest
- [ ] Run one sanity `pack_codebase` against a small BR3 subdir and inspect output
- [ ] Pre-populate `.claude/settings.local.json` with permissions for the MCP tools if prompts fire
- [ ] Document rollback (delete `mcpServers.repomix` block)

**Success Criteria:** Sanity `pack_codebase` call succeeds; no unhandled permission prompts.

**Rollback:** Remove `mcpServers.repomix` block from `.claude/settings.json`.

---

### Phase 3: A1 — Audit + enable per-prompt Jimmy retrieval

**Status:** not_started
**Files:**

- `~/.buildrunner/hooks/auto-context.sh` (MODIFY)
- `~/.buildrunner/config/auto-context.env` (NEW)
- `~/.buildrunner/scripts/auto-context-quality-probe.sh` (NEW)
- `.buildrunner/decisions.log` (APPEND)

**Blocked by:** None

**Deliverables:**

- [ ] Read current `auto-context.sh` end-to-end; confirm top_k, timeout, dedupe-vs-SessionStart logic
- [ ] Write `auto-context-quality-probe.sh`: 10 canned prompts (coding, debug, question, research, admin); heuristic + LLM-judge scoring (Sonnet 4.6, effort medium, ≤$0.30 total)
- [ ] Tune `top_k` and dedupe rules in `auto-context.env`; add hard timeout + circuit-breaker (3x >500ms → skip rest of session via `/tmp/br3-auto-context-tripped`)
- [ ] On error: emit empty `<auto-context>` block and exit 0 (never blocks prompts)
- [ ] Flip `BR3_AUTO_CONTEXT=on` in `~/.zshrc`; log decision
- [ ] Add killswitch note to `/rules` skill

**Success Criteria:** Probe scores ≥7/10 on relevance; 100 consecutive prompts in a real session: 0 blocks and median latency regression <500ms.

**Rollback:** `unset BR3_AUTO_CONTEXT` in shell rc.

---

### Phase 4: B3 — Wire `repomix --compress` into /learn and /cluster-research

**Status:** not_started
**Files:**

- `~/.claude/commands/learn.md` (MODIFY — Step 4 around lines 239-249)
- `~/.claude/commands/cluster-research.md` (MODIFY — Step 1 around lines 20-32)
- `.buildrunner/decisions.log` (APPEND)

**Blocked by:** Phase 1

**Deliverables:**

- [ ] Edit `/learn` Step 4: when match count ≥3, `repomix --compress --include <paths> --stdout` replaces individual Reads; fallback to per-file Read when `command -v repomix` fails
- [ ] Edit `/cluster-research` Step 1: replace 6 fixed `cat` calls with single `repomix --compress --include <6-file-glob> --stdout`; identical fallback
- [ ] Measure token delta on 3 representative queries; target ≥40% reduction on ≥2/3
- [ ] Confirm `model: claude-sonnet-4-6` pin unchanged on both skill files
- [ ] Skill files mention Phase 1 dependency (CLI must be installed)

**Success Criteria:** Both skills pass smoke invocations; ≥40% token reduction on ≥2/3 probe queries.

**Rollback:** Revert skill files to prior commit (git).

---

### Phase 5: A2 — Post-phase lessons-learned hook

**Status:** not_started
**Files:**

- `~/.buildrunner/scripts/lessons-learned.sh` (NEW)
- `~/.buildrunner/scripts/autopilot-phase-hook.sh` (MODIFY)
- `~/.buildrunner/scripts/dispatch-to-node.sh` (MODIFY — optional post-SSH call after line 598)
- `/Users/byronhudson/Projects/BuildRunner3/CLAUDE.md` (MODIFY — add `BR3_PHASE_LESSONS` to native-levers table)

**Blocked by:** None

**Deliverables:**

- [ ] `lessons-learned.sh <phase_num> <total_phases> <project_root> <build_name>`: invokes `claude -p` with ~1-2k-token prompt (effort medium) emitting 10-line lessons; writes structured entry to `$project_root/.buildrunner/decisions.log` and POSTs to Jimmy `api/memory/note`
- [ ] Modify `autopilot-phase-hook.sh`: replace hard early-exit at lines 18-21 with `[[ "$BR3_PHASE_LESSONS" == "on" ]] && lessons-learned.sh "$@"; [[ "$PHASE_NUM" -lt "$TOTAL_PHASES" ]] && exit 0`
- [ ] Smoke: scratch BUILD with one fake phase — verify decisions.log entry + Jimmy note both present within 90s
- [ ] Add `BR3_PHASE_LESSONS=on/off` row to project CLAUDE.md native-levers table
- [ ] Record per-phase token cost in decisions.log

**Success Criteria:** Scratch-phase run writes valid lessons entry to both targets within 90s; token cost <3k.

**Rollback:** `unset BR3_PHASE_LESSONS` or revert hook changes (git).

---

### Phase 6: B4 — Pre-phase Repomix context bundle for autopilot

**Status:** not_started
**Files:**

- `~/.buildrunner/scripts/autopilot-dispatch-prefix.sh` (MODIFY — insert between line 115 EOF and line 117 LLMLingua block)
- `~/.buildrunner/scripts/dispatch-to-node.sh` (MODIFY — POSTURE_PREFIX assembly lines 534-544)
- `~/.buildrunner/scripts/repomix-bundle.sh` (NEW)
- `/Users/byronhudson/Projects/BuildRunner3/CLAUDE.md` (MODIFY — add `BR3_REPOMIX_BUNDLE` to native-levers table)

**Blocked by:** Phase 1, Phase 5

**Deliverables:**

- [ ] `repomix-bundle.sh <build_spec_path> <phase_num>`: parses phase `**Files:**` list, runs `repomix --compress --include <list> --stdout`, returns bundle text
- [ ] Modify `autopilot-dispatch-prefix.sh`: between line 115 (EOF) and line 117 (LLMLingua), add `if [[ "$BR3_REPOMIX_BUNDLE" == "on" ]] && command -v repomix >/dev/null; then emit repomix-bundle.sh output; fi`
- [ ] Document Repomix → LLMLingua order (AST-aware first, then prose compression) with rationale comment
- [ ] Add `BR3_REPOMIX_BUNDLE=on/off` row to project CLAUDE.md native-levers table
- [ ] Measure: one phase dispatch with and without bundle; compare token count + mid-phase file-reads (from transcript)

**Success Criteria:** With flag on, bundle appears in phase prompt; mid-session file-reads drop ≥30% on ≥1 phase; no phase-success regression.

**Rollback:** `unset BR3_REPOMIX_BUNDLE`.

---

### Phase 7: Verification — end-to-end integration run

**Status:** not_started
**Files:**

- `.buildrunner/builds/BUILD_br3-repomix-smoke-test.md` (NEW, scratch)
- `.buildrunner/logs/phase-7-verification.md` (NEW)
- `.buildrunner/decisions.log` (APPEND)

**Blocked by:** Phases 1, 2, 3, 4, 5, 6

**Deliverables:**

- [ ] Scratch `BUILD_br3-repomix-smoke-test.md` with 2 tiny phases (one terminal-build on throwaway script; one architecture on a doc)
- [ ] Run with all flags on: `BR3_AUTO_CONTEXT=on BR3_PHASE_LESSONS=on BR3_REPOMIX_BUNDLE=on`
- [ ] Capture: per-prompt auto-context latency, per-phase bundle size, per-phase lessons entry presence, any hook stderr noise
- [ ] Write `phase-7-verification.md` comparing aggregate token/latency vs all-flags-off baseline
- [ ] Decide + record: any flag worth flipping to `on` by default? Log in report
- [ ] Clean up scratch BUILD spec after verification

**Success Criteria:** All three flags fire cleanly on smoke-test BUILD; latency regression <1s/phase; lessons captured on both phases; bundle reduces phase prompt tokens ≥20%.

**Rollback:** Individual flags unset; scratch artifacts deleted.

---

## Out of Scope (Future BUILD)

- **B5 — Jimmy Tree-sitter sub-document chunking.** Separate BUILD (`BUILD_jimmy-treesitter-chunking`), deferred until ≥2 weeks after this build lands. Requires Tree-sitter grammar audit for Python/TS/JS/Go, full re-index of `/srv/jimmy/research-library/`, and `/retrieve` downtime plan. May be descoped entirely if Repomix-in-skills (B3) proves sufficient.
- **Repomix in `/research`** — multi-LLM pipeline untouched; $2/invocation budget cap and adversarial-review flow too sensitive for this wave.
- **Arbiter circuit reset** — operator task; not bundled.

## Session Log

[Will be updated by /begin]
