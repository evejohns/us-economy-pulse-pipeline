"""
Post-transform quality checks for US Economy Pulse Pipeline.

Validates data quality after dbt transforms, including row counts, anomaly detection,
staleness checks, and dbt test result parsing.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from supabase import create_client

from ..ingestion.config import SERIES_CONFIG, SUPABASE_URL, SUPABASE_SERVICE_KEY

# Configure logging
logger = logging.getLogger(__name__)


class PostTransformCheckError(Exception):
    """Exception raised for post-transform check failures."""

    pass


class PostTransformChecks:
    """Validates data quality after dbt transforms."""

    def __init__(self, pipeline_run_id: str) -> None:
        """
        Initialize post-transform checks.

        Args:
            pipeline_run_id: ID from pre-ingestion checks for consistency

        Raises:
            PostTransformCheckError: If required environment variables are missing
        """
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise PostTransformCheckError("SUPABASE_URL and SUPABASE_SERVICE_KEY are required")

        self.supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        self.pipeline_run_id = pipeline_run_id
        self.check_results: Dict[str, Any] = {
            "pipeline_run_id": pipeline_run_id,
            "timestamp": datetime.now().isoformat(),
            "checks": {},
        }

        # Expected staleness windows (in days)
        self.staleness_windows = {
            "GDPC1": 45,  # GDP: quarterly
            "CPIAUCSL": 15,  # CPI: monthly
            "UNRATE": 15,  # Unemployment: monthly
            "FEDFUNDS": 15,  # Federal Funds: monthly
            "UMCSENT": 15,  # Consumer Sentiment: monthly
            "HOUST": 15,  # Housing Starts: monthly
        }

    def check_row_count_growth(self, pre_ingestion_counts: Dict[str, int]) -> Dict[str, Any]:
        """
        Compare post-ingestion row counts with pre-ingestion baseline.

        Flags if no new data was added.

        Args:
            pre_ingestion_counts: Row counts captured before ingestion

        Returns:
            Dict with check results for each table

        """
        logger.info("Checking row count growth...")
        check_result = {
            "check_type": "row_count",
            "resource_name": "raw_tables",
            "check_status": "passed",
            "severity": "info",
            "description": "Post-ingestion row count comparison",
            "details_json": {"table_comparisons": {}},
        }

        try:
            total_new_rows = 0
            tables_with_no_growth = []

            for indicator, config in SERIES_CONFIG.items():
                table_name = config["table_name"]
                series_id = config["series_id"]

                try:
                    # Get current row count
                    result = self.supabase_client.table(table_name).select("*", count="exact").execute()
                    current_count = result.count if hasattr(result, "count") else len(result.data)

                    # Compare with pre-ingestion count
                    pre_count = pre_ingestion_counts.get(table_name, 0) or 0
                    new_rows = current_count - pre_count

                    comparison = {
                        "table_name": table_name,
                        "series_id": series_id,
                        "pre_ingestion": pre_count,
                        "post_ingestion": current_count,
                        "new_rows": new_rows,
                        "status": "growth" if new_rows > 0 else "no_growth",
                    }

                    check_result["details_json"]["table_comparisons"][table_name] = comparison

                    if new_rows > 0:
                        total_new_rows += new_rows
                        logger.info(f"  {table_name}: +{new_rows} rows ({pre_count} -> {current_count})")
                    else:
                        tables_with_no_growth.append(table_name)
                        logger.warning(f"  {table_name}: no new rows")

                except Exception as e:
                    logger.warning(f"Failed to get row count for {table_name}: {str(e)}")
                    check_result["details_json"]["table_comparisons"][table_name] = {"error": str(e)}

            check_result["metric_value"] = total_new_rows
            check_result["details_json"]["total_new_rows"] = total_new_rows
            check_result["details_json"]["tables_with_no_growth"] = tables_with_no_growth

            # Flag as warning if no growth
            if total_new_rows == 0:
                check_result["check_status"] = "warning"
                check_result["severity"] = "warning"
                logger.warning("No new rows added during ingestion")
            else:
                logger.info(f"Total new rows: {total_new_rows}")

        except Exception as e:
            check_result["check_status"] = "failed"
            check_result["severity"] = "critical"
            check_result["details_json"]["error"] = str(e)
            logger.error(f"Row count check failed: {str(e)}")

        return check_result

    def detect_anomalies_zscore(self) -> Dict[str, Any]:
        """
        Detect anomalies in latest values using Z-score method.

        Pulls last 24 months of data, computes mean/stddev, flags if
        latest value is >3 sigma from mean.

        Returns:
            Dict with anomaly check results per series

        """
        logger.info("Running Z-score anomaly detection...")
        check_result = {
            "check_type": "anomaly",
            "resource_name": "economic_series",
            "check_status": "passed",
            "severity": "info",
            "description": "Z-score anomaly detection on latest values",
            "details_json": {"anomalies": []},
        }

        lookback_days = 365 * 2  # 24 months

        try:
            for indicator, config in SERIES_CONFIG.items():
                table_name = config["table_name"]
                series_id = config["series_id"]

                try:
                    # Get data from last 24 months
                    cutoff_date = (datetime.now() - timedelta(days=lookback_days)).isoformat()

                    result = (
                        self.supabase_client.table(table_name)
                        .select("observation_date, value")
                        .filter("observation_date", "gte", cutoff_date)
                        .order("observation_date", desc=True)
                        .execute()
                    )

                    if not result.data or len(result.data) < 2:
                        logger.debug(f"Insufficient data for {series_id} anomaly detection")
                        continue

                    # Extract values
                    values = [float(row["value"]) for row in result.data if row["value"] is not None]

                    if len(values) < 2:
                        continue

                    # Compute statistics
                    mean = sum(values) / len(values)
                    variance = sum((x - mean) ** 2 for x in values) / len(values)
                    stddev = variance ** 0.5

                    # Check latest value
                    latest_value = values[0]  # Ordered DESC, so first is latest
                    zscore = (latest_value - mean) / stddev if stddev > 0 else 0

                    # Flag if > 3 sigma
                    if abs(zscore) > 3:
                        anomaly = {
                            "series_id": series_id,
                            "latest_value": latest_value,
                            "mean": mean,
                            "stddev": stddev,
                            "zscore": zscore,
                            "anomaly_detected": True,
                        }
                        check_result["details_json"]["anomalies"].append(anomaly)
                        check_result["check_status"] = "warning"
                        check_result["severity"] = "warning"
                        logger.warning(
                            f"  Anomaly detected in {series_id}: "
                            f"value={latest_value}, z-score={zscore:.2f}"
                        )
                    else:
                        logger.debug(f"  {series_id}: z-score={zscore:.2f} (normal)")

                except Exception as e:
                    logger.warning(f"Anomaly detection failed for {series_id}: {str(e)}")

        except Exception as e:
            check_result["check_status"] = "warning"
            check_result["severity"] = "warning"
            check_result["details_json"]["error"] = str(e)
            logger.warning(f"Anomaly detection check failed: {str(e)}")

        return check_result

    def check_data_staleness(self) -> Dict[str, Any]:
        """
        Check that each series has recent data within expected windows.

        Returns:
            Dict with staleness status per series

        """
        logger.info("Checking data staleness...")
        check_result = {
            "check_type": "freshness",
            "resource_name": "economic_series",
            "check_status": "passed",
            "severity": "info",
            "description": "Data freshness check - verify recent observations exist",
            "details_json": {"stale_series": []},
        }

        now = datetime.now()

        try:
            for indicator, config in SERIES_CONFIG.items():
                table_name = config["table_name"]
                series_id = config["series_id"]
                expected_window = self.staleness_windows.get(series_id, 15)

                try:
                    # Get latest observation date
                    result = (
                        self.supabase_client.table(table_name)
                        .select("observation_date")
                        .order("observation_date", desc=True)
                        .limit(1)
                        .execute()
                    )

                    if not result.data:
                        stale = {
                            "series_id": series_id,
                            "status": "no_data",
                            "expected_window_days": expected_window,
                        }
                        check_result["details_json"]["stale_series"].append(stale)
                        check_result["check_status"] = "warning"
                        check_result["severity"] = "warning"
                        logger.warning(f"  {series_id}: no data available")
                        continue

                    latest_date_str = result.data[0]["observation_date"]
                    latest_date = datetime.fromisoformat(latest_date_str)
                    days_old = (now - latest_date).days

                    if days_old > expected_window:
                        stale = {
                            "series_id": series_id,
                            "latest_date": latest_date_str,
                            "days_old": days_old,
                            "expected_window_days": expected_window,
                            "status": "stale",
                        }
                        check_result["details_json"]["stale_series"].append(stale)
                        check_result["check_status"] = "warning"
                        check_result["severity"] = "warning"
                        logger.warning(f"  {series_id}: {days_old} days old (expected {expected_window})")
                    else:
                        logger.info(f"  {series_id}: fresh ({days_old} days old)")

                except Exception as e:
                    logger.warning(f"Staleness check failed for {series_id}: {str(e)}")

        except Exception as e:
            check_result["check_status"] = "warning"
            check_result["severity"] = "warning"
            check_result["details_json"]["error"] = str(e)
            logger.warning(f"Staleness check failed: {str(e)}")

        return check_result

    def parse_dbt_test_results(self, dbt_run_results_path: str = None) -> Dict[str, Any]:
        """
        Parse dbt test results from run_results.json.

        Extracts failed tests and their details.

        Args:
            dbt_run_results_path: Path to dbt's run_results.json. If None, searches common locations.

        Returns:
            Dict with failed test details

        """
        logger.info("Parsing dbt test results...")
        check_result = {
            "check_type": "schema",
            "resource_name": "dbt_tests",
            "check_status": "passed",
            "severity": "info",
            "description": "dbt test result parsing",
            "details_json": {"failed_tests": [], "passed_tests": 0},
        }

        # Search for run_results.json if path not provided
        if not dbt_run_results_path:
            possible_paths = [
                Path("/sessions/keen-confident-hamilton/project/dbt_project/target/run_results.json"),
                Path("/sessions/keen-confident-hamilton/project/target/run_results.json"),
                Path("./dbt_project/target/run_results.json"),
                Path("./target/run_results.json"),
            ]

            for path in possible_paths:
                if path.exists():
                    dbt_run_results_path = str(path)
                    break

        if not dbt_run_results_path or not Path(dbt_run_results_path).exists():
            logger.warning(f"dbt run_results.json not found at expected locations")
            check_result["details_json"]["note"] = "run_results.json not found - skipping dbt test parsing"
            return check_result

        try:
            with open(dbt_run_results_path, "r") as f:
                run_results = json.load(f)

            if "results" not in run_results:
                logger.warning("No 'results' key in run_results.json")
                return check_result

            failed_count = 0
            passed_count = 0

            for result in run_results["results"]:
                if result.get("resource_type") == "test":
                    status = result.get("status")

                    if status == "fail":
                        failed_count += 1
                        failed_test = {
                            "test_name": result.get("name"),
                            "node_id": result.get("unique_id"),
                            "status": status,
                            "message": result.get("message"),
                        }
                        check_result["details_json"]["failed_tests"].append(failed_test)
                        logger.warning(f"  Failed test: {result.get('name')}")

                    elif status == "pass":
                        passed_count += 1

            check_result["details_json"]["passed_tests"] = passed_count
            check_result["metric_value"] = failed_count

            if failed_count > 0:
                check_result["check_status"] = "failed"
                check_result["severity"] = "critical"
                logger.error(f"dbt tests: {failed_count} failed, {passed_count} passed")
            else:
                logger.info(f"dbt tests: all {passed_count} passed")

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse run_results.json: {str(e)}")
            check_result["details_json"]["error"] = f"Invalid JSON: {str(e)}"
        except Exception as e:
            logger.warning(f"Error parsing dbt results: {str(e)}")
            check_result["details_json"]["error"] = str(e)

        return check_result

    def write_checks_to_database(self) -> None:
        """
        Write all quality check results to Supabase quality_checks table.

        Raises:
            PostTransformCheckError: If database write fails

        """
        logger.info("Writing quality checks to database...")

        try:
            for check_name, check_data in self.check_results["checks"].items():
                # Prepare record for database
                record = {
                    "pipeline_run_id": self.pipeline_run_id,
                    "check_timestamp": datetime.now().isoformat(),
                    "check_type": check_data.get("check_type"),
                    "resource_name": check_data.get("resource_name"),
                    "check_status": check_data.get("check_status"),
                    "severity": check_data.get("severity"),
                    "metric_value": check_data.get("metric_value"),
                    "threshold_value": check_data.get("threshold_value"),
                    "description": check_data.get("description"),
                    "details_json": check_data.get("details_json", {}),
                    "dbt_run_id": check_data.get("dbt_run_id"),
                }

                # Insert into quality_checks table
                result = self.supabase_client.table("quality_checks").insert(record).execute()
                logger.info(f"Inserted check result: {check_name}")

        except Exception as e:
            logger.error(f"Failed to write checks to database: {str(e)}")
            raise PostTransformCheckError(f"Database write failed: {str(e)}")

    def run_all_checks(self, pre_ingestion_counts: Dict[str, int] = None) -> Dict[str, Any]:
        """
        Execute all post-transform checks.

        Args:
            pre_ingestion_counts: Row counts from pre-ingestion phase

        Returns:
            Dict with summary of all check results

        """
        logger.info("=" * 80)
        logger.info("Starting Post-Transform Quality Checks")
        logger.info(f"Pipeline Run ID: {self.pipeline_run_id}")
        logger.info("=" * 80)

        # Run checks
        self.check_results["checks"]["row_count_growth"] = self.check_row_count_growth(
            pre_ingestion_counts or {}
        )
        self.check_results["checks"]["anomaly_detection"] = self.detect_anomalies_zscore()
        self.check_results["checks"]["data_staleness"] = self.check_data_staleness()
        self.check_results["checks"]["dbt_tests"] = self.parse_dbt_test_results()

        # Summary
        total_checks = len(self.check_results["checks"])
        passed = sum(1 for c in self.check_results["checks"].values() if c["check_status"] == "passed")
        failed = sum(1 for c in self.check_results["checks"].values() if c["check_status"] == "failed")
        warnings = sum(1 for c in self.check_results["checks"].values() if c["check_status"] == "warning")

        self.check_results["summary"] = {
            "total_checks": total_checks,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
        }

        logger.info("=" * 80)
        logger.info(f"Post-Transform Checks Summary: {passed} passed, {failed} failed, {warnings} warnings")
        logger.info("=" * 80)

        return self.check_results


def main() -> None:
    """Run post-transform checks and write results to database."""
    load_dotenv()

    # Load pipeline_run_id from file
    run_id_file = "/tmp/pipeline_run_id.txt"
    try:
        with open(run_id_file, "r") as f:
            pipeline_run_id = f.read().strip()
        logger.info(f"Loaded pipeline_run_id: {pipeline_run_id}")
    except FileNotFoundError:
        pipeline_run_id = "manual_run"
        logger.warning(f"Could not find {run_id_file}, using manual_run")

    try:
        checks = PostTransformChecks(pipeline_run_id)
        results = checks.run_all_checks()

        # Write to database
        checks.write_checks_to_database()

        logger.info(json.dumps(results, indent=2, default=str))

    except PostTransformCheckError as e:
        logger.error(f"Post-transform check error: {str(e)}")
        raise


if __name__ == "__main__":
    main()
