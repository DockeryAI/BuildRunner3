---
description: Guard - Validates work against spec, governance, decisions, and architecture. Prevents drift.
allowed-tools: Read, Bash, Grep
model: opus
---

# Architecture Guard - Drift Prevention

Validate current work against all project constraints. Quick, focused check.

---

## Step 0: Locate Project Root

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
```

---

## Step 1: Load Context (READ ONLY WHAT EXISTS)

```bash
# Load available files - don't fail on missing
cat "$PROJECT_ROOT/.buildrunner/PROJECT_SPEC.md" 2>/dev/null | head -100
cat "$PROJECT_ROOT/.buildrunner/governance.yaml" 2>/dev/null
cat "$PROJECT_ROOT/.buildrunner/decisions.log" 2>/dev/null | tail -30
cat "$PROJECT_ROOT/.buildrunner/ARCHITECTURE.md" 2>/dev/null | head -50
ls -t "$PROJECT_ROOT/.buildrunner/builds/BUILD_"*.md 2>/dev/null | head -1 | xargs cat 2>/dev/null | head -50
```

---

## Step 2: Understand Current Work

What is Claude currently doing or about to do? Consider:
- The user's recent request
- Files recently modified
- Features being implemented

---

## Step 3: Validate Against Each Source

### 3.1 PROJECT_SPEC.md Validation
- [ ] Feature being built exists in spec
- [ ] Implementation matches spec description
- [ ] Priority aligns with current phase
- [ ] Not building features marked as out-of-scope

**Flag if:** Building something not in spec, or spec says something different

### 3.2 Governance Rules Validation
- [ ] No blocked libraries being imported
- [ ] No RLS being disabled
- [ ] No hardcoded secrets
- [ ] No direct API calls in frontend
- [ ] LLM model not changed without permission
- [ ] Security patterns followed

**Flag if:** Any governance rule violated

### 3.3 Decisions Log Validation
- [ ] Not contradicting a previous architectural decision
- [ ] Not reintroducing a pattern that was explicitly rejected
- [ ] Not undoing a fix without understanding why it was made
- [ ] Respecting trade-offs that were consciously made

**Flag if:** About to contradict or undo a logged decision

### 3.4 Architecture Validation
- [ ] Following established patterns
- [ ] Using correct layers (UI → Edge Functions → DB)
- [ ] Respecting module boundaries
- [ ] Not introducing circular dependencies

**Flag if:** Violating architectural patterns

### 3.5 Build Plan Validation
- [ ] Working on current phase items
- [ ] Not jumping ahead to future phases
- [ ] Phase dependencies satisfied

**Flag if:** Working outside current phase scope

---

## Step 4: Generate Guard Report

Present findings in this format:

```markdown
## Guard Report

**Status:** ✅ CLEAR / ⚠️ WARNINGS / 🛑 VIOLATIONS

### Spec Alignment
[✅/⚠️/🛑] [Finding or "Aligned"]

### Governance Compliance
[✅/⚠️/🛑] [Finding or "Compliant"]

### Decision Consistency
[✅/⚠️/🛑] [Finding or "Consistent"]

### Architecture Compliance
[✅/⚠️/🛑] [Finding or "Compliant"]

### Build Phase Alignment
[✅/⚠️/🛑] [Finding or "Aligned"]

---

### Violations Found (if any)

| # | Type | Issue | Source | Action Required |
|---|------|-------|--------|-----------------|
| 1 | [Spec/Gov/Decision/Arch] | [What's wrong] | [Which doc] | [How to fix] |

---

### Recommendations

[What to do before proceeding]
```

---

## Step 5: Act on Findings

### If ✅ CLEAR
> "Guard check passed. No drift detected. Safe to proceed."

### If ⚠️ WARNINGS
> "Guard check found [N] warnings. Review above before proceeding. These may be intentional - confirm if so."

### If 🛑 VIOLATIONS
> "Guard check found [N] violations. **Do not proceed** until resolved. See action items above."

For violations:
1. Explain what's wrong and why
2. Reference the specific source (spec line, decision entry, governance rule)
3. Suggest how to resolve
4. **Do not continue with violating work** until user acknowledges

---

## When to Run /guard

- Before starting a new feature
- When changing architecture or patterns
- After a long session (drift accumulates)
- When unsure if something aligns with past decisions
- Before major commits

---

## Key Violations to Always Catch

| Violation | Severity | Source |
|-----------|----------|--------|
| Building feature not in spec | 🛑 HIGH | PROJECT_SPEC.md |
| Using blocked UI library | 🛑 HIGH | governance.yaml |
| Disabling RLS | 🛑 CRITICAL | governance.yaml |
| Changing LLM model | 🛑 HIGH | governance.yaml |
| Direct API calls in frontend | 🛑 HIGH | governance.yaml |
| Contradicting logged decision | ⚠️ MEDIUM | decisions.log |
| Working outside current phase | ⚠️ MEDIUM | BUILD_*.md |
| Violating architecture pattern | ⚠️ MEDIUM | ARCHITECTURE.md |

---

## Rules

1. **Read all context first** - Don't validate without full picture
2. **Be specific** - Reference exact lines/entries when flagging
3. **Explain why** - Not just what's wrong, but why it matters
4. **Block on violations** - Don't let work continue if rules are broken
5. **Warn on drift** - Even if not a hard violation, flag concerning patterns

---

## DO NOT (Opus Constraints)

- **DO NOT spend more than 60 seconds on this check** - It's a quick validation
- **DO NOT read entire files** - Use head/tail to get key sections
- **DO NOT block on missing optional files** - Only validate what exists
- **DO NOT generate false positives** - Only flag real violations with evidence
- **DO NOT suggest improvements** - Only flag violations, not suggestions
