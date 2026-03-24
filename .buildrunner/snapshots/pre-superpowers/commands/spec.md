---
description: Strategic project planning - define phases and create BUILD spec
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, AskUserQuestion
model: opus
---

# Strategic Project Spec

Design project phases, create BUILD spec. Works from any directory.

---

## Step 0: Locate Project Root

```bash
# Find project root (git root or current directory)
git rev-parse --show-toplevel 2>/dev/null || pwd
```

All files will be created relative to project root.

---

## Step 1: Understand the Project

What is the user trying to build? Gather from:

- This conversation
- Any existing PROJECT_SPEC.md or requirements
- User's description

If unclear, use AskUserQuestion to clarify:

- Core purpose (what problem does it solve?)
- Target users (who is this for?)
- Must-have vs nice-to-have features
- Technical constraints (stack, integrations, etc.)

---

## Step 2: Analyze Scope

Think deeply about the full scope:

1. **Core Features** - What MUST exist for v1?
2. **Supporting Features** - What enables the core?
3. **Infrastructure** - Auth, database, API patterns
4. **Dependencies** - What blocks what?

Create a mental model of the entire system before breaking into phases.

---

## Step 3: Define Phases

Break the project into phases with clear boundaries.

**Phase Design Principles:**

- Each phase delivers working functionality (not half-built features)
- Phase N must be complete before Phase N+1 starts
- Each phase is testable independently
- Max 10 tasks per phase (hard limit — split if more)
- Later phases can be cut without breaking earlier work
- **List FILES explicitly** - Every phase must specify which files it creates/modifies

**Typical Phase Pattern:**

1. **Foundation** - Core infrastructure, auth, database schema
2. **Core Feature** - The main thing the app does
3. **Supporting Features** - Things that enhance the core
4. **Polish** - Edge cases, error handling, UX improvements

---

## Step 3.5: Parallelization Analysis

**After defining phases, analyze which can run in parallel.**

For each phase, extract the FILES it will touch:

- Parse deliverables for file paths, component names, edge functions
- Mark each file as (NEW) or (MODIFY)
- Example: "Create useContentMix hook" → `src/hooks/useContentMix.ts (NEW)`
- Example: "Update InstagramMockup" → `src/components/InstagramMockup.tsx (MODIFY)`

**Compare file lists across phases:**

- **Blocks** = Phase X modifies same files as Phase Y → cannot parallelize
- **After** = Phase X logically follows Phase Y but different files → CAN parallelize

**Output a Parallelization Matrix:**

```markdown
## Parallelization Matrix

| Phase | Key Files                     | Can Parallel With | Blocked By     |
| ----- | ----------------------------- | ----------------- | -------------- |
| 1     | supabase/functions/auth/      | -                 | -              |
| 2     | src/components/Dashboard/\*   | 1                 | -              |
| 3     | supabase/functions/auth/      | 2                 | 1 (same files) |
| 4     | src/hooks/useNewFeature (NEW) | 1, 2, 3           | -              |
```

**This matrix is REQUIRED in the final spec.**

---

## Step 4: Output Format

Present the spec for approval:

```markdown
## Project Spec: [Name]

**Purpose:** [One sentence - what problem this solves]
**Target Users:** [Who uses this]
**Tech Stack:** [Framework, database, key dependencies]

---

### Phase 1: [Name]

**Goal:** [What's working at end of this phase]
**Files:**

- path/to/file1.ts (NEW)
- path/to/file2.tsx (MODIFY)
  **Blocked by:** None
  **Deliverables:**
- [ ] [Specific deliverable 1]
- [ ] [Specific deliverable 2]
- [ ] [Specific deliverable 3]

**Success Criteria:** [How we know it's done]
**Can parallelize:** [Yes/No - which deliverables are independent]

---

### Phase 2: [Name]

**Goal:** [What's working at end of this phase]
**Files:**

- path/to/different/file.ts (NEW)
- path/to/another.tsx (MODIFY)
  **Blocked by:** None (different files than Phase 1)
  **After:** Phase 1 (logical sequence, but CAN run in parallel)
  **Deliverables:**
- [ ] [Specific deliverable 1]
- [ ] [Specific deliverable 2]

**Success Criteria:** [How we know it's done]

---

### Out of Scope (Future)

- [Feature that's not in this build]
- [Nice-to-have that can wait]

---

## Parallelization Matrix

| Phase | Key Files | Can Parallel With | Blocked By |
| ----- | --------- | ----------------- | ---------- |
| 1     | [files]   | -                 | -          |
| 2     | [files]   | 1                 | -          |
| ...   | ...       | ...               | ...        |

---

**Total Phases:** [N]
**Parallelizable:** [List which phases can run together]

Type "go" to create BUILD spec, or adjust the plan.
```

