-- Check if RLS is actually disabled
SELECT
  tablename,
  rowsecurity as rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename = 'industry_profiles';

-- Check permissions
SELECT
  grantee,
  privilege_type
FROM information_schema.table_privileges
WHERE table_schema = 'public'
  AND table_name = 'industry_profiles'
  AND grantee IN ('anon', 'authenticated', 'public')
ORDER BY grantee, privilege_type;
