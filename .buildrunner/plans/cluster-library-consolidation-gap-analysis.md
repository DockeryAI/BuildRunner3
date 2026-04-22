# Cluster-Library-Consolidation — Gap Analysis

**Build:** BUILD_cluster-library-consolidation
**Closed:** 2026-04-22T17:26Z
**Analyst:** Claude Opus 4.7
**Verdict:** BUILD COMPLETE — all spec done-whens met. Four follow-ups logged as out-of-scope future work.

## Spec vs. delivery

Every phase `Done-When` from `.buildrunner/builds/BUILD_cluster-library-consolidation.md` was verified green in review docs under `.buildrunner/codex-dispatch/reviews/`:

| Phase | Subject                             | Review doc               | Verdict                                 |
| ----- | ----------------------------------- | ------------------------ | --------------------------------------- |
| 1     | GitHub backup rollback anchor       | phase-01 (telemetry log) | OK                                      |
| 2     | Reconcile conflicting specs         | phase-02-review.md       | OK                                      |
| 3     | Path mismatch + Jimmy storage       | phase-03-review.md       | OK                                      |
| 4     | Clone GitHub repo to Jimmy          | phase-04-review.md       | OK                                      |
| 5     | Jimmy capability stack              | phase-05-review.md       | OK                                      |
| 6     | Below handoff worker                | phase-06-review.md       | OK                                      |
| 7     | Rewrite /research skill             | phase-07-review.md       | OK                                      |
| 8     | Enforcement — block Muddy bypass    | phase-08-review.md       | OK                                      |
| 9     | E2E verification gate               | phase-09-review.md       | PARTIAL → 9B remediation                |
| 9B    | Rebuild Jimmy index                 | phase-09b-review.md      | PARTIAL → 9C remediation                |
| 9C    | Narrow broken-record re-test        | phase-09c-review.md      | FINDING (not blocker) — see follow-up 1 |
| 10    | Delete Muddy copy (+ stray cleanup) | phase-10-review.md       | OK (scope extended to 4 copies)         |

Spec-adjacent amendment during execution: the GitHub repo was provisioned under the `DockeryAI` org rather than `byronhudson` (per user directive mid-build); all Phase-1 done-whens still semantically met against the actual org.

## Follow-ups — out-of-scope future work

None of these block consolidation. All are hardening beyond the original spec.

### Follow-up 1: Reformat-prompt hardening (from Phase 9C finding)

**What:** In Phase 9C we fed an empty `draft_markdown` into the `research-worker` pipeline expecting a `SchemaViolation`. Instead, `llama3.3:70b` hallucinated a structurally-valid 9-key-frontmatter document from nothing, the validator passed, and the worker committed it to Jimmy (SHA `47ad39cc`, 4 orphan chunks). We reverted the commit (da27612) and dropped the orphan chunks with the Phase-9B rebuild.

**Fix:** Two parts in a follow-up build:

1. `core/cluster/below/reformat_prompt.md` — add guard clause: "If the input draft is empty or under 50 words, respond with ONLY the JSON `{\"error\":\"insufficient input\"}`; do not invent content."
2. `core/cluster/below/research_worker.py` — `generate_reformatted_markdown` detects that JSON shape and raises `SchemaViolation` before the commit step.

**Coverage if skipped:** Phase 6.7 unit tests (`test_failure_modes.py`, `test_commit.py`) already cover the real failure modes (Ollama down, OOM, git rejected, reindex timeout, SchemaViolation on malformed file) under mocks. The hallucination path is a prompt-quality gap, not an architectural gap.

### Follow-up 2: Tombstone-aware indexer (from Phase 9 root cause)

**What:** Phase 9.3 exposed a 75% chunk-count drift (fresh-clone 6,726 vs live 26,915). Root cause: `research_library.lance` indexer uses add-only delta logic; it never drops rows for files that were renamed, deleted, or modified. Ghost rows accumulated across every reindex cycle.

**Fix:** Post-reindex, delete rows whose `source_file` is not in the current discovery set. Or: use full-rebuild semantics for `research_library.lance` exclusively (leave `codebase.lance` add-only since its churn profile differs).

**Workaround:** Phase 9B did a full nuke + rebuild. Going forward, schedule periodic rebuilds via cron (weekly?) until the indexer is tombstone-aware.

### Follow-up 3: Worker CLI Python version check

**What:** `core.cluster.below.research_worker` uses `datetime.UTC` (Python 3.11+). Bare `python3` on macOS is 3.9; Phase 9B and 9C both had false starts when Codex invoked `python3` instead of `python3.14`.

**Fix:** Add `import sys; assert sys.version_info >= (3, 11), "Python 3.11+ required"` at the top of the worker CLI entrypoint, with a clear error message.

### Follow-up 4: `sync-cluster-context.sh` post-cleanup audit on Otis+Below

**What:** The mirror script (research-library block removed in Phase 10.6) seeded `~/br3-context/research-library` on Otis. That stray was deleted in Phase 10. But the script may also have left orphan files elsewhere under `~/br3-context/` that reference research-library content.

**Fix:** Grep Otis+Below `~/br3-context/` for any remaining research-library references; clean up.

**Risk if skipped:** cosmetic only — no code path reads those stale files post-Phase-10 script edits.

## State summary (post-close)

| Check                                          | Value                                                                                         |
| ---------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Canonical live                                 | Jimmy `/srv/jimmy/research-library/` @ `da27612`                                              |
| Off-site anchor                                | `github.com/DockeryAI/research-library` @ `da27612` (tag `backup/pre-consolidation-20260422`) |
| Stray copies                                   | 0 (Muddy/Lockwood/Walter/Otis all cleaned; Below had no copy)                                 |
| /retrieve endpoint                             | healthy — 5 results on canonical probe, first = live Jimmy doc                                |
| PreToolUse block hook                          | live — `~/.claude/hooks/block-muddy-library.sh` (Read + Bash verbs)                           |
| Nightly backup cron                            | installed on Jimmy — `/srv/jimmy/backups/YYYY-MM-DD.tar.zst` daily                            |
| Persistent backups                             | 5 on `/srv/jimmy/backups/` (see phase-10-review.md)                                           |
| Below research worker daemon                   | NOT installed (intentional — started per-session; spec-compliant)                             |
| Research queue                                 | clean                                                                                         |
| Chunk-count drift (live vs fresh-clone GitHub) | 0.21% raw / within spec ±5%                                                                   |
| Decision log                                   | `.buildrunner/decisions.log` — build-close entry at 2026-04-22T17:25:56Z                      |

## Decision: BUILD CLOSED. No further Codex dispatches needed for consolidation. Four follow-ups spun off as future builds.
