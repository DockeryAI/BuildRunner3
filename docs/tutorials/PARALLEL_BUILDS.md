# Parallel Builds Tutorial

Learn to work on multiple features simultaneously using git worktrees and Build Runner's parallel build orchestration.

## Table of Contents

- [Introduction](#introduction)
- [Understanding Git Worktrees](#understanding-git-worktrees)
- [Parallel Build Concepts](#parallel-build-concepts)
- [Setting Up Worktrees](#setting-up-worktrees)
- [Parallel Build Orchestration](#parallel-build-orchestration)
- [Dependency Management](#dependency-management)
- [Merge Strategies](#merge-strategies)
- [Real Example: BuildRunner 3.0](#real-example-buildrunner-30)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Introduction

Parallel development allows you to:
- Work on multiple features simultaneously
- Switch between features without stashing
- Test features independently
- Merge when ready without blocking others

Traditional approach (slow):
```
Feature A → Complete → Merge → Feature B → Complete → Merge
Timeline: 10 days
```

Parallel approach (fast):
```
Feature A ──┐
            ├→ Both complete → Merge together
Feature B ──┘
Timeline: 5 days
```

## Understanding Git Worktrees

### What is a Git Worktree?

A worktree is a separate working directory for the same Git repository:

```
project/              # Main worktree (main branch)
project-feature-a/    # Worktree 1 (build/feature-a branch)
project-feature-b/    # Worktree 2 (build/feature-b branch)
```

All worktrees share the same `.git` repository but have independent:
- Working directories
- Checked out branches
- Uncommitted changes

### Worktrees vs Traditional Branching

**Traditional:**
```bash
git checkout main
# Work on main...

git checkout -b feature-a
# Work on feature-a...

git checkout main     # Must stash or commit
# Can't work on both simultaneously
```

**With Worktrees:**
```bash
# In project/
vim file.py          # Edit main branch

# In project-feature-a/
vim new_feature.py   # Edit feature-a branch

# Switch between terminals, no git checkout needed!
```

### Benefits

✅ **No branch switching** - Just switch directories
✅ **Independent builds** - Separate virtual environments
✅ **Parallel testing** - Run tests in each worktree
✅ **No stashing** - Each worktree has its own state
✅ **Easy comparison** - Open both in editor side-by-side

## Parallel Build Concepts

### Build Isolation

Each worktree should be isolated:

```
project/
├── .venv/              # Main venv
├── .buildrunner/
└── src/

project-feature-a/
├── .venv/              # Feature A venv
├── .buildrunner/
└── src/
```

### Build Orchestration

BuildRunner can orchestrate builds across worktrees:

```yaml
# .buildrunner/parallel.yaml
builds:
  - name: feature-auth
    worktree: ../project-auth
    branch: build/auth-system

  - name: feature-api
    worktree: ../project-api
    branch: build/api-endpoints

dependencies:
  feature-api:
    - feature-auth    # API depends on auth completing
```

### Dependency Graph

BuildRunner tracks dependencies:

```
feature-auth (independent)
    ↓
feature-api (depends on auth)
    ↓
feature-dashboard (depends on api)
```

Builds run in order, but independent builds run in parallel.

## Setting Up Worktrees

### Step 1: Verify Clean State

```bash
# Ensure main is clean
cd ~/projects/my-app
git status
# Should show: "nothing to commit, working tree clean"
```

### Step 2: Create Worktree

```bash
# Create worktree for feature A
git worktree add ../my-app-feature-a -b build/feature-a

# Output:
# Preparing worktree (new branch 'build/feature-a')
# HEAD is now at abc1234 Latest commit
```

### Step 3: Verify Worktree

```bash
# List all worktrees
git worktree list

# Output:
# /Users/you/projects/my-app              abc1234 [main]
# /Users/you/projects/my-app-feature-a    abc1234 [build/feature-a]
```

### Step 4: Set Up Feature Environment

```bash
# Navigate to feature worktree
cd ../my-app-feature-a

# Create isolated venv
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify isolation
which python
# Should show: /Users/you/projects/my-app-feature-a/.venv/bin/python
```

### Step 5: Initialize BuildRunner

```bash
# Feature worktree gets its own .buildrunner config
br init

# Or copy from main
cp -r ../my-app/.buildrunner .
```

## Parallel Build Orchestration

### Manual Orchestration

Work in each worktree independently:

```bash
# Terminal 1 - Feature A
cd ~/projects/my-app-feature-a
source .venv/bin/activate
pytest tests/test_auth.py

# Terminal 2 - Feature B
cd ~/projects/my-app-feature-b
source .venv/bin/activate
pytest tests/test_api.py

# Both run simultaneously!
```

### BuildRunner Orchestration

Let BuildRunner manage builds:

```bash
# From main worktree
cd ~/projects/my-app

# Create parallel build config
br parallel init

# Output creates .buildrunner/parallel.yaml
```

Configure builds:

```yaml
# .buildrunner/parallel.yaml
version: "1.0"

builds:
  - id: build-auth
    name: "Authentication System"
    worktree: ../my-app-auth
    branch: build/auth-system
    commands:
      test: pytest tests/
      lint: br quality check --threshold 80
      build: python setup.py build

  - id: build-api
    name: "API Endpoints"
    worktree: ../my-app-api
    branch: build/api-endpoints
    commands:
      test: pytest tests/
      lint: br quality check --threshold 80
      build: python setup.py build
    depends_on:
      - build-auth    # API needs auth first

  - id: build-dashboard
    name: "Dashboard UI"
    worktree: ../my-app-dashboard
    branch: build/dashboard-ui
    commands:
      test: pytest tests/
      lint: br quality check --threshold 80
      build: npm run build
    depends_on:
      - build-api     # Dashboard needs API first

strategy:
  parallel: true      # Run independent builds in parallel
  fail_fast: false    # Continue even if one fails
  timeout: 3600       # 1 hour max for all builds
```

Run orchestrated builds:

```bash
# Run all builds in correct order
br parallel run

# Output:
# Building: build-auth (independent)
# ├─ Running tests... ✓
# ├─ Running lint... ✓
# └─ Running build... ✓
#
# Building: build-api (depends on build-auth)
# ├─ Running tests... ✓
# ├─ Running lint... ✓
# └─ Running build... ✓
#
# Building: build-dashboard (depends on build-api)
# ├─ Running tests... ✓
# ├─ Running lint... ✓
# └─ Running build... ✓
#
# ✅ All builds successful!
```

### Selective Builds

```bash
# Run only specific builds
br parallel run --builds build-auth,build-api

# Run only builds affected by changes
br parallel run --affected

# Run with specific command
br parallel run --command test
```

## Dependency Management

### Declaring Dependencies

In `.buildrunner/parallel.yaml`:

```yaml
builds:
  - id: core
    worktree: ../app-core
    # No dependencies - can run first

  - id: api
    worktree: ../app-api
    depends_on:
      - core          # Needs core models

  - id: worker
    worktree: ../app-worker
    depends_on:
      - core          # Needs core models
    # api and worker can run in parallel

  - id: frontend
    worktree: ../app-frontend
    depends_on:
      - api          # Needs API definitions
```

Dependency graph:
```
      core
       / \
     api  worker  (parallel)
     /
frontend
```

### Cross-Worktree Dependencies

Share code between worktrees:

**Option 1: Shared Package**

```bash
# In core worktree
cd ../app-core
python setup.py develop  # Editable install

# In api worktree
cd ../app-api
pip install -e ../app-core  # Link to core
```

**Option 2: Git Submodules**

```bash
# In api worktree
git submodule add -b build/core ../app-core core/
```

**Option 3: BuildRunner Linking**

```yaml
# .buildrunner/parallel.yaml
builds:
  - id: api
    worktree: ../app-api
    links:
      - source: ../app-core/src
        target: lib/core
        type: symlink
```

### Version Pinning

Pin dependency versions across worktrees:

```yaml
# .buildrunner/parallel.yaml
shared_dependencies:
  python: "3.11"
  packages:
    - fastapi==0.104.0
    - pydantic==2.0.0
    - pytest==7.4.0

# Each worktree gets same versions
```

## Merge Strategies

### Strategy 1: Independent Merge

Features are independent, merge separately:

```bash
# Feature A complete
cd ~/projects/my-app-feature-a
git add .
git commit -m "feat: add authentication system"
git push origin build/feature-a

# Create PR, get review, merge to main

# Feature B complete (independently)
cd ~/projects/my-app-feature-b
git add .
git commit -m "feat: add API endpoints"
git push origin build/feature-b

# Create PR, get review, merge to main
```

### Strategy 2: Synchronized Merge

Features must merge together:

```bash
# Both features complete
# Create integration branch
cd ~/projects/my-app
git checkout -b integration/features-ab

# Merge feature A
git merge build/feature-a
# Resolve conflicts if any

# Merge feature B
git merge build/feature-b
# Resolve conflicts if any

# Test integration
pytest tests/

# Push integration branch
git push origin integration/features-ab

# Create single PR for both features
```

### Strategy 3: Stacked PRs

Features depend on each other:

```bash
# PR 1: Feature A (base: main)
build/feature-a -> main

# PR 2: Feature B (base: feature-a)
build/feature-b -> build/feature-a

# PR 3: Feature C (base: feature-b)
build/feature-c -> build/feature-b

# Merge order: A, then B, then C
```

### BuildRunner Merge Helper

```bash
# Check merge readiness
br parallel check-merge

# Output:
# build-auth:      ✓ Ready (tests passing, quality gate passing)
# build-api:       ✓ Ready (depends on auth, which is ready)
# build-dashboard: ✗ Not ready (quality gate failing)

# Create merge plan
br parallel merge-plan

# Output:
# Merge Plan:
# 1. Merge build-auth to main
# 2. Merge build-api to main
# 3. Wait for build-dashboard to pass quality gate
```

## Real Example: BuildRunner 3.0

BuildRunner itself was built using parallel builds!

### Week 1: Four Parallel Builds

```yaml
# .buildrunner/parallel.yaml (simplified)
builds:
  # Build 1A - Independent
  - id: quality-gaps
    name: "Code Quality + Gap Analysis"
    worktree: ../br3-quality-gaps
    branch: build/quality-gaps
    duration: "1 day"

  # Build 1B - Independent
  - id: docs-core
    name: "Core Documentation"
    worktree: ../br3-docs-core
    branch: build/docs-core
    duration: "2 days"

  # Build 1C - Depends on 1A
  - id: arch-guard
    name: "Architecture Guard"
    worktree: ../br3-arch-guard
    branch: build/arch-guard
    duration: "1 day"
    depends_on:
      - quality-gaps    # Reuses quality system

  # Build 1D - Independent
  - id: tutorials
    name: "Tutorial System"
    worktree: ../br3-tutorials
    branch: build/tutorials
    duration: "1 day"
```

Timeline without parallel builds: **5 days**
Timeline with parallel builds: **2 days** ✨

### Week 2: Integration

```yaml
# .buildrunner/parallel.yaml
integration:
  branches:
    - build/quality-gaps
    - build/docs-core
    - build/arch-guard
    - build/tutorials

  strategy: synchronized    # Merge all together
  target: main
  tag: v3.0.0-rc.2
```

### Actual Commands Used

```bash
# Week 1 - Create all worktrees
cd ~/Projects/BuildRunner3

git worktree add ../br3-quality-gaps -b build/quality-gaps
git worktree add ../br3-docs-core -b build/docs-core
git worktree add ../br3-arch-guard -b build/arch-guard
git worktree add ../br3-tutorials -b build/tutorials

# Work in each worktree independently
# (4 different terminal windows)

# Week 2 - Merge all
git checkout main
git merge build/quality-gaps
git merge build/docs-core
git merge build/arch-guard
git merge build/tutorials
git tag v3.0.0-rc.2
```

Result: **BuildRunner 3.0 delivered on schedule!**

## Best Practices

### 1. Use Descriptive Worktree Names

```bash
# Good
git worktree add ../my-app-user-auth -b build/user-auth
git worktree add ../my-app-payment-gateway -b build/payment

# Bad
git worktree add ../temp -b feature
git worktree add ../app2 -b dev
```

### 2. Keep Main Worktree Clean

```bash
# Main worktree = main branch only
cd ~/projects/my-app
git checkout main

# All features in separate worktrees
# Don't do feature work in main worktree
```

### 3. Isolate Environments

```bash
# Each worktree gets own venv
cd ../my-app-feature-a
python3 -m venv .venv

cd ../my-app-feature-b
python3 -m venv .venv

# Prevents dependency conflicts
```

### 4. Clean Up When Done

```bash
# Remove worktree after merge
git worktree remove ../my-app-feature-a

# Or force remove if changes exist
git worktree remove ../my-app-feature-a --force

# Prune stale worktrees
git worktree prune
```

### 5. Document Dependencies

```yaml
# .buildrunner/parallel.yaml
builds:
  - id: feature-a
    notes: "Authentication system, no dependencies"

  - id: feature-b
    notes: "API layer, requires auth models from feature-a"
    depends_on:
      - feature-a
```

### 6. Sync Regularly

```bash
# In each worktree, keep up-to-date with main
cd ../my-app-feature-a
git fetch origin
git rebase origin/main

# Or merge
git merge origin/main
```

## Troubleshooting

### Issue: "fatal: 'build/feature-a' is already checked out"

**Cause:** Branch already used in another worktree

**Solution:**
```bash
# List worktrees to find where it's checked out
git worktree list

# Remove old worktree first
git worktree remove ../old-path

# Or use different branch name
git worktree add ../my-app-feature-a2 -b build/feature-a-v2
```

### Issue: Conflicts When Merging Multiple Branches

**Cause:** Both features modified same files

**Solution:**
```bash
# Create integration branch
git checkout -b integration/all-features

# Merge one at a time
git merge build/feature-a
# Fix conflicts

git merge build/feature-b
# Fix conflicts

# Test integration
pytest

# Then merge integration branch to main
git checkout main
git merge integration/all-features
```

### Issue: Worktree Has Uncommitted Changes

**Cause:** Forgot to commit in worktree

**Solution:**
```bash
# Option 1: Commit changes
cd ../my-app-feature-a
git add .
git commit -m "WIP: save progress"

# Option 2: Remove with force
cd ~/projects/my-app
git worktree remove ../my-app-feature-a --force
```

### Issue: Different Test Results in Different Worktrees

**Cause:** Environment differences

**Solution:**
```bash
# Ensure same Python version
cd ../my-app-feature-a
python --version

cd ../my-app-feature-b
python --version  # Should match

# Ensure same dependencies
pip freeze > /tmp/deps-a.txt
cd ../my-app-feature-b
pip freeze > /tmp/deps-b.txt
diff /tmp/deps-a.txt /tmp/deps-b.txt
```

### Issue: Disk Space Issues with Multiple Worktrees

**Cause:** Each worktree + venv takes space

**Solution:**
```bash
# Check worktree sizes
du -sh ../my-app*

# Share venv across worktrees (careful!)
cd ../my-app-feature-a
rm -rf .venv
ln -s ~/projects/my-app/.venv .venv

# Or use shared packages directory
pip install --user  # Installs to ~/.local
```

## Summary

You've learned:

✅ What git worktrees are and their benefits
✅ How to set up worktrees for parallel development
✅ How to orchestrate builds across worktrees
✅ How to manage dependencies between builds
✅ Different merge strategies
✅ Real example from BuildRunner 3.0 development
✅ Best practices for parallel builds
✅ Common issues and solutions

## Next Steps

- Read [COMPLETION_ASSURANCE.md](COMPLETION_ASSURANCE.md) - Ensure nothing is missed
- Read [QUALITY_GATES.md](QUALITY_GATES.md) - Enforce quality across builds
- Try parallel builds on your next multi-feature project!

Happy parallel building! 🚀
