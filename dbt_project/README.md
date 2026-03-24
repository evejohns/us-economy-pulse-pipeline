# US Economy Pulse - dbt Project

Complete data transformation pipeline for US economic indicators using dbt and Supabase PostgreSQL.

## Project Structure

```
dbt_project/
├── dbt_project.yml           # Main dbt configuration
├── profiles.yml.example      # Supabase connection template
├── packages.yml              # dbt package dependencies
├── README.md                 # This file
├── models/
│   ├── sources.yml           # FRED source definitions (6 tables)
│   ├── staging/              # Staging layer (views)
│   │   ├── stg_gdp.sql
│   │   ├── stg_cpi.sql
│   │   ├── stg_unemployment_rate.sql
│   │   ├── stg_federal_funds_rate.sql
│   │   ├── stg_consumer_sentiment.sql
│   │   ├── stg_housing_starts.sql
│   │   └── _stg_economic_indicators.yml
│   ├── intermediate/         # Intermediate layer (tables)
│   │   ├── int_gdp_with_yoy_change.sql
│   │   ├── int_cpi_inflation_rates.sql
│   │   ├── int_labor_market_metrics.sql
│   │   ├── int_financial_conditions.sql
│   │   ├── int_economic_rolling_averages.sql
│   │   ├── int_recession_indicators.sql
│   │   ├── int_indicator_cross_correlations.sql
│   │   └── _int_economic_metrics.yml
│   └── marts/                # Marts/presentation layer (tables + view)
│       ├── fct_economic_indicators_monthly.sql
│       ├── fct_economic_indicators_quarterly.sql
│       ├── fct_recession_analysis.sql
│       ├── fct_inflation_analysis.sql
│       ├── fct_employment_analysis.sql
│       ├── dim_economic_periods.sql
│       ├── vw_economic_overview_dashboard.sql
│       ├── _marts_core.yml
│       └── _marts_analysis.yml
├── macros/                   # Reusable SQL functions
│   ├── calculate_yoy_change.sql
│   └── calculate_rolling_average.sql
├── tests/                    # dbt tests
│   └── generic/
│       ├── test_valid_economic_range.sql
│       ├── test_month_over_month_spike.sql
│       └── test_outlier_detection.sql
└── seeds/                    # Static reference data (optional)
```

## Setup Instructions

### 1. Install dbt-core and Postgres adapter
```bash
pip install dbt-core dbt-postgres
```

### 2. Configure Supabase connection
```bash
cp profiles.yml.example ~/.dbt/profiles.yml
```

Edit `~/.dbt/profiles.yml` with your Supabase credentials:
```yaml
us_economy_pulse:
  target: dev
  outputs:
    dev:
      type: postgres
      host: your-project.supabase.co
      port: 5432  # or 6543 for pooler
      user: postgres
      password: your_password
      dbname: postgres
      schema: public
      threads: 4
      keepalives_idle: 0
      application_name: dbt_us_economy_pulse
      sslmode: require
```

### 3. Install dbt packages
```bash
cd dbt_project
dbt deps
```

### 4. Verify connection
```bash
dbt debug
```

## Running dbt

### Execute all models
```bash
dbt run
```

### Execute specific models
```bash
dbt run -s stg_*              # staging layer
dbt run -s int_*              # intermediate layer
dbt run -s fct_* dim_* vw_*   # marts layer
```

### Run tests
```bash
dbt test
```

### Test specific models
```bash
dbt test -s stg_gdp
dbt test -s fct_economic_indicators_monthly
```

### Generate documentation
```bash
dbt docs generate
dbt docs serve
```

## Data Layers

### Staging (Views)
Raw FRED data cleaned and standardized with consistent column naming:
- `stg_gdp` - Real GDP (quarterly)
- `stg_cpi` - Consumer Price Index (monthly)
- `stg_unemployment_rate` - Unemployment Rate (monthly)
- `stg_federal_funds_rate` - Federal Funds Rate (monthly)
- `stg_consumer_sentiment` - Consumer Sentiment (monthly)
- `stg_housing_starts` - Housing Starts (monthly)

