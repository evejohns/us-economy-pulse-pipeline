# US Economy Pulse dbt Project - Complete File Manifest

## Overview
Complete dbt transformation pipeline for US economic indicators analysis.
Database: Supabase PostgreSQL | Data Source: FRED API | Grain: Monthly/Quarterly

## Configuration Files

### dbt_project.yml
- Project name, version, profile configuration
- Materialization defaults: staging=view, intermediate=table, marts=table
- Schema routing: staging, intermediate, analytics
- Variable configurations for data freshness thresholds
- Package dependencies declarations

### profiles.yml.example
- Supabase PostgreSQL connection template
- Environment variable configuration
- Connection pooling options (port 5432 or 6543)
- Documentation for setup

### packages.yml
- dbt-utils 1.1.1
- dbt-expectations 0.8.0

## Source Layer

### models/sources.yml
Defines FRED data source with 6 raw tables:
1. **raw_gdp** (GDPC1) - Quarterly, freshness warn 35d / error 60d
2. **raw_cpi** (CPIAUCSL) - Monthly, freshness warn 10d / error 20d
3. **raw_unemployment_rate** (UNRATE) - Monthly, freshness warn 8d / error 15d
4. **raw_federal_funds_rate** (FEDFUNDS) - Monthly, freshness warn 5d / error 15d
5. **raw_consumer_sentiment** (UMCSENT) - Monthly, freshness warn 10d / error 20d
6. **raw_housing_starts** (HOUST) - Monthly, freshness warn 12d / error 25d

All tables include column-level documentation and freshness monitoring.

## Staging Layer (Views)

Standardize raw data with consistent naming and type casting.

### stg_gdp.sql
- GDP data cleaning and normalization
- Rename: observation_date → period_date, value → gdp_billions_usd
- Type casting to numeric(18,2)
- is_latest flag using ROW_NUMBER()
- Output: ~7 columns

### stg_cpi.sql
- CPI data cleaning with numeric(18,4) precision
- Standard transformations: date, type casting
- Output: ~7 columns

### stg_unemployment_rate.sql
- Unemployment data to numeric(6,2)
- Standard staging transformations
- Output: ~7 columns

### stg_federal_funds_rate.sql
- Federal Funds Rate with numeric(6,2) precision
- Output: ~7 columns

### stg_consumer_sentiment.sql
- Sentiment index with numeric(8,2) precision
- Output: ~7 columns

### stg_housing_starts.sql
- Housing Starts with numeric(10,1) precision
- Output: ~7 columns

### _stg_economic_indicators.yml
Schema definition for all 6 staging models:
- Column documentation
- not_null, unique, accepted_values, range tests
- Type validation with dbt_expectations
- Custom range tests for economic bounds

## Intermediate Layer (Tables)

Business logic and analytical transformations.

### int_gdp_with_yoy_change.sql
- Quarter-over-quarter growth (lag by 1)
- Year-over-year growth (lag by 4)
- Flags for negative growth periods
- Grain: quarterly
- Output: 14 columns including growth metrics

### int_cpi_inflation_rates.sql
- Year-over-year inflation rate
- Month-over-month changes
- 3-month rolling inflation average
- Severity categorization (Mild, Moderate, High, Severe)
- Grain: monthly
- Output: 13 columns

### int_labor_market_metrics.sql
- YoY unemployment changes
- 3-month rolling average
- Trend direction (Rising, Declining, Flat)
- Labor market health flag
- Grain: monthly
- Output: 13 columns

### int_financial_conditions.sql
- Federal Funds Rate with direction
- Consumer Sentiment with outlook
- Full outer join on monthly grain
- Financial stress elevated flag
- Output: 12 columns

### int_economic_rolling_averages.sql
- UNION of 5 rolling average streams
- 3M, 6M, 12M windows
- Covers: CPI, unemployment, Fed funds, sentiment, housing
- Grain: monthly
- Output: 7 columns

### int_recession_indicators.sql
- Joins GDP, unemployment, inflation, sentiment
- Consecutive negative quarters calculation
- Recession risk level (Low, Emerging, Moderate, High)
- Recession intensity score (0-10)
- Grain: quarterly
- Output: 16 columns

### int_indicator_cross_correlations.sql
- 5 rolling 12-quarter correlations
- GDP vs unemployment
- Inflation vs Fed Funds
- GDP vs sentiment
- Unemployment vs sentiment
- Inflation vs sentiment
- Relationship quality assessments
- Output: 8 columns

