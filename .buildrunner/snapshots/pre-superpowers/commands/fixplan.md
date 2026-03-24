---
description: Generate a concise fix plan covering ALL issues from the entire session - no code, no action, just the plan
allowed-tools: Read, Grep, Glob
model: opus
arguments:
  - name: project
    description: "Optional: project alias or path"
    required: false
---

# Fix Plan Generator

You are generating a concise, actionable fix plan that covers **ALL issues discussed throughout the ENTIRE session**, not just the most recent topic.

**Arguments:** $ARGUMENTS

---

## CRITICAL RULES

1. **NO CODE** - Do not output any code blocks or snippets
2. **NO GRIDS/MATRICES** - Simple bullet points and prose only
3. **NO ACTION** - Do not fix anything, only output the plan
4. **CONCISE** - Be brief and direct, no fluff
5. **ACTIONABLE** - Each step must be a clear action someone can take
6. **COMPREHENSIVE** - Capture ALL issues from the session, not just recent ones

---

## Step 1: Full Session Scan

Scan the ENTIRE conversation from start to finish. Review:
- The beginning of the session (first 20%)
- The middle of the session (often forgotten - pay extra attention here)
- The end of the session (most recent)

Extract EVERY issue, problem, bug, or improvement discussed - even if it was mentioned briefly or early in the conversation.

---

## Step 2: Issue Extraction

List ALL issues found. For each issue:
- Give it a short name/label
- Note when it was discussed (early/middle/late in session)
- Identify if it's related to other issues

Group related issues together. Remove true duplicates but keep distinct problems even if similar.

---

## Step 3: Generate Fix Plan

Output this format:

```markdown
## Fix Plan

**Issues Identified:** [count] issues from this session

1. **[Issue Name]** - [One sentence description]
2. **[Issue Name]** - [One sentence description]
3. [Continue for all issues...]

---

**Affected:** [List all files or areas across all issues]

**Steps:**
1. [First action - specify which issue(s) it addresses]
2. [Second action]
3. [Continue as needed - address ALL identified issues]

**Verify:** [How to confirm all fixes worked]
```

---

## FORMAT RULES

- List ALL issues first, then provide consolidated steps
- Steps can address multiple related issues together
- Maximum 10 steps unless truly complex (consolidate where logical)
- Each step is one sentence
- Steps describe WHAT to do, not HOW (no code)
- Use plain English, not technical jargon where possible
- Include file paths where relevant
- Mark which issue(s) each step addresses if not obvious

---

## PROHIBITED

- Code blocks of any kind
- Tables, grids, or matrices
- Taking any action to implement the fix
- Modifying any files
- Running any commands
- Lengthy explanations - be concise
- Multiple alternative approaches - pick the best one
- **Forgetting issues from early in the session**
- **Only covering the most recent discussion**

---

## EXAMPLES

Good issue list:
1. **Auth Token Expiry** - Tokens not refreshing after 24 hours
2. **Missing Error Handler** - API calls fail silently on network errors
3. **CSS Overlap** - Modal z-index conflicts with header

Bad issue list:
1. The thing we talked about last (missing earlier issues)

Good step: "Add token refresh logic in auth.service.ts (addresses #1: Auth Token Expiry)"

Bad step: "Fix the auth bug" (vague, doesn't reference specific issue)

Good step: "Update the position calculation in pool-visual-generator.service.ts to account for the container offset"

Bad step: "Change `x = item.x` to `x = item.x - containerOffset.x` in the render function"
