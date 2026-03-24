"""
FRED API client for fetching US economic data.

Handles API communication, rate limiting, retries, and data parsing.
"""

import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import (
    FRED_BASE_URL,
    FRED_API_KEY,
    FRED_RATE_LIMIT_DELAY,
    RETRY_ATTEMPTS,
    RETRY_BACKOFF_FACTOR,
)

logger = logging.getLogger(__name__)


class FREDAPIError(Exception):
    """Custom exception for FRED API errors."""

    pass


class FREDClient:
    """
    Client for fetching data from the FRED (Federal Reserve Economic Data) API.

    Handles rate limiting, retries, and data parsing with proper error handling.
    """

    def __init__(self, api_key: str):
        """
        Initialize the FRED API client.

        Args:
            api_key: FRED API key for authentication

        Raises:
            ValueError: If api_key is not provided
        """
        if not api_key:
            raise ValueError("FRED_API_KEY environment variable is required")

        self.api_key = api_key
        self.base_url = FRED_BASE_URL
        self.last_request_time = 0.0

        # Set up session with retry logic
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            max_retries=requests.adapters.Retry(
                total=RETRY_ATTEMPTS,
                backoff_factor=RETRY_BACKOFF_FACTOR,
                status_forcelist=[429, 500, 502, 503, 504],
            )
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _apply_rate_limit(self) -> None:
        """Apply rate limiting to respect FRED's 120 requests/minute limit."""
        elapsed = time.time() - self.last_request_time
        if elapsed < FRED_RATE_LIMIT_DELAY:
            sleep_time = FRED_RATE_LIMIT_DELAY - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    @retry(stop=stop_after_attempt(RETRY_ATTEMPTS), wait=wait_exponential(multiplier=1, min=1, max=10))
    def _fetch_with_retry(self, url: str, params: Dict[str, Any]) -> requests.Response:
        """
        Fetch data from FRED API with exponential backoff retry logic.

        Args:
            url: API endpoint URL
            params: Query parameters

        Returns:
            Response object

        Raises:
            FREDAPIError: If request fails after retries
        """
        self._apply_rate_limit()

        try:
            logger.debug(f"Fetching from {url} with params: {params}")
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"FRED API request failed: {str(e)}")
            raise FREDAPIError(f"Failed to fetch data from FRED API: {str(e)}") from e

    def get_series_observations(
        self,
        series_id: str,
        start_date: str,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch observations for a FRED series within a date range.

        Args:
            series_id: FRED series identifier (e.g., "GDPC1")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format. Defaults to today.

        Returns:
            List of observation dictionaries with 'date' and 'value' keys

        Raises:
            FREDAPIError: If API request fails or response is invalid
        """
        if not series_id:
            raise ValueError("series_id is required")
        if not start_date:
            raise ValueError("start_date is required")

        # Default end_date to today
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        params = {
            "api_key": self.api_key,
            "series_id": series_id,
            "observation_start": start_date,
            "observation_end": end_date,
            "file_type": "json",
        }

        try:
            response = self._fetch_with_retry(self.base_url, params)
            data = response.json()

            if "observations" not in data:
                logger.warning(f"No observations found for series {series_id}")
                return []

            observations = []
            for obs in data["observations"]:
                try:
                    # FRED uses "." to represent missing data
                    value = obs.get("value")
                    if value == "." or value is None:
                        parsed_value = None
                    else:
                        parsed_value = float(value)

                    # Parse date string to datetime
                    obs_date = datetime.strptime(obs["date"], "%Y-%m-%d").date()

                    observations.append(
                        {
                            "date": obs_date,
                            "value": parsed_value,
                        }
                    )
                except (ValueError, KeyError) as e:
                    logger.warning(f"Failed to parse observation for {series_id}: {obs}. Error: {str(e)}")
                    continue

            logger.info(f"Successfully fetched {len(observations)} observations for {series_id}")
            return observations

        except FREDAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching series {series_id}: {str(e)}")
            raise FREDAPIError(f"Unexpected error: {str(e)}") from e
