-- ============================================================================
-- COMPLETE RLS FIX + POSTGREST RELOAD
-- ============================================================================
-- This will disable RLS and force PostgREST to reload the schema cache
-- ============================================================================

-- Step 1: Disable RLS on industry_profiles
ALTER TABLE industry_profiles DISABLE ROW LEVEL SECURITY;

-- Step 2: Grant all necessary permissions to anon users
GRANT SELECT, INSERT, UPDATE, DELETE ON industry_profiles TO anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON industry_profiles TO authenticated;

-- Step 3: Also grant to public (broader access for demo)
GRANT SELECT, INSERT, UPDATE ON industry_profiles TO public;

-- Step 4: Fix cache tables too while we're at it
ALTER TABLE IF EXISTS intelligence_cache DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS location_detection_cache DISABLE ROW LEVEL SECURITY;

GRANT SELECT, INSERT, UPDATE, DELETE ON intelligence_cache TO anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON intelligence_cache TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON location_detection_cache TO anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON location_detection_cache TO authenticated;

-- Step 5: Reload PostgREST schema cache (CRITICAL!)
NOTIFY pgrst, 'reload schema';

-- Step 6: Verify the fix worked
SELECT
  tablename,
  rowsecurity as rls_enabled,
  CASE
    WHEN rowsecurity THEN '❌ STILL ENABLED (BAD)'
    ELSE '✅ DISABLED (GOOD)'
  END as status
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('industry_profiles', 'intelligence_cache', 'location_detection_cache')
ORDER BY tablename;

-- Show permissions
SELECT
  grantee,
  table_name,
  string_agg(privilege_type, ', ' ORDER BY privilege_type) as privileges
FROM information_schema.table_privileges
WHERE table_schema = 'public'
  AND table_name IN ('industry_profiles', 'intelligence_cache', 'location_detection_cache')
  AND grantee IN ('anon', 'authenticated', 'public')
GROUP BY grantee, table_name
ORDER BY table_name, grantee;
