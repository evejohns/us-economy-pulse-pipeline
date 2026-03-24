"""
Standalone backfill script using requests for both FRED API and Supabase REST API.
Bypasses supabase-py to avoid httpx/socks5h incompatibility in sandbox environments.
"""

import json
import os
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
import requests

# Load env
load_dotenv(".env")

FRED_API_KEY    = os.getenv("FRED_API_KEY")
SUPABASE_URL    = os.getenv("SUPABASE_URL")
SUPABASE_KEY    = os.getenv("SUPABASE_SERVICE_KEY")
START_DATE      = "2000-01-01"
END_DATE        = datetime.now().strftime("%Y-%m-%d")

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

SERIES = [
    {"series_id": "GDPC1",    "table": "raw_gdp",                "units": "Billions of Chained 2012 Dollars", "frequency": "quarterly"},
    {"series_id": "CPIAUCSL", "table": "raw_cpi",                "units": "Index 1982-1984=100",              "frequency": "monthly"},
    {"series_id": "UNRATE",   "table": "raw_unemployment",       "units": "Percent",                          "frequency": "monthly"},
    {"series_id": "FEDFUNDS", "table": "raw_federal_funds",      "units": "Percent",                          "frequency": "monthly"},
    {"series_id": "UMCSENT",  "table": "raw_consumer_sentiment", "units": "Index",                            "frequency": "monthly"},
    {"series_id": "HOUST",    "table": "raw_housing_starts",     "units": "Thousands of Units",               "frequency": "monthly"},
]

SUPABASE_HEADERS = {
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
    "Prefer":        "resolution=merge-duplicates",
}


def fetch_fred(series_id):
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id":         series_id,
        "api_key":           FRED_API_KEY,
        "observation_start": START_DATE,
        "observation_end":   END_DATE,
        "file_type":         "json",
    }
    log.info(f"Fetching {series_id} from FRED ...")
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    observations = [o for o in data.get("observations", []) if o.get("value") != "."]
    log.info(f"  Got {len(observations)} observations")
    return observations


def upsert_supabase(table, series_id, observations, units, frequency):
    endpoint = f"{SUPABASE_URL}/rest/v1/{table}"
    records = []
    for o in observations:
        try:
            records.append({
                "series_id":        series_id,
                "observation_date": o["date"],
                "value":            float(o["value"]),
                "units":            units,
                "frequency":        frequency,
                "raw_json":         json.dumps(o),
            })
        except (ValueError, KeyError):
            continue

    # Batch in chunks of 500
    batch_size = 500
    total_upserted = 0
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        resp = requests.post(endpoint, headers=SUPABASE_HEADERS, json=batch, timeout=30)
        if resp.status_code in (200, 201):
            total_upserted += len(batch)
            log.info(f"  Upserted batch {i//batch_size + 1}: {len(batch)} rows")
        else:
            log.error(f"  Batch failed: {resp.status_code} — {resp.text[:200]}")
        time.sleep(0.2)

    return total_upserted


def main():
    log.info("=" * 60)
    log.info("US Economy Pulse — Backfill")
    log.info(f"Date range: {START_DATE} → {END_DATE}")
    log.info("=" * 60)

    total = 0
    for s in SERIES:
        log.info(f"\n── {s['series_id']} → {s['table']}")
        try:
            obs = fetch_fred(s["series_id"])
            n   = upsert_supabase(s["table"], s["series_id"], obs, s["units"], s["frequency"])
            total += n
            log.info(f"  ✓ {n} rows loaded")
        except Exception as e:
            log.error(f"  ✗ Failed: {e}")
        time.sleep(0.5)

    log.info("\n" + "=" * 60)
    log.info(f"Done. Total rows upserted: {total:,}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
