# Plan: Phase 6 — Git Worktree Integration

## 6.1 — Update begin-locks.md

- Add option 3 to Lock Found Prompt template
- Add handler for option "3" → invoke /worktree with parallel phase build plan
- Branch naming: br3/phase-[N]-[short-desc]
- Add "Worktree Dispatch" subsection under Find Parallel Work

## 6.2 — Update begin-completion.md

- Add worktree detection (git worktree list)
- If in worktree: output merge guidance after lock release
- Present commands for user confirmation, do NOT auto-execute

## 6.3 — Update begin.md

- Add option 3 to lock detection output block in Step 1
- Add handler for "3" or "worktree"

## Tests

TDD Gate: SKIP — all deliverables are skill/command markdown files.
