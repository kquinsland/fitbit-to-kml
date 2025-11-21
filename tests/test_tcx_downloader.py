"""Tests for FitbitTCXDownloader and helper functions."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

from fitbit_to_kml.tcx import (
    FitbitTCXDownloader,
    TCXDownloadItem,
    _activity_has_distance,
    _activity_has_gps,
    _extract_tcx_id,
    _extract_tcx_link,
    _resolve_year_month,
    load_plan,
    save_plan,
    summarize_plan_progress,
)


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: bytes | Dict[str, Any],
        *,
        headers: Dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        if isinstance(payload, dict):
            self._json = payload
            self.content = json.dumps(payload).encode("utf-8")
            self.text = json.dumps(payload)
        else:
            self._json = {}
            self.content = payload
            self.text = payload.decode("utf-8")
        self.headers = headers or {}

    def json(self) -> Dict[str, Any]:
        return self._json


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


def _create_token_file(path: Path) -> None:
    payload = {
        "access_token": "token",
        "refresh_token": "refresh",
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _create_activity_fixture(tmp_path: Path) -> Path:
    activities_dir = tmp_path / "activities"
    (activities_dir / "2024").mkdir(parents=True)
    (activities_dir / "2024" / "11.json").write_text(
        json.dumps(
            [
                {
                    "tcx_link": "https://api.fitbit.com/1/user/-/activities/999.tcx",
                    "distance": 5,
                    "hasGps": True,
                },
                {
                    "tcx_link": "https://api.fitbit.com/1/user/-/activities/should_skip.tcx",
                    "distance": 0,
                    "hasGps": True,
                },
                {
                    "tcx_link": "https://api.fitbit.com/1/user/-/activities/should_skip_2.tcx",
                    "distance": 2,
                    "hasGps": False,
                },
            ]
        ),
        encoding="utf-8",
    )
    return activities_dir


def test_resolve_year_month():
    assert _resolve_year_month(Path("2024/11.json")) == ("2024", "11")
    with pytest.raises(ValueError):
        _resolve_year_month(Path("2024.json"))


def test_extract_tcx_id():
    link = "https://api.fitbit.com/1/user/-/activities/12345.tcx"
    assert _extract_tcx_id(link) == "12345"
    assert _extract_tcx_id("https://example.com/foo") is None


def test_extract_tcx_link_handles_variants():
    assert (
        _extract_tcx_link({"tcxLink": " http://example.com/one.tcx "})
        == "http://example.com/one.tcx"
    )
    assert (
        _extract_tcx_link({"tcx_link": "http://example.com/two.tcx"})
        == "http://example.com/two.tcx"
    )
    assert _extract_tcx_link({"tcx_link": ""}) is None


def test_activity_has_distance():
    assert _activity_has_distance({"distance": 1})
    assert not _activity_has_distance({"distance": 0})
    assert _activity_has_distance({"distance": "3.2"})
    assert not _activity_has_distance({"distance": None})


def test_activity_has_gps():
    assert _activity_has_gps({"hasGps": True})
    assert not _activity_has_gps({"hasGps": False})
    assert _activity_has_gps({"hasGps": "true"})
    assert not _activity_has_gps({"hasGps": "no"})


def test_collect_plan_filters_and_deduplicates(tmp_path):
    token_path = tmp_path / "tokens.json"
    _create_token_file(token_path)
    activities_dir = _create_activity_fixture(tmp_path)

    session = DummySession([FakeResponse(200, b"")])
    downloader = FitbitTCXDownloader(
        token_path,
        session=session,
        client_id="client",
        client_secret="secret",
    )

    plan = downloader.collect_plan(activities_dir)
    assert len(plan) == 1
    assert isinstance(plan[0], TCXDownloadItem)
    assert plan[0].url.endswith("999.tcx")


def test_summarize_plan_progress_counts_flags():
    plan = [
        TCXDownloadItem(
            url="https://example.com/one.tcx",
            path="one.tcx",
            downloaded=True,
        ),
        TCXDownloadItem(
            url="https://example.com/two.tcx",
            path="two.tcx",
            downloaded=False,
        ),
        TCXDownloadItem(
            url="https://example.com/three.tcx",
            path="three.tcx",
            downloaded=True,
        ),
    ]

    stats = summarize_plan_progress(plan)

    assert stats.total_items == 3
    assert stats.on_disk == 2
    assert stats.remaining == 1


def test_download_plan_writes_files_and_updates_checkpoint(tmp_path):
    token_path = tmp_path / "tokens.json"
    _create_token_file(token_path)
    activities_dir = _create_activity_fixture(tmp_path)

    plan_path = tmp_path / "plan.json"
    session = DummySession(
        [FakeResponse(200, b"<TrainingCenterDatabase></TrainingCenterDatabase>")]
    )
    downloader = FitbitTCXDownloader(
        token_path,
        session=session,
        client_id="client",
        client_secret="secret",
    )
    plan = downloader.collect_plan(activities_dir)
    save_plan(plan, plan_path)

    summary = downloader.download_plan(plan, plan_path=plan_path)

    target = activities_dir / "2024" / "11_999.tcx"
    assert summary.downloaded == 1
    assert target.exists()
    updated = load_plan(plan_path)
    assert updated[0].downloaded is True
    assert session.calls[0][1].endswith("/999.tcx")


def test_rate_limit_retry(tmp_path):
    token_path = tmp_path / "tokens.json"
    _create_token_file(token_path)

    activities_dir = tmp_path / "activities"
    (activities_dir / "2024").mkdir(parents=True)
    (activities_dir / "2024" / "11.json").write_text(
        json.dumps(
            [
                {
                    "tcx_link": "https://api.fitbit.com/1/user/-/activities/999.tcx",
                    "distance": 1,
                    "hasGps": True,
                }
            ]
        ),
        encoding="utf-8",
    )

    responses = [
        FakeResponse(
            429,
            {"error": {"code": 429, "message": "Resource has been exhausted."}},
            headers={"Retry-After": "0.01"},
        ),
        FakeResponse(200, b"<TrainingCenterDatabase></TrainingCenterDatabase>"),
    ]
    session = DummySession(responses)
    waits: List[float] = []

    def fake_sleep(duration: float) -> None:
        waits.append(duration)

    downloader = FitbitTCXDownloader(
        token_path,
        session=session,
        client_id="client",
        client_secret="secret",
        sleep_func=fake_sleep,
    )

    plan = downloader.collect_plan(activities_dir)
    save_plan(plan, tmp_path / "plan.json")

    summary = downloader.download_plan(plan, plan_path=tmp_path / "plan.json")

    assert summary.downloaded == 1
    assert waits and waits[0] >= 0.01
    assert len(session.calls) == 2


def test_rate_limit_uses_fitbit_reset_header(tmp_path):
    token_path = tmp_path / "tokens.json"
    _create_token_file(token_path)

    activities_dir = tmp_path / "activities"
    (activities_dir / "2024").mkdir(parents=True)
    (activities_dir / "2024" / "11.json").write_text(
        json.dumps(
            [
                {
                    "tcx_link": "https://api.fitbit.com/1/user/-/activities/999.tcx",
                    "distance": 1,
                    "hasGps": True,
                }
            ]
        ),
        encoding="utf-8",
    )

    responses = [
        FakeResponse(
            429,
            {"error": {"code": 429, "message": "Resource has been exhausted."}},
            headers={"Fitbit-Rate-Limit-Reset": "0.5"},
        ),
        FakeResponse(200, b"<TrainingCenterDatabase></TrainingCenterDatabase>"),
    ]
    session = DummySession(responses)
    waits: List[float] = []

    def fake_sleep(duration: float) -> None:
        waits.append(duration)

    downloader = FitbitTCXDownloader(
        token_path,
        session=session,
        client_id="client",
        client_secret="secret",
        sleep_func=fake_sleep,
    )

    plan = downloader.collect_plan(activities_dir)
    save_plan(plan, tmp_path / "plan.json")

    summary = downloader.download_plan(plan, plan_path=tmp_path / "plan.json")

    assert summary.downloaded == 1
    assert waits and waits[0] >= 0.5
    assert len(session.calls) == 2


def test_dry_run_lists_urls(tmp_path):
    token_path = tmp_path / "tokens.json"
    _create_token_file(token_path)

    activities_dir = tmp_path / "activities"
    (activities_dir / "2024").mkdir(parents=True)
    (activities_dir / "2024" / "11.json").write_text(
        json.dumps(
            [
                {
                    "tcx_link": "https://api.fitbit.com/1/user/-/activities/123.tcx",
                    "distance": 1,
                    "hasGps": True,
                }
            ]
        ),
        encoding="utf-8",
    )

    session = DummySession([])
    captured: List[str] = []

    downloader = FitbitTCXDownloader(
        token_path,
        session=session,
        client_id="client",
        client_secret="secret",
    )

    plan = downloader.collect_plan(activities_dir)

    summary = downloader.download_plan(plan, dry_run=True, printer=captured.append)

    assert summary.dry_run_listed == 1
    assert summary.downloaded == 0
    assert not session.calls
    assert captured == []


def test_resume_skips_already_downloaded(tmp_path):
    token_path = tmp_path / "tokens.json"
    _create_token_file(token_path)
    activities_dir = _create_activity_fixture(tmp_path)

    downloaded_file = activities_dir / "2024" / "11_999.tcx"
    downloaded_file.parent.mkdir(parents=True, exist_ok=True)
    downloaded_file.write_text("<tcx/>", encoding="utf-8")

    session = DummySession([])
    downloader = FitbitTCXDownloader(
        token_path,
        session=session,
        client_id="client",
        client_secret="secret",
    )

    plan = downloader.collect_plan(activities_dir)
    assert plan[0].downloaded is True

    summary = downloader.download_plan(plan, plan_path=tmp_path / "plan.json")

    assert summary.already_downloaded == 1
    assert summary.downloaded == 0
    assert not session.calls
