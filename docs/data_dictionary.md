# Data Dictionary

Complete reference for all tables, views, and columns in the US Economy Pulse Pipeline.

## Table of Contents

1. [Mart Tables (Analytics Layer)](#mart-tables)
2. [Staging Tables (Raw Cleaned)](#staging-tables)
3. [Quality Monitoring Tables](#quality-tables)

---

## Mart Tables

### fct_economic_indicators_monthly

**Description**: Primary fact table with all monthly economic indicators in a single denormalized table. One row per month, fully joined across all indicator sources. This is the central table for analysis, BI tools, and dashboards.

**Grain**: One row per calendar month (first observation date of the month)

**Materialization**: Table (indexed on `period_date_key`, year, month)

**Update Frequency**: Daily (via incremental upsert)

**Data Retention**: Full history from January 2000 onward

| Column | Data Type | Description | Example | Notes |
|--------|-----------|-------------|---------|-------|
| period_date_key | date | The month-end date (primary key) | 2024-01-31 | Unique; used for time-series joins |
| year | integer | Calendar year | 2024 | 4-digit year |
| month | integer | Month of year | 1 | 1-12; enforced via dbt test |
| year_month | text | YYYY-MM format | 2024-01 | Useful for grouping, filtering |
| cpi_index | numeric(10,2) | Consumer Price Index value | 314.87 | Base: 1982-1984 = 100; from FRED CPIAUCSL |
| yoy_inflation_rate_pct | numeric(6,3) | Year-over-year inflation | 3.420 | Percent; calculated in `int_cpi_inflation_rates` |
| inflation_severity_category | text | Inflation classification | Moderate | Enum: 'Mild' (<2.5%), 'Moderate' (2.5-4%), 'High' (4-5%), 'Severe' (>5%) |
| cpi_mom_change_pct | numeric(6,3) | Month-over-month CPI change | 0.312 | Percent; calculated in `int_cpi_inflation_rates` |
| unemployment_rate_pct | numeric(5,2) | Civilian unemployment rate | 3.80 | Percent; from FRED UNRATE |
| unemployment_yoy_change_pct | numeric(6,3) | YoY change in unemployment | -0.450 | Percent; negative = improving labor market |
| unemployment_trend | text | Labor market direction | Declining | Enum: 'Rising', 'Declining', 'Flat'; signals from dbt logic |
| is_labor_market_healthy | boolean | Flag for healthy labor conditions | true | TRUE if unemployment < 5% and declining |
| fedfunds_rate_pct | numeric(6,3) | Effective Federal Funds Rate | 5.330 | Percent; from FRED FEDFUNDS |
| fedfunds_direction | text | Fed rate movement | Rising | Enum: 'Rising', 'Falling', 'Flat' |
| sentiment_index | numeric(8,2) | Consumer sentiment index | 71.40 | Range ~50-120; from FRED UMCSENT |
| sentiment_outlook | text | Sentiment classification | Neutral | Enum: 'Pessimistic' (<65), 'Neutral' (65-80), 'Optimistic' (>80) |
| housing_starts_thousands | numeric(8,2) | Total housing starts | 1247.50 | Thousands of units; from FRED HOUST |
| data_completeness_score | integer | Count of available indicators | 6 | 0-6; flags rows with missing data |
| is_data_complete | boolean | All indicators present | true | TRUE if `data_completeness_score >= 4` |
| dbt_loaded_at | timestamp | Timestamp when row was loaded | 2024-02-15 08:12:33 | UTC; set by dbt at runtime |

**Primary Key**: `period_date_key` (unique constraint via dbt test)

**Indexes**:
- (period_date_key) BTREE — for time-series queries
- (year, month) BTREE — for time grouping

**Typical Query**:
```sql
SELECT period_date_key, cpi_index, yoy_inflation_rate_pct, unemployment_rate_pct
FROM analytics.fct_economic_indicators_monthly
WHERE period_date_key >= '2023-01-01'
ORDER BY period_date_key DESC;
```

---

### fct_economic_indicators_quarterly

**Description**: Quarterly-aligned version of the monthly fact table. Contains the same indicators but with quarterly grain for analysis requiring quarterly alignment (e.g., GDP is inherently quarterly).

**Grain**: One row per quarter (Q1, Q2, Q3, Q4)

**Materialization**: Table

**Update Frequency**: Quarterly (updated when new GDP data arrives)

| Column | Data Type | Description |
|--------|-----------|-------------|
| period_date_key | date | Quarter-end date (Q1→03-31, Q2→06-30, Q3→09-30, Q4→12-31) |
| year | integer | Calendar year |
| quarter | integer | Quarter number (1-4) |
| gdp_billions_usd | numeric(12,2) | Real GDP (chained 2012 dollars); from FRED GDPC1 |
| gdp_yoy_growth_pct | numeric(6,3) | Year-over-year GDP growth |
| *inflation / unemployment / fedfunds / sentiment* | numeric | Quarterly average of monthly indicators |
| is_recession | boolean | TRUE if 2+ consecutive quarters of negative GDP growth |
| dbt_loaded_at | timestamp | Load timestamp |

---

### fct_employment_analysis

**Description**: Specialized fact table for labor market analysis. Focuses on unemployment dynamics with 3/6/12-month rolling averages and trend signals.

**Grain**: One row per month

**Materialization**: Table

| Column | Data Type | Description |
|--------|-----------|-------------|
| period_date_key | date | Month-end date |
| unemployment_rate_pct | numeric(5,2) | Current unemployment |
| unemployment_3mo_avg | numeric(5,2) | 3-month rolling average |
| unemployment_6mo_avg | numeric(5,2) | 6-month rolling average |
| unemployment_12mo_avg | numeric(5,2) | 12-month rolling average |
| yoy_change_pct | numeric(6,3) | Year-over-year change |
| trend_direction | text | 'Rising', 'Declining', 'Flat' |
| is_labor_market_healthy | boolean | Unemployment < 5% |
| jobs_outlook | text | 'Strong', 'Moderate', 'Weak' (derived from trends) |
| dbt_loaded_at | timestamp | Load timestamp |

**Use Cases**: Labor market reports, employment forecasting, hiring trend analysis

---

### fct_inflation_analysis

**Description**: Specialized fact table for inflation monitoring. Combines CPI, YoY rates, severity categories, and rolling averages for comprehensive inflation tracking.

**Grain**: One row per month

**Materialization**: Table

| Column | Data Type | Description |
|--------|-----------|-------------|
| period_date_key | date | Month-end date |
| cpi_index | numeric(10,2) | CPI value (base 1982-1984 = 100) |
| yoy_inflation_rate_pct | numeric(6,3) | Year-over-year inflation |
| mom_change_pct | numeric(6,3) | Month-over-month change |
| inflation_3mo_avg | numeric(6,3) | 3-month rolling average |
| inflation_6mo_avg | numeric(6,3) | 6-month rolling average |
| inflation_12mo_avg | numeric(6,3) | 12-month rolling average |
| inflation_severity_category | text | 'Mild', 'Moderate', 'High', 'Severe' |
| fed_response_needed | boolean | TRUE if inflation > 4% (policy trigger) |
| dbt_loaded_at | timestamp | Load timestamp |

**Use Cases**: Inflation tracking, Fed policy monitoring, purchasing power analysis

---

### fct_recession_analysis

**Description**: Quarterly fact table for recession probability and indicators. Combines GDP with leading indicators (unemployment, sentiment, housing starts) to signal recession risk.

**Grain**: One row per quarter

**Materialization**: Table

| Column | Data Type | Description |
|--------|-----------|-------------|
| period_date_key | date | Quarter-end date |
| year | integer | Calendar year |
| quarter | integer | Quarter number |
| gdp_billions_usd | numeric(12,2) | Real GDP |
| gdp_growth_rate_pct | numeric(6,3) | Quarterly growth rate |
| consecutive_negative_growth | integer | Consecutive quarters of negative growth (0-2+) |
| is_technical_recession | boolean | TRUE if 2+ consecutive quarters of negative growth |
| unemployment_rate_pct | numeric(5,2) | Unemployment at quarter-end |
| unemployment_rising | boolean | TRUE if unemployment increased vs prior quarter |
| housing_starts_thousands | numeric(8,2) | Housing starts (leading indicator) |
| consumer_sentiment_index | numeric(8,2) | Sentiment at quarter-end |
| recession_risk_score | numeric(5,2) | 0-100 composite risk score |
| recession_signals | integer | Count of negative signals (0-5) |
| dbt_loaded_at | timestamp | Load timestamp |

**Recession Risk Score Formula**:
- +25 points: 2+ quarters negative GDP growth
- +20 points: Unemployment rising
- +15 points: Consumer sentiment declining
- +15 points: Housing starts declining
- +10 points: YoY GDP growth < 0%
- +15 points: Each additional consecutive negative quarter

Score > 50 indicates elevated recession risk.

---

### dim_economic_periods

**Description**: Conformed dimension table for time-based grouping and filtering. Provides fiscal/calendar/business cycle classifications for all dates.

**Grain**: One row per calendar month

**Materialization**: Table

| Column | Data Type | Description |
|--------|-----------|-------------|
| period_date_key | date | Month-end date (primary key) |
| year | integer | Calendar year |
| month | integer | Month (1-12) |
| quarter | integer | Quarter (1-4) |
| year_quarter | text | YYYY-Q format (e.g., 2024-Q1) |
| year_month | text | YYYY-MM format |
| is_recession_period | boolean | TRUE if in NBER-defined recession |
| expansion_phase | text | Phase of economic cycle |
| dbt_loaded_at | timestamp | Load timestamp |

---

### vw_economic_overview_dashboard

**Description**: Pre-joined view optimized for BI tools (Metabase, Tableau, Power BI). Denormalizes fact + dimension tables with common calculations already done.

**Materialization**: View (no materialization; reads from fct_economic_indicators_monthly + dim_economic_periods)

**Columns**: All columns from fct_economic_indicators_monthly

**Use Cases**: Dashboards, BI exports, real-time reporting

**Example Query**:
```sql
SELECT * FROM analytics.vw_economic_overview_dashboard
WHERE period_date_key >= CURRENT_DATE - INTERVAL '1 year'
ORDER BY period_date_key DESC;
```

---

## Staging Tables

Staging tables clean and standardize raw FRED data. All are **views** (not materialized).

### stg_gdp

**Source**: `staging.raw_gdp` (FRED GDPC1)

**Description**: Real Gross Domestic Product, quarterly.

| Column | Data Type | Description |
|--------|-----------|-------------|
| period_date_key | date | Quarter-end date |
| series_code | text | 'GDPC1' |
| gdp_billions_usd | numeric(18,2) | Real GDP in billions (2012 dollars) |
| data_source | text | 'FRED' |
| indicator_type | text | 'Economic Output' |
| indicator_name | text | 'GDPC1' |
| loaded_at | timestamp | When raw data was ingested |
| is_latest | boolean | TRUE for most recent observation |
| dbt_loaded_at | timestamp | When staging model ran |

---

### stg_cpi

**Source**: `staging.raw_cpi` (FRED CPIAUCSL)

**Description**: Consumer Price Index for All Urban Consumers, monthly.

| Column | Data Type | Description |
|--------|-----------|-------------|
| period_date_key | date | Month-end date |
| series_code | text | 'CPIAUCSL' |
| cpi_index | numeric(18,2) | CPI value (1982-1984 = 100) |
| data_source | text | 'FRED' |
| indicator_type | text | 'Prices' |
| indicator_name | text | 'CPIAUCSL' |
| loaded_at | timestamp | Ingestion timestamp |
| is_latest | boolean | TRUE for most recent |
| dbt_loaded_at | timestamp | Staging model runtime |

---

### stg_unemployment_rate

**Source**: `staging.raw_unemployment` (FRED UNRATE)

| Column | Data Type | Description |
|--------|-----------|-------------|
| period_date_key | date | Month-end date |
| series_code | text | 'UNRATE' |
| unemployment_rate_pct | numeric(18,2) | Unemployment % |
| data_source | text | 'FRED' |
| indicator_type | text | 'Labor Market' |
| indicator_name | text | 'UNRATE' |
| loaded_at | timestamp | Ingestion timestamp |
| is_latest | boolean | TRUE for most recent |
| dbt_loaded_at | timestamp | Staging model runtime |

---

### stg_federal_funds_rate

**Source**: `staging.raw_federal_funds` (FRED FEDFUNDS)

| Column | Data Type | Description |
|--------|-----------|-------------|
| period_date_key | date | Month-end date |
| series_code | text | 'FEDFUNDS' |
| fedfunds_rate_pct | numeric(18,2) | Fed Funds rate % |
| data_source | text | 'FRED' |
| indicator_type | text | 'Policy Rate' |
| indicator_name | text | 'FEDFUNDS' |
| loaded_at | timestamp | Ingestion timestamp |
| is_latest | boolean | TRUE for most recent |
| dbt_loaded_at | timestamp | Staging model runtime |

---

### stg_consumer_sentiment

**Source**: `staging.raw_consumer_sentiment` (FRED UMCSENT)

| Column | Data Type | Description |
|--------|-----------|-------------|
| period_date_key | date | Month-end date |
| series_code | text | 'UMCSENT' |
| sentiment_index | numeric(18,2) | Sentiment index (50-120) |
| data_source | text | 'FRED' |
| indicator_type | text | 'Sentiment' |
| indicator_name | text | 'UMCSENT' |
| loaded_at | timestamp | Ingestion timestamp |
| is_latest | boolean | TRUE for most recent |
| dbt_loaded_at | timestamp | Staging model runtime |

---

### stg_housing_starts

**Source**: `staging.raw_housing_starts` (FRED HOUST)

| Column | Data Type | Description |
|--------|-----------|-------------|
| period_date_key | date | Month-end date |
| series_code | text | 'HOUST' |
| housing_starts_thousands | numeric(18,2) | Housing starts (thousands of units) |
| data_source | text | 'FRED' |
| indicator_type | text | 'Construction' |
| indicator_name | text | 'HOUST' |
| loaded_at | timestamp | Ingestion timestamp |
| is_latest | boolean | TRUE for most recent |
| dbt_loaded_at | timestamp | Staging model runtime |

---

## Quality Tables

### quality_checks

**Description**: Audit log of all dbt tests and Python quality checks. Every check (pass, fail, error) is logged here for historical tracking and alerting.

**Grain**: One row per check execution

**Materialization**: Table

| Column | Data Type | Description |
|--------|-----------|-------------|
| check_id | uuid | Unique check execution ID |
| check_name | text | Name of check (e.g., 'test_not_null_cpi_index') |
| check_type | text | 'dbt_test', 'freshness', 'anomaly', 'completeness' |
| indicator | text | Which indicator was checked (e.g., 'CPI', 'UNEMPLOYMENT') |
| table_name | text | Table being checked (e.g., 'analytics.fct_economic_indicators_monthly') |
| status | text | 'PASS', 'FAIL', 'ERROR' |
| failure_count | integer | Number of rows that failed (if applicable) |
| error_message | text | Details if status = 'FAIL' or 'ERROR' |
| checked_at | timestamp | When check ran |
| checked_by | text | 'dbt' or 'python' |

**Example Query**:
```sql
-- Find all failed checks in the last 7 days
SELECT check_name, status, failure_count, checked_at
FROM quality.quality_checks
WHERE status != 'PASS' AND checked_at >= NOW() - INTERVAL '7 days'
ORDER BY checked_at DESC;
```

---

### quality_baselines

**Description**: Rolling statistics for each indicator used in anomaly detection. Tracks mean, stddev, min, max, and percentiles for z-score calculation.

**Grain**: One row per indicator per baseline period (monthly refresh)

**Materialization**: Table

| Column | Data Type | Description |
|--------|-----------|-------------|
| baseline_id | uuid | Unique baseline ID |
| indicator | text | Which indicator (e.g., 'CPI', 'UNEMPLOYMENT') |
| baseline_period | date | Start date of the baseline window (e.g., 2024-01-01) |
| window_months | integer | Number of months in baseline (typically 24) |
| mean_value | numeric(18,4) | Average value in window |
| stddev_value | numeric(18,4) | Standard deviation |
| min_value | numeric(18,4) | Minimum value in window |
| max_value | numeric(18,4) | Maximum value in window |
| p25_value | numeric(18,4) | 25th percentile |
| p75_value | numeric(18,4) | 75th percentile |
| p95_value | numeric(18,4) | 95th percentile |
| last_updated | timestamp | When baseline was recalculated |

**Usage**: Anomaly detection calculates `z_score = (current_value - mean) / stddev`. If `|z_score| > 3`, value is flagged as anomalous.

---

## Raw Tables (fred_raw Schema)

Raw data from FRED API is stored in one table per indicator. These are created by Python ingestion and upserted daily.

| Table | Series ID | Description |
|-------|-----------|-------------|
| fred_raw.raw_gdp | GDPC1 | Real GDP |
| fred_raw.raw_cpi | CPIAUCSL | Consumer Price Index |
| fred_raw.raw_unemployment | UNRATE | Unemployment Rate |
| fred_raw.raw_federal_funds | FEDFUNDS | Federal Funds Rate |
| fred_raw.raw_consumer_sentiment | UMCSENT | Consumer Sentiment |
| fred_raw.raw_housing_starts | HOUST | Housing Starts |

**Schema** (all raw tables):

| Column | Data Type | Description |
|--------|-----------|-------------|
| observation_date | date | Date of observation |
| series_id | text | FRED series ID |
| value | numeric | Raw value from FRED |
| ingested_at | timestamp | When Python fetched this |

These tables are **internal** — do not query them directly. Use staging views instead.

---

## Intermediate Tables

Intermediate tables contain business logic transformations. They bridge staging (raw) and marts (analytics). Typically not queried directly by end users.

| Table | Description |
|-------|-------------|
| int_cpi_inflation_rates | CPI with YoY%, MoM%, and severity categories |
| int_labor_market_metrics | Unemployment with trends and health flags |
| int_gdp_with_yoy_change | GDP with growth rates and regimes |
| int_financial_conditions | Fed rate + sentiment with classifications |
| int_economic_rolling_averages | All indicators with 3/6/12-month rolling averages |
| int_recession_indicators | Recession probability and flags |
| int_indicator_cross_correlations | Pairwise correlations between indicators |

---

## Summary

**For Analysis**: Query `analytics.fct_economic_indicators_monthly` or use the dashboard view `vw_economic_overview_dashboard`.

**For Specialized Analysis**: Use focused fact tables like `fct_employment_analysis`, `fct_inflation_analysis`, `fct_recession_analysis`.

**For Quality Insights**: Check `quality.quality_checks` for recent test results and `quality.quality_baselines` for anomaly detection context.

**For Schema Details**: Use dbt documentation (`dbt docs serve`) or this dictionary.
