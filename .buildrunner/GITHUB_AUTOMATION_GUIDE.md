# GitHub Automation Guide
**BuildRunner 3.0 - Complete GitHub Workflow Automation**

## Overview

BR3's GitHub automation streamlines your entire Git workflow from branch creation to deployment. This guide covers all features and best practices.

## Quick Start

```bash
# Create feature branch with auto-naming
br github branch create user-authentication

# Make changes, then smart push
br github push

# Create release
br github release patch

# Create PR
br github pr create
```

## Branch Management

### Create Feature Branch

```bash
# Auto-calculate week number
br github branch create my-feature

# Specify week number
br github branch create my-feature --week 3

# Create without checkout
br github branch create my-feature --no-checkout
```

**Branch Naming:**
- Pattern: `build/week{N}-{feature-name}`
- Week number auto-calculated from project start
- Feature name auto-slugified

### List Feature Branches

```bash
br github branch list
```

Shows:
- All feature branches
- Current branch (marked with →)
- Week number
- Readiness status (✅ or ⚠️)

### Check Branch Readiness

```bash
br github branch ready
```

Checks:
- ✅ All tests passing
- ✅ No uncommitted changes
- ✅ Up to date with main
- ✅ No merge conflicts
- ✅ All features complete

### Switch to Branch

```bash
# Search by feature name
br github branch switch authentication

# Fuzzy matching works
br github branch switch auth
```

### Cleanup Merged Branches

```bash
# Dry run (show what would be deleted)
br github branch cleanup

# Actually delete
br github branch cleanup --execute
```

## Smart Push

### Push with Readiness Checks

```bash
# Standard smart push
br github push

# Only push if 100% ready
br github push --when-ready

# Skip conflict checks
br github push --skip-conflicts

# Force push (skip all checks)
br github push --force
```

**Readiness Score (0-100):**
- 90-100: ✅ Ready to push
- 70-89: ⚠️ Can push with warnings
- 50-69: 🚧 Not recommended
- 0-49: ❌ Do not push

**Checks Performed:**
- Uncommitted changes (-30)
- Tests failing (-40)
- Exposed secrets (-50)
- SQL injection risks (-10)
- Incomplete features (-5)
- Behind main (-10)
- Merge conflicts (-30)

### Sync with Main

```bash
# Rebase on main
br github sync

# Merge main instead
br github sync --merge
```

Automatically:
- Fetches latest main
- Checks for conflicts
- Rebases or merges
- Reports status

## Release Management

### Create Release

```bash
# Patch release (v3.1.0 → v3.1.1)
br github release patch

# Minor release (v3.1.0 → v3.2.0)
br github release minor

# Major release (v3.1.0 → v4.0.0)
br github release major

# Or specify type
br github release create patch
```

**Automatic:**
1. Reads current version from pyproject.toml
2. Bumps version (semantic versioning)
3. Updates all version files:
   - pyproject.toml
   - package.json (if exists)
4. Generates changelog from commits
5. Creates git tag
6. Creates GitHub release
7. Pushes tag

## Pull Requests

### Create PR

```bash
# Auto-generate title and description
br github pr create

# Custom title
br github pr create --title "Add user authentication"

# Draft PR
br github pr create --draft
```

**Auto-Generated:**
- Title from branch name or first commit
- Description from commits and file changes
- Reviewers (from governance config)
- Labels (from commit types)

## Conventional Commits

### Interactive Commit Builder

```bash
# Interactive prompts
br github commit

# Specify type and message
br github commit --type feat --message "Add login form"

# With scope
br github commit --type fix --message "Handle null user" --scope auth
```

**Commit Types:**
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code refactoring
- `docs`: Documentation
- `test`: Tests
- `chore`: Maintenance

**Output Format:**
```
feat(auth): Add login form

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Branch Protection

### Setup Protection

```bash
# Protect main branch
br github protect

# Protect custom branch
br github protect --branch develop
```

**Protection Rules:**
- Require PR reviews (1-2)
- Require status checks (CI/CD)
- Require linear history
- Block force push
- Block deletion

**Note:** Requires `GITHUB_TOKEN` environment variable.

## Snapshots

### Create Snapshot

```bash
# Named snapshot
br github snapshot create before-refactor

# Auto-named (timestamp)
br github snapshot create "$(date +%Y%m%d-%H%M%S)"
```

**Use Cases:**
- Before major refactoring
- Before risky changes
- Before experimental features
- Milestone markers

### List Snapshots

```bash
br github snapshot list
```

**Snapshots are:**
- Lightweight git tags
- Pattern: `snapshot/{name}`
- Easy to restore: `git checkout snapshot/before-refactor`

## Configuration

### Governance Rules

Edit `.buildrunner/governance/governance.yaml`:

```yaml
github:
  branch_naming:
    enforce: true
    patterns:
      feature: "build/week{week_number}-{feature_name}"
      hotfix: "hotfix/{id}-{description}"

  versioning:
    scheme: semver
    auto_tag: true
    auto_changelog: true

  pull_requests:
    auto_title: true
    auto_description: true
    require_tests: true
    require_reviews: 1
    reviewers:
      - your-username

  push_rules:
    check_feature_complete: true
    check_conflicts: true
    warn_if_behind: true
    require_tests_pass: true
