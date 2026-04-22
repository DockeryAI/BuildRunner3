# Codex-Optimized Project Spec: cluster-library-consolidation

**Purpose:** Consolidate the research library to a single source of truth on Jimmy with all cluster-max + cluster-activation capabilities, backed up to GitHub, with Muddy's copy deleted and bypass-blocked.
**Target Users:** Claude (via `/research`, `/retrieve`, `/learn`), Codex workers on Below, autopilot phase dispatch.
**Tech Stack:** Git + GitHub (SSOT + DR), LanceDB (vector index), FastAPI on Jimmy (`:8100` retrieval / `:4500` context parity), Ollama on Below (llama3.3:70b, qwen3:8b, nomic-embed-text), bge-reranker-v2-m3, Claude Sonnet 4.6 for `/research`, shell/Python glue.
**Codex Model:** GPT-5.4 default; GPT-5.3-Codex for Phase 6 (terminal-heavy worker).
**Effort Level:** Medium default. xHigh on Phase 1 (GitHub backup — rollback anchor), Phase 8 (enforcement hooks — security boundary), Phase 10 (Muddy delete — irreversible).

---

## Capability Inventory (what lands on Jimmy by the end)

Pulled from BUILD_cluster-max.md + BUILD_cluster-max-research-library.md + BUILD_cluster-activation.md. Every item below must be verified working on Jimmy before Phase 10 gate:

1. Single non-bare git repo at `/srv/jimmy/research-library/` with `.git/` colocated
2. GitHub remote (`origin`) pushing/pulling from `research-library` private repo
3. LanceDB `research_library` table at `/srv/jimmy/lancedb`, 384-dim MiniLM embeddings
4. Background indexer (300s loop, H2/H3 chunking via `research_chunker.py`, max 2000 chars/chunk)
5. `POST /retrieve` endpoint on `:8100` with vector search + bge-reranker-v2-m3 cross-encoder rerank
6. Context-parity API on `:4500` serving `/context/{model}` bundles
7. Research queue at `.buildrunner/research-queue/{pending,completed}.jsonl`
8. Below handoff worker — llama3.3:70b reformat → qwen3:8b metadata → nomic-embed → commit + reindex
9. Nightly backups to `/srv/jimmy/backups/` + GitHub push cron
10. `br_debug` / decisions log integration
11. Schema validation per `schema.md` (document template, required frontmatter)

---

## Phases

### Phase 1: GitHub Backup — Rollback Anchor

**Goal:** Muddy's research library fully mirrored to a private GitHub repo with history intact, before any other change is made. If everything else goes wrong, we restore from GitHub.
**Effort:** xHigh (irreversible-preventing step)
**Files:**

- `~/Projects/research-library/.git/config` (MODIFY — add remote)
- `.buildrunner/plans/library-backup-manifest.json` (NEW — records file count, byte count, commit SHA)

**Blocked by:** None
**Can parallelize:** No (gate for everything else)

**Tasks:**

#### Task 1.1: Create private GitHub repo `research-library`

- **Goal:** Empty private GitHub repo exists under the user's account, named `research-library`.
- **Context:** User's GitHub account is accessible via `gh` CLI. Repo must be private.
- **Constraints:** No description, no README init, no license init — must be empty so `git push --mirror` lands cleanly.
- **Done-When:** `gh repo view byronhudson/research-library --json visibility,isEmpty` returns `"visibility":"PRIVATE"` and `"isEmpty":true`.

#### Task 1.2: Capture pre-backup manifest on Muddy

- **Goal:** Record current state of Muddy repo for post-push verification.
- **Context:** Muddy repo at `~/Projects/research-library/`, 499 files, 10 MB, latest commit `a6dcbb6`.
- **Constraints:** Store output as JSON at `.buildrunner/plans/library-backup-manifest.json` — fields: `file_count`, `byte_count`, `head_sha`, `branch`, `timestamp`.
- **Done-When:** JSON file exists, `file_count` ≥ 499, `head_sha` matches `git -C ~/Projects/research-library rev-parse HEAD`.

#### Task 1.3: Add GitHub remote and push full history

- **Goal:** Muddy repo's full history pushed to GitHub.
- **Context:** No remote currently configured; single-branch repo.
- **Constraints:** Use `git push --mirror` to push all refs including tags; do not force-push.
- **Done-When:** `git -C ~/Projects/research-library ls-remote origin HEAD` returns same SHA as local HEAD.

#### Task 1.4: Verify file parity remote vs local

- **Goal:** GitHub copy has identical file count and content to Muddy's HEAD.
- **Context:** Clone GitHub repo to a temp dir (`/tmp/rl-verify`), compare file tree.
- **Constraints:** Use `diff -r --brief` after excluding `.git/`; count must match manifest.
- **Done-When:** `diff -r --brief` returns no differences, and `find /tmp/rl-verify -type f ! -path '*/.git/*' | wc -l` equals manifest `file_count`.

#### Task 1.5: Tag the backup commit