---

## Step 5: Create Build File (After "go")

### 5.1 Ensure Directory Exists

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
mkdir -p "$PROJECT_ROOT/.buildrunner/builds"
```

### 5.1.5 Detect Deploy Target

Before writing the BUILD file, detect the project's deployment target:

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
if [ -f "$PROJECT_ROOT/capacitor.config.ts" ] || [ -f "$PROJECT_ROOT/capacitor.config.json" ]; then
    echo "capacitor"
elif [ -f "$PROJECT_ROOT/wrangler.toml" ] || [ -f "$PROJECT_ROOT/wrangler.jsonc" ]; then
    echo "cloudflare"
elif grep -q '"electron"' "$PROJECT_ROOT/package.json" 2>/dev/null; then
    echo "electron"
elif grep -q '"expo"' "$PROJECT_ROOT/package.json" 2>/dev/null; then
    echo "expo"
elif [ -f "$PROJECT_ROOT/tauri.conf.json" ]; then
    echo "tauri"
else
    echo "web"
fi
```

Write the detected target into the BUILD spec `Deploy:` field.

### 5.2 Create BUILD\_[name].md

Write to `$PROJECT_ROOT/.buildrunner/builds/BUILD_[name].md`:

```markdown
# Build: [Name]

**Created:** [DATE]
**Status:** Phase 1 In Progress
**Deploy:** [detected type] — `[detected command]`

## Overview

[Brief description]

## Parallelization Matrix

| Phase | Key Files | Can Parallel With | Blocked By |
| ----- | --------- | ----------------- | ---------- |
| 1     | [files]   | -                 | -          |
| 2     | [files]   | 1                 | -          |

## Phases

### Phase 1: [Name]

**Status:** in_progress
**Files:**

- path/to/file.ts (NEW)
  **Blocked by:** None
  **Deliverables:**
- [ ] [Deliverable 1]
- [ ] [Deliverable 2]

### Phase 2: [Name]

**Status:** not_started
**Files:**

- path/to/other.ts (NEW)
  **Blocked by:** None
  **After:** Phase 1 (logical sequence, CAN parallelize)
  **Deliverables:**
- [ ] [Deliverable 1]

[Continue for all phases...]

## Session Log

[Will be updated by /begin]
```

### 5.3 Update PROJECT_SPEC.md (if exists)

If `PROJECT_SPEC.md` exists, add the features.

### 5.4 Log Decision

```bash
br decision log "Created build spec: [name] with [N] phases" 2>/dev/null || \
echo "[$(date)] [DECISION] Created build spec: [name] with [N] phases" >> "$PROJECT_ROOT/.buildrunner/decisions.log"
```

---

## Step 6: Confirm

```markdown
## Spec Created

**File:** `.buildrunner/builds/BUILD_[name].md`
**Phases:** [N]
**First phase:** [Name] - [deliverable count] deliverables

**Next:** Run `/begin` to start Phase 1.

That's it. One command to build the entire phase.
```

---

## Rules

1. **Think deeply first** - Full analysis before proposing structure
2. **Clear phase boundaries** - Each phase stands alone
3. **Specific deliverables** - Concrete tasks, not vague goals
4. **Dependencies explicit** - What blocks what
5. **Wait for approval** - Don't create files until "go"
6. **Out of scope matters** - Explicitly list what we're NOT building
7. **Works anywhere** - Uses git root detection, creates directories as needed

---

## DO NOT (Opus Constraints)

- **DO NOT create phases with more than 10 tasks/deliverables** - Split into multiple phases if scope exceeds 10
- **DO NOT create vague deliverables** - "Improve performance" is bad, "Add caching to API calls" is good
- **DO NOT add nice-to-haves to Phase 1** - Foundation only
- **DO NOT skip the Files list** - Every phase MUST list files it creates/modifies
- **DO NOT use "Depends on" without file analysis** - "Blocked by" requires ACTUAL file conflicts
- **DO NOT mark phases as blocked when they're just logical sequence** - Use "After" for preferred order, "Blocked by" only for file conflicts
- **DO NOT skip the Parallelization Matrix** - Required in every spec
- **DO NOT skip the Out of Scope section** - Always list what we're NOT building
- **DO NOT over-engineer the spec** - Simple, clear, actionable
