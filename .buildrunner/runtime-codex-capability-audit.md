# Codex Runtime Capability Audit

Date: April 15, 2026
Source of truth: direct local probes against `codex-cli 0.48.0` on `/Users/byronhudson/Projects/BuildRunner3`

## Validated Surface

- CLI version observed: `codex-cli 0.48.0`
- Validated compatibility range pinned for BR3 Phase 0: `>= 0.48.0, < 0.49.0`
- Primary non-interactive entrypoint: `codex exec`
- Required approval flag placement: `codex --ask-for-approval never exec ...`
- Validated `exec` flags in current surface:
  - `--json`
  - `--skip-git-repo-check`
  - `--sandbox workspace-write`
  - `--cd <DIR>`
  - `--output-last-message <FILE>`
- `--output-schema <FILE>` is present in CLI help, but Phase 0 did not validate it as a stable review path. Two schema-constrained review attempts exited non-zero with repeated stream-disconnect warnings, so BR3 does not rely on it in the Phase 0 baseline.

## Auth Model

- V1 auth source matches the build spec: local per-node `~/.codex/auth.json`
- Observed auth file shape on the validating node:
  - top-level keys: `OPENAI_API_KEY`, `last_refresh`, `tokens`
  - token keys: `access_token`, `account_id`, `id_token`, `refresh_token`
- Measured local failure signatures:
  - missing file: `Codex not authenticated. Run: codex`
  - corrupt JSON: `Codex auth.json corrupted. Run: codex`
  - missing access token: `Codex tokens missing. Run: codex`
  - expired auth probe: mapped to `Codex auth expired. Run: codex`

## Output And Streaming

- Plain `codex exec -- <prompt>` does not produce a clean machine-only payload. It emits a transcript-like response with banner, prompt echo, assistant output, and token summary.
- `codex exec --json` emits structured JSONL lifecycle events.
- Observed event types:
  - `thread.started`
  - `turn.started`
  - `item.completed`
  - `turn.completed`
- The current JSON event stream is not token-by-token content streaming.
- Measured behavior:
  - first JSON event on a trivial probe arrived in `0.061s`
  - final review content arrived only as completed message items, not incremental tokens

## Timeout And Review Payload Findings

- Trivial non-review probe:
  - prompt: `reply with only READY`
  - mode: plain `exec`
  - duration: `1.431s`
- Tiny synthetic review prompt on the final JSON-mode code path:
  - prompt size: `2571` chars
  - result: completed
  - duration: `10.859s`
  - usage: `7154` input tokens, `299` output tokens
- Representative BR3 review prompts assembled with the current review template and BUILD context were rerun sequentially through the final JSON-mode helper and still did not complete inside the current budgets:
  - small repo diff: `5079` prompt chars, `1` file, timed out after `60s`
  - medium repo diff: `9254` prompt chars, `11` files, timed out after `90s`
  - large repo diff: `12179` prompt chars, `6` files, timed out after `90s`

## Phase 0 Conclusion

- Codex local execution is working.
- Codex auth and version checks are observable and now preflightable.
- The original BR3 review shape was not reliable because Codex treated review as an open-ended agent session and explored the workspace.
- A parallel, non-disruptive fix pass proved a stable pattern:
  - isolate review execution from the repository workspace
  - narrow BUILD context to only relevant sections
  - batch multi-file diffs
  - chunk oversized single-file new-file diffs by added-line slices
- This fix pass was run in isolated probes only. The active BR3 review helper was restored so current infrastructure remains unchanged until cutover.
- Go / No-Go Gate 0 result after the isolated fix pass: `CONDITIONALLY_GO` for Phase 1 design work, with the requirement that any Codex execution path use isolated, batched review inputs rather than the old open-workspace review shape.
