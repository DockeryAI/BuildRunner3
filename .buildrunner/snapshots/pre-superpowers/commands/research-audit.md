---
description: Audit research library - find schema drift, orphan subjects, unused entries
allowed-tools: Read, Edit, Bash, Grep, Glob
model: opus
---

# Research Library Audit: /research-audit

**PURPOSE: Scan all research docs, identify schema drift, and update subjects systematically.**

---

## When to Run

- Periodically (weekly/monthly) to catch drift
- After bulk imports or migrations
- When `/learn` queries aren't finding expected docs
- Before major research initiatives

---

## Step 1: Extract All Subjects from All Docs

```bash
RESEARCH_LIB=~/Projects/research-library

# Extract all subjects arrays from all docs
grep -h "^subjects:" $RESEARCH_LIB/docs/**/*.md | \
  sed 's/subjects: \[//' | \
  sed 's/\]//' | \
  tr ',' '\n' | \
  tr -d ' ' | \
  sort | uniq
```

**Store this as: DOCS_SUBJECTS (all subjects currently in documents)**

---

## Step 2: Extract All Subjects from Schema

```bash
# Read schema.md Valid Subjects section
# Extract all subjects listed in the tables
grep "^\| \`" ~/Projects/research-library/schema.md | \
  grep -o '`[^`]*`' | \
  tr -d '`' | \
  sort | uniq
```

**Store this as: SCHEMA_SUBJECTS (all subjects defined in schema)**

---

## Step 3: Identify Drift

### 3.1 Orphan Subjects (in docs, not in schema)

```bash
# Subjects used in documents but not defined in schema
comm -23 <(echo "$DOCS_SUBJECTS" | sort) <(echo "$SCHEMA_SUBJECTS" | sort)
```

**These need to be added to schema.md**

### 3.2 Unused Subjects (in schema, not in docs)

```bash
# Subjects defined in schema but never used
comm -13 <(echo "$DOCS_SUBJECTS" | sort) <(echo "$SCHEMA_SUBJECTS" | sort)
```

**Consider removing these or note as "available for future use"**

### 3.3 Subject Frequency

```bash
# Count how many docs use each subject
for subject in $DOCS_SUBJECTS; do
  count=$(grep -l "subjects:.*$subject" $RESEARCH_LIB/docs/**/*.md | wc -l)
  echo "$count $subject"
done | sort -rn
```

**High-frequency subjects are most valuable for cross-document discovery**

---

## Step 4: Auto-Categorize Orphans

For each orphan subject, determine category by:

### 4.1 Naming Pattern Heuristics

| Pattern | Likely Category |
|---------|-----------------|
| ends with `-api`, `-sdk` | Tools & APIs |
| ends with `-ui`, `-js`, `-react` | UI/Frontend |
| contains `bert`, `gpt`, `llm`, `embed` | Algorithms & ML or LLM & AI |
| ends with `-score`, `-metric` | Algorithms & ML |
| contains `signal`, `trigger`, `buyer` | Business Concepts |

### 4.2 Context from Source Doc

```bash
# Find which doc contains the orphan subject
grep -l "subjects:.*{orphan}" ~/Projects/research-library/docs/**/*.md

# Read that doc's domain to infer category
grep "^domain:" {found-doc}
```

| Doc Domain | Subject Category Hint |
|------------|----------------------|
| social-voc-mining | Algorithms & ML or Tools & APIs |
| buyer-psychology | Business Concepts |
| ui-design | UI/Frontend |
| debugging | UI/Frontend or Techniques |
| hallucination-prevention | LLM & AI |

### 4.3 Flag Ambiguous

If categorization unclear, mark for user decision:
```
AMBIGUOUS: {subject} - found in {doc}, could be {cat1} or {cat2}
```

---

## Step 5: Generate Audit Report

```markdown
## Research Library Audit Report

**Date:** {today}
**Documents scanned:** {count}
**Total unique subjects in docs:** {count}
**Total subjects in schema:** {count}

---

### Orphan Subjects (ADD to schema.md)

| Subject | Found In | Suggested Category | Description |
|---------|----------|-------------------|-------------|
| `{subject}` | {doc-name} | {category} | {auto-generated or TBD} |

### Unused Subjects (CONSIDER removing from schema)

| Subject | Category | Notes |
|---------|----------|-------|
| `{subject}` | {category} | Never used in any doc |

### Ambiguous (NEEDS user decision)

| Subject | Found In | Options |
|---------|----------|---------|
| `{subject}` | {doc} | {cat1} or {cat2}? |

### New Category Proposals

If 3+ orphan subjects share a theme not covered by existing categories:

| Proposed Category | Subjects | Rationale |
|-------------------|----------|-----------|
| {new-category} | {s1}, {s2}, {s3} | {why this grouping} |

### Subject Frequency (Top 10)

| Subject | Doc Count | Cross-reference Value |
|---------|-----------|----------------------|
| `apify` | 6 | High |
| `cosine-similarity` | 3 | Medium |

---

### Actions Required

1. [ ] Add {n} orphan subjects to schema.md
2. [ ] Review {n} unused subjects for removal
3. [ ] Decide on {n} ambiguous categorizations
4. [ ] Consider {n} new category proposals
```

---

## Step 6: Apply Changes (with confirmation)

### 6.1 Present summary to user

```
## Audit Complete

Found:
- {n} orphan subjects to add
- {n} unused subjects to review
- {n} ambiguous subjects needing decision

Apply recommended changes? [Y/n/selective]
```

### 6.2 If confirmed, update schema.md

For each orphan subject:
1. Find correct category table in schema.md
2. Add new row: `| \`{subject}\` | {description} |`
3. Keep tables alphabetically sorted

### 6.3 Handle new categories

If new category approved:
1. Add new `### {Category Name}` section
2. Create table with header
3. Add subjects

### 6.4 Log the audit

Add to research library or output:
```
Audit completed: {date}
- Added {n} subjects to schema
- Created {n} new categories
- Flagged {n} for removal review
```

---

## Step 7: Verification

After applying changes, verify:

```bash
# Re-run orphan check - should be empty
comm -23 <(grep -h "^subjects:" ~/Projects/research-library/docs/**/*.md | ...) \
         <(grep "^\| \`" ~/Projects/research-library/schema.md | ...)
```

---

## Quick Mode: `/research-audit quick`

If argument is "quick", skip detailed report and just show:
- Count of orphans
- Count of unused
- Top 5 most-used subjects

---

## Rules

1. **Never auto-delete** - Only flag unused subjects, don't remove
2. **Always confirm** - Ask before modifying schema.md
3. **Preserve existing** - Add to schema, don't reorganize existing entries
4. **Document changes** - Log what was added/modified

---

## What This Command Does

- Scans entire research library for subject usage
- Compares against schema.md definitions
- Identifies gaps and drift
- Proposes categorizations for new subjects
- Updates schema.md with confirmation

## What This Command Does NOT Do

- Delete subjects from schema without explicit approval
- Modify document frontmatter (only schema.md)
- Conduct new research
- Change subject values in existing docs
