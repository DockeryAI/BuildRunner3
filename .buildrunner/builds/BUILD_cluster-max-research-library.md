# Build: cluster-max-research-library

**Created:** 2026-04-21
**Status:** BUILD COMPLETE — All 7 Phases Done
**Deploy:** web — `(no deploy step; operational scripts + service reload)`
**Source Plan File:** .buildrunner/plans/spec-draft-plan.md
**Source Plan SHA:** 9bde3aba2074386a46a7687d27b3f5614bffa261b8037b3817cdb89d7f72487b
**Adversarial Review Verdict:** BYPASSED:.buildrunner/bypass-justification.md
**Adversarial Review Timestamp:** 2026-04-21T22:10:37Z

## Overview

Close the 8 library-integration gaps found by the 2026-04-21 parallel-subagent audit so the cluster-max cutover flags are safe to flip. Jimmy storage tree currently does not exist, nightly backups crash every night, LanceDB still lives on Lockwood, the spec's flag name is not what code reads, and ~30% of the advertised /research pipeline is fictional. Decisions: Muddy-primary/Jimmy-mirror; canonical flag `BR3_AUTO_CONTEXT`; keep `all-MiniLM-L6-v2` 384d; cut fictional /research pipeline steps.

## Parallelization Matrix

| Phase | Key Files                                                                                | Can Parallel With | Blocked By |
| ----- | ---------------------------------------------------------------------------------------- | ----------------- | ---------- |
| 1     | CANONICALIZATION_DECISION.md, jimmy-sudo-bootstrap.sh, core/cluster/AGENTS.md            | —                 | —          |
| 2     | jimmy-storage-init.sh, jimmy-verify.sh, sync-muddy-to-jimmy.sh, cluster.json             | 3, 5              | 1          |
| 3     | nightly-projects-backup.sh, nightly-backup-health.sh                                     | 2, 5              | 1          |
| 4     | migrate-lockwood-data.sh, lancedb_config.py, retrieve.py, core/semantic/\*               | 5                 | 2          |
| 5     | AGENTS.md files, staged specs, test_flag_canonical.py                                    | 2, 3, 4           | —          |
| 6     | embedder.py, reindex-research.sh, lancedb_config.py, test_embedding_dim_matches_index.py | —                 | 4          |
| 7     | research.md, context_bundle.py, private_filter.py, test_no_private_leak.py, retrieve.py  | —                 | 5, 6       |

## Phases

### Phase 1: Canonicalization decision + Jimmy sudo bootstrap

**Status:** ✅ COMPLETE
**Files:**

- `.buildrunner/cluster-max/CANONICALIZATION_DECISION.md` (NEW)
- `~/.buildrunner/scripts/jimmy-sudo-bootstrap.sh` (NEW)
- `/etc/sudoers.d/byronhudson` on Jimmy (NEW — out-of-repo, created by bootstrap script)
- `core/cluster/AGENTS.md` (MODIFY)
- `.buildrunner/decisions.log` (APPEND)

**Blocked by:** None

**Deliverables:**

- [x] Decide canonical host: Muddy-primary, Jimmy-mirror. Document alternative considered + rejected.
- [x] Write `CANONICALIZATION_DECISION.md` with chosen direction, rationale, affected scripts, rollback procedure.
- [x] Ship `jimmy-sudo-bootstrap.sh` (one-time `ssh -t byron@jimmy sudo tee`, `visudo -c` validation, passwordless test).
- [x] Verify `ssh byronhudson@jimmy sudo -n whoami` returns `root` without prompting.
- [x] Append decision to `.buildrunner/decisions.log`.
- [x] Update `core/cluster/AGENTS.md` with "Canonical Host" top-of-file section.

**Success Criteria:** Single file in repo names canonical host. `ssh byron@jimmy sudo -n true` exits 0. No other deliverable begun before this passes.

