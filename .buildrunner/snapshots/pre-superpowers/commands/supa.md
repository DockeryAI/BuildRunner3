---
description: Connect Supabase edge function logging for current project
allowed-tools: Read, Bash, Grep, Glob
model: haiku
---

# Connect Supabase Logging

Set `DEBUG=true` on the current project's Supabase instance to enable edge function logging via `withDevLogs`.

---

## Step 1: Resolve Supabase Project Ref

Use the current working directory. Try these in order:

### 1a. Check project-ref file
```bash
cat supabase/.temp/project-ref 2>/dev/null
```

### 1b. Parse from .env files
If not found, scan for SUPABASE_URL or VITE_SUPABASE_URL:
```bash
grep -rh 'SUPABASE_URL' .env .env.local .env.development .env.production ui/.env 2>/dev/null | grep -v '^#' | head -1
```

Extract the subdomain (project ref) from the URL (`https://<ref>.supabase.co`):
```bash
echo "$URL" | sed 's|.*://||' | sed 's|\.supabase\.co.*||'
```

### 1c. Prompt user
If still not found, ask for the project ref.

---

## Step 2: Set DEBUG=true

```bash
supabase secrets set DEBUG=true --project-ref <REF>
```

---

## Step 3: Verify

```bash
supabase secrets list --project-ref <REF> 2>/dev/null | grep DEBUG
```

---

## Step 4: Report

> **Supabase logging connected** — `<ref>`
> DEBUG=true confirmed. Edge functions using `withDevLogs` will now emit internal logs.
