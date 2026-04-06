# Incremental Updates - Design System Evolution

**How BuildRunner handles PROJECT_SPEC changes and feature synchronization over time.**

---

## Overview

Incremental updates manage the evolution of your project:
- **Spec changes** - PROJECT_SPEC modifications
- **Feature sync** - features.json ↔ PROJECT_SPEC bidirectional sync
- **Conflict resolution** - Handling divergence between spec and implementation
- **Migration scenarios** - Upgrading from one design profile to another

---

## Delta Tracking System

### How BuildRunner Tracks Changes

```yaml
# .buildrunner/spec_history.json
{
  "current_checksum": "abc123...",
  "last_sync": "2025-01-15T10:30:00Z",
  "changes": [
    {
      "timestamp": "2025-01-15T10:30:00Z",
      "section": "technical_architecture",
      "field": "backend_framework",
      "old_value": "Django",
      "new_value": "FastAPI",
      "synced_to_features": true
    }
  ]
}
```

### Detecting Changes

```bash
# Check for spec changes since last sync
br spec validate

# Output:
⚠️  PROJECT_SPEC has changed since last sync
   Changed sections: technical_architecture
   Last sync: 2 days ago

💡 Run `br spec sync` to update features.json
```

---

## Spec Change Detection

### Automatic Detection

BuildRunner detects changes via:
1. **File checksums** - MD5 hash of PROJECT_SPEC.md
2. **Timestamp tracking** - Last modified vs. last sync
3. **Git diff integration** - Compare with committed version

### Manual Validation

```bash
# Validate spec completeness
br spec validate

# Check sync status
br spec sync --dry-run
```

---

## Feature Sync Mechanisms

### Bidirectional Sync

**Spec → Features (Forward Sync):**
```bash
# Update features.json from PROJECT_SPEC changes
br spec sync

# What it does:
# 1. Parse PROJECT_SPEC.md
# 2. Extract new/modified features
# 3. Update features.json
# 4. Preserve existing feature status (planned/in_progress/completed)
```

**Features → Spec (Reverse Sync):**
```bash
# Update PROJECT_SPEC from features.json changes
br spec sync --reverse

# What it does:
# 1. Read features.json
# 2. Update PROJECT_SPEC feature list
# 3. Preserve spec narrative/architecture
# 4. Mark spec as modified
```

---

## Conflict Resolution

### Scenario 1: Feature Added to Both

**Situation:**
- Feature "User Authentication" added to PROJECT_SPEC
- Feature "User Login" added to features.json
- Both are essentially the same feature

**Detection:**
```bash
br spec sync

# Output:
⚠️  Potential duplicate features detected:
   1. "User Authentication" (in PROJECT_SPEC)
   2. "User Login" (in features.json)

   Similarity: 85%

Options:
  [M]erge as single feature
  [K]eep both as separate
  [R]ename one feature
```

**Resolution:**
```bash
# Interactive prompt
Select option: M

# Result:
✅ Merged as "User Authentication & Login"
   ID: auth-001
   Status: Preserved from features.json (in_progress)
```

---

### Scenario 2: Feature Removed from Spec

**Situation:**
- Feature exists in features.json with status "in_progress"
- Feature removed from PROJECT_SPEC
- Work already started on implementation

**Detection:**
```bash
br spec sync

# Output:
⚠️  Features in features.json not found in PROJECT_SPEC:
   - "Email Notifications" (in_progress, 60% complete)

Options:
  [K]eep in features.json (orphan feature)
  [R]emove from features.json
  [M]ark as deprecated
```

**Resolution Options:**

**Keep (Orphan):**
```yaml
# features.json
{
  "id": "email-001",
  "name": "Email Notifications",
  "status": "in_progress",
  "orphaned": true,  # Not in spec
  "note": "Implementation started before spec removal"
}
```

**Remove:**
```bash
# Removes feature entirely
✅ Removed "Email Notifications" from features.json
```

**Deprecate:**
```yaml
{
  "id": "email-001",
  "name": "Email Notifications",
  "status": "deprecated",
  "deprecated_date": "2025-01-15"
}
```

---

### Scenario 3: Spec Modified, Features In Progress

**Situation:**
- PROJECT_SPEC updated tech stack (Django → FastAPI)
- 5 features in_progress using Django
- Need to migrate without losing work

**Detection:**
```bash
br spec validate

# Output:
⚠️  Architecture change detected:
   Backend: Django → FastAPI

   Affected features: 5
   - API Endpoints (in_progress)
   - Authentication (in_progress)
   - Database Models (completed)
   ... 2 more

💡 This may require refactoring existing work
```

**Resolution:**
```bash
# Create migration plan
br gaps analyze

# Output:
📋 Migration Plan:

   Phase 1: Complete Django features (2 in_progress)
   Phase 2: Migrate completed features (3 completed)
   Phase 3: New features use FastAPI (5 planned)

   Estimated effort: 3-5 days
```

---

## Migration Scenarios

### Scenario A: Change Industry Profile

**From:** Healthcare → Fintech

```bash
# Update PROJECT_SPEC industry
br spec wizard
# Select: Fintech

# Sync changes
br spec sync

# Output:
⚠️  Industry profile changed: healthcare → fintech

   Design changes:
   - Primary color: #0066CC → #1E3A8A
   - Compliance: HIPAA → PCI DSS
   - Components: PatientCard → TransactionCard

   ⚠️  This will affect 8 components

Proceed? (y/n): y

✅ Updated design profile
   - Created migration guide: .buildrunner/migrations/healthcare-to-fintech.md
   - Updated Tailwind config
   - Flagged affected components
```

---