- **Goal:** Tag the backup point for rollback reference.
- **Context:** The current HEAD is the state we might need to restore to.
- **Constraints:** Tag name `backup/pre-consolidation-$(date +%Y%m%d)`; push tag to origin.
- **Done-When:** `git -C ~/Projects/research-library tag -l 'backup/pre-consolidation-*'` returns the tag, and `gh api repos/byronhudson/research-library/git/refs/tags` includes it.

**Phase Success Criteria:** GitHub repo contains full history, all files match Muddy, backup tag pushed, manifest JSON saved. Gate: no later phase proceeds until this phase's success criteria are green.
**Rollback:** None needed — this phase is additive. If anything fails, delete the GitHub repo and retry.

---

### Phase 2: Reconcile Conflicting Specs (Paper-Only)

**Goal:** `BUILD_cluster-max-research-library.md` flipped to Jimmy-primary. Remove references to `sync-muddy-to-jimmy.sh`. Both specs now agree: Jimmy is authoritative.
**Effort:** Medium
**Files:**

- `.buildrunner/builds/BUILD_cluster-max-research-library.md` (MODIFY)
- `.buildrunner/builds/BUILD_cluster-max.md` (MODIFY — only if its path/direction language needs tightening)
- `.buildrunner/decisions.log` (MODIFY — log the flip)

**Blocked by:** Phase 1
**Can parallelize:** With Phase 3 (different files)

**Tasks:**

#### Task 2.1: Rewrite the Overview/Decisions section to Jimmy-primary

- **Goal:** Replace every "Muddy-primary / Jimmy-mirror" string with "Jimmy-primary / GitHub-DR / no Muddy copy".
- **Context:** Affected file: `.buildrunner/builds/BUILD_cluster-max-research-library.md`.
- **Constraints:** Preserve all phase numbering and IDs; only wording changes. Flag any phase whose technical content now contradicts the new direction for Task 2.2.
- **Done-When:** `grep -n "Muddy-primary" .buildrunner/builds/BUILD_cluster-max-research-library.md` returns zero hits.

#### Task 2.2: Delete the wrong-direction sync script from the plan

- **Goal:** Remove the `sync-muddy-to-jimmy.sh` deliverable and replace it with a Jimmy→GitHub push step.
- **Context:** Current sub-build ships a sync script; that direction is now wrong.
- **Constraints:** Do NOT write the new script yet — that's Phase 5 of this build. Just update the spec's task list.
- **Done-When:** `grep -n "sync-muddy-to-jimmy" .buildrunner/builds/BUILD_cluster-max-research-library.md` returns zero hits.

#### Task 2.3: Log the decision

- **Goal:** Decision log records the direction flip with rationale.
- **Context:** Uses the existing `br decision log` command.
- **Constraints:** One-line entry, references both build IDs.
- **Done-When:** `tail -1 .buildrunner/decisions.log` contains "Jimmy-primary" and today's date.

**Phase Success Criteria:** Both specs align on Jimmy-primary. No Muddy-primary or `sync-muddy-to-jimmy` strings remain. Decision logged.
**Rollback:** `git checkout -- .buildrunner/builds/BUILD_cluster-max-research-library.md` (pre-Phase-2 state).

---

### Phase 3: Fix Path Mismatch + Prepare Jimmy Storage

**Goal:** Jimmy's code and config agree on a single library path: `/srv/jimmy/research-library/`. No `~/repos/research-library` references remain in active code paths.
**Effort:** Medium
**Files:**

- `~/.buildrunner/cluster.json` (VERIFY — already correct per prior analysis)
- `core/cluster/node_semantic.py` (MODIFY — line 63: change `RESEARCH_DIR` default)
- `core/cluster/lancedb_config.py` (VERIFY)
- Jimmy systemd unit or launch script (MODIFY — set `RESEARCH_DIR=/srv/jimmy/research-library`)
- `/srv/jimmy/research-library/` on Jimmy (NEW — empty directory with correct ownership)
- `/srv/jimmy/backups/` on Jimmy (VERIFY exists)

**Blocked by:** Phase 1
**Can parallelize:** With Phase 2 (different files)

**Tasks:**

#### Task 3.1: Update `node_semantic.py` default path

- **Goal:** `RESEARCH_DIR` default changed from `~/repos/research-library` to `/srv/jimmy/research-library`.
- **Context:** File `core/cluster/node_semantic.py` line 63.
- **Constraints:** Keep the `os.environ.get("RESEARCH_DIR", ...)` pattern — just change the fallback.
- **Done-When:** `grep -n "RESEARCH_DIR" core/cluster/node_semantic.py` shows `/srv/jimmy/research-library` as the default and no `~/repos/research-library` remains.

#### Task 3.2: Set `RESEARCH_DIR` env var on Jimmy's service

- **Goal:** Jimmy's running service explicitly exports `RESEARCH_DIR=/srv/jimmy/research-library`.
- **Context:** Jimmy runs the semantic-search service (likely via systemd or a launch script in `/srv/jimmy/`).
- **Constraints:** SSH to Jimmy; locate the unit/launcher; add the env; reload (do NOT restart yet — restart after Phase 4 when the repo is actually in place).
- **Done-When:** On Jimmy, `systemctl show semantic-search -p Environment` (or equivalent) shows `RESEARCH_DIR=/srv/jimmy/research-library`.

