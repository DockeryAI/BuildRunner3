# Prior-State Survey — BR3 Cleanup (Wave A/B/C)

**Build slug:** `br3-cleanup-wave-abc`
**Date:** 2026-04-23
**Trigger:** prior_builds=51 + shared_surface_touched (core/, .buildrunner/scripts/, governance.yaml, cluster.json, ui/)

---

## Prior BUILDs

- **`burnin-harness`** (active, 11 phases COMPLETE, Phase 12 PLANNED) — Phase 12 plan is the natural home for Wave D1 burn-in cases against `dispatch-to-node.sh`, `ship-runner.sh`, `cross_model_review.py`. **Action:** this spec defers Wave D1 to that build.
- **`cluster-library-consolidation`** (10 phases) — closest cleanup precedent. Established the "delete the duplicates after consolidating to a single source of truth" pattern this spec reuses for `JIMMY_URL`/`BELOW_HOST` (Phase 3) and root-level RLS docs (Phase 4). No file-level overlap.
- **`dev-discipline-gates`** — established the pre-commit/pre-push hook structure that Phase 6 collapses. Confirms `pre-commit-enforced` and `pre-push-enforced` are the canonical variants.
- **`rock-solid-build-tracking`** — touched dispatch surfaces; informs Phase 6 reconciliation of `dispatch-to-otis.sh` vs `dispatch-phase-to-otis.sh`.
- **`ship-self-healing-prepush`** — established `pre-push.d/50-ship-gate.sh` append pattern. Phase 6 must preserve the auto-append when collapsing pre-push hooks.
- **`cluster-prometheus-integration`** + **`cluster-dashboard-prometheus-surfacing`** — touched `cluster.json` and Below; Phase 1 must not contradict the Prometheus-port additions.
- **`cluster-max`** — has open status referencing the unapplied `adversarial-review.sh.patch-phase5`. Phase 4 reconciles that status.
- **`claude-4-7-optimization`** — established the autopilot prefix pattern; Phase 1 changes to `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING` must respect the 4.7 posture rules in global CLAUDE.md.

## Shared-Surface Impact

- **`core/cluster/*.py`** — Phase 2 (race fixes) + Phase 3 (constants consolidation) + Phase 5 (dead module deletion) all touch this tree. **Mitigation:** strict serialization (Phase 3 blocked-by Phase 2; Phase 5 blocked-by Phase 3).
- **`core/persistence/*.py`** — Phase 2 only. No active callers will break: `database.py`, `event_storage.py`, `metrics_db.py` are leaf modules consumed by api routes that already handle exceptions.
- **`.buildrunner/scripts/`** — Phases 1, 3, 6 all touch. File sets diverge (Phase 1: ship/autopilot config; Phase 3: developer-brief, collect-intel; Phase 6: hooks + dispatch wrappers + load-role-matrix). No same-file conflict.
- **`governance.yaml`** — Phase 1 only. Single source of truth after coverage-threshold unification. Other governance consumers (autopilot, ship-runner) read this file at runtime — schema changes to coverage_threshold key would break them; Phase 1 only changes the value, not the key.
- **`~/.buildrunner/cluster.json`** — Phase 1 adds `vram_required_gib` + `ollama_port` to Below entry, strips 70B model declarations. Phase 3 reads cluster.json via `cluster_config.py`. **Risk:** any consumer that hardcodes a list of Below models will break when 70B is stripped. Audit needed in Phase 1.
- **`ui/src/components/`** — Phase 5 deletes orphans; Phase 7 prunes deps. No overlap (Phase 5 deletes files; Phase 7 deletes package.json entries).
- **Root-level `.md`/`.png`/`.sql`** — Phase 4 only. Other phases read CLAUDE.md (which stays); no other phase touches the docs being archived.

## Governance Drift

- `governance.yaml:87` enforces `coverage_threshold: 90` with `block_commit: true` + `block_push: true`. Phase 1 keeps 90 as canonical (raises `quality-standards.yaml`'s 85 to match by reference, not by value).
- `governance.yaml:174-185` has `quality.thresholds.overall: 50` with a "temporarily lowered, target 70+" note. Phase 1 does NOT raise this — out of scope for this spec; would require Walter sweep first.
- `~/.buildrunner/config/default-role-matrix.yaml` defines bucket → primary-model + effort + reviewers. This spec uses standard buckets only (`terminal-build`, `backend-build`, `architecture`, `qa`); no per-phase model/effort overrides needed.
- `architecture: muddy/below/jimmy preferred` — Phase 4 (architecture bucket) on muddy is fine.
- No `governance.yaml` rule prohibits mass file deletion in Phase 4; per-deletion `decisions.log` append is the audit trail.

## Completed-Phase Blast Radius

- **`burnin-harness` Phase 1-11 (COMPLETE)** — touched `.buildrunner/plugins/{walter,below,sharding}/` and `/burnin` skill registry. This spec does NOT touch those directories. No collision.
- **`cluster-library-consolidation` (all phases)** — established `/srv/jimmy/research-library/` SSOT. This spec does NOT touch the research library, only queries Jimmy's `/api/memory/note` endpoint. No collision.
- **`cluster-activation` Phase 5 patch** — `adversarial-review.sh.patch-phase5` was staged but never applied. Phase 4 of this spec resolves that explicitly (apply or discard, then update `BUILD_cluster-max.md` status). **This is the only completed-phase blast radius worth surfacing — and it's a known-bad state, not a regression risk.**
- **`ship-self-healing-prepush`** — Phase 6 collapses pre-push hooks. The auto-appended `50-ship-gate.sh` MUST be preserved or re-appended after consolidation. Phase 6 deliverable explicitly calls this out.
- **`claude-4-7-optimization`** — autopilot dispatch prefix is from this build. Phase 1's change to `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING` must be coordinated with the prefix logic. Decision required in Phase 1: trust env var (delete prefix injection) OR trust prefix (delete env var). Both are valid; document the choice.

---

**Summary:** No phase in this spec re-modifies a completed phase's deliverable destructively. The single known-bad legacy state (`patch-phase5`) is explicitly addressed in Phase 4. All shared-surface overlaps are serialized via blocked-by ordering (2→3→5).
