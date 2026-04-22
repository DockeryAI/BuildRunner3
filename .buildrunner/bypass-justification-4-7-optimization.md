# Adversarial Review Bypass — Spec: Claude 4.7 Optimization Sweep

**Date:** 2026-04-21
**Plan file:** `.buildrunner/plans/spec-draft-4-7-optimization.md`
**Review artifact:** `.buildrunner/adversarial-reviews/phase-0-20260421T224442Z.json`
**Verdict from arbiter:** BLOCKED (2 blockers, 4 notes, 30.4s review at xhigh on claude-opus-4-7)
**Bypass type:** Inline-fix-and-continue per /spec Step 3.7 ("On BLOCKED → fix blockers inline, auto-bypass 3.7, proceed to 3.8").

## Blockers fixed inline

1. **anthropic SDK v0.74.1 does not expose `output_config`.**
   Fix: Phase 1 now has an SDK-prerequisite deliverable — pin to a SDK version that supports `output_config`, OR route via `extra_body={"output_config": {...}}` as interim. Test asserts the pinned version.

2. **`message.content[0].text` crashes when adaptive thinking puts `ThinkingBlock` first.**
   Fix: Phase 1 deliverable replaces every `content[0].text` with a type-filtered accessor `next((b.text for b in message.content if getattr(b, "type", None) == "text"), "")` at all 4 call sites and any content-parsing helper. Tests verify via mock.

## Notes addressed inline

3. Phase 4 pre-edit audit added — skip skills already carrying 4.7 frontmatter (e.g. `audit-site.md`).
4. Phase 2 verb changed from "add" to "change" for `/learn`, `/research`, `/cluster-research` frontmatter (they already carry `model: opus` alias); alias-resolution check added.
5. Phase 1 `max_tokens` right-sized per method (pre_fill_spec 16k / analyze_requirements 4k / generate_design_tokens 4k / validate_spec 2k), replacing the blanket 64k to avoid cost exposure under 1.0–1.35× tokenizer inflation.
6. Execution order reconciled with parallelization matrix — replaced linear 1→2→3→4 shorthand with wave-based ordering (A={1,2,4,8} → B=3 → C=5 → D=6 → E=7).
7. `validate_spec` effort tier changed xhigh → medium (aligns with "medium for lint-grade / classification" guidance).

## Path fixes (from architecture validation 3.8)

- Removed `~/.claude/commands/security-review.md` from MODIFY list — it is a Claude-Code-provided plugin skill with no user-owned file. Pattern documented via CLAUDE.md instead.
- Corrected `~/.claude/skills/br3-frontend-design/` → `~/.claude/skills/br3-frontend-design/SKILL.md`.
- Corrected `~/.claude/skills/br3-planning/` → `~/.claude/skills/br3-planning/SKILL.md`.
- Corrected `~/.buildrunner/hooks/session-start.sh` → `~/.buildrunner/scripts/developer-brief.sh` (real SessionStart hook location).

## Why inline fix, not re-run

Per /spec Step 3.7: "HARD STOP — EXACTLY ONE REVIEW PER SPEC. THEN BUILD. On BLOCKED → fix the surfaced blockers inline in the draft plan, auto-bypass 3.7, proceed to 3.8. Do NOT re-run the review." All 6 findings were concrete and fixable from the draft text. None required a product decision or >50% plan rewrite.

## Risk assessment

- Scope is documentation + config work (markdown, bash, Python client knobs). No production code path, no DB, no API surface.
- Every phase is independently reversible.
- Phase 1 Python edits covered by a new unit test (`tests/test_opus_client_4_7.py`) asserting param shapes, SDK pin, and `ThinkingBlock`-first mock handling.
- User explicitly invoked `/spec` for this work and set priority order.

Bypass authorized.
