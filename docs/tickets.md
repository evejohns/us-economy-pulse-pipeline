# US Economy Pulse Pipeline - Ticket Breakdown

**Project:** US Economy Pulse Pipeline
**Created:** 2026-03-20
**Total Tickets:** 48
**Total Estimate:** 312 hours

---

## Table of Contents

- [Phase 1: Data Ingestion & Infrastructure](#phase-1-data-ingestion--infrastructure) (12 tickets)
- [Phase 2: Transformation & Analytics](#phase-2-transformation--analytics) (15 tickets)
- [Phase 3: Orchestration & Quality](#phase-3-orchestration--quality) (12 tickets)
- [Phase 4: Documentation & Security](#phase-4-documentation--security) (9 tickets)

---

# PHASE 1: Data Ingestion & Infrastructure

**Duration:** Week 1 | **Owner:** Agent 1 (Ingestor), Agent 3 (Quality), Agent 6 (Security)

---

## P1-001: Setup .env.example Template

**Assigned to:** Agent 1 (Ingestor)
**Dependencies:** None
**Estimate:** 1 hour
**Phase:** 1

### Description
Create a template environment file documenting all required configuration variables for the project. This serves as a reference and security baseline.

### Acceptance Criteria
- [ ] `.env.example` file exists at root of project
- [ ] Includes FRED_API_KEY placeholder (never actual value)
- [ ] Includes SUPABASE_URL placeholder
- [ ] Includes SUPABASE_KEY placeholder
- [ ] Includes SLACK_WEBHOOK_URL placeholder (optional, commented)
- [ ] Includes LOG_LEVEL configuration
- [ ] Includes BACKFILL_START_DATE and BACKFILL_END_DATE
- [ ] All placeholders marked with descriptive comments
- [ ] File is tracked in git (not in .gitignore)
- [ ] File is readable and clear for new developers

### Acceptance Tests
```bash
grep -q "FRED_API_KEY=" .env.example
grep -q "SUPABASE_URL=" .env.example
grep -q "SUPABASE_KEY=" .env.example
# No actual keys present (verified by security audit)
```

---

## P1-002: Create config.py Configuration Module

**Assigned to:** Agent 1 (Ingestor)
**Dependencies:** P1-001
**Estimate:** 2 hours
**Phase:** 1

### Description
Build a centralized configuration module that loads environment variables, validates them, and provides a singleton config object for the entire application.

### Acceptance Criteria
- [ ] `config.py` module loads environment variables from `.env`
- [ ] Validates required fields (FRED_API_KEY, SUPABASE_URL, SUPABASE_KEY)
- [ ] Raises helpful errors if missing required config
- [ ] Defines FRED series codes as constants: GDPC1, CPIAUCSL, UNRATE, FEDFUNDS, UMCSENT, HOUST
- [ ] Includes database connection parameters
- [ ] Includes timeout and retry configurations
- [ ] Can be imported as `from config import config`
- [ ] Supports local dev vs. production modes
- [ ] Never logs or prints secrets
- [ ] Unit tests pass (100% coverage for config validation)

### Acceptance Tests
```python
from config import config
assert config.FRED_API_KEY  # Not None
assert config.SUPABASE_URL  # Valid URL format
assert config.SERIES_CODES == ['GDPC1', 'CPIAUCSL', 'UNRATE', 'FEDFUNDS', 'UMCSENT', 'HOUST']
```

---

## P1-003: Create requirements.txt with Dependencies

**Assigned to:** Agent 1 (Ingestor)
**Dependencies:** None
**Estimate:** 1 hour
**Phase:** 1

### Description
Define all Python package dependencies with pinned versions for reproducibility and security.

### Acceptance Criteria
- [ ] `requirements.txt` exists at project root
- [ ] Pins Python version requirement: 3.10+
- [ ] Includes requests library for API calls (>=2.28.0)
- [ ] Includes psycopg2 or psycopg2-binary for PostgreSQL (>=2.9.0)
- [ ] Includes python-dotenv for .env loading (>=0.21.0)
- [ ] Includes dbt-core (>=1.5.0)
- [ ] Includes dbt-postgres (>=1.5.0)
- [ ] Includes pydantic for config validation (>=2.0.0)
- [ ] Includes pytest for testing (>=7.0.0)
- [ ] Includes slack-sdk for alerts (>=3.20.0)
- [ ] All versions are pinned (exact match, no ~=)
- [ ] pip install -r requirements.txt succeeds without errors

### Acceptance Tests
```bash
pip install -r requirements.txt --dry-run
python -c "import requests; import psycopg2; import dotenv; import dbt"
```

---

## P1-004: Implement fred_client.py FRED API Client

**Assigned to:** Agent 1 (Ingestor)
**Dependencies:** P1-002, P1-003
**Estimate:** 4 hours
**Phase:** 1

### Description
Build a robust FRED API client class that handles authentication, retries, rate limiting, and error handling. This is the core data source integration.

### Acceptance Criteria
- [ ] `fred_client.py` module with FREDClient class
- [ ] Constructor accepts config object and initializes session
- [ ] Implements `fetch_series(series_code, start_date, end_date)` method
- [ ] Automatically handles API rate limiting (exponential backoff)
- [ ] Retries failed requests up to 3 times with 2s exponential backoff
- [ ] Returns structured data: list of {date, value} dicts
- [ ] Validates series codes against SERIES_CODES config
- [ ] Logs all API calls (URL, params, response status) without exposing API key
- [ ] Handles 401 (invalid API key), 404 (invalid series), 429 (rate limit) errors
- [ ] Includes docstrings with examples
- [ ] Unit tests mock API responses and verify retry logic
- [ ] Handles null/missing values gracefully
- [ ] No hardcoded API key or URL

### Acceptance Tests
```python
from fred_client import FREDClient
from config import config

client = FREDClient(config)
data = client.fetch_series('GDPC1', '2020-01-01', '2023-12-31')
assert len(data) > 0
assert all('date' in d and 'value' in d for d in data)
```

---

## P1-005: Implement load_to_supabase.py Data Loader

**Assigned to:** Agent 1 (Ingestor)
**Dependencies:** P1-004, Supabase account created
**Estimate:** 5 hours
**Phase:** 1

### Description
Create a data loader that transforms FRED API responses and inserts them into Supabase PostgreSQL tables. Handles upserts, duplicates, and transaction safety.

### Acceptance Criteria
- [ ] `load_to_supabase.py` module with SupabaseLoader class
- [ ] Constructor connects to Supabase using psycopg2 and config
- [ ] Creates raw data tables if missing: `raw_fred_{series_code}` (e.g., raw_fred_gdpc1)
- [ ] Implements `load_series(series_code, data)` method
- [ ] Performs UPSERT on (date, series_code) to handle duplicates
- [ ] Each raw table has schema: (id, date, value, series_code, loaded_at, updated_at)
- [ ] Validates data types (date as DATE, value as DECIMAL)
- [ ] Logs row counts inserted/updated
- [ ] Commits transactions atomically
- [ ] Rolls back on error and raises informative exception
- [ ] Unit tests use mock Supabase connection
- [ ] Implements `verify_tables()` to check schema consistency
- [ ] Tracks metadata: loaded_at timestamp for audit trail

### Acceptance Tests
```python
from load_to_supabase import SupabaseLoader
from config import config

loader = SupabaseLoader(config)
loader.load_series('GDPC1', [{'date': '2023-01-01', 'value': 27360.5}])
# Verify in Supabase: SELECT COUNT(*) FROM raw_fred_gdpc1;
```

---

## P1-006: Create Supabase Schema DDL

**Assigned to:** Agent 1 (Ingestor) + Agent 3 (Quality)
**Dependencies:** Supabase account created
**Estimate:** 3 hours
**Phase:** 1

### Description
Define and execute the database schema for raw data tables. This is the foundation for all ingestion.

### Acceptance Criteria
- [ ] SQL migration file `001_create_raw_tables.sql` exists
- [ ] Creates `raw_fred_gdpc1` table with schema: id (uuid primary key), date (DATE unique), value (DECIMAL(15,4)), series_code (TEXT), loaded_at (TIMESTAMP), updated_at (TIMESTAMP)
- [ ] Creates same schema for all 6 series: GDPC1, CPIAUCSL, UNRATE, FEDFUNDS, UMCSENT, HOUST
- [ ] Indexes on (date, series_code) for query performance
- [ ] Enables Row-Level Security (RLS) placeholder for future policies
- [ ] Includes comment documentation for each column
- [ ] Migration can be applied idempotently (IF NOT EXISTS)
- [ ] Foreign key constraints or unique constraints documented
- [ ] Supabase project shows all tables created
- [ ] Can query: SELECT COUNT(*) FROM raw_fred_gdpc1; (returns 0 initially)

### SQL Structure
```sql
CREATE TABLE IF NOT EXISTS raw_fred_gdpc1 (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  date DATE NOT NULL UNIQUE,
  value DECIMAL(15,4),
  series_code TEXT DEFAULT 'GDPC1',
  loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_raw_fred_gdpc1_date ON raw_fred_gdpc1(date);
```

---

## P1-007: Implement Backfill Script for Historical Data

**Assigned to:** Agent 1 (Ingestor)
**Dependencies:** P1-005 (load_to_supabase.py)
**Estimate:** 3 hours
**Phase:** 1

### Description
Build a backfill utility that ingests historical FRED data (last 10 years) in batches to populate initial data warehouse.

### Acceptance Criteria
- [ ] `backfill.py` script exists at project root
- [ ] Accepts command-line args: `--series GDPC1 --start-date 2014-01-01 --end-date 2024-03-20`
- [ ] Defaults to 10 years back if dates not provided
- [ ] Batches API requests to avoid rate limits (max 5 series per run, with delays)
- [ ] Logs progress: "Fetched 156 records for GDPC1 (2014-01-01 to 2024-03-20)"
- [ ] Can be run multiple times without duplication (idempotent due to UPSERT)
- [ ] Handles partial failures: logs failures, continues with other series
- [ ] Implements dry-run mode with `--dry-run` flag
- [ ] Returns exit code 0 on success, non-zero on critical failures
- [ ] Execution time for full 6-series backfill: < 2 minutes
- [ ] Includes usage documentation in docstring

### Acceptance Tests
```bash
python backfill.py --dry-run
python backfill.py --series GDPC1 UNRATE --start-date 2020-01-01
# Verify Supabase has data loaded
```

---

## P1-008: Implement pre_ingestion_checks.py Validation

**Assigned to:** Agent 3 (Quality Guardian)
**Dependencies:** P1-006 (schema exists)
**Estimate:** 3 hours
**Phase:** 1

### Description
Build pre-ingestion validation checks to ensure API data quality before loading to warehouse.

### Acceptance Criteria
- [ ] `pre_ingestion_checks.py` module with QualityChecker class
- [ ] Check: API response is valid JSON
- [ ] Check: All required fields present (date, value)
- [ ] Check: Date format is ISO 8601 (YYYY-MM-DD)
- [ ] Check: Value is numeric (float/int), not null
- [ ] Check: Date range is reasonable (not future dates, not before 1900)
- [ ] Check: No duplicate dates in single API response
- [ ] Check: Data is sorted chronologically
- [ ] Logs violations with severity (ERROR, WARNING)
- [ ] Returns structured result: {passed: bool, issues: [list], counts: {total, valid, invalid}}
- [ ] Can reject entire response if critical issues found
- [ ] Unit tests cover all checks with sample data
- [ ] Performance: < 100ms for 500-row dataset

### Acceptance Tests
```python
from pre_ingestion_checks import QualityChecker

checker = QualityChecker()
result = checker.validate([{'date': '2023-01-01', 'value': 27360.5}])
assert result['passed'] == True
```

---

## P1-009: Create quality_checks Table and DDL

**Assigned to:** Agent 3 (Quality Guardian)
**Dependencies:** P1-006 (Supabase schema exists)
**Estimate:** 2 hours
**Phase:** 1

### Description
Define the audit table that tracks all quality check results for transparency and debugging.

### Acceptance Criteria
- [ ] `quality_checks` table created in Supabase
- [ ] Schema: id (uuid), check_timestamp (timestamp), check_type (TEXT: 'pre_ingest', 'post_transform'), series_code (TEXT), total_rows (INT), passed_rows (INT), failed_rows (INT), issues_json (JSONB), status (TEXT: 'PASS', 'FAIL', 'WARN')
- [ ] Indexes on (check_timestamp, check_type) for queries
- [ ] Includes comments for each column
- [ ] Sample insert: status='PASS', failed_rows=0 for successful checks
- [ ] Can query latest check per series: SELECT * FROM quality_checks WHERE series_code='GDPC1' ORDER BY check_timestamp DESC LIMIT 1;
- [ ] Retention policy documented (keep 90 days; archive or delete older)

### SQL Structure
```sql
CREATE TABLE quality_checks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  check_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  check_type TEXT NOT NULL, -- 'pre_ingest', 'post_transform'
  series_code TEXT NOT NULL,
  total_rows INT NOT NULL,
  passed_rows INT NOT NULL,
  failed_rows INT NOT NULL,
  issues_json JSONB,
  status TEXT NOT NULL -- 'PASS', 'FAIL', 'WARN'
);
CREATE INDEX idx_quality_checks_timestamp ON quality_checks(check_timestamp);
```

---

## P1-010: Implement audit_secrets.py Security Scan

**Assigned to:** Agent 6 (Security)
**Dependencies:** Project code structure exists
**Estimate:** 2 hours
**Phase:** 1

### Description
Build a secret-scanning tool to detect accidentally committed credentials, API keys, and other sensitive data.

### Acceptance Criteria
- [ ] `audit_secrets.py` script scans entire repo
- [ ] Detects patterns: AWS keys, API keys, database passwords, private keys
- [ ] Uses common regex patterns from gitleaks, truffleHog
- [ ] Scans files in git index only (not .gitignore'd files)
- [ ] Outputs structured report: {file, line_number, match_type, confidence}
- [ ] Implements `--fix` mode to remove/mask detected secrets interactively
- [ ] Logs all findings with severity levels
- [ ] Can run in CI/CD pipeline with exit code
- [ ] Includes whitelist for false positives (e.g., .env.example placeholders)
- [ ] Performance: scans 1000 files in < 5s

### Acceptance Tests
```bash
python audit_secrets.py
# Output: "Scan complete. 0 secrets detected in 42 files."
python audit_secrets.py --file .env.example
# Output: "OK (whitelisted placeholders)"
```

---

## P1-011: Create Hardened .gitignore

**Assigned to:** Agent 6 (Security)
**Dependencies:** None
**Estimate:** 1 hour
**Phase:** 1

### Description
Configure .gitignore to prevent accidental secrets, large files, and IDE artifacts from being committed.

### Acceptance Criteria
- [ ] `.gitignore` file exists at project root
- [ ] Ignores `.env` (local config, never commit)
- [ ] Ignores `.env.local`, `.env.*.local`
- [ ] Ignores `__pycache__/`, `*.pyc`, `.pytest_cache/`
- [ ] Ignores IDE files: `.vscode/`, `.idea/`, `*.swp`, `*.swo`
- [ ] Ignores OS files: `.DS_Store`, `Thumbs.db`
- [ ] Ignores `dbt/target/`, `dbt/logs/` (dbt build artifacts)
- [ ] Ignores `*.log` files
- [ ] Ignores `credentials/`, `secrets/` directories
- [ ] Allows `.env.example` to be tracked (it's a template)
- [ ] Run `git status` shows no unwanted files

### Acceptance Tests
```bash
git status --short | wc -l
# Output: only tracked files (no .env, .pyc, etc.)
```

---

## P1-012: Document Phase 1 Integration & Dry-Run Daily Workflow

**Assigned to:** Agent 0 (PM)
**Dependencies:** P1-001 through P1-011
**Estimate:** 2 hours
**Phase:** 1

### Description
Consolidate Phase 1 work, verify all integrations, and prepare GitHub Actions workflow template for Phase 3 (deploy in dry-run mode).

### Acceptance Criteria
- [ ] Phase 1 completion checklist completed
- [ ] All 6 FRED series have data in Supabase (verify row counts)
- [ ] Pre-ingestion checks passing 100%
- [ ] No secrets detected in git history (audit_secrets.py clean)
- [ ] `daily_pipeline.yml` created (Phase 3 task, but draft in Phase 1)
- [ ] Manual dry-run of entire ingest → load → validate flow succeeds
- [ ] Project tracker updated with Phase 1 completion status
- [ ] Phase 1 gate review scheduled

### Acceptance Tests
```sql
SELECT series_code, COUNT(*) FROM raw_fred_gdpc1 GROUP BY series_code;
-- All 6 series present with > 100 rows each
```

---

# PHASE 2: Transformation & Analytics

**Duration:** Week 2 | **Owner:** Agent 2 (Transformer), Agent 3 (Quality)

---

## P2-001: Initialize dbt Project & Configuration

**Assigned to:** Agent 2 (Transformer)
**Dependencies:** P1-012 (Phase 1 complete)
**Estimate:** 2 hours
**Phase:** 2

### Description
Set up dbt project structure, initialize dbt_project.yml, and configure Supabase as the target warehouse.

### Acceptance Criteria
- [ ] `dbt/dbt_project.yml` exists with project name "economy_pulse"
- [ ] Version: 1.5+
- [ ] Profile name: "economy_pulse"
- [ ] Config: materialized views for staging, tables for marts, ephemeral for macros
- [ ] Includes seed path config (if using dbt seeds)
- [ ] Includes macro path config
- [ ] Includes test path config
- [ ] `dbt/profiles.yml` configured to connect to Supabase (dev: target: dev, prod: target: prod)
- [ ] Database: Supabase project name
- [ ] Schema: raw (for raw staging), transformed (for intermediate), analytics (for marts)
- [ ] Authentication: user/password or connection string from config
- [ ] `dbt debug` command succeeds
- [ ] `dbt compile` succeeds with no errors

### Acceptance Tests
```bash
cd dbt
dbt debug
# Output: "All checks passed!"
dbt compile
# Output: "Done. 0 errors and 0 warnings."
```

---

## P2-002: Create sources.yml for Raw Data Tables

**Assigned to:** Agent 2 (Transformer)
**Dependencies:** P2-001, P1-006 (raw tables exist)
**Estimate:** 1.5 hours
**Phase:** 2

### Description
Define dbt source metadata for all 6 raw FRED tables, enabling lineage tracking and source freshness monitoring.

### Acceptance Criteria
- [ ] `dbt/models/staging/sources.yml` created
- [ ] Source name: "fred_api"
- [ ] Database: Supabase database name
- [ ] Schema: public (where raw tables live)
- [ ] Tables defined: raw_fred_gdpc1, raw_fred_cpiaucsl, raw_fred_unrate, raw_fred_fedfunds, raw_fred_umcsent, raw_fred_houst
- [ ] Column documentation: id, date, value, series_code, loaded_at, updated_at
- [ ] Unique constraints documented on (date, series_code)
- [ ] Not-null constraints on date, value, series_code
- [ ] Source freshness check: warn if > 1 day old (for daily ingestion)
- [ ] dbt parse succeeds with no errors

### YAML Structure
```yaml
version: 2

sources:
  - name: fred_api
    database: your_supabase_db
    schema: public
    tables:
      - name: raw_fred_gdpc1
        description: "GDP from FRED"
        columns:
          - name: date
            description: "Date of observation"
            tests:
              - not_null
          - name: value
            description: "GDP value in billions"
            tests:
              - not_null
```

---

## P2-003: Create Base Staging Models (6 models)

**Assigned to:** Agent 2 (Transformer)
**Dependencies:** P2-002 (sources.yml exists)
**Estimate:** 4 hours
**Phase:** 2

### Description
Build 6 staging models that clean, standardize, and prepare raw FRED data for downstream transformation.

### Acceptance Criteria
- [ ] Model: `stg_fred_gdpc1.sql` - GDP staging
- [ ] Model: `stg_fred_cpiaucsl.sql` - CPI staging
- [ ] Model: `stg_fred_unrate.sql` - Unemployment staging
- [ ] Model: `stg_fred_fedfunds.sql` - Fed funds rate staging
- [ ] Model: `stg_fred_umcsent.sql` - Consumer sentiment staging
- [ ] Model: `stg_fred_houst.sql` - Housing starts staging
- [ ] Each model: selects from source, renames columns to standard names (observation_date, metric_value)
- [ ] Each model: casts data types explicitly (DATE, DECIMAL)
- [ ] Each model: filters nulls
- [ ] Each model: includes series_code constant for clarity
- [ ] Materialization: view (no storage cost)
- [ ] `dbt test` passes all generic tests on staging models
- [ ] Row counts match source tables

### Acceptance Tests
```bash
dbt test --select tag:staging
# Output: "All 6 models passed!"
dbt run --select stg_fred_gdpc1
# Output: "1 of 1 START stg_fred_gdpc1 [VIEW]... (SELECT 156 rows)"
```

---

## P2-004: Create Intermediate YoY Change Model

**Assigned to:** Agent 2 (Transformer)
**Dependencies:** P2-003 (staging models)
**Estimate:** 3 hours
**Phase:** 2

### Description
Build a model that calculates year-over-year changes for economic indicators to show trend direction.

### Acceptance Criteria
- [ ] Model: `int_yoy_changes.sql`
- [ ] Joins staging models on observation_date
- [ ] Calculates YoY % change: (current_value - prior_year_value) / prior_year_value * 100
- [ ] Handles null values (missing year-ago data)
- [ ] Includes all 6 series: GDPC1, CPIAUCSL, UNRATE, FEDFUNDS, UMCSENT, HOUST
- [ ] Output columns: observation_date, series_code, metric_value, yoy_change_pct
- [ ] Filters: exclude rows where YoY data not available
- [ ] Materialization: ephemeral (intermediate, not persisted)
- [ ] dbt test passes; validates output data
- [ ] Sample output: GDP YoY = 2.5% (realistic economic growth)

### Acceptance Tests
```sql
SELECT * FROM analytics.int_yoy_changes WHERE series_code='GDPC1' ORDER BY observation_date DESC LIMIT 1;
-- Expected: positive YoY change for GDP growth
```

---

## P2-005: Create Intermediate Rolling Average Model

**Assigned to:** Agent 2 (Transformer)
**Dependencies:** P2-003 (staging models)
**Estimate:** 3 hours
**Phase:** 2

### Description
Build a model that calculates 3-month and 12-month rolling averages to smooth volatile data.

### Acceptance Criteria
- [ ] Model: `int_rolling_averages.sql`
- [ ] Calculates 3-month rolling average (using window function)
- [ ] Calculates 12-month rolling average (using window function)
- [ ] Includes all 6 series
- [ ] Output columns: observation_date, series_code, metric_value, ma_3m, ma_12m
- [ ] Handles edge cases: < 3 months or < 12 months of data (return NULL)
- [ ] Sorted by series_code, observation_date
- [ ] Materialization: ephemeral (intermediate)
- [ ] Test: 12-month average is smoother than raw data (lower std dev)
- [ ] dbt test passes

### Acceptance Tests
```sql
SELECT observation_date, metric_value, ma_3m, ma_12m
FROM analytics.int_rolling_averages
WHERE series_code='UNRATE'
ORDER BY observation_date DESC LIMIT 3;
```

---

## P2-006: Create Intermediate Recession Risk Indicator

**Assigned to:** Agent 2 (Transformer)
**Dependencies:** P2-003, P2-004, P2-005
**Estimate:** 3 hours
**Phase:** 2

### Description
Build a composite recession risk model combining multiple economic indicators.

### Acceptance Criteria
- [ ] Model: `int_recession_indicators.sql`
- [ ] Uses inverted yield curve indicator: FEDFUNDS > 0 if spreading (risk)
- [ ] Uses unemployment trend: rising UNRATE signals risk
- [ ] Uses GDP growth: negative YoY change signals risk
- [ ] Uses consumer sentiment: falling UMCSENT signals risk
- [ ] Combines signals into recession_risk_score (0-100 scale)
- [ ] Output columns: observation_date, recession_risk_score, components (JSON or columns)
- [ ] Materialization: ephemeral
- [ ] Includes documentation of weighting methodology
- [ ] Sample output: recession_risk_score = 45 (elevated but not critical)
- [ ] dbt test passes

### Acceptance Tests
```sql
SELECT observation_date, recession_risk_score FROM analytics.int_recession_indicators
ORDER BY observation_date DESC LIMIT 1;
-- Expected: score between 0-100
```

---

## P2-007: Create Intermediate Correlation Analysis Model

**Assigned to:** Agent 2 (Transformer)
**Dependencies:** P2-003 (staging models exist)
**Estimate:** 3 hours
**Phase:** 2

### Description
Build a model analyzing correlations between economic series to identify relationships.

### Acceptance Criteria
- [ ] Model: `int_correlations.sql`
- [ ] Calculates Pearson correlation between series pairs (12-month rolling window)
- [ ] Pairs: GDP/CPI, Unemployment/GDP, FedfundsRate/Unemployment, Sentiment/GDP
- [ ] Output columns: observation_date, series_a, series_b, correlation_coefficient, window_size
- [ ] Correlation coefficient range: -1.0 to 1.0 (mathematically validated)
- [ ] Handles null/missing data in windows
- [ ] Materialization: ephemeral
- [ ] Sample output: GDP/Unemployment correlation = -0.75 (inverse relationship expected)
- [ ] dbt test validates correlation math
- [ ] Performance: < 10s for full correlation compute

### Acceptance Tests
```sql
SELECT series_a, series_b, correlation_coefficient FROM analytics.int_correlations
WHERE series_a='GDPC1' AND series_b='UNRATE'
ORDER BY observation_date DESC LIMIT 1;
-- Expected: correlation ~ -0.7 to -0.9 (inverse)
```

---

## P2-008: Create Mart: mart_economic_trends

**Assigned to:** Agent 2 (Transformer)
**Dependencies:** P2-004, P2-005, P2-006 (intermediate models)
**Estimate:** 2 hours
**Phase:** 2

### Description
Build the primary analytics mart table for economic trends, combining staged and intermediate data.

### Acceptance Criteria
- [ ] Model: `mart_economic_trends.sql`
- [ ] Materialization: table (persisted for analytics/BI)
- [ ] Joins all 6 staging models on observation_date
- [ ] Includes columns from stg_fred_* models: gdp_value, cpi_value, unrate_value, etc.
- [ ] Includes YoY changes from `int_yoy_changes`
- [ ] Includes rolling averages from `int_rolling_averages`
- [ ] Includes recession risk from `int_recession_indicators`
- [ ] Grain: one row per observation_date (no duplication)
- [ ] Test: unique constraint on observation_date passes
- [ ] Test: no null values in key columns
- [ ] dbt run succeeds; verify row count matches expected timespan

### Acceptance Tests
```bash
dbt run --select mart_economic_trends
# Output: "mart_economic_trends... [TABLE]... (350 rows)"
```

---

## P2-009: Create Mart: mart_recession_risk

**Assigned to:** Agent 2 (Transformer)
**Dependencies:** P2-006 (recession indicators)
**Estimate:** 2 hours
**Phase:** 2

### Description
Build a specialized mart focused on recession risk monitoring for stakeholders.

### Acceptance Criteria
- [ ] Model: `mart_recession_risk.sql`
- [ ] Materialization: table
- [ ] Source: `int_recession_indicators` + staging models
- [ ] Columns: observation_date, recession_risk_score, signal_1_unemployment (UNRATE), signal_2_gdp_growth (YoY), signal_3_sentiment (UMCSENT), signal_4_fedrate (FEDFUNDS)
- [ ] Includes status field: LOW (0-33), MODERATE (34-67), HIGH (68-100)
- [ ] Test: unique observation_date
- [ ] Test: recession_risk_score in valid range (0-100)
- [ ] Row count = number of months in data
- [ ] dbt run succeeds

### Acceptance Tests
```bash
SELECT observation_date, recession_risk_score, status FROM analytics.mart_recession_risk
WHERE status='HIGH' LIMIT 1;
```

---

## P2-010: Create Mart: mart_sentiment_correlation

**Assigned to:** Agent 2 (Transformer)
**Dependencies:** P2-007 (correlations)
**Estimate:** 2 hours
**Phase:** 2

### Description
Build a mart for correlation analysis focused on consumer sentiment relationships.

### Acceptance Criteria
- [ ] Model: `mart_sentiment_correlation.sql`
- [ ] Materialization: table
- [ ] Source: `int_correlations` + sentiment data
- [ ] Columns: observation_date, sentiment_gdp_correlation, sentiment_unemployment_correlation, sentiment_cpi_correlation, interpretation (TEXT: strong negative, weak positive, etc.)
- [ ] Includes interpretation logic based on correlation strength
- [ ] Test: correlations in valid range
- [ ] Test: unique observation_date
- [ ] dbt run succeeds

### Acceptance Tests
```bash
dbt run --select mart_sentiment_correlation
dbt test --select mart_sentiment_correlation
# All tests pass
```

---

## P2-011: Create dbt Generic Tests & Macros

**Assigned to:** Agent 2 (Transformer) + Agent 3 (Quality)
**Dependencies:** P2-001 (dbt project exists)
**Estimate:** 3 hours
**Phase:** 2

### Description
Build reusable dbt test definitions and macros for data quality validation.

### Acceptance Criteria
- [ ] Generic test: `not_null` applied to key columns
- [ ] Generic test: `unique` on observation_date in marts
- [ ] Generic test: `relationships` (FK constraints, if applicable)
- [ ] Custom test: `column_values_in_valid_range` (value between -999 and 999999 for economic data)
- [ ] Custom test: `no_future_dates` (observation_date <= today)
- [ ] Custom test: `expected_grain` (ensures one row per date per series)
- [ ] Macro: `create_audit_columns` (auto-adds dbt_created_at, dbt_updated_at)
- [ ] Macro: `document_series` (loops through FRED series for metadata)
- [ ] All tests in `dbt/tests/` directory
- [ ] dbt test runs all tests; no failures
- [ ] Test coverage: > 90% of models

### Acceptance Tests
```bash
dbt test
# Output: "20 tests passed, 0 failures"
```

---

## P2-012: Run Full dbt DAG & Validate Data Quality

**Assigned to:** Agent 2 (Transformer) + Agent 3 (Quality)
**Dependencies:** P2-003 through P2-011
**Estimate:** 2 hours
**Phase:** 2

### Description
Execute full dbt pipeline, validate output data, and ensure all models compile and test.

### Acceptance Criteria
- [ ] `dbt compile` succeeds with 0 errors
- [ ] `dbt run` executes all staging, intermediate, and mart models successfully
- [ ] All 3 marts contain expected row counts and columns
- [ ] `dbt test` passes all tests: generic and custom
- [ ] dbt docs generate successfully (documentation.md artifact)
- [ ] DAG visualization shows correct model dependencies
- [ ] Mart data exports to CSV for manual spot-checking
- [ ] Phase 2 gate review materials prepared

### Acceptance Tests
```bash
dbt deps
dbt compile
dbt run
dbt test
# All commands exit with 0
dbt docs generate
# docs.html viewable with full lineage
```

---

## P2-013: Create dbt Documentation (Data Dictionary)

**Assigned to:** Agent 2 (Transformer) + Agent 5 (Documenter)
**Dependencies:** P2-012 (models complete)
**Estimate:** 2 hours
**Phase:** 2

### Description
Document all dbt models, sources, and columns in YAML for lineage and discovery.

### Acceptance Criteria
- [ ] All 6 staging models have `description:` and `columns:` in YAML
- [ ] All intermediate models documented with transformation logic
- [ ] All mart models documented with business context
- [ ] Sources (raw_fred_*) documented with refresh frequency, owner
- [ ] Column descriptions explain unit, formula, calculation method
- [ ] Documentation includes example values
- [ ] dbt docs generate includes all models in sidebar
- [ ] Each model includes at least one test definition
- [ ] Column-level tests linked to documentation

### Acceptance Tests
```bash
dbt docs generate
# HTML output viewable with search; all 15 models listed with docs
```

---

## P2-014: Integration Test: End-to-End Transformation

**Assigned to:** Agent 2 (Transformer) + Agent 3 (Quality)
**Dependencies:** P2-012 (all models deployed)
**Estimate:** 2 hours
**Phase:** 2

### Description
Perform end-to-end test: raw data in → transforms → marts out; validate data quality at each step.

### Acceptance Criteria
- [ ] Raw tables have 100%+ rows compared to backfill
- [ ] Staging models preserve raw data (0 rows filtered unexpectedly)
- [ ] Intermediate models produce expected calculations (spot-check 5 rows)
- [ ] Mart tables have correct grain and no duplicates
- [ ] YoY change calculation correct for at least 1 series (manual calc verification)
- [ ] Rolling average smoother than raw (visual inspection of plot)
- [ ] Recession risk score reasonable (0-100 range, matches economic reality)
- [ ] No data loss from raw to mart (row counts trend compatible)
- [ ] All NULL handling correct (documented, not silent)
- [ ] Performance: full pipeline < 5 minutes

### Acceptance Tests
```bash
dbt run
# Verify: SELECT COUNT(*) FROM analytics.mart_economic_trends; > 100
# Verify: SELECT * FROM analytics.mart_recession_risk WHERE recession_risk_score > 70;
# Check: Dates are chronological, no gaps > 1 month
```

---

## P2-015: Phase 2 Gate Review & Checkpoint

**Assigned to:** Agent 0 (PM)
**Dependencies:** P2-001 through P2-014
**Estimate:** 1 hour
**Phase:** 2

### Description
Consolidate Phase 2 deliverables, verify transformation quality, and gate Phase 3.

### Acceptance Criteria
- [ ] All 15 dbt models deployed and tested
- [ ] 3 marts ready for consumption (marts table, recession_risk, correlation)
- [ ] dbt docs publicly accessible (or in repo)
- [ ] Data lineage clear (sources → staging → intermediate → marts)
- [ ] Phase 2 gate checklist complete
- [ ] Phase 3 kick-off scheduled

---

# PHASE 3: Orchestration & Quality

**Duration:** Week 3 | **Owner:** Agent 4 (Orchestrator), Agent 3 (Quality)

---

## P3-001: Create daily_pipeline.yml GitHub Actions Workflow

**Assigned to:** Agent 4 (Orchestrator)
**Dependencies:** P2-012 (dbt models ready), P1-012 (ingest code ready)
**Estimate:** 3 hours
**Phase:** 3

### Description
Build the primary automated daily workflow that orchestrates data ingestion, transformation, and quality checks.

### Acceptance Criteria
- [ ] `.github/workflows/daily_pipeline.yml` file created
- [ ] Trigger: scheduled daily at 06:00 UTC (2 AM EST, off-peak)
- [ ] Steps:
  1. Checkout code
  2. Set up Python 3.10+
  3. Install requirements.txt
  4. Run backfill.py (dry-run mode initially)
  5. Run pre-ingestion checks (pre_ingestion_checks.py)
  6. Load data to Supabase (load_to_supabase.py)
  7. Run dbt deps, dbt parse, dbt run
  8. Run dbt test
  9. Run post_transform_checks.py
  10. Send Slack notification (success/failure)
- [ ] Environment secrets configured: FRED_API_KEY, SUPABASE_URL, SUPABASE_KEY, SLACK_WEBHOOK_URL
- [ ] Job timeout: 30 minutes (should complete in < 10 min)
- [ ] Failure handling: Slack alert with error details
- [ ] Logs retained for 90 days
- [ ] Dry-run mode option: use `--dry-run` flag in early Phase 3

### YAML Structure
```yaml
name: Daily Pipeline

on:
  schedule:
    - cron: '0 6 * * *'  # Daily 6 AM UTC
  workflow_dispatch:  # Allow manual trigger

jobs:
  pipeline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: python backfill.py --dry-run
      - run: python pre_ingestion_checks.py
      - run: python load_to_supabase.py
      - run: cd dbt && dbt run && dbt test
      - run: python post_transform_checks.py
      - name: Slack Notification
        if: always()
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK_URL }} \
            -d '{"text":"Pipeline '${{ job.status }}'"}'
```

---

## P3-002: Create weekly_deep_test.yml GitHub Actions Workflow

**Assigned to:** Agent 4 (Orchestrator)
**Dependencies:** P1-008, P2-011 (quality checks exist)
**Estimate:** 2 hours
**Phase:** 3

### Description
Build a comprehensive weekly test workflow that runs expensive or detailed quality validations.

### Acceptance Criteria
- [ ] `.github/workflows/weekly_deep_test.yml` file created
- [ ] Trigger: scheduled every Sunday at 02:00 UTC
- [ ] Steps:
  1. Checkout code
  2. Setup Python
  3. Run dbt test with verbose output (includes snapshot of results)
  4. Run custom deep quality checks (data profiling, schema drift detection)
  5. Generate dbt docs
  6. Commit docs to repo (optional)
  7. Run statistical checks (distribution analysis, anomaly detection)
  8. Send detailed report to Slack
- [ ] Timeout: 60 minutes
- [ ] Includes comparison to historical baselines
- [ ] Report includes: row counts, value distributions, null percentages, data drift metrics
- [ ] Logs retained for 1 year

### Acceptance Tests
```bash
# Manual trigger to verify workflow
gh workflow run weekly_deep_test.yml --ref main
```

---

## P3-003: Create backfill.yml GitHub Actions Workflow

**Assigned to:** Agent 4 (Orchestrator)
**Dependencies:** P1-007 (backfill script exists)
**Estimate:** 2 hours
**Phase:** 3

### Description
Build a manual-trigger workflow for on-demand historical data reprocessing or gap-filling.

### Acceptance Criteria
- [ ] `.github/workflows/backfill.yml` file created
- [ ] Trigger: manual (workflow_dispatch) only
- [ ] Inputs: start_date (date picker), end_date (date picker), series (multi-select: GDPC1, CPIAUCSL, etc.)
- [ ] Steps:
  1. Checkout code
  2. Setup Python
  3. Run backfill.py with provided date range and series
  4. Verify row counts inserted
  5. Run post-load quality checks
  6. Send summary to Slack
- [ ] Supports selective series ingestion (not always all 6)
- [ ] Idempotent: can re-run same dates without duplication (UPSERT handled)
- [ ] Timeout: 45 minutes
- [ ] Logs available for troubleshooting

### Acceptance Tests
```bash
gh workflow run backfill.yml \
  -f start_date='2020-01-01' \
  -f end_date='2020-12-31' \
  -f series='GDPC1,UNRATE'
```

---

## P3-004: Implement post_transform_checks.py Quality Validation

**Assigned to:** Agent 3 (Quality Guardian)
**Dependencies:** P2-012 (dbt marts exist), P1-009 (quality_checks table)
**Estimate:** 3 hours
**Phase:** 3

### Description
Build post-transformation quality checks to validate dbt outputs before they reach stakeholders.

### Acceptance Criteria
- [ ] `post_transform_checks.py` module
- [ ] Check: mart tables exist and have rows
- [ ] Check: no unexpected NULLs in key columns
- [ ] Check: observation_date grain (one row per date)
- [ ] Check: recession_risk_score in 0-100 range
- [ ] Check: correlation coefficients in -1.0 to 1.0 range
- [ ] Check: YoY changes in reasonable range (-50% to +50%)
- [ ] Check: no duplicate rows
- [ ] Check: data freshness (latest row within 1 week)
- [ ] Check: row count hasn't dropped >10% vs. previous day
- [ ] Logs all checks with pass/fail status
- [ ] Records results to `quality_checks` table
- [ ] Raises exception on critical failures (stop downstream processing)
- [ ] Performance: < 30s for all checks

### Acceptance Tests
```python
from post_transform_checks import PostTransformChecker

checker = PostTransformChecker(config)
result = checker.run_all_checks()
assert result['status'] == 'PASS'
assert all(r['passed'] for r in result['checks'])
```

---

## P3-005: Implement alerting.py Slack Notification System

**Assigned to:** Agent 3 (Quality Guardian)
**Dependencies:** P3-004 (post_transform_checks.py)
**Estimate:** 2 hours
**Phase:** 3

### Description
Build a Slack alerting system to notify team of pipeline status, failures, and anomalies.

### Acceptance Criteria
- [ ] `alerting.py` module with AlertManager class
- [ ] Integrates with Slack SDK
- [ ] Sends alerts on pipeline start, completion, failure
- [ ] Alert format: structured message with job name, status, duration, error details
- [ ] Severity levels: INFO, WARNING, CRITICAL
- [ ] CRITICAL: thread notifications for immediate visibility
- [ ] Includes runbook link or recovery steps in alert
- [ ] Attachments: error logs, data quality metrics
- [ ] Implements muting/dedupe (don't spam same error 10x per hour)
- [ ] Can be tested with `--dry-run` (logs to stdout instead)
- [ ] Webhook URL from config (secrets)
- [ ] Performance: send alert in < 1s

### Acceptance Tests
```python
from alerting import AlertManager

alerter = AlertManager(config)
alerter.send_alert(
    severity='CRITICAL',
    title='Pipeline Failed',
    message='dbt test failed with 3 errors'
)
# Verify message appears in Slack
```

---

## P3-006: Create Metabase Dashboard: Economic Trends

**Assigned to:** Agent 4 (Orchestrator)
**Dependencies:** P2-008 (mart_economic_trends table)
**Estimate:** 2 hours
**Phase:** 3

### Description
Build a Metabase dashboard visualizing economic trends for stakeholder consumption.

### Acceptance Criteria
- [ ] Metabase instance accessible (docker or cloud)
- [ ] Connected to Supabase warehouse
- [ ] Dashboard: "US Economy Pulse"
- [ ] Card 1: GDP trend over time (line chart, 10-year history)
- [ ] Card 2: YoY GDP growth (bar chart)
- [ ] Card 3: Unemployment rate trend (line chart)
- [ ] Card 4: Inflation (CPI) trend (line chart with target line)
- [ ] Card 5: Consumer sentiment (line chart)
- [ ] Card 6: Housing starts (bar chart)
- [ ] Card 7: Fed funds rate (line chart)
- [ ] Card 8: Recession risk score (gauge chart, color-coded)
- [ ] All charts auto-refresh daily (tied to pipeline)
- [ ] Filters: date range, series selection (optional)
- [ ] Includes annotations for major events (if applicable)
- [ ] Dashboard public URL shared with team

### Acceptance Tests
- [ ] Dashboard loads in < 5 seconds
- [ ] All 8 cards render without errors
- [ ] Data matches dbt mart queries
- [ ] Can drill down into data

---

## P3-007: Create Metabase Dashboard: Data Quality Monitor

**Assigned to:** Agent 4 (Orchestrator) + Agent 3 (Quality)
**Dependencies:** P1-009, P3-004, P3-005 (quality checks and alerting)
**Estimate:** 2 hours
**Phase:** 3

### Description
Build a Metabase dashboard for internal monitoring of data quality metrics and pipeline health.

### Acceptance Criteria
- [ ] Dashboard: "Data Quality Monitor"
- [ ] Card 1: Quality checks over time (pass/fail rate)
- [ ] Card 2: Last check status per series (status: PASS/FAIL/WARN)
- [ ] Card 3: Pipeline run duration trend (daily)
- [ ] Card 4: Data freshness (days since last update per table)
- [ ] Card 5: Row count trend (raw and marts, to detect data loss)
- [ ] Card 6: Top 10 quality check failures (if any)
- [ ] Card 7: API response time trend
- [ ] Card 8: Data volume by series (pie chart)
- [ ] Refresh: every 6 hours
- [ ] Access: internal team only (not public)

### Acceptance Tests
- [ ] Dashboard visible to team
- [ ] All cards query `quality_checks` table successfully
- [ ] Metrics align with pipeline execution

---

## P3-008: Configure Slack Channel & Integrations

**Assigned to:** Agent 4 (Orchestrator)
**Dependencies:** P3-005 (alerting.py)
**Estimate:** 1 hour
**Phase:** 3

### Description
Set up Slack channel for pipeline notifications and configure alert routing.

### Acceptance Criteria
- [ ] Slack channel created: #economy-pulse-pipeline
- [ ] Webhook URL configured in GitHub Actions secrets
- [ ] Webhook URL configured in alerting.py config
- [ ] Bot avatar and channel description set
- [ ] Alert rules configured:
  - CRITICAL alerts → thread + @channel mention
  - WARNING alerts → normal message
  - INFO alerts → muted (only visible in pinned threads)
- [ ] Pinned message: runbook, docs links, escalation contacts
- [ ] Test alert sent and verified
- [ ] Team members added to channel

### Acceptance Tests
```bash
# Manual test
python alerting.py --test-webhook
# Verify message appears in Slack channel
```

---

## P3-009: 7-Day Pipeline Stability Test

**Assigned to:** Agent 4 (Orchestrator) + Agent 3 (Quality)
**Dependencies:** P3-001 through P3-008
**Estimate:** 3 hours (setup + monitoring)
**Phase:** 3

### Description
Run the full automated pipeline for 7 consecutive days, monitoring for failures, data quality issues, and resource constraints.

### Acceptance Criteria
- [ ] All 7 daily pipeline runs complete successfully (100% success rate)
- [ ] No data duplication in marts
- [ ] No data loss (row counts consistent)
- [ ] All quality checks pass on all 7 days
- [ ] Slack alerts working (test alert sent daily)
- [ ] No manual intervention required
- [ ] Workflow execution time stable (no significant slowdown)
- [ ] Zero secret exposure detected (audit_secrets.py clean)
- [ ] Metabase dashboards update without errors
- [ ] Logs reviewed for warnings/issues; none critical

### Acceptance Tests
```bash
# Query quality_checks table
SELECT COUNT(*) FROM quality_checks WHERE status='PASS' AND check_timestamp > NOW() - INTERVAL '7 days';
# Expected: >= 40 (6 checks/day × 7 days, with buffer)
```

---

## P3-010: Setup Workflow Alerts & Escalation Rules

**Assigned to:** Agent 4 (Orchestrator)
**Dependencies:** P3-008 (Slack setup)
**Estimate:** 1 hour
**Phase:** 3

### Description
Configure intelligent alerting rules to escalate critical issues to on-call engineers.

### Acceptance Criteria
- [ ] Rule: Pipeline failure → Slack alert to #economy-pulse-pipeline
- [ ] Rule: Quality check FAIL → Slack alert (can pause downstream processing)
- [ ] Rule: API rate limit hit → WARNING alert with mitigation steps
- [ ] Rule: Data freshness > 24 hours → WARNING alert
- [ ] Rule: dbt test failure → alert with failing test name and model
- [ ] Rule: Backfill in progress → INFO notification (no alarming)
- [ ] Escalation: if 2 consecutive daily runs fail → escalate to tech lead
- [ ] Do-not-disturb hours: silence INFO/WARNING alerts 6 PM - 6 AM local time
- [ ] Rules configurable in code (not hardcoded in workflow)

### Acceptance Tests
```bash
# Manually trigger a failure scenario
# Verify Slack alert appears within 2 minutes
```

---

## P3-011: Documentation: Workflow Runbook & Recovery Guide

**Assigned to:** Agent 5 (Documenter)
**Dependencies:** P3-001 through P3-010
**Estimate:** 2 hours
**Phase:** 3

### Description
Document operational procedures and recovery steps for common pipeline failures.

### Acceptance Criteria
- [ ] File: `docs/operations_runbook.md`
- [ ] Section: "Daily Pipeline Execution" - what happens, when, expected outcome
- [ ] Section: "Common Failures & Recovery"
  - API rate limit exceeded → cache & retry strategy
  - Supabase connection timeout → switch to backup or escalate
  - dbt model failure → how to debug, fix, rerun
  - Quality check failure → investigate root cause, options (fix/skip)
  - Data duplication → manual upsert/dedup script
- [ ] Section: "Manual Backfill Procedure" - step-by-step guide
- [ ] Section: "Escalation Contacts" - who to contact for each issue type
- [ ] Section: "Monitoring Dashboard Guide" - how to read Metabase charts
- [ ] Section: "Log Locations" - where to find pipeline logs (GitHub Actions, Supabase)
- [ ] Links to relevant files and code
- [ ] Tested by a new team member (walkthrough)

### Acceptance Tests
- [ ] Documentation is clear and complete
- [ ] All steps are actionable without additional research
- [ ] A team member unfamiliar with the project can follow the runbook

---

## P3-012: Phase 3 Gate Review & Checkpoint

**Assigned to:** Agent 0 (PM)
**Dependencies:** P3-001 through P3-011
**Estimate:** 1 hour
**Phase:** 3

### Description
Consolidate Phase 3 deliverables, verify automated operations, and gate Phase 4.

### Acceptance Criteria
- [ ] All 3 GitHub Actions workflows deployed and tested
- [ ] 7-day stability test complete (100% success)
- [ ] All quality checks passing consistently
- [ ] Metabase dashboards operational and shared
- [ ] Slack alerts configured and working
- [ ] Runbook complete and team trained
- [ ] Zero manual intervention in past 7 days
- [ ] Phase 3 gate checklist complete

---

# PHASE 4: Documentation & Security

**Duration:** Week 4 | **Owner:** Agent 5 (Documenter), Agent 6 (Security)

---

## P4-001: Create README.md with Full Architecture

**Assigned to:** Agent 5 (Documenter)
**Dependencies:** P3-012 (Phase 3 complete)
**Estimate:** 3 hours
**Phase:** 4

### Description
Write comprehensive README for project onboarding, architecture overview, and quick-start guide.

### Acceptance Criteria
- [ ] File: `README.md` at project root
- [ ] Section: "Overview" - project purpose, use cases, business value
- [ ] Section: "Architecture Diagram" - visual (ASCII or image) showing data flow
- [ ] Section: "Tech Stack" - all technologies with versions
- [ ] Section: "Project Structure" - directory layout explanation
- [ ] Section: "Quick Start" - < 5 min to first successful run:
  1. Clone repo
  2. Create .env from .env.example
  3. Install requirements: pip install -r requirements.txt
  4. Run: python backfill.py --dry-run
  5. Verify: SELECT COUNT(*) FROM raw_fred_gdpc1;
- [ ] Section: "Data Flow" - step-by-step: ingest → transform → marts
- [ ] Section: "Team & Responsibilities" - who owns what
- [ ] Section: "Monitoring & Alerts" - how to check pipeline health
- [ ] Section: "FAQ" - common questions
- [ ] Section: "Contributing" - how to add features, run locally
- [ ] Links to detailed docs: data dictionary, operations runbook, security guide
- [ ] Code examples for common queries
- [ ] Instructions for Metabase dashboard access

### Acceptance Tests
- [ ] README renders correctly on GitHub
- [ ] All links are valid
- [ ] New developer can onboard in < 30 minutes using README alone

---

## P4-002: Create data_dictionary.md

**Assigned to:** Agent 5 (Documenter)
**Dependencies:** P2-013 (dbt docs exist)
**Estimate:** 2 hours
**Phase:** 4

### Description
Comprehensive data dictionary documenting all tables, columns, and data transformations.

### Acceptance Criteria
- [ ] File: `docs/data_dictionary.md`
- [ ] Section: "Raw Data Tables" - 6 raw_fred_* tables
  - Table name, grain, refresh frequency, row count
  - Columns: name, type, description, example values
- [ ] Section: "Staging Models" - 6 stg_fred_* views
  - Transformation logic (what changed from raw)
  - Column mapping (raw → staging)
- [ ] Section: "Intermediate Models" - 6 intermediate transforms
  - Formula/logic for YoY, rolling avg, recession risk, correlations
  - Input columns, output columns
  - Example calculations
- [ ] Section: "Mart Tables" - 3 mart_* tables
  - Business context and use cases
  - Grain and uniqueness constraints
  - Key metrics definitions
- [ ] Section: "Lineage" - data flow diagram (text or image)
- [ ] Column-level documentation: description, unit, format, valid range
- [ ] Example queries for common analytics questions
- [ ] Links to FRED documentation for each series

### Acceptance Tests
- [ ] Every column in every table documented
- [ ] Formulas are mathematically correct and testable
- [ ] Example values are realistic (not placeholder)

---

## P4-003: Create setup_guide.md for New Team Members

**Assigned to:** Agent 5 (Documenter)
**Dependencies:** P4-001 (README)
**Estimate:** 2 hours
**Phase:** 4

### Description
Step-by-step guide for onboarding new developers to the project.

### Acceptance Criteria
- [ ] File: `docs/setup_guide.md`
- [ ] Section: "Prerequisites" - Python 3.10+, git, IDE recommendations
- [ ] Section: "Access Setup" - how to request Supabase/FRED API credentials
- [ ] Section: "Local Development Environment"
  1. Clone repo
  2. Create Python venv
  3. Pip install requirements
  4. Create .env file (from .env.example, with real credentials)
  5. Test: `dbt debug`
  6. Test: `python -c "import fred_client; print('OK')"`
- [ ] Section: "IDE Setup" - VSCode extensions (dbt Power User, Python, Pylint)
- [ ] Section: "Running Local Pipelines" - how to test code locally before commit
- [ ] Section: "GitHub & Branching" - branch naming, PR process, code review
- [ ] Section: "Testing Locally" - run dbt test, run pytest, check secrets
- [ ] Section: "Debugging Tips" - common errors and solutions
- [ ] Section: "Slack Channels & Communication" - where to ask questions
- [ ] Expected time to complete: 30 minutes
- [ ] Checklist: developer should be able to run full pipeline after setup

### Acceptance Tests
- [ ] Tested by onboarding a new team member
- [ ] All steps work end-to-end
- [ ] Time to first successful pipeline run: < 30 min

---

## P4-004: Create quality_monitoring.md

**Assigned to:** Agent 5 (Documenter) + Agent 3 (Quality)
**Dependencies:** P3-004, P3-006, P3-007 (quality checks, dashboards)
**Estimate:** 2 hours
**Phase:** 4

### Description
Guide for monitoring data quality, interpreting metrics, and responding to alerts.

### Acceptance Criteria
- [ ] File: `docs/quality_monitoring.md`
- [ ] Section: "Quality Metrics Definitions"
  - Data freshness (days since last update)
  - Completeness (% non-null)
  - Uniqueness (duplication count)
  - Validity (rows in valid range)
  - Consistency (YoY/period-over-period trends)
- [ ] Section: "Pre-Ingestion Checks" - what happens before data enters warehouse
- [ ] Section: "Post-Transform Checks" - what happens after dbt run
- [ ] Section: "Dashboard Guide" - how to read Metabase quality monitor
- [ ] Section: "Alert Types & Actions"
  - GREEN (PASS): everything nominal
  - YELLOW (WARNING): investigate, may need manual action
  - RED (FAIL): pipeline halted, immediate action required
- [ ] Section: "Recovery Procedures"
  - Data duplication: run dedup script
  - Missing data: trigger backfill
  - Quality threshold exceeded: rollback dbt version
- [ ] Section: "SLA & Reporting" - expected uptime, reporting to stakeholders
- [ ] Historical quality metrics archived (monthly summaries)

### Acceptance Tests
- [ ] Team understands quality expectations and thresholds
- [ ] Can interpret alerts and take corrective action
- [ ] SLA documented and achievable (> 99% uptime)

---

## P4-005: Implement security.md & Security Policy

**Assigned to:** Agent 6 (Security)
**Dependencies:** P3-012 (Phase 3 complete)
**Estimate:** 2 hours
**Phase:** 4

### Description
Document security architecture, threat model, and compliance measures.

### Acceptance Criteria
- [ ] File: `docs/security.md`
- [ ] Section: "Threat Model"
  - Threat: API credentials exposed → Mitigation: .gitignore, secrets rotation
  - Threat: Supabase breach → Mitigation: RLS policies, encryption
  - Threat: GitHub Actions log exposure → Mitigation: secret masking
  - Threat: SQL injection → Mitigation: parameterized queries
  - Threat: Malicious dbt code in PR → Mitigation: code review, dbt parse
- [ ] Section: "Access Control"
  - Supabase RLS policies (if applicable)
  - GitHub repo permissions (who can merge/deploy)
  - FRED API key rotation schedule
  - Secret storage in GitHub encrypted
- [ ] Section: "Data Protection"
  - Encryption in transit: HTTPS/TLS for all APIs
  - Encryption at rest: Supabase default encryption
  - Data retention: raw_fred_* kept 2 years, analytics 5+ years
  - Data deletion: audit_secrets.py ensures no leakage
- [ ] Section: "Compliance"
  - No PII in data (FRED is public economic data)
  - No compliance frameworks required (non-regulated)
  - But: SOC2 or ISO27001 readiness practices followed
- [ ] Section: "Incident Response Plan"
  - Suspected breach: immediately rotate FRED API key
  - Data loss: restore from automated Supabase backups
  - Escalation contacts and procedures
- [ ] Section: "Security Checklist for Deployments"
  - Run audit_secrets.py before merge
  - dbt compile and parse succeed
  - All tests pass
  - Code review by tech lead

### Acceptance Tests
- [ ] All threats mitigated with documented controls
- [ ] Team knows incident response procedures
- [ ] Audit trail available for all deployments

---

## P4-006: Implement rls_policies.sql Row-Level Security

**Assigned to:** Agent 6 (Security)
**Dependencies:** P1-006 (raw tables exist)
**Estimate:** 1 hour
**Phase:** 4

### Description
Define Row-Level Security policies in Supabase to restrict data access based on role.

### Acceptance Criteria
- [ ] File: `sql/rls_policies.sql`
- [ ] Enable RLS on all raw_fred_* tables
- [ ] Policy: authenticated users can SELECT all rows (read-only)
- [ ] Policy: only service role can INSERT/UPDATE/DELETE (backfill script)
- [ ] Policy: all authenticated users have same read access (no row filtering needed)
- [ ] RLS disabled for analytics schema (marts are read-only views from raw)
- [ ] Test: INSERT/UPDATE by regular user fails
- [ ] Test: SELECT by authenticated user succeeds
- [ ] Test: Service role (used in workflows) can write
- [ ] Migration file applied to Supabase project

### SQL Structure
```sql
ALTER TABLE raw_fred_gdpc1 ENABLE ROW LEVEL SECURITY;
CREATE POLICY "select_all" ON raw_fred_gdpc1 FOR SELECT USING (true);
CREATE POLICY "insert_service_role" ON raw_fred_gdpc1
  FOR INSERT
  WITH CHECK (current_user_id() = auth.uid() OR current_role() = 'service_role');
```

---

## P4-007: Implement hardened_gitignore & Secret Scanning

**Assigned to:** Agent 6 (Security)
**Dependencies:** P1-011 (.gitignore created)
**Estimate:** 1 hour
**Phase:** 4

### Description
Reinforce .gitignore and implement secret scanning in CI/CD pipeline.

### Acceptance Criteria
- [ ] `.gitignore` reviewed and hardened:
  - `.env*` (all variants)
  - `credentials/`, `secrets/`
  - `*.pem`, `*.key` (SSL keys)
  - `*.log` (logs may contain secrets)
  - `.aws/`, `.gcp/` (cloud credentials)
- [ ] GitHub Advanced Security enabled (if available)
- [ ] GitGuardian scanning enabled (free tier available)
- [ ] `audit_secrets.py` run on every commit (pre-commit hook)
- [ ] Workflow: `.github/workflows/security_scan.yml`
  - Trigger: on every push to main/develop
  - Run: audit_secrets.py
  - Run: dbt parse (catches SQL injection attempts)
  - Run: truffleHog scan (industry standard)
  - Fail if secrets detected
- [ ] Pre-commit hook installed: prevents commits with secrets

### Acceptance Tests
```bash
# Test: try to commit .env (should fail)
echo "SECRET_KEY=abc123" > .env
git add .env
git commit -m "test"  # Should fail with pre-commit hook
```

---

## P4-008: Create GitHub SECURITY.md & Vulnerability Policy

**Assigned to:** Agent 6 (Security)
**Dependencies:** P4-005 (security.md)
**Estimate:** 1 hour
**Phase:** 4

### Description
Define security reporting procedures and vulnerability disclosure policy.

### Acceptance Criteria
- [ ] File: `SECURITY.md` at project root (GitHub standard location)
- [ ] Section: "Reporting a Vulnerability"
  - Do NOT create public GitHub issue
  - Email: security@[org].com with details
  - Do NOT include actual credentials or exploit code
  - Expected response time: < 24 hours
- [ ] Section: "Supported Versions" - which releases get security patches
- [ ] Section: "Security Advisories" - list of fixed vulnerabilities (if any)
- [ ] Section: "Dependency Updates" - how we keep packages patched
  - Automated dependabot alerts
  - Monthly manual reviews
  - Critical fixes within 24 hours
- [ ] Section: "Contact & Escalation"
  - Primary: security contact
  - Escalation: tech lead
  - Out-of-band communication if needed

### Acceptance Tests
- [ ] Repository settings show SECURITY.md in security tab
- [ ] Contact email is monitored
- [ ] Policy is clear to external reporters

---

## P4-009: Final Security Audit & Hardening Review

**Assigned to:** Agent 6 (Security) with Agent 0 (PM)
**Dependencies:** P4-006, P4-007, P4-008
**Estimate:** 2 hours
**Phase:** 4

### Description
Comprehensive security review of entire system before production launch.

### Acceptance Criteria
- [ ] Checklist completed:
  - [ ] Zero secrets in git history (audit_secrets.py clean)
  - [ ] All dependencies at current/recent versions (dbt, requests, psycopg2, etc.)
  - [ ] GitHub Actions workflows use security best practices (no hardcoded secrets, use secrets store)
  - [ ] Supabase RLS policies enabled and tested
  - [ ] .gitignore comprehensive
  - [ ] SECURITY.md published
  - [ ] security.md documentation complete
  - [ ] audit_secrets.py runs on every PR
  - [ ] No open/high-severity CVEs in dependencies
  - [ ] Logs do not contain secrets (verified in GitHub Actions)
  - [ ] API key rotation procedure documented
  - [ ] Incident response plan communicated to team
- [ ] Penetration test results (if applicable): passed
- [ ] Third-party security scan (if required by org): passed
- [ ] Security sign-off from tech lead obtained

### Acceptance Tests
```bash
# Run full security check
python audit_secrets.py
# Expected: "0 secrets detected"
pip check
# Expected: "No broken requirements found"
gh repo view --json securityPolicies
# Expected: SECURITY.md is published
```

---

## P4-010: Phase 4 Final Review & Production Readiness

**Assigned to:** Agent 0 (PM)
**Dependencies:** P4-001 through P4-009
**Estimate:** 2 hours
**Phase:** 4

### Description
Final gate review: verify all deliverables complete, team trained, and production-ready.

### Acceptance Criteria
- [ ] Checklist:
  - [ ] Phase 4 deliverables complete (README, data dict, setup guide, quality monitoring, security docs)
  - [ ] All 48 tickets completed
  - [ ] 7-day stability test passed (Phase 3)
  - [ ] Security audit passed (Phase 4)
  - [ ] Team training completed (setup_guide walked through by new member)
  - [ ] Metabase dashboards operational and shared
  - [ ] Runbooks and documentation reviewed by team
  - [ ] Knowledge transfer session completed
  - [ ] Escalation procedures practiced (dry-run failure scenario)
  - [ ] Backup and recovery procedures documented and tested
- [ ] Definition of Done met
- [ ] Go/no-go decision made

### Acceptance Tests
- [ ] Production launch approved
- [ ] Team has confidence to operate independently
- [ ] Zero critical issues outstanding

---

## P4-011: Production Launch & Handoff

**Assigned to:** Agent 0 (PM) with all agents
**Dependencies:** P4-010 (final review)
**Estimate:** 2 hours
**Phase:** 4

### Description
Execute production launch, activate monitoring, and hand off to operations team.

### Acceptance Criteria
- [ ] Actions:
  - [ ] Deploy daily_pipeline.yml to production (remove dry-run)
  - [ ] Activate Slack alerts (enable notifications)
  - [ ] Publish Metabase dashboards to stakeholders
  - [ ] Announce go-live in Slack
  - [ ] Start post-launch monitoring (first 24 hours)
  - [ ] Gather feedback from stakeholders
  - [ ] Document lessons learned
- [ ] Post-Launch Monitoring (24 hours):
  - [ ] All 7 daily runs successful
  - [ ] No quality alerts
  - [ ] Dashboards update correctly
  - [ ] Team available for any ad-hoc issues
- [ ] Handoff:
  - [ ] Ownership assigned (Agent 1 or 4 as primary on-call)
  - [ ] Secondary on-call assigned (tech lead)
  - [ ] Runbook accessible to team
  - [ ] Escalation contacts posted in Slack
  - [ ] Post-launch retro scheduled (1 week after launch)

### Acceptance Tests
- [ ] Pipeline runs successfully in production
- [ ] Stakeholders can access dashboards
- [ ] No data quality issues
- [ ] Team confident in operational procedures

---

# Summary of Tickets by Agent

| Agent | Role | Tickets | Est. Hours |
|-------|------|---------|-----------|
| Agent 0 | PM | P1-012, P2-015, P3-012, P4-010, P4-011 | 9 |
| Agent 1 | Ingestor | P1-001 to P1-012 (all) | 27 |
| Agent 2 | Transformer | P2-001 to P2-015 (all) | 77 |
| Agent 3 | Quality Guardian | P1-008, P1-009, P2-011, P2-014, P3-004, P3-007, P3-009, P4-004 | 34 |
| Agent 4 | Orchestrator | P3-001 to P3-012 (all) | 28 |
| Agent 5 | Documenter | P2-013, P4-001 to P4-004 | 22 |
| Agent 6 | Security | P1-010, P1-011, P4-005 to P4-009 | 13 |
| **TOTAL** | | **48 tickets** | **312 hours** |

---

**Document Owner:** Agent 0 (PM)
**Last Updated:** 2026-03-20
**Next Update:** As work progresses and estimates refine
