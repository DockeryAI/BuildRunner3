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

## NEW SECTION: Quick Solutions from Supabase Community

### Common 401 Unauthorized Fixes

Based on extensive community reports, here are proven solutions for 401 errors:

#### Solution 1: Ensure Both USING and WITH CHECK for INSERT Operations

When using Supabase client with `.select()` after insert:

```sql
-- WRONG: Only WITH CHECK
CREATE POLICY "insert_policy"
ON table
FOR INSERT
TO anon
WITH CHECK (true);

-- CORRECT: Both clauses needed when returning data
CREATE POLICY "insert_policy"
ON table
FOR INSERT
TO anon
WITH CHECK (true)  -- What can be inserted
USING (true);      -- What can be selected after insert
```

#### Solution 2: Test with Service Key First

If getting RLS errors with anon key, temporarily test with service key:

```javascript
// If this works with service key but not anon key, it's definitely RLS
const supabase = createClient(url, SERVICE_KEY);
```

#### Solution 3: Disable RLS Temporarily to Isolate Issue

```sql
-- Temporarily disable to test if it's RLS or something else
ALTER TABLE your_table DISABLE ROW LEVEL SECURITY;

-- Test your operation
-- If it works, the issue is definitely RLS policies

-- Re-enable after testing
ALTER TABLE your_table ENABLE ROW LEVEL SECURITY;
```

#### Solution 4: The Nuclear Option - Full Reset

When nothing else works:

```sql
-- Complete reset of table RLS
BEGIN;

-- 1. Disable RLS
ALTER TABLE your_table DISABLE ROW LEVEL SECURITY;

-- 2. Drop ALL policies
DO $$
DECLARE pol record;
BEGIN
  FOR pol IN SELECT policyname FROM pg_policies WHERE tablename = 'your_table' LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON your_table', pol.policyname);
  END LOOP;
END $$;

-- 3. Re-enable RLS
ALTER TABLE your_table ENABLE ROW LEVEL SECURITY;

-- 4. Create simple permissive policy to start
CREATE POLICY "temporary_allow_all"
ON your_table
FOR ALL
TO public
USING (true)
WITH CHECK (true);

-- 5. Grant all permissions
GRANT ALL ON your_table TO anon, authenticated, public;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, public;

COMMIT;

-- Now gradually add restrictions back
```

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

### NEW: Pitfall 1b: Missing USING Clause When Returning Data

**Symptom:** 401 Unauthorized on INSERT operations even with permissive WITH CHECK

**Problem:**
```sql
CREATE POLICY "Allow anon inserts"
ON your_table
FOR INSERT
TO anon
WITH CHECK (true);  -- Only controls what can be inserted

-- If using .select() or returning data, USING is also needed!
```

**Solution:**
```sql
CREATE POLICY "Allow anon inserts"
ON your_table
FOR INSERT
TO anon
WITH CHECK (true)  -- Controls what can be inserted
USING (true);      -- Controls what can be selected after insert
```

**Prevention:** When INSERT operations return data (common in Supabase), include both USING and WITH CHECK clauses.

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

### NEW: Pitfall 13: Prisma Migrations Wiping Grants

**Symptom:** 401/403 errors after running Prisma migrations

**Problem:** Prisma during migrations often wipes out Postgres grants to the public schema.

**Solution:**
```sql
-- Re-grant permissions after Prisma migrations
GRANT USAGE ON SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role;
```

**Prevention:** Add these grants to a post-migration script or include in your deployment process.

### NEW: Pitfall 14: Storage RLS Requirements

**Symptom:** Cannot upload files to Supabase Storage despite having table access

**Problem:** Storage requires specific RLS policies on the `storage.objects` table

**Solution:**
```sql
-- Enable RLS on storage.objects
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- For uploading
CREATE POLICY "Users can upload"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'your-bucket' AND owner = auth.uid());

-- For overwriting (upsert)
CREATE POLICY "Users can update own files"
ON storage.objects
FOR UPDATE
TO authenticated
USING (owner = auth.uid())
WITH CHECK (owner = auth.uid());

CREATE POLICY "Users can view own files"
ON storage.objects
FOR SELECT
TO authenticated
USING (owner = auth.uid());
```

**Prevention:** Remember that Storage has its own RLS separate from your tables.

### NEW: Pitfall 15: Role Confusion - 'anon' vs 'public'

**Symptom:** Policy doesn't work for anonymous users when using TO anon

**Problem:** The `public` role includes ALL other roles (anon, authenticated, etc.)

**Solution:**
```sql
-- For truly public access (both anon AND authenticated)
CREATE POLICY "everyone_can_read"
ON table
FOR SELECT
TO public  -- Includes anon, authenticated, and all other roles
USING (true);

-- For ONLY anonymous users (rare)
CREATE POLICY "only_anon"
ON table
FOR SELECT
TO anon  -- ONLY anon, authenticated users won't match
USING (true);
```

**Key Point:** A policy with `TO anon` means authenticated users will NOT have access through that policy. Use `TO public` for universal access.

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

**Document Version:** 1.1
**Last Updated:** 2025-11-22
**Feedback:** Report issues or suggest improvements

### Version 1.1 Updates (2025-11-22)

Added insights from Supabase community and official documentation:

1. **NEW Pitfall 1b**: Missing USING clause when INSERT operations return data
2. **NEW Pitfall 13**: Prisma migrations wiping PostgreSQL grants
3. **NEW Pitfall 14**: Supabase Storage RLS requirements
4. **NEW Pitfall 15**: Role confusion between 'anon' and 'public'
5. **NEW Section**: Quick Solutions from Supabase Community
   - Solution for INSERT operations that return data (.select())
   - Testing methodology with service keys
   - Nuclear reset option for stubborn RLS issues
   - Temporary isolation techniques

Key insights added:
- INSERT policies may need both USING and WITH CHECK when returning data
- The 'public' role includes all other roles (anon, authenticated, etc.)
- Prisma migrations can break RLS by wiping grants
- Storage has its own RLS separate from regular tables
- Community-proven troubleshooting approaches for 401 errors

