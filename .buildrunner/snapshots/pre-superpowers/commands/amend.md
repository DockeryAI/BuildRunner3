---
description: Add changes to BUILD spec mid-project (cross-phase amendments)
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, AskUserQuestion
model: opus
---

# Amend Build Spec

Add changes discovered mid-project to the BUILD spec. Lightweight alternative to `/spec`.

**Use when:** You've discovered changes needed across multiple phases after work has started.

**Don't use when:**
- Small single-phase change → just tell Claude to add it
- Complete project redesign → use `/spec` instead

---

## Step 1: Gather Changes

Collect all changes needed from:
- This conversation
- User's description
- Issues discovered during implementation

**Output:**
```markdown
## Proposed Changes

1. [Change A] - [brief description]
2. [Change B] - [brief description]
3. [Change C] - [brief description]
...
```

If unclear, use AskUserQuestion to clarify scope.

---

## Step 2: Load Current BUILD Spec

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
ls -t "$PROJECT_ROOT/.buildrunner/builds/BUILD_"*.md 2>/dev/null | head -1
```

Read the spec. Understand:
- Current phase and progress
- Existing tasks in each phase
- Dependencies between phases
- **Which phases are locked** (status: in_progress or complete)

---

## Step 2.5: Check for Locked Phases

**CRITICAL:** Before proposing to add tasks to any phase, check if it's locked.

A phase is **locked** if:
- Status is `in_progress` (actively being worked on)
- Status is `COMPLETE` or contains `Complete`
- Phase has session notes (indicates work has been done)

**If the target phase is locked:**
- DO NOT add tasks to it
- Create a NEW phase instead (Phase N+1)
- The new phase should be blocked by the locked phase

Example:
```markdown
## Lock Check

Phase 10 (Weather): in_progress ← LOCKED
Phase 11: does not exist

→ Cannot add to Phase 10. Will create Phase 11.
```

---

## Step 3: Analyze Impact

For each proposed change:

| Change | Affects Phase | Dependencies | Priority |
|--------|---------------|--------------|----------|
| [A] | Phase 2 | None | High |
| [B] | Phase 1 (current) | None | High |
| [C] | Phase 3 | Needs A first | Medium |

**Questions to answer:**
- Does this change existing work? (needs review of completed tasks)
- Does this add new tasks? (add to appropriate phase)
- Does this change phase order? (rare, flag if so)
- Are there new dependencies? (update task order)

---

## Step 4: Present Amendment Plan

**If target phase is locked**, present plan with NEW phase:

```markdown
## Amendment Plan

**Changes to add:** [N]
**Target phase locked:** Phase [X] is in_progress → Creating Phase [X+1]

### NEW Phase [X+1]: [Name] *(added: [DATE])*
**Status:** pending
**Blocked by:** Phase [X]

- [ ] [New task A]
- [ ] [New task B]
- [ ] [New task C]

---

**Approve?** (yes/no)
```

**If target phase is NOT locked**, add to existing phase:

```markdown
## Amendment Plan

**Changes to add:** [N]

### Phase [N] - Add:
- [ ] [New task B] ← **Will be in next /begin**

### Completed Work to Review:
- [Task X] - may need adjustment due to [Change Y]

---

**Approve?** (yes/no)
- **yes** → Update BUILD spec, log decision, continue
- **no** → Adjust the plan
```

---

## Step 5: Update BUILD Spec (After Approval)

### 5.1 Add New Tasks to Phases

Edit the BUILD spec to add new tasks. Mark them as amendments:

```markdown
- [ ] [New task] *(added: [DATE])*
```

### 5.2 Update Dependencies

If task order changed, update the phase dependencies.

### 5.3 Log Decision

```bash
br decision log "Amended BUILD spec: added [N] tasks across [M] phases. Reason: [brief reason]" --type AMENDMENT 2>/dev/null || \
echo "[$(date)] [AMENDMENT] Added [N] tasks: [list]. Reason: [reason]" >> "$PROJECT_ROOT/.buildrunner/decisions.log"
```

### 5.4 Commit Amendment

```bash
git add -A && git commit -m "$(cat <<'EOF'
chore: amend BUILD spec with [N] new tasks

Reason: [brief reason for changes]

Added to Phase [N]: [tasks]
Added to Phase [M]: [tasks]

🤖 Generated with Claude Code
EOF
)"
```

---

## Step 6: Confirm

```markdown
## BUILD Spec Amended

**Tasks added:** [N]
**Phases affected:** [list]
**Logged:** ✅
**Committed:** ✅

**Current phase:** [N] - now has [X] remaining tasks

---

**Next:** Run `/begin` to continue with updated tasks.
```

---

## When NOT to Use /amend

| Situation | Do This Instead |
|-----------|-----------------|
| Single task to add | Just say "add [task] to phase [N]" |
| Bug fix needed | Just fix it, no spec change |
| Complete redesign | Run `/spec` again |
| Scope creep | Push back, use `/later` to defer |

---

## Rules

1. **Don't over-engineer** - Small changes don't need /amend
2. **BUILD spec is memory** - Update it, Claude will follow
3. **Log the why** - Future sessions need context
4. **Commit amendments** - Git is memory
5. **One amendment at a time** - Don't batch multiple amendment sessions
6. **NEVER add to locked phases** - If phase is in_progress or complete, create a new phase instead
7. **Max 10 tasks per phase** - If adding tasks would push a phase over 10, split into a new phase
