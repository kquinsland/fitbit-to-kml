#!/usr/bin/env python3
"""Merge multiple KML files into a single document."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import structlog

from fitbit_to_kml.merge_kml import MergeError, merge_kml_files

logger = structlog.get_logger()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge multiple KML files into one.")
    parser.add_argument(
        "--in-dir",
        required=True,
        type=Path,
        help="Directory containing .kml files (scanned recursively).",
    )
    parser.add_argument(
        "--out",
        dest="output",
        type=Path,
        help="Path to the merged KML file (defaults to MERGED.kml inside --in-dir).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing output file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform all parsing but do not write output; just report planned work.",
    )
    return parser.parse_args()


def format_relative(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def main() -> int:
    args = parse_args()

    input_dir = args.in_dir
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Input directory not found: {input_dir}", file=sys.stderr)
        return 1

    output = args.output or input_dir / "MERGED.kml"

    try:
        result = merge_kml_files(
            input_dir,
            output,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )
    except MergeError as exc:
        logger.error("Merge failed", error=str(exc))
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(
            f"[dry-run] Would merge {result.stats.files} files "
            f"({result.stats.placemarks} tracks, {result.stats.points} points) into {output}"
        )
        for path in result.merged_files:
            print(f"  - {format_relative(path, input_dir)}")
    else:
        print(
            f"Merged {result.stats.files} files into {output}\n"
            f"  Placemarks: {result.stats.placemarks}\n"
            f"  Points: {result.stats.points}"
        )

    if result.skipped_files:
        skipped_rel = ", ".join(
            format_relative(path, input_dir) for path in result.skipped_files
        )
        print(
            f"Skipped {len(result.skipped_files)} files without LineStrings: {skipped_rel}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
