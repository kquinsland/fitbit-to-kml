#!/usr/bin/env python3
"""Download TCX exports for activities stored in monthly JSON files."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import structlog

from fitbit_to_kml.client import FitbitAPIError
from fitbit_to_kml.tcx import (
    FitbitTCXDownloader,
    load_plan,
    save_plan,
    summarize_plan_progress,
)

logger = structlog.get_logger(__name__)


def _default_token_file() -> str:
    return (
        os.environ.get("FB_TOKENS_FILE")
        or os.environ.get("FB_CLIENT_SECRET_FILE")
        or "tokens.json"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download TCX exports for Fitbit activities with tcx_link fields."
    )
    parser.add_argument(
        "--token-file",
        default=_default_token_file(),
        help="Path to the OAuth tokens file (default: %(default)s).",
    )
    parser.add_argument(
        "--activities-dir",
        default="data/fitbit_activities",
        help="Directory containing YYYY/MM.json activity dumps.",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=None,
        help=(
            "Directory where TCX files are stored (default: same as --activities-dir)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List eligible TCX URLs without downloading them.",
    )
    parser.add_argument(
        "--plan-file",
        default="data/tcx-files.json",
        help="Path where the download plan is stored (default: %(default)s).",
    )
    parser.add_argument(
        "--resume-from",
        help="Resume downloads using an existing plan file instead of scanning activity JSON.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    token_file = Path(args.token_file)
    downloader = FitbitTCXDownloader(token_file)

    if args.resume_from:
        plan_path = Path(args.resume_from)
        if not plan_path.exists():
            logger.error("plan_file_missing", path=str(plan_path))
            sys.exit(1)
    else:
        plan_path = Path(args.plan_file)

    plan = None
    plan_loaded_from_disk = False
    if plan_path.exists():
        plan = load_plan(plan_path)
        plan_loaded_from_disk = True
        logger.info(
            "tcx_plan_loaded",
            path=str(plan_path),
            entries=len(plan),
        )
        if plan:
            stats = summarize_plan_progress(plan)
            logger.info(
                "tcx_resume_progress",
                total=stats.total_items,
                on_disk=stats.on_disk,
                remaining=stats.remaining,
            )
        else:
            logger.info("tcx_plan_empty", path=str(plan_path))

    if not plan_loaded_from_disk:
        activities_dir = Path(args.activities_dir)
        if not activities_dir.exists():
            logger.error("activities_dir_missing", path=str(activities_dir))
            sys.exit(1)
        output_dir = Path(args.output_dir) if args.output_dir else activities_dir
        plan = downloader.collect_plan(activities_dir, output_dir)
        save_plan(plan, plan_path)
        logger.info(
            "tcx_plan_created",
            path=str(plan_path),
            entries=len(plan),
        )

    if args.dry_run:
        summary = downloader.download_plan(plan, dry_run=True)
        logger.info(
            "tcx_plan_ready",
            path=str(plan_path),
            total=summary.total_items,
            pending=summary.dry_run_listed,
            already_downloaded=summary.already_downloaded,
        )
        return

    try:
        summary = downloader.download_plan(plan, plan_path=plan_path)
    except FitbitAPIError as exc:
        logger.error("fitbit_api_error", error=str(exc))
        sys.exit(1)

    logger.info(
        "tcx_download_summary",
        total=summary.total_items,
        downloaded=summary.downloaded,
        already_downloaded=summary.already_downloaded,
        failed=summary.failed,
        plan=str(plan_path),
    )


if __name__ == "__main__":
    main()
