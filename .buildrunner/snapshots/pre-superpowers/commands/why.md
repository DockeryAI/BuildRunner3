---
description: Diagnose console errors - explains what's wrong, why, and how to fix (no code, no action)
allowed-tools: Read, Bash, Grep, Glob
model: opus
---

# Error Diagnosis: /why

**PURPOSE: Understand errors, not fix them.**

---

## Step 1: Detect Project Type & Capture Errors

```bash
# Detect project type
ls package.json pyproject.toml Cargo.toml go.mod 2>/dev/null | head -1
```

### For JavaScript/TypeScript projects:
```bash
# TypeScript errors (if tsc available)
which npx 2>/dev/null && npx tsc --noEmit 2>&1 | grep -E "error TS" | head -30
```

```bash
# Build errors
npm run build 2>&1 | grep -E "error|Error|ERROR" | head -30 || yarn build 2>&1 | grep -E "error|Error|ERROR" | head -30
```

```bash
# Runtime errors (if dev server log exists)
cat .next/trace 2>/dev/null | grep -i error | tail -20 || true
```

```bash
# Test failures
npm test 2>&1 | grep -E "FAIL|Error:|✕" | head -20 || true
```

### For Python projects:
```bash
# Python type errors (if mypy available)
which mypy 2>/dev/null && mypy . 2>&1 | grep -E "error:" | head -30
```

```bash
# Python test failures
pytest 2>&1 | grep -E "FAILED|ERROR|error" | head -20 || python -m pytest 2>&1 | grep -E "FAILED|ERROR" | head -20
```

### For other projects:
Adapt the error capture to the project's build system.

---

## Step 2: Identify Root Causes

**Group errors by root cause.** Many errors cascade from one source.

For each unique error:
1. What file/line?
2. What's the actual problem?
3. Is this a ROOT cause or SYMPTOM of another error?

---

## Step 3: Output Format (STRICT)

```markdown
# Error Diagnosis

## Root Causes ([X] found)

### 1. [Short description]
- **Where:** [file:line]
- **What:** [One sentence - what's broken]
- **Why:** [One sentence - why it's happening]
- **Fix:** [One sentence - how to fix]

### 2. [Next root cause...]

## Cascading Errors ([Y] errors from root causes)

These will resolve when root causes are fixed:
- [Error message] → caused by Root Cause #[N]
- [Error message] → caused by Root Cause #[N]

## Fix Plan (in order)

1. [First fix] → resolves [X] errors
2. [Second fix] → resolves [Y] errors
3. [Third fix] → resolves [Z] errors

**Estimated total errors after fix plan: [0 or remaining count]**
```

---

## Rules

1. **NO CODE** - Describe fixes in plain English
2. **NO ACTION** - Diagnose only, do not fix anything
3. **CONCISE** - One sentence per field, no paragraphs
4. **ROOT CAUSES FIRST** - Don't list 50 errors, find the 3 that cause them
5. **ORDER MATTERS** - Fix plan should be in dependency order

---

## Example Output

```markdown
# Error Diagnosis

## Root Causes (2 found)

### 1. Missing export in auth module
- **Where:** src/lib/auth.ts:45
- **What:** `AuthProvider` is not exported but imported elsewhere
- **Why:** Function was made private during refactor
- **Fix:** Add `export` keyword to AuthProvider function

### 2. Type mismatch in API response
- **Where:** src/api/users.ts:23
- **What:** API returns `string` but code expects `number` for userId
- **Why:** Backend changed response format, frontend not updated
- **Fix:** Update User type to use string for userId field

## Cascading Errors (12 errors from root causes)

These will resolve when root causes are fixed:
- "Cannot find name 'AuthProvider'" (x5) → caused by Root Cause #1
- "Type 'string' not assignable to 'number'" (x7) → caused by Root Cause #2

## Fix Plan (in order)

1. Export AuthProvider in auth.ts → resolves 5 errors
2. Update User.userId type to string → resolves 7 errors

**Estimated total errors after fix plan: 0**
```

---

## What This Command Does NOT Do

- ❌ Write any code
- ❌ Make any changes
- ❌ Run fixes
- ❌ List every single error (find root causes instead)
- ❌ Explain in paragraphs (one sentence max)
