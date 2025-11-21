"""Shared Fitbit API client utilities."""

from __future__ import annotations

import math
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import requests
import structlog

from .tokens import TokenData, load_token_file, write_token_file

logger = structlog.get_logger(__name__)

TOKEN_ENDPOINT = "https://api.fitbit.com/oauth2/token"


class FitbitAPIError(RuntimeError):
    """Raised when Fitbit API interactions fail."""


class FitbitAPIClient:
    """Base class that manages OAuth tokens and authorized requests."""

    def __init__(
        self,
        token_file: str | Path,
        *,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        session: Optional[requests.Session] = None,
        max_rate_limit_retries: int = 5,
        sleep_func: Optional[Callable[[float], None]] = None,
    ) -> None:
        self.token_path = Path(token_file)
        self.session = session or requests.Session()
        self.client_id = client_id or os.environ.get("FB_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("FB_CLIENT_SECRET")
        self._token: TokenData = load_token_file(self.token_path)
        self.max_rate_limit_retries = max_rate_limit_retries
        self._sleep = sleep_func or time.sleep

    def request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        retry_on_unauthorized: bool = True,
        **kwargs: Any,
    ) -> requests.Response:
        """Perform an authorized HTTP request, refreshing tokens when needed."""
        rate_limit_attempts = 0
        retry_auth = retry_on_unauthorized

        while True:
            self._ensure_fresh_token()
            merged_headers = {"Accept": "application/json"}
            if headers:
                merged_headers.update(headers)
            merged_headers["Authorization"] = f"Bearer {self._token.access_token}"

            response = self.session.request(
                method,
                url,
                params=params,
                data=data,
                headers=merged_headers,
                **kwargs,
            )

            if response.status_code == 401 and retry_auth:
                logger.info("token_expired_retrying")
                self.refresh_access_token(force=True)
                retry_auth = False
                continue

            if (
                response.status_code == 429
                and rate_limit_attempts < self.max_rate_limit_retries
            ):
                delay = self._rate_limit_delay(response, rate_limit_attempts)
                rate_limit_attempts += 1
                logger.warning(
                    "fitbit_rate_limited",
                    wait_seconds=delay,
                    wait_hhmm=_human_readable_duration(delay),
                    attempt=rate_limit_attempts,
                    url=url,
                )
                self._sleep(delay)
                continue

            if response.status_code >= 400:
                raise FitbitAPIError(
                    f"Fitbit API call failed with {response.status_code}: {response.text}"
                )

            return response

    def _ensure_fresh_token(self) -> None:
        if self._token.will_expire_within():
            logger.info("token_expiring_refreshing")
            self.refresh_access_token()

    def refresh_access_token(self, *, force: bool = False) -> None:
        """Refresh the OAuth token and persist the response."""
        if not self._token.refresh_token:
            if force:
                raise FitbitAPIError("Refresh token is missing.")
            return

        if not self.client_id or not self.client_secret:
            raise FitbitAPIError(
                "Refreshing tokens requires FB_CLIENT_ID and FB_CLIENT_SECRET."
            )

        response = self.session.post(
            TOKEN_ENDPOINT,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self._token.refresh_token,
            },
            auth=(self.client_id, self.client_secret),
        )

        if response.status_code >= 400:
            raise FitbitAPIError(
                f"Failed to refresh token ({response.status_code}): {response.text}"
            )

        payload = response.json()
        expires_in = payload.get("expires_in")
        if expires_in:
            expiration = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
            payload["expires_at"] = expiration.isoformat()
        elif "expires_at" not in payload:
            payload["expires_at"] = datetime.now(timezone.utc).isoformat()

        self._token = TokenData.from_dict(payload)
        write_token_file(self._token, self.token_path)
        logger.info("token_refreshed", path=str(self.token_path))

    def _rate_limit_delay(self, response: requests.Response, attempt: int) -> float:
        """Compute the delay before retrying after a 429 response."""
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(1.0, float(retry_after))
            except ValueError:
                pass
        reset_header = response.headers.get("Fitbit-Rate-Limit-Reset")
        if reset_header:
            try:
                return max(1.0, float(reset_header))
            except ValueError:
                pass
        # Exponential backoff with jitter-friendly base capped at 60 seconds
        return min(60.0, max(1.0, 2.0**attempt))


def _human_readable_duration(seconds: float) -> str:
    """Return a zero-padded HH:MM:SS string for the provided seconds value."""
    total_seconds = max(0, int(math.ceil(seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