### _int_economic_metrics.yml
Schema definitions for 7 intermediate models:
- Comprehensive column documentation
- Type validation and range tests
- Relationship quality categorical tests
- All critical columns tested

## Marts/Presentation Layer (Tables + View)

Analysis-ready fact and dimension tables.

### Fact Tables (5)

#### fct_economic_indicators_monthly.sql
- **Grain**: One row per month
- **Width**: All monthly indicators + data quality
- **Columns**: 27 (inflation, unemployment, rates, sentiment, housing + completeness)
- **Indexes**: period_date_key, year/month
- **Key metrics**: 
  - CPI, inflation rate, severity category
  - Unemployment rate, YoY change, trend
  - Fed Funds rate, direction
  - Sentiment index, outlook
  - Housing starts
  - Data completeness score (0-5)

#### fct_economic_indicators_quarterly.sql
- **Grain**: One row per quarter
- **Width**: GDP metrics + averaged monthly indicators + recession signals
- **Columns**: 25
- **Indexes**: period_date_key, year/quarter
- **Key metrics**:
  - GDP value, QoQ growth, YoY growth
  - Averaged CPI, unemployment, Fed Funds, sentiment, housing
  - Recession risk level, intensity score

#### fct_recession_analysis.sql
- **Grain**: Quarterly
- **Focus**: Recession risk and contributing factors
- **Columns**: 17
- **Key metrics**:
  - Recession risk level (4 categories)
  - Recession intensity score (0-10)
  - Contributing factors (1-4)
  - Risk assessment summary

#### fct_inflation_analysis.sql
- **Grain**: Monthly
- **Focus**: Inflation severity and Fed response
- **Columns**: 18
- **Key metrics**:
  - YoY inflation rate
  - Inflation momentum (Accelerating, Decelerating, Stable)
  - Fed policy stance (5 categories)
  - Fed policy effectiveness (4 categories)

#### fct_employment_analysis.sql
- **Grain**: Monthly
- **Focus**: Labor market health and leading indicators
- **Columns**: 17
- **Key metrics**:
  - Labor market health score (0-10)
  - Labor market condition (4 categories)
  - Housing leading indicator
  - Employment assessment

### Dimension Tables (1)

#### dim_economic_periods.sql
- **Grain**: One row per month (from 2000-01-01 forward)
- **Width**: Calendar dimensions + NBER recession dates
- **Columns**: 15
- **Key attributes**:
  - Year, quarter, month
  - Month name/short name
  - Quarter name
  - Week of year, day of month, day of week
  - NBER recession period flag
  - Recession name (if applicable)

### Views (1)

#### vw_economic_overview_dashboard.sql
- **Type**: Wide denormalized view
- **Grain**: Latest single row across all metrics
- **Columns**: 35+
- **Purpose**: Dashboard display
- **Content**: Latest month + latest quarter + latest recession analysis + period info

## Schema Documentation

### _stg_economic_indicators.yml
Complete schema for staging models:
- 6 models × ~7 columns each
- Column descriptions, types, tests
- ~150 data tests total

### _int_economic_metrics.yml
Complete schema for intermediate models:
- 7 models × variable columns
- Column descriptions, test specifications
- Relationship tests, range validation

### _marts_core.yml
Core mart models schema:
- 3 fact tables + 1 dimension
- Comprehensive column documentation
- Test specifications for all columns

### _marts_analysis.yml
Analysis mart models schema:
- 4 specialized fact tables
- Detailed column documentation
- 100+ data tests

## Macros (2)

### calculate_yoy_change.sql
- Reusable YoY percentage change calculation
- Parameters: value_col, date_col, intervals
- Returns: YoY % change using LAG()
- Used in: GDP, CPI, unemployment, sentiment

### calculate_rolling_average.sql
- Reusable rolling average calculation
- Parameters: value_col, date_col, window_size
- Returns: N-period rolling average using ROWS BETWEEN
- Used in: All rolling average transformations

## Tests (3 Custom Generic)

### test_valid_economic_range.sql
- Validates values within min/max bounds
- Used for: GDP, CPI, unemployment, rates, sentiment, housing
- Configuration: min_value, max_value parameters

### test_month_over_month_spike.sql
- Detects anomalous MoM percentage changes
- Flags records exceeding threshold
- Configuration: threshold_pct parameter

