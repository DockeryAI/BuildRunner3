# Phase 3 Plan: Skill Write-Back to Lockwood

## Approach

Add a Lockwood POST step at the end of each of these 6 skills so that useful findings are saved as institutional memory. Each skill already uses `cluster-check.sh` for reads — we add a write-back at the end.

Pattern (from /save which already does this):
```
NODE_URL=$(~/.buildrunner/scripts/cluster-check.sh semantic-search)
[ -n "$NODE_URL" ] && curl -s -X POST "$NODE_URL/api/memory/note" ...
```

All write-backs are optional (graceful fallback if Lockwood offline).

## Tasks

1. **root.md** — After Step 5 (report), POST root cause summary + full report to Lockwood with topic "root-cause: {summary}", source "root"
2. **guard.md** — After Step 4 (report), POST violations found to Lockwood with topic "governance-violation: {summary}", source "guard"
3. **review.md** — After Step 3 (auto-fix), POST review findings to Lockwood with topic "review-findings: {summary}", source "review"
4. **gaps.md** — After Step 4 (report), POST gap analysis results to Lockwood with topic "gap-analysis: {summary}", source "gaps"
5. **dead.md** — After Step 3 (report), POST dead code findings to Lockwood with topic "dead-code: {summary}", source "dead"
6. **e2e.md** — After Step 5 (report), POST test results to Lockwood with topic "e2e-results: {summary}", source "e2e"

## Tests

Non-testable (markdown skill files, no runtime code). TDD step skipped.
