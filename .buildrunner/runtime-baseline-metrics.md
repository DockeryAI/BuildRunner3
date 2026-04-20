# Codex Runtime Baseline Metrics

Date: April 15, 2026
Environment: local BR3 repo on Muddy, `codex-cli 0.48.0`

## Baseline Table

| Workload | Prompt chars | File count | Result | Duration | Notes |
| --- | ---: | ---: | --- | ---: | --- |
| Trivial exec probe | 21 | 0 | complete | 1.431s | Plain `exec`, final transcript output |
| Trivial exec JSON probe | 21 | 0 | complete | 2.215s | First event at 0.061s, lifecycle JSON only |
| Synthetic tiny review | 2571 | 1 synthetic file | complete | 10.859s | Final stable JSON-mode code path returned structured findings |
| Representative small BR3 review | 5079 | 1 | timeout | 61.702s | Sequential final-path run on `git show 8eda4b3966` |
| Representative medium BR3 review | 9254 | 11 | timeout | 92.537s | Sequential final-path run on `git show 1f15f1138d` |
| Representative large BR3 review | 12179 | 6 | timeout | 91.868s | Sequential final-path run on `git show 792c86e0aa` |
| Forced timeout control | n/a | n/a | timeout | 1.000s budget | `RuntimeError: Codex timed out after 1s` |
| Schema-constrained synthetic review retry | 2571 | 1 synthetic file | exit 1 | 11.114s, 10.502s | Repeated `stream disconnected - retrying turn` warnings |

## Parallel Fix Pass

These measurements were gathered in isolated one-off probes only. They are not wired into the live BR3 review helper.

| Workload | Prompt chars | Batch shape | Result | Duration | Notes |
| --- | ---: | --- | --- | ---: | --- |
| Real BR3 small diff, isolated | 4159 | 1 file | complete | 35.965s | Completed once workspace access was removed |
| Real BR3 medium diff, isolated | 4166-4991 | 4 file batches | complete | 35.449s / 54.940s / 9.977s / 30.436s | All four batches completed under 60s |
| Real BR3 large diff, isolated | 3524-9985 | 6 file batches | partial | 5 of 6 completed | One large new-file skill diff still timed out |
| Oversized single-file retry, isolated | 7877 | 1 file | timeout | 60.005s | `.buildrunner/skills-staging/2nd-SKILL.md` |
| Oversized single-file line chunks, isolated | 3114-4518 | 4 line chunks | complete | 52.157s / 48.945s / 42.184s / 18.343s | New-file chunk slicing cleared the last timeout |

## Auth Validation Metrics

- `--check-auth` passes on the validating node.
- Missing `~/.codex/auth.json` returns a deterministic failure.
- Corrupt `auth.json` returns a deterministic failure.
- Missing `tokens.access_token` returns a deterministic failure.

## Baseline Implications

- Current `60s` Codex review timeout is not safe for representative BR3 diff-plus-spec review payloads.
- Even `90s` is not sufficient for the representative medium and large sequential review workloads measured in Phase 0.
- JSON mode is usable for observability and final message extraction.
- JSON mode should be treated as buffered lifecycle reporting, not true streaming token output.
- The CLI's schema-output flag is not stable enough yet to treat as the BR3 review contract.
- Approximate direct per-run Codex CLI cost remains unmetered at the CLI layer, so BR3 logs this as `0.0` with explicit local-CLI cost basis metadata.
- The reliable pattern is not “increase the timeout.” The reliable pattern is isolated execution plus batching and, for oversized new-file diffs, line-chunking.

## Gate Decision

- Original Phase 0 Gate: `NO-GO`
- After isolated fix pass: `CONDITIONALLY_GO`
- Condition: any Codex path taken into later phases must keep the live BR3 infrastructure untouched until cutover and must use isolated, batched review inputs instead of the old open-workspace review shape.
