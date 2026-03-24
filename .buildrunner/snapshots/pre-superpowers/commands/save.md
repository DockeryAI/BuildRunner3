---
description: Save session - log decisions, architecture, reasoning, and goals
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
model: haiku
---

# Save Session

Capture every significant decision, architecture change, rationale, and goal from this conversation.

---

## Step 1: Review Conversation

Scan the full conversation for:
- **Decisions** - What was decided and why
- **Architecture changes** - Structural changes to the system
- **Reasoning** - The "why" behind every choice, trade-off, or rejection
- **Goals** - What we're trying to achieve, shifted priorities, new objectives

---

## Step 2: Log to Decision Journal

Append entries to `.buildrunner/decisions.log`:

```bash
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] [TYPE] description" >> .buildrunner/decisions.log
```

### Entry Types

| Type | Use When |
|------|----------|
| `[DECISION]` | A choice was made between alternatives |
| `[ARCHITECTURE]` | System structure, data flow, or component design changed |
| `[WHY]` | Rationale behind a non-obvious choice — the reasoning |
| `[TRADE-OFF]` | Something was sacrificed for something else |
| `[REJECTED]` | An approach was considered and rejected (and why) |
| `[GOAL]` | A new objective, shifted priority, or clarified target |
| `[PATTERN]` | A code pattern was adopted or established |
| `[CONSTRAINT]` | A limitation or boundary was discovered or imposed |

### Entry Format

Each entry MUST include:
1. **What** — The decision or change (1 line)
2. **Why** — The reasoning (1-2 lines)
3. **Context** — Files, components, or features affected

**Example entries:**

```
[2025-01-15T14:30:00Z] [ARCHITECTURE] Moved auth logic from frontend to edge functions
  WHY: Frontend auth exposed tokens in browser; edge functions keep secrets server-side
  CONTEXT: src/auth/, supabase/functions/auth

[2025-01-15T14:32:00Z] [REJECTED] Considered using localStorage for session state
  WHY: XSS vulnerability; switched to httpOnly cookies instead
  CONTEXT: auth flow, session management

[2025-01-15T14:35:00Z] [GOAL] Priority shift: performance optimization before new features
  WHY: Users reporting 3s+ load times; retention dropping
  CONTEXT: dashboard, data fetching layer
```

---

## Step 3: Log EVERY Decision

**Be exhaustive.** Log everything, not just the big calls:

- Why a specific library/tool was chosen
- Why a file was structured a certain way
- Why an approach was rejected
- Why a goal changed or was refined
- Why a trade-off was made
- Why a pattern was adopted over alternatives
- Why constraints exist

**The goal is that a future session can read `decisions.log` and understand not just WHAT was built, but WHY every choice was made.**

---

## Step 4: Report

```markdown
## Session Saved

**Entries logged:** [N]
- Decisions: [n]
- Architecture: [n]
- Reasoning/Why: [n]
- Goals: [n]
- Trade-offs: [n]
- Rejected: [n]
- Patterns: [n]
- Constraints: [n]

**Key decisions this session:**
- [1-liner summary of most important decisions]
```

---

## Rules

1. **Log everything** — If it was discussed, decided, or debated, it gets logged
2. **Always include WHY** — The reasoning is more valuable than the decision itself
3. **Be specific** — Include file names, function names, component names
4. **No commits** — This skill only logs. Use `/commit` separately if needed
5. **Future-proof** — Write entries so someone with zero context can understand the choice
6. **Capture rejections** — What was NOT chosen is as important as what was
