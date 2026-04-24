# Verify Report — burnin-harness-reliability

**Date:** 2026-04-24
**Runner:** Claude Opus 4.7 (Phase 6 = Codex per role-matrix; inline execution under /autopilot go)
**Build:** `.buildrunner/builds/BUILD_burnin-harness-reliability.md` (Phases 1–5 already ✅ COMPLETE)

## Summary

All five Phase 6 success checks are green. The burn-in harness is
autonomous end-to-end: the stuck case is unstuck, the passthrough
contract holds, the fix loop has a working timeout, the state
machine has a reaper escape hatch, and the watchd LaunchAgent is
resident with reaper + fswatch sidecars.

## Check Matrix

| #   | Check                          | Command                                                                                            | Expected                                                          | Actual                                                                                               | Result   |
| --- | ------------------------------ | -------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | -------- | --- |
| 1   | cluster-check passthrough case | `burnin run sharding-cluster-check-passthrough`                                                    | PASS; state=probation                                             | `PASS  state=probation`                                                                              | ✅       |
| 2   | dashboard-chip case            | `burnin run sharding-dashboard-chip`                                                               | PASS; state=probation                                             | `PASS  state=probation`                                                                              | ✅       |
| 3   | `--untested` sweep             | `burnin run --untested`                                                                            | All untested cases get a first run                                | `No untested cases.` (Phase 4 sweep already moved all 43 untested cases; current untested count = 0) | ✅       |
| 4   | Hang-simulation                | `BR3_BURNIN_FIX_CLAUDE_CMD='sleep 600' BR3_BURNIN_FIX_TIMEOUT_S=10 burnin fix walter-trigger-logs` | exits ~15–35s; case in `needs_human`; 3 rows `resolver='timeout'` | 32s elapsed; `needs_human`; fix_requests 110/111/112 all `failed                                     | timeout` | ✅  |
| 5   | Zero stale fixing              | `burnin status` + direct SQL for fixing>30min                                                      | 0                                                                 | 0                                                                                                    | ✅       |

## Observed Case-State Distribution (post-Phase-6)

```
fixing    | 36
needs_human |  1   (walter-trigger-logs from hang-sim)
probation |  9
promoted  |  5
```

The 36 cases currently in `fixing` are from the Phase 4 untested
sweep with `BR3_BURNIN_AUTOHEAL=off`: they transitioned
`untested → fixing`, each had its `requested` stub reconciled to
`aborted/skipped` by the Phase 5 revision backfill, and they now
have no pending fix_requests. They are all < 30 minutes old at
report time; the watchd reaper tick (every 5 minutes, threshold
30 minutes) will flip them to `needs_human` as they age out. This
is the designed behavior — the reaper exists precisely to drain
stuck `fixing` cases that no autoheal or external actor is
resolving.

## Residual `needs_human` Cases for Operator Follow-up

- **walter-trigger-logs** — produced by the Phase 6 hang-simulation
  smoke test (three forced `resolver='timeout'` rows). Not a real
  failure; operator can `burnin reset walter-trigger-logs` to re-run.

Additional `needs_human` cases will appear over the next ~30 minutes
as the watchd reaper sweeps the current `fixing` cohort (see above).
These represent untested sharding cases that have not yet had a
real fix attempt; expected operator action is to re-enable
autoheal (`BR3_BURNIN_AUTOHEAL=on`) or provide fixes manually.

## Evidence Artifacts

- Smoke outputs captured above (tails from each command).
- Adversarial review: `.buildrunner/adversarial-reviews/burnin-harness-fix-review.md`
  — APPROVE after revision pass (Finding 10 blocked; `db_record_fix_skip`
  refactor + 37-row backfill reconciled all orphan stubs to zero).
- Watchd LaunchAgent: `launchctl list com.buildrunner.burnin-watchd`
  reports PID 96735, LastExitStatus 0; first reaper tick logged in
  `~/.buildrunner/burnin/watchd.log` at 14:59:23Z on 2026-04-24.
- fix_requests orphan-stub check:
  `SELECT COUNT(*) FROM fix_requests WHERE status IN ('requested','proposed');`
  → `0`.

## Conclusion

Build `burnin-harness-reliability` is complete. All success criteria
in Phase 6 are satisfied. The harness can recover autonomously from
stuck `fixing` cases, the fix loop cannot hang indefinitely on a
wedged `claude` invocation, and the passthrough case no longer
trips the Phase 2 contract.
