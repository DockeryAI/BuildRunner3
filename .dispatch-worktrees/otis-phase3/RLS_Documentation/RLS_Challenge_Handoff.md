# Critical Production Issue: Dashboard Not Rebuilding Due to RLS/PostgREST Cache

## Executive Summary
A React/Vite application using Supabase is experiencing a critical issue where the dashboard fails to rebuild and display fresh data after hard refresh. The root cause appears to be Row Level Security (RLS) policies blocking access to critical cache tables (`intelligence_cache` and `industry_profiles`), combined with PostgREST schema caching that doesn't detect policy changes.

## Technical Stack
- **Frontend**: React + Vite + TypeScript
- **Backend**: Supabase (PostgreSQL + PostgREST)
- **Auth**: Supabase Auth (anonymous + authenticated users)
- **Critical Tables**: `intelligence_cache`, `industry_profiles`, `marba_uvps`, `uvp_sessions`

## The Core Problem

### Primary Issue
1. Dashboard shows "Loading cached intelligence..." indefinitely
2. Hard refresh (Cmd+Shift+R) doesn't trigger dashboard rebuild
3. New sessions reuse old cached dashboards instead of creating fresh ones
4. Local and market insights are missing from the dashboard

### Error Messages
- **Initial**: `406 Not Acceptable` on `intelligence_cache` and `industry_profiles` tables
- **After partial fix**: `Cannot coerce the result to a single JSON object (The result contains 0 rows)` when updating `marba_uvps`
- **Current**: Dashboard not rebuilding despite multiple SQL fixes applied

### Code Locations
- **Cache Service**: `/src/services/intelligence/intelligence-cache.service.ts:100` uses `.single()` expecting 1 row
- **Dashboard**: `/src/pages/DashboardPage.tsx:267` calls `deepContextBuilder.buildDeepContext()`
- **Deep Context**: `/src/services/intelligence/deepcontext-builder.service.ts` orchestrates data fetching

## What We've Tried (Chronologically)

### 1. Initial RLS Fix Attempts
```sql
-- Added PUBLIC policies
CREATE POLICY "allow_all" ON public.intelligence_cache
  FOR ALL TO PUBLIC USING (true) WITH CHECK (true);
```
**Result**: Waited 3-5 minutes for auto-reload, no effect

### 2. Migration Deployment
- Created migration: `20251121145000_fix_uvp_sessions_rls.sql`
- **Result**: Conflict error - "Remote migration versions not found in local migrations directory"

### 3. Encyclopedia-Based Fix (Pitfall 10)
Based on RLS Encyclopedia documentation:
```sql
-- Fixed missing USING clause in UPDATE policies
CREATE POLICY "anon_update_marba_uvps"
  ON public.marba_uvps FOR UPDATE TO anon
  USING (user_id IS NULL AND created_at > NOW() - INTERVAL '24 hours')
  WITH CHECK (user_id IS NULL);
```
**Result**: Fixed marba_uvps error but dashboard still not rebuilding

### 4. Production-Ready RLS Setup
- Added missing columns (`user_id`, `is_public`, `created_at`)
- Implemented time-based anonymous access
- Created comprehensive policies for all tables
**Result**: Still not rebuilding

### 5. Code Fix
Changed `.single()` to `.maybeSingle()` in intelligence-cache.service.ts
**Result**: More graceful error handling but dashboard still not loading

### 6. Cache Clearing Attempts
- Multiple PostgREST reload methods:
  - `NOTIFY pgrst, 'reload schema'`
  - Add/drop column trick
  - Schema version bumping
**Result**: Cache not clearing, dashboard not rebuilding

## Key Discoveries

### 1. RLS Blocking Pattern
- When RLS blocks access, queries return 0 rows
- `.single()` expects exactly 1 row, throws error with 0 rows
- This creates a cascade failure in the data loading pipeline

### 2. PostgREST Cache Persistence
- PostgREST caches schema for performance
- Policy changes don't trigger automatic reload
- Supabase supposedly auto-reloads after 3-5 minutes, but this isn't working

### 3. Anonymous User Complexity
- App supports anonymous users with time-limited access (24 hours)
- Policies must handle both `user_id IS NULL` and authenticated cases
- UPDATE operations require both USING and WITH CHECK clauses

## Documentation Created
1. **RLS_Troubleshooting_Guide.md** - 40 pages, 74KB comprehensive guide
2. **RLS_Encyclopedia_Robust.md** - Complete reference with patterns and pitfalls
3. Multiple SQL fix files targeting specific issues

## Current State
- RLS is ENABLED (production requirement, cannot disable)
- Multiple policies applied but not taking effect
- PostgREST appears to be using cached schema
- Dashboard loading stuck at "Loading cached intelligence..."
- Browser console shows successful API calls but no data returned

## Constraints
1. **MUST keep RLS enabled** - Production security requirement
2. **Cannot use development-only solutions** - Must be production-ready
3. **Must support anonymous users** - Key business requirement
4. **Must maintain data security** - No PUBLIC write access to user data

## The Question
Given all the above context, attempts, and constraints:

**How do we force PostgREST to recognize the new RLS policies and allow the dashboard to load data from `intelligence_cache` and `industry_profiles` tables while maintaining production-level security?**

Specifically:
1. Why isn't PostgREST auto-reloading after 3-5 minutes as documented?
2. Is there a Supabase-specific way to force cache invalidation?
3. Are we missing something fundamental about how RLS interacts with anonymous users?
4. Is there a different pattern we should use for public cache tables?

## Ideal Solution Criteria
- Production-ready (no security compromises)
- Works with RLS enabled
- Supports both anonymous and authenticated users
- Allows dashboard to rebuild with fresh data
- Doesn't require manual intervention after deployment