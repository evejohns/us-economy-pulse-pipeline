"""
Main orchestrator for US Economy Pulse Pipeline quality checks.

Coordinates pre-ingestion, post-transform, and alerting workflows.
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

from .alerting import alert_on_failure, send_daily_summary
from .post_transform_checks import PostTransformChecks, PostTransformCheckError
from .pre_ingestion_checks import PreIngestionChecks, PreIngestionCheckError

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class QualityCheckOrchestrator:
    """Orchestrates all quality checks for the ingestion pipeline."""

    def __init__(self, stage: str = "full") -> None:
        """
        Initialize the quality check orchestrator.

        Args:
            stage: 'pre', 'post', or 'full' - which checks to run

        """
        self.stage = stage
        self.pipeline_run_id: str = None
        self.pre_ingestion_results: Dict[str, Any] = {}
        self.post_transform_results: Dict[str, Any] = {}
        self.final_summary: Dict[str, Any] = {
            "stage": stage,
            "started_at": datetime.now().isoformat(),
            "run_by_orchestrator": True,
        }

    def run_pre_ingestion_checks(self) -> bool:
        """
        Run pre-ingestion quality checks.

        Returns:
            True if all critical checks passed, False if any critical failures

        """
        logger.info("Running pre-ingestion quality checks...")

        try:
            checks = PreIngestionChecks()
            self.pre_ingestion_results = checks.run_all_checks()
            self.pipeline_run_id = checks.pipeline_run_id

            # Save pipeline_run_id for post-ingestion consistency
            self._save_pipeline_run_id()

            # Check for critical failures
            failed = self.pre_ingestion_results.get("summary", {}).get("failed", 0)
            critical_checks = [
                c
                for c in self.pre_ingestion_results.get("checks", {}).values()
                if c.get("severity") == "critical" and c.get("check_status") == "failed"
            ]

            if critical_checks:
                logger.error(
                    f"Critical pre-ingestion failures: {len(critical_checks)} checks failed"
                )
                return False

            logger.info(f"Pre-ingestion checks completed: {self.pre_ingestion_results['summary']}")
            return True

        except PreIngestionCheckError as e:
            logger.error(f"Pre-ingestion check error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in pre-ingestion checks: {str(e)}", exc_info=True)
            return False

    def run_post_transform_checks(self) -> bool:
        """
        Run post-transform quality checks.

        Requires pipeline_run_id from pre-ingestion or file.

        Returns:
            True if all critical checks passed, False if any critical failures

        """
        logger.info("Running post-transform quality checks...")

        # Load pipeline_run_id if not already set
        if not self.pipeline_run_id:
            self.pipeline_run_id = self._load_pipeline_run_id()

        if not self.pipeline_run_id:
            logger.error("Cannot run post-transform checks without pipeline_run_id")
            return False

        try:
            checks = PostTransformChecks(self.pipeline_run_id)

            # Extract pre-ingestion row counts if available
            pre_counts = {}
            if self.pre_ingestion_results:
                pre_counts = (
                    self.pre_ingestion_results.get("checks", {})
                    .get("row_counts", {})
                    .get("details_json", {})
                    .get("table_counts", {})
                )

            self.post_transform_results = checks.run_all_checks(pre_ingestion_counts=pre_counts)

            # Write to database
            checks.write_checks_to_database()

            # Check for critical failures
            critical_checks = [
                c
                for c in self.post_transform_results.get("checks", {}).values()
                if c.get("severity") == "critical" and c.get("check_status") == "failed"
            ]

            if critical_checks:
                logger.error(
                    f"Critical post-transform failures: {len(critical_checks)} checks failed"
                )
                return False

            logger.info(f"Post-transform checks completed: {self.post_transform_results['summary']}")
            return True

        except PostTransformCheckError as e:
            logger.error(f"Post-transform check error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in post-transform checks: {str(e)}", exc_info=True)
            return False

    def send_alerts(self) -> None:
        """
        Send Slack alerts based on check results.

        Sends failure alerts if any checks failed, and/or daily summary.

        """
        # Use post-transform results if available, otherwise pre-ingestion
        results = self.post_transform_results or self.pre_ingestion_results

        if not results:
            logger.warning("No check results available for alerting")
            return

        # Send failure alert if needed
        try:
            alert_on_failure(results)
        except Exception as e:
            logger.warning(f"Failed to send failure alert: {str(e)}")

        # Optionally send daily summary
        # Uncomment to enable daily summaries:
        # try:
        #     send_daily_summary(results)
        # except Exception as e:
        #     logger.warning(f"Failed to send daily summary: {str(e)}")

    def compile_final_summary(self) -> Dict[str, Any]:
        """
        Compile final summary of all check stages.

        Returns:
            Dict with combined results from all stages

        """
        self.final_summary["completed_at"] = datetime.now().isoformat()

        if self.pre_ingestion_results:
            self.final_summary["pre_ingestion"] = self.pre_ingestion_results

        if self.post_transform_results:
            self.final_summary["post_transform"] = self.post_transform_results

        # Aggregate summary
        all_passed = 0
        all_failed = 0
        all_warnings = 0

        for stage_results in [self.pre_ingestion_results, self.post_transform_results]:
            if stage_results:
                summary = stage_results.get("summary", {})
                all_passed += summary.get("passed", 0)
                all_failed += summary.get("failed", 0)
                all_warnings += summary.get("warnings", 0)

        self.final_summary["aggregate_summary"] = {
            "total_passed": all_passed,
            "total_failed": all_failed,
            "total_warnings": all_warnings,
            "pipeline_run_id": self.pipeline_run_id,
        }

        return self.final_summary

    def _save_pipeline_run_id(self) -> None:
        """Save pipeline_run_id to file for use by subsequent stages."""
        run_id_file = Path("/tmp/pipeline_run_id.txt")
        try:
            with open(run_id_file, "w") as f:
                f.write(self.pipeline_run_id)
            logger.info(f"Saved pipeline_run_id to {run_id_file}")
        except Exception as e:
            logger.warning(f"Failed to save pipeline_run_id: {str(e)}")

    def _load_pipeline_run_id(self) -> str:
        """Load pipeline_run_id from file."""
        run_id_file = Path("/tmp/pipeline_run_id.txt")
        try:
            if run_id_file.exists():
                with open(run_id_file, "r") as f:
                    run_id = f.read().strip()
                logger.info(f"Loaded pipeline_run_id from file: {run_id}")
                return run_id
        except Exception as e:
            logger.warning(f"Failed to load pipeline_run_id from file: {str(e)}")

        return None

    def run(self) -> int:
        """
        Execute quality checks based on configured stage.

        Returns:
            Exit code: 0 if all checks passed, 1 if critical failures

        """
        logger.info("=" * 80)
        logger.info("US Economy Pulse Pipeline - Quality Check Orchestrator")
        logger.info(f"Stage: {self.stage}")
        logger.info("=" * 80)

        all_passed = True

        # Run pre-ingestion checks
        if self.stage in ["pre", "full"]:
            pre_success = self.run_pre_ingestion_checks()
            if not pre_success:
                all_passed = False
                if self.stage == "pre":
                    # Pre-only mode: fail the pipeline
                    logger.error("Pre-ingestion checks failed. Aborting pipeline.")

        # Run post-transform checks
        if self.stage in ["post", "full"]:
            post_success = self.run_post_transform_checks()
            if not post_success:
                all_passed = False

        # Send alerts
        self.send_alerts()

        # Compile and log final summary
        final_summary = self.compile_final_summary()
        logger.info("=" * 80)
        logger.info("Final Quality Check Summary")
        logger.info("=" * 80)
        logger.info(json.dumps(final_summary, indent=2, default=str))
        logger.info("=" * 80)

        # Return appropriate exit code
        if all_passed:
            logger.info("All quality checks passed ✓")
            return 0
        else:
            logger.error("Some quality checks failed ✗")
            return 1


def main() -> None:
    """Parse arguments and run quality check orchestrator."""
    parser = argparse.ArgumentParser(
        description="US Economy Pulse Pipeline Quality Check Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.quality.run_quality_checks --stage pre
  python -m src.quality.run_quality_checks --stage post
  python -m src.quality.run_quality_checks --stage full
        """,
    )

    parser.add_argument(
        "--stage",
        choices=["pre", "post", "full"],
        default="full",
        help="Which quality checks to run [default: full]",
    )

    args = parser.parse_args()

    # Load environment variables
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        logger.info(f"Loaded environment from {env_file}")
    else:
        logger.warning(f"No .env file found at {env_file}")

    # Run orchestrator
    try:
        orchestrator = QualityCheckOrchestrator(stage=args.stage)
        exit_code = orchestrator.run()
        sys.exit(exit_code)

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
