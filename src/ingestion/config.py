"""
Configuration for US Economy Pulse data ingestion.

Defines FRED API settings, economic series mappings, and Supabase configuration.
"""

import os
from datetime import datetime
from typing import Dict, Any

# FRED API Configuration
FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_API_KEY = os.getenv("FRED_API_KEY")

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Backfill start date
BACKFILL_START_DATE = "2000-01-01"

# Economic series mapping: indicator name to FRED series details
SERIES_CONFIG: Dict[str, Dict[str, Any]] = {
    "GDP": {
        "series_id": "GDPC1",
        "frequency": "quarterly",
        "description": "Real Gross Domestic Product, Quarterly",
        "expected_range": {"min": 5000.0, "max": 30000.0},
        "table_name": "raw_gdp",
        "units": "Billions of Chained 2012 Dollars",
    },
    "CPI": {
        "series_id": "CPIAUCSL",
        "frequency": "monthly",
        "description": "Consumer Price Index for All Urban Consumers: All Items",
        "expected_range": {"min": 30.0, "max": 400.0},
        "table_name": "raw_cpi",
        "units": "Index 1982-1984 = 100",
    },
    "Unemployment Rate": {
        "series_id": "UNRATE",
        "frequency": "monthly",
        "description": "Unemployment Rate",
        "expected_range": {"min": 0.0, "max": 15.0},
        "table_name": "raw_unemployment",
        "units": "Percent",
    },
    "Federal Funds Rate": {
        "series_id": "FEDFUNDS",
        "frequency": "monthly",
        "description": "Effective Federal Funds Rate",
        "expected_range": {"min": 0.0, "max": 20.0},
        "table_name": "raw_federal_funds",
        "units": "Percent",
    },
    "Consumer Sentiment": {
        "series_id": "UMCSENT",
        "frequency": "monthly",
        "description": "University of Michigan Inflation Expectation",
        "expected_range": {"min": 50.0, "max": 120.0},
        "table_name": "raw_consumer_sentiment",
        "units": "Index",
    },
    "Housing Starts": {
        "series_id": "HOUST",
        "frequency": "monthly",
        "description": "Total Housing Starts",
        "expected_range": {"min": 400.0, "max": 2500.0},
        "table_name": "raw_housing_starts",
        "units": "Thousands of Units",
    },
}

# Rate limiting: FRED allows 120 requests/minute
FRED_RATE_LIMIT_PER_MINUTE = 120
FRED_RATE_LIMIT_DELAY = 60 / FRED_RATE_LIMIT_PER_MINUTE  # seconds per request

# Retry configuration
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_FACTOR = 2

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = "INFO"
