# Draft Spec: cluster-max-research-library-remediation

**Created:** 2026-04-21
**Purpose:** Close the 8 library-integration gaps found by the 2026-04-21 parallel-subagent audit. Today the research library is de-facto single-homed on Muddy with zero working backups, LanceDB is still on Lockwood, Jimmy's storage tree does not exist, the auto-context flag name the spec checks is not the one code reads, and about 30% of the advertised /research pipeline is fictional. This build makes the cutover flags safe to flip.
**Target Users:** Byron (primary). The cluster itself is the downstream consumer.
**Tech Stack:** Bash scripts + LaunchAgents (macOS), LaunchDaemons (Jimmy), LanceDB + sentence-transformers OR nomic-embed-text, Python FastAPI retrieve service, Ollama HTTP on Below, rsync (BSD on macOS / GNU on Linux).

---

## Context & Motivation

The post-cutover audit produced five findings in severity order:

1. **Jimmy's storage tree does not exist.** `jimmy-storage-init.sh` hit a sudo password prompt on Apr 20. `/srv/jimmy/research-library/`, `/srv/jimmy/lancedb/`, `/srv/jimmy/backups/` were never created. Every downstream script is writing into a void.
2. **Canonical-host drift.** Spec says Jimmy is source of truth; reality is Muddy (10 recent commits through Apr 17). All sync scripts go Muddy → Jimmy. If any Phase-13 code writes to Jimmy while believing it's canonical, those commits are at risk.
3. **Nightly backup has never succeeded.** `nightly-projects-backup.sh` crashes every night with `rsync: invalid option -- A`. Written for GNU rsync; macOS ships BSD rsync (no `-A` / `-X`). Zero successful backups on record.
4. **LanceDB still on Lockwood.** `migrate-lockwood-data.sh` died with `fork: Resource temporarily unavailable`. Vector index lives at `~/.lockwood/lancedb/`. Anything pointing at "Jimmy's index" is hitting the wrong box.
5. **Embedding model mismatch.** Spec says `nomic-embed-text` (768d via Below). Code uses `sentence-transformers/all-MiniLM-L6-v2` (384d in-process). Incompatible indices; a full reindex is required to converge.

Three narrower gaps:

6. **/research pipeline Steps 4–6 are fictional.** Spec advertises Below reformat → qwen3 metadata → nomic embed → LanceDB write → completed.jsonl → next-turn chunk-count report. Zero implementing code. `/research` today fires one curl at Lockwood reindex and returns. The "indexed at doc-id, Y chunks" UX never appears.
7. **Flag-name drift.** Spec gates everything on `BR3_MULTI_MODEL_CONTEXT`. Every line of actual code (`context_bundle.py`, `context_router.py`, `context_injector.py`, `context.py`) reads `BR3_AUTO_CONTEXT`. Flipping the spec's flag activates nothing.
8. **`[private]` leak filter runs on decisions only.** Research docs passing `[private]` lines reach every model unfiltered. Leak test only seeds a decisions canary. Research reaches the bundle via 30-day mtime glob — no semantic ranking, despite Phase 10 building a reranker. `retrieve.py` may still be running on Lockwood, not Jimmy (Phase 3 migration notes show deploy was deferred). `start_line`/`end_line` always return 0. Empty index silently returns `[]`.

---

## Phases

### Phase 1: Canonicalization decision + Jimmy sudo bootstrap

**Goal:** Exactly one host is the documented source of truth for the research library, and Jimmy is reachable for privileged operations without an interactive password prompt.

**Files:**

- `.buildrunner/cluster-max/CANONICALIZATION_DECISION.md` (NEW)
- `/etc/sudoers.d/byronhudson` on Jimmy (NEW — out-of-repo, documented via `~/.buildrunner/scripts/jimmy-sudo-bootstrap.sh`)
- `~/.buildrunner/scripts/jimmy-sudo-bootstrap.sh` (NEW — idempotent; writes sudoers drop-in via `visudo -c` validation)
- `core/cluster/AGENTS.md` (MODIFY — add "canonical host" section at top)
- `.buildrunner/decisions.log` (APPEND)

