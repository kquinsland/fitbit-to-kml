"""Download Fitbit TCX exports for activities."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Mapping, Optional, Tuple
from urllib.parse import urlparse

import structlog

from .client import FitbitAPIClient, FitbitAPIError

logger = structlog.get_logger(__name__)

TimeKey = Tuple[str, str]


@dataclass
class TCXDownloadItem:
    """Represents an individual TCX download task."""

    url: str
    path: str
    downloaded: bool = False

    def to_dict(self) -> Mapping[str, object]:
        return {"url": self.url, "path": self.path, "downloaded": self.downloaded}

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "TCXDownloadItem":
        return cls(
            url=str(data["url"]),
            path=str(data["path"]),
            downloaded=bool(data.get("downloaded", False)),
        )


@dataclass
class TCXDownloadSummary:
    """Metrics about the TCX download process."""

    total_items: int = 0
    downloaded: int = 0
    already_downloaded: int = 0
    failed: int = 0
    dry_run_listed: int = 0


@dataclass(frozen=True)
class TCXPlanStats:
    """Simple stats describing the current plan progress."""

    total_items: int
    on_disk: int

    @property
    def remaining(self) -> int:
        return self.total_items - self.on_disk


class FitbitTCXDownloader(FitbitAPIClient):
    """Download TCX files referenced inside activity dumps."""

    def collect_plan(
        self,
        activities_dir: str | Path,
        output_dir: Optional[str | Path] = None,
    ) -> List[TCXDownloadItem]:
        activities_path = Path(activities_dir)
        output_path = Path(output_dir) if output_dir else activities_path
        items: List[TCXDownloadItem] = []
        seen_urls: set[str] = set()

        for json_file in sorted(activities_path.rglob("*.json")):
            rel_path = json_file.relative_to(activities_path)
            try:
                year, month = _resolve_year_month(rel_path)
            except ValueError:
                logger.warning("invalid_activity_file_path", path=str(rel_path))
                continue

            try:
                data = _load_json_array(json_file)
            except ValueError as exc:
                logger.warning(
                    "invalid_activity_file",
                    path=str(rel_path),
                    error=str(exc),
                )
                continue

            for activity in data:
                if not _activity_has_distance(activity):
                    continue
                if not _activity_has_gps(activity):
                    continue

                link = _extract_tcx_link(activity)
                if not link or link in seen_urls:
                    continue

                tcx_id = _extract_tcx_id(link)
                if not tcx_id:
                    logger.warning("tcx_link_unrecognized", link=link)
                    continue

                output_file = output_path / year / f"{month}_{tcx_id}.tcx"
                items.append(
                    TCXDownloadItem(
                        url=link,
                        path=str(output_file),
                        downloaded=output_file.exists(),
                    )
                )
                seen_urls.add(link)

        return items

    def download_plan(
        self,
        plan: Iterable[TCXDownloadItem],
        *,
        plan_path: Optional[str | Path] = None,
        dry_run: bool = False,
        printer: Optional[Callable[[str], None]] = None,
    ) -> TCXDownloadSummary:
        items = list(plan)
        summary = TCXDownloadSummary(total_items=len(items))
        plan_path_obj = Path(plan_path).expanduser() if plan_path else None

        if dry_run:
            summary.dry_run_listed = sum(1 for item in items if not item.downloaded)
            summary.already_downloaded = sum(1 for item in items if item.downloaded)
            return summary

        for item in items:
            if item.downloaded:
                summary.already_downloaded += 1
                continue

            path_obj = Path(item.path)
            path_obj.parent.mkdir(parents=True, exist_ok=True)

            try:
                content = self.download_tcx(item.url)
            except FitbitAPIError as exc:
                summary.failed += 1
                logger.error("tcx_download_failed", link=item.url, error=str(exc))
                continue

            path_obj.write_bytes(content)
            item.downloaded = True
            summary.downloaded += 1
            logger.info("tcx_downloaded", link=item.url, target=str(path_obj))

            if plan_path_obj:
                save_plan(items, plan_path_obj)

        return summary

    def download_tcx(self, link: str) -> bytes:
        """Download the TCX payload for a single activity."""
        response = self.request(
            "GET",
            link,
            headers={
                "Accept": "application/vnd.garmin.tcx+xml,application/xml;q=0.9,*/*;q=0.8"
            },
        )
        return response.content


def save_plan(plan: Iterable[TCXDownloadItem], path: str | Path) -> None:
    plan_path = Path(path).expanduser()
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    with plan_path.open("w", encoding="utf-8") as handle:
        json.dump([item.to_dict() for item in plan], handle, indent=2)
        handle.write("\n")


def load_plan(path: str | Path) -> List[TCXDownloadItem]:
    plan_path = Path(path).expanduser()
    with plan_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, list):
        raise ValueError("Plan file must be a JSON array.")
    return [TCXDownloadItem.from_dict(entry) for entry in raw]


def summarize_plan_progress(plan: Iterable[TCXDownloadItem]) -> TCXPlanStats:
    """Count plan entries along with those already marked downloaded."""
    items = list(plan)
    on_disk = sum(1 for item in items if item.downloaded)
    return TCXPlanStats(total_items=len(items), on_disk=on_disk)


def _resolve_year_month(relative_path: Path) -> TimeKey:
    if len(relative_path.parts) < 2:
        raise ValueError("Path does not include year/month components.")
    year = relative_path.parts[0]
    month = Path(relative_path).stem
    if not year.isdigit() or len(month) == 0:
        raise ValueError("Year or month component missing.")
    return year, month


def _load_json_array(path: Path) -> List[Mapping[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        activities = payload.get("activities")
        if isinstance(activities, list):
            return activities
    raise ValueError(f"Unexpected JSON format in {path}")


def _extract_tcx_link(activity: Mapping[str, object]) -> Optional[str]:
    link = activity.get("tcx_link") or activity.get("tcxLink")
    if isinstance(link, str):
        normalized = link.strip()
        if normalized:
            return normalized
    return None


def _extract_tcx_id(link: str) -> Optional[str]:
    parsed = urlparse(link)
    name = Path(parsed.path).name
    if not name.lower().endswith(".tcx"):
        return None
    return name[:-4]  # strip .tcx


def _activity_has_distance(activity: Mapping[str, object]) -> bool:
    """Return True if the activity contains a non-zero distance."""
    value = activity.get("distance")
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return float(value) > 0
    if isinstance(value, str):
        try:
            return float(value.strip()) > 0
        except ValueError:
            return False
    return False


def _activity_has_gps(activity: Mapping[str, object]) -> bool:
    """Return True if the activity reports GPS data."""
    has_gps = activity.get("hasGps")
    if isinstance(has_gps, bool):
        return has_gps
    if isinstance(has_gps, str):
        lowered = has_gps.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return False
