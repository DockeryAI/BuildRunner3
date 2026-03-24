---
description: Write failing tests for current task, then commit
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
model: opus
---

# Test First

Write failing tests that define success for the current task.

---

## Step 1: Understand What to Test

From the plan or conversation:
- What behavior needs to work?
- What inputs/outputs are expected?
- What edge cases matter?

---

## Step 2: Find Test Patterns

```bash
# Find existing test files
find . -name "*.test.ts" -o -name "*.spec.ts" | head -10

# Check test structure
head -50 $(find . -name "*.test.ts" | head -1) 2>/dev/null
```

Follow existing test conventions in this project.

---

## Step 3: Write Failing Tests

Create test file with:
- Clear test names describing expected behavior
- Tests that WILL FAIL (feature doesn't exist yet)
- No implementation code

**Test naming:** `[feature].test.ts` or `[feature].spec.ts` (match project convention)

---

## Step 4: Verify Tests Fail

```bash
# Run the new tests
npm test -- --testPathPattern="[test-file]" 2>&1 | tail -20
```

**Expected:** Tests should FAIL. If they pass, tests are wrong.

---

## Step 5: Commit Tests

```bash
git add [test-file]
git commit -m "test: add failing tests for [feature]

Tests define expected behavior before implementation.

🤖 Generated with Claude Code"
```

---

## Step 6: Confirm

```markdown
## Tests Created

**File:** `[path/to/test.ts]`
**Tests:** [N] tests written
**Status:** ✅ All failing as expected

**Tests cover:**
- [Test 1 description]
- [Test 2 description]
- [Test 3 description]

**Committed:** [commit hash]

---

Ready to implement. Tests define success criteria.
```

---

## Rules

1. **Tests first** - Write tests before any implementation
2. **Tests must fail** - If they pass, something's wrong
3. **Commit before implementing** - Checkpoint the tests
4. **Match project conventions** - Use existing test patterns
5. **Clear names** - Test names describe expected behavior
