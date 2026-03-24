# Plan: Phase 3 — Two-Stage Review

## 3.1: Create `~/.claude/docs/begin-review.md`

New reference doc with two review passes:

**Pass 1 — Spec Compliance (subagent):**

- Input: BUILD spec phase section + approved plan + git diff
- Checks: each deliverable implemented? missing? unplanned additions?
- Output: compliance report (PASS/FAIL per deliverable, gaps, unplanned additions)

**Pass 2 — Code Quality (subagent):**

- Input: project CLAUDE.md + git diff + test results
- Checks: TypeScript errors, security (OWASP top 10), dead code introduced, test coverage, performance
- Output: quality report (issues by severity: critical/warning/info)

Sequential: Pass 2 only runs if Pass 1 passes (or user overrides).
Scope constraints per subagent.
Combined output template.

## 3.2: Update `~/.claude/commands/begin.md` Step 5

Replace current single-subagent Step 5 with:

- Reference to `@begin-review.md`
- Two sequential subagent launches
- Combined report
- Gate: Pass 1 must pass before Pass 2 runs

## Tests

TDD Gate: SKIP — all deliverables are markdown skill/doc files. No testable code.
