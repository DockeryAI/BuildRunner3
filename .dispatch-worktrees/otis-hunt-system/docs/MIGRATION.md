# BuildRunner 2.0 to 3.0 Migration Guide

This guide explains how to migrate your BuildRunner 2.0 projects to BuildRunner 3.0.

## Overview

BuildRunner 3.0 introduces several improvements over 2.0:
- Unified `.buildrunner/` directory structure
- YAML-based governance configuration
- Enhanced features.json schema with metrics
- Improved MCP integration
- Better git hooks support

## Migration Process

### Prerequisites

1. **Backup your project** before migrating
2. Ensure you have BuildRunner 3.0 installed
3. Your BR 2.0 project should be committed to git

### Quick Start

```bash
# Preview migration (dry-run)
br migrate from-v2 /path/to/your/project --dry-run

# Execute migration
br migrate from-v2 /path/to/your/project

# Rollback if needed
br migrate rollback /path/to/your/project
```

## What Gets Migrated

### 1. Governance Configuration

**From:** `.runner/governance.json` (BR 2.0)
```json
{
  "project": {
    "name": "My Project",
    "slug": "my-project"
  },
  "policies": {
    "inline_open_editor_policy": {
      "enforced": true,
      "targets": [".py", ".js"]
    }
  }
}
```

**To:** `.buildrunner/governance/governance.yaml` (BR 3.0)
```yaml
project:
  name: My Project
  slug: my-project

enforcement:
  policy: strict
  on_violation:
    pre_commit: block
    pre_push: block

policies:
  file_editing:
    enforced: true
    targets:
      - .py
      - .js
```

### 2. HRPO Data (if exists)

**From:** `.runner/hrpo.json` (BR 2.0)
```json
{
  "phases": [
    {
      "name": "Phase 1: Foundation",
      "status": "complete",
      "steps": [
        {
          "name": "Step 1: Setup",
          "status": "complete"
        }
      ]
    }
  ]
}
```

**To:** Features in `.buildrunner/features.json` (BR 3.0)
```json
{
  "features": [
    {
      "id": "phase-1",
      "name": "Phase 1: Foundation",
      "status": "complete",
      "metadata": {
        "total_steps": 1,
        "migrated_from": "hrpo"
      }
    },
    {
      "id": "phase-1-step-1",
      "name": "Step 1: Setup",
      "status": "complete",
      "parent": "phase-1",
      "metadata": {
        "migrated_from": "hrpo"
      }
    }
  ]
}
```

### 3. Features Schema

**From:** v2.0 schema
```json
{
  "project": "my-project",
  "version": "2.0.0",
  "status": "production_ready",
  "features": [
    {
      "id": "feature-1",
      "status": "working",
      "priority": "p1"
    }
  ]
}
```

**To:** v3.0 schema
```json
{
  "project": "my-project",
  "version": "3.0.0",
  "status": "production",
  "features": [
    {
      "id": "feature-1",
      "status": "in_progress",
      "priority": "high",
      "created": "2025-01-17T12:00:00Z",
      "metadata": {
        "migrated_from": "v2.0"
      }
    }
  ],
  "metrics": {
    "features_total": 1,
    "features_complete": 0,
    "features_in_progress": 1,
    "completion_percentage": 0.0
  }
}
```

## Status & Priority Mapping

### Status Mapping

| BR 2.0 Status | BR 3.0 Status |
|--------------|---------------|
| `complete` | `complete` |
| `working` | `in_progress` |
| `in-progress` | `in_progress` |
| `planned` | `planned` |
| `blocked` | `blocked` |
| `production_ready` | `complete` |

### Priority Mapping

| BR 2.0 Priority | BR 3.0 Priority |
|----------------|-----------------|
| `critical` | `critical` |
| `p0` | `critical` |
| `high` | `high` |
| `p1` | `high` |
| `medium` | `medium` |
| `p2` | `medium` |
| `low` | `low` |
| `p3` | `low` |

## Detailed Migration Steps

### Step 1: Validate Your Project

Before migrating, validate your BR 2.0 project:

```bash
# The migration tool will automatically validate
br migrate from-v2 /path/to/project --dry-run
```

