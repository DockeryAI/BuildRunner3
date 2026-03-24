---
description: Find the root cause - exhaustive analysis with subagents, 100% confirmed, report only (no action)
allowed-tools: Read, Bash, Grep, Glob, Task, WebSearch, WebFetch
model: opus
arguments:
  - name: project
    description: "Optional: project alias or path"
    required: false
---

# Root Cause Analysis

You are performing exhaustive root cause analysis on whatever issue has been discussed in the current conversation. Your job is to find the **100% confirmed** root cause - no guesses, no assumptions, no "likely" or "probably".

**Arguments:** $ARGUMENTS

---

## CRITICAL RULES

1. **NO ASSUMPTIONS** - Every claim must be verified by reading actual code
2. **NO GUESSES** - If you're not 100% certain, investigate further
3. **NO "LIKELY"** - Ban words: likely, probably, possibly, might, could be, seems like
4. **NO CODE OUTPUT** - Report in plain English only
5. **NO ACTION** - Do not fix anything, only report and plan
6. **NO MATRICES/GRIDS** - Simple bullet points and prose only

---

## Step 0: Determine Project Path

If a project was specified in $ARGUMENTS, resolve it:

**Known project aliases:**
- `sales` → `~/Projects/sales-assistant/web/app`
- `oracle` → `~/Projects/buildrunner-oracle`
- `synapse` → `~/Projects/Synapse`
- `marba` → `~/Projects/MARBA`
- `synapse-admin` → `~/Projects/synapse-admin-panel`
- `synapse-triggers` → `~/Projects/Synapse-Triggers-3.0`
- `synapse-uvp` → `~/Projects/synapse-uvp-v2`

If argument contains `/` or `~`, treat as direct path.
If no argument, use current working directory.

---

## Step 1: Identify the Problem Statement

Review the conversation history and extract:
- **What symptom was observed?** (error message, wrong behavior, visual bug)
- **What was expected?** (correct behavior)
- **When does it occur?** (always, sometimes, specific conditions)

Write this down before proceeding.

---

## Step 2: Spawn Investigation Subagents

Use the Task tool with `subagent_type: "Explore"` to thoroughly investigate. Spawn **multiple agents in parallel** to cover all angles:

### Agent 1: Code Flow Analysis
```
Trace the exact execution path for [problem area].
Read every file involved. Document the data flow step by step.
Report what actually happens vs what should happen.
```

### Agent 2: Assumption Verification
```
For every assumption made about [problem]:
- Find the actual code that implements it
- Verify the assumption is correct or incorrect
- Quote the exact lines that prove it
```

### Agent 3: Edge Case Analysis
```
Identify all conditions, branches, and edge cases in [problem area].
Check which conditions are actually being met.
Find any unhandled cases or incorrect conditions.
```

### Agent 4: Dependency Chain
```
Trace all dependencies and data sources for [problem area].
Verify each dependency provides correct data.
Find any missing, stale, or incorrect inputs.
```

---

## Step 3: Cross-Reference Results

After all agents complete:

1. **Collect findings** - Combine all verified facts
2. **Eliminate theories** - Any theory not 100% proven is discarded
3. **Identify the single root cause** - There must be ONE definitive cause
4. **Verify causation** - Confirm this cause directly produces the symptom

If no single root cause is 100% confirmed, spawn additional investigation agents.

---

## Step 4: Confirm 100% Certainty

Before reporting, verify you can answer "YES" to all:

- [ ] Have I read the exact code that causes this?
- [ ] Can I point to specific file:line numbers?
- [ ] Do I understand WHY this code produces the symptom?
- [ ] Have I verified there's no other possible cause?
- [ ] Is my explanation based on facts, not inference?

If any answer is "NO", return to Step 2 and investigate further.

---

## Step 5: Generate Report

Output this EXACT format (no deviations):

```markdown
## Root Cause Analysis Report

**Problem:** [One sentence describing the observed symptom]

**Root Cause:** [One sentence stating the definitive cause]

**Proof:**
- [File:line] - [What this code does wrong]
- [File:line] - [Supporting evidence]

**Why This Happens:**
[2-3 sentences explaining the causal chain from root cause to symptom]

**Fix Plan:**
1. [First action to take]
2. [Second action if needed]
3. [Third action if needed]

**Confidence:** 100% confirmed
```

---

## PROHIBITED

- Do not output any code blocks (except the report template)
- Do not create tables or matrices
- Do not say "likely", "probably", "seems", "appears to be"
- Do not suggest multiple possible causes - find THE cause
- Do not take any action to fix the issue
- Do not modify any files
- Do not run any build/test commands

---

## REQUIRED

- Use multiple parallel subagents for thorough investigation
- Read actual source code, don't assume
- Quote specific file paths and line numbers
- Verify every claim with evidence
- Continue investigating until 100% certain
