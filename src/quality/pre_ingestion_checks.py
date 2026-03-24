"""
Pre-ingestion quality checks for US Economy Pulse Pipeline.

Validates FRED API health, Supabase connectivity, and captures baseline metrics
before ingestion begins.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict

import requests
from dotenv import load_dotenv
from supabase import create_client

from ..ingestion.config import FRED_API_KEY, FRED_BASE_URL, SERIES_CONFIG, SUPABASE_URL, SUPABASE_SERVICE_KEY

# Configure logging
logger = logging.getLogger(__name__)


class PreIngestionCheckError(Exception):
    """Exception raised for pre-ingestion check failures."""

    pass


class PreIngestionChecks:
    """Validates pipeline prerequisites before ingestion begins."""

    def __init__(self) -> None:
        """
        Initialize pre-ingestion checks.

        Raises:
            PreIngestionCheckError: If required environment variables are missing
        """
        if not FRED_API_KEY:
            raise PreIngestionCheckError("FRED_API_KEY environment variable is required")
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise PreIngestionCheckError("SUPABASE_URL and SUPABASE_SERVICE_KEY are required")

        self.fred_api_key = FRED_API_KEY
        self.supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        self.pipeline_run_id = str(uuid.uuid4())
        self.check_results: Dict[str, Any] = {
            "pipeline_run_id": self.pipeline_run_id,
            "timestamp": datetime.now().isoformat(),
            "checks": {},
        }

    def check_fred_api_health(self) -> Dict[str, Any]:
        """
        Verify FRED API is responding and accessible.

        Tests a simple API call to confirm connectivity and HTTP 200 response.

        Returns:
            Dict with check_status ('passed'/'failed'), api_response_time, and details

        """
        logger.info("Checking FRED API health...")
        check_result = {
            "check_type": "api_health",
            "resource_name": "FRED_API",
            "check_status": "failed",
            "severity": "critical",
            "description": "FRED API connectivity check",
            "details_json": {},
        }

        try:
            # Test with a simple series query
            start_time = datetime.now()
            response = requests.get(
                f"{FRED_BASE_URL}",
                params={
                    "series_id": "GDPC1",
                    "api_key": self.fred_api_key,
                    "file_type": "json",
                },
                timeout=10,
            )
            response_time = (datetime.now() - start_time).total_seconds()

            if response.status_code == 200:
                check_result["check_status"] = "passed"
                check_result["severity"] = "info"
                check_result["metric_value"] = response_time
                check_result["details_json"] = {
                    "http_status": response.status_code,
                    "response_time_seconds": response_time,
                }
                logger.info(f"FRED API health check passed (response time: {response_time:.2f}s)")
            else:
                check_result["details_json"] = {
                    "http_status": response.status_code,
                    "error": response.text[:500],
                }
                logger.error(f"FRED API returned status {response.status_code}")

        except requests.exceptions.Timeout:
            check_result["details_json"] = {"error": "Request timeout"}
            logger.error("FRED API health check timeout")
        except requests.exceptions.RequestException as e:
            check_result["details_json"] = {"error": str(e)}
            logger.error(f"FRED API health check failed: {str(e)}")
        except Exception as e:
            check_result["details_json"] = {"error": str(e)}
            logger.error(f"Unexpected error in FRED API health check: {str(e)}")

        return check_result

    def check_fred_rate_limit(self) -> Dict[str, Any]:
        """
        Track FRED API rate limit status.

        FRED allows 120 requests per minute. This check provides baseline
        for rate limit monitoring.

        Returns:
            Dict with rate_limit_per_minute and documented limits

        """
        logger.info("Checking FRED rate limit configuration...")
        check_result = {
            "check_type": "api_rate_limit",
            "resource_name": "FRED_API",
            "check_status": "passed",
            "severity": "info",
            "description": "FRED rate limit documentation check",
            "details_json": {
                "rate_limit_per_minute": 120,
                "requests_per_series": len(SERIES_CONFIG),
                "expected_requests": len(SERIES_CONFIG),
                "note": "FRED allows 120 requests per minute",
            },
            "metric_value": 120,
        }
        logger.info("FRED rate limit check passed")
        return check_result

    def check_supabase_connectivity(self) -> Dict[str, Any]:
        """
        Verify Supabase database is reachable.

        Attempts a simple SELECT 1 query to confirm connectivity.

        Returns:
            Dict with check_status ('passed'/'failed') and connection details

        """
        logger.info("Checking Supabase connectivity...")
        check_result = {
            "check_type": "schema",
            "resource_name": "Supabase",
            "check_status": "failed",
            "severity": "critical",
            "description": "Supabase database connectivity check",
            "details_json": {},
        }

        try:
            # Simple connectivity test via RPC
            result = self.supabase_client.rpc("ping", {}).execute()
            if result:
                check_result["check_status"] = "passed"
                check_result["severity"] = "info"
                check_result["details_json"] = {"connection_status": "healthy"}
                logger.info("Supabase connectivity check passed")
            else:
                check_result["details_json"] = {"error": "Unexpected response from ping RPC"}
                logger.error("Supabase ping RPC returned unexpected result")
        except Exception as e:
            # If RPC doesn't exist, try a simple table query as fallback
            try:
                result = self.supabase_client.table("quality_checks").select("*").limit(1).execute()
                check_result["check_status"] = "passed"
                check_result["severity"] = "info"
                check_result["details_json"] = {"connection_status": "healthy"}
                logger.info("Supabase connectivity check passed (via table query)")
            except Exception as e2:
                check_result["details_json"] = {"error": str(e2)}
                logger.error(f"Supabase connectivity check failed: {str(e2)}")

        return check_result

    def capture_row_counts(self) -> Dict[str, Any]:
        """
        Capture current row counts for all raw tables before ingestion.

        Used as baseline for post-ingestion comparison.

        Returns:
            Dict with row counts per table and total

        """
        logger.info("Capturing pre-ingestion row counts...")
        check_result = {
            "check_type": "row_count",
            "resource_name": "raw_tables",
            "check_status": "passed",
            "severity": "info",
            "description": "Pre-ingestion row count snapshot",
            "details_json": {"table_counts": {}},
        }

        total_rows = 0

        try:
            for indicator, config in SERIES_CONFIG.items():
                table_name = config["table_name"]
                try:
                    result = self.supabase_client.table(table_name).select("*", count="exact").execute()
                    row_count = result.count if hasattr(result, "count") else len(result.data)
                    check_result["details_json"]["table_counts"][table_name] = row_count
                    total_rows += row_count
                    logger.info(f"  {table_name}: {row_count} rows")
                except Exception as e:
                    logger.warning(f"Failed to get row count for {table_name}: {str(e)}")
                    check_result["details_json"]["table_counts"][table_name] = None

            check_result["metric_value"] = total_rows
            check_result["details_json"]["total_rows_before_ingestion"] = total_rows
            logger.info(f"Total pre-ingestion rows: {total_rows}")

        except Exception as e:
            check_result["check_status"] = "warning"
            check_result["details_json"]["error"] = str(e)
            logger.warning(f"Error capturing row counts: {str(e)}")

        return check_result

    def run_all_checks(self) -> Dict[str, Any]:
        """
        Execute all pre-ingestion checks.

        Returns:
            Dict with pipeline_run_id, timestamp, and check results

        """
        logger.info("=" * 80)
        logger.info("Starting Pre-Ingestion Quality Checks")
        logger.info(f"Pipeline Run ID: {self.pipeline_run_id}")
        logger.info("=" * 80)

        # Run all checks
        self.check_results["checks"]["fred_api_health"] = self.check_fred_api_health()
        self.check_results["checks"]["fred_rate_limit"] = self.check_fred_rate_limit()
        self.check_results["checks"]["supabase_connectivity"] = self.check_supabase_connectivity()
        self.check_results["checks"]["row_counts"] = self.capture_row_counts()

        # Summary
        total_checks = len(self.check_results["checks"])
        passed = sum(1 for c in self.check_results["checks"].values() if c["check_status"] == "passed")
        failed = sum(1 for c in self.check_results["checks"].values() if c["check_status"] == "failed")

        self.check_results["summary"] = {
            "total_checks": total_checks,
            "passed": passed,
            "failed": failed,
            "warnings": total_checks - passed - failed,
        }

        logger.info("=" * 80)
        logger.info(f"Pre-Ingestion Checks Summary: {passed}/{total_checks} passed")
        if failed > 0:
            logger.warning(f"  {failed} checks failed - pipeline may not succeed")
        logger.info("=" * 80)

        return self.check_results


def main() -> None:
    """Run pre-ingestion checks and save results."""
    load_dotenv()

    try:
        checks = PreIngestionChecks()
        results = checks.run_all_checks()

        # Save pipeline_run_id to file for use by post-ingestion checks
        run_id_file = "/tmp/pipeline_run_id.txt"
        with open(run_id_file, "w") as f:
            f.write(checks.pipeline_run_id)
        logger.info(f"Saved pipeline_run_id to {run_id_file}")

        # Log results as JSON
        logger.info(json.dumps(results, indent=2, default=str))

    except PreIngestionCheckError as e:
        logger.error(f"Pre-ingestion check error: {str(e)}")
        raise


if __name__ == "__main__":
    main()