Common warnings you might see:

- ⚠️ **No .runner/ directory found** - Not a BR 2.0 project
- ⚠️ **No governance.json found** - Governance won't be migrated
- ℹ️ **No hrpo.json found** - HRPO migration will be skipped
- ℹ️ **Existing features.json found** - Will be merged with migrated data

### Step 2: Review Dry-Run Output

Run migration in dry-run mode to preview changes:

```bash
br migrate from-v2 /path/to/project --dry-run
```

This shows:
- What files will be created
- What data will be migrated
- How many features will be in the result
- Git metadata (if available)

### Step 3: Execute Migration

When ready, execute the migration:

```bash
br migrate from-v2 /path/to/project
```

The tool will:
1. Create backup of existing `.buildrunner/` → `.buildrunner-backup/`
2. Migrate governance.json → governance.yaml
3. Extract features from hrpo.json (if exists)
4. Upgrade features.json from v2.0 to v3.0
5. Merge HRPO features with existing features
6. Calculate project metrics
7. Preserve git history and metadata

### Step 4: Verify Migration

After migration, verify the results:

```bash
# Check features
cat .buildrunner/features.json | jq '.version'
# Should show: "3.0.0"

# Check governance
cat .buildrunner/governance/governance.yaml

# Check metrics
cat .buildrunner/features.json | jq '.metrics'
```

### Step 5: Commit Changes

```bash
git add .buildrunner/
git commit -m "chore: Migrate from BuildRunner 2.0 to 3.0"
```

## Edge Cases

### Missing .runner/ Directory

If your project doesn't have a `.runner/` directory, the migration will create a new `.buildrunner/` directory with minimal structure.

**Solution:** This is normal for projects that weren't using BR 2.0.

### Corrupt governance.json

If `governance.json` contains invalid JSON:

**Error:**
```
json.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**Solution:**
1. Fix the JSON syntax manually, or
2. Delete `governance.json` and let migration skip it

### Incomplete HRPO Data

If `hrpo.json` is missing phase names or statuses:

**Behavior:** Migration will use default values:
- Name: `Phase N` or `Step N`
- Status: `planned`
- Priority: `medium`

### Version Conflicts

If `.buildrunner/features.json` already exists with v3.0:

**Behavior:** Migration will still run and merge any HRPO data, but won't downgrade the version.

### Mixed v1/v2 Projects

If you have both old BR 1.0 and BR 2.0 structures:

**Recommendation:** Migrate to 2.0 first, then to 3.0.

## Rollback Procedures

### Automatic Rollback

If migration fails, you can rollback:

```bash
br migrate rollback /path/to/project
```

This restores the backup from `.buildrunner-backup/`.

### Manual Rollback

If needed, manually restore:

```bash
# Remove new .buildrunner
rm -rf .buildrunner

# Restore backup
mv .buildrunner-backup .buildrunner

# Revert git changes
git reset --hard HEAD
```

### Backup Location

Backups are stored in `.buildrunner-backup/` at the project root.

**Note:** Only the most recent backup is kept.

## Troubleshooting

### Migration Fails with "Project root not found"

**Cause:** Invalid path provided

**Solution:** Ensure the path exists and is absolute:
```bash
br migrate from-v2 $(pwd)/my-project
```

### No files created after migration

**Cause:** Running in dry-run mode

**Solution:** Remove `--dry-run` flag:
```bash
br migrate from-v2 /path/to/project
```

### Features duplicated after migration

**Cause:** HRPO features have same IDs as existing features

**Solution:** The migration tool automatically prevents duplicates. If you see duplicates, they have different IDs. Check with:
```bash
cat .buildrunner/features.json | jq '.features[].id'
```

### Git metadata not preserved

**Cause:** Project is not a git repository

**Solution:** Initialize git before migrating:
```bash
cd /path/to/project
git init
git add .
git commit -m "Initial commit"
```

### Permission denied when creating backup

**Cause:** Insufficient file permissions

**Solution:** Ensure write permissions:
```bash
chmod -R u+w .buildrunner
```

## Best Practices

### Before Migration

1. ✅ Commit all changes to git
2. ✅ Run `git status` to ensure clean working tree
3. ✅ Create a branch for migration: `git checkout -b migrate-to-v3`
4. ✅ Run dry-run first to preview changes

### During Migration

1. ✅ Review all warnings carefully
2. ✅ Check file counts and metrics
3. ✅ Verify status and priority mappings
4. ✅ Test git metadata extraction

### After Migration

1. ✅ Verify all features are present
2. ✅ Check governance rules are correct
3. ✅ Run `br status` to validate project
4. ✅ Test git hooks (if installed)
5. ✅ Update any scripts that reference `.runner/`
6. ✅ Commit migration changes

## Command Reference

### migrate from-v2

Migrate a BR 2.0 project to BR 3.0.

```bash
br migrate from-v2 <path> [options]
```

**Arguments:**
- `path` - Path to BR 2.0 project root (required)

**Options:**
- `--dry-run` - Preview migration without writing files
- `--preserve-history` - Preserve git history (default: true)

**Examples:**

```bash
# Preview migration
br migrate from-v2 ~/projects/my-app --dry-run

