# US Economy Pulse Pipeline

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/downloads/release/python-3110/)
[![dbt 1.5+](https://img.shields.io/badge/dbt-1.5%2B-orange)](https://www.getdbt.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Pipeline Status](https://img.shields.io/badge/Status-Active-brightgreen)](https://github.com)
[![Live Dashboard](https://img.shields.io/badge/Live%20Dashboard-Streamlit-ff4b4b?logo=streamlit)](https://us-economy-pulse-pipeline-b3qs5emwiyydwtlvav4aeg.streamlit.app/)

A production-grade data pipeline that ingests, transforms, and monitors six critical US economic indicators from the Federal Reserve Economic Data (FRED) API, delivering clean, analysis-ready data for economic research and forecasting.

**[→ View the live dashboard](https://us-economy-pulse-pipeline-b3qs5emwiyydwtlvav4aeg.streamlit.app/)**

## Architecture

```
┌──────────────────┐
│   FRED API       │
│  (6 indicators)  │
└────────┬─────────┘
         │
         ▼
┌────────────────────────┐
│  Python Ingestor       │
│ • Rate limiting        │
│ • Error handling       │
│ • Backfill + Incr.     │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│  Supabase (PostgreSQL) │
│  Raw Layer             │
│  (6 raw tables)        │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────────────┐
│      dbt Transformations       │
│  ┌──────────────────────────┐  │
│  │ Staging (Views)          │  │
│  │ • Clean, standardize     │  │
│  │ • Add metadata           │  │
│  └──────────┬───────────────┘  │
│             ▼                  │
│  ┌──────────────────────────┐  │
│  │ Intermediate (Tables)    │  │
│  │ • Transformations        │  │
│  │ • YoY changes            │  │
│  │ • Rolling averages       │  │
│  │ • Correlations           │  │
│  └──────────┬───────────────┘  │
│             ▼                  │
│  ┌──────────────────────────┐  │
│  │ Analytics Layer (Tables) │  │
│  │ • Fact tables            │  │
│  │ • Dimensions             │  │
│  │ • Dashboard views        │  │
│  └──────────────────────────┘  │
└────────┬───────────────────────┘
         │
         ▼
┌────────────────────────┐
│  Quality Monitor       │
│ • Anomaly detection    │
│ • Freshness checks     │
│ • Data completeness    │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│   Slack Alerts         │
│  (Optional)            │
└────────────────────────┘
```

## What This Project Demonstrates

This portfolio project showcases end-to-end data engineering capabilities:

- **API Integration**: Robust client for FRED API with rate limiting, retry logic, and comprehensive error handling
- **Data Modeling**: Layered dbt architecture (staging → intermediate → analytics) for maintainability and scalability
- **ETL/ELT Orchestration**: Python pipeline with backfill/incremental modes and idempotent upserts
- **Data Transformation**: Computed metrics (YoY changes, rolling averages, cross-correlations, inflation severity)
- **Data Quality**: Hybrid monitoring combining dbt tests and Python anomaly detection with z-score thresholds
- **Production Hardening**: Type safety, logging, secret scanning, dependency auditing, comprehensive error handling
- **CI/CD Automation**: GitHub Actions for daily orchestration, security scans, and code quality checks
- **Documentation**: Data dictionary, setup guide, monitoring docs, and model-level documentation

## Data Sources

| Indicator | FRED Series ID | Description | Frequency | Typical Release | Units |
|-----------|----------------|-------------|-----------|-----------------|-------|
| GDP | GDPC1 | Real Gross Domestic Product | Quarterly | End of month + 28 days | Billions USD (2012 $) |
| CPI | CPIAUCSL | Consumer Price Index (All Items) | Monthly | Mid-month + 12 days | Index (1982-84=100) |
| Unemployment | UNRATE | Civilian Unemployment Rate | Monthly | Early month + 5 days | Percent |
| Fed Funds Rate | FEDFUNDS | Effective Federal Funds Rate | Monthly | Early month + 1 day | Percent |
| Consumer Sentiment | UMCSENT | University of Michigan Sentiment | Monthly | Mid-month | Index (0-120) |
| Housing Starts | HOUST | Total Housing Starts | Monthly | Mid-month + 12 days | Thousands of units |

## Tech Stack

| Component | Tool | Purpose |
|-----------|------|---------|
| **API** | FRED (St. Louis Fed) | Source of authoritative economic data |
| **Ingestion** | Python 3.11+ + requests | HTTP client, orchestration, rate limiting |
| **Database** | Supabase (PostgreSQL) | Managed PostgreSQL with free tier |
| **Transformation** | dbt Core 1.5+ | SQL-based data modeling and testing |
| **Quality** | Python (custom) | Anomaly detection, freshness validation |
| **Alerts** | Slack Webhooks | Real-time issue notifications |
| **Orchestration** | GitHub Actions | Free, built-in CI/CD for scheduled runs |
| **Dashboard** | Streamlit Cloud | Live public dashboard, auto-deploys from GitHub |
| **Version Control** | Git / GitHub | Source of truth for code and schema |

## dbt Model Inventory

### Staging Layer (Views)
Standardize raw FRED data with consistent naming, types, and metadata.

| Model | Description | Grain | Materialization |
|-------|-------------|-------|-----------------|
| stg_gdp | Real GDP data cleaned and typed | One row per quarter | view |
| stg_cpi | Consumer Price Index standardized | One row per month | view |
| stg_unemployment_rate | Unemployment rate with metadata | One row per month | view |
| stg_federal_funds_rate | Fed Funds rate with direction flag | One row per month | view |
| stg_consumer_sentiment | Consumer sentiment index | One row per month | view |
| stg_housing_starts | Housing starts in thousands | One row per month | view |

### Intermediate Layer (Tables)
Business logic and derived metrics: YoY changes, rolling averages, correlations, regime indicators.

| Model | Description | Key Metrics |
|-------|-------------|-------------|
| int_cpi_inflation_rates | Inflation calculations | YoY%, MoM%, severity categories |
| int_labor_market_metrics | Unemployment analysis | YoY change, trend direction, health flag |
| int_gdp_with_yoy_change | GDP growth metrics | YoY% change, growth regimes |
| int_financial_conditions | Fed rates + sentiment | Rate direction, sentiment outlook |
| int_economic_rolling_averages | 3/6/12-month rolling stats | All indicators with rolling avg |
| int_recession_indicators | Recession probability signals | Multi-indicator recession flags |
| int_indicator_cross_correlations | Pairwise correlations | Inter-indicator relationships |

### Analytics Layer (Tables & Views)
Denormalized fact tables and dashboard-ready views for analysis and BI tools.

| Model | Description | Grain | Primary Use |
|-------|-------------|-------|-------------|
| fct_economic_indicators_monthly | All monthly indicators in one row | One row per month | Primary fact table |
| fct_economic_indicators_quarterly | Quarterly-aligned data | One row per quarter | Quarterly analysis |
| fct_employment_analysis | Labor market deep-dive | One row per month | Employment studies |
| fct_inflation_analysis | CPI and inflation focus | One row per month | Inflation tracking |
| fct_recession_analysis | Recession probability scores | One row per quarter | Macro forecasting |
| dim_economic_periods | Calendar + regime dimensions | One row per date | Conformed dimensions |
| vw_economic_overview_dashboard | Pre-joined view for BI | One row per month | Streamlit dashboard (live) |

## Quick Start

### Prerequisites
- Python 3.11 or later
- pip (Python package manager)
- Git
- A free Supabase account
- A free FRED API key

### 1. Get API Keys

**FRED API Key:**
- Visit https://fredaccount.stlouisfed.org/apikeys
- Sign up or log in with your email
- Create a new API key (takes seconds)

**Supabase Project:**
- Go to https://supabase.com
- Click "New Project"
- Choose a name and region (closest to you)
- Create the project
- Navigate to Settings → Database → Connection Pooling
- Copy your connection string and note your `SUPABASE_SERVICE_ROLE_KEY`

### 2. Clone Repository

```bash
git clone https://github.com/your-org/us-economy-pulse-pipeline.git
cd us-economy-pulse-pipeline
```

### 3. Set Environment Variables

```bash
cp .env.example .env
# Edit .env with your credentials
```

`.env` should contain:
```
FRED_API_KEY=your_api_key_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key_here
```

### 4. Initialize dbt

```bash
# Create dbt profiles directory
mkdir -p ~/.dbt

# Copy and customize profiles
cp dbt_project/profiles.yml.example ~/.dbt/profiles.yml

# Edit ~/.dbt/profiles.yml with your Supabase credentials

# Install dbt dependencies
cd dbt_project
dbt deps

# Test dbt connection
dbt debug
```

### 5. Run Initial Backfill

```bash
# From project root
python -m src.ingestion.run_ingestion --backfill

# This fetches all data from 2000-01-01 to today (one-time, takes ~2-3 minutes)
```

### 6. Run dbt

```bash
cd dbt_project

# Run all models (staging → intermediate → analytics)
dbt run

# Run tests
dbt test

# Generate documentation
dbt docs generate
dbt docs serve  # Opens docs at http://localhost:8000
```

### 7. Schedule with GitHub Actions (Optional)

Push your code to GitHub, then add these secrets to your repository:
- `FRED_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `SLACK_WEBHOOK_URL` (optional, for alerts)

The included workflow runs daily at 8:00 AM UTC.

## Project Structure

```
us-economy-pulse-pipeline/
├── .github/
│   └── workflows/
│       ├── daily_pipeline.yml          # Main orchestration schedule
│       └── security_scan.yml           # Secret scanning, dependency audits
├── dbt_project/
│   ├── models/
│   │   ├── staging/                    # stg_* views (raw → clean)
│   │   ├── intermediate/               # int_* tables (business logic)
│   │   └── marts/                      # fct_*, dim_*, vw_* (analytics)
│   ├── tests/
│   │   └── generic/                    # Custom tests (outlier, freshness)
│   ├── macros/                         # Reusable SQL (rolling avg, YoY calc)
│   └── dbt_project.yml                 # dbt config + thresholds
├── src/
│   ├── ingestion/
│   │   ├── fred_client.py              # FRED API client (rate limit, retry)
│   │   ├── load_to_supabase.py         # Upsert logic to Supabase
│   │   ├── run_ingestion.py            # Main orchestrator
│   │   └── config.py                   # Series config, thresholds
│   └── quality/
│       ├── anomaly_detector.py         # Z-score based detection
│       ├── freshness_checker.py        # Data currency validation
│       └── slack_notifier.py           # Alert delivery
├── docs/
│   ├── README.md                       # This file
│   ├── data_dictionary.md              # Column-level documentation
│   ├── setup_guide.md                  # Detailed onboarding
│   └── quality_monitoring.md           # QA system deep-dive
├── requirements.txt                    # Python dependencies
├── .env.example                        # Template for env config
└── .gitignore                          # Excludes .env, profiles.yml
```

## Data Quality

The pipeline includes a comprehensive hybrid quality monitoring system:

**dbt-Native Tests** (run with `dbt test`):
- Not-null checks on critical columns
- Unique constraints on keys
- Accepted-values for categorical fields
- Type validation for numeric columns
- Custom outlier detection (z-score > 3)
- Month-over-month spike detection (> 25% change)
- Valid range checks (e.g., unemployment 0-15%)

**Python Runtime Checks** (run post-dbt):
- **Freshness**: Verifies each series has data within expected age (GDP: 60 days, CPI: 20 days, etc.)
- **Anomaly Detection**: Z-score analysis flags unusual values (configurable sensitivity)
- **Completeness**: Monitors percentage of non-null values in fact tables
- **Cross-indicator Validation**: Ensures logical relationships (e.g., recession signals correlate)

**Quality Metadata**:
- `quality_checks` table logs every check with pass/fail/error status
- `quality_baselines` table stores rolling statistics for anomaly detection
- Configurable thresholds per indicator in `dbt_project.yml`

**Failure Response**:
- dbt test failures are logged in `dbt_test_failures` table
- Python checks send Slack alerts (webhook URL optional)
- GitHub Actions job succeeds but logs detailed failure summaries
- On-call engineer reviews quality report in Slack

See `docs/quality_monitoring.md` for complete QA system documentation.

## Pipeline Schedule

Configured in `.github/workflows/daily_pipeline.yml`:

| Step | Time | Action | Duration |
|------|------|--------|----------|
| **Fetch Raw Data** | 08:00 UTC | Python → FRED API (incremental mode) | ~2 min |
| **Transform** | 08:05 UTC | dbt run (all models) | ~3 min |
| **Test** | 08:10 UTC | dbt test + Python quality checks | ~2 min |
| **Alert** | 08:15 UTC | Slack notification with summary | instant |

The pipeline is idempotent: re-running it with the same data produces no duplicates, making it safe for retries.

## Viewing Results

### Live Dashboard (Streamlit Cloud)
The dashboard is publicly deployed and updates automatically whenever the pipeline runs.

**[→ https://us-economy-pulse-pipeline-b3qs5emwiyydwtlvav4aeg.streamlit.app/](https://us-economy-pulse-pipeline-b3qs5emwiyydwtlvav4aeg.streamlit.app/)**

It displays KPI cards (GDP growth, inflation, unemployment, fed funds rate, recession risk), an interactive GDP chart, a color-coded recession risk timeline, inflation vs. monetary policy overlay, and a recession intensity score chart — all pulling live from Supabase.

To deploy your own fork:
1. Push the repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect the repo
3. Set `dashboard/app.py` as the entry point
4. Add your Supabase credentials under **Secrets** in the Streamlit Cloud dashboard

### Supabase Studio (Built-in SQL Explorer)
1. Log into https://supabase.com and select your project
2. Navigate to **Database → Tables** to browse the raw and analytics layers
3. Use the **SQL Editor** to query views directly, e.g. `SELECT * FROM public_analytics.vw_economic_overview_dashboard`

### dbt Documentation (Local)
```bash
cd dbt_project
dbt docs generate
dbt docs serve  # Opens at http://localhost:8080 — local only
```
Generates interactive model lineage, column definitions, and test history. Not deployed publicly.

## Contributing

1. Create a feature branch: `git checkout -b feature/my-indicator`
2. Make changes (add series in `config.py`, create `stg_*` model, intermediate transform, mart table)
3. Write tests in YAML for data validation
4. Push and open a pull request
5. GitHub Actions runs security scans and dbt tests on PR

## License

MIT License — see LICENSE file for details.

---

**Last Updated**: March 2026

For questions or issues, open a GitHub issue or reach out to the data team.
