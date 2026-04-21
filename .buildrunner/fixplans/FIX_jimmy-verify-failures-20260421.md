# Fix Plan — jimmy-verify.sh 4-Failure Corrective Run

**Date:** 2026-04-21
**Source:** Follow-on to BUILD_cluster-max-research-library (already COMPLETE)
**Do NOT edit:** `.buildrunner/builds/BUILD_cluster-max-research-library.md`
**Target Executor:** Codex (terminal-delegation via `/codex-do`)
**Success Gate:** `~/.buildrunner/scripts/jimmy-verify.sh` exits 0 with zero `FAIL:` lines.
**Canonical direction:** Muddy → Jimmy. Never rsync the other way.

## Environment

- Muddy: local machine, Darwin, user `byronhudson`.
- Jimmy: `byronhudson@jimmy` (10.0.1.106), Linux (systemd), passwordless `sudo -n`.
- SSH discipline: never pipe SSH output to `head/tail/grep/awk/sed`. Redirect to a file first (e.g. `ssh jimmy 'cmd' > /tmp/out 2>&1; cat /tmp/out`). Fork-exhaustion incident: `~/.buildrunner/incidents/2026-04-20-fork-exhaustion.md`.

## Inputs (paths you may need)

- Muddy AGENTS.md source: `/Users/byronhudson/Projects/BuildRunner3/AGENTS.md`
- Jimmy AGENTS.md target: `/home/byronhudson/AGENTS.md`
- Muddy launchd plist: `/Users/byronhudson/Library/LaunchAgents/com.buildrunner.nightly-backup.plist`
- Muddy backup script: `/Users/byronhudson/.buildrunner/scripts/nightly-projects-backup.sh`
- Muddy backup log: `/Users/byronhudson/.buildrunner/logs/nightly-backup.log`
- Jimmy unit: `br3-semantic.service` (systemd)
- Verify script (gate): `/Users/byronhudson/.buildrunner/scripts/jimmy-verify.sh`
- Sync script (canonical): `/Users/byronhudson/.buildrunner/scripts/sync-muddy-to-jimmy.sh`
- Decisions log: `/Users/byronhudson/Projects/BuildRunner3/.buildrunner/decisions.log`

---

## Task 1 — Sync AGENTS.md Muddy → Jimmy (SHA match)

**Problem:** `jimmy-verify.sh` Check 8 reports SHA mismatch between local and remote AGENTS.md.
Evidence: `local=df1450c22a4cd30e8f9b312d65d302a08b7c97988b2a8eacaf4f170236275bf8`, `remote=7ecb9ac4aab0aba4ea93d8126ccea7caa734e7b61c30257e077ac23eb6818bca`.

**Steps:**

1. Compute local SHA:
   - `shasum -a 256 /Users/byronhudson/Projects/BuildRunner3/AGENTS.md > /tmp/agents-local.sha`
   - `cat /tmp/agents-local.sha`
2. Copy Muddy → Jimmy using scp (one-way; canonical direction):
   - `scp /Users/byronhudson/Projects/BuildRunner3/AGENTS.md byronhudson@jimmy:/home/byronhudson/AGENTS.md`
3. Verify remote SHA:
   - `ssh byronhudson@jimmy 'sha256sum /home/byronhudson/AGENTS.md' > /tmp/agents-remote.sha 2>&1`
   - `cat /tmp/agents-remote.sha`
4. Fail-closed: the hex string in `/tmp/agents-remote.sha` must equal the hex in `/tmp/agents-local.sha`. If not, stop and escalate — do NOT proceed to Task 2 unless they match.

**DO NOT:** edit AGENTS.md on Jimmy; never rsync Jimmy→Muddy.

---

## Task 2 — Enable and start `br3-semantic` on Jimmy

**Problem:** `jimmy-verify.sh` Check 5 reports `br3-semantic` inactive; Check 6 reports port 8100 `/api/search` not responding.

**Steps:**

1. Check current unit state and config:
   - `ssh byronhudson@jimmy 'systemctl status br3-semantic --no-pager; echo ---; systemctl cat br3-semantic --no-pager' > /tmp/semantic-before.out 2>&1`
   - `cat /tmp/semantic-before.out`
   - If the unit file is missing, STOP — do not create one; escalate. The unit was provisioned in an earlier phase; missing means drift, not a bug to paper over.
2. Enable + start:
   - `ssh byronhudson@jimmy 'sudo -n systemctl enable --now br3-semantic' > /tmp/semantic-enable.out 2>&1`
   - `cat /tmp/semantic-enable.out`
3. Verify active + listening:
   - `ssh byronhudson@jimmy 'systemctl is-active br3-semantic; ss -ltn sport = :8100' > /tmp/semantic-active.out 2>&1`
   - `cat /tmp/semantic-active.out` — expect `active` and a listener on 8100.
