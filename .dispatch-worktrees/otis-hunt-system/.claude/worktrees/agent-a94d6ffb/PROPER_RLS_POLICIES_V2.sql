-- ============================================================================
-- PROPER RLS POLICIES V2 (Handles existing policies)
-- ============================================================================

-- ============================================================================
-- INDUSTRY PROFILES
-- ============================================================================

ALTER TABLE industry_profiles ENABLE ROW LEVEL SECURITY;

-- Drop ALL existing policies first
DROP POLICY IF EXISTS "Public read access to industry profiles" ON industry_profiles;
DROP POLICY IF EXISTS "Anon can insert on-demand profiles" ON industry_profiles;
DROP POLICY IF EXISTS "Anon can update on-demand profiles" ON industry_profiles;
DROP POLICY IF EXISTS "Authenticated can manage profiles" ON industry_profiles;
DROP POLICY IF EXISTS "Service role full access" ON industry_profiles;
DROP POLICY IF EXISTS "Anyone can view industry profiles" ON industry_profiles;
DROP POLICY IF EXISTS "Service role can manage industry profiles" ON industry_profiles;

-- Create new secure policies
CREATE POLICY "Public read access to industry profiles"
  ON industry_profiles
  FOR SELECT
  TO public
  USING (true);

CREATE POLICY "Anon can insert on-demand profiles"
  ON industry_profiles
  FOR INSERT
  TO anon
  WITH CHECK (generated_on_demand = true);

CREATE POLICY "Anon can update on-demand profiles"
  ON industry_profiles
  FOR UPDATE
  TO anon
  USING (generated_on_demand = true)
  WITH CHECK (generated_on_demand = true);

CREATE POLICY "Authenticated can manage profiles"
  ON industry_profiles
  FOR ALL
  TO authenticated
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role full access"
  ON industry_profiles
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ============================================================================
-- INTELLIGENCE CACHE
-- ============================================================================

ALTER TABLE IF EXISTS intelligence_cache ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public cache access" ON intelligence_cache;
DROP POLICY IF EXISTS "Cache read access" ON intelligence_cache;
DROP POLICY IF EXISTS "Cache write access" ON intelligence_cache;

CREATE POLICY "Public cache access"
  ON intelligence_cache
  FOR ALL
  TO public
  USING (true)
  WITH CHECK (true);

-- ============================================================================
-- LOCATION DETECTION CACHE
-- ============================================================================

ALTER TABLE IF EXISTS location_detection_cache ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public location cache access" ON location_detection_cache;
DROP POLICY IF EXISTS "Location cache read" ON location_detection_cache;
DROP POLICY IF EXISTS "Location cache write" ON location_detection_cache;

CREATE POLICY "Public location cache access"
  ON location_detection_cache
  FOR ALL
  TO public
  USING (true)
  WITH CHECK (true);

-- ============================================================================
-- RELOAD POSTGREST
-- ============================================================================

NOTIFY pgrst, 'reload schema';

-- ============================================================================
-- VERIFY
-- ============================================================================

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

SELECT
  tablename,
  policyname,
  roles,
  cmd as operation
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('industry_profiles', 'intelligence_cache', 'location_detection_cache')
ORDER BY tablename, policyname;