#### Task 3.3: Create `/srv/jimmy/research-library/` with correct ownership

- **Goal:** Empty directory ready to receive the cloned repo.
- **Context:** Runs as the jimmy service user or `byronhudson` — match existing `/srv/jimmy/lancedb` ownership.
- **Constraints:** `mkdir -p` on Jimmy; `chown` to match sibling dirs; permissions `755`.
- **Done-When:** `ssh byronhudson@10.0.1.106 'stat -c "%U:%G %a" /srv/jimmy/research-library'` matches `/srv/jimmy/lancedb`'s owner/group/mode.

#### Task 3.4: Verify backups dir exists

- **Goal:** `/srv/jimmy/backups/` exists on Jimmy.
- **Context:** `cluster.json` declares it but hasn't been verified live.
- **Constraints:** Create if missing; do not alter if present.
- **Done-When:** `ssh byronhudson@10.0.1.106 'test -d /srv/jimmy/backups && echo ok'` prints `ok`.

**Phase Success Criteria:** All path references unified on `/srv/jimmy/research-library/`. Directory exists on Jimmy. Env var set. No dead code paths pointing at `~/repos/research-library`.
**Rollback:** Revert `node_semantic.py` via git; remove env var; `rmdir /srv/jimmy/research-library` (still empty).

---

### Phase 4: Clone GitHub Repo Onto Jimmy

**Goal:** Jimmy has a single non-bare git repo at `/srv/jimmy/research-library/` with `.git/` colocated, origin pointing at GitHub. Full history present.
**Effort:** Medium
**Files:**

- `/srv/jimmy/research-library/` on Jimmy (POPULATE)
- `.buildrunner/plans/jimmy-clone-manifest.json` (NEW)

**Blocked by:** Phase 1, Phase 3
**Can parallelize:** No

**Tasks:**

#### Task 4.1: Clone from GitHub into Jimmy

- **Goal:** `git clone git@github.com:byronhudson/research-library.git /srv/jimmy/research-library` succeeds.
- **Context:** Run over SSH to Jimmy. Jimmy must have a GitHub deploy key or the user's SSH key forwarded.
- **Constraints:** Use SSH remote, not HTTPS. Do NOT copy via rsync — the clone ensures clean provenance from GitHub (rollback anchor).
- **Done-When:** `ssh byronhudson@10.0.1.106 'git -C /srv/jimmy/research-library rev-parse HEAD'` equals Phase 1 manifest `head_sha`.

#### Task 4.2: Verify file parity Jimmy vs Muddy vs GitHub

- **Goal:** All three copies identical at commit level.
- **Context:** Muddy HEAD, Jimmy HEAD, GitHub HEAD should all be the same SHA.
- **Constraints:** Compare SHAs only (faster than diffing file trees).
- **Done-When:** `ssh byronhudson@10.0.1.106 'git -C /srv/jimmy/research-library rev-parse HEAD'` == Muddy HEAD == `gh api repos/byronhudson/research-library/commits/main --jq .sha`.

#### Task 4.3: Restart Jimmy semantic-search service

- **Goal:** Service picks up the new repo location.
- **Context:** Service was configured in Phase 3 but not restarted.
- **Constraints:** Restart, wait 10s, then confirm health.
- **Done-When:** `~/.buildrunner/scripts/cluster-check.sh semantic-search` returns healthy URL.

#### Task 4.4: Confirm indexer picks up repo

- **Goal:** Background indexer runs once and reports chunks loaded.
- **Context:** Indexer runs every 300s.
- **Constraints:** Either wait 300s OR trigger via `reindex-research.sh`.
- **Done-When:** `curl -s http://10.0.1.106:8100/api/research/stats` returns `chunk_count > 0` with a timestamp newer than the service restart.

#### Task 4.5: Save clone manifest

- **Goal:** Record Jimmy repo state for later verification.
- **Context:** Output to `.buildrunner/plans/jimmy-clone-manifest.json`.
- **Constraints:** Same schema as Phase 1 manifest plus `jimmy_head_sha`, `chunk_count`.
- **Done-When:** JSON exists and all SHAs match.

**Phase Success Criteria:** Jimmy holds the full repo, service is healthy, indexer has chunked the library, SHAs match across Muddy/Jimmy/GitHub.
**Rollback:** `rm -rf /srv/jimmy/research-library/*` on Jimmy; Muddy copy still intact.

---

### Phase 5: Jimmy Capability Stack (Retrieve + Rerank + Context-Parity + Backups)

**Goal:** Every library-related capability from BUILD_cluster-max and BUILD_cluster-activation is live on Jimmy. `/retrieve`, cross-encoder rerank, context-parity API, and nightly backup cron all working end-to-end.
**Effort:** Medium
**Files:**

- `api/routes/retrieve.py` (VERIFY — already exists per prior analysis)
- `api/routes/context.py` or similar (VERIFY/MODIFY — for `:4500/context/{model}`)
- `core/cluster/reranker.py` (VERIFY — bge-reranker-v2-m3 wired)
- `core/cluster/scripts/nightly-backup.sh` (NEW)
- Jimmy cron entry (NEW — nightly backup + push to GitHub)
- `core/cluster/schemas/research_document.json` (NEW or VERIFY — schema enforcement)

