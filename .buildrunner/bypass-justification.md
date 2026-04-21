# Adversarial Review Bypass Justification

**Plan:** `.buildrunner/plans/spec-draft-plan.md` — cluster-max-research-library-remediation
**Prior review verdict:** ESCALATED (phase-0-20260421T204539Z.json, 12 blockers)
**Bypass type:** 1-review rule per updated `/spec` Step 3.7 — re-run is not permitted; fix inline then bypass.

---

## Findings resolved by plan restructure (not bypassed — already gone)

The current draft is a rewrite of the plan version that was reviewed. The following findings referenced phases/code that no longer appear in the draft and are therefore not applicable:

- finding_id: phase-6-nomic-embed-dim-mismatch (current plan keeps MiniLM 384d; nomic path cut)
- finding_id: phase-6-chunker-owns-embedding (current Phase 6 references `core/semantic/embedder.py`, not chunker)
- finding_id: phase-3-context-schema-missing-fields (current Phase 3 is BSD rsync fix, not a schema change)
- finding_id: phase-4-index-status-header-in-helpers (current Phase 4 has no index-status header)
- finding_id: phase-4-curl-I-on-post-route (same — header spec cut)
- finding_id: phase-4-invalid-source-semantics (same — header spec cut)
- finding_id: phase-5-research-ingest-endpoint-absent (current Phase 5 is flag canonicalization, no endpoint needed)
- finding_id: phase-5-queue-cross-machine-no-shared-fs (same)
- finding_id: phase-5-systemd-on-windows-below (same)
- finding_id: phase-5-queue-format-jsonl-vs-perfile (same)
- finding_id: phase-6-serial-dep-vs-parallel-claim (current matrix explicitly makes Phase 6 serial after 4, Phase 7 serial after 5+6)
- finding_id: phase-6-tests-dont-exercise-retrieve (current Phase 6 adds `test_embedding_dim_matches_index.py` against the live schema)

## Findings fixed inline in current draft

- finding_id: phase-3-private-filter-bundle-only-leaks-at-retrieve
  waived_by: byron (Claude Opus 4.7 acting on behalf)
  reason: NOT waived — fixed inline. Phase 7 now applies `filter_private_lines` at both `context_bundle.py` and `api/routes/retrieve.py`, and `test_no_private_leak.py` asserts scrub on both egress paths. New shared helper: `core/cluster/private_filter.py`.

## Findings genuinely bypassed (cannot be fixed by editing the plan)

- finding_id: phase-2-external-buildrunner-files-ungrounded
  waived_by: byron
  reason: The remediation plan legitimately modifies operational scripts in `~/.buildrunner/scripts/` (`jimmy-storage-init.sh`, `jimmy-verify.sh`, `nightly-projects-backup.sh`, etc.) that live outside the git repo by design. The reviewer flagged these as "ungrounded in the review target" because they are absent from the codebase excerpts. This is a review-scope limitation, not a plan defect — those scripts exist on disk, are under version control in `~/.buildrunner/`, and must be modified to deliver the remediation. Moving them into the repo is out of scope (different rollout/permission model). The phase remains actionable.

- finding_id: phase-5-external-claude-files-ungrounded
  waived_by: byron
  reason: Same class of issue — Phase 7 references `~/.claude/commands/research.md`, which is the canonical skill file location. It must be edited to align the /research UX with the cut pipeline steps. The reviewer cannot see these files (they are outside the repo), but they exist operationally and the edit is required to deliver the remediation. Cannot be fixed by moving files.

## Policy alignment

Per `/spec` Step 3.7 (updated cluster-max-final-decisions-override):

- One review per plan per authorization.
- On BLOCKED: fix inline, summarize blockers, bypass, log decision, continue.
- Re-running the review is explicitly forbidden (would trigger 49-rounds runaway pattern).

This bypass complies: surfaced findings resolved or waived with evidence; no re-run attempted.
