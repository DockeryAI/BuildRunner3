# Runtime Cluster Architecture

**Date:** 2026-04-15
**Phase:** 3
**Status:** complete_local_only

## Purpose

Lock the V1 BR3 runtime-dispatch model before broader adapter work continues.

The decision for Phase 3 is:

- V1 Codex cluster execution model remains `codex exec` on the target node.
- BR3 continues to own dispatch, sidecar monitoring, heartbeat, cancellation, and exit reporting.
- Codex remains local-only after Gate B because remote node readiness is not yet reliable.

## V1 Execution Model

1. `dispatch-to-node.sh` selects the primary runtime from `BR3_RUNTIME` and an optional advisory runtime from `BR3_SHADOW_RUNTIME`.
2. Before sync or launch, BR3 runs `check-runtime-auth.sh` on the target node for the primary runtime in `direct` mode.
3. If a shadow runtime is configured, BR3 runs a second preflight in `shadow` mode.
4. Direct Codex preflight failure blocks dispatch. During migration, direct Claude preflight is advisory-only so the live default route is not changed by Phase 3. Shadow preflight failure records `shadow_skipped` and does not silently reroute the task.
5. After preflight passes, BR3 launches the selected runtime through `build-sidecar.sh` on the target node.

## Sidecar Ownership

V1 does not introduce a new Codex daemon. The existing BR3 sidecar remains the monitored wrapper.

- The sidecar launches one runtime child process and tracks its PID and PGID.
- For Codex runs, the monitored child is the `codex exec ...` process launched by the sidecar.
- Heartbeats are written to `.buildrunner/locks/phase-N/heartbeat` every 15 seconds and mirrored to the dashboard as `build.heartbeat`.
- Exit state is written to `.buildrunner/locks/phase-N/exit-status.json`.
- Cancellation means killing the monitored runtime process group. Runtime selection is immutable for the life of a task.

Implementation note:

- `build-sidecar.sh` still uses legacy field names like `claude_pid` and `claude_pgid`. In V1 Codex dispatch, those fields identify the active runtime child until a later schema cleanup phase renames them.

## Auth and Compatibility Policy

Runtime preflight is now BR3-owned and uses `core/cluster/cross_model_review.py` as the shared helper for:

- CLI availability
- version compatibility
- local auth presence
- minimal runtime probe

V1 Codex policy is explicit:

- Direct `runtime=codex` dispatch failure is `fail_fast`.
- Shadow Codex failure is `shadow_skipped`.
- BR3 does not silently reroute a failed Codex task to Claude.
- Mid-run auth expiry fails the current direct task. In advisory shadow mode it records a skipped advisory result. Runtime never changes mid-task.

Validated Codex range:

- `>= 0.48.0`
- `< 0.49.0`

## Remote Preflight Mechanics

`check-runtime-auth.sh` now ships the current local `cross_model_review.py` helper to the target node before invoking remote preflight. This prevents stale remote BR3 checkouts from making preflight decisions with older logic.

That closes the mismatch seen earlier on Lomax, where the remote checkout lacked the new `--runtime-preflight` CLI.

## Node Readiness Snapshot

Measured on 2026-04-15:

| Node | Codex | Claude | Repo helper | Result |
| --- | --- | --- | --- | --- |
| Muddy / local | `codex-cli 0.48.0` | `2.0.31` | current | pass |
| Lockwood | missing | missing | missing | not eligible |
| Otis | missing | `2.1.92` | present | Claude-only |
| Lomax | `codex-cli 0.47.0` | `2.1.96` | present | no-go for Codex |

## Probe Results

### Muddy / local Codex

Command:

```bash
codex --ask-for-approval never exec --skip-git-repo-check -- "reply with only: ok"
```

Observed result:

- exit code `0`
- stdout `ok`
- version `codex-cli 0.48.0`

### Lomax remote Codex

Command:

```bash
ssh byronhudson@10.0.1.104 'zsh -lc '\''cd ~/repos/BuildRunner3 && /opt/homebrew/bin/codex --ask-for-approval never exec --skip-git-repo-check -- "reply with only: ok"'\'''
```

Observed result:

- exit code `1`
- version `codex-cli 0.47.0`
- repeated `Re-connecting... 1/5` through `5/5`
- terminal error `Failed to refresh token: 401 Unauthorized`

This remote result is not reliable enough for BR3 execution ownership.

## Phase 1 / Phase 3 Sync Memo

Phase 1 proved that BR3 can run isolated Claude and Codex shadow review locally through one shared task envelope without touching live routing.

Phase 3 adds the missing dispatch reality:

- remote nodes have install drift
- remote nodes have version drift
- remote nodes have auth drift
- remote repo checkouts may lag the local control-plane helper

Reconciled conclusion:

- the Phase 1 local isolated shadow model is valid
- the same assumption does not yet hold for remote Codex nodes
- BR3 must preflight runtime availability before sync and launch
- remote Codex stays disabled until a target node matches the validated version range, has working auth, and returns a stable probe result

## Gate B Decision

**Gate B:** complete_local_only_no_go_remote

Remote Codex execution is not approved after Phase 3.

Reason:

- Muddy/local meets the validated baseline.
- Lomax is the only remote node exposing Codex and fails both version compatibility and live auth refresh.
- Otis and Lockwood do not currently provide an eligible Codex target.

## Next Safe Step

Proceed to Phase 4 runtime contract and result/edit normalization work.

Do not enable remote Codex routing or cutover behavior before a future phase revalidates a remote node against the pinned version, auth, and probe baseline.