### Scenario B: Add New Features Mid-Project

**Process:**

1. **Update PROJECT_SPEC:**
```markdown
# PROJECT_SPEC.md

## Features

### Phase 1 (Completed)
- User authentication ✓
- Dashboard ✓

### Phase 2 (New!)
- Two-factor authentication
- API rate limiting
```

2. **Sync to features.json:**
```bash
br spec sync

# Output:
✅ Added 2 new features from PROJECT_SPEC:
   - two-factor-authentication (planned)
   - api-rate-limiting (planned)

💡 New features added as "planned" status
```

---

### Scenario C: Remove Deprecated Features

**Process:**

1. **Mark features as deprecated:**
```bash
br feature complete old-feature-001
br feature deprecate old-feature-001 --reason "Replaced by new implementation"
```

2. **Update PROJECT_SPEC:**
```markdown
# Remove deprecated feature from spec
# Or move to "Deprecated" section
```

3. **Sync:**
```bash
br spec sync --remove-deprecated

# Output:
✅ Removed 3 deprecated features from features.json
   Preserved in: .buildrunner/deprecated_features.json
```

---

## Spec Evolution Best Practices

### 1. Version Your Spec

```yaml
# PROJECT_SPEC.md header
---
version: 2.1.0
last_updated: 2025-01-15
changelog:
  - v2.1.0: Added two-factor authentication
  - v2.0.0: Migrated to FastAPI
  - v1.0.0: Initial spec
---
```

### 2. Use Spec Branches (Git)

```bash
# Create spec branch for major changes
git checkout -b spec/add-admin-panel

# Edit PROJECT_SPEC.md
# Test sync
br spec sync --dry-run

# Merge when ready
git checkout main
git merge spec/add-admin-panel
```

### 3. Lock Spec During Critical Development

```bash
# Lock spec to prevent changes
br spec lock --message "Critical release in progress"

# Attempt to sync
br spec sync
# Error: PROJECT_SPEC is locked. Unlock with `br spec unlock`

# Unlock when safe
br spec unlock
```

### 4. Maintain Changelog

```markdown
# PROJECT_SPEC.md

## Changelog

### 2025-01-15 - v2.1.0
- Added: Two-factor authentication
- Modified: User authentication flow
- Deprecated: Email-only login

### 2025-01-01 - v2.0.0
- Changed: Backend framework Django → FastAPI
- Added: API rate limiting
- Removed: Legacy REST endpoints
```

---

## Sync Workflows

### Daily Sync (Recommended)

```bash
# Morning routine
br spec validate              # Check for changes
br spec sync --dry-run        # Preview sync
br spec sync                  # Execute sync
br status                     # Verify status
```

### Pre-Commit Sync

```bash
# .buildrunner/hooks/pre-commit
#!/bin/bash
br spec validate || exit 1
br spec sync --dry-run || exit 1
```

### CI/CD Sync Validation

```yaml
# .github/workflows/validate.yml
- name: Validate Spec Sync
  run: |
    br spec validate
    br spec sync --dry-run
    # Fail if out of sync
    if [ $? -ne 0 ]; then
      echo "PROJECT_SPEC and features.json are out of sync!"
      exit 1
    fi
```

---

## Advanced Sync Options

### Selective Sync

```bash
# Sync only specific sections
br spec sync --section features
br spec sync --section architecture

# Sync only new features (ignore modifications)
br spec sync --new-only

# Sync only removals
br spec sync --remove-only
```

### Conflict Resolution Strategies

```bash
# Always prefer PROJECT_SPEC
br spec sync --prefer-spec

# Always prefer features.json
br spec sync --prefer-features

# Interactive (prompt for each conflict)
br spec sync --interactive
```

### Dry Run with Report

```bash
# Generate detailed sync report
br spec sync --dry-run --report sync-report.md

# Report includes:
# - Features to add
# - Features to modify
# - Features to remove
# - Potential conflicts
# - Estimated sync time
```

---

## Monitoring Sync Health

### Sync Status Dashboard

```bash
br spec status

# Output:
📊 Spec Sync Status
──────────────────────────────────
  Last Sync: 2 days ago
  Spec Modified: Yes (1 day ago)
  Out of Sync: Yes

  Pending Changes:
  - 2 features added to spec
  - 1 feature modified in spec
  - 0 features removed

  💡 Run `br spec sync` to synchronize
```

### Sync History

```bash
br spec history

# Output:
📅 Sync History
──────────────────────────────────
  2025-01-15 10:30 - Synced (2 features added)
  2025-01-14 09:15 - Synced (1 feature modified)
  2025-01-13 14:45 - Synced (architecture updated)
  2025-01-12 11:20 - Synced (initial sync)
```

---

## Related Documentation

- **[PRD Wizard](PRD_WIZARD.md)** - Creating PROJECT_SPEC
- **[Gap Analysis](GAP_ANALYSIS.md)** - Finding missing features
- **[Design System](DESIGN_SYSTEM.md)** - Design profile evolution

---

## FAQ

**Q: What happens if I manually edit both PROJECT_SPEC and features.json?**
A: BuildRunner will detect conflicts and prompt you to resolve them interactively.

**Q: Can I revert a sync?**
A: Yes! BuildRunner creates backups before syncing: `.buildrunner/backups/features.json.bak`

**Q: How do I handle large-scale refactoring?**
A: Lock the spec (`br spec lock`), complete refactoring, update spec, unlock, then sync.

**Q: What if features.json has features not in PROJECT_SPEC?**
A: You can keep them as "orphaned" features or remove them during sync.

---

**Incremental Updates** - Evolve your project spec without breaking stride 🔄
