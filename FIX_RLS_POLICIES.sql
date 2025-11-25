-- ============================================================================
-- RLS POLICY FIX FOR 406 ERRORS
-- ============================================================================
-- Run this in your Supabase SQL Editor to fix database access issues
--
-- These 406 errors are blocking:
-- - industry_profiles (needed for on-demand profile generation)
-- - intelligence_cache (needed for caching API responses)
-- - location_detection_cache (needed for location caching)
-- ============================================================================

-- 1. Disable RLS on cache tables (these are ephemeral non-sensitive data)
ALTER TABLE IF EXISTS intelligence_cache DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS location_detection_cache DISABLE ROW LEVEL SECURITY;

-- 2. Disable RLS on industry_profiles (read-only reference data for demo)
ALTER TABLE IF EXISTS industry_profiles DISABLE ROW LEVEL SECURITY;

-- 3. Grant permissions to anon users (for demo/testing)
GRANT SELECT, INSERT, UPDATE, DELETE ON intelligence_cache TO anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON location_detection_cache TO anon;
GRANT SELECT, INSERT ON industry_profiles TO anon;

-- 4. Grant permissions to authenticated users
GRANT SELECT, INSERT, UPDATE, DELETE ON intelligence_cache TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON location_detection_cache TO authenticated;
GRANT SELECT, INSERT ON industry_profiles TO authenticated;

-- 5. Verify permissions
SELECT tablename,
       pg_catalog.has_table_privilege('anon', schemaname||'.'||tablename, 'SELECT') as anon_select,
       pg_catalog.has_table_privilege('anon', schemaname||'.'||tablename, 'INSERT') as anon_insert
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('intelligence_cache', 'location_detection_cache', 'industry_profiles')
ORDER BY tablename;