**Blocked by:** None.

**Deliverables:**

- [ ] Decide canonical host: **Muddy-primary, Jimmy-mirror** (preserves the 10 recent commits; Jimmy's role narrows to read-replica + backup target). Document alternative considered + rejected.
- [ ] Write `CANONICALIZATION_DECISION.md` with: chosen direction, rationale, affected scripts (explicit list), rollback procedure.
- [ ] Ship `jimmy-sudo-bootstrap.sh` that writes `/etc/sudoers.d/byronhudson` via a single one-time `ssh -t byron@jimmy sudo tee` invocation (password entered once), validates with `visudo -c`, then tests passwordless by running `ssh byron@jimmy sudo -n true`.
- [ ] Verify passwordless sudo: `ssh byron@jimmy sudo -n whoami` returns `root` without prompting.
- [ ] Append decision to `.buildrunner/decisions.log` via `br decision log`.
- [ ] Update `core/cluster/AGENTS.md` with a top-of-file "Canonical Host" section citing the decision file.

**Success Criteria:** A single file in the repo states which host is canonical. `ssh byron@jimmy sudo -n true` exits 0. No other deliverable is begun before this phase passes.

---

### Phase 2: Jimmy storage tree + sync direction alignment

**Goal:** `/srv/jimmy/{research-library,lancedb,backups}` exist and are writable by `byronhudson`. All sync scripts reflect the Phase-1 canonical decision (Muddy → Jimmy mirror direction).

**Files:**

- `~/.buildrunner/scripts/jimmy-storage-init.sh` (MODIFY — remove interactive-sudo assumption; use passwordless path from Phase 1; idempotent)
- `~/.buildrunner/scripts/jimmy-verify.sh` (MODIFY — check ownership + writability, not just existence)
- `~/.buildrunner/scripts/sync-muddy-to-jimmy.sh` (NEW or MODIFY — canonical sync direction per Phase 1)
- `~/.buildrunner/scripts/sync-jimmy-to-muddy.sh` (DELETE if present — wrong direction under Muddy-primary decision)
- `~/.buildrunner/cluster.json` (MODIFY — add `storage_root` field to jimmy entry)

**Blocked by:** Phase 1.

**Deliverables:**

- [ ] Refactor `jimmy-storage-init.sh` to use `ssh byron@jimmy sudo -n` (from Phase 1), no interactive password assumption; script is idempotent (re-run safe).
- [ ] Create `/srv/jimmy/research-library`, `/srv/jimmy/lancedb`, `/srv/jimmy/backups` with `chown byronhudson:byronhudson` and `chmod 755`.
- [ ] Run `jimmy-verify.sh`; require it to check existence, ownership, writability (touch+rm in each dir), and exit non-zero on any failure.
- [ ] Ship `sync-muddy-to-jimmy.sh` with explicit comment at top naming Phase-1 canonical direction; first run with `--dry-run` logging.
- [ ] Delete any `sync-jimmy-to-muddy.sh` or equivalent wrong-direction script; log deletion to decisions.log.
- [ ] Add `storage_root: /srv/jimmy` to Jimmy's entry in `~/.buildrunner/cluster.json`.
- [ ] Smoke test: `ssh byron@jimmy "ls -la /srv/jimmy"` prints all three directories with correct ownership.

**Success Criteria:** `jimmy-verify.sh` exits 0. One successful dry-run of `sync-muddy-to-jimmy.sh` logs expected file counts. No wrong-direction sync script remains on disk.

---

### Phase 3: Nightly backup reliability (BSD rsync fix)

**Goal:** `nightly-projects-backup.sh` runs cleanly on macOS and produces at least one verified backup on disk.

**Files:**

- `~/.buildrunner/scripts/nightly-projects-backup.sh` (MODIFY)
- `~/Library/LaunchAgents/com.buildrunner.nightly-backup.plist` (VERIFY — no changes if already correct)
- `~/.buildrunner/logs/nightly-backup.log` (consumed, not created here)

**Blocked by:** Phase 1 (needs canonical host decision for backup target). Can run in parallel with Phase 2 (different files).

**Deliverables:**

- [ ] OS-branch the rsync invocation: if `uname` == `Darwin`, drop `-A` (ACLs) and `-X` (xattrs). On Linux, keep full set. Single `RSYNC_FLAGS` array built at top of script.
- [ ] Run the script manually end-to-end; require exit 0 and a non-empty `~/.buildrunner/logs/nightly-backup.log`.
- [ ] Trigger the LaunchAgent manually via `launchctl start com.buildrunner.nightly-backup`; verify the log shows a new run and exit 0.
- [ ] Verify target directory on Jimmy per Phase 1 canonical decision (Muddy → `/srv/jimmy/backups/`).
- [ ] Add a `--smoke` flag to the script that does a 10-file sync and exits, for use by E2E.
- [ ] Write one-line `nightly-backup-health.sh` that greps the last 24h of the log for `rsync error`; exits non-zero if found. Hook this into the Phase-7 feature-health check (out of scope for this build, but stub it).

**Success Criteria:** A line in `nightly-backup.log` within the last hour shows "backup complete, <N> files, 0 errors". `launchctl list | grep nightly-backup` shows last exit status 0.

---

### Phase 4: LanceDB migration completion (Lockwood → canonical host)

**Goal:** The LanceDB research index lives on the Phase-1 canonical host (Muddy per the chosen direction) and is reachable by every service that currently references it.

**Files:**

- `~/.buildrunner/scripts/migrate-lockwood-data.sh` (MODIFY — raise ulimit, chunk the transfer)
- `core/cluster/lancedb_config.py` (MODIFY — single source for DB URI)
- `api/routes/retrieve.py` (MODIFY — read URI from `lancedb_config.py`, not a hardcoded path)
- `core/semantic/` (MODIFY — any module that opens LanceDB reads the same config)
- `tests/cluster/test_lancedb_uri_single_source.py` (NEW — asserts no hardcoded LanceDB paths outside `lancedb_config.py`)

**Blocked by:** Phase 2 (needs the canonical-host storage tree to exist).

**Deliverables:**

- [ ] Fix `fork: Resource temporarily unavailable`: add `ulimit -n 4096` at script top; if that's insufficient, chunk the copy into 1000-file batches with `rsync --files-from`.
- [ ] Re-run `migrate-lockwood-data.sh`; capture source and destination row counts; fail if they differ.
- [ ] Introduce `core/cluster/lancedb_config.py` as the single URI source (env-overridable for tests); replace all hardcoded LanceDB paths.
- [ ] Update `api/routes/retrieve.py` and every `core/semantic/` module to import from `lancedb_config.py`.
- [ ] Write `test_lancedb_uri_single_source.py` that greps the repo for hardcoded LanceDB paths outside `lancedb_config.py`; fails if any are found.
- [ ] Smoke test: one sample vector query against the migrated table returns ≥1 result with expected columns.
- [ ] Leave the Lockwood copy intact for 7 days as a rollback; document the delete-after date in decisions.log.

**Success Criteria:** Row count on destination == source. Grep finds zero hardcoded LanceDB paths outside the config module. One sample query returns expected shape.

---

### Phase 5: Flag-name canonicalization (BR3_AUTO_CONTEXT)

**Goal:** Exactly one flag name controls auto-context behavior, and every code path + every spec agrees on that name.

**Files:**

- `AGENTS.md` (MODIFY — state canonical flag name)
- `core/cluster/AGENTS.md` (MODIFY)
- `core/runtime/AGENTS.md` (MODIFY)
- `ui/dashboard/AGENTS.md` (MODIFY)
- `.buildrunner/plans/*.md` (MODIFY — any referencing `BR3_MULTI_MODEL_CONTEXT`)
- `.buildrunner/builds/BUILD_cluster-max.md` (MODIFY — same)
- `core/cluster/context_bundle.py` (VERIFY — already reads `BR3_AUTO_CONTEXT`)
- `core/cluster/context_router.py` (VERIFY)
- `core/runtime/context_injector.py` (VERIFY)
- `api/routes/context.py` (VERIFY)
- `tests/cluster/test_flag_canonical.py` (NEW — greps repo for deprecated name, fails on any hit)

**Blocked by:** None. File-independent of Phases 2, 3, 4. Can run in parallel with any of them.

**Deliverables:**

- [ ] Decide canonical: **`BR3_AUTO_CONTEXT`** (all existing code reads it; changing code is more invasive than changing specs).
- [ ] Grep the repo for `BR3_MULTI_MODEL_CONTEXT`; enumerate every hit before editing.
- [ ] Rewrite each hit to `BR3_AUTO_CONTEXT` in specs, AGENTS.md files, and staged BUILD specs.
- [ ] Verify no code file reads `BR3_MULTI_MODEL_CONTEXT` (expected: zero hits outside docs).
- [ ] Write `test_flag_canonical.py` that fails if `BR3_MULTI_MODEL_CONTEXT` appears anywhere in the repo (specs included).
- [ ] Log decision + rationale to `.buildrunner/decisions.log`.

**Success Criteria:** `grep -r BR3_MULTI_MODEL_CONTEXT` returns zero hits. `test_flag_canonical.py` passes.

---

### Phase 6: Embedding model decision + research index rebuild

**Goal:** Exactly one embedding model governs the research index; spec + code + index dim agree.

**Files:**

- `core/semantic/embedder.py` or equivalent (MODIFY)
- `.buildrunner/plans/*.md` (MODIFY — align with decision)
- `~/.buildrunner/scripts/reindex-research.sh` (NEW)
- `core/cluster/lancedb_config.py` (MODIFY — embedding dim is a config field)
- `tests/cluster/test_embedding_dim_matches_index.py` (NEW)

**Blocked by:** Phase 4 (index must exist on canonical host before reindex).

**Deliverables:**

- [ ] Decide: **keep `sentence-transformers/all-MiniLM-L6-v2` (384d)**. Rationale: code already runs it in-process; no Below round-trip; adequate quality for research recall at this scale. Spec aligns to reality.
- [ ] Update spec references to nomic-embed-text / 768d → all-MiniLM-L6-v2 / 384d across all affected planning docs.
- [ ] Ship `reindex-research.sh`: drops `research` table, walks `~/Projects/research-library/`, re-embeds, writes back. Idempotent. Takes `--dry-run`.
- [ ] Add `embedding_dim: 384` field to `lancedb_config.py`; every embedder asserts the dim at startup.
- [ ] Write `test_embedding_dim_matches_index.py` that opens the LanceDB schema and asserts the vector column width matches config dim.
- [ ] Run `reindex-research.sh` once end-to-end; record chunk count in decisions.log.
- [ ] Smoke: `/research foo` returns ≥1 result; response includes model name + dim in metadata.

**Success Criteria:** Index dim == config dim == code-time assert. Reindex completes without error; one sample query returns non-empty.

---

### Phase 7: Research pipeline reconciliation + [private] filter + retrieve host verify

**Goal:** No advertised `/research` functionality without implementing code; `[private]` filter applies to research docs; `retrieve.py` is confirmed running on the canonical host; bundle uses semantic ranking not mtime.

**Files:**

- `~/.claude/commands/research.md` (MODIFY — align UX with actual code, OR build Steps 4–6)
- `.buildrunner/plans/*.md` + `.buildrunner/builds/BUILD_cluster-max.md` (MODIFY — remove fictional pipeline description if cutting)
- `core/cluster/context_bundle.py` (MODIFY — extend `[private]` scrubber to research docs; replace 30-day mtime glob with reranker call)
- `core/cluster/private_filter.py` (NEW — shared `filter_private_lines` helper, imported by both `context_bundle.py` and `retrieve.py` so the scrubber runs on every egress path)
- `tests/cluster/test_no_private_leak.py` (MODIFY — add research canary; assert both `/context` bundle and `POST /retrieve` responses scrub the canary)
- `api/routes/retrieve.py` (MODIFY — apply `filter_private_lines` to `row.get("text", "")` for every source before returning; return `line_start`/`line_end` from chunk metadata if available; surface empty-index warning)
- `~/.buildrunner/scripts/verify-retrieve-host.sh` (NEW — curl-based health check against canonical host)
- `tests/integration/test_retrieve_host_canonical.py` (NEW)

**Blocked by:** Phases 5 and 6 (flag name + embedding model must be settled before touching /research UX or the bundle ranker).

**Deliverables:**

- [ ] Decide pipeline Steps 4–6: **cut** (remove from spec and skill docs). Rationale: Claude-side research works today; the Below-reformat + qwen3 metadata + nomic embed chain is a 3–5 day build for marginal recall gain at this library size. Revisit when library exceeds 10k docs.
- [ ] Rewrite the spec + `/research` skill UX to describe only what actually runs: Claude researches → Claude synthesizes → immediate summary → Jimmy reindex fires → done. No "indexed at doc-id, Y chunks" claim.
- [ ] Extract `filter_private_lines(text)` into new `core/cluster/private_filter.py` (shared helper); failing test first.
- [ ] Apply `filter_private_lines` in `context_bundle.py` to research doc content before appending to bundle.
- [ ] Apply `filter_private_lines` in `api/routes/retrieve.py` to every source row's text before returning from `POST /retrieve` — closes the direct-egress path the reviewer flagged (review finding #4).
- [ ] Add research canary to `test_no_private_leak.py`; canary appears in a research doc; assert it never reaches `/context` bundle OR `POST /retrieve` response.
- [ ] Replace 30-day mtime glob in `context_bundle.py` with `rerank(query, candidates)` call using the Phase-10 bge cross-encoder; top-K configurable.
- [ ] Surface `start_line`/`end_line` from chunk metadata in `retrieve.py` responses (non-zero when available; 0 is explicit "not available" not default).
- [ ] Return a `{ results: [], warning: "index is empty" }` shape from `retrieve.py` when the table has zero rows, instead of silent `[]`.
- [ ] Ship `verify-retrieve-host.sh`: curls canonical host per Phase 1; fails if response host header or banner names the wrong machine.
- [ ] `test_retrieve_host_canonical.py` hits the live endpoint and asserts canonical-host reachability.

**Success Criteria:** /research skill doc reflects code reality exactly. `test_no_private_leak.py` includes research canary and asserts both `/context` and `POST /retrieve` scrub it. `verify-retrieve-host.sh` exits 0 against canonical host. Empty-index query returns explicit warning, not silent empty.

---

## Out of Scope (Future)

- Building the Below reformat → qwen3 metadata → nomic embed → LanceDB write pipeline (Steps 4–6). Revisit when library exceeds 10k docs.
- Switching to `nomic-embed-text`. If future research-recall quality requires it, a dedicated rebuild phase applies.
- Moving to Jimmy as primary (vs mirror). The Phase-1 decision is Muddy-primary; a future build can invert after Jimmy has proven reliable for ≥90 days.
- Cross-project research libraries. This build targets BR3's single library.
- Real-time index sync (Muddy → Jimmy on every write). Nightly sync + weekly verification is adequate for the current volume.
- `retrieve.py` pagination, faceted search, hybrid BM25+vector. Recall via vector + rerank is sufficient today.
- Auto-expansion of the `[private]` scrubber to memory docs. Memory is already scrubbed at ingest; research was the gap.

---

## Parallelization Matrix

| Phase | Key Files                                                                                     | Can Parallel With | Blocked By |
| ----- | --------------------------------------------------------------------------------------------- | ----------------- | ---------- |
| 1     | CANONICALIZATION_DECISION.md, jimmy-sudo-bootstrap.sh, AGENTS.md                              | —                 | —          |
| 2     | jimmy-storage-init.sh, jimmy-verify.sh, sync-muddy-to-jimmy.sh, cluster.json                  | 3, 5              | 1          |
| 3     | nightly-projects-backup.sh, nightly-backup-health.sh                                          | 2, 5              | 1          |
| 4     | migrate-lockwood-data.sh, lancedb_config.py, retrieve.py, core/semantic/\*                    | 5                 | 2          |
| 5     | AGENTS.md files, staged specs, test_flag_canonical.py                                         | 2, 3, 4           | —          |
| 6     | embedder.py, reindex-research.sh, lancedb_config.py, test_embedding_dim_matches_index.py      | —                 | 4          |
| 7     | research.md, context_bundle.py, test_no_private_leak.py, retrieve.py, verify-retrieve-host.sh | —                 | 5, 6       |

**Parallelizable groupings:**

- After Phase 1: Phases 2, 3, 5 run in parallel.
- After Phase 2: Phase 4 starts (can still overlap with 3 and 5).
- Phase 6 is serial after 4.
- Phase 7 is serial after 5 and 6.

**Total phases:** 7
**Total deliverables:** 55
**Estimated effort:** ~8–10 hours across 2 sessions; faster if Phases 2/3/5 actually parallelize.

---

## Risks & Mitigations

1. **Canonicalization decision locks in architecture.** Document alternatives considered so reversal is cheap. The Phase-1 decision file names the rollback procedure.
2. **Jimmy sudo bootstrap requires one interactive password.** This is unavoidable the first time. Script makes the window small (one ssh session) and never stores the password.
3. **Reindex duration on MiniLM.** Single-threaded CPU embedding of the full library takes 5–15 minutes at current size. Acceptable during a maintenance window; unacceptable in a hot-loop. `reindex-research.sh` is one-shot by design.
4. **Flag rename breaks the dashboard temporarily.** If the dashboard reads the old name anywhere, it goes yellow. Phase 5's `test_flag_canonical.py` catches this before merge.
5. **Deleting the wrong-direction sync script risks data loss if the decision is wrong.** Mitigation: keep `.bak` copy for 7 days; decisions.log records the delete-after date.
6. **Private scrubber extension may over-filter.** Write the test first with a known canary; validate the scrubber only strips lines that start with `[private]`, not lines that merely contain the substring.
7. **Cutting pipeline Steps 4–6 breaks any external consumer expecting "indexed at doc-id, Y chunks".** Grep the repo for that exact phrase before cutting; none should exist, but verify.

---

## Dependencies on Existing Infrastructure

- `jimmy-bootstrap.sh`, `jimmy-verify.sh`, `jimmy-storage-init.sh` — Phase-0 infrastructure, consumed by Phases 1, 2.
- `migrate-lockwood-data.sh` — consumed by Phase 4.
- `nightly-projects-backup.sh` + the existing LaunchAgent plist — consumed by Phase 3.
- `context_bundle.py`, `context_router.py`, `context_injector.py`, `api/routes/context.py` — source of truth for `BR3_AUTO_CONTEXT`; verified (not modified) by Phase 5.
- LanceDB + sentence-transformers — consumed by Phases 4, 6.
- Phase-10 bge cross-encoder reranker — consumed by Phase 7.
- `~/.claude/commands/research.md` — the /research skill — modified by Phase 7.
