# Canonicalization Decision — Muddy Primary, Jimmy Mirror

**Decided:** 2026-04-21
**Build:** `BUILD_cluster-max-research-library` — Phase 1
**Status:** FINAL (see `.buildrunner/decisions.log` for audit trail)

## Decision

Muddy (`10.0.1.100`) is the canonical authoring and source-of-truth node.
Jimmy (`10.0.1.106`) is the read-only mirror + semantic-search / `/retrieve`
service host.

Direction is one-way: **Muddy → Jimmy**. Any script that syncs the other
direction is a bug.

## Rationale

1. Muddy is where humans edit code and specs. Editing on two hosts invites
   divergence and "last write wins" accidents.
2. Jimmy runs the `/retrieve` API and LanceDB index. Reads are cheap to serve
   from a mirror; writes need a single owner.
3. The existing BR3 governance (AGENTS.md, decisions.log, CLAUDE.md) already
   assumes Muddy owns history. Making Jimmy primary would require a second
   governance tree and a merge protocol we do not want to build.

## Alternative Considered — Jimmy Primary

- **Pros:** Jimmy is on 24/7, runs the semantic index locally, no network hop
  for reindex jobs.
- **Cons:** Muddy is where humans work. Authoring on a headless node requires
  every edit to traverse SSH; editor/IDE integrations, git hooks, and skill
  state (`.buildrunner/skill-state.json`) all assume local-FS. The failure
  mode (developer edits on Muddy, reindex runs from Jimmy, they disagree) is
  the exact bug this decision prevents.
- **Rejected because:** authoring-on-mirror doubles the complexity for zero
  gain — every change still has to land on Muddy for review/commit.

## Affected Scripts

- `~/.buildrunner/scripts/nightly-projects-backup.sh` — target is
  `/srv/jimmy/backups/` on Jimmy (Muddy → Jimmy rsync).
- `~/.buildrunner/scripts/sync-muddy-to-jimmy.sh` — canonical direction.
- `~/.buildrunner/scripts/sync-jimmy-to-muddy.sh` — must not exist. If it
  appears, delete and log.
- `~/.buildrunner/scripts/migrate-lockwood-data.sh` — pushes LanceDB rows
  from Lockwood (transitional) to Jimmy.
- `~/.buildrunner/scripts/jimmy-storage-init.sh` — creates canonical layout
  under `/srv/jimmy/{research-library,lancedb,backups}`.
- `~/.buildrunner/scripts/jimmy-verify.sh` — asserts canonical dirs exist,
  owned by `byronhudson:byronhudson`, 755, writable.

## Rollback

If a reversal is ever required (e.g. Muddy dies, Jimmy becomes primary):

1. Freeze all writes on Muddy. `chmod -w ~/Projects/` (or equivalent).
2. Run `sync-muddy-to-jimmy.sh --live` one final time. Verify exit 0 and
   matching file counts on both sides.
3. Invert the rsync direction: create `sync-jimmy-to-muddy.sh` with the
   new canonical-direction comment; delete `sync-muddy-to-jimmy.sh`.
4. Update this file with the new decision + date. Commit.
5. Update `core/cluster/AGENTS.md` "Canonical Host" section to match.
6. Update `.buildrunner/decisions.log` with the reversal rationale.

## Enforcement

- `core/cluster/AGENTS.md` names the canonical host in its top-of-file
  "Canonical Host" section.
- `~/.buildrunner/scripts/verify-retrieve-host.sh` (Phase 7) asserts the live
  `/retrieve` endpoint resolves to Jimmy.
- The BUILD spec for any future cluster work MUST reference this document
  before introducing a new sync script.
