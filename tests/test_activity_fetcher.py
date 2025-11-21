"""Tests for the Fitbit activity fetcher."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from fitbit_to_kml.activity import FitbitActivityFetcher


class FakeResponse:
    def __init__(self, status_code: int, payload: Dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self) -> Dict[str, Any]:
        return self._payload


class DummySession:
    def __init__(self, responses: List[FakeResponse]) -> None:
        self._responses = responses
        self.calls: List[Tuple[str, str]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append((method, url))
        if not self._responses:
            raise AssertionError("No more responses queued.")
        return self._responses.pop(0)

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        return self.request("POST", url, **kwargs)


def create_token_file(path: Path) -> None:
    payload = {
        "access_token": "token",
        "refresh_token": "refresh",
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_fetch_all_paginates(tmp_path):
    token_path = tmp_path / "tokens.json"
    create_token_file(token_path)

    responses = [
        FakeResponse(
            200,
            {
                "activities": [{"activityId": 1}, {"activityId": 2}],
                "pagination": {
                    "next": "/1/user/-/activities/list.json?afterDate=2024-01-01&sort=desc&offset=2&limit=2"
                },
            },
        ),
        FakeResponse(
            200,
            {
                "activities": [{"activityId": 3}],
                "pagination": {"next": None},
            },
        ),
    ]
    session = DummySession(responses)
    fetcher = FitbitActivityFetcher(token_path, session=session)

    result = fetcher.fetch_all(after_date="2024-01-01", page_size=2)

    assert [a["activityId"] for a in result.activities] == [1, 2, 3]
    assert len(session.calls) == 2
    assert result.total_requests == fetcher.last_request_count == 2


def test_iter_activities_streams(tmp_path):
    token_path = tmp_path / "tokens.json"
    create_token_file(token_path)
    responses = [
        FakeResponse(
            200,
            {
                "activities": [{"activityId": 1}],
                "pagination": {"next": None},
            },
        )
    ]
    session = DummySession(responses)
    fetcher = FitbitActivityFetcher(token_path, session=session)

    activities = list(fetcher.iter_activities())

    assert [a["activityId"] for a in activities] == [1]
    assert fetcher.last_request_count == 1


def test_refresh_updates_token_file(tmp_path):
    token_path = tmp_path / "tokens.json"
    payload = {
        "access_token": "token",
        "refresh_token": "refresh",
        "expires_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
    }
    token_path.write_text(json.dumps(payload), encoding="utf-8")

    refreshed_payload = {
        "access_token": "new-token",
        "refresh_token": "new-refresh",
        "expires_in": 3600,
        "token_type": "Bearer",
        "scope": "activity",
    }

    responses = [
        FakeResponse(200, refreshed_payload),
    ]
    session = DummySession(responses)
    fetcher = FitbitActivityFetcher(
        token_path,
        session=session,
        client_id="client",
        client_secret="secret",
    )

    fetcher.refresh_access_token()

    saved = json.loads(token_path.read_text(encoding="utf-8"))
    assert saved["access_token"] == "new-token"
    assert saved["refresh_token"] == "new-refresh"
