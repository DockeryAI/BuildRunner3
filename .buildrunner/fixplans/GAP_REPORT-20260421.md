## Gap Report — cluster-max research-library reality

### GT-1: `/research <query>` returns real Jimmy research hits
- status: FAIL
- expected: `/research <query>` returns non-empty, scrubbed results with source paths and line ranges from Jimmy's `research_library` LanceDB table.
- actual: `~/.buildrunner/scripts/research-search.sh "dark mode color systems" 3` returns `{"results":[],"count":0}` on Muddy; the script still calls a local embed server plus `Lockwood` `/api/research/vsearch` instead of Jimmy `:8100/retrieve`.
- severity: critical
- gap: The user-facing research helper is still wired to the old Lockwood path and does not hit Jimmy's canonical retrieval service.
- fix: Repoint `~/.buildrunner/scripts/research-search.sh` to Jimmy `POST /retrieve` with `sources:["research"]` and preserve scrubbed source metadata.

### GT-2: Jimmy retrieval endpoint returns real hits from `/srv/jimmy/lancedb/research_library.lance`
- status: FAIL
- expected: `POST http://10.0.1.106:8100/retrieve` (canonical path) returns non-empty research hits from Jimmy's `research_library` table.
- actual: Jimmy probe returns `HTTP/1.1 200` with `{"query":"research","results":[],"total_candidates":0,"stage1_count":0,"stage2_count":0,"flag_active":false}`; `BR3_AUTO_CONTEXT` is off, the research corpus on Jimmy is empty, and the embedder cannot load the model.
- severity: critical
- gap: The canonical retrieval route is live but operationally disabled and backed by an unusable/empty research index.
- fix: Sync current code + corpus to Jimmy, enable the route on Jimmy, cache the model locally, rebuild the index, and re-test with a known-present query.

### GT-3: Jimmy embedder loads `all-MiniLM-L6-v2` offline inside the service process
- status: FAIL
- expected: Jimmy loads `sentence-transformers/all-MiniLM-L6-v2` from local cache without any runtime HuggingFace fetch.
- actual: Jimmy cache contains `BAAI/bge-reranker-v2-m3` but not `models--sentence-transformers--all-MiniLM-L6-v2`; `br3-semantic` logs show `We couldn't connect to 'https://huggingface.co'` for `all-MiniLM-L6-v2`, and `curl -I https://huggingface.co` on Jimmy times out on DNS resolution.
- severity: critical
- gap: The required embedding model is absent on Jimmy and Jimmy cannot fetch it from HuggingFace at runtime.
- fix: Copy Muddy's `all-MiniLM-L6-v2` cache to Jimmy, point service env at the canonical model, and run offline.

### GT-4: `reindex-research.sh` rebuilds the research index end-to-end on Jimmy
- status: FAIL
- expected: `~/.buildrunner/scripts/reindex-research.sh` exists on Jimmy, reads `/srv/jimmy/research-library/`, writes `research_library`, reports a real chunk count, and passes a sample-query sanity check.
- actual: Jimmy is missing `~/.buildrunner/scripts/reindex-research.sh`; `/srv/jimmy/research-library` currently has `0` files; Jimmy's repo mirror is stale and missing `core/cluster/lancedb_config.py` and `core/cluster/private_filter.py`.
- severity: critical
- gap: The intended reindex entrypoint is absent on Jimmy and the source corpus it should index is empty.
- fix: Sync the canonical scripts + repo files from Muddy to Jimmy, sync the research library Muddy→Jimmy, then run reindex and record chunk count.

### GT-5: `br3-semantic` is the only process on port 8100 and survives restart cleanly
- status: FAIL
- expected: Only `core.cluster.node_semantic:app` listens on `:8100`, with no orphan uvicorns, and `systemctl restart br3-semantic` works without manual cleanup.
- actual: Current steady state shows only `uvicorn` PID `347337` on `:8100`, but Jimmy logs contain repeated `ERROR: [Errno 98] ... address already in use` during recent restarts, proving earlier orphan/manual starts interfered with systemd control and restart hygiene is not yet re-verified.
- severity: high
- gap: The service currently looks clean, but restart behavior has recently depended on manual cleanup and has not been re-proved after syncing the canonical code.
- fix: Remove restart drift by deploying the canonical service/runtime files, then restart under systemd and prove single ownership of `:8100` after restart.