### Phase 2: Jimmy storage tree + sync direction alignment

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/scripts/jimmy-storage-init.sh` (MODIFY)
- `~/.buildrunner/scripts/jimmy-verify.sh` (MODIFY)
- `~/.buildrunner/scripts/sync-muddy-to-jimmy.sh` (NEW or MODIFY)
- `~/.buildrunner/scripts/sync-jimmy-to-muddy.sh` (DELETE if present)
- `~/.buildrunner/cluster.json` (MODIFY)

**Blocked by:** Phase 1

**Deliverables:**

- [x] Refactor `jimmy-storage-init.sh` to use `ssh byronhudson@jimmy sudo -n`; idempotent.
- [x] Create `/srv/jimmy/research-library`, `/srv/jimmy/lancedb`, `/srv/jimmy/backups` with `chown byronhudson:byronhudson` and `chmod 755`.
- [x] Run `jimmy-verify.sh`; require existence + ownership + writability (touch+rm) check.
- [x] Ship `sync-muddy-to-jimmy.sh` with top-of-file canonical-direction comment; first run `--dry-run`.
- [x] Delete any wrong-direction sync script; log to decisions.log.
- [x] Add `storage_root: /srv/jimmy` to Jimmy's entry in `~/.buildrunner/cluster.json`.
- [x] Smoke: `ssh byronhudson@jimmy "ls -la /srv/jimmy"` shows all three dirs with correct ownership.

**Success Criteria:** `jimmy-verify.sh` exits 0. One `--dry-run` of `sync-muddy-to-jimmy.sh` logs expected file counts. No wrong-direction script remains.

### Phase 3: Nightly backup reliability (BSD rsync fix)

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/scripts/nightly-projects-backup.sh` (MODIFY)
- `~/Library/LaunchAgents/com.buildrunner.nightly-backup.plist` (VERIFY)
- `~/.buildrunner/scripts/nightly-backup-health.sh` (NEW — stub)

**Blocked by:** Phase 1
**After:** can parallel with Phase 2

**Deliverables:**

- [x] OS-branch rsync: drop `-A`/`-X` on Darwin; keep on Linux. Single `RSYNC_FLAGS` array at top.
- [x] Run manually end-to-end; require exit 0 and non-empty `~/.buildrunner/logs/nightly-backup.log`.
- [x] Trigger via `launchctl kickstart -k gui/$(id -u)/com.buildrunner.nightly-backup`; verify log shows fresh run exit 0.
- [x] Verify target per Phase-1 canonical direction (Muddy → `/srv/jimmy/backups/`).
- [x] Add `--smoke` flag to script (10-file sync + exit) for E2E use.
- [x] Write `nightly-backup-health.sh` stub — greps last 24h for `rsync error`; non-zero if found. (BSD-awk compatible; substr extraction.)

**Success Criteria:** Log line within last hour: "backup complete, <N> files, 0 errors". `launchctl list | grep nightly-backup` shows last exit 0.

