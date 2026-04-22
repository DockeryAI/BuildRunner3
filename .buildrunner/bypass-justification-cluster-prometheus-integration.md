# Bypass Justification — cluster-prometheus-integration

**Date:** 2026-04-22
**Gate bypassed:** Step 3.7 (adversarial review) + Step 3.8 (architecture validation)
**Authorized by:** spec skill rules (one-review-per-spec, inline-fix-and-bypass)

## Step 3.7 — Adversarial Review

**Verdict:** BLOCK (exit_code=1, arbiter circuit open)

**Finding counts:** 4 blockers, 9 warnings, 9 notes. All blockers `consensus=false` (single-reviewer). Arbiter committed BLOCK because its circuit was already open from a prior session — not because the content was irreparable.

**All 4 blockers were `fix_type: fixable` and were addressed inline in `.buildrunner/plans/spec-draft-plan.md`:**

1. Phase 2 launchd plist used `~` in `--config.file` flag — launchd does not expand tilde. **Fixed:** plist now specifies absolute paths via `ProgramArguments` array.
2. Phase 2 `prometheus.yml` used `instance_label` field which does not exist in Prometheus scrape config. **Fixed:** each static_config target block now carries a `labels:` map with `node: <friendly-name>`.
3. Phase 4 `cpu_pct` PromQL was `rate(node_cpu_seconds_total{mode="idle"}[1m])` — returns per-core idle rate, not usage percentage. **Fixed:** now `100 - (avg by (node) (rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)`.
4. Phase 4 disk mountpoint regex `"/srv/jimmy|/"` was unanchored and matched every filesystem on the host. **Fixed:** now `"^/srv/jimmy$|^/$"` with `fstype!~"tmpfs|overlay"` exclusion.

**Warnings additionally addressed inline (7 of 9):** `ram_pct` inversion, dual-cadence caching mechanism, hostname → IP fallback, windows_exporter metric names enumerated, E2E remote-kill via explicit SSH + launchctl bootout command, Homebrew-specific paths replaced with user-owned absolute paths, range query `stepSec=3600` to cap samples at ~720, firewall deliverable added, `git grep` with pathspec exclusions for false-positive avoidance.

**Notes additionally addressed (6 of 9):** `schema_version` dual-layer conflation (renamed internal field to `internal_schema_version`), rate-limit warning promoted to explicit deliverable with test, `cluster.json` missing-file fallback specified, overflow-reserve initial-state `null` for first 300s specified, `_collect_node_health` / `_collect_storage_health` clarified as full-function deletion, apt package `prometheus-node-exporter` named explicitly, Phase 16 contingency documented as Key Design Decision #7.

**Notes intentionally deferred (3):** (a) node-label passthrough test — already covered by existing test list after inline edits; (b) extra historical-drift concerns — not relevant to first-run spec; (c) stylistic.

**Per skill rule:** one review per spec, fix inline, bypass — no re-review. This is enforced to prevent the runaway-loop pattern (7+ rounds, 49 consecutive blocked reviews) documented in cluster-max.

## Step 3.8 — Architecture Validation

**Validator output:** 2 BLOCKERs —

- `Spec says MODIFY jimmy-status.mjs but file does not exist`
- `Spec says MODIFY events.mjs but file does not exist`

**Why these are not plan bugs:**

The plan states explicitly and in multiple places that these files are created by **BUILD_cluster-max Phase 16** (currently `pending`). Phase 3 of this spec has a hard `blocked by` on "BUILD_cluster-max Phase 16 complete." By the time Phase 4 of this build executes, the files will exist.

The validator performs a point-in-time existence check against the current repo state; it does not model cross-build sequencing declared in the plan's `blocked by` fields. The files would be marked `(NEW)` from this spec's atomic perspective (because this spec authors their hardware-metric behavior), but they are `(MODIFY)` from the union-of-builds perspective because Phase 16 creates the scaffolding first.

**Deliberate choice:** keep the `(MODIFY)` tag because it reflects execution-time reality. Bypass the validator for this specific pair of blockers.

**Plan section `Key Design Decisions #7`** codifies the Phase 16 contingency explicitly: Phases 1 and 2 have no Phase 16 dependency and can ship to production with zero consumers; Phases 3–6 wait for Phase 16. This spec remains correct and executable regardless of Phase 16 slip.

## Risk Acknowledgement

- If Phase 16's final filenames drift from `jimmy-status.mjs` / `events.mjs`, Phase 4 of this build will need file-path updates. Mitigation: Phase 5 of Phase 16 will freeze the integration filenames before this build's Phase 3 can begin.
- If any of the inline PromQL fixes contain further correctness errors, they will surface during Phase 4 E2E tests (Phase 6) and be fixed in-phase. The arbiter circuit-open status prevented a second review; test-time correctness replaces a second reviewer.