4. Probe endpoint from Muddy (expect HTTP 200; if endpoint returns method-not-allowed on GET, test with the minimal POST shape the service expects — first read the unit's `ExecStart` in `/tmp/semantic-before.out` to identify the framework, then probe accordingly):
   - `curl -sS -o /tmp/semantic-curl.body -w 'HTTP=%{http_code}\n' http://10.0.1.106:8100/api/search > /tmp/semantic-curl.out 2>&1`
   - `cat /tmp/semantic-curl.out`
5. If the service fails to start, capture journal:
   - `ssh byronhudson@jimmy 'sudo -n journalctl -u br3-semantic --no-pager -n 200' > /tmp/semantic-journal.out 2>&1`
   - `cat /tmp/semantic-journal.out`
   - Report the first error line; do not invent fixes.

---

## Task 3 — Register `com.buildrunner.nightly-backup` with launchd on Muddy

**Problem:** `jimmy-verify.sh` Check 9 reports the backup timer is not enabled on Muddy. Muddy is Darwin, so this is a launchd plist (not a systemd timer despite the check name).

**Steps:**

1. Confirm plist exists:
   - `ls -la /Users/byronhudson/Library/LaunchAgents/com.buildrunner.nightly-backup.plist`
   - If missing, STOP — escalate; do not generate a new plist.
2. Load (bootstrap) and enable:
   - `launchctl bootstrap gui/$(id -u) /Users/byronhudson/Library/LaunchAgents/com.buildrunner.nightly-backup.plist 2>&1 | tee /tmp/nb-bootstrap.out`
   - If bootstrap reports "service already loaded", run `launchctl bootout gui/$(id -u)/com.buildrunner.nightly-backup` first, then bootstrap again.
   - `launchctl enable gui/$(id -u)/com.buildrunner.nightly-backup 2>&1 | tee /tmp/nb-enable.out`
3. Verify scheduled:
   - `launchctl print gui/$(id -u)/com.buildrunner.nightly-backup > /tmp/nb-print.out 2>&1`
   - `cat /tmp/nb-print.out`
   - Expect entries for `state = not running`/`waiting`, a `StartCalendarInterval` block, and `path = /Users/byronhudson/Library/LaunchAgents/com.buildrunner.nightly-backup.plist`.

---

## Task 4 — Fix nightly backup rsync exit 23 (exclude vanishing paths)

**Problem:** Last run exited 23. Evidence from `/Users/byronhudson/.buildrunner/logs/nightly-backup.log`: rsync error after 3 partial-transfer warnings under `workfloDock/vendor/bundle/ruby/2.6.0/gems/nkf-0.2.0/...`. These are build-vendor artifacts that rebuild mid-rsync; excluding them is the correct remediation.

**Steps:**

1. Open `/Users/byronhudson/.buildrunner/scripts/nightly-projects-backup.sh`. Find the existing rsync invocation or `EXCLUDES`/`--exclude` list. Do not invent a new list.
2. Add these excludes to the existing list (exact order, preserve the script's current style — argv array, `--exclude-from` file, or inline flags):
   - `workfloDock/vendor/bundle`
   - `**/vendor/bundle`
   - `**/node_modules/.cache`
   - `**/.bundle`
3. If the script reads an `--exclude-from` file, append the same patterns to that file instead; do not duplicate.
4. Run the backup in smoke mode first to confirm the script parses cleanly:
   - `bash /Users/byronhudson/.buildrunner/scripts/nightly-projects-backup.sh --smoke > /tmp/nb-smoke.out 2>&1; echo EXIT=$?`
   - `cat /tmp/nb-smoke.out`
   - Require `EXIT=0` and a non-empty log tail.
5. Kick a full fresh run via launchd:
   - `launchctl kickstart -k gui/$(id -u)/com.buildrunner.nightly-backup`
   - Tail the log until completion (wait ~5 min; poll every 60s):
     - `tail -n 50 /Users/byronhudson/.buildrunner/logs/nightly-backup.log > /tmp/nb-tail.out 2>&1`
     - `cat /tmp/nb-tail.out`
   - Require the final line to match "backup complete" and contain "0 errors" (or an explicit exit 0).
6. Re-run the health script:
   - `bash /Users/byronhudson/.buildrunner/scripts/nightly-backup-health.sh > /tmp/nbh.out 2>&1; echo EXIT=$?`
   - Require `EXIT=0`.

---

## Task 5 — Final gate: re-run jimmy-verify.sh

**Steps:**

1. `bash /Users/byronhudson/.buildrunner/scripts/jimmy-verify.sh > /tmp/jv-after.out 2>&1; echo EXIT=$?`
2. `cat /tmp/jv-after.out`
3. Required: `EXIT=0` and zero `FAIL:` lines. Count with:
   - `grep -c '^.*FAIL:' /tmp/jv-after.out`
   - Must print `0`.
4. If any check still fails, stop and report the failing check IDs (Check 1..13) with their log line — do not attempt additional fixes outside Tasks 1–4.

---

## Task 6 — Log the corrective run

**Steps:**

1. Append exactly one line to `/Users/byronhudson/Projects/BuildRunner3/.buildrunner/decisions.log`:
   - Format: `2026-04-21 <HH:MM:SSZ> corrective-run jimmy-verify 4-check fix: AGENTS.md synced, br3-semantic up, nightly-backup scheduled + clean; jimmy-verify exit 0`
2. Do NOT edit `.buildrunner/builds/BUILD_cluster-max-research-library.md`. Do NOT commit. Leave staging for a human to review.

---

## Hard rules for execution

- Never rsync Jimmy → Muddy. Canonical direction is Muddy → Jimmy.
- Never edit files on Jimmy that are owned by the canonical tree; sync them from Muddy.
- Always redirect SSH output to `/tmp/*.out` before reading; never pipe SSH to head/tail/grep/awk/sed.
- Use `sudo -n` on Jimmy (passwordless). If it prompts, stop — means sudoers bootstrap regressed.
- Do not generate new unit files, plists, or scripts. If an input is missing, escalate.
- Do not mark the BUILD spec. This is a corrective run, not a new phase.
- Success gate is a single command: `jimmy-verify.sh` exit 0 with zero `FAIL:` lines. All other verification is support, not gate.
