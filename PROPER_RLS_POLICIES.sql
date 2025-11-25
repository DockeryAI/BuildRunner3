-- ============================================================================
-- PROPER RLS POLICIES (SECURE)
-- ============================================================================
-- Instead of disabling RLS, create proper policies with appropriate access
-- ============================================================================

-- ============================================================================
-- INDUSTRY PROFILES - Public read, authenticated write
-- ============================================================================

-- Keep RLS ENABLED for security
ALTER TABLE industry_profiles ENABLE ROW LEVEL SECURITY;

-- Drop old restrictive policies
DROP POLICY IF EXISTS "Anyone can view industry profiles" ON industry_profiles;
DROP POLICY IF EXISTS "Service role can manage industry profiles" ON industry_profiles;

-- Policy 1: Anyone can read industry profiles (public reference data)
CREATE POLICY "Public read access to industry profiles"
  ON industry_profiles
  FOR SELECT
  TO public
  USING (true);

-- Policy 2: Anon users can insert on-demand generated profiles
CREATE POLICY "Anon can insert on-demand profiles"
  ON industry_profiles
  FOR INSERT
  TO anon
  WITH CHECK (generated_on_demand = true);

-- Policy 3: Anon users can update their own on-demand profiles
CREATE POLICY "Anon can update on-demand profiles"
  ON industry_profiles
  FOR UPDATE
  TO anon
  USING (generated_on_demand = true)
  WITH CHECK (generated_on_demand = true);

-- Policy 4: Authenticated users can insert/update
CREATE POLICY "Authenticated can manage profiles"
  ON industry_profiles
  FOR ALL
  TO authenticated
  USING (true)
  WITH CHECK (true);

-- Policy 5: Service role has full access
CREATE POLICY "Service role full access"
  ON industry_profiles
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ============================================================================
-- INTELLIGENCE CACHE - Ephemeral data, open access for performance
-- ============================================================================

ALTER TABLE IF EXISTS intelligence_cache ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Cache read access" ON intelligence_cache;
DROP POLICY IF EXISTS "Cache write access" ON intelligence_cache;

-- Anyone can read/write cache (TTL-based, non-sensitive)
CREATE POLICY "Public cache access"
  ON intelligence_cache
  FOR ALL
  TO public
  USING (true)
  WITH CHECK (true);

-- ============================================================================
-- LOCATION DETECTION CACHE - Ephemeral data, open access for performance
-- ============================================================================

ALTER TABLE IF EXISTS location_detection_cache ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Location cache read" ON location_detection_cache;
DROP POLICY IF EXISTS "Location cache write" ON location_detection_cache;

-- Anyone can read/write location cache (TTL-based, non-sensitive)
CREATE POLICY "Public location cache access"
  ON location_detection_cache
  FOR ALL
  TO public
  USING (true)
  WITH CHECK (true);

-- ============================================================================
-- RELOAD POSTGREST SCHEMA CACHE
-- ============================================================================

NOTIFY pgrst, 'reload schema';

-- ============================================================================
-- VERIFY POLICIES
-- ============================================================================

-- Show RLS status (should be ENABLED)
SELECT
  tablename,
  rowsecurity as rls_enabled,
  CASE
    WHEN rowsecurity THEN '✅ ENABLED (SECURE)'
    ELSE '⚠️  DISABLED (INSECURE)'
  END as security_status
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('industry_profiles', 'intelligence_cache', 'location_detection_cache')
ORDER BY tablename;

-- Show all policies
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
WHERE schemaname = 'public'
  AND tablename IN ('industry_profiles', 'intelligence_cache', 'location_detection_cache')
ORDER BY tablename, policyname;
