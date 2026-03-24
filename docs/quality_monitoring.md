# Data Quality Monitoring

Comprehensive documentation for the US Economy Pulse Pipeline's hybrid data quality system.

## Overview

The pipeline implements a **two-layer quality approach**:

1. **dbt Tests** (SQL-based, declarative)
   - Embedded in model YAML definitions
   - Standardized checks: not-null, unique, accepted values, range validation
   - Custom tests: outlier detection, spike detection, value range validation
   - Run as part of `dbt test` command
   - Failures block deployment in CI/CD

2. **Python Runtime Checks** (procedural, analytical)
   - Freshness validation (data currency by indicator)
   - Anomaly detection (z-score based, configurable sensitivity)
   - Completeness monitoring (null % by table)
   - Cross-indicator validation (logical consistency)
   - Scheduled after dbt transformations
   - Slack notifications for failures

Both layers feed into the `quality_checks` audit table for historical tracking and alerting.

---

## Quality Checks Matrix

Comprehensive reference of all checks: when they run, what they validate, and how they fail.

### dbt-Native Checks

These run with `dbt test` and check data as it loads into marts.

| Check | Type | Table | Frequency | Severity | Description |
|-------|------|-------|-----------|----------|-------------|
| not_null_period_date_key | Data test | fct_economic_indicators_monthly | Every dbt run | ERROR | Period key must not be null |
| unique_period_date_key | Data test | fct_economic_indicators_monthly | Every dbt run | ERROR | Period key must be unique (one row per month) |
| valid_month | Data test | fct_economic_indicators_monthly | Every dbt run | ERROR | Month must be 1-12 |
| accepted_inflation_category | Data test | fct_economic_indicators_monthly | Every dbt run | WARNING | Inflation category is one of: Mild, Moderate, High, Severe |
| accepted_unemployment_trend | Data test | fct_economic_indicators_monthly | Every dbt run | WARNING | Unemployment trend is one of: Rising, Declining, Flat |
| valid_unemployment_range | Data test | fct_employment_analysis | Every dbt run | WARNING | Unemployment must be 0-15% |
| valid_cpi_range | Data test | fct_inflation_analysis | Every dbt run | WARNING | CPI must be 30-400 (index) |
| valid_fed_rate_range | Data test | fct_economic_indicators_monthly | Every dbt run | WARNING | Fed Funds rate must be 0-20% |
| valid_sentiment_range | Data test | fct_economic_indicators_monthly | Every dbt run | WARNING | Sentiment index must be 50-120 |
| valid_housing_starts_range | Data test | fct_economic_indicators_monthly | Every dbt run | WARNING | Housing starts must be 400-2,500 thousands |
| outlier_detection_cpi | Generic test | fct_inflation_analysis | Every dbt run | WARNING | CPI z-score must be < 3 |
| outlier_detection_unemployment | Generic test | fct_employment_analysis | Every dbt run | WARNING | Unemployment z-score must be < 3 |
| outlier_detection_gdp | Generic test | fct_economic_indicators_quarterly | Every dbt run | WARNING | GDP z-score must be < 3 |
| month_over_month_spike_cpi | Generic test | fct_inflation_analysis | Every dbt run | WARNING | CPI MoM change must be < 25% |
| month_over_month_spike_unemployment | Generic test | fct_employment_analysis | Every dbt run | WARNING | Unemployment change must be < 5% |

---

### Python Runtime Checks

These run post-dbt and validate data freshness, completeness, and consistency.

| Check | Frequency | Indicator(s) | Failure Condition | Response |
|-------|-----------|--------------|-------------------|----------|
| **Freshness Validation** | Daily after dbt run | All 6 | GDP > 60 days old, CPI > 20 days, Unemployment > 15 days, Fed Funds > 15 days, Sentiment > 20 days, Housing > 25 days | WARN in logs; ALERT via Slack |
| **Completeness Check** | Daily after dbt run | All 6 | Any indicator < 90% non-null in fact tables | WARN in logs; log to quality_checks |
| **CPI Anomaly Detection** | Daily after dbt run | CPI | Z-score > 3 (>3σ deviation from baseline) | ALERT via Slack; investigate |
| **Unemployment Anomaly** | Daily after dbt run | Unemployment | Z-score > 3 | ALERT via Slack; investigate |
| **GDP Anomaly** | Daily after dbt run | GDP | Z-score > 3 | ALERT via Slack; investigate |
| **Correlation Check** | Weekly | GDP, CPI, Unemployment | GDP and unemployment correlation < 0.5 (typically -0.6 to -0.8) | WARN in logs |
| **Data Consistency** | Daily after dbt run | All | No duplicate observation dates in raw tables | FAIL dbt run; block deployment |