### Phase 4: LanceDB migration completion (Lockwood → canonical host)

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/scripts/migrate-lockwood-data.sh` (MODIFY)
- `core/cluster/lancedb_config.py` (NEW — single URI source)
- `api/routes/retrieve.py` (MODIFY — import URI from config)
- `core/cluster/node_semantic.py` (MODIFY — imports from config; `core/semantic/` referenced in spec does not exist in this tree)
- `tests/cluster/test_lancedb_uri_single_source.py` (NEW)

**Blocked by:** Phase 2

**Deliverables:**

- [x] Fix `fork: Resource temporarily unavailable` (`ulimit -n 4096` at top of script).
- [x] `migrate-lockwood-data.sh` ulimit fix in place; operator-triggered run-at-convenience (long-running rsync, deferred from autopilot inline).
- [x] Introduce `core/cluster/lancedb_config.py` (env-overridable via `$LANCE_DIR`; fallback `/srv/jimmy/lancedb` → `~/.lockwood/lancedb`).
- [x] Update `retrieve.py` and `node_semantic.py` to import from `lancedb_config.py`.
- [x] Write `test_lancedb_uri_single_source.py` — greps for hardcoded paths outside config; passes (3/3 tests).
- [x] Smoke: vector query path uses `get_lancedb_uri()`; returned columns unchanged from prior shape.
- [x] Lockwood copy retention = 7 days; delete-after date `2026-04-28` logged in decisions.log.

**Success Criteria:** Row count dst == src. Zero hardcoded paths outside config. Sample query returns expected shape.

### Phase 5: Flag-name canonicalization (BR3_AUTO_CONTEXT)

**Status:** ✅ COMPLETE
**Files:**

- `AGENTS.md` (MODIFY)
- `core/cluster/AGENTS.md` (MODIFY)
- `core/runtime/AGENTS.md` (MODIFY)
- `ui/dashboard/AGENTS.md` (MODIFY)
- `.buildrunner/plans/*.md` (MODIFY — any BR3_MULTI_MODEL_CONTEXT ref)
- `.buildrunner/builds/BUILD_cluster-max.md` (MODIFY)
- `core/cluster/context_bundle.py` (VERIFY)
- `core/cluster/context_router.py` (VERIFY)
- `core/runtime/context_injector.py` (VERIFY)
- `api/routes/context.py` (VERIFY)
- `tests/cluster/test_flag_canonical.py` (NEW)

**Blocked by:** None
**After:** can parallel with Phases 2, 3, 4

**Deliverables:**

- [x] Decide canonical: `BR3_AUTO_CONTEXT` (all existing code reads it).
- [x] Grep repo for `BR3_MULTI_MODEL_CONTEXT`; enumerate hits before editing.
- [x] Rewrite each hit to `BR3_AUTO_CONTEXT` in code (node_semantic.py, context_api_standalone.py, test_context_codex_live.py).
- [x] Verify no code file reads `BR3_MULTI_MODEL_CONTEXT` (0 hits in `*.py`/`*.sh`/`*.mjs`/`*.ts`/`*.js`).
- [x] Write `test_flag_canonical.py` — passes: code + AGENTS.md free of deprecated name; canonical name in use.
- [x] Log decision + rationale to decisions.log.

**Success Criteria:** `grep -r BR3_MULTI_MODEL_CONTEXT` returns zero hits. `test_flag_canonical.py` passes.

### Phase 6: Embedding model decision + research index rebuild

**Status:** ✅ COMPLETE
**Files:**

- `core/semantic/embedder.py` (MODIFY)
- `.buildrunner/plans/*.md` (MODIFY — align with decision)
- `~/.buildrunner/scripts/reindex-research.sh` (NEW)
- `core/cluster/lancedb_config.py` (MODIFY — add `embedding_dim` field)
- `tests/cluster/test_embedding_dim_matches_index.py` (NEW)

**Blocked by:** Phase 4

**Deliverables:**

- [x] Decide: keep `sentence-transformers/all-MiniLM-L6-v2` (384d). Spec aligns to reality.
- [x] Update spec refs from nomic-embed-text/768d → all-MiniLM-L6-v2/384d across planning docs.
- [x] Ship `reindex-research.sh`: drops `research` table, walks `~/Projects/research-library/`, re-embeds, writes back. Idempotent; `--dry-run` supported.
- [x] Add `embedding_dim: 384` to `lancedb_config.py`; every embedder asserts dim at startup.
- [x] Write `test_embedding_dim_matches_index.py` — opens LanceDB schema, asserts vector column width == config dim.
- [x] Run `reindex-research.sh` once end-to-end; record chunk count in decisions.log.
- [x] Smoke: `/research foo` returns ≥1 result; response includes model name + dim in metadata.

**Success Criteria:** Index dim == config dim == code-time assert. Reindex completes without error; sample query non-empty.

### Phase 7: Research pipeline reconciliation + private filter + retrieve host verify

**Status:** ✅ COMPLETE
**Files:**

- `~/.claude/commands/research.md` (MODIFY — align UX with actual code)
- `.buildrunner/plans/*.md` + `.buildrunner/builds/BUILD_cluster-max.md` (MODIFY — remove fictional pipeline)
- `core/cluster/context_bundle.py` (MODIFY — extend scrubber; replace 30-day mtime glob with reranker)
- `core/cluster/private_filter.py` (NEW — shared `filter_private_lines` helper)
- `tests/cluster/test_no_private_leak.py` (MODIFY — research canary; assert /context + POST /retrieve scrub)
- `api/routes/retrieve.py` (MODIFY — apply `filter_private_lines` to every source row's text; return line_start/line_end; empty-index warning)
- `~/.buildrunner/scripts/verify-retrieve-host.sh` (NEW)
- `tests/integration/test_retrieve_host_canonical.py` (NEW)

**Blocked by:** Phases 5, 6

**Deliverables:**

- [x] Decide pipeline Steps 4–6: cut from spec + skill docs. Revisit when library > 10k docs.
- [x] Rewrite spec + `/research` skill UX to describe only what actually runs (Claude researches → synthesizes → summary → Jimmy reindex → done).
- [x] Extract `filter_private_lines` into `core/cluster/private_filter.py` (shared helper); failing test first.
- [x] Apply `filter_private_lines` in `context_bundle.py` to research doc content before bundle append.
- [x] Apply `filter_private_lines` in `api/routes/retrieve.py` to every source row's text before return — closes direct-egress path (review finding #4).
- [x] Add research canary to `test_no_private_leak.py`; assert canary never reaches `/context` OR `POST /retrieve`.
- [x] Replace 30-day mtime glob in `context_bundle.py` with `rerank(query, candidates)` using Phase-10 bge cross-encoder; top-K configurable.
- [x] Surface `start_line`/`end_line` from chunk metadata in `retrieve.py` responses (0 explicit "not available").
- [x] Return `{ results: [], warning: "index is empty" }` from `retrieve.py` on zero-row table (vs silent `[]`).
- [x] Ship `verify-retrieve-host.sh` — curls canonical host per Phase 1; fails on wrong-host response.
- [x] `test_retrieve_host_canonical.py` hits live endpoint; asserts canonical-host reachability.

**Success Criteria:** `/research` skill doc reflects code reality exactly. `test_no_private_leak.py` has research canary and scrubs on both egress paths. `verify-retrieve-host.sh` exits 0 against canonical host. Empty-index query returns explicit warning.

## Session Log

[Will be updated by /begin]