**Blocked by:** Phase 4
**Can parallelize:** Tasks 5.1–5.5 largely independent within the phase

**Tasks:**

#### Task 5.1: Verify `/retrieve` endpoint end-to-end

- **Goal:** `POST /retrieve` on `:8100` returns ranked chunks against a known query.
- **Context:** Test with a query like "four-element prompts" (known research topic).
- **Constraints:** Request must include the full two-stage flow (vector + rerank); confirm rerank model is `bge-reranker-v2-m3`.
- **Done-When:** `curl -X POST http://10.0.1.106:8100/retrieve -d '{"query":"four-element prompts","top_k":5}'` returns 5 results with `reranker: "bge-reranker-v2-m3"` in response metadata.

#### Task 5.2: Verify context-parity API on `:4500`

- **Goal:** `GET /context/{model}` returns a properly shaped context bundle.
- **Context:** Listed in cluster.json at `:4500`. Unknown if currently live.
- **Constraints:** If service exists but endpoint missing, add it; if service missing, stand it up per cluster-max spec.
- **Done-When:** `curl http://10.0.1.106:4500/context/claude-opus-4-7` returns 200 with JSON containing research bundle.

#### Task 5.3: Write nightly backup script

- **Goal:** Script snapshots `/srv/jimmy/research-library/` + `/srv/jimmy/lancedb/` to `/srv/jimmy/backups/YYYY-MM-DD.tar.zst` and pushes repo to GitHub.
- **Context:** `core/cluster/scripts/nightly-backup.sh`.
- **Constraints:** Idempotent; retains last 14 days only; uses `zstd -T0`; logs to `/srv/jimmy/backups/nightly.log`.
- **Done-When:** `bash core/cluster/scripts/nightly-backup.sh --dry-run` prints planned actions with 0 errors; real run produces a `.tar.zst` in `/srv/jimmy/backups/`.

#### Task 5.4: Install nightly cron on Jimmy

- **Goal:** Cron runs the backup script at 03:00 local daily.
- **Context:** Jimmy's system cron or the `byronhudson` user crontab.
- **Constraints:** Schedule `0 3 * * *`; log redirect to `/srv/jimmy/backups/nightly.log`.
- **Done-When:** `ssh byronhudson@10.0.1.106 'crontab -l | grep nightly-backup'` returns the entry.

#### Task 5.5: Enforce document schema on write

- **Goal:** New documents written to the library must conform to `schema.md` (frontmatter with title, topic, date, sources).
- **Context:** Schema file exists at `~/Projects/research-library/schema.md`.
- **Constraints:** Add a pre-receive hook or validator the Phase 6 worker calls before committing a new doc.
- **Done-When:** Attempting to commit a doc missing frontmatter returns a non-zero exit with a clear "schema violation" message.

**Phase Success Criteria:** All five capabilities verifiable via curl/cron tests. Nightly backup produces an artifact in `/srv/jimmy/backups/`. Schema violations are rejected.
**Rollback:** Disable cron; remove new scripts. `/retrieve` and `:4500` endpoints are read-only, safe to leave running or revert code.

---

### Phase 6: Below Handoff Worker (Research Queue Processor)

**Goal:** Below runs a background worker that consumes `.buildrunner/research-queue/pending.jsonl`, invokes llama3.3:70b → qwen3:8b → nomic-embed, commits the final doc to Jimmy's repo, triggers reindex, and writes to `completed.jsonl`.
**Effort:** Medium (terminal-heavy; use GPT-5.3-Codex for this phase per Codex guidance)
**Files:**

- `core/cluster/below/research_worker.py` (NEW)
- `core/cluster/below/reformat_prompt.md` (NEW — llama3.3:70b template instructions)
- `core/cluster/below/metadata_prompt.md` (NEW — qwen3:8b extraction instructions)
- `core/cluster/below/below_worker.service` (NEW — systemd unit on Below/Windows equivalent)
- `core/cluster/below/queue_schema.py` (NEW)
- `.buildrunner/research-queue/.gitkeep` (NEW)
- `.buildrunner/research-queue/pending.jsonl` (NEW — empty)
- `.buildrunner/research-queue/completed.jsonl` (NEW — empty)

**Blocked by:** Phase 4, Phase 5
**Can parallelize:** With Phase 7 (different files)

**Tasks:**

#### Task 6.1: Queue record schema

- **Goal:** Define the pending/completed record format.
- **Context:** JSONL; one record per line.
- **Constraints:** Fields for pending — `id` (uuid), `title`, `draft_markdown`, `intended_path`, `sources` (array), `created_at`. Fields for completed add — `committed_sha`, `chunk_count`, `status` (`"ok"|"error"`), `error` (optional), `completed_at`.
- **Done-When:** `core/cluster/below/queue_schema.py` defines both dataclasses and a round-trip `to_jsonl`/`from_jsonl` test passes.

#### Task 6.2: Reformat step (llama3.3:70b on Below)