```

### Environment Variables

```bash
# GitHub API access (for PRs, releases, protection)
export GITHUB_TOKEN=ghp_your_token_here

# Or use gh CLI authentication
gh auth login
```

## Advanced Features

### Week Number Calculation

BR3 auto-calculates week numbers from:

1. **PROJECT_SPEC.md:** `Start Date: YYYY-MM-DD`
2. **features.json:** Last completed feature's week
3. **Default:** Week 1

### Readiness Assessment

Push intelligence checks multiple dimensions:

```bash
br github push
```

**Output:**
```
Push Readiness Assessment
Score: 85/100

✅ Passed Checks:
  • All changes committed
  • All tests passing
  • Security scan clean
  • Branch is up to date with main
  • No merge conflicts

⚠️ Warnings:
  • 2 features in progress

Recommendation: ⚠️ Can push but with warnings - review before pushing
```

### Conflict Detection

Pre-emptive conflict detection before pushing:

```bash
br github sync
```

**Output:**
```
⚠️ 5 commits behind with conflicts in 2 files
```

Fix conflicts locally before pushing.

## Integration with BR3

### Works with BR3 Hooks

GitHub commands integrate with BR3's pre-commit/pre-push hooks:

```bash
br github push
# → Runs BR3 validation automatically
# → Security scan
# → Quality check
# → Architecture guard
# → Then pushes
```

### Works with BR3 Features

```bash
# Check feature completion before pushing
br gaps analyze

# Check quality before PR
br quality check

# Run tests before release
br autodebug run
```

## Examples

### Complete Feature Workflow

```bash
# 1. Create feature branch
br github branch create user-profile

# 2. Make changes
# ... code code code ...

# 3. Commit with conventional format
br github commit --type feat --message "Add user profile page"

# 4. Check readiness
br github branch ready

# 5. Smart push
br github push --when-ready

# 6. Create PR
br github pr create
```

### Complete Release Workflow

```bash
# 1. Ensure all features complete
br gaps analyze

# 2. Run full validation
br autodebug run

# 3. Create release
br github release minor

# 4. Push release
git push origin main
git push --tags
```

### Safe Experimentation

```bash
# 1. Create snapshot
br github snapshot create before-experiment

# 2. Try experimental changes
# ... experiment ...

# 3. If it works, keep it
br github commit --type feat --message "Experimental feature works!"

# 4. If it fails, restore
git checkout snapshot/before-experiment
```

## Troubleshooting

### "Module not found: toml"

```bash
source .venv/bin/activate
pip install toml semver
pip install -e .
```

### "GitHub API token needed"

```bash
# Get token from https://github.com/settings/tokens
export GITHUB_TOKEN=ghp_your_token_here

# Or use gh CLI
gh auth login
```

### "Not a git repository"

GitHub commands only work in git repositories.

### "PyGithub not installed"

```bash
pip install PyGithub>=2.0.0
```

## Best Practices

### Branch Naming

✅ **Good:**
- `build/week2-user-authentication`
- `build/week3-payment-integration`

❌ **Avoid:**
- `feature/my-feature` (doesn't follow governance)
- `test-branch` (no context)

### Commit Messages

✅ **Good:**
```
feat(auth): Add JWT token validation

Implements token expiry checking and refresh logic.
```

❌ **Avoid:**
```
fixed stuff
```

### Push Timing

✅ **Push when:**
- All tests passing
- No uncommitted changes
- Features complete or at stopping point
- No merge conflicts

❌ **Don't push when:**
- Tests failing
- Work in progress
- Merge conflicts present
- Security issues detected

### Release Timing

✅ **Release when:**
- All features complete
- Full test suite passing
- Documentation updated
- Changelog generated

❌ **Don't release when:**
- Features incomplete
- Known bugs
- Tests failing

## FAQ

**Q: Can I use this without GitHub?**
A: Yes! Branch management, smart push, and snapshots work with any git remote. Only PR creation and branch protection require GitHub.

**Q: Does this work with GitLab/Bitbucket?**
A: Basic features (branch, push, release, snapshot) work with any git remote. PR/protection features are GitHub-specific.

**Q: Can I customize branch naming?**
A: Yes! Edit `.buildrunner/governance/governance.yaml` → `github.branch_naming.patterns`

**Q: How do I disable certain checks?**
A: Edit governance.yaml → `github.push_rules` and set checks to `false`

**Q: Can I use my own week numbering?**
A: Yes! Always specify `--week` flag or set project start date in PROJECT_SPEC.md

**Q: Does this replace git commands?**
A: No! It enhances git with governance, automation, and intelligence. You can still use raw git commands.

---

**Version:** 1.0.0
**Last Updated:** 2024-11-24
**Status:** Production-ready

For issues or questions, see: https://github.com/anthropics/buildrunner3/issues
