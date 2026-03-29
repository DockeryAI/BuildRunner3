# Phase 10.5 Plan: Validation & Enforcement Fixes

## Tasks

1. Add build-contract.json artifact after Step 3.4 constraint sheets (new Step 3.4b)
2. Add 60° minimum hue distance check to Step 2d color derivation (after Step 6: Session Randomization)
3. Add logo enforcement multishot example to Step 4.3 (after rule 16)
4. Add content variety build rule to Step 4.3 rule 6
5. Rewrite Step 4.4 validation to mandate Read tool + diff against build-contract.json
6. Add validation multishot example (PASS/FAIL with extracted values)
7. Soften all "Hard Gate"/"ENFORCED"/"CRITICAL" language throughout Steps 3-4.4

## Approach
- All edits to ~/.claude/commands/design.md
- Sequential edits, commit per logical task
- No tests (this is a prompt/skill file, not code)