- **Goal:** Given a draft markdown, return a library-template-conformant markdown (frontmatter + H2 structure per `schema.md`).
- **Context:** Below reachable at `http://10.0.1.105:11434/api/generate`.
- **Constraints:** Prompt in `reformat_prompt.md`; temperature N/A (Ollama default ok); hard cap 8k output tokens.
- **Done-When:** Unit test feeds a known draft, asserts output has required frontmatter fields and H2 sections.

#### Task 6.3: Metadata extraction (qwen3:8b on Below)

- **Goal:** Given reformatted markdown, return `{topic, tags, domain, difficulty}` JSON.
- **Context:** Same Ollama endpoint, different model.
- **Constraints:** Prompt in `metadata_prompt.md`; must return strict JSON (no prose wrapper).
- **Done-When:** Unit test validates JSON shape and required keys.

#### Task 6.4: Commit + push to Jimmy

- **Goal:** Worker SSHes to Jimmy, writes file, `git add/commit/push origin main`.
- **Context:** Jimmy is the primary; GitHub is the DR remote.
- **Constraints:** Use a machine account or deploy key; commit message format `research: add <title> [auto]`; push must succeed before queue record moves to completed.
- **Done-When:** End-to-end test: submit a pending record → file appears in Jimmy's repo → visible on GitHub.

#### Task 6.5: Trigger reindex after commit

- **Goal:** Worker calls `core/cluster/scripts/reindex-research.sh` after commit.
- **Context:** Reindex is async; worker waits for `chunk_count` to change or 60s timeout.
- **Constraints:** Non-blocking on indexer errors — record `status: ok` with a `reindex_warning` field if timeout.
- **Done-When:** `completed.jsonl` record shows `chunk_count > 0`.

#### Task 6.6: Worker daemonized on Below

- **Goal:** Worker runs as a service on Below, polls pending queue every 10s.
- **Context:** Below is Windows; use Task Scheduler or WSL systemd equivalent.
- **Constraints:** Restart on crash; logs to `~/AppData/BR3/below-worker.log`; honors shutdown signal.
- **Done-When:** Stop the worker, push a pending record, start worker — record processed within 30s.

#### Task 6.7: Failure modes

- **Goal:** Reformat/metadata/commit errors produce clear `status: error` records with diagnostic info.
- **Context:** Below offline, model OOM, git push rejected, reindex timeout.
- **Constraints:** Never drop a pending record silently. On fatal error, move to `completed.jsonl` with `status: error`; on transient error, retry with backoff (max 3).
- **Done-When:** Simulated failure tests cover all four modes; all produce `status: error` records with populated `error` field.

**Phase Success Criteria:** End-to-end queue round-trip works. A pending record becomes a committed, pushed, reindexed doc within 60s under nominal conditions.
**Rollback:** Stop the worker. Queue stays on disk, can be reprocessed later or processed manually.

---

### Phase 7: Rewrite /research per Cluster-Max Phase 10

**Goal:** `~/.claude/commands/research.md` uses Jimmy `/retrieve` for context, hands off post-synthesis work to Below via the queue, closes the loop on the next turn.
**Effort:** Medium
**Files:**

- `~/.claude/commands/research.md` (MODIFY — full rewrite of Step 0B, Step 8.5, add new Step 9 close-loop)
- `.buildrunner/plans/research-skill-diff.md` (NEW — documents old vs new behavior for review)

**Blocked by:** Phase 5 (retrieve endpoint live), Phase 6 (queue worker live)
**Can parallelize:** With Phase 8 (different files)

**Tasks:**

#### Task 7.1: Replace Step 0B with `/retrieve` call

- **Goal:** Step 0B no longer greps/finds on Muddy; instead POSTs to `http://10.0.1.106:8100/retrieve` with the research query.
- **Context:** Current Step 0B is a `bash grep -r` + `find` block on `~/Projects/research-library/`.
- **Constraints:** Preserve the input query and output shape so downstream synthesis steps don't change. Keep Sonnet 4.6 pin.
- **Done-When:** `grep -n "grep -r" ~/.claude/commands/research.md` returns zero hits in Step 0B region.

#### Task 7.2: Replace Step 8.5 SSH-reindex hack with queue enqueue

- **Goal:** After Claude synthesizes, skill writes a pending record to `.buildrunner/research-queue/pending.jsonl` with the draft, title, intended path, and sources.
- **Context:** Current Step 8.5 SSHes to Jimmy and runs `reindex-research.sh`.
- **Constraints:** Do not block the user on Below's processing — write the record and move on. Skill must not commit the file directly (that's Below's job now).
- **Done-When:** `grep -n "ssh byronhudson@10.0.1.106" ~/.claude/commands/research.md` returns zero hits; new enqueue step present.

#### Task 7.3: Add Step 9 — close the loop on next turn

- **Goal:** At the start of any `/research` invocation, read `completed.jsonl`, match to the previous turn's pending IDs (tracked in session state), report status to user.
- **Context:** Session state lives in `~/.claude/sessions/` or equivalent — use a simple JSON sidecar.
- **Constraints:** If no prior pending records, skip silently. On `status: error`, surface the error message clearly.
- **Done-When:** Two-turn test: turn 1 runs a research query (enqueues), turn 2 runs another — turn 2 reports "Research from turn 1 indexed at <path>, N chunks".

