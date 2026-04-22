# Gap Analysis + Fix Order — cluster-max-research-library runtime reality

**Date:** 2026-04-22
**Scope:** Full audit of BUILD_cluster-max-research-library vs. live cluster state. The BUILD spec is marked COMPLETE across 7 phases, but the user confirmed the system is not actually working end-to-end. Do not trust the spec's checkmarks — verify each promised capability against live behavior and enumerate every gap.
**Do NOT edit:** `.buildrunner/builds/BUILD_cluster-max-research-library.md`. The spec is frozen. All corrective actions land outside it.
**Target Executor:** Codex (agentic terminal executor)

## Ground Truth — what has to actually work

1. `/research <query>` returns non-empty, scrubbed (no `[private]` lines) results that came from Jimmy's LanceDB research_library table, with source paths and line ranges.
2. `POST http://10.0.1.106:8100/api/search` (or `/retrieve`, whichever the plan canonicalized) returns real hits against `/srv/jimmy/lancedb/research_library.lance`.
3. Embedder on Jimmy works offline — the `sentence-transformers/all-MiniLM-L6-v2` model is cached locally, does not attempt HuggingFace fetch at runtime, and loads inside the service process.
4. `~/.buildrunner/scripts/reindex-research.sh` rebuilds the `research_library` LanceDB table from `/srv/jimmy/research-library/` end-to-end with a real chunk count and a sample-query sanity check.
5. `core.cluster.node_semantic:app` on Jimmy is the ONLY thing listening on port 8100. No orphan uvicorns. Unit survives `systemctl restart` without manual cleanup.
6. Nightly backup exits 0 with zero `rsync error` lines; `nightly-backup-health.sh` returns 0.
7. `launchctl print gui/$(id -u)/com.buildrunner.nightly-backup` on Muddy shows a loaded, scheduled job.
8. AGENTS.md on Jimmy matches the canonical source (`~/.buildrunner/agents-md/jimmy.md`) byte-for-byte.
9. `BR3_AUTO_CONTEXT` is the only flag name in code + docs; `BR3_MULTI_MODEL_CONTEXT` grep returns zero.
10. `private_filter.filter_private_lines` is applied on BOTH `/context` AND `POST /retrieve` before any row leaves the server.
11. `core/cluster/context_bundle.py` uses bge cross-encoder reranking for candidates — not a 30-day mtime glob.
12. `jimmy-verify.sh` exits 0 because the underlying reality is correct, not because the script was softened.

## Known-bad starting state (as of 2026-04-22 00:05 UTC)

- `br3-semantic` log shows: `ERROR ... We couldn't connect to 'https://huggingface.co' to load the files, and couldn't find them in the cached files.` for `sentence-transformers/all-MiniLM-L6-v2`. Indexer is disabled (`DISABLE_INDEXER=true` observed in logs). Retrieval returns `{"results":[],"error":"Indexer disabled — semantic search unavailable"}`.
- An orphan uvicorn (pid 65943, killed earlier) had been holding port 8100 outside systemd's control — suggests prior manual starts or incomplete deploy hygiene that can recur.
- `/api/search` is POST-only; `/health` is GET. An earlier GET check was masking failures. Do not rely on `/health` alone to prove retrieval works — test POST with a real query.
- `nightly-backup-health.sh` still reports 4 rsync errors in the 24h window (pre-fix entries). The last backup run itself exited 0.
- `jimmy-verify.sh` was patched today to branch on OS (Check 9) and to use `/health` for Check 6. Those patches are correct, but if the underlying retrieval is broken, Check 6 now lies by design. Do not revert — extend verification with a Check 6b that proves POST retrieval returns a hit against a known-present corpus.

## Constraints (hard — do not violate)

- Canonical sync direction: Muddy → Jimmy. Never the other way.
- SSH output MUST be redirected to `/tmp/*.out` files. Never pipe SSH output through `head/tail/grep/awk/sed` (fork-exhaustion incident: `~/.buildrunner/incidents/2026-04-20-fork-exhaustion.md`). Inside the remote command is fine; on the Muddy side of the pipe is not.
- Jimmy: `byronhudson@jimmy` (10.0.1.106), Linux, passwordless `sudo -n`.
- Muddy: local Darwin.
- Use `.venv/bin/python` at `/home/byronhudson/repos/BuildRunner3/.venv` on Jimmy for any python invocation that must match the service's environment.
- Do NOT edit `.buildrunner/builds/BUILD_cluster-max-research-library.md`. Do NOT commit or push. Append to `.buildrunner/decisions.log` at the end.

## Deliverable 1 — Gap Report

Produce a gap report at `.buildrunner/fixplans/GAP_REPORT-20260421.md`. For EACH of the 12 ground-truth items above, include:

```
### GT-<n>: <one-line summary>
- expected: <what the plan says should work>
- actual: <what you observed, with file/command evidence>
- severity: critical | high | medium | low
- gap: <concrete description of the delta>
- fix: <one-line remediation direction>
```

Do not skip items. If an item passes, mark it `status: PASS` with evidence and move on. Enumerate unfiltered first; rank second.

## Deliverable 2 — Fix Execution

After the report is written, execute the fixes in severity order (critical → high → medium). For each fix:

- Write the change.
- Verify by reproducing the failing evidence from the report and showing it now succeeds.
- Append one line to `.buildrunner/decisions.log`.

Specific attention for the embedder / indexer failure:

- If the model is not cached on Jimmy, resolve it by one of: (a) copying the model cache from Muddy's `~/.cache/huggingface/hub/` via `rsync -a` Muddy→Jimmy; (b) running a one-time `huggingface-cli download` on Jimmy if outbound is actually allowed; (c) switching to a truly local model path baked into the repo. Pick the option that aligns with the plan's "keep all-MiniLM-L6-v2 384d" decision and document the choice in decisions.log.
- After the model loads, run `~/.buildrunner/scripts/reindex-research.sh` and record chunk count.
- Then re-test with: `curl -sS -X POST -H "Content-Type: application/json" -d '{"query":"<pick a phrase known to exist in /srv/jimmy/research-library/>"}' http://10.0.1.106:8100/api/search` and require a non-empty `results` array.

## Deliverable 3 — Verification extension

Extend `~/.buildrunner/scripts/jimmy-verify.sh` with a new Check 6b:

- Runs the POST retrieval against a known query.
- Requires HTTP 200 AND `results` array length >= 1 AND no `error` key present in the JSON response.

Do not remove existing Check 6. Add 6b after it. After the extension lands, re-run the full suite — exit must be 0 with zero FAIL lines AND the new 6b must PASS.

## Deliverable 4 — Final report

Print a final report with:
(a) every GT-n and its final status (PASS / STILL BROKEN / OUT OF SCOPE with reason)
(b) `jimmy-verify.sh` exit code and FAIL count after all fixes
(c) chunk count from the reindex
(d) sample POST retrieval response JSON (pretty-printed)
(e) any deferred items with a one-line reason

If any GT item cannot be fixed in this run, say so explicitly and escalate. Do NOT mark the BUILD spec. Do NOT commit.
