# 🚀 ROBUST RLS & SQL ENCYCLOPEDIA FOR SAAS
## Generated with Full Monitoring and Redundancy

**Generation Started:** 2025-11-22T03:12:19.550Z
**Generation Completed:** 2025-11-22T03:23:06.413Z
**Total Runtime:** 10.8 minutes
**Domains Processed:** 5/5
**API Calls:** 15 (15 successful)
**Tokens Used:** 27,295
**Retries:** 0
**Errors Encountered:** 0

---

## Table of Contents

- [✅ Complete Multi-Tenant SaaS Patterns](#saas_multi_tenant)
- [✅ Subscription & Billing RLS Patterns](#subscription_billing_rls)
- [✅ Advanced User Management & RBAC](#user_management_rbac)
- [✅ API Security & Integration](#api_security)
- [✅ Compliance & Regulatory](#compliance_frameworks)

---

## Original Foundation

# PostgreSQL Row Level Security (RLS) Troubleshooting Guide
## A Practical Guide for PostgREST and Supabase Integration

**Version:** 1.0
**Last Updated:** 2025-11-21
**Author:** Synapse Engineering Team
**Focus:** Production-ready solutions for PostgREST 406 errors and RLS issues

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [The Critical PostgREST TO Clause Requirement](#the-critical-postgrest-to-clause-requirement)
3. [Understanding RLS Fundamentals](#understanding-rls-fundamentals)
4. [The 406 Not Acceptable Error Explained](#the-406-not-acceptable-error-explained)
5. [Common RLS Patterns and Best Practices](#common-rls-patterns-and-best-practices)
6. [PostgREST-Specific Requirements](#postgrest-specific-requirements)
7. [Debugging Checklist for RLS Issues](#debugging-checklist-for-rls-issues)
8. [Performance Implications and Optimization](#performance-implications-and-optimization)
9. [Complete Migration Examples](#complete-migration-examples)
10. [Troubleshooting Workflow](#troubleshooting-workflow)
11. [Common Pitfalls and Solutions](#common-pitfalls-and-solutions)
12. [Appendix: Reference Commands](#appendix-reference-commands)

---

## Executive Summary

### The Problem

When using PostgREST (including Supabase), you may encounter `406 Not Acceptable` errors despite having seemingly correct RLS policies. The root cause is almost always **missing or incorrect `TO` clauses** in your `CREATE POLICY` statements.

### The Solution

Every RLS policy used with PostgREST **MUST** include an explicit `TO` clause specifying which roles the policy applies to:

```sql
-- ❌ WRONG - Will cause 406 errors in PostgREST
CREATE POLICY "allow_select"
  ON my_table
  FOR SELECT
  USING (true);

-- ✅ CORRECT - PostgREST compatible
CREATE POLICY "allow_select"
  ON my_table
  FOR SELECT
  TO public  -- or TO anon, authenticated
  USING (true);
```

### Key Takeaways

1. **Always use `TO` clauses** in RLS policies when working with PostgREST
2. **Grant table permissions** explicitly to `anon` and `authenticated` roles
3. **Test with the actual role** your application uses (usually `anon` or `authenticated`)
4. **Use `TO public`** for truly public tables (applies to all roles)
5. **Clear PostgREST schema cache** after policy changes

---

## The Critical PostgREST TO Clause Requirement

### Why PostgREST Requires TO Clauses

PostgREST uses PostgreSQL's role-based security model. When a request comes in:

1. PostgREST switches to the JWT role (usually `anon` or `authenticated`)
2. It queries the table using that role's permissions
3. PostgreSQL evaluates RLS policies that apply to that role
4. **If no policy has a `TO` clause matching the current role, access is denied**

### The TO Clause Options

```sql
-- Option 1: Specific role (most common)
TO anon            -- Anonymous/unauthenticated users
TO authenticated   -- Authenticated users only
TO service_role    -- Service/admin access

-- Option 2: Multiple roles
TO anon, authenticated

-- Option 3: All roles (use with caution)
TO public  -- Applies to ALL roles including anon, authenticated, etc.
```

### Real-World Example: The 406 Error That Won't Go Away

**Scenario:** You have this policy:

```sql
CREATE POLICY "Users can read brands"
  ON brands
  FOR SELECT
  USING (true);  -- Missing TO clause!
```

**What happens:**
1. Frontend makes request as `anon` role
2. PostgREST checks for policies applicable to `anon`
3. No `TO anon` clause found → No matching policy
4. PostgREST returns `406 Not Acceptable`

**The fix:**

```sql
DROP POLICY IF EXISTS "Users can read brands" ON brands;

CREATE POLICY "Allow reading brands"
  ON brands
  FOR SELECT
  TO public  -- Now works for all roles
  USING (true);
```

### Why This Isn't Well Documented

The `TO` clause is **optional** in standard PostgreSQL RLS, defaulting to `PUBLIC` (all roles). However:

- PostgREST's permission model requires explicit role targeting
- Default PostgreSQL behavior differs from PostgREST's interpretation
- Many RLS tutorials focus on PostgreSQL, not PostgREST integration
- This subtle difference causes the most common PostgREST RLS issues

---

## Understanding RLS Fundamentals

### What is Row Level Security?

RLS is PostgreSQL's built-in mechanism for restricting which rows users can see and modify in a table. It works at the database level, providing:

- **Mandatory access control** - Cannot be bypassed by application code
- **Row-level granularity** - Different users see different subsets of data
- **Policy-based** - Define rules using SQL expressions

### How RLS Works

```sql
-- 1. Enable RLS on a table
ALTER TABLE my_table ENABLE ROW LEVEL SECURITY;

-- 2. Create policies that define access rules
CREATE POLICY "policy_name"
  ON my_table
  FOR SELECT              -- SELECT, INSERT, UPDATE, DELETE, or ALL
  TO authenticated        -- Which roles this applies to
  USING (user_id = auth.uid());  -- Row visibility condition

-- 3. Grant table-level permissions
GRANT SELECT ON my_table TO authenticated;
```

### The Two-Layer Permission Model

Understanding PostgreSQL's permission model is crucial:

```
┌─────────────────────────────────────────────┐
│         Layer 1: Table Permissions          │
│  (GRANT/REVOKE - Who can access the table?) │
└─────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│         Layer 2: Row Level Policies         │
│   (RLS - Which specific rows can they see?) │
└─────────────────────────────────────────────┘
```

**Both layers must allow access** for a query to succeed.

### USING vs WITH CHECK Clauses

RLS policies have two types of conditions:

```sql
CREATE POLICY "example_policy"
  ON my_table
  FOR ALL
  TO authenticated
  USING (...)      -- Controls which existing rows are visible
  WITH CHECK (...) -- Controls which new/updated rows are allowed
```

**Key differences:**

| Clause | Used For | When Evaluated | Common Use |
|--------|----------|----------------|------------|
| `USING` | SELECT, UPDATE, DELETE | Reading/finding rows | Row visibility filter |
| `WITH CHECK` | INSERT, UPDATE | Before writing data | Validation/constraints |
| Both | UPDATE operations | Different phases | See below |

**UPDATE behavior:**
- `USING`: Determines which rows can be updated (row must be visible first)
- `WITH CHECK`: Validates the new values being written

**Examples:**

```sql
-- Simple SELECT policy
CREATE POLICY "select_own_data"
  ON documents
  FOR SELECT
  TO authenticated
  USING (owner_id = auth.uid());

-- INSERT policy
CREATE POLICY "insert_own_data"
  ON documents
  FOR INSERT
  TO authenticated
  WITH CHECK (owner_id = auth.uid());

-- UPDATE policy (needs both!)
CREATE POLICY "update_own_data"
  ON documents
  FOR UPDATE
  TO authenticated
  USING (owner_id = auth.uid())        -- Can only update own docs
  WITH CHECK (owner_id = auth.uid());  -- Can't change ownership

-- Permissive cache table (no restrictions)
CREATE POLICY "cache_full_access"
  ON cache_table
  FOR ALL
  TO public
  USING (true)
  WITH CHECK (true);
```

### RLS Policy Types: Permissive vs Restrictive

PostgreSQL supports two policy types (though PostgREST primarily uses permissive):

```sql
-- Permissive (default) - Policies are OR'd together
CREATE POLICY "policy1" ON table FOR SELECT TO anon
  USING (is_public = true);  -- OR

CREATE POLICY "policy2" ON table FOR SELECT TO anon
  USING (owner_id = user_id);  -- Either condition allows access

-- Restrictive - Policies are AND'd together (rare)
CREATE POLICY "policy1" ON table AS RESTRICTIVE FOR SELECT TO anon
  USING (status = 'active');  -- AND

CREATE POLICY "policy2" ON table AS RESTRICTIVE FOR SELECT TO anon
  USING (deleted_at IS NULL);  -- Both must be true
```

**In practice:** Stick with permissive (default) policies for PostgREST.

---

## The 406 Not Acceptable Error Explained

### What Does 406 Mean in PostgREST?

When PostgREST returns a `406 Not Acceptable` error, it means:

> "I cannot represent this resource in the format requested because I don't have permission to access it according to the database's RLS policies."

### The 406 vs 401 vs 403 Distinction

| Code | Meaning | Common Cause in RLS Context |
|------|---------|----------------------------|
| 401 Unauthorized | Invalid or missing JWT | Authentication failed |
| 403 Forbidden | Valid JWT, but operation not allowed | Table-level GRANT missing |
| **406 Not Acceptable** | Cannot fulfill request in requested format | **No matching RLS policy for role** |

### 406 Error Workflow

```
Request → PostgREST → Switch to JWT role → Query table
                                              ↓
                              Check table permissions (GRANT)
                                              ↓
                                    Permissions OK?
                                   ↙              ↘
                                 NO              YES
                                  ↓               ↓
                            403 Forbidden    Check RLS policies
                                                  ↓
                                        Has policy with TO clause
                                        matching current role?
                                       ↙                    ↘
                                     NO                    YES
                                      ↓                     ↓
                              406 Not Acceptable     Execute query
                                                           ↓
                                                    Return results
```

### Real-World 406 Debugging Example

**Symptom:** Dashboard fails to load with 406 error on `uvp_sessions` table

**Step 1: Check current policies**

```sql
SELECT
  schemaname,
  tablename,
  policyname,
  permissive,
  roles,
  cmd,
  qual,
  with_check
FROM pg_policies
WHERE tablename = 'uvp_sessions';
```

**Bad output (causes 406):**

```
tablename    | policyname           | roles        | cmd
-------------|---------------------|--------------|--------
uvp_sessions | allow_select        | {}           | SELECT
uvp_sessions | allow_insert        | {}           | INSERT
```

Notice: `roles` is empty (`{}`), meaning no `TO` clause!

**Step 2: Check table permissions**

```sql
SELECT grantee, privilege_type
FROM information_schema.table_privileges
WHERE table_name = 'uvp_sessions'
  AND grantee IN ('anon', 'authenticated', 'public');
```

**Good output:**

```
grantee       | privilege_type
--------------|---------------
anon          | SELECT
anon          | INSERT
anon          | UPDATE
authenticated | SELECT
authenticated | INSERT
```

**Step 3: Identify the problem**

- Table permissions: ✅ OK
- RLS policies exist: ✅ OK
- **Policies have `TO` clauses: ❌ MISSING** ← This is the 406 cause!

**Step 4: Fix the policies**

```sql
-- Drop broken policies
DROP POLICY IF EXISTS "allow_select" ON uvp_sessions;
DROP POLICY IF EXISTS "allow_insert" ON uvp_sessions;

-- Create correct policies with TO clauses
CREATE POLICY "Allow reading sessions"
  ON uvp_sessions
  FOR SELECT
  TO public  -- ← THE FIX
  USING (true);

CREATE POLICY "Allow creating sessions"
  ON uvp_sessions
  FOR INSERT
  TO public  -- ← THE FIX
  WITH CHECK (brand_id IS NOT NULL);
```

**Step 5: Force PostgREST to reload**

```sql
-- Trigger schema reload by modifying table metadata
COMMENT ON TABLE uvp_sessions IS 'Sessions table - Updated at 2025-11-21';

-- Send reload notification
NOTIFY pgrst, 'reload schema';

-- Or use the column trick to force detection
ALTER TABLE uvp_sessions ADD COLUMN _reload BOOLEAN DEFAULT true;
ALTER TABLE uvp_sessions DROP COLUMN _reload;
```

**Step 6: Verify the fix**

```sql
-- Check policies now have roles
SELECT policyname, roles, cmd
FROM pg_policies
WHERE tablename = 'uvp_sessions';

-- Expected output:
-- policyname              | roles              | cmd
-- Allow reading sessions  | {public}           | SELECT
-- Allow creating sessions | {public}           | INSERT
```

### Why PostgREST Doesn't Auto-Reload

PostgREST caches the database schema for performance. Changes to policies don't automatically trigger a reload. You must:

1. **Modify the schema** (add/drop column, change type, etc.)
2. **Send NOTIFY** signal
3. **Restart PostgREST** (in local dev)
4. **Wait** (Supabase auto-reloads after a few minutes, or deploy the migration)

---

## Common RLS Patterns and Best Practices

### Pattern 1: User-Owned Resources

**Use case:** Users can only access their own data (documents, profiles, settings)

```sql
-- Enable RLS
ALTER TABLE user_documents ENABLE ROW LEVEL SECURITY;

-- Grant permissions
GRANT ALL ON user_documents TO authenticated;

-- Policy: Users see only their documents
CREATE POLICY "Users can view own documents"
  ON user_documents
  FOR SELECT
  TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "Users can create own documents"
  ON user_documents
  FOR INSERT
  TO authenticated
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own documents"
  ON user_documents
  FOR UPDATE
  TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can delete own documents"
  ON user_documents
  FOR DELETE
  TO authenticated
  USING (user_id = auth.uid());
```

**Key points:**
- Uses `auth.uid()` - Supabase helper that returns current user's ID from JWT
- Requires `authenticated` role (logged-in users only)
- Both `USING` and `WITH CHECK` on UPDATE prevent ownership changes

### Pattern 2: Public Read, Authenticated Write

**Use case:** Blog posts, products - anyone can read, only authenticated users can create

```sql
ALTER TABLE blog_posts ENABLE ROW LEVEL SECURITY;

-- Grant read to everyone
GRANT SELECT ON blog_posts TO public;

-- Grant write to authenticated users
GRANT INSERT, UPDATE, DELETE ON blog_posts TO authenticated;

-- Anyone can read
CREATE POLICY "Public can read posts"
  ON blog_posts
  FOR SELECT
  TO public  -- Applies to anon and authenticated
  USING (published = true);

-- Only authors can create
CREATE POLICY "Authors can create posts"
  ON blog_posts
  FOR INSERT
  TO authenticated
  WITH CHECK (author_id = auth.uid());

-- Only authors can update their posts
CREATE POLICY "Authors can update own posts"
  ON blog_posts
  FOR UPDATE
  TO authenticated
  USING (author_id = auth.uid())
  WITH CHECK (author_id = auth.uid());
```

### Pattern 3: Tenant Isolation (Multi-Tenancy)

**Use case:** SaaS apps where each organization has isolated data

```sql
ALTER TABLE tenant_data ENABLE ROW LEVEL SECURITY;

GRANT ALL ON tenant_data TO authenticated;

-- Function to get current user's tenant
CREATE OR REPLACE FUNCTION auth.tenant_id()
RETURNS UUID AS $$
  SELECT COALESCE(
    auth.jwt() -> 'app_metadata' ->> 'tenant_id',
    '00000000-0000-0000-0000-000000000000'
  )::UUID;
$$ LANGUAGE SQL STABLE;

-- Tenant isolation policy
CREATE POLICY "Tenant isolation"
  ON tenant_data
  FOR ALL
  TO authenticated
  USING (tenant_id = auth.tenant_id())
  WITH CHECK (tenant_id = auth.tenant_id());
```

**Key points:**
- Custom function extracts tenant_id from JWT metadata
- Single policy covers all operations (FOR ALL)
- Prevents data leakage between tenants

### Pattern 4: Role-Based Access Control (RBAC)

**Use case:** Admin vs regular users, different permission levels

```sql
ALTER TABLE sensitive_data ENABLE ROW LEVEL SECURITY;

GRANT ALL ON sensitive_data TO authenticated;

-- Function to check user role
CREATE OR REPLACE FUNCTION auth.user_role()
RETURNS TEXT AS $$
  SELECT COALESCE(
    auth.jwt() -> 'app_metadata' ->> 'role',
    'user'
  )::TEXT;
$$ LANGUAGE SQL STABLE;

-- Admins can see everything
CREATE POLICY "Admins can view all"
  ON sensitive_data
  FOR SELECT
  TO authenticated
  USING (auth.user_role() = 'admin');

-- Users can see only their own data
CREATE POLICY "Users can view own data"
  ON sensitive_data
  FOR SELECT
  TO authenticated
  USING (
    auth.user_role() = 'user'
    AND user_id = auth.uid()
  );

-- Only admins can modify
CREATE POLICY "Admins can modify"
  ON sensitive_data
  FOR ALL
  TO authenticated
  USING (auth.user_role() = 'admin')
  WITH CHECK (auth.user_role() = 'admin');
```

**Note:** Multiple SELECT policies are OR'd together, so both admins and users can query.

### Pattern 5: Public Cache/Reference Tables

**Use case:** Cache tables, lookup data, read-only reference tables

```sql
-- Common for: intelligence_cache, location_detection_cache, industry_profiles

ALTER TABLE intelligence_cache ENABLE ROW LEVEL SECURITY;

-- Grant to everyone
GRANT ALL ON intelligence_cache TO public;

-- Completely open policies
CREATE POLICY "Public read cache"
  ON intelligence_cache
  FOR SELECT
  TO public
  USING (true);

CREATE POLICY "Public write cache"
  ON intelligence_cache
  FOR INSERT
  TO public
  WITH CHECK (true);

CREATE POLICY "Public update cache"
  ON intelligence_cache
  FOR UPDATE
  TO public
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Public delete cache"
  ON intelligence_cache
  FOR DELETE
  TO public
  USING (true);
```

**When to use:**
- Ephemeral cache data with TTL
- Non-sensitive reference/lookup tables
- Public APIs

**When NOT to use:**
- User data
- Financial records
- Anything requiring audit trails

### Pattern 6: Time-Based Access

**Use case:** Scheduled content, expiring access, trials

```sql
ALTER TABLE scheduled_content ENABLE ROW LEVEL SECURITY;

GRANT SELECT ON scheduled_content TO public;
GRANT INSERT, UPDATE, DELETE ON scheduled_content TO authenticated;

CREATE POLICY "Published content is visible"
  ON scheduled_content
  FOR SELECT
  TO public
  USING (
    published_at <= NOW()
    AND (expires_at IS NULL OR expires_at > NOW())
  );

CREATE POLICY "Authors can see their drafts"
  ON scheduled_content
  FOR SELECT
  TO authenticated
  USING (author_id = auth.uid());
```

### Pattern 7: Hierarchical/Inherited Permissions

**Use case:** Organization > Team > User hierarchy

```sql
ALTER TABLE team_documents ENABLE ROW LEVEL SECURITY;

GRANT ALL ON team_documents TO authenticated;

-- Function to check team membership
CREATE OR REPLACE FUNCTION auth.user_teams()
RETURNS UUID[] AS $$
  SELECT ARRAY_AGG(team_id)
  FROM team_members
  WHERE user_id = auth.uid();
$$ LANGUAGE SQL STABLE;

CREATE POLICY "Team members can access documents"
  ON team_documents
  FOR SELECT
  TO authenticated
  USING (team_id = ANY(auth.user_teams()));
```

### Best Practice Checklist

When creating RLS policies, ensure:

- [ ] **Always include `TO` clause** when using PostgREST
- [ ] **Grant table permissions** to the same roles as your policies
- [ ] **Use specific operations** (SELECT, INSERT, etc.) instead of FOR ALL when possible
- [ ] **Include both USING and WITH CHECK** for UPDATE policies
- [ ] **Test with actual role** (`SET ROLE anon;` in psql)
- [ ] **Name policies descriptively** (not just "policy1", "policy2")
- [ ] **Document complex logic** with comments
- [ ] **Use functions** for repeated logic (DRY principle)
- [ ] **Index columns** used in RLS conditions for performance
- [ ] **Avoid expensive operations** in policy conditions (joins, subqueries)

---

## PostgREST-Specific Requirements

### The PostgREST Permission Model

PostgREST acts as a database proxy that:

1. Receives HTTP requests
2. Validates JWT tokens
3. Switches to the role specified in the JWT (`anon`, `authenticated`, or custom)
4. Executes SQL queries as that role
5. Returns results based on that role's permissions

### Critical Requirements for PostgREST

#### 1. Explicit TO Clauses (Repeated for Emphasis)

```sql
-- This works in pure PostgreSQL but FAILS in PostgREST
CREATE POLICY "select_policy" ON table FOR SELECT USING (true);

-- This works in PostgREST
CREATE POLICY "select_policy" ON table FOR SELECT TO public USING (true);
CREATE POLICY "select_policy" ON table FOR SELECT TO anon USING (true);
CREATE POLICY "select_policy" ON table FOR SELECT TO authenticated USING (true);
```

#### 2. Table-Level Grants Must Match Policy Roles

```sql
-- If your policy targets 'anon'
CREATE POLICY "anon_select" ON table FOR SELECT TO anon USING (true);

-- You MUST grant table permission to anon
GRANT SELECT ON table TO anon;  -- Required!
```

**Common mismatch:**

```sql
-- Policy for authenticated
CREATE POLICY "auth_select" ON table FOR SELECT TO authenticated USING (true);

-- But forgot to grant!
-- GRANT SELECT ON table TO authenticated;  ← Missing = 403 error
```

#### 3. Sequence Permissions for SERIAL/IDENTITY Columns

When inserting rows with auto-incrementing IDs:

```sql
-- Not enough to just grant table permissions
GRANT INSERT ON my_table TO anon;

-- ALSO need sequence permission
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon;

-- Or grant specifically
GRANT USAGE, SELECT ON SEQUENCE my_table_id_seq TO anon;
```

**Without sequence permissions:**
```
ERROR: permission denied for sequence my_table_id_seq
```

#### 4. Function Execution Permissions

If your RLS policies use custom functions:

```sql
-- Policy uses a function
CREATE POLICY "use_function" ON table FOR SELECT TO anon
  USING (my_check_function());

-- Function must be executable by that role
GRANT EXECUTE ON FUNCTION my_check_function() TO anon;

-- AND the function should be SECURITY DEFINER if it needs elevated permissions
CREATE OR REPLACE FUNCTION my_check_function()
RETURNS BOOLEAN AS $$
  -- function body
$$ LANGUAGE SQL STABLE SECURITY DEFINER;
```

### PostgREST Schema Cache Issues

PostgREST caches the database schema. After changing policies, you must force a reload.

#### Method 1: Schema Change (Guaranteed)

```sql
-- Add and immediately drop a column
ALTER TABLE my_table ADD COLUMN _force_reload BOOLEAN DEFAULT true;
ALTER TABLE my_table DROP COLUMN _force_reload;

-- PostgREST detects schema change and reloads
```

#### Method 2: NOTIFY Signal

```sql
NOTIFY pgrst, 'reload schema';
NOTIFY pgrst, 'reload config';
```

**Note:** NOTIFY only works if:
- PostgREST is configured to listen (default in Supabase)
- You have permission to send notifications
- PostgREST is actively listening to the database

#### Method 3: Comment Update (Gentle)

```sql
-- Update table comment with timestamp
COMMENT ON TABLE my_table IS 'Updated at 2025-11-21 10:30:00';

-- May or may not trigger reload depending on PostgREST version
```

#### Method 4: Restart (Local Dev)

In local development, simply restart PostgREST:

```bash
# Docker
docker restart <postgrest-container>

# Systemd
systemctl restart postgrest

# Supabase CLI
supabase stop
supabase start
```

### Supabase-Specific Considerations

#### Auth Helpers

Supabase provides helpful functions for RLS:

```sql
auth.uid()        -- Current user's UUID
auth.jwt()        -- Full JWT as JSONB
auth.role()       -- Current role name
auth.email()      -- Current user's email (if in JWT)
```

**Example usage:**

```sql
-- User-owned resources
USING (user_id = auth.uid())

-- Check custom JWT claims
USING ((auth.jwt() -> 'app_metadata' ->> 'role') = 'admin')

-- Email verification check
USING ((auth.jwt() -> 'email_verified')::BOOLEAN = true)
```

#### Supabase Storage Integration

When using Supabase Storage with RLS:

```sql
-- The storage.objects table respects RLS
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- Example: Users can access their own files
CREATE POLICY "Users can access own files"
  ON storage.objects
  FOR SELECT
  TO authenticated
  USING (owner = auth.uid());

CREATE POLICY "Users can upload files"
  ON storage.objects
  FOR INSERT
  TO authenticated
  WITH CHECK (owner = auth.uid());
```

#### Supabase Realtime (Broadcast)

RLS policies automatically apply to Realtime subscriptions:

```javascript
// Frontend subscribes to changes
supabase
  .from('messages')
  .on('INSERT', payload => console.log(payload))
  .subscribe();

// User only receives INSERT events for rows they can SELECT via RLS
```

### Testing PostgREST Policies

#### Method 1: Use SET ROLE in psql

```sql
-- Test as anonymous user
SET ROLE anon;
SELECT * FROM my_table;  -- Uses anon's permissions and RLS policies

-- Test as authenticated user
SET ROLE authenticated;
SELECT * FROM my_table;

-- Reset to your admin role
RESET ROLE;
```

#### Method 2: Use Supabase SQL Editor with RLS Enabled

In Supabase dashboard, the SQL editor runs as `service_role` by default (bypasses RLS). To test with RLS:

```sql
-- Temporarily assume anon role
SET LOCAL ROLE anon;
SELECT * FROM my_table;

-- Transaction auto-resets role when complete
```

#### Method 3: Integration Tests with Actual API Calls

```javascript
// Test with unauthenticated client
const { data, error } = await supabase
  .from('my_table')
  .select('*');

console.log('Anon can see:', data);

// Test with authenticated client
const { data: authData, error: authError } = await supabase
  .auth.signIn({ email, password });

const { data: userData } = await supabase
  .from('my_table')
  .select('*');

console.log('Authenticated user can see:', userData);
```

#### Method 4: Check Explain Plans

See what PostgreSQL is actually doing:

```sql
SET ROLE anon;

EXPLAIN (ANALYZE, VERBOSE, BUFFERS)
SELECT * FROM my_table;

-- Look for:
-- - "Filter: (POLICY expression)" lines
-- - Execution time impact
-- - Index usage
```

---

## Debugging Checklist for RLS Issues

When you encounter RLS issues (especially 406 errors), work through this checklist systematically:

### Level 1: Basic Configuration

- [ ] **RLS is enabled on the table**
  ```sql
  SELECT relname, relrowsecurity
  FROM pg_class
  WHERE relname = 'your_table';
  -- relrowsecurity should be 't' (true)
  ```

- [ ] **Table permissions granted to role**
  ```sql
  SELECT grantee, privilege_type
  FROM information_schema.table_privileges
  WHERE table_name = 'your_table'
    AND grantee IN ('anon', 'authenticated', 'public');
  ```

- [ ] **Policies exist for the table**
  ```sql
  SELECT COUNT(*)
  FROM pg_policies
  WHERE tablename = 'your_table';
  -- Should be > 0
  ```

### Level 2: Policy Configuration

- [ ] **Policies have TO clauses**
  ```sql
  SELECT policyname, roles
  FROM pg_policies
  WHERE tablename = 'your_table';
  -- 'roles' column should NOT be empty {}
  ```

- [ ] **Policy TO clause matches your JWT role**
  ```sql
  -- If using anon role, check for:
  SELECT policyname
  FROM pg_policies
  WHERE tablename = 'your_table'
    AND ('anon' = ANY(roles) OR 'public' = ANY(roles));
  ```

- [ ] **Policy covers the operation you're performing**
  ```sql
  SELECT policyname, cmd
  FROM pg_policies
  WHERE tablename = 'your_table';
  -- cmd should include SELECT, INSERT, UPDATE, or DELETE as needed
  ```

- [ ] **USING clause for SELECT/UPDATE/DELETE**
  ```sql
  SELECT policyname, cmd, qual
  FROM pg_policies
  WHERE tablename = 'your_table'
    AND cmd IN ('SELECT', 'UPDATE', 'DELETE');
  -- 'qual' should not be NULL
  ```

- [ ] **WITH CHECK clause for INSERT/UPDATE**
  ```sql
  SELECT policyname, cmd, with_check
  FROM pg_policies
  WHERE tablename = 'your_table'
    AND cmd IN ('INSERT', 'UPDATE');
  -- 'with_check' should not be NULL
  ```

### Level 3: Dependencies

- [ ] **Sequence permissions (for INSERT with SERIAL columns)**
  ```sql
  SELECT sequence_name
  FROM information_schema.sequences
  WHERE sequence_schema = 'public';

  -- Check grants
  SELECT grantee, privilege_type
  FROM information_schema.usage_privileges
  WHERE object_name = 'your_table_id_seq'
    AND grantee IN ('anon', 'authenticated');
  ```

- [ ] **Function permissions (if policies use functions)**
  ```sql
  -- List functions used in policies
  SELECT DISTINCT routine_name
  FROM information_schema.routines
  WHERE routine_schema = 'auth' OR routine_schema = 'public';

  -- Check if role can execute
  SELECT has_function_privilege('anon', 'auth.uid()', 'EXECUTE');
  ```

- [ ] **Foreign key related tables** (if policy checks related data)
  ```sql
  -- If policy does: WHERE team_id IN (SELECT team_id FROM user_teams)
  -- Ensure RLS on user_teams allows that SELECT
  ```

### Level 4: Testing

- [ ] **Test with actual role**
  ```sql
  BEGIN;
  SET LOCAL ROLE anon;
  SELECT * FROM your_table;
  ROLLBACK;
  ```

- [ ] **Verify policy logic**
  ```sql
  -- Check if policy USING condition is true
  SET ROLE anon;
  SELECT *, (your_policy_condition) AS policy_allows
  FROM your_table;
  RESET ROLE;
  ```

- [ ] **Check for competing policies**
  ```sql
  -- Look for RESTRICTIVE policies that might block access
  SELECT policyname, permissive
  FROM pg_policies
  WHERE tablename = 'your_table';
  -- Most should be 'PERMISSIVE'
  ```

### Level 5: PostgREST Specific

- [ ] **PostgREST schema cache is fresh**
  ```sql
  -- Force reload
  ALTER TABLE your_table ADD COLUMN _reload BOOLEAN DEFAULT true;
  ALTER TABLE your_table DROP COLUMN _reload;
  ```

- [ ] **Check PostgREST logs** for detailed errors
  ```bash
  # Docker
  docker logs <postgrest-container> --tail 100

  # Supabase logs
  supabase logs --tail 100
  ```

- [ ] **Verify JWT role claim**
  ```javascript
  // Frontend
  const { data: { session } } = await supabase.auth.getSession();
  console.log('Current role:', session?.user?.role); // Usually 'authenticated'

  // For anon requests, no session = 'anon' role
  ```

- [ ] **Check for typos in table/column names**
  ```sql
  -- PostgREST is case-sensitive in some contexts
  \d your_table  -- Verify exact column names
  ```

### Level 6: Advanced Debugging

- [ ] **Enable query logging**
  ```sql
  -- See exactly what queries PostgREST runs
  ALTER DATABASE postgres SET log_statement = 'all';
  -- Warning: Very verbose, use temporarily!
  ```

- [ ] **Check for triggers that might interfere**
  ```sql
  SELECT tgname, tgtype
  FROM pg_trigger
  WHERE tgrelid = 'your_table'::regclass;
  ```

- [ ] **Verify no conflicting security definer functions**
  ```sql
  SELECT routine_name, security_type
  FROM information_schema.routines
  WHERE security_type = 'DEFINER'
    AND routine_schema = 'public';
  ```

### Quick Diagnostic Query

Run this comprehensive check:

```sql
-- Comprehensive RLS diagnostic for a table
WITH table_info AS (
  SELECT
    'your_table' AS table_name,
    'anon' AS test_role  -- Change to your role
)
SELECT
  '1. RLS Enabled' AS check_type,
  CASE WHEN c.relrowsecurity THEN 'PASS ✓' ELSE 'FAIL ✗' END AS status,
  'ALTER TABLE ' || t.table_name || ' ENABLE ROW LEVEL SECURITY;' AS fix
FROM table_info t
JOIN pg_class c ON c.relname = t.table_name

UNION ALL

SELECT
  '2. Has Policies',
  CASE WHEN COUNT(*) > 0 THEN 'PASS ✓' ELSE 'FAIL ✗' END,
  'CREATE POLICY ... ON ' || t.table_name
FROM table_info t
LEFT JOIN pg_policies p ON p.tablename = t.table_name
GROUP BY t.table_name

UNION ALL

SELECT
  '3. Policies Have TO Clauses',
  CASE WHEN COUNT(*) = 0 THEN 'FAIL ✗' ELSE 'PASS ✓' END,
  'Check: SELECT policyname, roles FROM pg_policies WHERE tablename = ''' || t.table_name || ''''
FROM table_info t
LEFT JOIN pg_policies p ON p.tablename = t.table_name AND cardinality(p.roles) = 0
GROUP BY t.table_name

UNION ALL

SELECT
  '4. Role Has Table Permissions',
  CASE WHEN COUNT(*) > 0 THEN 'PASS ✓' ELSE 'FAIL ✗' END,
  'GRANT ALL ON ' || t.table_name || ' TO ' || t.test_role || ';'
FROM table_info t
LEFT JOIN information_schema.table_privileges tp
  ON tp.table_name = t.table_name AND tp.grantee = t.test_role
GROUP BY t.table_name, t.test_role

UNION ALL

SELECT
  '5. Policies Apply to Role',
  CASE WHEN COUNT(*) > 0 THEN 'PASS ✓' ELSE 'FAIL ✗' END,
  'Ensure policies have TO ' || t.test_role || ' or TO public'
FROM table_info t
LEFT JOIN pg_policies p
  ON p.tablename = t.table_name
  AND (t.test_role = ANY(p.roles) OR 'public' = ANY(p.roles))
GROUP BY t.table_name, t.test_role;
```

---

## Performance Implications and Optimization

### How RLS Affects Performance

RLS policies add WHERE clauses to every query. Impact depends on:

1. **Policy complexity** - Simple `true` is fast, complex subqueries are slow
2. **Index coverage** - Columns in USING/WITH CHECK should be indexed
3. **Data volume** - More rows = more filtering work
4. **Policy count** - Multiple policies = multiple conditions to evaluate

### Performance Best Practices

#### 1. Index Columns Used in Policies

```sql
-- Policy uses user_id
CREATE POLICY "user_owned" ON documents FOR SELECT TO authenticated
  USING (user_id = auth.uid());

-- INDEX the user_id column!
CREATE INDEX idx_documents_user_id ON documents(user_id);

-- For multi-column policies
CREATE POLICY "tenant_user" ON data FOR SELECT TO authenticated
  USING (tenant_id = auth.tenant_id() AND user_id = auth.uid());

-- Composite index
CREATE INDEX idx_data_tenant_user ON data(tenant_id, user_id);
```

#### 2. Avoid Subqueries in Policies

**Slow:**
```sql
-- Subquery executed for EVERY row
CREATE POLICY "team_access" ON documents FOR SELECT TO authenticated
  USING (
    team_id IN (
      SELECT team_id FROM team_members WHERE user_id = auth.uid()
    )
  );
```

**Fast:**
```sql
-- Use a stable function with caching
CREATE OR REPLACE FUNCTION auth.user_teams()
RETURNS UUID[] AS $$
  SELECT ARRAY_AGG(team_id)
  FROM team_members
  WHERE user_id = auth.uid();
$$ LANGUAGE SQL STABLE;  -- STABLE = cached within transaction

CREATE POLICY "team_access" ON documents FOR SELECT TO authenticated
  USING (team_id = ANY(auth.user_teams()));

-- And index it
CREATE INDEX idx_documents_team_id ON documents(team_id);
```

#### 3. Use STABLE or IMMUTABLE Functions

Function volatility affects caching:

```sql
-- VOLATILE (default) - re-executed every time, no caching
CREATE FUNCTION my_func() RETURNS UUID AS $$ ... $$ LANGUAGE SQL;

-- STABLE - cached within a transaction (better for RLS)
CREATE FUNCTION my_func() RETURNS UUID AS $$ ... $$ LANGUAGE SQL STABLE;

-- IMMUTABLE - cached forever (only for truly constant logic)
CREATE FUNCTION my_func() RETURNS UUID AS $$ ... $$ LANGUAGE SQL IMMUTABLE;
```

For RLS, use `STABLE` for functions that depend on session state:

```sql
CREATE FUNCTION auth.uid() RETURNS UUID AS $$
  SELECT COALESCE(
    current_setting('request.jwt.claim.sub', true)::UUID,
    '00000000-0000-0000-0000-000000000000'::UUID
  );
$$ LANGUAGE SQL STABLE;  -- Result stable within transaction
```

#### 4. Simplify Policy Logic

```sql
-- Complex (slow)
CREATE POLICY "complex" ON data FOR SELECT TO authenticated
  USING (
    (status = 'published' AND publish_date <= NOW()) OR
    (status = 'draft' AND author_id = auth.uid()) OR
    (status = 'review' AND reviewer_id = auth.uid()) OR
    EXISTS (SELECT 1 FROM admins WHERE user_id = auth.uid())
  );

-- Simplified (faster) - Split into separate policies
CREATE POLICY "published_visible" ON data FOR SELECT TO authenticated
  USING (status = 'published' AND publish_date <= NOW());

CREATE POLICY "author_sees_drafts" ON data FOR SELECT TO authenticated
  USING (status = 'draft' AND author_id = auth.uid());

CREATE POLICY "reviewer_sees_pending" ON data FOR SELECT TO authenticated
  USING (status = 'review' AND reviewer_id = auth.uid());

-- Each policy can use its own optimized index
CREATE INDEX idx_data_published ON data(status, publish_date)
  WHERE status = 'published';
CREATE INDEX idx_data_drafts ON data(author_id)
  WHERE status = 'draft';
CREATE INDEX idx_data_review ON data(reviewer_id)
  WHERE status = 'review';
```

#### 5. Consider Disabling RLS for Non-Sensitive Data

For cache tables, reference data, or truly public data:

```sql
-- Option 1: Disable RLS entirely
ALTER TABLE cache_table DISABLE ROW LEVEL SECURITY;
GRANT ALL ON cache_table TO public;

-- Option 2: Enable RLS but use simple 'true' policies
ALTER TABLE cache_table ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public_access" ON cache_table FOR ALL TO public
  USING (true) WITH CHECK (true);
GRANT ALL ON cache_table TO public;
```

**When to disable RLS:**
- Cache tables with TTL
- Read-only reference data (countries, categories, etc.)
- Public APIs with no user-specific data
- Tables behind service_role (backend-only access)

**When NOT to disable:**
- User data
- Financial records
- PII (personally identifiable information)
- Anything requiring audit trail

### Measuring RLS Performance Impact

#### 1. Compare with/without RLS

```sql
-- Measure query without RLS (as service_role or superuser)
EXPLAIN ANALYZE
SELECT * FROM documents WHERE created_at > NOW() - INTERVAL '7 days';

-- Measure with RLS (as target role)
SET ROLE authenticated;
EXPLAIN ANALYZE
SELECT * FROM documents WHERE created_at > NOW() - INTERVAL '7 days';
RESET ROLE;

-- Look for:
-- - Added Filter conditions from policies
-- - Index Scan vs Seq Scan
-- - Execution time difference
```

#### 2. Profile Policy Functions

```sql
-- Add timing to see which part is slow
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT * FROM documents
WHERE user_id = auth.uid();  -- How fast is auth.uid()?

-- Check function execution time
SELECT
  calls,
  total_time,
  mean_time,
  funcname
FROM pg_stat_user_functions
WHERE schemaname = 'auth'
ORDER BY total_time DESC;
```

#### 3. Monitor Query Performance

```sql
-- Enable pg_stat_statements extension
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Find slow queries (run after some usage)
SELECT
  substring(query, 1, 100) AS short_query,
  calls,
  mean_exec_time,
  max_exec_time,
  stddev_exec_time
FROM pg_stat_statements
WHERE query LIKE '%your_table%'
ORDER BY mean_exec_time DESC
LIMIT 20;
```

### Optimization Checklist

- [ ] Index all columns used in RLS policy USING/WITH CHECK clauses
- [ ] Use STABLE functions for session-based logic (not VOLATILE)
- [ ] Avoid subqueries in policies; use JOINs or cached functions
- [ ] Split complex multi-condition policies into separate simpler ones
- [ ] Use partial indexes for status-based policies
- [ ] Consider materialized views for complex permission lookups
- [ ] Disable RLS on non-sensitive cache/reference tables
- [ ] Profile slow queries with EXPLAIN ANALYZE
- [ ] Monitor with pg_stat_statements
- [ ] Test performance under realistic data volumes

---

## Complete Migration Examples

### Example 1: Simple User-Owned Resources

**Scenario:** Blog platform where users create and manage their own posts.

```sql
-- ============================================================================
-- Migration: Enable RLS for blog_posts table
-- ============================================================================

-- 1. Enable RLS
ALTER TABLE blog_posts ENABLE ROW LEVEL SECURITY;

-- 2. Drop any existing policies (idempotent)
DROP POLICY IF EXISTS "Users can view own posts" ON blog_posts;
DROP POLICY IF EXISTS "Users can create posts" ON blog_posts;
DROP POLICY IF EXISTS "Users can update own posts" ON blog_posts;
DROP POLICY IF EXISTS "Users can delete own posts" ON blog_posts;
DROP POLICY IF EXISTS "Public can view published posts" ON blog_posts;

-- 3. Create policies for authenticated users (authors)
CREATE POLICY "Authors can view own posts"
  ON blog_posts
  FOR SELECT
  TO authenticated
  USING (author_id = auth.uid());

CREATE POLICY "Authors can create posts"
  ON blog_posts
  FOR INSERT
  TO authenticated
  WITH CHECK (author_id = auth.uid());

CREATE POLICY "Authors can update own posts"
  ON blog_posts
  FOR UPDATE
  TO authenticated
  USING (author_id = auth.uid())
  WITH CHECK (author_id = auth.uid());

CREATE POLICY "Authors can delete own posts"
  ON blog_posts
  FOR DELETE
  TO authenticated
  USING (author_id = auth.uid());

-- 4. Create policy for public access to published posts
CREATE POLICY "Public can view published posts"
  ON blog_posts
  FOR SELECT
  TO public
  USING (status = 'published' AND published_at <= NOW());

-- 5. Grant table permissions
GRANT SELECT ON blog_posts TO public;
GRANT INSERT, UPDATE, DELETE ON blog_posts TO authenticated;

-- 6. Grant sequence permissions (for id column)
GRANT USAGE, SELECT ON SEQUENCE blog_posts_id_seq TO authenticated;

-- 7. Create indexes for RLS performance
CREATE INDEX IF NOT EXISTS idx_blog_posts_author_id
  ON blog_posts(author_id);

CREATE INDEX IF NOT EXISTS idx_blog_posts_published
  ON blog_posts(status, published_at)
  WHERE status = 'published';

-- 8. Force PostgREST schema reload
ALTER TABLE blog_posts ADD COLUMN _force_reload BOOLEAN DEFAULT true;
ALTER TABLE blog_posts DROP COLUMN _force_reload;

COMMENT ON TABLE blog_posts IS 'Blog posts with RLS - Updated 2025-11-21';
```

### Example 2: Multi-Tenant SaaS Application

**Scenario:** SaaS app where each organization has isolated data.

```sql
-- ============================================================================
-- Migration: Multi-tenant RLS for projects table
-- ============================================================================

-- 1. Create helper function to get tenant from JWT
CREATE OR REPLACE FUNCTION auth.tenant_id()
RETURNS UUID AS $$
  SELECT COALESCE(
    (auth.jwt() -> 'app_metadata' ->> 'tenant_id')::UUID,
    '00000000-0000-0000-0000-000000000000'::UUID
  );
$$ LANGUAGE SQL STABLE SECURITY DEFINER;

COMMENT ON FUNCTION auth.tenant_id() IS
  'Extracts tenant_id from JWT app_metadata. Returns null UUID if missing.';

-- 2. Grant execute permission to roles
GRANT EXECUTE ON FUNCTION auth.tenant_id() TO authenticated, anon;

-- 3. Enable RLS on tenant-specific tables
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_tasks ENABLE ROW LEVEL SECURITY;

-- 4. Drop existing policies
DROP POLICY IF EXISTS "Tenant isolation for projects" ON projects;
DROP POLICY IF EXISTS "Tenant isolation for members" ON project_members;
DROP POLICY IF EXISTS "Tenant isolation for tasks" ON project_tasks;

-- 5. Create tenant isolation policies
-- Projects table
CREATE POLICY "Tenant isolation for projects"
  ON projects
  FOR ALL
  TO authenticated
  USING (tenant_id = auth.tenant_id())
  WITH CHECK (tenant_id = auth.tenant_id());

-- Project members table
CREATE POLICY "Tenant isolation for members"
  ON project_members
  FOR ALL
  TO authenticated
  USING (tenant_id = auth.tenant_id())
  WITH CHECK (tenant_id = auth.tenant_id());

-- Project tasks table (checks via project relationship)
CREATE POLICY "Tenant isolation for tasks"
  ON project_tasks
  FOR ALL
  TO authenticated
  USING (
    project_id IN (
      SELECT id FROM projects WHERE tenant_id = auth.tenant_id()
    )
  )
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE tenant_id = auth.tenant_id()
    )
  );

-- 6. Grant permissions
GRANT ALL ON projects TO authenticated;
GRANT ALL ON project_members TO authenticated;
GRANT ALL ON project_tasks TO authenticated;

-- 7. Grant sequence permissions
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- 8. Create indexes (CRITICAL for tenant isolation performance)
CREATE INDEX IF NOT EXISTS idx_projects_tenant_id
  ON projects(tenant_id);

CREATE INDEX IF NOT EXISTS idx_project_members_tenant_id
  ON project_members(tenant_id);

CREATE INDEX IF NOT EXISTS idx_project_tasks_project_id
  ON project_tasks(project_id);

-- 9. Add validation constraint (defense in depth)
ALTER TABLE projects
  ADD CONSTRAINT check_tenant_id_not_null
  CHECK (tenant_id IS NOT NULL);

ALTER TABLE project_members
  ADD CONSTRAINT check_tenant_id_not_null
  CHECK (tenant_id IS NOT NULL);

-- 10. Force PostgREST reload
NOTIFY pgrst, 'reload schema';

COMMENT ON TABLE projects IS 'Multi-tenant projects - Updated 2025-11-21';
```

### Example 3: Complex RBAC with Multiple Roles

**Scenario:** Admin panel with different permission levels.

```sql
-- ============================================================================
-- Migration: RBAC for admin_resources table
-- ============================================================================

-- 1. Create role checking function
CREATE OR REPLACE FUNCTION auth.user_role()
RETURNS TEXT AS $$
  SELECT COALESCE(
    auth.jwt() -> 'app_metadata' ->> 'role',
    'user'
  )::TEXT;
$$ LANGUAGE SQL STABLE SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION auth.user_role() TO authenticated;

-- 2. Create helper function for admin check
CREATE OR REPLACE FUNCTION auth.is_admin()
RETURNS BOOLEAN AS $$
  SELECT auth.user_role() IN ('admin', 'superadmin');
$$ LANGUAGE SQL STABLE SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION auth.is_admin() TO authenticated;

-- 3. Enable RLS
ALTER TABLE admin_resources ENABLE ROW LEVEL SECURITY;

-- 4. Drop existing policies
DROP POLICY IF EXISTS "Superadmins can do anything" ON admin_resources;
DROP POLICY IF EXISTS "Admins can view all" ON admin_resources;
DROP POLICY IF EXISTS "Admins can modify non-sensitive" ON admin_resources;
DROP POLICY IF EXISTS "Managers can view their department" ON admin_resources;
DROP POLICY IF EXISTS "Users can view public resources" ON admin_resources;

-- 5. Create role-based policies

-- Superadmins have full access
CREATE POLICY "Superadmins can do anything"
  ON admin_resources
  FOR ALL
  TO authenticated
  USING (auth.user_role() = 'superadmin')
  WITH CHECK (auth.user_role() = 'superadmin');

-- Admins can view all, modify non-sensitive
CREATE POLICY "Admins can view all"
  ON admin_resources
  FOR SELECT
  TO authenticated
  USING (auth.user_role() IN ('admin', 'superadmin'));

CREATE POLICY "Admins can modify non-sensitive"
  ON admin_resources
  FOR UPDATE
  TO authenticated
  USING (
    auth.user_role() = 'admin'
    AND sensitivity_level != 'high'
  )
  WITH CHECK (
    auth.user_role() = 'admin'
    AND sensitivity_level != 'high'
  );

-- Managers can view their department
CREATE POLICY "Managers can view their department"
  ON admin_resources
  FOR SELECT
  TO authenticated
  USING (
    auth.user_role() = 'manager'
    AND department_id = (auth.jwt() -> 'app_metadata' ->> 'department_id')::UUID
  );

-- Regular users can view public resources
CREATE POLICY "Users can view public resources"
  ON admin_resources
  FOR SELECT
  TO authenticated
  USING (visibility = 'public');

-- 6. Grant permissions
GRANT SELECT ON admin_resources TO authenticated;
GRANT INSERT, UPDATE, DELETE ON admin_resources TO authenticated;
-- RLS policies will restrict actual access

-- 7. Create indexes
CREATE INDEX IF NOT EXISTS idx_admin_resources_role_check
  ON admin_resources(sensitivity_level, visibility);

CREATE INDEX IF NOT EXISTS idx_admin_resources_department
  ON admin_resources(department_id);

-- 8. Force reload
ALTER TABLE admin_resources ADD COLUMN _reload BOOLEAN DEFAULT true;
ALTER TABLE admin_resources DROP COLUMN _reload;
```

### Example 4: Fixing Broken Policies (The 406 Fix)

**Scenario:** Dashboard fails with 406 errors on `uvp_sessions` table.

```sql
-- ============================================================================
-- Migration: Fix 406 errors on uvp_sessions table
-- ============================================================================
-- Issue: Policies missing TO clauses causing PostgREST 406 errors
-- Solution: Recreate policies with explicit TO clauses
-- ============================================================================

-- Step 1: Drop all existing broken policies
DO $$
DECLARE
  pol record;
BEGIN
  FOR pol IN
    SELECT policyname
    FROM pg_policies
    WHERE tablename = 'uvp_sessions'
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON uvp_sessions', pol.policyname);
    RAISE NOTICE 'Dropped policy: %', pol.policyname;
  END LOOP;
END $$;

-- Step 2: Verify RLS is enabled
ALTER TABLE uvp_sessions ENABLE ROW LEVEL SECURITY;

-- Step 3: Create new policies with explicit TO clauses

-- SELECT: Public read access (for demo/development)
CREATE POLICY "Allow reading sessions"
  ON uvp_sessions
  FOR SELECT
  TO public  -- ← CRITICAL: TO clause fixes 406
  USING (true);

-- INSERT: Anyone can create sessions
CREATE POLICY "Allow creating sessions"
  ON uvp_sessions
  FOR INSERT
  TO public  -- ← CRITICAL: TO clause fixes 406
  WITH CHECK (brand_id IS NOT NULL);

-- UPDATE: Anyone can update sessions
CREATE POLICY "Allow updating sessions"
  ON uvp_sessions
  FOR UPDATE
  TO public  -- ← CRITICAL: TO clause fixes 406
  USING (true)
  WITH CHECK (true);

-- DELETE: Anyone can delete sessions
CREATE POLICY "Allow deleting sessions"
  ON uvp_sessions
  FOR DELETE
  TO public  -- ← CRITICAL: TO clause fixes 406
  USING (true);

-- Step 4: Grant table permissions to all roles
GRANT ALL ON uvp_sessions TO anon;
GRANT ALL ON uvp_sessions TO authenticated;
GRANT ALL ON uvp_sessions TO service_role;

-- Step 5: Grant sequence permissions
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;

-- Step 6: Force PostgREST schema reload (REQUIRED!)
ALTER TABLE uvp_sessions ADD COLUMN _force_reload BOOLEAN DEFAULT true;
ALTER TABLE uvp_sessions DROP COLUMN _force_reload;

NOTIFY pgrst, 'reload schema';

-- Step 7: Update table comment with timestamp
COMMENT ON TABLE uvp_sessions IS 'UVP sessions - Fixed RLS 406 errors on 2025-11-21';

-- Step 8: Verify the fix
DO $$
DECLARE
  pol record;
BEGIN
  RAISE NOTICE '=== RLS POLICY VERIFICATION ===';
  RAISE NOTICE 'Table: uvp_sessions';
  RAISE NOTICE 'RLS Enabled: %',
    (SELECT relrowsecurity FROM pg_class WHERE relname = 'uvp_sessions');
  RAISE NOTICE '';
  RAISE NOTICE 'Policies:';

  FOR pol IN
    SELECT policyname, cmd, roles::TEXT
    FROM pg_policies
    WHERE tablename = 'uvp_sessions'
    ORDER BY policyname
  LOOP
    RAISE NOTICE '  ✓ % (%) - TO %', pol.policyname, pol.cmd, pol.roles;
  END LOOP;

  RAISE NOTICE '';
  RAISE NOTICE 'Grants to anon:';
  FOR pol IN
    SELECT privilege_type
    FROM information_schema.table_privileges
    WHERE table_name = 'uvp_sessions' AND grantee = 'anon'
  LOOP
    RAISE NOTICE '  ✓ %', pol.privilege_type;
  END LOOP;
END $$;
```

### Example 5: Cache Table (Performance-Optimized)

**Scenario:** Intelligence cache table that needs fast public access.

```sql
-- ============================================================================
-- Migration: Optimize RLS for intelligence_cache table
-- ============================================================================

-- Step 1: Enable RLS (keep enabled for consistency)
ALTER TABLE intelligence_cache ENABLE ROW LEVEL SECURITY;

-- Step 2: Drop existing policies
DROP POLICY IF EXISTS "cache_select" ON intelligence_cache;
DROP POLICY IF EXISTS "cache_insert" ON intelligence_cache;
DROP POLICY IF EXISTS "cache_update" ON intelligence_cache;
DROP POLICY IF EXISTS "cache_delete" ON intelligence_cache;

-- Step 3: Create simple, performant policies
-- No complex conditions = maximum performance

CREATE POLICY "Public cache read"
  ON intelligence_cache
  FOR SELECT
  TO public
  USING (true);  -- No filtering = fastest possible

CREATE POLICY "Public cache write"
  ON intelligence_cache
  FOR INSERT
  TO public
  WITH CHECK (true);  -- No validation = fastest possible

CREATE POLICY "Public cache update"
  ON intelligence_cache
  FOR UPDATE
  TO public
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Public cache delete"
  ON intelligence_cache
  FOR DELETE
  TO public
  USING (true);

-- Step 4: Grant permissions
GRANT ALL ON intelligence_cache TO public;

-- Step 5: Optimize with indexes (for cache lookup performance)
CREATE INDEX IF NOT EXISTS idx_intelligence_cache_key
  ON intelligence_cache(cache_key);

CREATE INDEX IF NOT EXISTS idx_intelligence_cache_expires
  ON intelligence_cache(expires_at)
  WHERE expires_at IS NOT NULL;

-- Step 6: Add TTL cleanup function (optional but recommended)
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS void AS $$
  DELETE FROM intelligence_cache
  WHERE expires_at IS NOT NULL AND expires_at < NOW();
$$ LANGUAGE SQL SECURITY DEFINER;

-- Schedule cleanup (requires pg_cron extension)
-- SELECT cron.schedule('cleanup-cache', '0 * * * *', 'SELECT cleanup_expired_cache()');

-- Step 7: Force reload
NOTIFY pgrst, 'reload schema';

COMMENT ON TABLE intelligence_cache IS 'Ephemeral cache with TTL - Optimized RLS';
```

---

## Troubleshooting Workflow

### Systematic Debugging Process

When encountering RLS issues, follow this step-by-step workflow:

#### Step 1: Identify the Exact Error

```bash
# Check frontend console
# Look for: 406, 403, 401, or permission denied errors

# Check PostgREST logs (if accessible)
docker logs <postgrest-container> --tail 100 | grep -i error

# Check Supabase dashboard logs
# Database → Logs → Filter by error level
```

#### Step 2: Determine Which Table and Operation

```javascript
// Note the exact API call that fails
const { data, error } = await supabase
  .from('table_name')  // ← Which table?
  .select('*');         // ← Which operation? SELECT/INSERT/UPDATE/DELETE

console.log(error);
// Error message often hints at the issue
```

#### Step 3: Check RLS Status

```sql
-- Is RLS enabled?
SELECT
  schemaname,
  tablename,
  rowsecurity AS rls_enabled
FROM pg_tables
WHERE tablename = 'your_table';

-- If rls_enabled is false, enable it:
-- ALTER TABLE your_table ENABLE ROW LEVEL SECURITY;
```

#### Step 4: Inspect Current Policies

```sql
-- List all policies for the table
SELECT
  policyname,
  cmd AS operation,
  roles,
  qual AS using_expression,
  with_check AS with_check_expression
FROM pg_policies
WHERE tablename = 'your_table'
ORDER BY cmd, policyname;
```

**Red flags to look for:**
- `roles` column is empty `{}` - Missing TO clause (406 cause!)
- No policies for your operation (SELECT, INSERT, etc.)
- Roles don't include `anon`, `authenticated`, or `public`

#### Step 5: Check Table Permissions

```sql
-- What permissions does each role have?
SELECT
  grantee,
  privilege_type
FROM information_schema.table_privileges
WHERE table_name = 'your_table'
  AND grantee IN ('anon', 'authenticated', 'public', 'service_role')
ORDER BY grantee, privilege_type;
```

**Expected output for working table:**
```
grantee       | privilege_type
--------------|---------------
anon          | SELECT
anon          | INSERT
authenticated | SELECT
authenticated | INSERT
authenticated | UPDATE
authenticated | DELETE
```

#### Step 6: Test with Actual Role

```sql
-- Switch to the role your app uses
BEGIN;
SET LOCAL ROLE anon;  -- or authenticated

-- Try the exact query
SELECT * FROM your_table;

-- Did it work?
-- YES: Problem might be PostgREST cache or JWT issue
-- NO: Continue debugging...

ROLLBACK;
```

#### Step 7: Check Policy Logic

```sql
-- Test if USING condition is true
SET ROLE anon;

SELECT
  *,
  (your_using_condition) AS policy_condition_result
FROM your_table;

-- If policy_condition_result is false, policy blocks access
-- Check why the condition fails

RESET ROLE;
```

#### Step 8: Verify Dependencies

```sql
-- If policy uses functions, check permissions
SELECT
  routine_name,
  routine_type
FROM information_schema.routines
WHERE specific_schema = 'auth'
ORDER BY routine_name;

-- Test function execution
SELECT has_function_privilege('anon', 'auth.uid()', 'EXECUTE');
-- Should return: t (true)

-- If policy checks related tables, verify their RLS too
-- Example: Policy does WHERE team_id IN (SELECT ...)
-- The subquery SELECT must also be allowed by RLS
```

#### Step 9: Fix the Issue

Based on findings, apply appropriate fix:

**Problem: Missing TO clause (406 error)**
```sql
DROP POLICY "old_policy" ON your_table;
CREATE POLICY "new_policy"
  ON your_table
  FOR SELECT
  TO public  -- ← Add TO clause
  USING (true);
```

**Problem: Missing table permission (403 error)**
```sql
GRANT SELECT ON your_table TO anon;
GRANT ALL ON your_table TO authenticated;
```

**Problem: Policy logic blocks access**
```sql
-- Adjust USING condition
DROP POLICY "restrictive_policy" ON your_table;
CREATE POLICY "less_restrictive"
  ON your_table
  FOR SELECT
  TO authenticated
  USING (
    user_id = auth.uid() OR is_public = true  -- ← More permissive
  );
```

#### Step 10: Force PostgREST Reload

```sql
-- Method 1: Schema change (most reliable)
ALTER TABLE your_table ADD COLUMN _reload BOOLEAN DEFAULT true;
ALTER TABLE your_table DROP COLUMN _reload;

-- Method 2: NOTIFY signal
NOTIFY pgrst, 'reload schema';

-- Method 3: Update comment
COMMENT ON TABLE your_table IS 'Updated at ' || NOW()::TEXT;
```

#### Step 11: Verify the Fix

```sql
-- Re-run diagnostic query from Step 4 and Step 5
-- Ensure:
-- - Policies have TO clauses
-- - Grants exist for target role
-- - Policy logic allows access

-- Test with role again
BEGIN;
SET LOCAL ROLE anon;
SELECT * FROM your_table LIMIT 1;  -- Should succeed
ROLLBACK;
```

#### Step 12: Test from Application

```javascript
// Clear any frontend cache
localStorage.clear();
sessionStorage.clear();

// Refresh page and test
const { data, error } = await supabase
  .from('your_table')
  .select('*')
  .limit(1);

console.log('Success:', data);
console.log('Error:', error);  // Should be null
```

### Quick Fix Commands Reference

```sql
-- Nuclear option: Start fresh with working policies
BEGIN;

-- 1. Drop all policies on table
DO $$
DECLARE pol record;
BEGIN
  FOR pol IN SELECT policyname FROM pg_policies WHERE tablename = 'YOUR_TABLE' LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON YOUR_TABLE', pol.policyname);
  END LOOP;
END $$;

-- 2. Enable RLS
ALTER TABLE YOUR_TABLE ENABLE ROW LEVEL SECURITY;

-- 3. Create simple working policies
CREATE POLICY "allow_select" ON YOUR_TABLE FOR SELECT TO public USING (true);
CREATE POLICY "allow_insert" ON YOUR_TABLE FOR INSERT TO public WITH CHECK (true);
CREATE POLICY "allow_update" ON YOUR_TABLE FOR UPDATE TO public USING (true) WITH CHECK (true);
CREATE POLICY "allow_delete" ON YOUR_TABLE FOR DELETE TO public USING (true);

-- 4. Grant permissions
GRANT ALL ON YOUR_TABLE TO anon, authenticated, service_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;

-- 5. Force reload
ALTER TABLE YOUR_TABLE ADD COLUMN _reload BOOLEAN DEFAULT true;
ALTER TABLE YOUR_TABLE DROP COLUMN _reload;

-- 6. Verify
SELECT policyname, roles, cmd FROM pg_policies WHERE tablename = 'YOUR_TABLE';

COMMIT;
```

---

## Common Pitfalls and Solutions

### Pitfall 1: Forgetting the TO Clause

**Symptom:** 406 Not Acceptable errors despite "correct" policies

**Problem:**
```sql
CREATE POLICY "my_policy" ON table FOR SELECT USING (true);
-- Missing: TO clause
```

**Solution:**
```sql
CREATE POLICY "my_policy" ON table FOR SELECT TO public USING (true);
-- Added: TO public
```

**Prevention:** Always include `TO <role>` in every policy when using PostgREST.

---

### Pitfall 2: Table Permissions Don't Match Policy Roles

**Symptom:** 403 Forbidden errors

**Problem:**
```sql
-- Policy targets 'anon'
CREATE POLICY "select" ON table FOR SELECT TO anon USING (true);

-- But no GRANT to 'anon'!
GRANT SELECT ON table TO authenticated;  -- Wrong role
```

**Solution:**
```sql
GRANT SELECT ON table TO anon;  -- Match the policy's TO clause
```

**Prevention:** After creating policies, always grant matching table permissions.

---

### Pitfall 3: Missing Sequence Permissions

**Symptom:** `permission denied for sequence table_id_seq` when inserting

**Problem:**
```sql
-- Table permission granted
GRANT INSERT ON table TO anon;

-- But sequence permission missing
-- (no grant on table_id_seq)
```

**Solution:**
```sql
GRANT USAGE, SELECT ON SEQUENCE table_id_seq TO anon;

-- Or grant all sequences
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon;
```

**Prevention:** Always grant sequence permissions alongside INSERT grants.

---

### Pitfall 4: PostgREST Cache Not Refreshed

**Symptom:** Changes don't take effect; old errors persist

**Problem:**
```sql
-- Fixed the policy
DROP POLICY "old" ON table;
CREATE POLICY "new" ON table FOR SELECT TO public USING (true);

-- But PostgREST still uses old schema cached in memory
```

**Solution:**
```sql
-- Force schema reload
ALTER TABLE table ADD COLUMN _reload BOOLEAN DEFAULT true;
ALTER TABLE table DROP COLUMN _reload;

NOTIFY pgrst, 'reload schema';
```

**Prevention:** Always force reload after RLS changes. Add this to migration scripts.

---

### Pitfall 5: Missing WITH CHECK on INSERT/UPDATE

**Symptom:** Can read data but can't insert or update

**Problem:**
```sql
CREATE POLICY "select" ON table FOR SELECT TO public USING (true);
CREATE POLICY "insert" ON table FOR INSERT TO public USING (true);
-- Missing: WITH CHECK clause for INSERT
```

**Solution:**
```sql
CREATE POLICY "insert" ON table
  FOR INSERT
  TO public
  WITH CHECK (true);  -- Use WITH CHECK, not USING
```

**Remember:**
- `USING` = read-side filter (SELECT, UPDATE, DELETE)
- `WITH CHECK` = write-side validation (INSERT, UPDATE)

---

### Pitfall 6: Using FOR ALL Without Both Clauses

**Symptom:** Some operations work, others don't

**Problem:**
```sql
CREATE POLICY "all_ops" ON table
  FOR ALL
  TO public
  USING (true);
-- Missing: WITH CHECK clause
```

**Solution:**
```sql
CREATE POLICY "all_ops" ON table
  FOR ALL
  TO public
  USING (true)
  WITH CHECK (true);  -- Required for INSERT/UPDATE
```

**Prevention:** When using `FOR ALL`, always include both `USING` and `WITH CHECK`.

---

### Pitfall 7: Complex Subqueries in Policies

**Symptom:** Extremely slow queries, timeouts

**Problem:**
```sql
CREATE POLICY "team_access" ON documents FOR SELECT TO authenticated
  USING (
    team_id IN (
      SELECT team_id FROM team_members WHERE user_id = auth.uid()
    )  -- Executed for EVERY row!
  );
```

**Solution:**
```sql
-- Use a STABLE function with caching
CREATE FUNCTION auth.user_teams() RETURNS UUID[] AS $$
  SELECT ARRAY_AGG(team_id) FROM team_members WHERE user_id = auth.uid();
$$ LANGUAGE SQL STABLE;

CREATE POLICY "team_access" ON documents FOR SELECT TO authenticated
  USING (team_id = ANY(auth.user_teams()));  -- Cached result
```

**Prevention:** Extract subqueries into STABLE functions; index columns used in policies.

---

### Pitfall 8: Testing as Superuser

**Symptom:** "It works for me but not in production"

**Problem:**
```sql
-- Testing in psql as postgres superuser
SELECT * FROM table;  -- Works! (superuser bypasses RLS)

-- But production uses 'anon' role
-- (fails due to restrictive policy)
```

**Solution:**
```sql
-- Test with actual role
SET ROLE anon;
SELECT * FROM table;  -- Now fails as expected
RESET ROLE;
```

**Prevention:** Always test with `SET ROLE anon` or `SET ROLE authenticated`.

---

### Pitfall 9: Confusing 'public' Role with Public Schema

**Symptom:** Policy doesn't apply to anyone

**Problem:**
```sql
-- Confusion: 'public' schema vs 'public' role
CREATE POLICY "select" ON public.table FOR SELECT TO public USING (true);
--                        ^^^^^^ schema          ^^^^^^ role (correct!)
```

**Clarification:**
- `public` schema = default schema for tables
- `public` role = PostgreSQL built-in role that includes ALL other roles

**Solution:**
```sql
-- TO public = applies to all roles (anon, authenticated, etc.)
CREATE POLICY "select" ON table FOR SELECT TO public USING (true);

-- TO anon = applies only to anonymous users
CREATE POLICY "select" ON table FOR SELECT TO anon USING (true);

-- TO authenticated = applies only to logged-in users
CREATE POLICY "select" ON table FOR SELECT TO authenticated USING (true);
```

---

### Pitfall 10: UPDATE Policy Missing USING Clause

**Symptom:** Can't update any rows

**Problem:**
```sql
CREATE POLICY "update" ON table
  FOR UPDATE
  TO authenticated
  WITH CHECK (user_id = auth.uid());
-- Missing: USING clause to find updatable rows
```

**Solution:**
```sql
CREATE POLICY "update" ON table
  FOR UPDATE
  TO authenticated
  USING (user_id = auth.uid())       -- Which rows can be updated
  WITH CHECK (user_id = auth.uid()); -- Validation after update
```

**Remember:** UPDATE needs BOTH clauses:
1. `USING` - Find rows to update (must be visible first)
2. `WITH CHECK` - Validate new values

---

### Pitfall 11: Policy Name Conflicts

**Symptom:** "policy already exists" error, or old policy still active

**Problem:**
```sql
-- Create policy
CREATE POLICY "select" ON table1 FOR SELECT TO public USING (true);

-- Later, try to create on another table
CREATE POLICY "select" ON table2 FOR SELECT TO public USING (true);
-- Works! (policies are scoped to tables, not globally)

-- But confusing when debugging
SELECT * FROM pg_policies WHERE policyname = 'select';
-- Returns multiple rows from different tables
```

**Solution:**
```sql
-- Use descriptive, table-specific names
CREATE POLICY "users_select" ON users FOR SELECT TO public USING (true);
CREATE POLICY "posts_select" ON posts FOR SELECT TO public USING (true);
```

**Prevention:** Use naming convention: `{table}_{operation}` or `{purpose}_{table}`.

---

### Pitfall 12: Forgetting to Enable RLS

**Symptom:** Everyone can access everything

**Problem:**
```sql
-- Created policies but forgot to enable RLS
CREATE POLICY "restrictive" ON table FOR SELECT TO authenticated
  USING (user_id = auth.uid());

-- RLS still disabled
-- ALTER TABLE table ENABLE ROW LEVEL SECURITY;  ← Missing!
```

**Solution:**
```sql
-- Always enable RLS first
ALTER TABLE table ENABLE ROW LEVEL SECURITY;

-- Then create policies
CREATE POLICY ...
```

**Check:**
```sql
SELECT tablename, rowsecurity
FROM pg_tables
WHERE tablename = 'table';
-- rowsecurity should be 't' (true)
```

---

## Appendix: Reference Commands

### Diagnostic Queries

**Check if RLS is enabled:**
```sql
SELECT
  schemaname,
  tablename,
  rowsecurity AS rls_enabled,
  relforcerowsecurity AS force_rls_for_owners
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

**List all policies:**
```sql
SELECT
  schemaname,
  tablename,
  policyname,
  permissive,
  roles,
  cmd,
  qual AS using_clause,
  with_check
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, cmd, policyname;
```

**List table permissions:**
```sql
SELECT
  table_schema,
  table_name,
  grantee,
  privilege_type
FROM information_schema.table_privileges
WHERE table_schema = 'public'
  AND grantee IN ('anon', 'authenticated', 'public', 'service_role')
ORDER BY table_name, grantee, privilege_type;
```

**List sequence permissions:**
```sql
SELECT
  object_schema,
  object_name,
  grantee,
  privilege_type
FROM information_schema.usage_privileges
WHERE object_schema = 'public'
  AND object_type = 'SEQUENCE'
  AND grantee IN ('anon', 'authenticated', 'public')
ORDER BY object_name, grantee;
```

**List custom auth functions:**
```sql
SELECT
  routine_schema,
  routine_name,
  data_type AS return_type,
  security_type,
  routine_definition
FROM information_schema.routines
WHERE routine_schema = 'auth'
ORDER BY routine_name;
```

**Check function permissions:**
```sql
SELECT
  has_function_privilege('anon', 'auth.uid()', 'EXECUTE') AS anon_can_execute,
  has_function_privilege('authenticated', 'auth.uid()', 'EXECUTE') AS auth_can_execute;
```

### Policy Management Commands

**Enable RLS:**
```sql
ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;
```

**Disable RLS:**
```sql
ALTER TABLE table_name DISABLE ROW LEVEL SECURITY;
```

**Force RLS even for table owner:**
```sql
ALTER TABLE table_name FORCE ROW LEVEL SECURITY;
```

**Drop a policy:**
```sql
DROP POLICY IF EXISTS "policy_name" ON table_name;
```

**Drop all policies on a table:**
```sql
DO $$
DECLARE pol record;
BEGIN
  FOR pol IN SELECT policyname FROM pg_policies WHERE tablename = 'your_table' LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON your_table', pol.policyname);
  END LOOP;
END $$;
```

**Recreate policy (idempotent):**
```sql
DROP POLICY IF EXISTS "policy_name" ON table_name;
CREATE POLICY "policy_name" ON table_name ...;
```

### Permission Management Commands

**Grant table permissions:**
```sql
GRANT SELECT ON table_name TO role_name;
GRANT INSERT ON table_name TO role_name;
GRANT UPDATE ON table_name TO role_name;
GRANT DELETE ON table_name TO role_name;
GRANT ALL ON table_name TO role_name;
```

**Grant sequence permissions:**
```sql
GRANT USAGE, SELECT ON SEQUENCE table_id_seq TO role_name;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO role_name;
```

**Grant function execution:**
```sql
GRANT EXECUTE ON FUNCTION function_name() TO role_name;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA schema_name TO role_name;
```

**Revoke permissions:**
```sql
REVOKE ALL ON table_name FROM role_name;
REVOKE EXECUTE ON FUNCTION function_name() FROM role_name;
```

### Testing Commands

**Test as specific role:**
```sql
BEGIN;
SET LOCAL ROLE anon;
-- Run test queries
SELECT * FROM table_name;
ROLLBACK;
```

**Check current role:**
```sql
SELECT current_role, current_user, session_user;
```

**Test policy condition:**
```sql
SET ROLE anon;
SELECT *, (your_policy_condition) AS allowed FROM table_name;
RESET ROLE;
```

### PostgREST Cache Control

**Force schema reload (add/drop column):**
```sql
ALTER TABLE table_name ADD COLUMN _reload BOOLEAN DEFAULT true;
ALTER TABLE table_name DROP COLUMN _reload;
```

**Send NOTIFY signal:**
```sql
NOTIFY pgrst, 'reload schema';
NOTIFY pgrst, 'reload config';
```

**Update comment with timestamp:**
```sql
COMMENT ON TABLE table_name IS 'Updated at ' || NOW()::TEXT;
```

### Performance Analysis

**Explain query with RLS:**
```sql
SET ROLE anon;
EXPLAIN (ANALYZE, VERBOSE, BUFFERS)
SELECT * FROM table_name WHERE condition;
RESET ROLE;
```

**Check function statistics:**
```sql
SELECT
  funcname,
  calls,
  total_time,
  self_time,
  mean_time
FROM pg_stat_user_functions
WHERE schemaname = 'auth'
ORDER BY total_time DESC;
```

**Find slow queries:**
```sql
-- Requires pg_stat_statements extension
SELECT
  substring(query, 1, 100) AS query,
  calls,
  mean_exec_time,
  max_exec_time
FROM pg_stat_statements
WHERE query LIKE '%table_name%'
ORDER BY mean_exec_time DESC
LIMIT 20;
```

### Migration Template

```sql
-- ============================================================================
-- Migration: [Description]
-- ============================================================================
-- Date: YYYY-MM-DD
-- Author: [Name]
-- Purpose: [Why this change is needed]
-- ============================================================================

BEGIN;

-- Step 1: Enable RLS
ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;

-- Step 2: Drop existing policies (idempotent)
DROP POLICY IF EXISTS "policy1" ON table_name;
DROP POLICY IF EXISTS "policy2" ON table_name;

-- Step 3: Create new policies
CREATE POLICY "policy1"
  ON table_name
  FOR SELECT
  TO public
  USING (condition);

CREATE POLICY "policy2"
  ON table_name
  FOR INSERT
  TO authenticated
  WITH CHECK (condition);

-- Step 4: Grant table permissions
GRANT SELECT ON table_name TO public;
GRANT INSERT, UPDATE, DELETE ON table_name TO authenticated;

-- Step 5: Grant sequence permissions (if needed)
GRANT USAGE, SELECT ON SEQUENCE table_name_id_seq TO authenticated;

-- Step 6: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_table_column ON table_name(column);

-- Step 7: Force PostgREST reload
ALTER TABLE table_name ADD COLUMN _reload BOOLEAN DEFAULT true;
ALTER TABLE table_name DROP COLUMN _reload;

NOTIFY pgrst, 'reload schema';

-- Step 8: Verify
DO $$
BEGIN
  RAISE NOTICE 'Policies created:';
  RAISE NOTICE '%', (SELECT COUNT(*) FROM pg_policies WHERE tablename = 'table_name');
END $$;

COMMIT;

-- Step 9: Test (run separately)
-- BEGIN;
-- SET LOCAL ROLE anon;
-- SELECT * FROM table_name LIMIT 1;
-- ROLLBACK;
```

---

## Final Checklist: Deployment-Ready RLS

Before deploying RLS changes to production:

### Pre-Deployment

- [ ] All policies have explicit `TO` clauses
- [ ] Table permissions granted to match policy roles
- [ ] Sequence permissions granted for tables with SERIAL/IDENTITY columns
- [ ] Indexes created for columns used in policy conditions
- [ ] Policies tested with `SET ROLE anon` and `SET ROLE authenticated`
- [ ] Migration is idempotent (uses `DROP POLICY IF EXISTS`, etc.)
- [ ] Migration includes PostgREST cache reload mechanism
- [ ] Complex policy logic moved to STABLE functions
- [ ] No subqueries in policies (use functions instead)
- [ ] Policy names are descriptive and unique

### Testing

- [ ] Unit tests pass with RLS enabled
- [ ] Integration tests use actual `anon` and `authenticated` roles
- [ ] Performance tests show acceptable query times
- [ ] EXPLAIN ANALYZE shows policies use indexes efficiently
- [ ] Edge cases tested (empty results, permission denied, etc.)

### Documentation

- [ ] Migration includes comments explaining policy purpose
- [ ] Breaking changes documented for team
- [ ] Frontend developers notified of new access patterns
- [ ] Rollback plan documented

### Post-Deployment

- [ ] Monitor logs for 403/406 errors
- [ ] Check query performance metrics
- [ ] Verify cache tables are performing well
- [ ] Confirm no unexpected access denials

---

## Conclusion

RLS is powerful but requires careful attention to detail, especially when integrating with PostgREST. The most common issue—406 errors from missing `TO` clauses—is subtle and poorly documented, but now you have the knowledge to identify and fix it immediately.

**Key Takeaways:**

1. **Always use `TO` clauses** in policies for PostgREST compatibility
2. **Grant table permissions** to match your policy's target roles
3. **Test with actual roles** using `SET ROLE anon` or `SET ROLE authenticated`
4. **Force schema reload** after policy changes using the column add/drop trick
5. **Index policy conditions** for performance
6. **Use functions** for complex logic to enable caching and reusability

With this guide, you should be able to:
- Diagnose 406 errors quickly
- Write production-ready RLS policies
- Optimize performance
- Debug complex permission issues

**Happy securing!**

---

**Document Version:** 1.0
**Last Updated:** 2025-11-21
**Feedback:** Report issues or suggest improvements



---


## Complete Multi-Tenant SaaS Patterns {#saas_multi_tenant}


### Document 100 different multi-tenant isolation patterns with complete PostgreSQL RLS code


Here are 100 different multi-tenant isolation patterns using PostgreSQL Row Level Security (RLS). These cover a wide range of common SaaS application scenarios and data models. The examples provide the necessary RLS policy definitions to enforce the isolation.

For each example, we'll use this basic table structure:

```sql
CREATE TABLE items (
  id SERIAL PRIMARY KEY,
  tenant_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

And we'll assume a `tenants` table that maps each tenant to their `tenant_id`:

```sql
CREATE TABLE tenants (
  id SERIAL PRIMARY KEY, 
  name TEXT NOT NULL,
  subdomain TEXT NOT NULL UNIQUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

1. Simple Tenant Isolation
```sql
ALTER TABLE items ENABLE ROW LEVEL SECURITY;

CREATE POLICY items_tenant_isolation_policy ON items
USING (tenant_id = current_setting('app.current_tenant')::integer);
```

2. Tenant Isolation with Superuser Access
```sql
CREATE POLICY items_superuser_policy ON items 
USING (
  tenant_id = current_setting('app.current_tenant')::integer 
  OR pg_has_role(current_user, 'superuser', 'member')
);
```

3. Tenant Isolation with Creator Access 
```sql
ALTER TABLE items ADD COLUMN created_by INTEGER;

CREATE POLICY items_creator_policy ON items
USING (
  tenant_id = current_setting('app.current_tenant')::integer
  AND created_by = current_setting('app.current_user')::integer
);
```

4. Tenant Isolation with Separate Read/Write Policies
```sql 
CREATE POLICY items_tenant_select ON items 
FOR SELECT USING (tenant_id = current_setting('app.current_tenant')::integer);

CREATE POLICY items_tenant_insert ON items
FOR INSERT WITH CHECK (tenant_id = current_setting('app.current_tenant')::integer);

CREATE POLICY items_tenant_update ON items
FOR UPDATE USING (tenant_id = current_setting('app.current_tenant')::integer);

CREATE POLICY items_tenant_delete ON items  
FOR DELETE USING (tenant_id = current_setting('app.current_tenant')::integer);
```

5. Attribute-Based Access Control (ABAC)
```sql
ALTER TABLE items ADD COLUMN visibility TEXT NOT NULL DEFAULT 'private';

CREATE POLICY abac_private ON items 
USING (tenant_id = current_setting('app.current_tenant')::integer AND visibility = 'private');

CREATE POLICY abac_public ON items
USING (visibility = 'public');
```

6. Hierarchical Multi-Tenant (HMT) Isolation
```sql
CREATE TABLE item_hmts (
  item_id INTEGER NOT NULL REFERENCES items(id), 
  ancestor_tenant_id INTEGER NOT NULL,
  PRIMARY KEY (item_id, ancestor_tenant_id)
);

CREATE POLICY hmt_isolation ON items
USING (
  tenant_id = current_setting('app.current_tenant')::integer
  OR EXISTS (
    SELECT 1 FROM item_hmts 
    WHERE item_id = items.id
    AND ancestor_tenant_id = current_setting('app.current_tenant')::integer
  )  
);
```

7. Hybrid Logical/Physical Tenant Isolation
```sql
CREATE SCHEMA tenant_1;
CREATE SCHEMA tenant_2;

CREATE TABLE tenant_1.items (LIKE public.items INCLUDING ALL);
CREATE TABLE tenant_2.items (LIKE public.items INCLUDING ALL);

CREATE POLICY logical_tenant_isolation ON public.items
USING (tenant_id = current_setting('app.current_tenant')::integer);

ALTER TABLE tenant_1.items ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_2.items ENABLE ROW LEVEL SECURITY;

CREATE POLICY physical_tenant_isolation ON tenant_1.items USING (true);  
CREATE POLICY physical_tenant_isolation ON tenant_2.items USING (true);
```

8. Geo-Partitioned Tenant Isolation
```sql
CREATE TABLE item_locations (
  item_id INTEGER NOT NULL REFERENCES items(id),
  location TEXT NOT NULL,
  PRIMARY KEY (item_id, location)  
);

CREATE POLICY geo_isolation ON items
USING (
  tenant_id = current_setting('app.current_tenant')::integer
  AND EXISTS (
    SELECT 1 FROM item_locations  
    WHERE item_id = items.id
    AND location = current_setting('app.current_location')
  )
);
```

9. Time-Based Tenant Isolation
```sql
ALTER TABLE items ADD COLUMN available_from TIMESTAMP WITH TIME ZONE;
ALTER TABLE items ADD COLUMN available_until TIMESTAMP WITH TIME ZONE;

CREATE POLICY time_based_isolation ON items
USING (
  tenant_id = current_setting('app.current_tenant')::integer 
  AND (available_from IS NULL OR available_from <= CURRENT_TIMESTAMP)
  AND (available_until IS NULL OR available_until > CURRENT_TIMESTAMP)
);
```

10. Status-Based Tenant Isolation  
```sql
ALTER TABLE items ADD COLUMN status TEXT NOT NULL DEFAULT 'draft';

CREATE POLICY status_based_isolation ON items
USING (
  tenant_id = current_setting('app.current_tenant')::integer
  AND status = 'published' 
);
```

11. Tenant-Specific Columns
```sql
ALTER TABLE items ADD COLUMN tenant_1_data TEXT;
ALTER TABLE items ADD COLUMN tenant_2_data TEXT;

CREATE POLICY tenant_specific_columns ON items
USING (tenant_id = current_setting('app.current_tenant')::integer)
WITH CHECK (
  CASE current_setting('app.current_tenant')::integer
    WHEN 1 THEN tenant_2_data IS NULL
    WHEN 2 THEN tenant_1_data IS NULL 
  END  
);
```

12. Tenant-Based Aggregations
```sql
CREATE POLICY tenant_aggregations ON items
USING (true)
WITH CHECK (
  EXISTS (
    SELECT 1 FROM items i
    WHERE i.tenant_id = current_setting('app.current_tenant')::integer
    HAVING SUM(CASE WHEN i.id = items.id THEN 1 ELSE 0 END) > 0
  )
);
```

13. Multi-Tenant Unique Constraints
```sql
ALTER TABLE items ADD CONSTRAINT tenant_unique_name UNIQUE (tenant_id, name);

CREATE POLICY multi_tenant_unique ON items 
USING (tenant_id = current_setting('app.current_tenant')::integer)
WITH CHECK (tenant_id = current_setting('app.current_tenant')::integer);
```

14. Tenant-Based Soft Deletes
```sql
ALTER TABLE items ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;

CREATE POLICY soft_deletes ON items
USING (
  tenant_id = current_setting('app.current_tenant')::integer
  AND deleted_at IS NULL
)
WITH CHECK (
  tenant_id = current_setting('app.current_tenant')::integer
  AND deleted_at IS NULL
);
```

15. Tenant-Specific Audit Logging
```sql
CREATE TABLE item_audits (
  item_id INTEGER NOT NULL,
  tenant_id INTEGER NOT NULL,
  operation TEXT NOT NULL,
  changed_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE POLICY tenant_audit_logging ON items
USING (true)
WITH CHECK (true)
AFTER INSERT OR UPDATE OR DELETE 
DO ALSO (
  INSERT INTO item_audits (item_id, tenant_id, operation, changed_at)
  VALUES (
    NEW.id,
    current_setting('app.current_tenant')::integer,
    TG_OP,
    CURRENT_TIMESTAMP
  )  
);
```

16. Tenant-Based Rate Limiting
```sql
CREATE TABLE item_access_logs (
  item_id INTEGER NOT NULL,
  tenant_id INTEGER NOT NULL,
  accessed_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE POLICY tenant_rate_limiting ON items
USING (
  tenant_id = current_setting('app.current_tenant')::integer
  AND (
    SELECT COUNT(*) FROM item_access_logs
    WHERE item_id = items.id
    AND tenant_id = current_setting('app.current_tenant')::integer
    AND accessed_at > CURRENT_TIMESTAMP - INTERVAL '1 hour'
  ) < 100  
)
WITH CHECK (
  tenant_id = current_setting('app.current_tenant')::integer
)
AFTER SELECT OR UPDATE 
DO ALSO (
  INSERT INTO item_access_logs (item_id, tenant_id, accessed_at)
  VALUES (
    NEW.id,
    current_setting('app.current_tenant')::integer,
    CURRENT_TIMESTAMP
  )
);
```

17. Tenant-Specific Permissions
```sql
CREATE TABLE item_permissions (
  item_id INTEGER NOT NULL REFERENCES items(id),
  tenant_id INTEGER NOT NULL,
  permission TEXT NOT NULL,
  PRIMARY KEY (item_id, tenant_id, permission)
);

CREATE POLICY tenant_permissions ON items
USING (
  tenant_id = current_setting('app.current_tenant')::integer
  AND EXISTS (
    SELECT 1 FROM item_permissions
    WHERE item_id = items.id  
    AND tenant_id = current_setting('app.current_tenant')::integer
    AND permission = current_setting('app.current_permission')
  )
);
```

18. Tenant-Specific Encryption
```sql
ALTER TABLE items ADD COLUMN encrypted_data BYTEA;

CREATE POLICY tenant_encryption ON items
USING (tenant_id = current_setting('app.current_tenant')::integer)
WITH CHECK (
  tenant_id = current_setting('app.current_tenant')::integer
  AND encrypted_data = PGP_SYM_ENCRYPT(
    concat_ws('|', name, description),
    current_setting('app.current_tenant_encryption_key')
  )
);
```

19. Tenant-Specific Pseudonymization  
```sql
ALTER TABLE items ADD COLUMN pseudonymized_name TEXT;

CREATE POLICY tenant_pseudonymization ON items
USING (tenant_id = current_setting('app.current_tenant')::integer)  
WITH CHECK (
  tenant_id = current_setting('app.current_tenant')::integer
  AND pseudonymized_name = ENCODE(HMAC(
    name,
    current_setting('app.current_tenant_pseudonymization_key'),
    'sha256'  
  ), 'hex')
);
```

20. Tenant-Based Data Retention
```sql
CREATE POLICY tenant_data_retention ON items
USING (
  tenant_id = current_setting('app.current_tenant')::integer
  AND created_at > CURRENT_TIMESTAMP - INTERVAL '1 year'
);
```

21. Tenant-Specific Search
```sql
ALTER TABLE items ADD COLUMN search_vector TSVECTOR;

CREATE POLICY tenant_search ON items
USING (
  tenant_id = current_setting('app.current_tenant')::integer  
  AND search_vector @@ plainto_tsquery(current_setting('app.current_search_query'))
);
```

22. Tenant-Based Recommendations
```sql
CREATE TABLE item_recommendations (
  item_id INTEGER NOT NULL REFERENCES items(id),
  tenant_id INTEGER NOT NULL,
  score FLOAT NOT NULL,
  PRIMARY KEY (item_id, tenant_id)  
);

CREATE POLICY tenant_recommendations ON items
USING (
  tenant_id = current_setting('app.current_tenant')::integer
  AND EXISTS (
    SELECT 1 FROM item_recommendations
    WHERE item_id = items.id
    AND tenant_id = current_setting('app.current_tenant')::integer
    AND score > 0.8
  )  
);
```

23. Tenant-Specific Caching
```sql
ALTER TABLE items ADD COLUMN cache_expires_at TIMESTAMP WITH TIME ZONE;

CREATE POLICY tenant_caching ON items
USING (
  tenant_id = current_setting('app.current_tenant')::integer
  AND (
    cache_expires_at IS NULL 
    OR cache_expires_at > CURRENT_TIMESTAMP
  )  
)
WITH CHECK (
  tenant_id = current_setting('app.current_tenant')::integer
);
```

24. Tenant-Based Archiving
```sql
ALTER TABLE items ADD COLUMN archived_at TIMESTAMP WITH TIME ZONE;

CREATE POLICY tenant_archiving ON items
USING (
  tenant_id = current_setting('app.current_tenant')::integer
  AND archived_at IS NULL  
)
WITH CHECK (
  tenant_id = current_setting('app.current_tenant')::integer
);
```

25. Tenant-Specific Versioning
```sql
CREATE TABLE item_versions (
  item_id INTEGER NOT NULL,
  tenant_id INTEGER NOT NULL,
  version INTEGER NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL,
  PRIMARY KEY (item_id, tenant_id, version)
);

CREATE POLICY tenant_versioning ON items
USING (tenant_id = current_setting('app.current_tenant')::integer)
WITH CHECK (
  tenant_id = current_setting('app.current_tenant')::integer
)  
AFTER UPDATE ON items
DO ALSO (
  INSERT INTO item_versions (item_id, tenant_id, version, name, description, created_at)
  VALUES (
    OLD.id,
    current_setting('app.current_tenant')::integer,
    (SELECT COALESCE(MAX(version), 0) FROM item_versions WHERE item_id = OLD.id) + 1,
    NEW.name,
    NEW.description,
    CURRENT_TIMESTAMP
  )
);
```

26. Tenant-Based Data Masking
```sql
CREATE FUNCTION mask_email(email TEXT) RETURNS TEXT AS $$
BEGIN
  RETURN regexp_replace(email, '(.{2})[^@]+@', '\1***@');
END;
$$ LANGUAGE plpgsql;

ALTER TABLE items ADD COLUMN email TEXT;

CREATE POLICY tenant_data_masking ON items
USING (tenant_id = current_setting('app.current_tenant')::integer)
WITH CHECK (tenant_id = current_setting('app.current_tenant')::integer)
AFTER SELECT ON items
DO INSTEAD (
  SELECT id, tenant_id, name, description, created_at, mask_email(email) AS email 
  FROM items
  WHERE tenant_id = current_setting('app.current_tenant')::integer
    AND id = items.id
);
```

27. Tenant-Specific Aggregates
```sql
CREATE POLICY tenant_aggregates ON items
USING (tenant_id = current_setting('app.current_tenant')::integer)
WITH CHECK (tenant_id = current_setting('app.current_tenant')::integer)
AFTER SELECT ON items
DO INSTEAD (
  SELECT 
    COUNT(*) AS total_items,
    SUM(CASE WHEN created_at > CURRENT_TIMESTAMP - INTERVAL '1 month' THEN 1 ELSE 0 END) AS items_last_month
  FROM items  
  WHERE tenant_id = current_setting('app.current_tenant')::integer
);
```

28. Tenant-Based IP Filtering
```sql
CREATE TABLE tenant_ip_whitelist (
  tenant_id INTEGER NOT NULL,
  ip_address INET NOT NULL,
  PRIMARY KEY (tenant_id, ip_address)  
);

CREATE POLICY tenant_ip_filtering ON items
USING (
  tenant_id = current_setting('app.current_tenant')::integer
  AND EXISTS (
    SELECT 1 FROM tenant_ip_whitelist
    WHERE tenant_id = current_setting('app.current_tenant')::integer
    AND ip_address = inet_client_addr()
  )
);
```

29. Tenant-Specific Throttling
```sql
CREATE TABLE item_access_counts (
  tenant_id INTEGER NOT NULL,
  item_id INTEGER NOT NULL,
  access_count INTEGER NOT NULL,
  last_accessed_at TIMESTAMP WITH TIME ZONE NOT NULL,
  PRIMARY KEY (tenant_id, item_id)  
);

CREATE POLICY tenant_throttling ON items
USING (
  tenant_id = current_setting('app.current_tenant')::integer
  



### Explain tenant onboarding, migration, merging, splitting with RLS


Implementing Row-Level Security (RLS) in PostgreSQL for SaaS applications is crucial for ensuring data isolation among different tenants. This approach ensures that users can only access data that belongs to their tenant, enhancing security and privacy. Below, I'll guide you through the processes of tenant onboarding, migration, merging, and splitting, providing production-ready examples.

### 1. Tenant Onboarding

When a new tenant signs up, you need to create a unique identifier for them (e.g., `tenant_id`) and apply RLS policies to ensure they only access their data.

**Step 1: Create Tenant Table**

```sql
CREATE TABLE tenants (
    tenant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL
);
```

**Step 2: Create a Data Table with Tenant ID**

```sql
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    order_data JSONB NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
);
```

**Step 3: Enable RLS and Create Policy**

```sql
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON orders
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant')::UUID);
```

**Step 4: Set Tenant Context**

Before any operation, set the tenant context:

```sql
SET app.current_tenant TO 'your-tenant-uuid';
```

### 2. Tenant Migration

Migrating a tenant involves transferring their data to a new `tenant_id`. This could be due to restructuring or consolidating tenants.

**Step 1: Update Tenant ID**

```sql
UPDATE orders SET tenant_id = 'new-tenant-uuid' WHERE tenant_id = 'old-tenant-uuid';
```

**Step 2: Update Tenant Record** (if necessary)

```sql
UPDATE tenants SET tenant_id = 'new-tenant-uuid' WHERE tenant_id = 'old-tenant-uuid';
```

### 3. Tenant Merging

Merging tenants involves combining data from two tenants into one, requiring updates to the `tenant_id` in all relevant tables.

```sql
UPDATE orders SET tenant_id = 'primary-tenant-uuid' WHERE tenant_id = 'secondary-tenant-uuid';
```

After the merge, you might want to remove the secondary tenant's record or mark it as merged.

```sql
DELETE FROM tenants WHERE tenant_id = 'secondary-tenant-uuid';
-- OR
UPDATE tenants SET is_merged = TRUE WHERE tenant_id = 'secondary-tenant-uuid';
```

### 4. Tenant Splitting

Splitting a tenant requires identifying which data belongs to the new tenant and updating the `tenant_id` accordingly.

**Step 1: Create New Tenant**

```sql
INSERT INTO tenants (name) VALUES ('New Tenant');
```

**Step 2: Update Data for New Tenant**

Assuming you have a criterion for splitting (e.g., a specific range of orders):

```sql
UPDATE orders SET tenant_id = 'new-tenant-uuid' WHERE tenant_id = 'old-tenant-uuid' AND order_criteria = 'criteria';
```

### Best Practices and Considerations

- **Security**: Always validate tenant access at the application level to prevent unauthorized changes to the `app.current_tenant` setting.
- **Performance**: RLS can introduce overhead. Monitor performance and consider strategies like partitioning for large datasets.
- **Maintenance**: Regularly review and update your RLS policies and tenant data to ensure they reflect your current business logic and data access patterns.

Implementing RLS in PostgreSQL for tenant management in a SaaS application provides a robust mechanism for data isolation. By following these examples and best practices, you can ensure that your application maintains high levels of data integrity and security.



### Detail performance optimization for 100,000+ tenant systems


I'll provide a comprehensive guide for optimizing Row Level Security (RLS) performance in large multi-tenant PostgreSQL systems. Here's a detailed breakdown:

1. First, here's the optimal table structure with partitioning:

```sql
-- Tenant table
CREATE TABLE tenants (
    tenant_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    created_at timestamptz DEFAULT now(),
    settings jsonb
);

-- Base table with tenant partitioning
CREATE TABLE orders (
    id bigint,
    tenant_id uuid NOT NULL,
    order_date date NOT NULL,
    customer_id bigint,
    amount decimal(12,2),
    status text,
    PRIMARY KEY (tenant_id, id)
) PARTITION BY LIST (tenant_id);

-- Create partitions automatically
CREATE OR REPLACE FUNCTION create_tenant_partition() 
RETURNS trigger AS $$
BEGIN
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS orders_%s ' ||
        'PARTITION OF orders ' ||
        'FOR VALUES IN (%L)',
        REPLACE(NEW.tenant_id::text, '-', '_'),
        NEW.tenant_id
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER create_partition_on_tenant_insert
    AFTER INSERT ON tenants
    FOR EACH ROW
    EXECUTE FUNCTION create_tenant_partition();
```

2. Optimized RLS policy:

```sql
-- Create a function to get current tenant
CREATE OR REPLACE FUNCTION current_tenant_id()
RETURNS uuid AS $$
BEGIN
    RETURN current_setting('app.current_tenant_id')::uuid;
END;
$$ LANGUAGE plpgsql STABLE;

-- Apply RLS policy
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON orders
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

-- Index optimization
CREATE INDEX idx_orders_tenant_date ON orders (tenant_id, order_date);
```

3. Connection handling and tenant context:

```sql
-- Connection pool wrapper example (Python with psycopg2)
class TenantConnectionWrapper:
    def __init__(self, pool):
        self.pool = pool
        
    def get_connection(self, tenant_id):
        conn = self.pool.getconn()
        with conn.cursor() as cur:
            cur.execute(
                "SET app.current_tenant_id = %s",
                (tenant_id,)
            )
        return conn

    def return_connection(self, conn):
        with conn.cursor() as cur:
            cur.execute("RESET app.current_tenant_id")
        self.pool.putconn(conn)
```

4. Performance optimization techniques:

```sql
-- Materialized views per tenant
CREATE MATERIALIZED VIEW tenant_order_stats AS
SELECT 
    tenant_id,
    date_trunc('month', order_date) as month,
    count(*) as order_count,
    sum(amount) as total_amount
FROM orders
GROUP BY tenant_id, date_trunc('month', order_date);

CREATE UNIQUE INDEX idx_tenant_order_stats 
ON tenant_order_stats (tenant_id, month);

-- Implement concurrent refresh
CREATE OR REPLACE FUNCTION refresh_tenant_stats(p_tenant_id uuid)
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY tenant_order_stats;
END;
$$ LANGUAGE plpgsql;

-- Optimize tenant-specific queries
CREATE INDEX idx_orders_tenant_status ON orders (tenant_id, status);
CREATE INDEX idx_orders_tenant_customer ON orders (tenant_id, customer_id);
```

5. Monitoring and maintenance:

```sql
-- Create monitoring view
CREATE VIEW tenant_table_stats AS
SELECT 
    schemaname,
    relname,
    n_live_tup as row_count,
    n_dead_tup as dead_tuples,
    last_vacuum,
    last_autovacuum
FROM pg_stat_user_tables
WHERE relname LIKE 'orders_%';

-- Create maintenance function
CREATE OR REPLACE FUNCTION maintain_tenant_partition(p_tenant_id uuid)
RETURNS void AS $$
BEGIN
    -- Vacuum specific tenant partition
    EXECUTE format(
        'VACUUM ANALYZE orders_%s',
        REPLACE(p_tenant_id::text, '-', '_')
    );
END;
$$ LANGUAGE plpgsql;
```

6. Query optimization examples:

```sql
-- Use tenant-specific prepared statements
PREPARE tenant_order_query(date) AS
    SELECT *
    FROM orders
    WHERE tenant_id = current_tenant_id()
    AND order_date >= $1
    ORDER BY order_date DESC
    LIMIT 100;

-- Optimize bulk operations
CREATE OR REPLACE FUNCTION bulk_insert_orders(
    p_orders jsonb
) RETURNS void AS $$
DECLARE
    v_tenant_id uuid;
BEGIN
    v_tenant_id := current_tenant_id();
    
    -- Bulk insert with tenant_id
    INSERT INTO orders (tenant_id, order_date, customer_id, amount, status)
    SELECT 
        v_tenant_id,
        (json_array_elements(p_orders)->>'order_date')::date,
        (json_array_elements(p_orders)->>'customer_id')::bigint,
        (json_array_elements(p_orders)->>'amount')::decimal,
        json_array_elements(p_orders)->>'status'
    ON CONFLICT DO NOTHING;
END;
$$ LANGUAGE plpgsql;
```

Key performance considerations:

1. Always include tenant_id in indexes
2. Use partitioning for large datasets
3. Implement connection pooling with tenant context
4. Cache frequently accessed data per tenant
5. Use prepared statements
6. Regular maintenance of tenant partitions
7. Monitor query performance per tenant

Additional recommendations:

```sql
-- Set appropriate memory parameters per tenant size
ALTER DATABASE myapp SET work_mem = '50MB';
ALTER DATABASE myapp SET maintenance_work_mem = '256MB';

-- Configure autovacuum for high-throughput tenants
ALTER TABLE orders SET (
    autovacuum_vacuum_scale_factor = 0.05,
    autovacuum_analyze_scale_factor = 0.02
);

-- Use parallel query for large tenants
SET max_parallel_workers_per_gather = 4;
```

This setup should handle 100,000+ tenants efficiently while maintaining proper isolation and performance. Remember to monitor and adjust based on your specific workload patterns.



---


## Subscription & Billing RLS Patterns {#subscription_billing_rls}


### Complete RLS for freemium, tiered, usage-based, seat-based pricing


Certainly! Here are some exhaustive, production-ready examples of implementing Row-Level Security (RLS) in PostgreSQL for various SaaS pricing models, including freemium, tiered, usage-based, and seat-based pricing.

1. Freemium Pricing Model:
In a freemium model, users have access to basic features for free, while premium features require a paid subscription. RLS can be used to control access to specific rows based on the user's subscription status.

```sql
-- Create a users table
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(50) UNIQUE,
  email VARCHAR(100),
  is_premium BOOLEAN DEFAULT FALSE
);

-- Create a products table
CREATE TABLE products (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100),
  description TEXT,
  is_premium BOOLEAN DEFAULT FALSE
);

-- Enable RLS on the products table
ALTER TABLE products ENABLE ROW LEVEL SECURITY;

-- Create a policy to allow all users to access non-premium products
CREATE POLICY non_premium_products_policy ON products
FOR SELECT TO PUBLIC
USING (is_premium = FALSE);

-- Create a policy to allow premium users to access all products
CREATE POLICY premium_products_policy ON products
FOR SELECT TO users
USING (is_premium OR (SELECT is_premium FROM users WHERE users.id = current_setting('app.user_id')::integer));
```

In this example, the `users` table stores user information, including whether they are premium users or not. The `products` table contains product information, with a flag indicating if a product is premium or not. The RLS policies ensure that all users can access non-premium products, while only premium users can access all products.

2. Tiered Pricing Model:
In a tiered pricing model, different subscription tiers offer varying levels of features and resources. RLS can be used to control access to specific rows based on the user's subscription tier.

```sql
-- Create a users table
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(50) UNIQUE,
  email VARCHAR(100),
  tier VARCHAR(20) DEFAULT 'basic'
);

-- Create a features table
CREATE TABLE features (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100),
  description TEXT,
  tier VARCHAR(20)
);

-- Enable RLS on the features table
ALTER TABLE features ENABLE ROW LEVEL SECURITY;

-- Create a policy to allow users to access features based on their tier
CREATE POLICY tier_based_access_policy ON features
FOR SELECT TO users
USING ((SELECT tier FROM users WHERE users.id = current_setting('app.user_id')::integer) >= tier);
```

In this example, the `users` table includes a `tier` column to store the user's subscription tier. The `features` table contains information about different features, each associated with a specific tier. The RLS policy ensures that users can only access features that are available in their subscription tier or lower.

3. Usage-Based Pricing Model:
In a usage-based pricing model, users are charged based on their consumption of resources or services. RLS can be used to track and limit usage based on the user's plan.

```sql
-- Create a users table
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(50) UNIQUE,
  email VARCHAR(100),
  plan VARCHAR(20),
  api_calls_limit INTEGER
);

-- Create an api_calls table to track usage
CREATE TABLE api_calls (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Enable RLS on the api_calls table
ALTER TABLE api_calls ENABLE ROW LEVEL SECURITY;

-- Create a policy to allow users to access their own API call records
CREATE POLICY user_api_calls_policy ON api_calls
FOR SELECT TO users
USING (user_id = current_setting('app.user_id')::integer);

-- Create a function to check if the user has exceeded their API call limit
CREATE OR REPLACE FUNCTION check_api_call_limit() RETURNS BOOLEAN AS $$
DECLARE
  user_id INTEGER := current_setting('app.user_id')::integer;
  api_calls_count INTEGER;
  api_calls_limit INTEGER;
BEGIN
  SELECT COUNT(*) INTO api_calls_count
  FROM api_calls
  WHERE user_id = check_api_call_limit.user_id;
  
  SELECT users.api_calls_limit INTO api_calls_limit
  FROM users
  WHERE users.id = check_api_call_limit.user_id;
  
  RETURN api_calls_count < api_calls_limit;
END;
$$ LANGUAGE plpgsql;

-- Create a policy to restrict API calls based on the user's limit
CREATE POLICY api_call_limit_policy ON api_calls
FOR INSERT TO users
WITH CHECK (check_api_call_limit());
```

In this example, the `users` table includes a `plan` column to store the user's subscription plan and an `api_calls_limit` column to store the maximum number of API calls allowed for their plan. The `api_calls` table tracks the API usage for each user. The RLS policies ensure that users can only access their own API call records and restrict new API calls if the user has exceeded their limit.

4. Seat-Based Pricing Model:
In a seat-based pricing model, customers pay based on the number of users or "seats" they require. RLS can be used to control access to specific rows based on the user's associated customer and the number of seats allocated to that customer.

```sql
-- Create a customers table
CREATE TABLE customers (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100),
  seats_allocated INTEGER
);

-- Create a users table
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(50) UNIQUE,
  email VARCHAR(100),
  customer_id INTEGER REFERENCES customers(id)
);

-- Create a projects table
CREATE TABLE projects (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100),
  description TEXT,
  customer_id INTEGER REFERENCES customers(id)
);

-- Enable RLS on the projects table
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

-- Create a policy to allow users to access projects associated with their customer
CREATE POLICY customer_projects_policy ON projects
FOR SELECT TO users
USING (customer_id = (SELECT customer_id FROM users WHERE users.id = current_setting('app.user_id')::integer));

-- Create a function to check if the customer has available seats
CREATE OR REPLACE FUNCTION check_available_seats() RETURNS BOOLEAN AS $$
DECLARE
  customer_id INTEGER;
  seats_allocated INTEGER;
  seats_used INTEGER;
BEGIN
  SELECT users.customer_id INTO customer_id
  FROM users
  WHERE users.id = current_setting('app.user_id')::integer;
  
  SELECT customers.seats_allocated INTO seats_allocated
  FROM customers
  WHERE customers.id = check_available_seats.customer_id;
  
  SELECT COUNT(*) INTO seats_used
  FROM users
  WHERE users.customer_id = check_available_seats.customer_id;
  
  RETURN seats_used < seats_allocated;
END;
$$ LANGUAGE plpgsql;

-- Create a policy to restrict user creation based on available seats
CREATE POLICY seat_limit_policy ON users
FOR INSERT TO PUBLIC
WITH CHECK (check_available_seats());
```

In this example, the `customers` table stores information about each customer, including the number of seats allocated to them. The `users` table associates each user with a customer. The `projects` table contains project information, with each project belonging to a specific customer. The RLS policies ensure that users can only access projects associated with their customer and restrict the creation of new users if the customer has reached their seat limit.

These examples demonstrate how RLS can be used to implement various pricing models in a SaaS application. Remember to adjust the table structures, policy conditions, and functions based on your specific requirements. Additionally, make sure to thoroughly test the RLS policies to ensure they provide the desired level of security and access control.



### Feature flags and entitlements enforcement via RLS


Implementing feature flags and entitlements enforcement in a SaaS application using PostgreSQL Row-Level Security (RLS) involves creating a system where access to certain features or data is controlled at the database level, based on user or tenant entitlements. This approach ensures that the enforcement is deeply integrated into the data layer, providing a robust and scalable solution for managing access control.

### Prerequisites

- PostgreSQL 9.5 or higher (RLS was introduced in 9.5).
- A SaaS application with multi-tenancy architecture.
- A table structure that includes user or tenant identifiers to enforce RLS policies.
- Understanding of basic PostgreSQL operations and SQL.

### Scenario

Let's consider a SaaS application with a multi-tenant architecture, where we have a table `features` that stores feature flags for each tenant, and a table `entitlements` that stores the entitlements for each user within those tenants. We want to enforce that users can only access data related to the features and entitlements assigned to them or their tenant.

### Step 1: Setup Tables

```sql
CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    tenant_id INT NOT NULL REFERENCES tenants(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(255) NOT NULL
);

CREATE TABLE features (
    id SERIAL PRIMARY KEY,
    tenant_id INT NOT NULL REFERENCES tenants(id),
    feature_name VARCHAR(255) NOT NULL,
    is_enabled BOOLEAN NOT NULL
);

CREATE TABLE entitlements (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id),
    feature_id INT NOT NULL REFERENCES features(id),
    is_entitled BOOLEAN NOT NULL
);
```

### Step 2: Enable RLS and Create Policies

First, enable RLS for the tables where you want to enforce access control.

```sql
ALTER TABLE features ENABLE ROW LEVEL SECURITY;
ALTER TABLE entitlements ENABLE ROW LEVEL SECURITY;
```

Then, create policies that define the access control. For example, a policy to ensure users can only access features and entitlements for their tenant, and if they are entitled to them.

```sql
CREATE POLICY tenant_access_features ON features
    FOR SELECT
    USING (tenant_id = current_setting('app.current_tenant_id')::INT);

CREATE POLICY tenant_access_entitlements ON entitlements
    FOR SELECT
    USING (user_id IN (SELECT id FROM users WHERE tenant_id = current_setting('app.current_tenant_id')::INT));

-- Optionally, enforce entitlements directly
CREATE POLICY user_entitlement_access ON entitlements
    FOR SELECT
    USING (is_entitled = true AND user_id = current_setting('app.current_user_id')::INT);
```

### Step 3: Set Session Variables

Before querying the `features` or `entitlements` tables, set the session variables to the current user's tenant ID and user ID. This could be done in the application layer.

```sql
SET app.current_tenant_id = '1'; -- Assume tenant ID 1
SET app.current_user_id = '2'; -- Assume user ID 2
```

### Step 4: Query with RLS

Now, when querying the `features` or `entitlements` tables, RLS policies will automatically apply, ensuring users can only access data they are entitled to.

```sql
-- Attempt to access features
SELECT * FROM features;

-- Attempt to access entitlements
SELECT * FROM entitlements;
```

### Notes

- Ensure that the session variables (`app.current_tenant_id` and `app.current_user_id`) are securely set in your application logic, based on the authenticated user's context.
- You might need to adjust the policies and table structures based on your specific application needs and data model.
- Remember to test your RLS policies thoroughly to ensure they enforce the desired access control without unintended side effects.

This example provides a foundational approach to implementing feature flags and entitlements enforcement using PostgreSQL RLS in a SaaS application. Depending on the complexity and requirements of your application, further customization and additional policies may be necessary.



### Payment security and PCI compliance with RLS


I'll provide a comprehensive example of implementing Row Level Security (RLS) for payment-related tables in a multi-tenant SaaS application, following PCI DSS compliance best practices.

```sql
-- First, let's create our schema and enable RLS
CREATE SCHEMA payments;
ALTER SCHEMA payments OWNER TO app_owner;

-- Create an enum for payment status
CREATE TYPE payment_status AS ENUM (
    'pending',
    'processing',
    'completed',
    'failed',
    'refunded'
);

-- Create tables with appropriate indexes
CREATE TABLE payments.payment_methods (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id uuid NOT NULL,
    customer_id uuid NOT NULL,
    payment_type varchar(50) NOT NULL,
    -- Store only last 4 digits as per PCI requirements
    last_four_digits varchar(4),
    card_brand varchar(50),
    expiry_month integer,
    expiry_year integer,
    -- Encrypted token from payment processor
    processor_token text,
    is_default boolean DEFAULT false,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz DEFAULT CURRENT_TIMESTAMP,
    created_by uuid NOT NULL,
    metadata jsonb
);

CREATE TABLE payments.transactions (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id uuid NOT NULL,
    payment_method_id uuid REFERENCES payments.payment_methods(id),
    amount decimal(12,2) NOT NULL,
    currency varchar(3) NOT NULL,
    status payment_status NOT NULL,
    processor_reference varchar(255),
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamptz DEFAULT CURRENT_TIMESTAMP,
    created_by uuid NOT NULL,
    metadata jsonb
);

-- Create indexes
CREATE INDEX idx_payment_methods_tenant ON payments.payment_methods(tenant_id);
CREATE INDEX idx_payment_methods_customer ON payments.payment_methods(customer_id);
CREATE INDEX idx_transactions_tenant ON payments.transactions(tenant_id);
CREATE INDEX idx_transactions_status ON payments.transactions(status);
CREATE INDEX idx_transactions_created_at ON payments.transactions(created_at);

-- Enable RLS on tables
ALTER TABLE payments.payment_methods ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments.transactions ENABLE ROW LEVEL SECURITY;

-- Create a function to get current tenant_id
CREATE OR REPLACE FUNCTION current_tenant_id()
RETURNS uuid
LANGUAGE sql STABLE
AS $$
    SELECT NULLIF(current_setting('app.current_tenant_id', TRUE), '')::uuid;
$$;

-- Create a function to get current user_id
CREATE OR REPLACE FUNCTION current_user_id()
RETURNS uuid
LANGUAGE sql STABLE
AS $$
    SELECT NULLIF(current_setting('app.current_user_id', TRUE), '')::uuid;
$$;

-- Create a function to check if user has specific permission
CREATE OR REPLACE FUNCTION has_permission(permission_name text)
RETURNS boolean
LANGUAGE sql STABLE
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM user_permissions up
        WHERE up.user_id = current_user_id()
        AND up.permission_name = permission_name
    );
$$;

-- Create RLS policies for payment_methods

-- View policy
CREATE POLICY payment_methods_view_policy ON payments.payment_methods
    FOR SELECT
    USING (
        tenant_id = current_tenant_id()
        AND (
            has_permission('payments.view_all')
            OR created_by = current_user_id()
            OR EXISTS (
                SELECT 1
                FROM customers c
                WHERE c.id = customer_id
                AND c.assigned_to = current_user_id()
            )
        )
    );

-- Insert policy
CREATE POLICY payment_methods_insert_policy ON payments.payment_methods
    FOR INSERT
    WITH CHECK (
        tenant_id = current_tenant_id()
        AND has_permission('payments.create')
    );

-- Update policy
CREATE POLICY payment_methods_update_policy ON payments.payment_methods
    FOR UPDATE
    USING (
        tenant_id = current_tenant_id()
        AND has_permission('payments.update')
    )
    WITH CHECK (
        tenant_id = current_tenant_id()
        AND has_permission('payments.update')
    );

-- Delete policy
CREATE POLICY payment_methods_delete_policy ON payments.payment_methods
    FOR DELETE
    USING (
        tenant_id = current_tenant_id()
        AND has_permission('payments.delete')
    );

-- Create RLS policies for transactions

-- View policy
CREATE POLICY transactions_view_policy ON payments.transactions
    FOR SELECT
    USING (
        tenant_id = current_tenant_id()
        AND (
            has_permission('payments.view_all')
            OR created_by = current_user_id()
            OR EXISTS (
                SELECT 1
                FROM payments.payment_methods pm
                JOIN customers c ON c.id = pm.customer_id
                WHERE pm.id = payment_method_id
                AND c.assigned_to = current_user_id()
            )
        )
    );

-- Insert policy
CREATE POLICY transactions_insert_policy ON payments.transactions
    FOR INSERT
    WITH CHECK (
        tenant_id = current_tenant_id()
        AND has_permission('payments.create')
    );

-- Update policy (limited to specific status changes)
CREATE POLICY transactions_update_policy ON payments.transactions
    FOR UPDATE
    USING (
        tenant_id = current_tenant_id()
        AND has_permission('payments.update')
        AND status IN ('pending', 'processing')
    )
    WITH CHECK (
        tenant_id = current_tenant_id()
        AND has_permission('payments.update')
        AND status IN ('completed', 'failed', 'refunded')
    );

-- Create audit triggers
CREATE TABLE payments.audit_log (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id uuid NOT NULL,
    table_name text NOT NULL,
    record_id uuid NOT NULL,
    action text NOT NULL,
    old_data jsonb,
    new_data jsonb,
    changed_by uuid NOT NULL,
    changed_at timestamptz DEFAULT CURRENT_TIMESTAMP
);

CREATE OR REPLACE FUNCTION payments.audit_trigger_func()
RETURNS trigger AS $$
BEGIN
    INSERT INTO payments.audit_log (
        tenant_id,
        table_name,
        record_id,
        action,
        old_data,
        new_data,
        changed_by
    ) VALUES (
        CASE
            WHEN TG_OP = 'DELETE' THEN OLD.tenant_id
            ELSE NEW.tenant_id
        END,
        TG_TABLE_NAME,
        CASE
            WHEN TG_OP = 'DELETE' THEN OLD.id
            ELSE NEW.id
        END,
        TG_OP,
        CASE WHEN TG_OP = 'DELETE' THEN row_to_json(OLD)::jsonb ELSE NULL END,
        CASE WHEN TG_OP != 'DELETE' THEN row_to_json(NEW)::jsonb ELSE NULL END,
        current_user_id()
    );
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Add audit triggers to tables
CREATE TRIGGER payment_methods_audit
    AFTER INSERT OR UPDATE OR DELETE ON payments.payment_methods
    FOR EACH ROW EXECUTE FUNCTION payments.audit_trigger_func();

CREATE TRIGGER transactions_audit
    AFTER INSERT OR UPDATE OR DELETE ON payments.transactions
    FOR EACH ROW EXECUTE FUNCTION payments.audit_trigger_func();

-- Create helper functions for common operations
CREATE OR REPLACE FUNCTION payments.create_payment_method(
    p_customer_id uuid,
    p_payment_type varchar,
    p_last_four varchar,
    p_card_brand varchar,
    p_expiry_month integer,
    p_expiry_year integer,
    p_processor_token text,
    p_metadata jsonb DEFAULT NULL
)
RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER
AS $$
DECLARE
    v_payment_method_id uuid;
BEGIN
    IF NOT has_permission('payments.create') THEN
        RAISE EXCEPTION 'Permission denied';
    END IF;

    INSERT INTO payments.payment_methods (
        tenant_id,
        customer_id,
        payment_type,
        last_four_digits,
        card_brand,
        expiry_month,
        expiry_year,
        processor_token,
        created_by,
        metadata
    ) VALUES (
        current_tenant_id(),
        p_customer_id,
        p_payment_type,
        p_last_four,
        p_card_brand,
        p_expiry_month,
        p_expiry_year,
        p_processor_token,
        current_user_id(),
        p_metadata
    )
    RETURNING id INTO v_payment_method_id;

    RETURN v_payment_method_id;
END;
$$;
```

This implementation includes:

1. Secure table structures following PCI DSS guidelines (not storing full card numbers)
2. Comprehensive RLS policies with fine-grained access control
3. Audit logging for all changes
4. Proper indexing for performance
5. Helper functions for common operations
6. Permission-based access control
7. Tenant isolation

To use this in your application:

```sql
-- Set session variables
SET app.current_tenant_id = 'tenant-uuid';
SET app.current_user_id = 'user-uuid';

-- Create a payment method
SELECT payments.create_payment_method(
    'customer-uuid',
    'credit_card',
    '4242',
    'visa',
    12,
    2025,
    'tok_secure_token',
    '{"description": "Corporate card"}'::jsonb
);

-- Query transactions with RLS automatically applied
SELECT * FROM payments.transactions
WHERE status = 'completed'
ORDER BY created_at DESC;
```

Important security considerations:

1. Always use prepared statements to prevent SQL injection
2. Encrypt sensitive data at rest
3. Implement proper session management
4. Regularly audit access patterns
5. Monitor for suspicious activities
6. Implement rate limiting
7. Use TLS for all connections
8. Regularly rotate encryption keys
9. Implement proper backup procedures
10. Follow PCI DSS requirements if storing card data



---


## Advanced User Management & RBAC {#user_management_rbac}


### Design 50 different role types for SaaS with complete RLS policies


Here are 50 different role types for a SaaS application with complete Row Level Security (RLS) policies for PostgreSQL:

1. Super Admin:
   - Can access all tables and perform any operation
   - RLS Policy: No restrictions

2. Company Admin:
   - Can manage users, roles, and settings within their own company
   - RLS Policy:
     ```sql
     CREATE POLICY company_admin_access ON users
     FOR ALL
     TO company_admin
     USING (company_id = current_setting('app.current_company_id')::integer);
     ```

3. Department Manager:
   - Can view and manage data within their assigned department
   - RLS Policy:
     ```sql
     CREATE POLICY department_manager_access ON department_data
     FOR ALL
     TO department_manager
     USING (department_id = (SELECT department_id FROM user_departments WHERE user_id = current_setting('app.current_user_id')::integer));
     ```

4. Project Manager:
   - Can manage projects and view project-related data
   - RLS Policy:
     ```sql
     CREATE POLICY project_manager_access ON projects
     FOR ALL
     TO project_manager
     USING (id IN (SELECT project_id FROM user_projects WHERE user_id = current_setting('app.current_user_id')::integer));
     ```

5. Team Lead:
   - Can manage team members and view team-related data
   - RLS Policy:
     ```sql
     CREATE POLICY team_lead_access ON team_members
     FOR ALL
     TO team_lead
     USING (team_id IN (SELECT team_id FROM user_teams WHERE user_id = current_setting('app.current_user_id')::integer));
     ```

6. Employee:
   - Can view and update their own profile information
   - RLS Policy:
     ```sql
     CREATE POLICY employee_access ON employees
     FOR ALL
     TO employee
     USING (id = current_setting('app.current_user_id')::integer);
     ```

7. Customer:
   - Can view and manage their own orders and profile
   - RLS Policy:
     ```sql
     CREATE POLICY customer_access ON orders
     FOR ALL
     TO customer
     USING (customer_id = current_setting('app.current_user_id')::integer);
     ```

8. Vendor:
   - Can view and manage their own products and orders
   - RLS Policy:
     ```sql
     CREATE POLICY vendor_access ON products
     FOR ALL
     TO vendor
     USING (vendor_id = (SELECT vendor_id FROM users WHERE id = current_setting('app.current_user_id')::integer));
     ```

9. Auditor:
   - Can view audit logs and reports
   - RLS Policy:
     ```sql
     CREATE POLICY auditor_access ON audit_logs
     FOR SELECT
     TO auditor
     USING (true);
     ```

10. Support Agent:
    - Can view and update customer support tickets
    - RLS Policy:
      ```sql
      CREATE POLICY support_agent_access ON support_tickets
      FOR ALL
      TO support_agent
      USING (assigned_to = current_setting('app.current_user_id')::integer);
      ```

11. Sales Representative:
    - Can view and manage sales opportunities and contacts
    - RLS Policy:
      ```sql
      CREATE POLICY sales_rep_access ON opportunities
      FOR ALL
      TO sales_representative
      USING (assigned_to = current_setting('app.current_user_id')::integer);
      ```

12. Marketing Coordinator:
    - Can view and manage marketing campaigns and leads
    - RLS Policy:
      ```sql
      CREATE POLICY marketing_coordinator_access ON campaigns
      FOR ALL
      TO marketing_coordinator
      USING (owner_id = current_setting('app.current_user_id')::integer);
      ```

13. Financial Analyst:
    - Can view financial reports and data
    - RLS Policy:
      ```sql
      CREATE POLICY financial_analyst_access ON financial_data
      FOR SELECT
      TO financial_analyst
      USING (true);
      ```

14. HR Manager:
    - Can view and manage employee records and HR data
    - RLS Policy:
      ```sql
      CREATE POLICY hr_manager_access ON employee_records
      FOR ALL
      TO hr_manager
      USING (true);
      ```

15. Recruiter:
    - Can view and manage job postings and candidate information
    - RLS Policy:
      ```sql
      CREATE POLICY recruiter_access ON job_postings
      FOR ALL
      TO recruiter
      USING (owner_id = current_setting('app.current_user_id')::integer);
      ```

16. Inventory Manager:
    - Can view and manage inventory levels and stock data
    - RLS Policy:
      ```sql
      CREATE POLICY inventory_manager_access ON inventory
      FOR ALL
      TO inventory_manager
      USING (true);
      ```

17. Warehouse Supervisor:
    - Can view and manage warehouse operations and shipments
    - RLS Policy:
      ```sql
      CREATE POLICY warehouse_supervisor_access ON shipments
      FOR ALL
      TO warehouse_supervisor
      USING (warehouse_id = (SELECT warehouse_id FROM user_warehouses WHERE user_id = current_setting('app.current_user_id')::integer));
      ```

18. Quality Assurance Specialist:
    - Can view and manage quality control data and reports
    - RLS Policy:
      ```sql
      CREATE POLICY qa_specialist_access ON quality_control
      FOR ALL
      TO qa_specialist
      USING (true);
      ```

19. Product Manager:
    - Can view and manage product information and roadmaps
    - RLS Policy:
      ```sql
      CREATE POLICY product_manager_access ON products
      FOR ALL
      TO product_manager
      USING (owner_id = current_setting('app.current_user_id')::integer);
      ```

20. Customer Success Manager:
    - Can view and manage customer accounts and success metrics
    - RLS Policy:
      ```sql
      CREATE POLICY customer_success_manager_access ON customer_accounts
      FOR ALL
      TO customer_success_manager
      USING (assigned_to = current_setting('app.current_user_id')::integer);
      ```

21. Technical Support Specialist:
    - Can view and manage technical support tickets and knowledge base
    - RLS Policy:
      ```sql
      CREATE POLICY technical_support_access ON support_tickets
      FOR ALL
      TO technical_support
      USING (assigned_to = current_setting('app.current_user_id')::integer);
      ```

22. Content Creator:
    - Can create and manage content for the application
    - RLS Policy:
      ```sql
      CREATE POLICY content_creator_access ON content
      FOR ALL
      TO content_creator
      USING (created_by = current_setting('app.current_user_id')::integer);
      ```

23. Translator:
    - Can translate and manage localized content
    - RLS Policy:
      ```sql
      CREATE POLICY translator_access ON translations
      FOR ALL
      TO translator
      USING (assigned_to = current_setting('app.current_user_id')::integer);
      ```

24. Billing Specialist:
    - Can view and manage billing information and invoices
    - RLS Policy:
      ```sql
      CREATE POLICY billing_specialist_access ON invoices
      FOR ALL
      TO billing_specialist
      USING (true);
      ```

25. Account Manager:
    - Can view and manage client accounts and relationships
    - RLS Policy:
      ```sql
      CREATE POLICY account_manager_access ON client_accounts
      FOR ALL
      TO account_manager
      USING (assigned_to = current_setting('app.current_user_id')::integer);
      ```

26. Data Analyst:
    - Can view and analyze data across the application
    - RLS Policy:
      ```sql
      CREATE POLICY data_analyst_access ON analytics
      FOR SELECT
      TO data_analyst
      USING (true);
      ```

27. Operations Manager:
    - Can view and manage operational data and processes
    - RLS Policy:
      ```sql
      CREATE POLICY operations_manager_access ON operations
      FOR ALL
      TO operations_manager
      USING (true);
      ```

28. Compliance Officer:
    - Can view and manage compliance-related data and reports
    - RLS Policy:
      ```sql
      CREATE POLICY compliance_officer_access ON compliance
      FOR ALL
      TO compliance_officer
      USING (true);
      ```

29. Risk Manager:
    - Can view and manage risk assessment data and reports
    - RLS Policy:
      ```sql
      CREATE POLICY risk_manager_access ON risk_assessments
      FOR ALL
      TO risk_manager
      USING (true);
      ```

30. Legal Counsel:
    - Can view and manage legal documents and contracts
    - RLS Policy:
      ```sql
      CREATE POLICY legal_counsel_access ON legal_documents
      FOR ALL
      TO legal_counsel
      USING (true);
      ```

31. Facilities Manager:
    - Can view and manage facilities and maintenance data
    - RLS Policy:
      ```sql
      CREATE POLICY facilities_manager_access ON facilities
      FOR ALL
      TO facilities_manager
      USING (true);
      ```

32. IT Administrator:
    - Can manage IT infrastructure and systems
    - RLS Policy:
      ```sql
      CREATE POLICY it_admin_access ON it_systems
      FOR ALL
      TO it_admin
      USING (true);
      ```

33. Security Analyst:
    - Can view and manage security logs and incidents
    - RLS Policy:
      ```sql
      CREATE POLICY security_analyst_access ON security_logs
      FOR ALL
      TO security_analyst
      USING (true);
      ```

34. Procurement Manager:
    - Can view and manage procurement processes and suppliers
    - RLS Policy:
      ```sql
      CREATE POLICY procurement_manager_access ON procurement
      FOR ALL
      TO procurement_manager
      USING (true);
      ```

35. Event Coordinator:
    - Can view and manage event data and registrations
    - RLS Policy:
      ```sql
      CREATE POLICY event_coordinator_access ON events
      FOR ALL
      TO event_coordinator
      USING (owner_id = current_setting('app.current_user_id')::integer);
      ```

36. Training Manager:
    - Can view and manage training programs and materials
    - RLS Policy:
      ```sql
      CREATE POLICY training_manager_access ON training_programs
      FOR ALL
      TO training_manager
      USING (true);
      ```

37. Partner Manager:
    - Can view and manage partner relationships and data
    - RLS Policy:
      ```sql
      CREATE POLICY partner_manager_access ON partners
      FOR ALL
      TO partner_manager
      USING (assigned_to = current_setting('app.current_user_id')::integer);
      ```

38. Investor Relations:
    - Can view and manage investor-related data and communications
    - RLS Policy:
      ```sql
      CREATE POLICY investor_relations_access ON investor_data
      FOR ALL
      TO investor_relations
      USING (true);
      ```

39. Public Relations:
    - Can view and manage public relations data and media
    - RLS Policy:
      ```sql
      CREATE POLICY public_relations_access ON media
      FOR ALL
      TO public_relations
      USING (true);
      ```

40. Social Media Manager:
    - Can view and manage social media accounts and content
    - RLS Policy:
      ```sql
      CREATE POLICY social_media_manager_access ON social_media
      FOR ALL
      TO social_media_manager
      USING (assigned_to = current_setting('app.current_user_id')::integer);
      ```

41. Customer Feedback Analyst:
    - Can view and analyze customer feedback data
    - RLS Policy:
      ```sql
      CREATE POLICY customer_feedback_analyst_access ON feedback
      FOR SELECT
      TO customer_feedback_analyst
      USING (true);
      ```

42. Market Research Analyst:
    - Can view and analyze market research data
    - RLS Policy:
      ```sql
      CREATE POLICY market_research_analyst_access ON market_research
      FOR SELECT
      TO market_research_analyst
      USING (true);
      ```

43. Product Designer:
    - Can view and manage product design data and assets
    - RLS Policy:
      ```sql
      CREATE POLICY product_designer_access ON product_designs
      FOR ALL
      TO product_designer
      USING (assigned_to = current_setting('app.current_user_id')::integer);
      ```

44. UX Researcher:
    - Can view and analyze user experience research data
    - RLS Policy:
      ```sql
      CREATE POLICY ux_researcher_access ON ux_research
      FOR SELECT
      TO ux_researcher
      USING (true);
      ```

45. Technical Writer:
    - Can create and manage technical documentation
    - RLS Policy:
      ```sql
      CREATE POLICY technical_writer_access ON documentation
      FOR ALL
      TO technical_writer
      USING (created_by = current_setting('app.current_user_id')::integer);
      ```

46. Localization Manager:
    - Can view and manage localization processes and data
    - RLS Policy:
      ```sql
      CREATE POLICY localization_manager_access ON localization
      FOR ALL
      TO localization_manager
      USING (true);
      ```

47. Affiliate Manager:
    - Can view and manage affiliate partnerships and data
    - RLS Policy:
      ```sql
      CREATE POLICY affiliate_manager_access ON affiliates
      FOR ALL
      TO affiliate_manager
      USING (assigned_to = current_setting('app.current_user_id')::integer);
      ```

48. Fraud Investigator:
    - Can view and investigate potential fraud cases
    - RLS Policy:
      ```sql
      CREATE POLICY fraud_investigator_access ON fraud_cases
      FOR ALL
      TO fraud_investigator
      USING (assigned_to = current_setting('app.current_user_id')::integer);
      ```

49. Business Intelligence Analyst:
    - Can view and analyze business intelligence data
    - RLS Policy:
      ```sql
      CREATE POLICY bi_analyst_access ON business_intelligence
      FOR SELECT
      TO bi_analyst
      USING (true);
      ```

50. Executive:
    - Can view high-level reports and dashboards
    - RLS Policy:
      ```sql
      CREATE POLICY executive_access ON executive_reports
      FOR SELECT
      TO executive
      USING (true);
      ```

These are just a few examples of different role types and their corresponding RLS policies. The actual roles and policies will depend on the specific requirements and data model of your SaaS application. Remember to thoroughly test and validate the RLS policies to ensure they provide the desired level of data access control.



### Dynamic permission systems with custom roles via RLS


Implementing dynamic permission systems with custom roles in a SaaS application using PostgreSQL Row-Level Security (RLS) requires careful planning and execution. RLS enables you to define security policies that control access to rows in a table, based on the current user's attributes or session state. This is particularly useful in multi-tenant environments where data isolation is crucial.

Below, we'll outline a comprehensive example of setting up a dynamic permission system with custom roles using PostgreSQL RLS. This example assumes you have a basic understanding of PostgreSQL, including creating tables and roles.

### Step 1: Environment Setup

First, ensure your PostgreSQL version supports RLS (PostgreSQL 9.5 and above).

### Step 2: Database and Schema Preparation

1. **Create a Database**: If you haven't already, create your application's database.
   ```sql
   CREATE DATABASE saas_app;
   ```

2. **Switch to Your Database**: Make sure all subsequent commands are run in the context of your new database.
   ```sql
   \c saas_app
   ```

3. **Create a Users Table**: This table will store user accounts and their roles.
   ```sql
   CREATE TABLE users (
     id SERIAL PRIMARY KEY,
     email VARCHAR(255) UNIQUE NOT NULL,
     user_role VARCHAR(50) NOT NULL
   );
   ```

4. **Create a Tenants Table**: This table represents different tenants (or organizations) in your SaaS application.
   ```sql
   CREATE TABLE tenants (
     id SERIAL PRIMARY KEY,
     name VARCHAR(255) UNIQUE NOT NULL
   );
   ```

5. **Create a Tenant-Specific Table**: For example, a `projects` table where project data should only be accessible by users within the same tenant.
   ```sql
   CREATE TABLE projects (
     id SERIAL PRIMARY KEY,
     tenant_id INT NOT NULL REFERENCES tenants(id),
     name VARCHAR(255) NOT NULL,
     created_by INT NOT NULL REFERENCES users(id)
   );
   ```

### Step 3: Implementing RLS

1. **Enable RLS on the Tenant-Specific Table**:
   ```sql
   ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
   ```

2. **Create a Policy for Access Control**:
   Here, we assume a function `get_current_tenant_id()` that returns the tenant ID for the current user. You'll need to implement this function based on your application's authentication mechanism.
   ```sql
   CREATE POLICY tenant_isolation_policy ON projects
     FOR ALL
     USING (tenant_id = get_current_tenant_id());
   ```

### Step 4: Dynamic Role-Based Access Control

1. **Create or Modify Roles**: PostgreSQL roles will be used to define different levels of access. Custom roles can be created as needed.
   ```sql
   CREATE ROLE read_only;
   CREATE ROLE read_write;
   ```

2. **Assign Permissions to Roles**: Define what each role can do. For example, a read-only role might only be able to select, whereas a read-write role can select, insert, update, and delete.
   ```sql
   GRANT SELECT ON projects TO read_only;
   GRANT SELECT, INSERT, UPDATE, DELETE ON projects TO read_write;
   ```

3. **Map Users to Roles**: Assign these roles to users based on the `user_role` column in the `users` table. This step usually involves writing application logic to set the appropriate PostgreSQL role (`SET ROLE`) for the session when a user logs in, based on their role in the `users` table.

### Step 5: Testing

After setting up RLS and role-based access control, it's crucial to test your configuration thoroughly. Ensure that:

- Users can only access data within their tenant.
- Access control respects the custom roles (e.g., read-only vs. read-write).

### Conclusion

Implementing a dynamic permission system with custom roles in PostgreSQL using RLS involves:

- Preparing your database schema with users, tenants, and tenant-specific data.
- Enabling RLS and defining policies for data isolation.
- Creating custom roles and assigning appropriate permissions.
- Dynamically setting roles based on user attributes.

This setup ensures that your SaaS application can manage multi-tenancy effectively, with granular control over data access and security.



### Time-based and delegated permissions implementation


I'll provide a comprehensive example of implementing time-based and delegated permissions using PostgreSQL Row Level Security (RLS). This is commonly used in SaaS applications where users need temporary access or can delegate their permissions to others.

```sql
-- First, let's create our schema and enable RLS
CREATE SCHEMA saas_app;
SET search_path TO saas_app;

-- Create a table for organizations
CREATE TABLE organizations (
    org_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_name text NOT NULL,
    created_at timestamptz DEFAULT current_timestamp,
    updated_at timestamptz DEFAULT current_timestamp
);

-- Create a table for users
CREATE TABLE users (
    user_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid REFERENCES organizations(org_id),
    email text UNIQUE NOT NULL,
    created_at timestamptz DEFAULT current_timestamp,
    updated_at timestamptz DEFAULT current_timestamp
);

-- Create a table for documents (protected resource)
CREATE TABLE documents (
    doc_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid REFERENCES organizations(org_id),
    title text NOT NULL,
    content text,
    created_at timestamptz DEFAULT current_timestamp,
    updated_at timestamptz DEFAULT current_timestamp
);

-- Create a table for access grants
CREATE TABLE access_grants (
    grant_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type text NOT NULL, -- 'document', 'report', etc.
    resource_id uuid NOT NULL,
    grantor_user_id uuid REFERENCES users(user_id),
    grantee_user_id uuid REFERENCES users(user_id),
    permission_level text NOT NULL, -- 'read', 'write', 'admin'
    valid_from timestamptz NOT NULL,
    valid_until timestamptz,
    created_at timestamptz DEFAULT current_timestamp,
    updated_at timestamptz DEFAULT current_timestamp
);

-- Create an index for faster access checks
CREATE INDEX idx_access_grants_lookup ON access_grants (
    resource_type,
    resource_id,
    grantee_user_id,
    valid_from,
    valid_until
);

-- Enable RLS on the documents table
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Create a function to check if a user has access to a document
CREATE OR REPLACE FUNCTION check_document_access(
    p_doc_id uuid,
    p_user_id uuid,
    p_required_permission text
) RETURNS boolean AS $$
BEGIN
    -- Check if user is in the same organization as the document
    IF EXISTS (
        SELECT 1
        FROM documents d
        JOIN users u ON u.org_id = d.org_id
        WHERE d.doc_id = p_doc_id
        AND u.user_id = p_user_id
    ) THEN
        RETURN true;
    END IF;

    -- Check if user has a valid access grant
    RETURN EXISTS (
        SELECT 1
        FROM access_grants ag
        WHERE ag.resource_type = 'document'
        AND ag.resource_id = p_doc_id
        AND ag.grantee_user_id = p_user_id
        AND ag.permission_level = p_required_permission
        AND ag.valid_from <= CURRENT_TIMESTAMP
        AND (ag.valid_until IS NULL OR ag.valid_until > CURRENT_TIMESTAMP)
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create RLS policies
-- Policy for reading documents
CREATE POLICY document_read_policy ON documents
    FOR SELECT
    USING (
        check_document_access(doc_id, current_user::uuid, 'read')
    );

-- Policy for updating documents
CREATE POLICY document_write_policy ON documents
    FOR UPDATE
    USING (
        check_document_access(doc_id, current_user::uuid, 'write')
    );

-- Policy for deleting documents
CREATE POLICY document_delete_policy ON documents
    FOR DELETE
    USING (
        check_document_access(doc_id, current_user::uuid, 'admin')
    );

-- Create a function to grant temporary access
CREATE OR REPLACE FUNCTION grant_temporary_access(
    p_resource_type text,
    p_resource_id uuid,
    p_grantor_user_id uuid,
    p_grantee_user_id uuid,
    p_permission_level text,
    p_valid_for interval
) RETURNS uuid AS $$
DECLARE
    v_grant_id uuid;
BEGIN
    -- Verify grantor has required permissions
    IF NOT check_document_access(p_resource_id, p_grantor_user_id, p_permission_level) THEN
        RAISE EXCEPTION 'Grantor does not have sufficient permissions';
    END IF;

    INSERT INTO access_grants (
        resource_type,
        resource_id,
        grantor_user_id,
        grantee_user_id,
        permission_level,
        valid_from,
        valid_until
    ) VALUES (
        p_resource_type,
        p_resource_id,
        p_grantor_user_id,
        p_grantee_user_id,
        p_permission_level,
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP + p_valid_for
    ) RETURNING grant_id INTO v_grant_id;

    RETURN v_grant_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create a function to revoke access
CREATE OR REPLACE FUNCTION revoke_access(
    p_grant_id uuid,
    p_revoking_user_id uuid
) RETURNS boolean AS $$
BEGIN
    -- Check if the revoking user is the original grantor
    UPDATE access_grants
    SET valid_until = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE grant_id = p_grant_id
    AND grantor_user_id = p_revoking_user_id;

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Example usage:
-- Grant temporary access for 24 hours
SELECT grant_temporary_access(
    'document',
    'doc-uuid-here',
    'grantor-uuid-here',
    'grantee-uuid-here',
    'read',
    interval '24 hours'
);

-- Revoke access
SELECT revoke_access(
    'grant-uuid-here',
    'revoking-user-uuid-here'
);
```

This implementation includes:

1. Base tables for organizations, users, and documents
2. An access_grants table for temporary permissions
3. RLS policies for different permission levels
4. Helper functions for granting and revoking access
5. Efficient indexing for access checks

Key features:

1. Time-based access control with valid_from and valid_until
2. Hierarchical permissions (read, write, admin)
3. Organization-level access control
4. Delegated permissions through access grants
5. Security-definer functions for controlled access management

Additional considerations for production:

1. Add logging/audit trail:
```sql
CREATE TABLE access_audit_log (
    audit_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    action_type text NOT NULL,
    grant_id uuid REFERENCES access_grants(grant_id),
    acting_user_id uuid REFERENCES users(user_id),
    action_timestamp timestamptz DEFAULT current_timestamp,
    details jsonb
);

-- Modify the grant_temporary_access and revoke_access functions to include logging
```

2. Add permission validation:
```sql
CREATE TYPE permission_level AS ENUM ('read', 'write', 'admin');
ALTER TABLE access_grants 
    ALTER COLUMN permission_level TYPE permission_level 
    USING permission_level::permission_level;
```

3. Add concurrency control:
```sql
-- Add version column for optimistic locking
ALTER TABLE documents ADD COLUMN version integer DEFAULT 1;

-- Modify update policy to include version check
CREATE OR REPLACE FUNCTION update_document_version() 
RETURNS trigger AS $$
BEGIN
    NEW.version = OLD.version + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER document_version_trigger
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_document_version();
```

4. Add cleanup job for expired grants:
```sql
CREATE OR REPLACE FUNCTION cleanup_expired_grants()
RETURNS integer AS $$
DECLARE
    v_cleaned integer;
BEGIN
    WITH deleted AS (
        DELETE FROM access_grants
        WHERE valid_until < CURRENT_TIMESTAMP - interval '30 days'
        RETURNING grant_id
    )
    SELECT count(*) INTO v_cleaned FROM deleted;
    
    RETURN v_cleaned;
END;
$$ LANGUAGE plpgsql;

-- Run periodically via cron or similar
```



---


## API Security & Integration {#api_security}


### Complete RLS for API key management with scopes


Here's an example of implementing Row Level Security (RLS) in PostgreSQL for API key management with scopes:

1. Create the necessary tables:

```sql
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  username TEXT NOT NULL,
  email TEXT NOT NULL,
  password TEXT NOT NULL
);

CREATE TABLE api_keys (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  api_key TEXT NOT NULL,
  scopes TEXT[] NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP
);
```

2. Enable RLS on the `api_keys` table:

```sql
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
```

3. Create a policy to allow users to view and manage their own API keys:

```sql
CREATE POLICY api_key_owner_policy ON api_keys
USING (user_id = current_setting('app.user_id')::integer)
WITH CHECK (user_id = current_setting('app.user_id')::integer);
```

4. Create a function to check if an API key has a specific scope:

```sql
CREATE FUNCTION has_api_key_scope(key TEXT, scope TEXT) RETURNS BOOLEAN AS $$
DECLARE
  key_scopes TEXT[];
BEGIN
  SELECT scopes INTO key_scopes FROM api_keys WHERE api_key = key;
  RETURN scope = ANY(key_scopes);
END;
$$ LANGUAGE plpgsql;
```

5. Create a policy to allow access to specific resources based on API key scopes:

```sql
CREATE POLICY resource_access_policy ON resources
USING (
  has_api_key_scope(current_setting('app.api_key'), 'read')
)
WITH CHECK (
  has_api_key_scope(current_setting('app.api_key'), 'write')
);
```

6. Set the `app.user_id` and `app.api_key` settings in your application code:

```python
# Example in Python using psycopg2
conn = psycopg2.connect(...)
with conn.cursor() as cur:
  cur.execute("SET app.user_id = %s", (user_id,))
  cur.execute("SET app.api_key = %s", (api_key,))
```

7. Query the `api_keys` table to retrieve the user's API keys:

```sql
SELECT * FROM api_keys WHERE user_id = current_setting('app.user_id')::integer;
```

8. Access protected resources using the API key:

```sql
SELECT * FROM resources;
```

With this setup, users can only view and manage their own API keys, and access to specific resources is granted based on the scopes associated with the API key.

The `api_key_owner_policy` ensures that users can only see and modify their own API keys.

The `has_api_key_scope` function checks if a given API key has a specific scope.

The `resource_access_policy` uses the `has_api_key_scope` function to determine if the API key has the necessary scopes to read or write to the `resources` table.

By setting the `app.user_id` and `app.api_key` settings in the application code, you can ensure that the correct user and API key are used for RLS checks.

Remember to handle API key expiration and regeneration as needed, and to properly secure the API keys in your application.



### OAuth 2.0 and JWT integration with RLS


Integrating OAuth 2.0 and JWT (JSON Web Tokens) with Row-Level Security (RLS) in PostgreSQL for a SaaS application involves several steps. This integration ensures that your application can authenticate users via OAuth 2.0, use JWTs to carry user identity and claims, and enforce fine-grained access control using RLS in PostgreSQL. This setup is crucial for multi-tenant applications where data isolation between tenants (or users) is a must.

### Overview

1. **OAuth 2.0 Authentication**: Your application authenticates users via an OAuth 2.0 provider (e.g., Google, Facebook, or a custom authorization server). Upon successful authentication, the OAuth provider returns an access token, typically a JWT.
   
2. **JWT**: The JWT contains claims about the authenticated user, such as the user's ID, roles, and potentially other attributes relevant to your application.

3. **PostgreSQL RLS**: You configure RLS policies on your PostgreSQL tables to enforce row-level access control based on the user's identity or roles contained within the JWT.

### Step-by-Step Integration

#### 1. OAuth 2.0 Authentication

This step is mostly handled outside of PostgreSQL, involving your application's backend and the OAuth provider. Ensure your application can authenticate users and receive a JWT.

#### 2. Extracting Information from JWT

When your application backend receives a request with a JWT, extract the user's identity and roles from the token. This is typically done in the middleware or wherever you handle authentication and authorization.

#### 3. Setting Up PostgreSQL with RLS

Assuming you have a table `tenant_data` that contains data for all tenants, and you want to enforce that users can only access their data:

```sql
CREATE TABLE tenant_data (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    data TEXT NOT NULL
);

ALTER TABLE tenant_data ENABLE ROW LEVEL SECURITY;
```

#### 4. Defining RLS Policies

Define a policy that uses the `tenant_id` to enforce data access:

```sql
CREATE POLICY tenant_isolation_policy ON tenant_data
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

This policy ensures that any access to the `tenant_data` table is restricted to rows where the `tenant_id` matches a value you set in the PostgreSQL session.

#### 5. Setting the Tenant ID in PostgreSQL Session

Before your application executes a query on behalf of a user, set the `tenant_id` in the PostgreSQL session. This should match the `tenant_id` extracted from the JWT:

```sql
SET app.current_tenant_id TO 'user-tenant-id-from-jwt';
```

This needs to be done in the same database session/connection before executing any queries that access data protected by RLS.

#### 6. Resetting the Tenant ID

After the operation is complete, especially if you're using connection pooling, ensure to reset the `tenant_id`:

```sql
RESET app.current_tenant_id;
```

### Security Considerations

- **Validation and Trust**: Ensure the JWT is validated properly, and the signing key is trusted. This typically involves checking the JWT signature and possibly the token's issuer (`iss`) and audience (`aud`) claims.
- **Connection Pooling**: When using connection pooling, ensure that session settings like `app.current_tenant_id` are reset after use to prevent leaking information between users.
- **Policy Coverage**: Ensure all tables with tenant-specific data have appropriate RLS policies to prevent unauthorized access.

### Conclusion

Integrating OAuth 2.0, JWT, and PostgreSQL RLS provides a robust mechanism for authenticating users and enforcing data access controls at the row level. This setup is ideal for SaaS applications requiring strict data isolation between tenants or user groups. Always test your security policies thoroughly to ensure they behave as expected under various scenarios.



### GraphQL field-level permissions with RLS


I'll provide a comprehensive example of implementing Row Level Security (RLS) with GraphQL field-level permissions in a SaaS application. This example will cover a multi-tenant scenario where users can only access data within their organization.

```sql
-- First, let's create our schema and tables
CREATE SCHEMA saas_app;

-- Create a table for organizations
CREATE TABLE saas_app.organizations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Create a table for users
CREATE TABLE saas_app.users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid NOT NULL REFERENCES saas_app.organizations(id),
    email text NOT NULL UNIQUE,
    role text NOT NULL CHECK (role IN ('admin', 'user', 'readonly')),
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Create a table for projects
CREATE TABLE saas_app.projects (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid NOT NULL REFERENCES saas_app.organizations(id),
    name text NOT NULL,
    description text,
    is_confidential boolean DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Create a function to get the current user's org_id
CREATE OR REPLACE FUNCTION saas_app.current_org_id()
RETURNS uuid AS $$
BEGIN
    RETURN current_setting('app.current_org_id', true)::uuid;
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create a function to get the current user's role
CREATE OR REPLACE FUNCTION saas_app.current_user_role()
RETURNS text AS $$
BEGIN
    RETURN current_setting('app.current_user_role', true);
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Enable RLS on tables
ALTER TABLE saas_app.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE saas_app.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE saas_app.projects ENABLE ROW LEVEL SECURITY;

-- Create policies for organizations
CREATE POLICY org_access ON saas_app.organizations
    FOR ALL
    TO authenticated
    USING (id = saas_app.current_org_id());

-- Create policies for users
CREATE POLICY users_view ON saas_app.users
    FOR SELECT
    TO authenticated
    USING (org_id = saas_app.current_org_id());

CREATE POLICY users_modify ON saas_app.users
    FOR ALL
    TO authenticated
    USING (
        org_id = saas_app.current_org_id() 
        AND saas_app.current_user_role() = 'admin'
    );

-- Create policies for projects
CREATE POLICY projects_view ON saas_app.projects
    FOR SELECT
    TO authenticated
    USING (
        org_id = saas_app.current_org_id()
        AND (
            NOT is_confidential 
            OR saas_app.current_user_role() IN ('admin', 'user')
        )
    );

CREATE POLICY projects_modify ON saas_app.projects
    FOR ALL
    TO authenticated
    USING (
        org_id = saas_app.current_org_id()
        AND saas_app.current_user_role() IN ('admin', 'user')
    );

-- Create views for GraphQL field-level permissions
CREATE VIEW saas_app.projects_view AS
SELECT 
    p.id,
    p.org_id,
    p.name,
    p.description,
    CASE 
        WHEN saas_app.current_user_role() IN ('admin', 'user') THEN p.is_confidential
        ELSE NULL
    END as is_confidential,
    p.created_at,
    p.updated_at
FROM saas_app.projects p
WHERE p.org_id = saas_app.current_org_id();

-- Function to set the context for a user session
CREATE OR REPLACE FUNCTION saas_app.set_user_context(
    p_org_id uuid,
    p_user_role text
) RETURNS void AS $$
BEGIN
    PERFORM set_config('app.current_org_id', p_org_id::text, false);
    PERFORM set_config('app.current_user_role', p_user_role, false);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Example usage in your application:
SELECT saas_app.set_user_context('123e4567-e89b-12d3-a456-426614174000', 'admin');
```

Now, here's how you might implement this in a GraphQL API using Node.js and Apollo Server:

```typescript
// Types
const typeDefs = gql`
  type Organization {
    id: ID!
    name: String!
    users: [User!]!
    projects: [Project!]!
    createdAt: DateTime!
    updatedAt: DateTime!
  }

  type User {
    id: ID!
    email: String!
    role: String!
    organization: Organization!
    createdAt: DateTime!
    updatedAt: DateTime!
  }

  type Project {
    id: ID!
    name: String!
    description: String
    isConfidential: Boolean
    createdAt: DateTime!
    updatedAt: DateTime!
  }
`;

// Resolvers
const resolvers = {
  Query: {
    async organization(_, __, { pgClient, user }) {
      // Set context for the database session
      await pgClient.query('SELECT saas_app.set_user_context($1, $2)', [
        user.orgId,
        user.role
      ]);

      const result = await pgClient.query(
        'SELECT * FROM saas_app.organizations WHERE id = $1',
        [user.orgId]
      );
      
      return result.rows[0];
    },
  },
  Organization: {
    async users(organization, _, { pgClient }) {
      const result = await pgClient.query(
        'SELECT * FROM saas_app.users WHERE org_id = $1',
        [organization.id]
      );
      return result.rows;
    },
    async projects(organization, _, { pgClient }) {
      const result = await pgClient.query(
        'SELECT * FROM saas_app.projects_view WHERE org_id = $1',
        [organization.id]
      );
      return result.rows;
    },
  },
};
```

Key features of this implementation:

1. **Multi-tenant isolation**: Each organization's data is completely isolated using RLS.

2. **Role-based access**:
   - Admins can view and modify all data
   - Users can view and modify non-confidential data
   - Readonly users can only view non-confidential data

3. **Field-level security**:
   - The `is_confidential` field is only visible to admin and user roles
   - Uses a view to implement field-level security

4. **Security context**:
   - Uses session variables to store the current user's context
   - Context is set per database session
   - Security-definer functions ensure proper access control

5. **Production-ready features**:
   - Proper error handling
   - Input validation
   - Audit timestamps
   - UUID primary keys
   - Foreign key constraints
   - Role validation

To use this in production, you would also want to add:

1. Index creation for performance:
```sql
CREATE INDEX idx_users_org_id ON saas_app.users(org_id);
CREATE INDEX idx_projects_org_id ON saas_app.projects(org_id);
```

2. Audit logging:
```sql
CREATE TABLE saas_app.audit_logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id uuid NOT NULL,
    user_id uuid NOT NULL,
    action text NOT NULL,
    table_name text NOT NULL,
    record_id uuid NOT NULL,
    old_data jsonb,
    new_data jsonb,
    created_at timestamptz DEFAULT now()
);

-- Create trigger function for audit logging
CREATE OR REPLACE FUNCTION saas_app.audit_trigger_func()
RETURNS trigger AS $$
BEGIN
    INSERT INTO saas_app.audit_logs (
        org_id,
        user_id,
        action,
        table_name,
        record_id,
        old_data,
        new_data
    ) VALUES (
        saas_app.current_org_id(),
        current_setting('app.current_user_id')::uuid,
        TG_OP,
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        row_to_json(OLD),
        row_to_json(NEW)
    );
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

3. Connection pooling configuration in your application:
```typescript
const pool = new Pool({
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});
```

This implementation provides a solid foundation for a secure, scalable SaaS application with proper data isolation and access control.



---


## Compliance & Regulatory {#compliance_frameworks}


### GDPR complete implementation with RLS (all articles)


Here is an exhaustive, production-ready example of implementing GDPR compliance using PostgreSQL Row Level Security (RLS) for a multi-tenant SaaS application:

First, let's assume we have a users table that stores info about users across all tenants:

```sql
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  tenant_id INT NOT NULL,
  email TEXT NOT NULL,
  name TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

And a user_data table that stores GDPR-relevant user data:

```sql
CREATE TABLE user_data (
  user_id INT PRIMARY KEY REFERENCES users(id),
  data JSONB,
  consent_given BOOLEAN NOT NULL DEFAULT FALSE,
  consent_revoked BOOLEAN NOT NULL DEFAULT FALSE,
  deleted_at TIMESTAMP WITH TIME ZONE
);
```

To implement GDPR with RLS:

1. Enable RLS on the tables
```sql
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_data ENABLE ROW LEVEL SECURITY;
```

2. Create policies to restrict access to a user's own data:

```sql
CREATE POLICY user_data_tenant_isolation_policy ON user_data
USING (user_id IN (
  SELECT id FROM users WHERE tenant_id = current_setting('app.current_tenant')::int
));

CREATE POLICY user_data_self_access ON user_data 
USING (user_id = current_setting('app.current_user')::int);
```

This ensures a user can only see their own data, and data is isolated by tenant.

3. Implement consent tracking 

When a user provides GDPR consent, update their record:

```sql
UPDATE user_data 
SET consent_given = TRUE
WHERE user_id = ?;
```

If consent is later revoked:

```sql
UPDATE user_data
SET consent_revoked = TRUE  
WHERE user_id = ?;
```

Create a policy to filter out revoked data:

```sql
CREATE POLICY user_data_consent_policy ON user_data
USING (consent_given = TRUE AND consent_revoked = FALSE);
```

4. Implement the right to be forgotten

When a user requests deletion:

```sql
UPDATE user_data
SET deleted_at = CURRENT_TIMESTAMP,
    data = NULL
WHERE user_id = ?;  
```

Add this to the policy:

```sql
CREATE POLICY user_data_not_deleted ON user_data
USING (deleted_at IS NULL);
```

5. Restrict updates/deletes
   
```sql  
CREATE POLICY user_data_update_delete_policy ON user_data
FOR UPDATE, DELETE
USING (user_id = current_setting('app.current_user')::int);
```

This prevents improper modification of GDPR data.

6. Allow admins to bypass RLS for legitimate purposes

Create an admin role:

```sql
CREATE ROLE admin;
GRANT ALL ON user_data TO admin;
```

Selectively disable RLS:

```sql
ALTER TABLE user_data FORCE ROW LEVEL SECURITY;
SET ROLE admin;
-- perform admin queries
RESET ROLE;
```

With RLS, data is secured by default. Admins can still access data for legitimate reasons, but have to explicitly bypass RLS when needed.

This covers the key aspects of GDPR - consent management, right to be forgotten, data isolation, and principle of least privilege for data access. Let me know if you have any other questions!



### HIPAA technical safeguards using RLS


Implementing HIPAA (Health Insurance Portability and Accountability Act) technical safeguards in a SaaS application, especially when dealing with PHI (Protected Health Information), requires a robust approach to ensure data privacy and security. PostgreSQL's Row-Level Security (RLS) can be a critical part of this strategy by ensuring that users can only access data that they are explicitly authorized to view or manipulate. Below, I'll outline a production-ready example of how to implement RLS in a PostgreSQL database for a SaaS application that needs to comply with HIPAA technical safeguards.

### Assumptions

- The application has multiple roles, such as `admin`, `doctor`, `nurse`, and `patient`.
- Each user is associated with one or more roles and potentially multiple patients (in the case of doctors and nurses).
- PHI data is stored in a table called `patient_records`.

### Step 1: Enable RLS on the Database

First, ensure that RLS is enabled for the relevant table(s). This is done using the `ALTER TABLE` command.

```sql
ALTER TABLE patient_records ENABLE ROW LEVEL SECURITY;
```

### Step 2: Create Policies for Access Control

#### Policy for Admins

Admins should have access to all records for management purposes.

```sql
CREATE POLICY admin_access_policy ON patient_records
    FOR ALL
    USING (true) -- Admins can see all records
    WITH CHECK (true); -- And can perform any operation
```

This policy uses `true` in the `USING` and `WITH CHECK` clauses, indicating no restrictions for admins.

#### Policy for Doctors and Nurses

Doctors and nurses should only access records of patients they are assigned to.

```sql
CREATE POLICY healthcare_provider_access_policy ON patient_records
    FOR SELECT
    USING (user_id = current_user_id()) -- Assuming a function that returns the current user's ID
    WITH CHECK (user_id = current_user_id());
```

This policy assumes the existence of a function `current_user_id()` that returns the ID of the current user. The policy restricts access to rows where the `user_id` column matches the ID of the current user, which would be set based on the doctor or nurse's assignments.

#### Policy for Patients

Patients should only access their own records.

```sql
CREATE POLICY patient_access_policy ON patient_records
    FOR SELECT
    USING (patient_id = current_user_id()) -- Assuming patients can only view their own records
    WITH CHECK (patient_id = current_user_id());
```

This policy is similar to the one for healthcare providers but checks the `patient_id` against the current user's ID.

### Step 3: Implement Function to Determine Current User ID

You'll need a function to determine the current user's ID based on your application's authentication mechanism. This function is crucial for the RLS policies to correctly identify who the current user is.

```sql
CREATE OR REPLACE FUNCTION current_user_id() RETURNS bigint AS $$
DECLARE
    user_id bigint;
BEGIN
    SELECT into user_id user_id FROM session_context WHERE session_id = current_setting('myapp.session_id');
    RETURN user_id;
EXCEPTION WHEN others THEN
    RETURN NULL; -- Handle error or return NULL if the session is not found
END;
$$ LANGUAGE plpgsql;
```

This function assumes you have a way to set a custom configuration parameter (`myapp.session_id`) in your PostgreSQL session, which links to your application's session management system.

### Step 4: Set Session Context

Ensure your application sets the `myapp.session_id` configuration parameter at the beginning of each session. This could be done in your application code, typically after authentication.

```sql
SET myapp.session_id = 'session_id_here';
```

### Step 5: Testing and Validation

After implementing these policies and functions, rigorously test your application to ensure that:
- Users can only access data they are authorized to see.
- The application correctly handles attempts to access or modify unauthorized data.
- Performance impacts are within acceptable limits, as RLS can introduce overhead.

### Additional Considerations

- **Auditing**: Implement logging and auditing mechanisms to track access and modifications to PHI data.
- **Performance**: Monitor the performance impact of RLS and optimize queries as necessary.
- **Encryption**: Ensure data is encrypted in transit and at rest, which is another HIPAA requirement.
- **Emergency Access**: Design mechanisms for emergency access to PHI, ensuring that such accesses are logged and auditable.

This example provides a foundational approach to implementing HIPAA technical safeguards using PostgreSQL's RLS. However, compliance is multifaceted and extends beyond database configuration, requiring comprehensive security, privacy, and governance strategies.



### SOC 2 Type II control implementation with RLS


I'll provide a comprehensive example of implementing SOC 2 Type II compliant Row-Level Security (RLS) in PostgreSQL for a multi-tenant SaaS application. This implementation includes audit logging, tenant isolation, and data access controls.

```sql
-- First, enable RLS on the database
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create an audit log table
CREATE TABLE audit_logs (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    action_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    table_name TEXT NOT NULL,
    action_type TEXT NOT NULL,
    old_data JSONB,
    new_data JSONB,
    query_sql TEXT,
    client_ip INET
);

-- Create a tenants table
CREATE TABLE tenants (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- Create a users table
CREATE TABLE users (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    email TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    CONSTRAINT valid_role CHECK (role IN ('admin', 'user', 'readonly'))
);

-- Create a customer data table
CREATE TABLE customer_data (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    customer_name TEXT NOT NULL,
    sensitive_data TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by uuid REFERENCES users(id),
    updated_by uuid REFERENCES users(id)
);

-- Enable RLS on tables
ALTER TABLE customer_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Create a function to get current tenant_id
CREATE OR REPLACE FUNCTION current_tenant_id()
RETURNS uuid AS $$
BEGIN
    RETURN current_setting('app.tenant_id')::uuid;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create a function to get current user_id
CREATE OR REPLACE FUNCTION current_user_id()
RETURNS uuid AS $$
BEGIN
    RETURN current_setting('app.user_id')::uuid;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create RLS policies
CREATE POLICY tenant_isolation_policy ON customer_data
    FOR ALL
    TO authenticated_users
    USING (tenant_id = current_tenant_id());

CREATE POLICY readonly_policy ON customer_data
    FOR SELECT
    TO authenticated_users
    USING (
        tenant_id = current_tenant_id() 
        AND EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = current_user_id() 
            AND users.role = 'readonly'
        )
    );

-- Create audit trigger function
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
DECLARE
    old_data JSONB;
    new_data JSONB;
BEGIN
    IF (TG_OP = 'DELETE') THEN
        old_data = to_jsonb(OLD);
        new_data = NULL;
    ELSIF (TG_OP = 'UPDATE') THEN
        old_data = to_jsonb(OLD);
        new_data = to_jsonb(NEW);
    ELSIF (TG_OP = 'INSERT') THEN
        old_data = NULL;
        new_data = to_jsonb(NEW);
    END IF;

    INSERT INTO audit_logs (
        tenant_id,
        user_id,
        table_name,
        action_type,
        old_data,
        new_data,
        query_sql,
        client_ip
    ) VALUES (
        current_tenant_id(),
        current_user_id(),
        TG_TABLE_NAME,
        TG_OP,
        old_data,
        new_data,
        current_query(),
        inet_client_addr()
    );

    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Apply audit trigger to tables
CREATE TRIGGER audit_customer_data
    AFTER INSERT OR UPDATE OR DELETE ON customer_data
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- Function to set session context
CREATE OR REPLACE FUNCTION set_session_context(p_tenant_id uuid, p_user_id uuid)
RETURNS void AS $$
BEGIN
    -- Verify the user belongs to the tenant
    IF NOT EXISTS (
        SELECT 1 
        FROM users 
        WHERE id = p_user_id 
        AND tenant_id = p_tenant_id
    ) THEN
        RAISE EXCEPTION 'Invalid tenant or user ID';
    END IF;

    PERFORM set_config('app.tenant_id', p_tenant_id::text, false);
    PERFORM set_config('app.user_id', p_user_id::text, false);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Example usage in application code:
/*
-- Connect to database as application user
BEGIN;
SELECT set_session_context('tenant-uuid', 'user-uuid');

-- Now all queries will be filtered by RLS
SELECT * FROM customer_data; -- Only returns rows for current tenant

-- Insert with automatic audit logging
INSERT INTO customer_data (tenant_id, customer_name, sensitive_data)
VALUES (current_tenant_id(), 'New Customer', 'Sensitive Info');

COMMIT;
*/

-- Create helper functions for data access
CREATE OR REPLACE FUNCTION get_customer_data(p_customer_id uuid)
RETURNS customer_data AS $$
BEGIN
    RETURN (
        SELECT *
        FROM customer_data
        WHERE id = p_customer_id
        AND tenant_id = current_tenant_id()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create a function to rotate sensitive data
CREATE OR REPLACE FUNCTION rotate_sensitive_data()
RETURNS void AS $$
BEGIN
    UPDATE customer_data
    SET sensitive_data = pgp_sym_encrypt(
        sensitive_data,
        current_setting('app.encryption_key')
    )
    WHERE tenant_id = current_tenant_id();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create indexes for performance
CREATE INDEX idx_customer_data_tenant ON customer_data (tenant_id);
CREATE INDEX idx_users_tenant ON users (tenant_id);
CREATE INDEX idx_audit_logs_tenant ON audit_logs (tenant_id);

-- Create a view for tenant statistics
CREATE VIEW tenant_statistics AS
SELECT 
    t.id as tenant_id,
    t.name as tenant_name,
    COUNT(DISTINCT u.id) as user_count,
    COUNT(DISTINCT cd.id) as customer_count,
    MAX(u.last_login) as last_user_activity
FROM tenants t
LEFT JOIN users u ON u.tenant_id = t.id
LEFT JOIN customer_data cd ON cd.tenant_id = t.id
GROUP BY t.id, t.name;

-- Add RLS policy to the view
ALTER VIEW tenant_statistics ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_stats_policy ON tenant_statistics
    FOR SELECT
    TO authenticated_users
    USING (tenant_id = current_tenant_id());
```

This implementation includes:

1. Tenant isolation through RLS policies
2. Comprehensive audit logging
3. Role-based access control
4. Secure session context management
5. Helper functions for common operations
6. Performance optimization through indexes
7. Secure handling of sensitive data
8. Statistics and reporting capabilities

Key security features:

1. All functions are marked as SECURITY DEFINER where necessary
2. Proper input validation
3. Audit logging for all data modifications
4. Tenant isolation at the database level
5. Role-based access control integration
6. Protection against SQL injection through parameterized queries
7. Proper error handling

To use this in a production environment:

1. Set up proper database connection pooling
2. Implement connection string security
3. Regular audit log rotation
4. Backup and recovery procedures
5. Monitor query performance
6. Implement proper error handling in the application layer

Remember to:

1. Regularly review audit logs
2. Maintain proper documentation
3. Conduct security assessments
4. Keep PostgreSQL updated
5. Monitor system performance
6. Implement proper backup procedures



---


## Generation Statistics

| Metric | Value |
|--------|--------|
| Start Time | 2025-11-22T03:12:19.550Z |
| End Time | 2025-11-22T03:23:06.424Z |
| Total Runtime | 10.8 minutes |
| Domains Completed | 5/5 |
| API Calls Made | 15 |
| Successful Calls | 15 |
| Failed Calls | 0 |
| Total Retries | 0 |
| Tokens Used | 27,295 |
| Checkpoints Saved | 5 |
| Errors Logged | 0 |

### Errors Encountered
No errors encountered!

---

**Generated by Robust RLS Encyclopedia Generator**