### GT-6: Nightly backup exits cleanly and `nightly-backup-health.sh` returns 0
- status: FAIL
- expected: Latest nightly backup exits `0` with zero `rsync error` lines, and `~/.buildrunner/scripts/nightly-backup-health.sh` returns `0`.
- actual: `~/.buildrunner/scripts/nightly-backup-health.sh` on Muddy returns `HEALTH FAIL: 4 rsync error(s) found in the last 24 hours`; the log tail shows a successful later run, but the health script still fails because earlier error lines remain in the 24-hour window.
- severity: high
- gap: Backup execution has recovered, but backup health still reports failure because the log/health contract does not isolate the latest successful run.
- fix: Repair the backup health contract around the latest completed run (not stale earlier failures), then prove a clean health check against a successful backup.

### GT-7: Muddy launchd job is loaded and scheduled
- status: PASS
- expected: `launchctl print gui/$(id -u)/com.buildrunner.nightly-backup` shows a loaded, scheduled job.
- actual: `launchctl print gui/$(id -u)/com.buildrunner.nightly-backup` returns a loaded job block with schedule fields present.
- severity: low
- gap: None.
- fix: None.

### GT-8: Jimmy `AGENTS.md` matches canonical source byte-for-byte
- status: PASS
- expected: Jimmy `~/AGENTS.md` matches Muddy `~/.buildrunner/agents-md/jimmy.md` exactly.
- actual: `jimmy-verify.sh` Check 8 passes and SHA-256 matches: `df1450c22a4cd30e...`.
- severity: low
- gap: None.
- fix: None.

### GT-9: `BR3_AUTO_CONTEXT` is the only active flag name
- status: FAIL
- expected: Active code + docs use only `BR3_AUTO_CONTEXT`; `BR3_MULTI_MODEL_CONTEXT` grep returns zero meaningful active hits.
- actual: Active repo grep still finds `BR3_MULTI_MODEL_CONTEXT` in `tests/cluster/test_flag_canonical.py`; immutable historical/spec artifacts also retain the old name, including the frozen build doc that this run must not edit.
- severity: medium
- gap: Canonicalization is incomplete in active repo content, and immutable historical docs prevent a true global zero-hit grep across every file on disk.
- fix: Remove the deprecated literal from active test code and document the frozen-spec limitation honestly in the final report.

### GT-10: `[private]` filtering is applied on both `/context` and `POST /retrieve`
- status: FAIL
- expected: Both live Jimmy egress paths scrub `[private]` lines before returning any row.
- actual: Jimmy's repo mirror is stale: `core/cluster/private_filter.py` is missing, remote `api/routes/retrieve.py` has no `filter_private_lines` references, and remote `core/cluster/context_bundle.py` still carries its own older filter path rather than the shared helper.
- severity: high
- gap: The current Jimmy deployment is not the canonical scrubbed code path and cannot satisfy the two-egress guarantee.
- fix: Sync Muddy's canonical `private_filter.py`, `retrieve.py`, and `context_bundle.py` to Jimmy and validate live with a canary document.

### GT-11: `context_bundle.py` reranks research docs with the bge cross-encoder
- status: FAIL
- expected: Research candidates are reranked with the bge cross-encoder, not selected by a 30-day mtime glob.
- actual: Remote Jimmy `core/cluster/context_bundle.py` still shows `_extract_research(max_docs..., ttl_days=30)` and `"Read recent research library docs. Skips docs older than ttl_days."`; the rerank path exists only on Muddy's newer repo copy.
- severity: high
- gap: Jimmy's deployed code is behind Muddy and still uses the old recency-based research selection logic.
- fix: Sync the canonical `context_bundle.py` to Jimmy and verify the rerank code path is deployed.

### GT-12: `jimmy-verify.sh` passes because reality is correct, not because checks were softened
- status: FAIL
- expected: `jimmy-verify.sh` exits `0` only when retrieval reality is correct, including a POST retrieval proof.
- actual: `~/.buildrunner/scripts/jimmy-verify.sh` currently exits `0` even while GT-1 through GT-4 remain broken; Check 6 only calls `/health`, so the script certifies a broken retrieval stack.
- severity: critical
- gap: Verification still has a blind spot for real research retrieval and therefore misreports cluster health.
- fix: Add Check 6b to require HTTP 200, no `error`, and `results.length >= 1` for a known Jimmy research query.
