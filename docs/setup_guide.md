# Setup Guide

Complete step-by-step instructions for setting up the US Economy Pulse Pipeline on your machine.

## Prerequisites

Before you start, ensure you have:

- **Python 3.11 or later** ([download](https://www.python.org/downloads/))
  - Verify: `python --version`
- **pip** (usually comes with Python 3.11+)
  - Verify: `pip --version`
- **Git** ([download](https://git-scm.com/))
  - Verify: `git --version`
- **Text editor or IDE** (VS Code, PyCharm, etc.)

Estimated total setup time: **15-20 minutes** (includes API key registration)

---

## Step 1: Register for FRED API Key

The FRED (Federal Reserve Economic Data) API is the authoritative source for US economic indicators.

1. Go to https://fredaccount.stlouisfed.org/apikeys
2. Click **"Create New API Key"**
3. Enter your email and click **"Request Key"**
4. Check your email for a verification link
5. Click the link and confirm your email
6. You'll receive your **API key** (40-character string like `abcd1234efgh5678...`)
7. **Keep this safe** — you'll need it in Step 4

**Note**: The FRED API is free and allows up to 120 requests per minute. This pipeline uses ~1-2 requests per day in incremental mode, well within the limit.

---

## Step 2: Create a Supabase Project

Supabase is a managed PostgreSQL service with a free tier. We use it to store raw and transformed economic data.

1. Go to https://supabase.com
2. Click **"Start your project"** (or log in if you have an account)
3. Sign up with email or GitHub
4. Click **"New Project"**
5. Choose:
   - **Name**: `us-economy-pulse` (or your preferred name)
   - **Database Password**: Create a strong password (you won't need it, but keep it safe)
   - **Region**: Select the closest region to you (lower latency)
6. Click **"Create new project"** (takes 1-2 minutes)

Once your project is created, you'll need two pieces of information:

### Get Connection String & URL

1. In the Supabase dashboard, go to **Settings** → **Database** → **Connection Pooling**
2. Select **Connection String** (not the regular connection info)
3. Copy the connection string for **Session mode** (looks like `postgresql://postgres:...@db....supabase.co:...`)
4. Also note the **Project URL** from Settings → General (looks like `https://your-project.supabase.co`)

### Get Service Role Key

1. Go to **Settings** → **API**
2. Find **Service Role Key** (labeled with a warning icon)
3. Copy this key (long string, starts with `eyJ...`)
   - This has full database access; treat it like a password
   - **Do not commit this to git**

**Keep both safe** — you'll add them to `.env` in Step 4.

---

## Step 3: Clone the Repository

```bash
git clone https://github.com/your-org/us-economy-pulse-pipeline.git
cd us-economy-pulse-pipeline
```

If you don't have access yet, ask your team for the repository link.

---

## Step 4: Configure Environment Variables

Create a `.env` file with your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your favorite editor and add:

```
# FRED API Configuration
FRED_API_KEY=your_fred_api_key_here

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key_here
```

Replace the placeholders with your actual credentials from Steps 1 and 2.

**Security**:
- Never commit `.env` to git (it's in `.gitignore`)
- Never share your API key or service key
- If you accidentally commit them, regenerate them in their respective dashboards

---

## Step 5: Set Up Python Environment

Create and activate a virtual environment to isolate dependencies:

### macOS / Linux

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate
```

### Windows

```bash
# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate
```

Install Python dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs:
- `requests` — HTTP client for FRED API
- `supabase` — Supabase Python SDK
- `python-dotenv` — Load `.env` variables
- `tenacity` — Retry logic for resilience

Verify installation:

```bash
python -c "import requests, supabase, dotenv; print('All packages installed!')"
```

---

## Step 6: Set Up dbt

dbt (data build tool) orchestrates SQL transformations. We use dbt Core (free, open-source).

### Install dbt

```bash
pip install dbt-postgres==1.5.0
```

Verify:

```bash
dbt --version
# Output should show dbt-postgres 1.5.x
```

### Configure dbt Profiles

dbt needs credentials to connect to Supabase. Create a profiles configuration file:

```bash
# Create .dbt directory if it doesn't exist
mkdir -p ~/.dbt

# Copy the example profile
cp dbt_project/profiles.yml.example ~/.dbt/profiles.yml
```

Edit `~/.dbt/profiles.yml` and update the Supabase section:

```yaml
us_economy_pulse:
  outputs:
    dev:
      type: postgres
      host: your-project.supabase.co
      user: postgres
      password: your_supabase_password
      port: 5432
      dbname: postgres
      schema: staging
      threads: 4
      keepalives_idle: 0

  target: dev
```

Replace:
- `host`: From your Supabase Settings → General → Project URL (extract `your-project.supabase.co`)
- `password`: The database password you created in Step 2
- `schema`: Can stay as `staging` (dbt will create schemas as needed)

### Test dbt Connection

```bash
cd dbt_project

# Test connection to Supabase
dbt debug

# Expected output:
#   Connection test: [ok]
```

If you see errors, double-check your hostname and password.

### Install dbt Dependencies

```bash
# Still in dbt_project/
dbt deps

# This installs dbt packages (dbt_utils, dbt_expectations)
# Check output for successful installation
```

---

## Step 7: Run Initial Data Backfill

The ingestion pipeline loads economic data from FRED. The first time, we backfill from January 2000 to today (this is a one-time operation).

From the project root:

```bash
python -m src.ingestion.run_ingestion --backfill
```

What happens:
1. Python connects to FRED API
2. Fetches 6 economic series (GDP, CPI, unemployment, Fed funds, sentiment, housing starts)
3. For each series, fetches all observations from 2000-01-01 to today
4. Creates raw tables in Supabase (if they don't exist)
5. Upserts data (row insertion/update for idempotency)

Expected output:
```
================================================================================
Starting US Economy Pulse Ingestion Pipeline
Mode: backfill
================================================================================

Processing GDP...
Fetching GDPC1 from 2000-01-01 to 2024-03-20...
Upserting 96 observations to raw_gdp...
GDP: Fetched 96, Upserted 96, Failed 0

Processing CPI...
[... similar output for other 5 series ...]

================================================================================
Ingestion Pipeline Summary
================================================================================
Mode: backfill
Total Fetched: 2,847 records
Total Upserted: 2,847 records
Total Failed: 0 records
Started: 2024-03-20T13:00:00...
Completed: 2024-03-20T13:03:45...
================================================================================
```

This typically takes 2-3 minutes. Raw data is now in Supabase in tables like `fred_raw.raw_gdp`, `fred_raw.raw_cpi`, etc.

---

## Step 8: Run dbt Models

dbt transforms raw data into clean, analysis-ready tables.

```bash
cd dbt_project

# Run all models (staging → intermediate → marts)
dbt run

# Output shows model execution, expected ~10-15 models
```

Then test data quality:

```bash
dbt test

# Runs all dbt tests; should see all tests PASS
```

If all tests pass, your data is clean and ready for analysis.

### Optional: Generate Documentation

```bash
dbt docs generate

# Starts a local web server
dbt docs serve

# Opens http://localhost:8000 with model lineage, definitions, and tests
```

Press Ctrl+C to stop the server.

---

## Step 9: Verify Data in Supabase

Log in to Supabase and browse your data:

1. Go to https://supabase.com → Select your project
2. Navigate to **SQL Editor** (left sidebar)
3. Run a quick query:

```sql
SELECT period_date_key, cpi_index, unemployment_rate_pct, fedfunds_rate_pct
FROM analytics.fct_economic_indicators_monthly
ORDER BY period_date_key DESC
LIMIT 10;
```

You should see the latest 10 months of economic data. If this works, your pipeline is working end-to-end!

---

## Step 10: Set Up GitHub Actions (Optional but Recommended)

GitHub Actions automatically runs your pipeline on a schedule. This keeps your data fresh daily.

### Prerequisites
- Your code pushed to GitHub
- A GitHub repository with appropriate permissions

### Add Repository Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add these four secrets:

| Secret Name | Value |
|-------------|-------|
| `FRED_API_KEY` | Your FRED API key from Step 1 |
| `SUPABASE_URL` | Your Supabase URL (https://your-project.supabase.co) |
| `SUPABASE_SERVICE_KEY` | Your Supabase service role key from Step 2 |
| `SLACK_WEBHOOK_URL` | (Optional) For Slack alerts; see next section |

### How It Works

The included workflow (`.github/workflows/daily_pipeline.yml`) runs daily at **8:00 AM UTC**:

1. 08:00 — Fetches new data from FRED (incremental mode, last 90 days)
2. 08:05 — Runs dbt to transform data
3. 08:10 — Runs dbt tests for quality assurance
4. 08:15 — Sends Slack notification (if configured)

The pipeline is idempotent: if you run it multiple times with the same data, it creates no duplicates. Safe for retries!

---

## Step 11: Set Up Slack Alerts (Optional)

Get notified in Slack when data quality issues are detected.

### Create Slack Incoming Webhook

1. Go to https://api.slack.com/apps
2. Click **Create New App** → **From scratch**
3. Name: `US Economy Pulse Alerts`
4. Choose your workspace
5. Click **Create App**
6. In the left menu, go to **Incoming Webhooks**
7. Toggle **Activate Incoming Webhooks** to ON
8. Click **Add New Webhook to Workspace**
9. Select the Slack channel (create one like #data-alerts if needed)
10. Authorize the app
11. Copy the **Webhook URL** (looks like `https://hooks.slack.com/services/T.../B.../X...`)
12. Add this as `SLACK_WEBHOOK_URL` secret in GitHub Actions (Step 10)

When the pipeline detects issues, it sends a message to that channel with:
- Which check failed
- Which indicator was affected
- Timestamp and severity
- Link to view the full report

---

## Step 12: Running Incrementally

After backfill, the pipeline runs in **incremental mode** (fetches last 90 days):

```bash
python -m src.ingestion.run_ingestion --incremental
```

Or just:

```bash
python -m src.ingestion.run_ingestion
```

(incremental is the default)

This is much faster (typically < 1 minute) and is what GitHub Actions runs daily.

---

## Step 13: (Optional) Set Up Metabase for Dashboards

Metabase is a free, open-source BI tool. You can build visual dashboards of your economic data.

### Install and Run Metabase

```bash
# Using Docker (requires Docker installation)
docker run -d -p 3000:3000 metabase/metabase

# Or download from https://www.metabase.com/start/
```

### Connect to Supabase

1. Open http://localhost:3000
2. Follow the setup wizard
3. At the database setup, choose **PostgreSQL**
4. Enter your Supabase connection details:
   - **Host**: your-project.supabase.co
   - **Port**: 5432
   - **Database**: postgres
   - **User**: postgres
   - **Password**: Your Supabase password
5. Click **Test** then **Save**

### Build a Dashboard

1. Click **+ New** → **Question**
2. Select your Supabase database
3. Choose table `analytics.vw_economic_overview_dashboard`
4. Visualize as a table or chart
5. Click **Save** and add to a new dashboard

Example cards:
- CPI Index trend (line chart)
- Unemployment Rate over time (area chart)
- Fed Funds Rate vs Inflation (dual-axis chart)
- Labor Market Health Heatmap

---

## Troubleshooting

### "FRED_API_KEY not found"
- Check `.env` file exists and has correct key
- Run `source venv/bin/activate` (or Windows equivalent) to ensure env vars load

### "Connection to Supabase failed"
- Verify `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in `.env`
- Check your internet connection
- Ensure the Supabase project is active (not paused)

### "dbt debug fails"
- Verify `~/.dbt/profiles.yml` has correct Supabase hostname and password
- Try `dbt debug --target dev` explicitly
- Check network connectivity (Supabase may be region-blocked)

### "No data returned from FRED"
- Verify `FRED_API_KEY` is valid at https://fredaccount.stlouisfed.org/apikeys
- Check if FRED API is up (https://fred.stlouisfed.org/)
- Review ingestion logs for rate-limit errors

### Python package conflicts
```bash
# Reinstall fresh
rm -rf venv/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### dbt test failures
- Review error message; usually indicates data quality issue
- Check `quality_checks` table in Supabase for details
- Verify raw data loaded correctly with: `SELECT COUNT(*) FROM fred_raw.raw_gdp;`

---

## Next Steps

1. **Explore the data**: Browse `fct_economic_indicators_monthly` in Supabase Studio
2. **Review dbt docs**: Run `dbt docs serve` to see model lineage and descriptions
3. **Set up dashboards**: Connect Metabase or your preferred BI tool
4. **Configure alerts**: Add Slack webhook for production monitoring
5. **Customize thresholds**: Edit `dbt_project/dbt_project.yml` for data quality parameters

---

## Support

- **dbt Docs**: https://docs.getdbt.com/
- **FRED API**: https://fred.stlouisfed.org/docs/api/
- **Supabase Docs**: https://supabase.com/docs
- **Issues**: Open a GitHub issue or contact your data team

For detailed information on monitoring and quality checks, see `docs/quality_monitoring.md`.
