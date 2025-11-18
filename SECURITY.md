# Security - BuildRunner 3.1

**Status:** Build 4E - Security Foundation
**Version:** v3.1.0-alpha
**Last Updated:** 2025-11-18

---

## Overview

BuildRunner 3.1 includes comprehensive security safeguards to prevent common vulnerabilities and protect sensitive data. These checks are integrated into all development workflows including pre-commit hooks, quality gates, and gap analysis.

### Tier 1 Security Checks (Non-Negotiable)

1. **Secret Detection** - Prevents accidentally committing API keys, tokens, and credentials
2. **SQL Injection Detection** - Identifies unsafe database query construction
3. **Test Coverage** - Ensures adequate test coverage (warning only, not blocking)

---

## Quick Start

### Install Pre-Commit Hooks

```bash
br security hooks install
```

This installs a git pre-commit hook that automatically runs Tier 1 security checks before every commit. Commits with security issues will be blocked.

### Check Your Code

```bash
# Run all security checks
br security check

# Check only staged files (faster)
br security check --staged

# Check specific types
br security check --no-sql        # Skip SQL injection checks
br security check --secrets       # Only check for secrets
```

### Scan for Issues

```bash
# Scan entire project
br security scan

# Scan specific file
br security scan --file config.py

# Scan specific directory
br security scan --directory src/
```

---

## Secret Detection

### What Gets Detected

BuildRunner detects **13 types of secrets**:

1. **Anthropic API Keys** - `sk-ant-*`
2. **OpenAI API Keys** - `sk-proj-*`, `sk-*`
3. **OpenRouter API Keys** - `sk-or-v1-*`
4. **JWT Tokens** - `eyJ*`
5. **Notion Secrets** - `ntn_*`, `secret_*`
6. **Apify API Keys** - `apify_api_*`
7. **AWS Access Keys** - `AKIA*`
8. **GitHub Tokens** - `gh*_*`
9. **Slack Tokens** - `xox*`
10. **Bearer Tokens** - `Bearer *`
11. **Basic Auth** - `Basic *`
12. **Generic API Keys** - Various patterns
13. **Database Credentials** - Connection strings with passwords

### How It Works

Secrets are detected using regex patterns and automatically masked in output:

```
Original:  sk-ant-api03-abc123def456ghi789jkl012mno345pqr678
Masked:    sk-a...r678
```

### If Secrets Are Detected

**Immediate Actions:**

1. **DO NOT** commit the file
2. **DO NOT** push to GitHub
3. Remove the secret from the file immediately
4. Move the secret to a `.env` file
5. Add `.env` to `.gitignore`
6. Rotate the compromised secret if it was committed

**Example - Safe Secret Storage:**

```python
# ❌ WRONG - Hardcoded secret
api_key = "sk-ant-abc123def456"

# ✅ CORRECT - Environment variable
import os
api_key = os.getenv("ANTHROPIC_API_KEY")
```

**`.env` file:**
```bash
ANTHROPIC_API_KEY=sk-ant-abc123def456
```

**`.gitignore` file:**
```
.env
*.env
.env.*
```

### Whitelist False Positives

If you have legitimate test data or examples that match secret patterns, add them to the whitelist:

**`.buildrunner/security/whitelist.txt`**
```
# Whitelist format:
# file:line:pattern    - Specific instance
# file:line            - Entire line
# file                 - Entire file

tests/test_api.py:42:anthropic_key
tests/examples/        # Entire directory
```

---

## SQL Injection Detection

### Unsafe Patterns Detected

**Python:**

```python
# ❌ String concatenation
query = "SELECT * FROM users WHERE id=" + user_id

# ❌ f-strings
query = f"SELECT * FROM users WHERE id={user_id}"

# ❌ .format()
query = "SELECT * FROM users WHERE id={}".format(user_id)

# ❌ % formatting
query = "SELECT * FROM users WHERE id=%s" % user_id
```

**JavaScript/TypeScript:**

```javascript
// ❌ Template literals
const query = `SELECT * FROM users WHERE id=${userId}`;

// ❌ String concatenation
const query = "SELECT * FROM users WHERE id=" + userId;
```