#### Task 7.4: Preserve model pin

- **Goal:** Skill frontmatter still pins `model: claude-sonnet-4-6` with the long-context rationale comment.
- **Context:** 4.7 regressed on long-context (91.9 → 59.2%) — pin is deliberate.
- **Constraints:** Do not upgrade; do not remove the rationale comment.
- **Done-When:** `grep -n "claude-sonnet-4-6" ~/.claude/commands/research.md` returns the pin line.

#### Task 7.5: Failure-mode documentation in skill

- **Goal:** Skill documents what happens when Below offline, Jimmy `/retrieve` unreachable, queue record stale.
- **Context:** Matches Phase 6 failure modes.
- **Constraints:** Inline in the skill so Claude follows them at runtime — not in a separate doc.
- **Done-When:** Skill contains explicit handling for all three cases with user-visible messages.

**Phase Success Criteria:** Running `/research <topic>` produces an immediate Claude synthesis, enqueues a record, and reports completion on the next turn. No direct Muddy file access. No SSH reindex.
**Rollback:** Restore the skill from git; old behavior still works as long as Phase 10 hasn't deleted Muddy.

---

### Phase 8: Enforcement — Block Bypass

**Goal:** Any attempt to read `~/Projects/research-library/` on Muddy is blocked by a hook, and a CLAUDE.md rule declares the violation. Bypass becomes impossible even if someone re-clones the path.
**Effort:** xHigh (security/enforcement boundary)
**Files:**

- `~/.claude/hooks/block-muddy-library.sh` (NEW — PreToolUse hook)
- `~/.claude/settings.json` (MODIFY — register the hook for Read, Bash matchers)
- `~/.claude/CLAUDE.md` (MODIFY — add rule under global rules)
- `/Users/byronhudson/Projects/BuildRunner3/CLAUDE.md` (MODIFY — project-level reinforcement)

**Blocked by:** Phase 7
**Can parallelize:** With Phase 7 (different files) — but better sequenced after so `/research` is ready before the block lands

**Tasks:**

#### Task 8.1: Write PreToolUse hook

- **Goal:** Hook rejects `Read` on `~/Projects/research-library/**` and `Bash` commands containing `~/Projects/research-library` (`cat|grep|find|ls|head|tail`).
- **Context:** Hooks run before tool execution; exit code != 0 blocks.
- **Constraints:** Emit a clear BLOCKED message directing user to `/retrieve` instead. Must handle tilde expansion and absolute path forms.
- **Done-When:** Shell test: `bash ~/.claude/hooks/block-muddy-library.sh Read '{"file_path":"/Users/byronhudson/Projects/research-library/index.md"}'` exits non-zero with "BLOCKED" in stderr.

#### Task 8.2: Register the hook in settings

- **Goal:** Settings activate the hook for `Read` and `Bash` PreToolUse events.
- **Context:** `~/.claude/settings.json` has a hooks section.
- **Constraints:** Use the exact matcher schema (PreToolUse → array of `{matcher, hooks: [...]}`). Do not use `replace_all`. Add, don't clobber.
- **Done-When:** `jq '.hooks.PreToolUse' ~/.claude/settings.json` shows the new matcher entry.

#### Task 8.3: Add CLAUDE.md rule (global)

- **Goal:** Global CLAUDE.md documents: "Research library lives only on Jimmy. Direct reads of `~/Projects/research-library/` on Muddy are a violation — the path should not exist; if it does, escalate to the user."
- **Context:** `~/.claude/CLAUDE.md`.
- **Constraints:** Add to the Global Rules section; one short paragraph; reference `/retrieve` as the only access path.
- **Done-When:** `grep -n "Research library lives only on Jimmy" ~/.claude/CLAUDE.md` returns the rule.

#### Task 8.4: Mirror into project CLAUDE.md

- **Goal:** Project CLAUDE.md carries the same rule (belt and suspenders; project instructions override).
- **Context:** `/Users/byronhudson/Projects/BuildRunner3/CLAUDE.md`.
- **Constraints:** One-liner pointing to the global rule.
- **Done-When:** Project CLAUDE.md grep match.

#### Task 8.5: Document the exception path

- **Goal:** If a developer legitimately needs to edit the library, the documented path is: SSH to Jimmy → edit in `/srv/jimmy/research-library/` → commit + push.
- **Context:** Add to the same CLAUDE.md paragraph as Task 8.3.
- **Constraints:** Plain language; no ambiguity about "when it's ok to read Muddy" (answer: never after Phase 10).
- **Done-When:** Rule paragraph names the SSH-to-Jimmy exception path.

**Phase Success Criteria:** Hook blocks a test read; CLAUDE.md rules in place at both levels; exception path documented.
**Rollback:** Disable the hook in settings (keep the script on disk). Remove the CLAUDE.md lines via git.

---

### Phase 9: End-to-End Verification Gate

**Goal:** Every capability works, every copy is accounted for, every gate green. This is the pre-deletion verification phase.
**Effort:** Medium
**Files:**

- `.buildrunner/plans/phase-9-verification.md` (NEW — results log)