### test_outlier_detection.sql
- Z-score based statistical outlier detection
- Flags records beyond N standard deviations
- Configuration: std_dev_threshold parameter

## Data Quality Features

### Freshness Monitoring (sources.yml)
- 6 FRED sources with warn/error thresholds
- Loaded_at tracking on all raw tables

### Completeness Tracking
- fct_economic_indicators_monthly.data_completeness_score (0-5)
- fct_economic_indicators_monthly.is_data_complete flag

### Test Coverage
- ~250+ dbt tests across all layers
- Column-level validation in every model
- Custom tests for domain-specific checks
- store_failures=true for audit trail

### Type Safety
- All numeric columns cast to appropriate precision
- Date handling consistent across models
- Type validation with dbt_expectations

## Modeling Approaches

### Grain Levels
- **Staging**: Inherit source grain (quarterly for GDP, monthly for others)
- **Intermediate**: Grain-specific calculations (quarterly for GDP, monthly for indicators)
- **Marts**: Two grains - monthly (indicators, inflation, employment) and quarterly (GDP, recession)

### Key Design Patterns
- **UNION pattern**: int_economic_rolling_averages (5 streams)
- **Full Outer Join**: int_financial_conditions (different monthly sources)
- **Window functions**: YoY/rolling calculations, is_latest flag
- **Lag/Lead**: Change calculations, trend direction
- **CASE WHEN**: Categorization and scoring
- **Composite keys**: Multidimensional indexing

### Naming Conventions
- **Staging**: stg_[indicator_name]
- **Intermediate**: int_[metric_type]_[transformation]
- **Marts**: fct_[subject], dim_[dimension], vw_[view]
- Columns: descriptive with _pct, _billions, _index suffixes

## Documentation & Reference

### README.md
- Setup instructions
- Running dbt commands
- Data layer explanations
- Metric definitions
- Freshness thresholds
- Dependencies

### PROJECT_MANIFEST.md
- This file
- Complete file-by-file inventory
- Column count reference
- Design patterns documented

## Statistics

### File Counts
- Configuration files: 4
- Source definitions: 1
- Staging models: 6 SQL + 1 YAML
- Intermediate models: 7 SQL + 1 YAML
- Mart models: 7 SQL + 2 YAML
- Macros: 2
- Tests: 3
- Documentation: 2 Markdown files
- **Total**: 36 files

### Code Statistics (Approximate)
- Staging models: ~150 lines SQL
- Intermediate models: ~750 lines SQL
- Mart models: ~800 lines SQL
- Macros: ~50 lines SQL
- Tests: ~100 lines SQL
- Schema YAML: ~1500 lines
- **Total**: ~3,350 lines of code

### Data Model Statistics
- Source tables: 6
- Staging models: 6
- Intermediate models: 7
- Fact tables: 5
- Dimension tables: 1
- Views: 1
- Total tables: 20+
- Columns per model: 7-35 (average ~15)
- Total columns across all models: ~300+
- Dbt tests: 250+

## Execution Order

### Natural dependency chain (dbt handles automatically):
1. Sources (raw_*)
2. Staging models (stg_*)
3. Intermediate models (int_*)
4. Mart models (fct_*, dim_*)
5. Views (vw_*)

### Tag-based execution:
```bash
dbt run -s tag:staging      # staging layer only
dbt run -s tag:intermediate # intermediate layer only
dbt run -s tag:marts        # marts layer only
dbt run -s tag:monthly      # monthly grain only
dbt run -s tag:quarterly    # quarterly grain only
```

## Database Schema Layout

After running `dbt run`, the following schemas are created:
- **public**: Contains raw sources (input)
- **staging**: 6 staging views
- **intermediate**: 7 intermediate tables
- **analytics**: Marts layer (5 fact tables + 1 dimension + 1 view)

## Notes for Deployment

1. **Freshness monitoring** is active - data older than thresholds will trigger warnings/errors
2. **Test failures** in marts cause the entire mart to fail (severity=error)
3. **Rolling averages** require sufficient historical data (~12 months minimum)
4. **Recession dates** are hardcoded - update when NBER releases new data
5. **Correlations** need 12+ quarters of data to produce valid results
6. **Missing data** is handled gracefully with NULL values and completeness scoring
7. **Timezone**: All timestamps are UTC (current_timestamp)

---
Generated: 2024
Last Updated: As documented in dbt_project.yml
