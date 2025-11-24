# BuildRunner 3.0 Pre-Commit Checklist

**Purpose:** Ensure BR3 validation is run BEFORE every commit, preventing the irony of building enforcement tools without using them.

## Why This Checklist Exists

**Root Cause Identified:** During v3.1 finalization, new features were committed without running BR3 validation, despite explicit instructions to use BR3 enforcement. This checklist prevents that pattern from recurring.

---

## ✅ Pre-Commit Validation Workflow

Before running `git commit`, complete ALL steps below:

### 1. Code Quality Checks (< 30 seconds)

```bash
# Run security scan
br security check

# Run quality analysis
br quality check

# Run gap analysis
br gaps analyze
```

**Exit Criteria:**
- ✅ No NEW security issues in changed files (existing issues OK)
- ✅ Quality score doesn't decrease
- ✅ No new critical gaps introduced

### 2. Architecture Compliance (< 10 seconds)

```bash
# Verify architectural compliance
br guard check
```

**Exit Criteria:**
- ✅ No architecture violations
- ✅ All new code follows PROJECT_SPEC patterns

### 3. Automated Testing (< 2 minutes)

```bash
# Run quick autodebug checks
br autodebug run --skip-deep
```

**Exit Criteria:**
- ✅ Syntax checks pass
- ✅ Import checks pass
- ✅ Quick tests pass

### 4. Manual Review

**Ask yourself:**
- [ ] Did I read the changed files with `git diff`?
- [ ] Are commit messages clear and descriptive?
- [ ] Did I update relevant documentation?
- [ ] Did I remove debug/console statements?
- [ ] Are there any TODO comments that should be addressed?

### 5. Feature Tracking (if applicable)

If you're implementing a feature from BUILD_PLAN:

```bash
# Update feature status
br features update <feature-id> --status complete
```

---

## 🚨 Emergency Override

If you need to commit despite failing checks (e.g., work-in-progress save):

1. Use `git commit --no-verify` to bypass hooks
2. **IMMEDIATELY** create a task to fix issues:
   ```bash
   br gaps add "Fix validation issues in [file/feature]" --priority high
   ```
3. Do NOT push until issues are resolved

---

## 🎯 Quick Reference

**Minimum viable validation (< 1 minute):**
```bash
br security check && br guard check && br autodebug run --skip-deep
```

**Full validation (< 3 minutes):**
```bash
br security check && \
br quality check && \
br gaps analyze && \
br guard check && \
br autodebug run
```

**Create convenience alias:**
```bash
# Add to ~/.bashrc or ~/.zshrc
alias br-validate='br security check && br guard check && br autodebug run --skip-deep'
alias br-validate-full='br security check && br quality check && br gaps analyze && br guard check && br autodebug run'
```

---

## 📊 Validation Report

After running all checks, review:
- `.buildrunner/build-reports/security_*.json`
- `.buildrunner/build-reports/quality_*.json`
- `.buildrunner/build-reports/autodebug_*.json`

Use `br autodebug status` to see last validation summary.

---

## 🔄 Automated Enforcement

BR3 git hooks will automatically run during commit. If hooks are not installed:

```bash
# Activate all BR3 systems
bash .buildrunner/scripts/activate-all-systems.sh .

# Verify hooks are installed
ls -la .git/hooks/pre-commit
cat .git/hooks/pre-commit
```

---

## 💡 Pro Tips

1. **Run validation continuously** during development:
   ```bash
   br autodebug watch
   ```

2. **Check specific files** before staging:
   ```bash
   br autodebug run --files src/module.py
   br security check --files src/module.py
   ```

3. **Use retry analyzer** if checks fail:
   ```bash
   br autodebug retry
   # Shows intelligent fix suggestions with confidence scores
   ```

4. **Review history** to avoid repeated mistakes:
   ```bash
   br autodebug history
   # Shows failure hot spots and trends
   ```

---

## 🎓 Learning from Mistakes

**Case Study: v3.1 Finalization (2025-11-24)**

**What happened:**
- Implemented Auto-Debug and Design System features
- User explicitly said "make sure BR3 force mechanisms are working"
- Committed without running ANY BR3 checks
- User discovered the oversight

**Why it happened:**
1. Muscle memory over explicit instructions
2. Irony blindness (building enforcement without using it)
3. No systematic checklist (this document!)
4. False sense of completion
5. BR3 wasn't activated on itself

**Lesson learned:**
> "The cobbler's children have no shoes, but that's unacceptable for BR3. Use what you build."

**Fix implemented:**
- Created this checklist
- Activated BR3 on BuildRunner3 project
- Ran retroactive validation
- All new code was clean (validated the process would have caught real issues)

---

## ✅ Sign-Off

Before every commit, mentally check:

> "Did I run BR3 validation? Would I be embarrassed if this commit introduced issues that BR3 could have caught?"

If the answer is no or yes respectively, **STOP** and run the validation workflow above.

---

**Version:** 1.0
**Last Updated:** 2025-11-24
**Owned by:** BuildRunner 3.0 Development Team
**Status:** MANDATORY for all commits
