"""
Main ingestion orchestrator for US Economy Pulse Pipeline.

Coordinates FRED API fetching and Supabase loading with support for
backfill and incremental load modes.
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv

from .config import (
    FRED_API_KEY,
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY,
    BACKFILL_START_DATE,
    SERIES_CONFIG,
    LOG_FORMAT,
    LOG_LEVEL,
)
from .fred_client import FREDClient, FREDAPIError
from .load_to_supabase import SupabaseLoader, SupabaseLoaderError

# Configure logging
logging.basicConfig(
    format=LOG_FORMAT,
    level=getattr(logging, LOG_LEVEL),
)
logger = logging.getLogger(__name__)


class IngestionPipeline:
    """
    Main orchestrator for fetching and loading US economic data.

    Handles backfill and incremental load modes with comprehensive error handling.
    """

    def __init__(self, mode: str = "incremental"):
        """
        Initialize the ingestion pipeline.

        Args:
            mode: "backfill" for full history, "incremental" for recent data

        Raises:
            ValueError: If required environment variables are missing
        """
        self.mode = mode

        # Validate required config
        if not FRED_API_KEY:
            raise ValueError("FRED_API_KEY environment variable is required")
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables are required")

        # Initialize clients
        self.fred_client = FREDClient(FRED_API_KEY)
        self.supabase_loader = SupabaseLoader(SUPABASE_URL, SUPABASE_SERVICE_KEY)

        # Summary tracking
        self.summary: Dict[str, Any] = {
            "mode": mode,
            "started_at": datetime.now().isoformat(),
            "series_results": {},
            "total_fetched": 0,
            "total_upserted": 0,
            "total_failed": 0,
            "errors": [],
        }

    def _get_date_range(self) -> tuple[str, str]:
        """
        Determine the date range for fetching data.

        Returns:
            Tuple of (start_date, end_date) as YYYY-MM-DD strings
        """
        end_date = datetime.now().strftime("%Y-%m-%d")

        if self.mode == "backfill":
            start_date = BACKFILL_START_DATE
            logger.info(f"Backfill mode: fetching from {start_date} to {end_date}")
        else:  # incremental
            # Default to last 90 days
            start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
            logger.info(f"Incremental mode: fetching from {start_date} to {end_date}")

        return start_date, end_date

    def run(self) -> Dict[str, Any]:
        """
        Execute the full ingestion pipeline.

        Returns:
            Summary dictionary with results and statistics

        Raises:
            SystemExit: If critical errors occur
        """
        logger.info("=" * 80)
        logger.info("Starting US Economy Pulse Ingestion Pipeline")
        logger.info(f"Mode: {self.mode}")
        logger.info("=" * 80)

        try:
            # Create raw tables
            logger.info("Creating raw tables if they don't exist...")
            table_names = [config["table_name"] for config in SERIES_CONFIG.values()]
            try:
                self.supabase_loader.create_raw_tables(table_names)
            except SupabaseLoaderError as e:
                logger.error(f"Failed to create tables: {str(e)}")
                self.summary["errors"].append(f"Table creation error: {str(e)}")
                return self.summary

            # Get date range
            start_date, end_date = self._get_date_range()

            # Process each economic series
            for indicator_name, config in SERIES_CONFIG.items():
                logger.info(f"\nProcessing {indicator_name}...")
                series_id = config["series_id"]
                table_name = config["table_name"]

                try:
                    # Determine actual start date for incremental loads
                    if self.mode == "incremental":
                        try:
                            latest_date = self.supabase_loader.get_latest_date(
                                table_name, series_id
                            )
                            if latest_date:
                                # Start from the day after the latest date
                                actual_start = (latest_date + timedelta(days=1)).strftime(
                                    "%Y-%m-%d"
                                )
                                logger.info(
                                    f"Latest date in DB: {latest_date}, "
                                    f"fetching from {actual_start}"
                                )
                            else:
                                actual_start = start_date
                        except SupabaseLoaderError as e:
                            logger.warning(
                                f"Failed to get latest date for {series_id}, "
                                f"using default start date: {str(e)}"
                            )
                            actual_start = start_date
                    else:
                        actual_start = start_date

                    # Fetch observations from FRED
                    logger.info(
                        f"Fetching {series_id} from {actual_start} to {end_date}..."
                    )
                    observations = self.fred_client.get_series_observations(
                        series_id, actual_start, end_date
                    )

                    self.summary["total_fetched"] += len(observations)

                    if not observations:
                        logger.warning(f"No observations fetched for {series_id}")
                        self.summary["series_results"][indicator_name] = {
                            "fetched": 0,
                            "upserted": 0,
                            "failed": 0,
                            "status": "no_data",
                        }
                        continue

                    # Upsert to Supabase
                    logger.info(f"Upserting {len(observations)} observations to {table_name}...")
                    result = self.supabase_loader.upsert_observations(
                        table_name=table_name,
                        series_id=series_id,
                        observations=observations,
                        units=config.get("units", ""),
                        frequency=config.get("frequency", ""),
                    )

                    self.summary["total_upserted"] += result["upserted"]
                    self.summary["total_failed"] += result["failed"]

                    self.summary["series_results"][indicator_name] = {
                        "fetched": len(observations),
                        "upserted": result["upserted"],
                        "failed": result["failed"],
                        "status": "success" if result["upserted"] > 0 else "partial",
                    }

                    logger.info(
                        f"{indicator_name}: Fetched {len(observations)}, "
                        f"Upserted {result['upserted']}, Failed {result['failed']}"
                    )

                except FREDAPIError as e:
                    error_msg = f"FRED API error for {indicator_name}: {str(e)}"
                    logger.error(error_msg)
                    self.summary["errors"].append(error_msg)
                    self.summary["series_results"][indicator_name] = {
                        "status": "failed",
                        "error": str(e),
                    }

                except SupabaseLoaderError as e:
                    error_msg = f"Supabase error for {indicator_name}: {str(e)}"
                    logger.error(error_msg)
                    self.summary["errors"].append(error_msg)
                    self.summary["series_results"][indicator_name] = {
                        "status": "failed",
                        "error": str(e),
                    }

                except Exception as e:
                    error_msg = f"Unexpected error for {indicator_name}: {str(e)}"
                    logger.error(error_msg)
                    self.summary["errors"].append(error_msg)
                    self.summary["series_results"][indicator_name] = {
                        "status": "failed",
                        "error": str(e),
                    }

        except Exception as e:
            logger.error(f"Pipeline execution failed: {str(e)}", exc_info=True)
            self.summary["errors"].append(f"Pipeline error: {str(e)}")

        finally:
            # Log summary
            self.summary["completed_at"] = datetime.now().isoformat()
            self._log_summary()

        return self.summary

    def _log_summary(self) -> None:
        """Log ingestion summary statistics."""
        logger.info("\n" + "=" * 80)
        logger.info("Ingestion Pipeline Summary")
        logger.info("=" * 80)
        logger.info(f"Mode: {self.summary['mode']}")
        logger.info(f"Total Fetched: {self.summary['total_fetched']:,} records")
        logger.info(f"Total Upserted: {self.summary['total_upserted']:,} records")
        logger.info(f"Total Failed: {self.summary['total_failed']:,} records")
        logger.info(f"Started: {self.summary['started_at']}")
        logger.info(f"Completed: {self.summary['completed_at']}")

        if self.summary["errors"]:
            logger.warning(f"\nErrors encountered ({len(self.summary['errors'])}):")
            for error in self.summary["errors"]:
                logger.warning(f"  - {error}")

        logger.info("\nSeries Results:")
        for indicator, result in self.summary["series_results"].items():
            status = result.get("status", "unknown")
            if status == "success":
                logger.info(
                    f"  ✓ {indicator}: {result.get('upserted', 0)} upserted "
                    f"({result.get('fetched', 0)} fetched)"
                )
            elif status == "no_data":
                logger.info(f"  - {indicator}: No data available")
            elif status == "partial":
                logger.info(
                    f"  ⚠ {indicator}: {result.get('upserted', 0)} upserted, "
                    f"{result.get('failed', 0)} failed"
                )
            else:
                logger.error(f"  ✗ {indicator}: {result.get('error', 'Unknown error')}")

        logger.info("=" * 80 + "\n")


def main():
    """Parse arguments and run the ingestion pipeline."""
    parser = argparse.ArgumentParser(
        description="US Economy Pulse data ingestion pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.ingestion.run_ingestion --backfill
  python -m src.ingestion.run_ingestion --incremental
        """,
    )

    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Run in backfill mode (fetch full history from 2000-01-01)",
    )

    parser.add_argument(
        "--incremental",
        action="store_true",
        default=True,
        help="Run in incremental mode (fetch last 90 days) [default]",
    )

    args = parser.parse_args()

    # Determine mode
    mode = "backfill" if args.backfill else "incremental"

    # Load environment variables
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        logger.info(f"Loaded environment from {env_file}")
    else:
        logger.warning(f"No .env file found at {env_file}")

    # Run pipeline
    try:
        pipeline = IngestionPipeline(mode=mode)
        summary = pipeline.run()

        # Exit with error if there were failures
        if summary["errors"]:
            sys.exit(1)

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
