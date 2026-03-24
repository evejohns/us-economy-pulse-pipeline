-- quality_checks: every check result logged here
CREATE TABLE IF NOT EXISTS quality_checks (
    check_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    check_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    pipeline_run_id TEXT NOT NULL,
    check_type TEXT NOT NULL,       -- 'freshness','schema','range','anomaly','api_health','row_count','spike'
    resource_name TEXT NOT NULL,    -- 'GDP','CPIAUCSL','UNRATE','FEDFUNDS','UMCSENT','HOUST','FRED_API'
    check_status TEXT NOT NULL,     -- 'passed','failed','warning'
    severity TEXT NOT NULL,         -- 'info','warning','critical'
    metric_value NUMERIC,
    threshold_value NUMERIC,
    description TEXT,
    details_json JSONB,
    dbt_run_id TEXT
);

-- quality_baselines: historical stats for anomaly detection
CREATE TABLE IF NOT EXISTS quality_baselines (
    baseline_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    series_id TEXT NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    lookback_days INT NOT NULL,
    row_count INT,
    mean_value NUMERIC,
    std_dev NUMERIC,
    min_value NUMERIC,
    max_value NUMERIC,
    p25 NUMERIC,
    p75 NUMERIC,
    null_pct NUMERIC
);

CREATE INDEX IF NOT EXISTS idx_quality_checks_timestamp ON quality_checks(check_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_quality_checks_status ON quality_checks(check_status, severity);
CREATE INDEX IF NOT EXISTS idx_quality_checks_resource ON quality_checks(resource_name, check_type);
CREATE INDEX IF NOT EXISTS idx_quality_baselines_series ON quality_baselines(series_id, computed_at DESC);