**Blocked by:** Phases 5, 6, 7, 8
**Can parallelize:** Tasks are sequential but each is quick

**Tasks:**

#### Task 9.1: Run 3 real `/research` sessions end-to-end

- **Goal:** Three distinct research topics processed via the new pipeline; each produces a `completed.jsonl` record with `status: ok`.
- **Context:** Topics from actual pending research needs (pick from intelligence alerts or current build needs).
- **Constraints:** Each session measured: time-to-synthesis (user-visible), time-to-index (Below completion), chunk count.
- **Done-When:** Three `completed.jsonl` records exist, all with `status: ok`, and each doc is retrievable via `/retrieve`.

#### Task 9.2: HEAD parity check across all three stores

- **Goal:** Jimmy HEAD == GitHub HEAD.
- **Context:** Muddy HEAD may have diverged if anyone edited during migration — that's ok, we're deleting it next.
- **Constraints:** Compare SHAs; if Muddy diverged, merge any lost commits to Jimmy via PR before proceeding.
- **Done-When:** `ssh byronhudson@10.0.1.106 'git -C /srv/jimmy/research-library rev-parse HEAD'` == `gh api repos/byronhudson/research-library/commits/main --jq .sha`.

#### Task 9.3: Fresh-clone reindex test

- **Goal:** A throwaway clone of the GitHub repo on a different path, reindexed from scratch, produces the same chunk count ± 5%.
- **Context:** Validates that GitHub alone is sufficient for disaster recovery.
- **Constraints:** Use a temp dir on Jimmy like `/tmp/rl-dr-test/`; run the indexer; compare chunk counts; delete the temp dir after.
- **Done-When:** Fresh chunk count within 5% of live `/srv/jimmy/research-library/` chunk count.

#### Task 9.4: Below queue round-trip with induced failure

- **Goal:** Submit 5 pending records, including one designed to fail (invalid draft); verify 4 complete ok, 1 completes with `status: error`.
- **Context:** Proves failure-handling from Phase 6.
- **Constraints:** Use synthetic titles prefixed `test-` so they're easy to remove from the library post-test.
- **Done-When:** 5 records in `completed.jsonl`, status distribution matches expectation; test docs cleaned up.

#### Task 9.5: Enforcement hook live-fire test

- **Goal:** Attempt a `Read` on `~/Projects/research-library/index.md` from the active Claude session; hook blocks it.
- **Context:** Hook was installed in Phase 8.
- **Constraints:** Must produce the specific "BLOCKED" message, not a silent failure.
- **Done-When:** Hook firing confirmed in logs.

#### Task 9.6: Nightly backup dry-run

- **Goal:** Nightly backup script runs successfully and produces a `.tar.zst` in `/srv/jimmy/backups/`.
- **Context:** Phase 5 installed the script and cron.
- **Constraints:** Run the script manually once; don't wait for 03:00.
- **Done-When:** New `.tar.zst` file exists, dated today, non-zero size.

**Phase Success Criteria:** All six verifications green. Results logged to `.buildrunner/plans/phase-9-verification.md`.
**Rollback:** None — this phase is read-only verification. If any task fails, fix the underlying phase, do not proceed to Phase 10.

---

### Phase 10: Delete Muddy Copy (Irreversible, Last)

**Goal:** `~/Projects/research-library/` on Muddy is gone. No stale copies anywhere in the cluster. GitHub is the sole DR copy; Jimmy is the sole live copy.
**Effort:** xHigh (irreversible)
**Files:**

- `~/Projects/research-library/` on Muddy (DELETE)
- `.buildrunner/decisions.log` (MODIFY — log the deletion)
- `~/.buildrunner/scripts/session-start-hook.sh` or equivalent (MODIFY)

**Blocked by:** Phase 9 — ALL tasks green, no exceptions.
**Can parallelize:** No

**Tasks:**

#### Task 10.1: Final Muddy-to-GitHub sanity check

- **Goal:** Muddy HEAD is present in GitHub history (i.e., no uncommitted or unpushed changes would be lost).
- **Context:** Muddy is about to be deleted.
- **Constraints:** If Muddy has commits not in GitHub, push them first. Abort phase if `git status` shows unstaged changes.
- **Done-When:** `git -C ~/Projects/research-library status --porcelain` is empty AND `git -C ~/Projects/research-library log origin/main..HEAD --oneline` is empty.

#### Task 10.2: Scan cluster for other stray copies

- **Goal:** No node in the cluster (except Jimmy) has a `research-library` directory.
- **Context:** Check each node listed in cluster.json: Muddy, Lockwood, Walter, Otis, Lomax, Below.
- **Constraints:** SSH to each; `find ~ -maxdepth 4 -type d -name research-library 2>/dev/null`. If any found, flag to user and delete only after confirmation.
- **Done-When:** Only Jimmy returns a hit.

#### Task 10.3: Delete Muddy repo

- **Goal:** `rm -rf ~/Projects/research-library/` on Muddy succeeds.
- **Context:** Muddy local; user-owned directory.
- **Constraints:** Use `rm -rf`, not Trash. Require an explicit confirmation prompt in the deletion script — this is the only irreversible step.
- **Done-When:** `test -d ~/Projects/research-library` returns 1 (does not exist).

