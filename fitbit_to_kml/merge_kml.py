"""Helpers for merging multiple KML files into a single document."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple, Sequence
import xml.etree.ElementTree as ET

import simplekml
import structlog

logger = structlog.get_logger()

KML_NS = "http://www.opengis.net/kml/2.2"
NS = {"kml": KML_NS}

ET.register_namespace("", KML_NS)

Coordinate = tuple[float, float] | tuple[float, float, float]


class MergeStats(NamedTuple):
    """Summary information for a merge run."""

    files: int
    placemarks: int
    points: int


class MergeResult(NamedTuple):
    """Result metadata for a merge run."""

    stats: MergeStats
    merged_files: list[Path]
    skipped_files: list[Path]


@dataclass(slots=True)
class KmlTrack:
    """A single KML LineString extracted from an input file."""

    source: Path
    name: str
    coordinates: list[Coordinate]


def collect_kml_files(input_dir: Path, output_file: Path | None = None) -> list[Path]:
    """Return all KML files found under ``input_dir`` (recursively)."""

    if not input_dir.exists() or not input_dir.is_dir():
        raise MergeError(f"Input directory does not exist: {input_dir}")

    candidates = sorted(p for p in input_dir.rglob("*.kml") if p.is_file())
    if output_file is not None:
        output_resolved = output_file.resolve()
        candidates = [p for p in candidates if p.resolve() != output_resolved]

    return candidates


def parse_kml_file(file_path: Path) -> list[KmlTrack]:
    """Extract LineStrings from a KML file."""

    try:
        tree = ET.parse(file_path)
    except ET.ParseError as exc:
        raise MergeError(f"Failed to parse KML file {file_path}") from exc

    tracks: list[KmlTrack] = []
    placemarks = tree.findall(".//kml:Placemark", namespaces=NS)

    for placemark in placemarks:
        linestring = placemark.find(".//kml:LineString", namespaces=NS)
        if linestring is None:
            continue
        coords_elem = linestring.find("kml:coordinates", namespaces=NS)
        if coords_elem is None or not coords_elem.text:
            continue

        coords = parse_coordinates(coords_elem.text)
        if not coords:
            continue

        name_elem = placemark.find("kml:name", namespaces=NS)
        name = (
            name_elem.text.strip()
            if name_elem is not None and name_elem.text
            else file_path.stem
        )

        tracks.append(KmlTrack(source=file_path, name=name, coordinates=coords))

    return tracks


def parse_coordinates(raw_coordinates: str) -> list[Coordinate]:
    """Convert a ``coordinates`` string into tuples of lon/lat(/alt)."""

    coords: list[Coordinate] = []
    for chunk in raw_coordinates.split():
        if not chunk:
            continue
        parts = chunk.split(",")
        if len(parts) < 2:
            continue
        try:
            lon = float(parts[0])
            lat = float(parts[1])
        except ValueError:
            continue

        if len(parts) >= 3 and parts[2]:
            try:
                alt = float(parts[2])
            except ValueError:
                alt = 0.0
            coords.append((lon, lat, alt))
        else:
            coords.append((lon, lat))

    return coords


def build_kml(tracks: Sequence[KmlTrack]) -> simplekml.Kml:
    """Render the provided tracks to a ``simplekml`` document."""

    kml = simplekml.Kml()
    for track in tracks:
        linestring = kml.newlinestring(name=track.name)
        linestring.coords = track.coordinates
        linestring.style.linestyle.color = simplekml.Color.red
        linestring.style.linestyle.width = 3
    return kml


class MergeError(Exception):
    """Raised when the merge operation cannot be completed."""


def merge_kml_files(
    input_dir: Path,
    output_file: Path,
    *,
    overwrite: bool = False,
    dry_run: bool = False,
) -> MergeResult:
    """Merge all KML files under ``input_dir`` into ``output_file``."""

    kml_files = collect_kml_files(input_dir, output_file=output_file)
    if not kml_files:
        raise MergeError(f"No KML files found in {input_dir}")

    tracks: list[KmlTrack] = []
    merged_files: list[Path] = []
    skipped_files: list[Path] = []

    for kml_file in kml_files:
        extracted = parse_kml_file(kml_file)
        if not extracted:
            logger.warning("No LineStrings found in file", file=str(kml_file))
            skipped_files.append(kml_file)
            continue
        merged_files.append(kml_file)
        tracks.extend(extracted)

    if not tracks:
        raise MergeError("No LineStrings found in any KML files")

    stats = MergeStats(
        files=len(merged_files),
        placemarks=len(tracks),
        points=sum(len(track.coordinates) for track in tracks),
    )

    if dry_run:
        return MergeResult(
            stats=stats, merged_files=merged_files, skipped_files=skipped_files
        )

    if output_file.exists() and not overwrite:
        raise MergeError(
            f"Output file already exists: {output_file}. Pass --overwrite to replace it."
        )

    output_file.parent.mkdir(parents=True, exist_ok=True)
    document = build_kml(tracks)
    document.save(str(output_file))
    logger.info(
        "Merged KML files",
        files=stats.files,
        placemarks=stats.placemarks,
        points=stats.points,
        output=str(output_file),
    )

    return MergeResult(
        stats=stats, merged_files=merged_files, skipped_files=skipped_files
    )
