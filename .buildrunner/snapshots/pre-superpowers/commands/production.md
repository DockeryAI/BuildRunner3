---
description: Setup dev/prod architecture - current DB becomes PROD, creates DEV, outputs env vars
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion
---

# Go to Production

Converts current project to production architecture. Current Supabase becomes PROD, you create a new DEV.

---

## Step 1: Capture Current (PROD) Supabase Info

```bash
# Get current linked project (this becomes PROD)
PROD_REF=$(cat supabase/.temp/project-ref 2>/dev/null || supabase projects list 2>&1 | grep "●" | awk '{print $4}')
echo "PROD Project Ref: $PROD_REF"

# Get PROD URL and anon key from current .env or supabase
cat .env.local 2>/dev/null | grep -E "SUPABASE_URL|SUPABASE_ANON" || \
cat .env 2>/dev/null | grep -E "SUPABASE_URL|SUPABASE_ANON"
```

Store PROD info:
- `PROD_REF`: [from above]
- `PROD_URL`: https://[PROD_REF].supabase.co
- `PROD_ANON_KEY`: [from .env]

---

## Step 2: Ask for DEV Supabase Info

Ask the user:

```
Create a new Supabase project for DEV at https://supabase.com/dashboard

Name it: [project-name]-dev
Region: Same as PROD

Once created, paste the following from Project Settings > API:
1. Project Reference ID
2. Project URL
3. anon/public key
```

User will paste something like:
```
Reference ID: xjfydvpnfahdcwqxeszu
URL: https://xjfydvpnfahdcwqxeszu.supabase.co
anon key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Parse and store:
- `DEV_REF`: [reference ID]
- `DEV_URL`: [URL]
- `DEV_ANON_KEY`: [anon key]

---

## Step 3: Output Netlify Environment Variables

Output a single copyable block:

```
══════════════════════════════════════════════════════════════
COPY THESE TO NETLIFY (Site Settings > Environment Variables):
══════════════════════════════════════════════════════════════

VITE_SUPABASE_URL = [PROD_URL]
VITE_SUPABASE_ANON_KEY = [PROD_ANON_KEY]

══════════════════════════════════════════════════════════════
```

---

## Step 4: Link to DEV and Push Migrations

```bash
# Link to DEV
supabase link --project-ref [DEV_REF]

# Push all existing migrations to DEV
echo "Y" | supabase db push --include-all
```

---

## Step 5: Update Local Environment

Create/update `.env.local` for local development (uses DEV):

```env
VITE_SUPABASE_URL=[DEV_URL]
VITE_SUPABASE_ANON_KEY=[DEV_ANON_KEY]
```

Ensure `.env.local` is in `.gitignore`:
```bash
grep -q ".env.local" .gitignore || echo ".env.local" >> .gitignore
```

---

## Step 6: Create Deployment Documentation

Create `.buildrunner/DEPLOYMENT.md`:

```markdown
# Deployment Architecture

## Environments

| Env | Supabase Ref | Database |
|-----|--------------|----------|
| DEV | [DEV_REF] | Development/Testing |
| PROD | [PROD_REF] | Production (Live) |

## Database Workflow

1. **Always push to DEV first:**
   ```bash
   supabase link --project-ref [DEV_REF]
   supabase db push
   ```

2. **Test in DEV environment**

3. **Push to PROD only after user approval:**
   ```bash
   supabase link --project-ref [PROD_REF]
   supabase db push
   ```

## Quick Commands

```bash
# Switch to DEV database
supabase link --project-ref [DEV_REF]

# Switch to PROD database
supabase link --project-ref [PROD_REF]

# Check current environment
supabase projects list | grep "●"
```
```

---

## Step 7: Update Project CLAUDE.md

Add to the project's CLAUDE.md:

```markdown
## Deployment - STRICT

**Database:**
- DEV: [DEV_REF] - Push migrations here FIRST
- PROD: [PROD_REF] - Only push after DEV testing AND user approval

**NEVER push directly to PROD database without explicit user approval.**

**Code:** Netlify auto-deploys from `main` branch.

**Workflow:**
1. Work on feature branches
2. Push migrations to DEV, test
3. ASK USER before pushing migrations to PROD
4. Merge to main → auto-deploys to Netlify
```

---

## Step 8: Verify Setup

```bash
# Confirm DEV is linked
supabase projects list | grep "●"

# Confirm .env.local exists
cat .env.local | head -2

# Confirm migrations pushed to DEV
supabase migration list
```

---

## Step 9: Final Report

```markdown
## Production Architecture Complete ✅

### Supabase
| Environment | Project Ref | Status |
|-------------|-------------|--------|
| **DEV** | [DEV_REF] | ✅ Linked (default) |
| **PROD** | [PROD_REF] | ✅ Configured |

### Local Development
- `.env.local` → Points to DEV database
- All local testing uses DEV

### Netlify (paste vars if not done)
```
VITE_SUPABASE_URL = [PROD_URL]
VITE_SUPABASE_ANON_KEY = [PROD_ANON_KEY]
```

### Workflow
1. Code changes → feature branches
2. DB migrations → DEV first (`supabase db push`)
3. Test in DEV
4. Ask for approval → push to PROD
5. Merge to main → Netlify auto-deploys

### Quick Reference
```bash
# DEV database
supabase link --project-ref [DEV_REF]

# PROD database (ask first!)
supabase link --project-ref [PROD_REF]
```

See `.buildrunner/DEPLOYMENT.md` for full docs.
```

---

## Rules

1. **Current DB = PROD** - Don't modify current Supabase, it's now production
2. **DEV by default** - Always link to DEV after setup
3. **One block for Netlify** - Give user a single copy-paste block
4. **Never PROD without asking** - Always confirm before touching PROD database
5. **Document everything** - Create DEPLOYMENT.md and update CLAUDE.md
