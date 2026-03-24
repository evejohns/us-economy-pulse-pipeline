"""
Supabase loader for storing US economic data.

Handles table creation, upserts, and data validation.
"""

import json
import logging
from datetime import date, datetime
from typing import List, Dict, Any, Optional

from supabase import create_client, Client

logger = logging.getLogger(__name__)


class SupabaseLoaderError(Exception):
    """Custom exception for Supabase loader errors."""

    pass


class SupabaseLoader:
    """
    Loader for upserting economic data into Supabase PostgreSQL tables.

    Handles schema creation, data validation, and upsert operations.
    """

    def __init__(self, supabase_url: str, supabase_key: str):
        """
        Initialize the Supabase loader.

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase service role key

        Raises:
            ValueError: If URL or key is not provided
            SupabaseLoaderError: If unable to connect to Supabase
        """
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY are required")

        try:
            self.client: Client = create_client(supabase_url, supabase_key)
            logger.info("Successfully initialized Supabase client")
        except Exception as e:
            raise SupabaseLoaderError(f"Failed to initialize Supabase client: {str(e)}") from e

    def create_raw_tables(self, tables: List[str]) -> None:
        """
        Create raw data tables if they don't already exist.

        Each table has the following columns:
        - id: UUID primary key, auto-generated
        - series_id: Text identifier for the economic series
        - observation_date: Date of the observation
        - value: Numeric value of the observation
        - units: Text description of units
        - frequency: Text frequency of observations (monthly, quarterly)
        - ingested_at: Timestamp when record was inserted
        - raw_json: JSONB for storing original API response

        Args:
            tables: List of table names to create

        Raises:
            SupabaseLoaderError: If table creation fails
        """
        for table_name in tables:
            try:
                logger.info(f"Creating table {table_name} if it doesn't exist...")

                # SQL to create table with proper constraints
                sql = f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
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

                -- Create indexes for common queries
                CREATE INDEX IF NOT EXISTS idx_{table_name}_series_id
                    ON {table_name}(series_id);
                CREATE INDEX IF NOT EXISTS idx_{table_name}_observation_date
                    ON {table_name}(observation_date);
                CREATE INDEX IF NOT EXISTS idx_{table_name}_series_date
                    ON {table_name}(series_id, observation_date DESC);
                """

                # Tables are created via create_tables.sql in Supabase SQL Editor
                logger.info(f"Table {table_name} assumed to exist (created via SQL Editor)")

            except Exception as e:
                logger.error(f"Failed to create table {table_name}: {str(e)}")
                raise SupabaseLoaderError(f"Failed to create table {table_name}: {str(e)}") from e

    def upsert_observations(
        self,
        table_name: str,
        series_id: str,
        observations: List[Dict[str, Any]],
        units: str = "",
        frequency: str = "",
    ) -> Dict[str, int]:
        """
        Upsert observations into a table.

        Uses ON CONFLICT to update existing records with same series_id and observation_date.

        Args:
            table_name: Name of the target table
            series_id: FRED series identifier
            observations: List of observation dicts with 'date' and 'value' keys
            units: Unit description for the series
            frequency: Frequency of observations (monthly, quarterly)

        Returns:
            Dictionary with 'upserted' and 'failed' counts

        Raises:
            SupabaseLoaderError: If upsert operation fails
        """
        if not observations:
            logger.warning(f"No observations to upsert for {series_id}")
            return {"upserted": 0, "failed": 0}

        try:
            upserted_count = 0
            failed_count = 0

            for obs in observations:
                try:
                    # Extract and validate data
                    obs_date = obs.get("date")
                    obs_value = obs.get("value")

                    # Convert date if needed
                    if isinstance(obs_date, datetime):
                        obs_date = obs_date.date()
                    elif isinstance(obs_date, str):
                        obs_date = datetime.strptime(obs_date, "%Y-%m-%d").date()

                    # Prepare record
                    record = {
                        "series_id": series_id,
                        "observation_date": obs_date.isoformat(),
                        "value": obs_value,
                        "units": units,
                        "frequency": frequency,
                        "raw_json": json.dumps(obs),
                    }

                    # Upsert using ON CONFLICT
                    response = (
                        self.client.table(table_name)
                        .upsert(record, on_conflict="series_id,observation_date")
                        .execute()
                    )

                    if response.data:
                        upserted_count += 1
                    else:
                        logger.warning(f"Upsert returned no data for {series_id} on {obs_date}")
                        failed_count += 1

                except Exception as e:
                    logger.error(f"Failed to upsert observation {obs} to {table_name}: {str(e)}")
                    failed_count += 1
                    continue

            logger.info(
                f"Upserted {upserted_count} observations to {table_name} "
                f"(failed: {failed_count})"
            )
            return {"upserted": upserted_count, "failed": failed_count}

        except Exception as e:
            logger.error(f"Batch upsert operation failed: {str(e)}")
            raise SupabaseLoaderError(f"Failed to upsert observations: {str(e)}") from e

    def get_latest_date(self, table_name: str, series_id: str) -> Optional[date]:
        """
        Get the most recent observation date for a series.

        Used for incremental loading to avoid re-fetching old data.

        Args:
            table_name: Name of the table to query
            series_id: FRED series identifier

        Returns:
            Latest observation_date as a date object, or None if table is empty

        Raises:
            SupabaseLoaderError: If query fails
        """
        try:
            response = (
                self.client.table(table_name)
                .select("observation_date")
                .eq("series_id", series_id)
                .order("observation_date", desc=True)
                .limit(1)
                .execute()
            )

            if response.data and len(response.data) > 0:
                latest_date_str = response.data[0]["observation_date"]
                latest_date = datetime.strptime(latest_date_str, "%Y-%m-%d").date()
                logger.info(f"Latest date for {series_id} in {table_name}: {latest_date}")
                return latest_date
            else:
                logger.info(f"No data found for {series_id} in {table_name}")
                return None

        except Exception as e:
            logger.error(f"Failed to get latest date for {series_id}: {str(e)}")
            raise SupabaseLoaderError(f"Failed to query latest date: {str(e)}") from e

    def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """
        Get basic statistics about a table.

        Args:
            table_name: Name of the table to query

        Returns:
            Dictionary with row count and date range

        Raises:
            SupabaseLoaderError: If query fails
        """
        try:
            # Get total count
            count_response = self.client.table(table_name).select("id").execute()
            total_rows = len(count_response.data) if count_response.data else 0

            # Get date range
            date_response = (
                self.client.table(table_name)
                .select("observation_date")
                .order("observation_date", desc=True)
                .limit(1)
                .execute()
            )

            latest_date = None
            if date_response.data:
                latest_date = date_response.data[0]["observation_date"]

            stats = {
                "table": table_name,
                "total_rows": total_rows,
                "latest_date": latest_date,
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get stats for {table_name}: {str(e)}")
            raise SupabaseLoaderError(f"Failed to get table stats: {str(e)}") from e
