---
description: Dead code analysis - find duplicates, parallel/competing code, dead code, and race conditions
allowed-tools: Read, Bash, Grep, Glob, Task, WebSearch, WebFetch
model: opus
arguments:
  - name: subject
    description: "Optional: feature name, file pattern, or project alias to analyze. If omitted, analyzes code from current discussion."
    required: false
---

# Dead Code & Redundancy Analysis

You are performing code analysis to identify dead code, duplicates, parallel/competing implementations, and race conditions.

**Subject:** $ARGUMENTS

---

## CRITICAL RULES

1. **NO CODE OUTPUT** - Report in plain English only
2. **NO MATRICES/GRIDS** - Simple bullet points and prose only
3. **NO ACTION** - Do not fix anything, only report and plan
4. **THOROUGH** - Cover the full scope of the analysis target
5. **CITE LOCATIONS** - Always reference file:line for findings

---

## Step 0: Determine Analysis Scope

**If $ARGUMENTS is empty:**
- Analyze whatever code/feature was discussed in the current conversation
- Look at recent files mentioned, errors discussed, or features being worked on

**If $ARGUMENTS contains a project alias, resolve it:**
- `sales` → `~/Projects/sales-assistant/web/app`
- `oracle` → `~/Projects/buildrunner-oracle`
- `synapse` → `~/Projects/Synapse`
- `marba` → `~/Projects/MARBA`
- `synapse-admin` → `~/Projects/synapse-admin-panel`
- `synapse-triggers` → `~/Projects/Synapse-Triggers-3.0`
- `synapse-uvp` → `~/Projects/synapse-uvp-v2`
- `br` or `buildrunner` → `~/Projects/BuildRunner3`

**If $ARGUMENTS contains `/` or `~`:** Treat as direct path.

**If $ARGUMENTS is a feature name:** Search codebase for all related files.

---

## Step 1: Spawn Analysis Subagents

Use Task tool with `subagent_type: "Explore"` - spawn ALL these agents **in parallel** for maximum coverage:

### Agent 1: Dead Code Hunter
```
Search for dead code in [scope]:
- Unused functions (defined but never called)
- Unused imports and variables
- Unreachable code paths (after returns, impossible conditions)
- Commented-out code blocks
- TODO/FIXME that reference removed features
- Exports that are never imported elsewhere

For each finding, note: file:line, what it is, why it's dead.
```

### Agent 2: Duplicate Detector
```
Find duplicate/redundant code in [scope]:
- Near-identical functions doing the same thing
- Copy-pasted logic with minor variations
- Multiple implementations of the same utility
- Repeated inline code that should be extracted
- Same constants defined in multiple places

For each finding, note: all locations, what's duplicated.
```

### Agent 3: Parallel/Competing Implementation Finder
```
Identify parallel or competing implementations in [scope]:
- Multiple systems doing the same job (old + new)
- Feature flags controlling deprecated code paths
- Migration code that's still active
- Multiple event handlers for the same event
- Redundant state management (multiple sources of truth)
- Old API endpoints still active alongside new ones

For each finding, note: all implementations, which is canonical.
```

### Agent 4: Race Condition Analyzer
```
Analyze for race conditions in [scope]:
- Async operations without proper sequencing
- State updates that can interleave incorrectly
- Missing await/locks on shared resources
- Event handlers that assume order
- Database operations without transactions where needed
- Optimistic updates without conflict resolution

For each finding, note: the race, potential symptoms, trigger conditions.
```

### Agent 5: Import/Dependency Graph
```
Map the dependency structure of [scope]:
- Circular dependencies
- Unused dependencies in package.json
- Dependencies imported but features unused
- Version conflicts or multiple versions
- Barrel files re-exporting unused items

Create a simple summary of problematic dependencies.
```

---

## Step 2: Consolidate Findings

After all agents complete, categorize findings:

**CRITICAL** - Actively causing bugs or blocking progress
**HIGH** - Creates confusion, technical debt, maintenance burden
**MEDIUM** - Cleanup opportunities, minor redundancy
**LOW** - Style issues, minor dead code

---

## Step 3: Generate Report

Output this EXACT format:

```markdown
## Dead Code Analysis Report

**Scope:** [What was analyzed]
**Files Examined:** [count]

---

### Critical Issues

[List any actively harmful findings - race conditions causing bugs, competing implementations causing conflicts]

---

### Dead Code

[List all dead code findings with file:line references]
- [file:line] - [what and why it's dead]

---

### Duplicates

[List all duplicate code with all locations]
- [description] found in: [file1:line], [file2:line]

---

### Parallel/Competing Implementations

[List systems that overlap or compete]
- [what's duplicated]: [location1] vs [location2] - [which should win]

---

### Race Conditions

[List potential race conditions]
- [file:line] - [the race] - [when it triggers]

---

### Fix Plan

**Priority 1 (Critical):**
1. [First fix]
2. [Second fix]

**Priority 2 (High):**
1. [Fix]

**Priority 3 (Medium/Low):**
1. [Cleanup item]

---

**Summary:** [X dead code items, Y duplicates, Z competing implementations, W race conditions]
```

---

## PROHIBITED

- Do not output any code
- Do not create tables or matrices
- Do not fix anything
- Do not modify any files
- Do not run build/test commands

---

## REQUIRED

- Use ALL 5 subagents in parallel
- Read actual source code for every finding
- Cite specific file:line for every issue
- Categorize by severity
- Provide actionable fix plan (words only, no code)
