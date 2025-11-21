#!/usr/bin/env python3
"""Convert TCX files to KML format.

This tool converts GPS workout data from TCX (Training Center XML) format
to KML (Keyhole Markup Language) format for visualization in mapping applications.
"""

import argparse
import sys
from pathlib import Path
from typing import NamedTuple

import simplekml
import structlog
import tcxparser

logger = structlog.get_logger()


class ConversionStats(NamedTuple):
    """Statistics for a TCX to KML conversion."""

    total_files: int
    successful: int
    failed: int
    total_points: int
    total_laps: int


class ConversionResult(NamedTuple):
    """Result of a single file conversion."""

    success: bool
    points: int
    laps: int
    error: str | None = None


def convert_tcx_to_kml(
    tcx_path: Path, kml_path: Path, overwrite: bool = False
) -> ConversionResult:
    """Convert a single TCX file to KML format.

    Args:
        tcx_path: Path to the input TCX file
        kml_path: Path to the output KML file
        overwrite: Whether to overwrite existing output files

    Returns:
        ConversionResult with conversion details

    """
    # Check if output file exists and overwrite is not enabled
    if kml_path.exists() and not overwrite:
        logger.warning(
            "Output file already exists, skipping",
            output_file=str(kml_path),
        )
        return ConversionResult(
            success=False,
            points=0,
            laps=0,
            error="Output file already exists (use --overwrite-destination to force)",
        )

    try:
        # Parse the TCX file
        tcx = tcxparser.TCXParser(str(tcx_path))

        # Get position values (GPS coordinates)
        points = tcx.position_values()

        if not points:
            logger.warning(
                "No GPS points found in TCX file",
                input_file=str(tcx_path),
            )
            return ConversionResult(
                success=False,
                points=0,
                laps=0,
                error="No GPS points found in TCX file",
            )

        # Get lap count
        laps = tcx.activity.Laps if hasattr(tcx.activity, "Laps") else []
        lap_count = len(laps) if laps else 0

        # Create KML file
        kml = simplekml.Kml()

        # Create a line string from the GPS points
        # Note: simplekml expects (longitude, latitude) order
        line_coords = [(lon, lat) for lat, lon in points]

        # Add the track as a LineString
        linestring = kml.newlinestring(name=tcx_path.stem)
        linestring.coords = line_coords
        linestring.style.linestyle.color = simplekml.Color.red
        linestring.style.linestyle.width = 3

        # Save the KML file
        kml.save(str(kml_path))

        logger.info(
            "Successfully converted TCX to KML",
            input_file=str(tcx_path),
            output_file=str(kml_path),
            points=len(points),
            laps=lap_count,
        )

        return ConversionResult(
            success=True,
            points=len(points),
            laps=lap_count,
        )

    except FileNotFoundError:
        logger.error(
            "TCX file not found",
            input_file=str(tcx_path),
        )
        return ConversionResult(
            success=False,
            points=0,
            laps=0,
            error="TCX file not found",
        )
    except Exception as e:
        logger.error(
            "Failed to convert TCX to KML",
            input_file=str(tcx_path),
            error=str(e),
        )
        return ConversionResult(
            success=False,
            points=0,
            laps=0,
            error=str(e),
        )


def convert_single_file(
    input_path: Path, output_path: Path | None, overwrite: bool
) -> int:
    """Convert a single TCX file to KML.

    Args:
        input_path: Path to the input TCX file
        output_path: Path to the output KML file (optional, auto-generated if None)
        overwrite: Whether to overwrite existing output files

    Returns:
        Exit code (0 for success, 1 for failure)

    """
    # Auto-generate output path if not provided
    if output_path is None:
        output_path = input_path.with_suffix(".kml")

    result = convert_tcx_to_kml(input_path, output_path, overwrite)

    if result.success:
        print(f"✓ Converted {input_path} -> {output_path}")
        print(f"  Points: {result.points}, Laps: {result.laps}")
        return 0
    else:
        print(f"✗ Failed to convert {input_path}: {result.error}", file=sys.stderr)
        return 1


