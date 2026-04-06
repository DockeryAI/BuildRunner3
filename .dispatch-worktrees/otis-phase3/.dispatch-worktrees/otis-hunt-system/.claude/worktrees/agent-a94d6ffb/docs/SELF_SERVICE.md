# Self-Service Setup System

> Automate detection and setup of external service dependencies

## Overview

The Self-Service Setup System eliminates manual credential configuration by automatically:

- **Detecting** external service dependencies (Stripe, AWS, Supabase, etc.)
- **Guiding** through interactive credential setup
- **Validating** API keys and configuration
- **Generating** .env templates and documentation

**Key Benefits:**
- 🔍 Automatic service detection from code
- 🎯 Interactive setup wizards for each service
- ✅ Credential format validation
- 📝 Auto-generated .env templates
- 🚀 Faster onboarding for new team members

## Supported Services

The system currently supports 10 major external services:

| Service | Env Variables | Detection Pattern | Docs |
|---------|--------------|-------------------|------|
| **Stripe** | `STRIPE_SECRET_KEY`, `STRIPE_PUBLIC_KEY` | `import stripe` | [stripe.com/docs/keys](https://stripe.com/docs/keys) |
| **AWS** | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` | `import boto3` | [AWS Env Vars](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html) |
| **Supabase** | `SUPABASE_URL`, `SUPABASE_KEY` | `from supabase import` | [Supabase API Keys](https://supabase.com/docs/guides/api/api-keys) |
| **OpenAI** | `OPENAI_API_KEY` | `import openai` | [OpenAI Keys](https://platform.openai.com/api-keys) |
| **GitHub** | `GITHUB_TOKEN`, `GITHUB_REPO` | `from github import` | [GitHub Tokens](https://docs.github.com/en/authentication) |
| **Notion** | `NOTION_TOKEN` | `from notion import` | [Notion Auth](https://developers.notion.com/docs/authorization) |
| **Slack** | `SLACK_TOKEN`, `SLACK_WEBHOOK_URL` | `from slack import` | [Slack Tokens](https://api.slack.com/authentication/token-types) |
| **SendGrid** | `SENDGRID_API_KEY` | `from sendgrid import` | [SendGrid Keys](https://docs.sendgrid.com/ui/account-and-settings/api-keys) |
| **Twilio** | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` | `from twilio import` | [Twilio Keys](https://www.twilio.com/docs/iam/keys/api-key) |
| **Redis** | `REDIS_URL` | `import redis` | [Redis Docs](https://redis.io/docs/getting-started/) |

## CLI Usage

### Detect Required Services

Scan your codebase to find external service dependencies:

```bash
br service detect
```

**Example Output:**
```
Scanning codebase for service dependencies...

┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Service  ┃ Status            ┃ Env Variables             ┃ Detected In      ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ Stripe   │ ⚠️  Not configured │ STRIPE_SECRET_KEY,        │ core/payments.py │
│          │                   │ STRIPE_PUBLIC_KEY         │                  │
│ Aws      │ ✅ Configured      │ AWS_ACCESS_KEY_ID,        │ core/storage.py, │
│          │                   │ AWS_SECRET_ACCESS_KEY,    │ api/upload.py    │
│          │                   │ AWS_REGION                │                  │
│ Openai   │ ⚠️  Not configured │ OPENAI_API_KEY            │ core/ai.py       │
└──────────┴───────────────────┴───────────────────────────┴──────────────────┘

💡 Run 'br service setup <service>' to configure:
   br service setup stripe
   br service setup openai
```

### Setup a Service

Interactive setup wizard:

```bash
br service setup stripe
```

**Interactive Flow:**
```
🔧 Setting up Stripe
📚 Documentation: https://stripe.com/docs/keys
💡 Instructions: Get your API keys from https://dashboard.stripe.com/apikeys

Enter STRIPE_SECRET_KEY: sk_test_***************************
Enter STRIPE_PUBLIC_KEY: pk_test_***************************

✅ Stripe configured successfully!
Credentials saved to .env
```

### Setup All Detected Services

Run without arguments to see all services:

```bash
br service setup
```

**Output:**
```
Detected services that need setup:
  • Stripe
  • Openai

Run 'br service setup <service>' to configure a specific service
```

### Check Service Status

View setup status for all detected services:

```bash
br service status
```

**Output:**
```
# Service Setup Status

**Services Detected:** 3
**Configured:** 1/3

⚠️  **2 services need configuration:**
- stripe
- openai

## Service Details

### ✅ Aws
- **Status:** Configured
- **Required:** Yes
- **Environment Variables:** AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
- **Detected in:** core/storage.py, api/upload.py

### ⚠️ Stripe
- **Status:** Not configured
- **Required:** Yes
- **Environment Variables:** STRIPE_SECRET_KEY, STRIPE_PUBLIC_KEY
- **Detected in:** core/payments.py
- **Setup:** Run `br service setup stripe`
- **Docs:** https://stripe.com/docs/keys

### ⚠️ Openai
- **Status:** Not configured
- **Required:** Yes
- **Environment Variables:** OPENAI_API_KEY
- **Detected in:** core/ai.py
- **Setup:** Run `br service setup openai`
- **Docs:** https://platform.openai.com/api-keys
```

### Generate .env Template

Create .env.example file with all detected services:

```bash
br service template
```

**Output:**
```
✅ Generated .env.example

Template preview:
# Environment Variables for BuildRunner Project
# Copy this file to .env and fill in your credentials

# Stripe Configuration
# Documentation: https://stripe.com/docs/keys
# Required: Yes
STRIPE_SECRET_KEY=your_stripe_stripe_secret_key_here
STRIPE_PUBLIC_KEY=your_stripe_stripe_public_key_here

# Openai Configuration
# Documentation: https://platform.openai.com/api-keys
# Required: Yes
OPENAI_API_KEY=your_openai_openai_api_key_here

Copy .env.example to .env and fill in your credentials
```

## Environment Setup Guide

### Step 1: Detect Services

First, scan your codebase:

```bash
br service detect
```

### Step 2: Generate Template

Create .env.example for your team:

```bash
br service template
```

This creates `.env.example` that can be committed to git.

### Step 3: Setup Locally

Copy template and fill in credentials:

```bash
cp .env.example .env
br service setup stripe  # Interactive wizard
br service setup aws
# ... setup each service
```

### Step 4: Verify Configuration

Check that all services are configured:

```bash
br service status
```

Look for "All services are configured!" message.

### Step 5: Share with Team

Commit .env.example to git:

```bash
git add .env.example
git commit -m "Add environment template for external services"
```

Team members can then:
```bash
git pull
cp .env.example .env
# Fill in their own credentials
```

## Service-Specific Guides

### Stripe

**What you need:**
1. Stripe account at [stripe.com](https://stripe.com)
2. API keys from [dashboard.stripe.com/apikeys](https://dashboard.stripe.com/apikeys)

**Setup:**
```bash
br service setup stripe
```

**Test vs Live Keys:**
- Use `sk_test_...` for development
- Use `sk_live_...` for production (store securely!)

**Validation:**
The system checks that:
- Secret key starts with `sk_test_` or `sk_live_`
- Public key starts with `pk_test_` or `pk_live_`

### AWS

**What you need:**
1. AWS account
2. IAM user with programmatic access
3. Access key ID and secret access key

**Setup:**
```bash
br service setup aws
```

**Creating IAM Keys:**
1. Go to [IAM Console](https://console.aws.amazon.com/iam/)
2. Create user with appropriate permissions
3. Generate access key
4. Copy Access Key ID (20 characters) and Secret Access Key

**Validation:**
- Access Key ID must be exactly 20 characters
- Follows AWS key format conventions

### Supabase

**What you need:**
1. Supabase project at [supabase.com](https://supabase.com)
2. Project URL and anon/service key

**Setup:**
```bash
br service setup supabase
```

**Finding Credentials:**
1. Open your project at [app.supabase.com](https://app.supabase.com)
2. Go to Settings > API
3. Copy Project URL and anon key (or service_role key for backend)

### OpenAI

**What you need:**
1. OpenAI account
2. API key from [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

**Setup:**
```bash
br service setup openai
```

**Validation:**
- API key must start with `sk-`
- Typically 48+ characters long

**Cost Management:**
Set usage limits in OpenAI dashboard to prevent unexpected charges.

### GitHub

**What you need:**
1. GitHub account
2. Personal Access Token (PAT)

**Setup:**
```bash
br service setup github
```

**Creating PAT:**
1. Go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. Click "Generate new token"
3. Select scopes (repo, workflow, etc.)
4. Copy token immediately (can't view again)

**Scopes Needed:**
- `repo` - Full repository access
- `workflow` - Update GitHub Actions workflows
- `admin:repo_hook` - Read/write repository hooks

### Notion

**What you need:**
1. Notion workspace
2. Integration token

**Setup:**
```bash
br service setup notion
```

**Creating Integration:**
1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click "New integration"
3. Give it a name and select workspace
4. Copy Internal Integration Token

**Permissions:**
Grant integration access to specific pages/databases in Notion.

## Credential Validation

The system validates credential formats before saving:

### Format Checks

**Stripe:**
```
✅ sk_test_51HxAbCd... (correct)
❌ invalid_key (wrong format)
```

**AWS:**
```
✅ AKIAIOSFODNN7EXAMPLE (20 chars)
❌ TOOSHORT (< 20 chars)
```

**OpenAI:**
```
✅ sk-1234567890abcdef... (starts with sk-)
❌ api_key_123 (wrong prefix)
```

### Validation Workflow

```bash
# Setup with validation
br service setup stripe

# If validation fails:
❌ Validation failed: Stripe secret key should start with sk_test_ or sk_live_

# Fix and retry
```

## Best Practices

### 1. Use .env.example for Team Sharing

**Do:**
```bash
# Commit template
git add .env.example
git commit -m "Add service configuration template"

# .gitignore actual credentials
echo ".env" >> .gitignore
```

**Don't:**
```bash
# NEVER commit actual credentials
git add .env  # ❌ DON'T DO THIS
```

### 2. Different Environments

Use separate .env files:

```bash
.env.development
.env.staging
.env.production
```

Load appropriate file:
```bash
export ENV=production
python -m dotenv -f .env.$ENV run app.py
```

### 3. Rotate Credentials Regularly

Monthly rotation schedule:
```bash
# Month 1: Detect services
br service detect > services.txt

# Month 2: Review and rotate
# - Generate new keys in service dashboards
# - Run br service setup for each
# - Revoke old keys
```

### 4. Team Onboarding Checklist

For new team members:

```markdown
## Setup Checklist

- [ ] Clone repository
- [ ] Copy .env.example to .env
- [ ] Run `br service detect` to see what's needed
- [ ] Run `br service setup <service>` for each required service
- [ ] Run `br service status` to verify all configured
- [ ] Test application locally
```

### 5. CI/CD Secrets Management

**GitHub Actions:**
```yaml
# .github/workflows/deploy.yml
env:
  STRIPE_SECRET_KEY: ${{ secrets.STRIPE_SECRET_KEY }}
  AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
```

Add secrets in GitHub Settings > Secrets.

**GitLab CI:**
```yaml
# .gitlab-ci.yml
variables:
  STRIPE_SECRET_KEY: $STRIPE_SECRET_KEY
```

Add in GitLab Settings > CI/CD > Variables.

### 6. Local Development vs Production

Use different keys:

```bash
# .env.development
STRIPE_SECRET_KEY=sk_test_... # Test mode

# .env.production
STRIPE_SECRET_KEY=sk_live_... # Live mode
```

Never use production keys locally!

## Non-Interactive Mode

For CI/CD or scripting:

```bash
# Generate template without prompts
br service setup stripe --non-interactive

# Creates .env with placeholders:
# STRIPE_SECRET_KEY=your_stripe_stripe_secret_key_here
# STRIPE_PUBLIC_KEY=your_stripe_stripe_public_key_here
```

Then populate programmatically:
```bash
echo "STRIPE_SECRET_KEY=$SECRET_KEY" >> .env
echo "STRIPE_PUBLIC_KEY=$PUBLIC_KEY" >> .env
```

## Advanced Usage

### Programmatic Access

```python
from core.self_service import SelfServiceManager

manager = SelfServiceManager('/project/path')

# Detect services
requirements = manager.detect_required_services()

# Check status
for service, req in requirements.items():
    print(f"{service}: {'✅' if req.configured else '⚠️'}")

# Validate credentials
valid, msg = manager.validate_credentials('stripe', {
    'STRIPE_SECRET_KEY': 'sk_test_123...'
})
```

### Custom Service Patterns

Extend SERVICE_PATTERNS in `core/self_service.py`:

```python
SERVICE_PATTERNS['custom_service'] = {
    'import_patterns': [r'import custom_lib'],
    'usage_patterns': [r'custom_lib\.api_key'],
    'env_vars': ['CUSTOM_API_KEY'],
    'docs_url': 'https://custom.com/docs',
    'setup_instructions': 'Get API key from dashboard'
}
```

### Environment Variable Precedence

The system checks:
1. .env file in project root
2. Environment variables (os.environ)
3. .env.example (for template generation)

## Troubleshooting

### Service Not Detected

**Issue:** Service used in code but not detected

**Solutions:**
1. Check import syntax matches patterns
2. Ensure file is in scanned directories (core/, api/, cli/, plugins/)
3. Verify not in `__pycache__` or hidden directories

### .env File Not Created

**Issue:** Setup completes but .env doesn't exist

**Solution:**
```bash
# Check current directory
pwd

# Run from project root
cd /path/to/project
br service setup stripe
```

### Validation Always Fails

**Issue:** Credentials fail validation but appear correct

**Debug:**
```python
from core.self_service import SelfServiceManager

manager = SelfServiceManager()
valid, msg = manager.validate_credentials('stripe', {
    'STRIPE_SECRET_KEY': 'your_key_here'
})
print(f"Valid: {valid}")
print(f"Message: {msg}")
```

### Multiple .env Files

**Issue:** Have .env.development, .env.production, etc.

**Solution:**
```bash
# Generate template for each environment
br service template
cp .env.example .env.development
cp .env.example .env.production

# Set up each environment separately
# (manually or with scripts)
```

## Security Considerations

### Never Commit Credentials

Always exclude from git:
```gitignore
# .gitignore
.env
.env.local
.env.*.local
*.env.backup
```

### Use Secrets Management

For production:
- AWS Secrets Manager
- HashiCorp Vault
- Google Cloud Secret Manager
- Azure Key Vault

### Limit Key Permissions

**Stripe:** Use restricted keys when possible
**AWS:** Follow principle of least privilege
**GitHub:** Limit PAT scopes to minimum needed

### Rotate Regularly

Set calendar reminders:
- Monthly: Review and rotate high-privilege keys
- Quarterly: Audit all service credentials
- Immediately: Rotate if key exposed

## See Also

- [Architecture Guard](ARCHITECTURE_GUARD.md) - Validate code against specs
- [Feature Registry](FEATURES.md) - Feature tracking system
- [Git Governance](GOVERNANCE.md) - Branch protection and automation
- [BUILD_PLAN_MISSING_SYSTEMS.md](../.buildrunner/BUILD_PLAN_MISSING_SYSTEMS.md) - Implementation plan
