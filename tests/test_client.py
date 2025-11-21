"""Tests for Fitbit API client helpers."""

from __future__ import annotations

from fitbit_to_kml.client import _human_readable_duration


def test_human_readable_duration_handles_minutes_and_seconds():
    assert _human_readable_duration(1894) == "00:31:34"


def test_human_readable_duration_rounds_up_and_clamps():
    assert _human_readable_duration(0.1) == "00:00:01"
    assert _human_readable_duration(-5) == "00:00:00"