# Execute migration
br migrate from-v2 ~/projects/my-app

# Migrate without preserving git history
br migrate from-v2 ~/projects/my-app --preserve-history=false
```

### migrate rollback

Rollback a migration using the backup.

```bash
br migrate rollback <path>
```

**Arguments:**
- `path` - Path to project root (required)

**Examples:**

```bash
# Rollback migration
br migrate rollback ~/projects/my-app
```

## Python API

You can also use the migration tools programmatically:

```python
from cli.migrate import migrate_from_v2, rollback_migration

# Migrate
summary = migrate_from_v2(
    '/path/to/project',
    dry_run=False,
    preserve_history=True
)

print(f"Migrated {summary['features']['features_count']} features")

# Rollback if needed
rollback_migration('/path/to/project')
```

## Data Integrity

The migration tool ensures:

- ✅ No data loss - All BR 2.0 data is preserved or converted
- ✅ Schema validation - All migrated data passes v3.0 validation
- ✅ Backup creation - Original files are backed up before migration
- ✅ Atomic operations - Migration either completes fully or fails cleanly
- ✅ Rollback support - Easy rollback if anything goes wrong

## Migration Checklist

Use this checklist to track your migration:

- [ ] Project committed to git
- [ ] Dry-run completed and reviewed
- [ ] Warnings understood and addressed
- [ ] Backup created successfully
- [ ] Migration executed
- [ ] features.json version is 3.0.0
- [ ] Governance YAML created (if had governance.json)
- [ ] HRPO features migrated (if had hrpo.json)
- [ ] Metrics calculated correctly
- [ ] Git metadata preserved
- [ ] Changes committed to git
- [ ] Old .runner/ directory archived or removed
- [ ] Scripts updated to use .buildrunner/
- [ ] Team notified of migration

## Getting Help

If you encounter issues:

1. Check this documentation
2. Review error messages and warnings
3. Try dry-run mode to diagnose
4. Check project structure with `tree .buildrunner/`
5. Verify JSON syntax with `jq` or `python -m json.tool`
6. Report issues at: https://github.com/anthropics/buildrunner/issues

## FAQ

**Q: Can I migrate multiple projects at once?**
A: Run migration on each project individually for better control.

**Q: Will my BR 2.0 project still work after migration?**
A: Yes, the `.runner/` directory is untouched. But you should use BR 3.0 commands going forward.

**Q: Can I migrate back to BR 2.0?**
A: No direct downgrade tool. Use git revert or the backup.

**Q: What happens to custom shell scripts in .runner/tasks/?**
A: They're preserved. Update them to use `.buildrunner/` paths.

**Q: Do I need to reinstall BuildRunner?**
A: No, BR 3.0 is backwards compatible with BR 2.0 structures.

**Q: Can I run migration multiple times?**
A: Yes, but subsequent runs will merge data. Use rollback first if retrying.

---

**Next Steps:** After successful migration, see [MCP_INTEGRATION.md](MCP_INTEGRATION.md) to set up AI assistant integration.
