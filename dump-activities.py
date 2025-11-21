#!/usr/bin/env python3
"""Dump every Fitbit activity to a JSON file using an existing token."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import structlog

from fitbit_to_kml.activity import FitbitActivityFetcher, FitbitAPIError
from fitbit_to_kml.dump_utils import (
    bucket_activities_by_month,
    write_month_buckets,
)

logger = structlog.get_logger(__name__)


def _default_token_file() -> str:
    """Determine the default token file path."""
    return (
        os.environ.get("FB_TOKENS_FILE")
        or os.environ.get("FB_CLIENT_SECRET_FILE")
        or "tokens.json"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dump all Fitbit activities to a local JSON file."
    )
    parser.add_argument(
        "--token-file",
        default=_default_token_file(),
        help="Path to the OAuth tokens file (default: %(default)s).",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="data/fitbit_activities",
        help="Directory where YYYY/MM.json files are written (default: %(default)s).",
    )
    parser.add_argument(
        "--after-date",
        default="2008-01-01",
        help="Fetch activities recorded on or after this YYYY-MM-DD date.",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=100,
        help="Number of activities to fetch per request (1-100).",
    )
    parser.add_argument(
        "--sort",
        choices=("asc", "desc"),
        default="desc",
        help="Sort order passed to the Fitbit API (default: %(default)s).",
    )
    return parser.parse_args()


def dump_activities() -> None:
    args = parse_args()
    token_file = Path(args.token_file)

    logger.info("loading_tokens", path=str(token_file))
    fetcher = FitbitActivityFetcher(token_file)

    try:
        activities_iter = fetcher.iter_activities(
            after_date=args.after_date,
            page_size=args.page_size,
            sort=args.sort,
        )
        buckets, skipped = bucket_activities_by_month(activities_iter)
    except FitbitAPIError as exc:
        logger.error("fitbit_api_error", error=str(exc))
        sys.exit(1)

    written = write_month_buckets(buckets, args.output_dir)
    total = sum(len(values) for values in buckets.values())
    logger.info(
        "dump_complete",
        total=total,
        requests=fetcher.last_request_count,
        months=len(written),
        skipped=skipped,
        output=str(Path(args.output_dir).expanduser()),
    )


if __name__ == "__main__":
    dump_activities()
