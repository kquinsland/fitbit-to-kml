"""Helpers for writing Fitbit activity dumps to disk."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Tuple

import structlog

logger = structlog.get_logger(__name__)

TimeKey = Tuple[int, int]

_TIME_FIELDS = [
    "originalStartTime",
    "startDateTime",
    "startTime",
    "startDate",
    "startDateLocal",
]


def determine_activity_month(activity: Mapping[str, Any]) -> TimeKey:
    """Return the (year, month) tuple extracted from an activity payload."""
    dt = _extract_activity_datetime(activity)
    return dt.year, dt.month


def _extract_activity_datetime(activity: Mapping[str, Any]) -> datetime:
    for field in _TIME_FIELDS:
        value = activity.get(field)
        if value is None:
            continue
        dt = _coerce_datetime(value)
        if dt:
            return dt
    raise ValueError("Activity did not contain a recognizable start time")


def _coerce_datetime(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)

    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        normalized = normalized.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            try:
                return datetime.strptime(normalized, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                return None
    return None


def bucket_activities_by_month(
    activities: Iterable[Mapping[str, Any]],
) -> Tuple[MutableMapping[TimeKey, List[Mapping[str, Any]]], int]:
    """Group activities into month buckets, returning (buckets, skipped_count)."""
    buckets: MutableMapping[TimeKey, List[Mapping[str, Any]]] = defaultdict(list)
    skipped = 0
    for activity in activities:
        try:
            year, month = determine_activity_month(activity)
        except ValueError:
            skipped += 1
            logger.warning(
                "activity_missing_start_time",
                activity_id=activity.get("logId"),
            )
            continue
        buckets[(year, month)].append(activity)
    return buckets, skipped


def write_month_buckets(
    buckets: Mapping[TimeKey, List[Mapping[str, Any]]],
    output_root: str | Path,
) -> Mapping[TimeKey, Path]:
    """Persist activity buckets to YYYY/MM.json files."""
    output_dir = Path(output_root).expanduser()
    written: Dict[TimeKey, Path] = {}
    for (year, month), activities in sorted(buckets.items()):
        month_dir = output_dir / f"{year:04d}"
        month_dir.mkdir(parents=True, exist_ok=True)
        file_path = month_dir / f"{month:02d}.json"
        with file_path.open("w", encoding="utf-8") as handle:
            json.dump(activities, handle, indent=2)
            handle.write("\n")
        written[(year, month)] = file_path
    return written