### Intermediate (Tables)
Business logic and transformations:
- `int_gdp_with_yoy_change` - GDP with QoQ/YoY growth
- `int_cpi_inflation_rates` - Inflation metrics with severity categories
- `int_labor_market_metrics` - Unemployment trends and health flags
- `int_financial_conditions` - Fed rates and sentiment with stress indicators
- `int_economic_rolling_averages` - 3M/6M/12M rolling averages
- `int_recession_indicators` - Recession risk scoring (0-10 scale)
- `int_indicator_cross_correlations` - 12-quarter rolling correlations

### Marts/Presentation (Tables + View)
Analysis-ready fact tables and dimensions:

**Fact Tables:**
- `fct_economic_indicators_monthly` - All monthly metrics + data quality (grain: month)
- `fct_economic_indicators_quarterly` - GDP + averaged metrics (grain: quarter)
- `fct_recession_analysis` - Recession risk and contributing factors (grain: quarter)
- `fct_inflation_analysis` - Inflation severity and Fed response (grain: month)
- `fct_employment_analysis` - Labor market health scores (grain: month)

**Dimension Tables:**
- `dim_economic_periods` - Calendar dimensions + NBER recession dates (grain: month)

**Views:**
- `vw_economic_overview_dashboard` - Wide denormalized latest metrics for dashboard

## Key Metrics

### Recession Risk Level
Assessment of recession probability:
- **Low** - Economy functioning normally
- **Emerging** - Early warning signs (YoY growth <2.5%, pessimistic sentiment)
- **Moderate** - Elevated risk (negative growth + unemployment rising)
- **High** - Imminent risk (2+ consecutive negative quarters)

### Recession Intensity Score
Composite 0-10 scale based on:
- Negative GDP growth (0-5 points)
- GDP growth rate < 2% (0-2 points)
- High unemployment (0-2 points)
- Job losses (0-2 points)
- High inflation (0-1 point)
- Weak sentiment (0-1 point)

### Inflation Severity
- **Mild** - ≤ 2.5%
- **Moderate** - 2.5% to 4.0%
- **High** - 4.0% to 5.0%
- **Severe** - > 5.0%

### Labor Market Health
Score 0-10 based on:
- Unemployment below 4.0% (3 points)
- Unemployment 4.0-5.0% (2 points)
- Declining/flat trend (1-2 points)
- YoY job gains (1-2 points)
- Strong housing starts (1-2 points)

## Data Quality & Testing

### dbt Tests
All models include column-level tests:
- **not_null** - Required fields are populated
- **unique** - Primary keys are unique
- **accepted_values** - Categorical fields have valid values
- **dbt_expectations** - Type validation, range checks
- **custom tests** - Economic range validation, spike detection, outlier detection

### Data Completeness
Monthly fact table tracks completeness score (0-5):
- 5 = all indicators present
- 4+ = considered complete
- <4 = flagged for review

## Freshness Thresholds
Data source freshness monitoring:
- GDP: warn 35d, error 60d
- CPI: warn 10d, error 20d
- Unemployment: warn 8d, error 15d
- Fed Funds: warn 5d, error 15d
- Sentiment: warn 10d, error 20d
- Housing: warn 12d, error 25d

## Macros

### calculate_yoy_change(value_col, date_col, intervals)
Calculate year-over-year percentage change:
```sql
{{ calculate_yoy_change('gdp_billions_usd', 'period_date_key', 4) }}
```

### calculate_rolling_average(value_col, date_col, window_size)
Calculate N-period rolling average:
```sql
{{ calculate_rolling_average('unemployment_rate_pct', 'period_date_key', 3) }}
```

## Dependencies

### dbt Packages
- `dbt-utils` - SQL utilities and tests
- `dbt-expectations` - Advanced column validation

### Database
- Supabase PostgreSQL (14+)
- Standard port: 5432
- Connection pooler port: 6543 (optional)

## Notes

- All timestamps use UTC (current_timestamp)
- Dates are cast to DATE type for consistency
- Quarterly analysis aligns to calendar quarters
- NBER recession dates hardcoded (update as needed)
- Missing data handled with NULL values and completeness scoring
- All models include comprehensive documentation

## Contact & Support

For issues or questions about this dbt project, please refer to the US Economy Pulse Pipeline documentation.