---

## Understanding Failures

### dbt Test Failures

When `dbt test` reports failures:

**Example output:**
```
Failure in test outlier_detection_cpi (models/marts/fct_inflation_analysis.yml)
  Got 1 failure(s), expected 0.
  Failure rows in database:
    cpi_index | period_date_key | z_score
    --------- + --------------- + -------
    425.00    | 2024-03-01      | 3.45
```

**What it means**: CPI value on March 1, 2024 is 3.45 standard deviations above the historical baseline. This is a statistical anomaly.

**How to debug**:

1. **Check FRED directly**: Visit https://fred.stlouisfed.org/series/CPIAUCSL and verify the value
   - If FRED shows the same value, it's real (e.g., inflation spike)
   - If different, there's an ingestion error

2. **Check raw data**:
```sql
SELECT * FROM fred_raw.raw_cpi
WHERE observation_date = '2024-03-01';
```

3. **Decide**: Is this a real anomaly or a data error?
   - **Real anomaly** (e.g., post-inflation spike): Adjust baseline in `quality_baselines` or accept the flag
   - **Data error** (e.g., value should be 314, not 425): Fix raw data and re-run dbt

4. **Update baseline** (if it's a real new regime):
```sql
UPDATE quality.quality_baselines
SET mean_value = ..., stddev_value = ...
WHERE indicator = 'CPI' AND baseline_period = '2024-01-01';
```

5. **Re-run tests**:
```bash
dbt test --select fct_inflation_analysis
```

### Python Check Failures

Python checks produce different outputs:

**Freshness check failure** (logged and Slack):
```
⚠️  Data Freshness Issue
Indicator: GDP
Last observation: 2024-01-15
Days old: 64
Threshold (ERROR): 60 days
Status: STALE — update expected by 2024-03-16
```

**Anomaly detection failure** (Slack alert):
```
🚨 Anomaly Detected
Indicator: CPI
Current value: 425.00
Baseline mean: 314.50
Z-score: 3.45
Status: INVESTIGATE — beyond 3σ
```

**Completeness failure** (log entry):
```
⚠️  Data Completeness Issue
Table: fct_economic_indicators_monthly
Column: unemployment_rate_pct
Non-null %: 85%
Expected: 95%+
```

---

## How Anomaly Detection Works

The pipeline uses **z-score statistical detection** to flag unusual values.

### Formula

```
z_score = (current_value - baseline_mean) / baseline_stddev
```

Where:
- `baseline_mean`: Average value over the last 24 months (rolling window)
- `baseline_stddev`: Standard deviation over same window
- `current_value`: Most recent observation

### Interpretation

| Z-Score Range | Interpretation | Action |
|----------------|-----------------|--------|
| -1 to +1 | Normal (68% of data) | No alert |
| -2 to -1 or +1 to +2 | Unusual (95% of data) | Monitor, log |
| -3 to -2 or +2 to +3 | Very unusual | Alert, investigate |
| < -3 or > +3 | Extreme outlier (99.7% of data) | 🚨 CRITICAL alert |

### Example: CPI Anomaly

Baseline (24-month window):
- Mean CPI: 314.5
- Std Dev: 3.2

Current observation: CPI = 318.8

```
z_score = (318.8 - 314.5) / 3.2 = 1.34
Status: Normal (within +1σ)
Action: No alert
```

vs.

Current observation: CPI = 425.0 (data corruption?)

```
z_score = (425.0 - 314.5) / 3.2 = 34.5
Status: EXTREME OUTLIER
Action: 🚨 Critical alert, freeze deployment
```

---

## Configuring Thresholds

### dbt Thresholds

Edit `dbt_project/dbt_project.yml` under the `vars` section:

```yaml
vars:
  # Freshness thresholds (days before warning/error)
  gdp_freshness_warn_days: 35
  gdp_freshness_error_days: 60

  cpi_freshness_warn_days: 10
  cpi_freshness_error_days: 20

  unemployment_freshness_warn_days: 8
  unemployment_freshness_error_days: 15

  # Inflation severity thresholds (percent)
  inflation_mild_threshold: 2.5
  inflation_moderate_threshold: 4.0
  inflation_high_threshold: 5.0

  # Expected value ranges (used in generic tests)
  # Already hardcoded in src/ingestion/config.py
```

After editing, re-run dbt:
```bash
dbt run && dbt test
```

### Python Thresholds

Edit `src/quality/anomaly_detector.py`:

```python
# Z-score threshold for anomaly detection
ANOMALY_Z_SCORE_THRESHOLD = 3.0  # Standard: 3σ (99.7% confidence)

# Freshness thresholds (hours)
FRESHNESS_THRESHOLDS = {
    'GDP': 60 * 24,           # 60 days
    'CPI': 20 * 24,           # 20 days
    'Unemployment': 15 * 24,  # 15 days
    # ...
}

# Completeness thresholds (percent non-null)
COMPLETENESS_MIN_PCT = 90  # Alert if < 90% complete
```

After editing, push to GitHub to apply in CI/CD, or run locally:
```bash
python src/quality/freshness_checker.py
python src/quality/anomaly_detector.py
```

---

## Viewing Quality Results

### In Supabase Studio

1. Log into https://supabase.com → Your project
2. Go to **SQL Editor**
3. Run:

```sql
-- Recent quality checks
SELECT check_name, status, failure_count, error_message, checked_at
FROM quality.quality_checks
ORDER BY checked_at DESC
LIMIT 50;

-- Failures only (last 7 days)
SELECT check_name, status, failure_count, error_message
FROM quality.quality_checks
WHERE status != 'PASS' AND checked_at >= NOW() - INTERVAL '7 days'
ORDER BY checked_at DESC;

-- Anomaly baselines for current calculation
SELECT indicator, mean_value, stddev_value, last_updated
FROM quality.quality_baselines
ORDER BY last_updated DESC;
```

### In Slack (if configured)

Quality failures appear in your configured Slack channel with:
- Indicator name and check type
- Failure count and severity
- Brief error message
- Timestamp of failure
- Link to Supabase for deep dive

Example:
```
🚨 Data Quality Alert
━━━━━━━━━━━━━━━━━━━
Check: Outlier Detection
Indicator: CPI
Status: FAILED
Z-score: 3.45 (threshold: 3.0)
Date: 2024-03-20 08:12:33 UTC
Link: https://supabase.com/projects/.../editor

Review in: quality.quality_checks table
```

### In dbt Documentation

After running `dbt docs serve`, view:
- Model descriptions (why each exists)
- Column definitions (what each column means)
- Test results (which tests ran, which passed/failed)
- Lineage diagram (how data flows)

---

## Common Scenarios & Resolution

### Scenario 1: GDP Stale (Released Late by FRED)

**Symptom**: Alert says GDP is 75 days old; threshold is 60.

**Root Cause**: FRED occasionally delays GDP releases; it's a monthly series, so delays are expected.

**Resolution**:
```yaml
# In dbt_project.yml, increase threshold for GDP only
gdp_freshness_warn_days: 50  # Flexible
gdp_freshness_error_days: 90  # Hard stop at 90 days
```

Re-run tests; alert clears when new data arrives.

---

### Scenario 2: CPI Spike Detected (Real Inflation)

**Symptom**: CPI z-score = 4.2; anomaly detected.

**Root Cause**: Legitimate inflation surge (post-pandemic, Fed tightening, etc.)

**Investigation**:
1. Check FRED directly: https://fred.stlouisfed.org/series/CPIAUCSL
2. Verify value matches (if yes, it's real)
3. Review macro context: Is inflation spiking in news? Are other indicators (wages, unemployment) moving with it?

**Resolution**: Accept the anomaly as real. Optionally **update baseline** to adjust for new regime:
```sql
-- Recalculate baseline with 12-month window instead of 24
UPDATE quality.quality_baselines
SET mean_value = 320.1, stddev_value = 2.4, last_updated = NOW()
WHERE indicator = 'CPI';
```

Re-run; z-score normalizes.

---

### Scenario 3: Ingestion Failed Silently

**Symptom**: CPI data hasn't updated in 35 days; no alert fired (threshold is 20 days).

**Root Cause**: Ingestion job crashed without logging.

**Investigation**:
1. Check GitHub Actions logs: `.github/workflows/daily_pipeline.yml`
2. Look for errors in FRED API call (rate limit? API down?)
3. Check Supabase connection in logs

**Resolution**:
```bash
# Manual re-run from local environment
python -m src.ingestion.run_ingestion --incremental

# Check what was fetched
SELECT MAX(observation_date) FROM fred_raw.raw_cpi;
```

If data loads, re-run dbt:
```bash
dbt run && dbt test
```

Review GitHub Actions workflow and add retry logic if needed.

---

### Scenario 4: Unemployment Completeness Low (85%, Threshold 90%)

**Symptom**: Quality check: unemployment completeness = 85%; expected 90%+.

**Root Cause**: Usually a join issue (e.g., some months missing unemployment data).

**Investigation**:
```sql
-- Check for gaps
SELECT COUNT(*) FROM staging.stg_unemployment_rate;
SELECT COUNT(DISTINCT period_date_key) FROM analytics.fct_economic_indicators_monthly
WHERE unemployment_rate_pct IS NOT NULL;

-- Find NULL gaps
SELECT period_date_key FROM analytics.fct_economic_indicators_monthly
WHERE unemployment_rate_pct IS NULL
ORDER BY period_date_key;
```

**Resolution**:
- If missing months are in raw data, check staging model (join may be broken)
- If missing from FRED, data doesn't exist yet
- If join is broken, fix SQL in `int_labor_market_metrics.sql`
- Re-run dbt; completeness metric recovers

---

### Scenario 5: Test Failures on Pull Request

**Symptom**: You added a new indicator (e.g., M2 Money Supply), but dbt tests are failing with type mismatches.

**Root Cause**: New column doesn't have expected range in config, or types don't match.

**Resolution**:
1. Review error message: `Column M2_billions has type text, expected numeric`
2. Fix in staging model SQL (cast to correct type)
3. Add expected_range to `src/ingestion/config.py`
4. Add dbt test in `models/marts/_marts_*.yml`
5. Commit; re-run workflow; tests should pass

---

## Best Practices

1. **Monitor trends, not absolutes**
   - Don't alert on every anomaly; z-score > 3 is already extreme (99.7% confidence)
   - Focus on repeated failures vs. one-off spikes

2. **Baseline regularly**
   - Quarterly: update `quality_baselines` to reflect new economic regime
   - Example: Post-pandemic inflation shifted baseline; adjust after 6-month stabilization

3. **Log everything**
   - All checks flow to `quality_checks` table
   - Use this for audit trails, SLAs, and root-cause analysis

4. **Coordinate with data sources**
   - FRED release calendar is public: https://fred.stlouisfed.org/docs/api/fred/
   - Schedule dbt tests *after* expected release times
   - Add manual lookups for delayed releases

5. **Test in dev first**
   - When tuning thresholds, test locally before pushing to production
   - Use `dbt test --select model_name` to validate specific models

6. **Document anomalies**
   - When you accept a real anomaly (e.g., inflation spike), add comment in SQL
   - Link to FRED observation and macro context
   - Helps future team members understand the data

---

## Monitoring SLAs

Suggested service-level agreements for the pipeline:

| Metric | Target | Warning | Error |
|--------|--------|---------|-------|
| **Data Freshness** | < 5 days | > 5 days | > 15 days |
| **Pipeline Success** | 100% | 99% | < 95% |
| **Test Pass Rate** | 100% | 99% | < 95% |
| **Quality Check Coverage** | 100% | > 90% | < 80% |
| **Incident Resolution** | < 1 hour | < 2 hours | < 4 hours |

---

## Extending Quality Checks

To add a new quality check:

### For dbt Tests

1. Open relevant model YAML (e.g., `models/marts/_marts_core.yml`)
2. Add to the column's `data_tests` section:

```yaml
- name: new_indicator_pct
  description: New indicator as percentage
  data_tests:
    - not_null
    - dbt_expectations.expect_column_values_to_be_between:
        min_value: 0
        max_value: 100
    - dbt_expectations.expect_column_values_to_be_in_type_list:
        column_type_list: ['numeric']
```

3. Run `dbt test` to verify

### For Python Checks

1. Edit `src/quality/anomaly_detector.py` or create new module
2. Add check function:

```python
def check_new_indicator_completeness(db_connection):
    result = db_connection.query(
        "SELECT COUNT(*) as total, COUNT(new_indicator) as non_null "
        "FROM analytics.fct_economic_indicators_monthly"
    )
    pct = (result['non_null'] / result['total']) * 100
    if pct < 90:
        return {'status': 'WARN', 'message': f'Completeness: {pct}%'}
    return {'status': 'PASS'}
```

3. Call from `src/quality/run_checks.py`
4. Log to `quality_checks` table
5. Commit; deploy to GitHub Actions

---

## Contact & Support

- **dbt Test Docs**: https://docs.getdbt.com/reference/node-selection/test-selection
- **FRED API Issues**: Support at https://fred.stlouisfed.org/docs/api/
- **Data Team**: Reach out with quality concerns or false positive alerts

For deep dives on specific indicators, consult the **Data Dictionary** (`data_dictionary.md`).