### Safe Alternatives

**Python - Using parameterized queries:**

```python
# ✅ SQLite
cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))

# ✅ PostgreSQL (psycopg2)
cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))

# ✅ SQLAlchemy ORM
user = db.session.query(User).filter_by(id=user_id).first()

# ✅ SQLAlchemy Core
stmt = select(users).where(users.c.id == user_id)
```

**JavaScript - Using parameterized queries:**

```javascript
// ✅ PostgreSQL (node-postgres)
const result = await client.query(
  'SELECT * FROM users WHERE id=$1',
  [userId]
);

// ✅ MySQL (mysql2)
const [rows] = await connection.execute(
  'SELECT * FROM users WHERE id=?',
  [userId]
);
```

### Severity Levels

- **High** - Direct SQL injection vulnerability (user input in queries)
- **Medium** - Potentially unsafe pattern (needs review)
- **Low** - Minor issue or false positive

---

## Pre-Commit Hooks

### Hook Behavior

The pre-commit hook runs automatically before every commit and:

1. ✅ Scans staged files for secrets
2. ✅ Scans staged files for SQL injection patterns
3. ⚠️  Checks test coverage (warning only)
4. ❌ **Blocks commit** if security issues detected
5. ⏱️  Executes quickly (performance varies by file count)

### Hook Management

```bash
# Install hook
br security hooks install

# Check installation status
br security hooks status

# Uninstall hook
br security hooks uninstall

# Reinstall (overwrite existing)
br security hooks install --force
```

### Bypass Hook (Not Recommended)

In emergencies only:

```bash
git commit --no-verify -m "Emergency fix"
```

**⚠️ WARNING:** Bypassing the hook may commit secrets or vulnerabilities to the repository!

### Hook Output Example

**✅ Success:**
```
✅ Pre-commit checks passed
No security issues detected
```

**❌ Failure:**
```
❌ COMMIT BLOCKED - Security checks failed

❌ SECRETS DETECTED:
  Line 12: [openrouter_key] sk-o...8810
  Line 15: [anthropic_key] sk-a...o012

💡 Recommendation:
  • Move secrets to .env file (add to .gitignore)
  • Use environment variables
  • Never commit API keys to git
```

---

## Integration with Quality Gates

Security checks are automatically integrated into BuildRunner's quality gate system:

```bash
# Run quality analysis (includes security checks)
br quality check
```

Quality gate thresholds:
- **Overall:** 80/100
- **Structure:** 75/100
- **Security:** 90/100 (strict!)
- **Testing:** 80/100
- **Documentation:** 70/100

Security issues penalize the security score:
- **Exposed secret:** -20 points per secret
- **SQL injection (high):** -20 points
- **SQL injection (medium):** -10 points
- **SQL injection (low):** -5 points

---

## Integration with Gap Analyzer

Security gaps are automatically detected by the gap analyzer:

```bash
# Run gap analysis (includes security gaps)
br gaps analyze
```

Security gaps are classified as **HIGH SEVERITY** and appear prominently in gap reports.

---

## Performance

⚠️ **Note:** Performance metrics are based on unit tests. Real-world performance may vary depending on file size and count.

All security checks are designed to be efficient:

| Operation | Expected | Status |
|-----------|----------|--------|
| Pre-commit checks | Fast (<2s typical) | ⚠️ Needs production testing |
| Full project scan | Moderate | ⚠️ Needs production testing |
| Single file scan | Fast | ✅ Tested |
| Pattern matching | Fast | ✅ Tested |

---

## Incident Response Guide

### If You Committed a Secret

**⚠️ CRITICAL - Act Immediately:**

1. **Rotate the secret** - Generate a new API key/token immediately
2. **Revoke the old secret** - Disable the compromised credential
3. **Remove from git history** - Use `git-filter-repo` or BFG Repo-Cleaner
4. **Audit access logs** - Check if the secret was accessed by unauthorized parties
5. **Force push cleaned history** - Overwrite remote repository (coordinate with team!)
6. **Notify team members** - Ensure everyone pulls the cleaned history

