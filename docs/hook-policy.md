# Hook Policy

BuildRunner 3 replaces detected BR2 `brandock-spec` hooks instead of chaining them. Earlier chained-hook setups were unreliable and could mask the real non-zero exit code, which made failed checks look like successful pushes or commits. The Phase 2 installer keeps a backup for recovery, then installs the enforced BR3 hooks as the only active `.git/hooks/pre-commit` and `.git/hooks/pre-push` entrypoints.

The canonical fragment location for push-time extensions is `.git/hooks/pre-push.d/`. That location is authoritative because `.buildrunner/hooks/pre-push-enforced` runs fragments from `$(dirname "$0")/pre-push.d`, which resolves to the live git hook directory, not the repo asset directory. BR3 installs `50-ship-gate.sh` there so the enforced hook can execute it in lexical order.

When the installer detects a legacy BR2 hook, it copies that hook to `.buildrunner/hooks/legacy/<hookname>.<utc-iso-ts>`. Backups are append-only snapshots named with the UTC ISO timestamp used at install time, so multiple migrations in the same repo preserve their audit trail instead of overwriting each other.

For emergency pushes, the supported bypass is `BR3_SHIP_BYPASS_PREPUSH=1`. That bypass is implemented inside the shipped `pre-push.d/50-ship-gate.sh` fragment and is intended only for break-glass situations.
