# Phase 4 Plan: Parallel Subagent Task Execution

## Task 4.1: Dependency analysis section in Step 4
- Insert dependency analysis after plan approval, before execution
- Analyze task file lists for overlaps
- Output dependency graph as text

## Task 4.2: Parallel dispatch logic in Step 4
- 3+ independent tasks → dispatch as parallel subagents
- Subagent constraints with soft 4.6 language
- Model guidance (sonnet for simple, opus for complex)
- Fallback to sequential for <3 tasks or shared files

## Task 4.3: Heartbeat update for parallel execution
- Update heartbeat after each subagent completes

## Tests
TDD Gate: SKIP — all deliverables are skill markdown files. No testable code.
