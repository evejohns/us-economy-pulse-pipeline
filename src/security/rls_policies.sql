/*
 * Row Level Security (RLS) Policies for US Economy Pulse Pipeline
 *
 * This script implements comprehensive RLS policies to secure the Supabase database.
 * RLS ensures that:
 * - Raw tables are only accessible by the service role (backend processes)
 * - Anon and authenticated users can only read from published views
 * - No direct access to raw data from client applications
 *
 * Execution: Run this as a postgres superuser or the table owner in Supabase
 */

-- ============================================================================
-- Enable RLS on all raw data tables
-- ============================================================================

ALTER TABLE IF EXISTS raw_gdp ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS raw_cpi ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS raw_unemployment_rate ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS raw_federal_funds_rate ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS raw_consumer_sentiment ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS raw_housing_starts ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS quality_checks ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- RLS Policy for raw_gdp
-- ============================================================================

-- Service role (backend): full access for data ingestion and transformation
CREATE POLICY service_role_raw_gdp_all
ON raw_gdp
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

COMMENT ON POLICY service_role_raw_gdp_all ON raw_gdp IS
'Allows service role to perform SELECT, INSERT, UPDATE, DELETE operations for data ingestion and ETL processes';

-- Anon and authenticated users: no direct access to raw data
-- (If access is needed, it should be through published views only)

-- ============================================================================
-- RLS Policy for raw_cpi
-- ============================================================================

CREATE POLICY service_role_raw_cpi_all
ON raw_cpi
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

COMMENT ON POLICY service_role_raw_cpi_all ON raw_cpi IS
'Allows service role to perform SELECT, INSERT, UPDATE, DELETE operations for data ingestion and ETL processes';

-- ============================================================================
-- RLS Policy for raw_unemployment_rate
-- ============================================================================

CREATE POLICY service_role_raw_unemployment_rate_all
ON raw_unemployment_rate
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

COMMENT ON POLICY service_role_raw_unemployment_rate_all ON raw_unemployment_rate IS
'Allows service role to perform SELECT, INSERT, UPDATE, DELETE operations for data ingestion and ETL processes';

-- ============================================================================
-- RLS Policy for raw_federal_funds_rate
-- ============================================================================

CREATE POLICY service_role_raw_federal_funds_rate_all
ON raw_federal_funds_rate
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

COMMENT ON POLICY service_role_raw_federal_funds_rate_all ON raw_federal_funds_rate IS
'Allows service role to perform SELECT, INSERT, UPDATE, DELETE operations for data ingestion and ETL processes';

-- ============================================================================
-- RLS Policy for raw_consumer_sentiment
-- ============================================================================

CREATE POLICY service_role_raw_consumer_sentiment_all
ON raw_consumer_sentiment
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

COMMENT ON POLICY service_role_raw_consumer_sentiment_all ON raw_consumer_sentiment IS
'Allows service role to perform SELECT, INSERT, UPDATE, DELETE operations for data ingestion and ETL processes';

-- ============================================================================
-- RLS Policy for raw_housing_starts
-- ============================================================================

CREATE POLICY service_role_raw_housing_starts_all
ON raw_housing_starts
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

COMMENT ON POLICY service_role_raw_housing_starts_all ON raw_housing_starts IS
'Allows service role to perform SELECT, INSERT, UPDATE, DELETE operations for data ingestion and ETL processes';

-- ============================================================================
-- RLS Policy for quality_checks
-- ============================================================================

CREATE POLICY service_role_quality_checks_all
ON quality_checks
FOR ALL
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

COMMENT ON POLICY service_role_quality_checks_all ON quality_checks IS
'Allows service role to perform SELECT, INSERT, UPDATE, DELETE operations for quality check logging and ETL processes';

-- ============================================================================
-- Public Access Control: Revoke default permissions
-- ============================================================================

-- Revoke direct table access from anon and authenticated roles
-- These roles can only access published views (if any)

-- Note: If you have published views or materialized views (mart_*), you can
-- create separate RLS policies to allow SELECT-only access to those views:
--
-- CREATE POLICY anon_select_mart_gdp
-- ON mart_gdp
-- FOR SELECT
-- USING (TRUE);
--
-- This allows anonymous users to read published data while keeping raw tables hidden.

-- ============================================================================
-- Grant minimum necessary table privileges
-- ============================================================================

-- Grant SELECT, INSERT, UPDATE on raw tables only to service_role
-- This should be done by Supabase automatically, but can be made explicit:
--
-- GRANT SELECT, INSERT, UPDATE, DELETE ON raw_gdp TO service_role;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON raw_cpi TO service_role;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON raw_unemployment_rate TO service_role;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON raw_federal_funds_rate TO service_role;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON raw_consumer_sentiment TO service_role;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON raw_housing_starts TO service_role;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON quality_checks TO service_role;

-- ============================================================================
-- Security Checklist
-- ============================================================================

/*
After applying these policies, verify:

1. Test service_role access:
   - Connect as service_role user
   - Verify SELECT, INSERT, UPDATE, DELETE work on raw tables

2. Test anon access:
   - Connect as anon user
   - Verify direct table access is denied
   - Verify access to published views works (if created)

3. Test authenticated access:
   - Connect as authenticated user
   - Verify direct table access is denied
   - Verify access to published views works (if created)

4. Audit RLS policies:
   SELECT tablename, policyname, cmd, qual, with_check
   FROM pg_policies
   WHERE schemaname = 'public'
   ORDER BY tablename;

5. Check table security:
   - Ensure no world/public grants on raw tables
   - Use: SELECT * FROM information_schema.role_table_grants
         WHERE table_name LIKE 'raw_%';
*/
