"""
Alerting system for US Economy Pulse Pipeline quality checks.

Sends Slack notifications when checks fail or for daily digests.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)


class SlackAlertError(Exception):
    """Exception raised for Slack alerting failures."""

    pass


class SlackAlerter:
    """Manages Slack notifications for quality check results."""

    def __init__(self, webhook_url: Optional[str] = None) -> None:
        """
        Initialize Slack alerter.

        Args:
            webhook_url: Slack Incoming Webhook URL. If None, loads from SLACK_WEBHOOK_URL env var.

        """
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")

        if not self.webhook_url:
            logger.warning(
                "SLACK_WEBHOOK_URL not configured. Alerts will be logged to stdout instead."
            )

    def _send_slack_message(self, payload: Dict[str, Any]) -> bool:
        """
        Send message to Slack webhook.

        Args:
            payload: Slack message payload (dict)

        Returns:
            True if successful, False otherwise

        """
        if not self.webhook_url:
            logger.info(f"Slack not configured. Message: {json.dumps(payload, indent=2)}")
            return True  # Graceful fallback

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )

            if response.status_code == 200:
                logger.info("Slack alert sent successfully")
                return True
            else:
                logger.error(f"Slack webhook returned status {response.status_code}: {response.text}")
                return False

        except requests.exceptions.Timeout:
            logger.error("Slack webhook request timeout")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Slack message: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Slack message: {str(e)}")
            return False

    def alert_on_failure(self, check_results: Dict[str, Any]) -> bool:
        """
        Send alert to Slack if checks contain failures or critical issues.

        Only sends if there are failed or critical checks. Silent success if all passed.

        Args:
            check_results: Results dict from quality checks

        Returns:
            True if alert sent or no alert needed, False if send failed

        """
        # Extract summary
        summary = check_results.get("summary", {})
        failed = summary.get("failed", 0)
        warnings = summary.get("warnings", 0)

        # Only alert if there are failures
        if failed == 0:
            logger.info("No failures detected - no alert needed")
            return True

        logger.warning(f"Failures detected ({failed}). Sending Slack alert...")

        # Build failure message
        failed_checks = []
        for check_name, check_data in check_results.get("checks", {}).items():
            if check_data.get("check_status") in ["failed", "warning"]:
                failed_checks.append(
                    {
                        "type": check_data.get("check_type"),
                        "resource": check_data.get("resource_name"),
                        "status": check_data.get("check_status"),
                        "severity": check_data.get("severity"),
                        "description": check_data.get("description"),
                    }
                )

        # Build Slack message
        timestamp = check_results.get("timestamp", datetime.now().isoformat())
        pipeline_run_id = check_results.get("pipeline_run_id", "unknown")

        fields = [
            {"title": "Pipeline Run ID", "value": pipeline_run_id, "short": True},
            {"title": "Timestamp", "value": timestamp, "short": True},
            {"title": "Failed Checks", "value": str(failed), "short": True},
            {"title": "Warnings", "value": str(warnings), "short": True},
        ]

        # Add failed check details
        failed_details = "\n".join(
            [
                f"• {c['type'].upper()} ({c['resource']}): {c['description']} [_{c['severity'].upper()}_]"
                for c in failed_checks
            ]
        )

        if failed_details:
            fields.append({"title": "Failed Checks", "value": failed_details, "short": False})

        payload = {
            "attachments": [
                {
                    "fallback": f"US Economy Pipeline Alert: {failed} checks failed",
                    "color": "danger" if failed > 0 else "warning",
                    "title": "🚨 US Economy Pipeline Alert",
                    "title_link": "https://app.supabase.com/",
                    "fields": fields,
                    "footer": "Quality Check System",
                    "ts": int(datetime.now().timestamp()),
                }
            ]
        }

        return self._send_slack_message(payload)

    def send_daily_summary(self, check_results: Dict[str, Any]) -> bool:
        """
        Send daily digest to Slack regardless of pass/fail status.

        Args:
            check_results: Results dict from quality checks

        Returns:
            True if alert sent successfully, False if send failed

        """
        logger.info("Sending daily summary to Slack...")

        # Extract summary
        summary = check_results.get("summary", {})
        total = summary.get("total_checks", 0)
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        warnings = summary.get("warnings", 0)

        timestamp = check_results.get("timestamp", datetime.now().isoformat())
        pipeline_run_id = check_results.get("pipeline_run_id", "unknown")

        # Determine color based on results
        if failed > 0:
            color = "danger"
            status_emoji = "🚨"
        elif warnings > 0:
            color = "warning"
            status_emoji = "⚠️"
        else:
            color = "good"
            status_emoji = "✅"

        # Build fields
        fields = [
            {"title": "Pipeline Run ID", "value": pipeline_run_id, "short": True},
            {"title": "Timestamp", "value": timestamp, "short": True},
            {"title": "Total Checks", "value": str(total), "short": True},
            {"title": "Passed", "value": f"{passed}/{total}", "short": True},
            {"title": "Warnings", "value": str(warnings), "short": True},
            {"title": "Failed", "value": str(failed), "short": True},
        ]

        # Add check breakdown
        check_details = []
        for check_name, check_data in check_results.get("checks", {}).items():
            status = check_data.get("check_status", "unknown")
            status_icon = "✅" if status == "passed" else "⚠️" if status == "warning" else "❌"
            check_details.append(
                f"{status_icon} {check_data.get('check_type')}: {check_data.get('description')} "
                f"({check_data.get('resource_name')})"
            )

        if check_details:
            fields.append(
                {
                    "title": "Check Results",
                    "value": "\n".join(check_details),
                    "short": False,
                }
            )

        payload = {
            "attachments": [
                {
                    "fallback": f"US Economy Pipeline Daily Summary: {passed} passed, {failed} failed",
                    "color": color,
                    "title": f"{status_emoji} US Economy Pipeline Daily Summary",
                    "title_link": "https://app.supabase.com/",
                    "fields": fields,
                    "footer": "Quality Check System",
                    "ts": int(datetime.now().timestamp()),
                }
            ]
        }

        return self._send_slack_message(payload)


def alert_on_failure(check_results: Dict[str, Any]) -> bool:
    """
    Convenience function: send failure alert if needed.

    Args:
        check_results: Results dict from quality checks

    Returns:
        True if successful, False if failed

    """
    load_dotenv()
    alerter = SlackAlerter()
    return alerter.alert_on_failure(check_results)


def send_daily_summary(check_results: Dict[str, Any]) -> bool:
    """
    Convenience function: send daily digest.

    Args:
        check_results: Results dict from quality checks

    Returns:
        True if successful, False if failed

    """
    load_dotenv()
    alerter = SlackAlerter()
    return alerter.send_daily_summary(check_results)


def main() -> None:
    """Example: run alerting with sample check results."""
    load_dotenv()

    # Sample check results for testing
    sample_results = {
        "pipeline_run_id": "test-run-12345",
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "api_health": {
                "check_type": "api_health",
                "resource_name": "FRED_API",
                "check_status": "passed",
                "severity": "info",
                "description": "FRED API connectivity check",
            },
            "row_count": {
                "check_type": "row_count",
                "resource_name": "raw_tables",
                "check_status": "failed",
                "severity": "critical",
                "description": "Post-ingestion row count comparison",
            },
        },
        "summary": {
            "total_checks": 2,
            "passed": 1,
            "failed": 1,
            "warnings": 0,
        },
    }

    alerter = SlackAlerter()
    logger.info("Sending test failure alert...")
    alerter.alert_on_failure(sample_results)

    logger.info("Sending test daily summary...")
    alerter.send_daily_summary(sample_results)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    main()
