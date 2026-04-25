# Prior-State Survey: br3-memory-repomix-wave

## Prior BUILDs

- **BUILD_br3-cleanup-wave-abc.md** — 🚧 in_progress (Phase 7). No file overlap; cleanup wave touches import/dead-code surface, this spec touches hooks + autopilot dispatch. Safe to run concurrently.
- **BUILD_cluster-role-matrix-router.md** — complete. Defines the role-matrix resolver at `~/.buildrunner/scripts/load-role-matrix.sh`. This spec consumes that resolver but does not modify it.
- **BUILD_universal-role-routing.md** — complete. Established `autopilot-dispatch-prefix.sh` as the posture emitter. This spec inserts new content between existing emit blocks (lines 115-117) without rewriting the existing logic.
- **BUILD_research-multi-llm.md** — complete. Touches `/research` skill. This spec's B3 task edits `/learn` and `/cluster-research` but leaves `/research` pipeline untouched (deferred), avoiding collision.
- **BUILD_optimize-skill.md** — complete. Modifies skill prompt structure patterns; this spec follows same conventions (positive-examples, effort tiers, etc.) — no conflict.
- **BUILD_cluster-max.md** — complete. Established `cluster-check.sh` and node-health gating. This spec uses those APIs read-only.
- **BUILD_cluster-library-consolidation.md** — complete. Defined the "research library lives only on Jimmy" rule. Task B3 (compress source files before `/learn` and `/cluster-research` reads) respects this — Repomix compresses files it reads, it does not write to the research library.

## Shared-Surface Impact

This spec modifies **user-level shared surface** (`~/.buildrunner/`, `~/.claude/`) — changes apply to all BR3 projects, not just this repo.

- **`~/.buildrunner/hooks/auto-context.sh`** — A1 audits/enables. Already exists and is feature-gated (`BR3_AUTO_CONTEXT=on`). Other callers: UserPromptSubmit hook pipeline. Enabling it affects every Claude Code session across all projects. Mitigation: ship gate as env var, default off, flip on after quality audit.
- **`~/.buildrunner/scripts/autopilot-dispatch-prefix.sh`** — B4 inserts new block. Other callers: `dispatch-to-node.sh` line 537, all autopilot runs across all BR3 projects. Mitigation: gated on `BR3_REPOMIX_BUNDLE=on`, default off; pre-existing LLMLingua block (line 117+) is not displaced, only preceded.
- **`~/.buildrunner/scripts/dispatch-to-node.sh`** — B4 may also insert. Same blast radius as above. Mitigation: same env gate.
- **`~/.buildrunner/scripts/autopilot-phase-hook.sh`** — A2 replaces early-exit for non-final phases. All autopilot builds across all projects hit this hook. Mitigation: gated on `BR3_PHASE_LESSONS=on`, default off; current early-exit path preserved when flag off.
- **`~/.claude/settings.json`** — B2 adds `mcpServers` block (first such block; no conflict). A2/A1 do not touch this file.
- **`~/.claude/commands/learn.md` and `~/.claude/commands/cluster-research.md`** — B3 edits Step 4 and Step 1 respectively. Affects all projects. Mitigation: fallback when `repomix` binary missing, skill continues on current path.
- **`/Users/byronhudson/Projects/BuildRunner3/.claude/settings.json`** — B2 creates this file (does not exist today). Project-scoped; no cross-project impact.

## Governance Drift

- `~/.buildrunner/config/default-role-matrix.yaml` — resolver confirmed to accept buckets `terminal-build`, `backend-build`, `qa`, `architecture`. No new buckets introduced.
- Global CLAUDE.md rule: "Research library: Jimmy only." Task B3 respects this (Repomix reads source files before they enter context; does not write to research library).
- Global CLAUDE.md rule: "Retrieval pins (/learn, /research, /cluster-research) stay on Sonnet 4.6." B3 edits these skill files but does NOT change the model pin. Must be enforced in phase deliverables.
- `task-budgets-2026-03-13` 20k token floor — A2 adds ~1-2k tokens per phase for lessons capture; well under floor. Not a drift risk.
- Claude 4.7 deprecated params (`temperature`, `top_p`, `budget_tokens`, etc.) — none touched by this spec.

## Completed-Phase Blast Radius

No completed phase from any prior BUILD re-modifies the same lines this spec touches. Specifically:

- `autopilot-dispatch-prefix.sh` line 115-117: last modified by BUILD_universal-role-routing.md; new insertion preserves that boundary.
- `autopilot-phase-hook.sh` lines 18-21: established by BUILD_ship-self-healing-prepush.md; new code replaces the early-exit under flag gate only, preserving existing ship behavior for final phase.
- `~/.claude/commands/learn.md` Step 4 (lines 239-249): last modified by BUILD_research-multi-llm.md; edit inserts new branch, does not rewrite existing Read loop.

No locked phases disturbed. Clean.
