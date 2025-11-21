"""Utilities to query Fitbit activities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional
from urllib.parse import urljoin

import structlog

from . import FITBIT_API_BASE
from .client import FitbitAPIClient

logger = structlog.get_logger(__name__)

if TYPE_CHECKING:
    import requests

ACTIVITY_LIST_PATH = "/1/user/-/activities/list.json"


@dataclass
class ActivityDumpResult:
    """Record for the results of an activity dump request."""

    activities: List[Dict[str, Any]]
    total_requests: int


class FitbitActivityFetcher(FitbitAPIClient):
    """High level helper that queries the Fitbit API for activities."""

    def __init__(
        self,
        token_file: str | Path,
        *,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        session: Optional["requests.Session"] = None,
    ) -> None:
        super().__init__(
            token_file,
            client_id=client_id,
            client_secret=client_secret,
            session=session,
        )
        self._last_request_count = 0

    def fetch_all(
        self,
        *,
        after_date: str = "2008-01-01",
        page_size: int = 100,
        sort: str = "desc",
    ) -> ActivityDumpResult:
        """Fetch every activity for the user and return the payload."""
        activities = list(
            self.iter_activities(
                after_date=after_date,
                page_size=page_size,
                sort=sort,
            )
        )
        return ActivityDumpResult(
            activities=activities,
            total_requests=self._last_request_count,
        )

    def iter_activities(
        self,
        *,
        after_date: str = "2008-01-01",
        page_size: int = 100,
        sort: str = "desc",
    ) -> Iterator[Dict[str, Any]]:
        """Yield activities from the Fitbit API page by page."""
        if page_size < 1 or page_size > 100:
            raise ValueError("page_size must be between 1 and 100")

        page_url = urljoin(FITBIT_API_BASE, ACTIVITY_LIST_PATH)
        params: Dict[str, Any] | None = {
            "afterDate": after_date,
            "sort": sort,
            "limit": page_size,
            "offset": 0,
        }
        self._last_request_count = 0

        while True:
            response = self.request("GET", page_url, params=params)
            self._last_request_count += 1
            body = response.json()
            batch = body.get("activities", [])
            for activity in batch:
                yield activity
            logger.info(
                "fetched_activities_page",
                page=self._last_request_count,
                fetched=len(batch),
            )

            pagination = body.get("pagination") or {}
            next_url = pagination.get("next")
            if not next_url:
                break
            page_url = urljoin(FITBIT_API_BASE, next_url)
            params = None

    @property
    def last_request_count(self) -> int:
        """Return the number of API requests performed by the last fetch."""
        return self._last_request_count
