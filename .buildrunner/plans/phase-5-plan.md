# Phase 5 Plan: Adversarial Review Dispatch

## Tasks

1. **Create adversarial-review.sh** — Shell script with argument parsing (plan file, project root, optional target node defaulting to otis)
2. **Implement Otis online path** — Use cluster-check.sh to detect Otis, SSH + rsync plan file, run `claude --print` with adversarial prompt, capture JSON output
3. **Implement Otis offline fallback** — Output adversarial prompt to stdout for local subagent consumption
4. **Build adversarial prompt** — Target measured failure modes: requirement conflicts (43.53%), fabricated APIs (20.41%), broken execution order, missing edge cases, nonexistent files
5. **Add timeout + exit codes** — `timeout 180` on SSH command, exit 0 = review complete, exit 1 = timeout/error
6. **Output format** — JSON array of `{finding, severity}` with blocker/warning/note levels

## Tests

- Verify script is executable and accepts correct args
- Verify offline fallback produces valid prompt text
- Verify exit codes
