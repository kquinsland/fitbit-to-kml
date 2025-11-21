"""Tests for the dump utility helpers."""

from __future__ import annotations

from pathlib import Path

from fitbit_to_kml.dump_utils import (
    bucket_activities_by_month,
    determine_activity_month,
    write_month_buckets,
)


def test_determine_activity_month_prefers_original_start():
    activity = {
        "originalStartTime": "2024-01-15T10:00:00+00:00",
        "startTime": "2024-01-15T06:00:00-04:00",
    }
    assert determine_activity_month(activity) == (2024, 1)


def test_bucket_activities_groups_and_skips():
    activities = [
        {"startTime": "2024-02-01T12:00:00Z", "logId": 1},
        {"startDate": "2024-02-10"},
        {"logId": 3},  # skipped
    ]
    buckets, skipped = bucket_activities_by_month(activities)

    assert skipped == 1
    assert (2024, 2) in buckets
    assert len(buckets[(2024, 2)]) == 2


def test_write_month_buckets(tmp_path):
    buckets = {(2024, 3): [{"logId": 1}]}
    written = write_month_buckets(buckets, tmp_path / "data")

    target = Path(written[(2024, 3)])
    assert target.exists()
    assert target.read_text(encoding="utf-8").strip().startswith("[")