def convert_directory(
    input_dir: Path, output_dir: Path, overwrite: bool, show_stats: bool
) -> int:
    """Convert all TCX files in a directory to KML.

    Args:
        input_dir: Path to the input directory containing TCX files
        output_dir: Path to the output directory for KML files
        overwrite: Whether to overwrite existing output files
        show_stats: Whether to display statistics after conversion

    Returns:
        Exit code (0 for success, 1 if any conversions failed)

    """
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all TCX files in the input directory (recursively)
    tcx_files = sorted(input_dir.rglob("*.tcx"))

    if not tcx_files:
        logger.warning("No TCX files found in input directory", dir=str(input_dir))
        print(f"No TCX files found in {input_dir}", file=sys.stderr)
        return 1

    # Convert each file
    results: list[tuple[Path, ConversionResult]] = []
    for tcx_file in tcx_files:
        relative_path = tcx_file.relative_to(input_dir)
        kml_file = output_dir / relative_path.with_suffix(".kml")
        kml_file.parent.mkdir(parents=True, exist_ok=True)
        result = convert_tcx_to_kml(tcx_file, kml_file, overwrite)
        results.append((tcx_file, result))

        if result.success:
            print(f"✓ Converted {relative_path} -> {kml_file.relative_to(output_dir)}")
        else:
            print(f"✗ Failed to convert {relative_path}: {result.error}")

    # Calculate and display statistics
    if show_stats:
        total_files = len(results)
        successful = sum(1 for _, r in results if r.success)
        failed = total_files - successful
        total_points = sum(r.points for _, r in results if r.success)
        total_laps = sum(r.laps for _, r in results if r.success)

        stats = ConversionStats(
            total_files=total_files,
            successful=successful,
            failed=failed,
            total_points=total_points,
            total_laps=total_laps,
        )

        print("\n" + "=" * 50)
        print("Conversion Statistics")
        print("=" * 50)
        print(f"Total files processed: {stats.total_files}")
        print(f"Successful conversions: {stats.successful}")
        print(f"Failed conversions: {stats.failed}")
        print(f"Total GPS points: {stats.total_points}")
        print(f"Total laps: {stats.total_laps}")
        if stats.successful > 0:
            print(
                f"Average points per file: {stats.total_points / stats.successful:.1f}"
            )
            print(f"Average laps per file: {stats.total_laps / stats.successful:.1f}")

    # Return success if at least one file was converted successfully
    return 0 if any(r.success for _, r in results) else 1


def main() -> int:
    """Main entry point for the TCX to KML converter."""
    parser = argparse.ArgumentParser(
        description="Convert TCX workout files to KML format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert a single file (output auto-named)
  %(prog)s --in workout.tcx

  # Convert with explicit output
  %(prog)s --in workout.tcx --out ../maps/workout.kml

  # Convert all files in a directory
  %(prog)s --in-dir ./tcx-files --out-dir ./kml-files

  # Force overwrite existing files
  %(prog)s --in-dir ./tcx-files --out-dir ./kml-files --overwrite-destination

  # Disable statistics output
  %(prog)s --in-dir ./tcx-files --out-dir ./kml-files --no-stats
        """,
    )

    # Input/output arguments
    parser.add_argument(
        "--in",
        dest="input_file",
        type=Path,
        help="Input TCX file to convert",
    )
    parser.add_argument(
        "--out",
        dest="output_file",
        type=Path,
        help="Output KML file (optional for single file mode)",
    )
    parser.add_argument(
        "--in-dir",
        dest="input_dir",
        type=Path,
        help="Input directory containing TCX files",
    )
    parser.add_argument(
        "--out-dir",
        dest="output_dir",
        type=Path,
        help="Output directory for KML files (required for directory mode)",
    )

    # Options
    parser.add_argument(
        "--overwrite-destination",
        action="store_true",
        help="Overwrite existing output files",
    )
    parser.add_argument(
        "--no-stats",
        action="store_true",
        help="Disable statistics output in directory mode",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.input_file and args.input_dir:
        parser.error("Cannot specify both --in and --in-dir")

    if not args.input_file and not args.input_dir:
        parser.error("Must specify either --in or --in-dir")

    # Directory mode validation
    if args.input_dir:
        if not args.output_dir:
            parser.error("--out-dir is required when using --in-dir")

        if not args.input_dir.exists():
            parser.error(f"Input directory does not exist: {args.input_dir}")

        if not args.input_dir.is_dir():
            parser.error(f"Input path is not a directory: {args.input_dir}")

        return convert_directory(
            args.input_dir,
            args.output_dir,
            args.overwrite_destination,
            not args.no_stats,
        )

    # Single file mode
    if args.input_file:
        if not args.input_file.exists():
            parser.error(f"Input file does not exist: {args.input_file}")

        if not args.input_file.is_file():
            parser.error(f"Input path is not a file: {args.input_file}")

        return convert_single_file(
            args.input_file,
            args.output_file,
            args.overwrite_destination,
        )

    return 1


if __name__ == "__main__":
    sys.exit(main())
