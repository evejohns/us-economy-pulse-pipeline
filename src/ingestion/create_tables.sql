-- US Economy Pulse Pipeline — Raw Table Setup
-- Run this once in Supabase SQL Editor before first ingestion

CREATE TABLE IF NOT EXISTS raw_gdp (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    series_id TEXT NOT NULL,
    observation_date DATE NOT NULL,
    value NUMERIC,
    units TEXT,
    frequency TEXT,
    ingested_at TIMESTAMPTZ DEFAULT now(),
    raw_json JSONB,
    UNIQUE(series_id, observation_date)
);

CREATE TABLE IF NOT EXISTS raw_cpi (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    series_id TEXT NOT NULL,
    observation_date DATE NOT NULL,
    value NUMERIC,
    units TEXT,
    frequency TEXT,
    ingested_at TIMESTAMPTZ DEFAULT now(),
    raw_json JSONB,
    UNIQUE(series_id, observation_date)
);

CREATE TABLE IF NOT EXISTS raw_unemployment (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    series_id TEXT NOT NULL,
    observation_date DATE NOT NULL,
    value NUMERIC,
    units TEXT,
    frequency TEXT,
    ingested_at TIMESTAMPTZ DEFAULT now(),
    raw_json JSONB,
    UNIQUE(series_id, observation_date)
);

CREATE TABLE IF NOT EXISTS raw_federal_funds (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    series_id TEXT NOT NULL,
    observation_date DATE NOT NULL,
    value NUMERIC,
    units TEXT,
    frequency TEXT,
    ingested_at TIMESTAMPTZ DEFAULT now(),
    raw_json JSONB,
    UNIQUE(series_id, observation_date)
);

CREATE TABLE IF NOT EXISTS raw_consumer_sentiment (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    series_id TEXT NOT NULL,
    observation_date DATE NOT NULL,
    value NUMERIC,
    units TEXT,
    frequency TEXT,
    ingested_at TIMESTAMPTZ DEFAULT now(),
    raw_json JSONB,
    UNIQUE(series_id, observation_date)
);

CREATE TABLE IF NOT EXISTS raw_housing_starts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    series_id TEXT NOT NULL,
    observation_date DATE NOT NULL,
    value NUMERIC,
    units TEXT,
    frequency TEXT,
    ingested_at TIMESTAMPTZ DEFAULT now(),
    raw_json JSONB,
    UNIQUE(series_id, observation_date)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_raw_gdp_date ON raw_gdp(observation_date);
CREATE INDEX IF NOT EXISTS idx_raw_cpi_date ON raw_cpi(observation_date);
CREATE INDEX IF NOT EXISTS idx_raw_unemployment_date ON raw_unemployment(observation_date);
CREATE INDEX IF NOT EXISTS idx_raw_federal_funds_date ON raw_federal_funds(observation_date);
CREATE INDEX IF NOT EXISTS idx_raw_consumer_sentiment_date ON raw_consumer_sentiment(observation_date);
CREATE INDEX IF NOT EXISTS idx_raw_housing_starts_date ON raw_housing_starts(observation_date);