#### Task 10.4: Verify `/retrieve` still works post-deletion

- **Goal:** The `/retrieve` endpoint still returns results — proving Jimmy has everything.
- **Context:** Run the same test query from Phase 5.1.
- **Constraints:** Result count should match Phase 5.1's result.
- **Done-When:** `/retrieve` returns ≥5 results for the test query.

#### Task 10.5: Log final decision

- **Goal:** Decision log records completion of the consolidation.
- **Context:** `br decision log`.
- **Constraints:** One-line entry, references the backup tag and the GitHub repo URL.
- **Done-When:** Log line present.

#### Task 10.6: Update SessionStart brief source

- **Goal:** SessionStart brief no longer references `~/Projects/research-library/` as a local path.
- **Context:** Likely lives in `~/.buildrunner/scripts/session-start-hook.sh` or equivalent.
- **Constraints:** Replace any filesystem path references with `/retrieve` usage notes.
- **Done-When:** Grep for `Projects/research-library` in the hook script returns zero hits.

**Phase Success Criteria:** Muddy copy gone. No stray copies on other nodes. `/retrieve` still green. GitHub remote healthy. Decision logged. Session-start hook updated.
**Rollback:** Restore from GitHub via `git clone git@github.com:byronhudson/research-library.git /srv/jimmy/research-library-restore` (if something catastrophic happens to Jimmy). Muddy restore only by re-cloning from GitHub. GitHub is the permanent rollback anchor from this point on.

---

## Out of Scope (Future)

- Migrating other research directories (e.g., `~/Projects/intelligence/`) — separate build.
- Multi-writer Jimmy setup (currently single-writer via Below worker; if multiple agents write concurrently, queue serializes them).
- Automatic schema migration tools — right now schema is enforced, not migrated.
- Public GitHub repo or read-only mirror for external sharing — out of scope.

---

## Parallelization Matrix

| Phase | Key Files                                                         | Can Parallel (Worktree)        | Blocked By        |
| ----- | ----------------------------------------------------------------- | ------------------------------ | ----------------- |
| 1     | `library-backup-manifest.json`, GitHub repo                       | No (gate)                      | —                 |
| 2     | `BUILD_cluster-max-research-library.md`, `decisions.log`          | With Phase 3                   | 1                 |
| 3     | `node_semantic.py`, Jimmy systemd, `/srv/jimmy/research-library/` | With Phase 2                   | 1                 |
| 4     | Jimmy repo populate, `jimmy-clone-manifest.json`                  | No                             | 1, 3              |
| 5     | `retrieve.py`, context API, `nightly-backup.sh`, cron, schema     | Tasks within phase parallelize | 4                 |
| 6     | `below/research_worker.py`, queue JSONL, Below service            | With Phase 7                   | 4, 5              |
| 7     | `~/.claude/commands/research.md`                                  | With Phase 6/8                 | 5, 6              |
| 8     | `block-muddy-library.sh`, `settings.json`, CLAUDE.md              | With Phase 7                   | 7 (logical order) |
| 9     | `phase-9-verification.md`                                         | No (sequential verification)   | 5, 6, 7, 8        |
| 10    | Muddy deletion, `decisions.log`, session hook                     | No (irreversible)              | 9                 |

---

## AGENTS.md Recommendation (Draft — Human Review Required)

```markdown
# AGENTS.md

## Build & Test

- Test research worker: `python -m pytest core/cluster/below/tests/`
- Lint single file: `ruff check <path>`
- Type-check: `mypy <path>`
- Reindex trigger: `core/cluster/scripts/reindex-research.sh`
- Retrieve test: `curl -X POST http://10.0.1.106:8100/retrieve -d '{"query":"<q>","top_k":5}'`

## Library Access — HARD RULE

- Library lives only at `/srv/jimmy/research-library/` on Jimmy (10.0.1.106).
- Access via `/retrieve` on `:8100`. No other read path is supported.
- Never read, grep, cat, or find against any local `research-library/` path.
- Write path: SSH to Jimmy, commit, push to GitHub origin.

## Queue Conventions

- Pending records: `.buildrunner/research-queue/pending.jsonl`
- Completed records: `.buildrunner/research-queue/completed.jsonl`
- One JSON object per line. Schema in `core/cluster/below/queue_schema.py`.

## Prohibitions

- Do not re-create `~/Projects/research-library/` on Muddy. The block-muddy-library hook will reject reads.
- Do not commit directly to Jimmy's repo from Muddy — go through the Below worker or SSH.
- Do not change the /research skill's model pin (claude-sonnet-4-6 is deliberate).
- Do not add temperature, top_p, top_k, or budget_tokens to any Claude API call in this project.

## Effort Allocation for Codex

- Phase 1, 8, 10: xHigh (irreversibility / security)
- All others: Medium default
```

---

**Total Phases:** 10
**Parallelizable:** Phases 2/3 (paper + Jimmy prep), Phases 6/7/8 (worker + skill + enforcement)
**xHigh Tasks:** Phase 1 (backup), Phase 8 (enforcement hooks), Phase 10 (deletion)