**Example - Clean Git History:**

```bash
# Install git-filter-repo
brew install git-filter-repo

# Remove secret from all history
git filter-repo --invert-paths --path 'path/to/file.py'

# Force push (WARNING: Destructive!)
git push --force origin main
```

**⚠️ WARNING:** Force pushing rewrites history and affects all collaborators!

### If You Discovered a Secret in History

1. **Report to team lead** - Don't delay
2. **Assess exposure** - Check when it was committed and who has access
3. **Follow incident response** - Same as above
4. **Update security practices** - Learn from the incident

---

## Best Practices

### Development Workflow

1. **Never hardcode secrets** - Always use environment variables
2. **Run security checks locally** - Before pushing
3. **Install pre-commit hooks** - Let automation catch mistakes
4. **Use `.env` files** - For local development secrets
5. **Add `.env` to `.gitignore`** - Immediately on project start

### Code Review Checklist

- [ ] No hardcoded secrets or API keys
- [ ] All database queries use parameterization
- [ ] Sensitive data is properly masked in logs
- [ ] Environment variables used for configuration
- [ ] `.env` files not committed to git

### Team Practices

1. **Security onboarding** - Ensure all team members install hooks
2. **Regular audits** - Run `br security scan` weekly
3. **Quality gates** - Enforce security thresholds in CI/CD
4. **Incident drills** - Practice secret rotation procedures

---

## CLI Reference

### Security Commands

```bash
# Check for security issues
br security check [--staged] [--secrets] [--sql]

# Scan for vulnerabilities
br security scan [--file FILE] [--directory DIR]

# Pre-commit checks (called by hook)
br security precommit
```

### Hook Commands

```bash
# Install pre-commit hook
br security hooks install [--force]

# Uninstall pre-commit hook
br security hooks uninstall

# Check hook status
br security hooks status
```

---

## Technical Details

### Secret Detection

- **Engine:** Pattern-based regex matching with 13 secret types
- **Masking:** Shows first/last 4 characters only
- **Performance:** Fast pattern matching (tested in unit tests)
- **False Positives:** Whitelist system available
- **Pattern Accuracy:** Relaxed patterns (20+ chars) to catch realistic keys

### SQL Injection Detection

- **Engine:** AST-based pattern analysis
- **Languages:** Python, JavaScript, TypeScript
- **Severity:** Contextual (high/medium/low)
- **Safe Examples:** Provided for each language

### Pre-Commit Hook

- **Location:** `.git/hooks/pre-commit`
- **Execution:** Automatic on `git commit`
- **Bypass:** `git commit --no-verify` (not recommended)
- **Status:** ⚠️ Hook code exists but needs production validation
- **Performance:** Fast execution expected (varies by file count)

---

## Troubleshooting

### Hook Not Running

```bash
# Check installation
br security hooks status

# Reinstall
br security hooks install --force

# Verify permissions
ls -la .git/hooks/pre-commit
# Should show: -rwxr-xr-x (executable)
```

### False Positives

Add to `.buildrunner/security/whitelist.txt`:

```
tests/test_examples.py:42
docs/examples/
```

### Slow Performance

```bash
# Check only staged files
br security check --staged

# Skip specific checks
br security check --no-sql
```

### "br command not found"

```bash
# Install BuildRunner CLI
pip install -e .

# Or use Python directly
python3 -m cli.main security check
```

---

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE-89: SQL Injection](https://cwe.mitre.org/data/definitions/89.html)
- [CWE-798: Use of Hard-coded Credentials](https://cwe.mitre.org/data/definitions/798.html)
- [Git Secrets Management](https://docs.github.com/en/code-security/secret-scanning)

---

## Support

**Report Security Issues:**
- GitHub Issues: `https://github.com/your-org/buildrunner3/issues`
- Security Contact: `security@your-org.com`

**Get Help:**
```bash
br security --help
br security check --help
br security hooks --help
```

---

*BuildRunner 3.1 Security Foundation - Protecting your codebase from Day 1*
