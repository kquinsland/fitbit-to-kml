"""Tests for the KML merge helpers."""

from __future__ import annotations

import pytest

from fitbit_to_kml.merge_kml import (
    MergeError,
    merge_kml_files,
    parse_coordinates,
    parse_kml_file,
)


def make_kml_content(name: str, coordinates: str) -> str:
    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<kml xmlns=\"http://www.opengis.net/kml/2.2\">
  <Document>
    <Placemark>
      <name>{name}</name>
      <LineString>
        <coordinates>{coordinates}</coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>
"""


def test_parse_coordinates_handles_altitude():
    coords = parse_coordinates("-121.0,38.0,5  -122.0,39.0")
    assert coords == [(-121.0, 38.0, 5.0), (-122.0, 39.0)]


def test_parse_kml_file_extracts_track(tmp_path):
    file_path = tmp_path / "track.kml"
    file_path.write_text(
        make_kml_content("demo", "-121,38,0 -122,39,0"), encoding="utf-8"
    )

    tracks = parse_kml_file(file_path)

    assert len(tracks) == 1
    assert tracks[0].name == "demo"
    assert len(tracks[0].coordinates) == 2


def test_merge_kml_files_dry_run_counts(tmp_path):
    (tmp_path / "nested").mkdir()
    file_a = tmp_path / "a.kml"
    file_b = tmp_path / "nested" / "b.kml"
    file_a.write_text(make_kml_content("a", "-121,38,0 -122,39,0"), encoding="utf-8")
    file_b.write_text(make_kml_content("b", "-120,37 -121,38"), encoding="utf-8")

    result = merge_kml_files(tmp_path, tmp_path / "MERGED.kml", dry_run=True)

    assert result.stats.files == 2
    assert result.stats.placemarks == 2
    assert result.stats.points == 4
    assert len(result.merged_files) == 2


def test_merge_kml_files_writes_output(tmp_path):
    input_dir = tmp_path / "inputs"
    input_dir.mkdir()
    output_file = tmp_path / "out" / "merged.kml"
    (input_dir / "05.kml").write_text(
        make_kml_content("demo", "-121,38 -120,37"),
        encoding="utf-8",
    )

    result = merge_kml_files(input_dir, output_file, dry_run=False)

    assert output_file.exists()
    assert result.stats.files == 1
    assert result.stats.points == 2


def test_merge_kml_files_errors_when_none_found(tmp_path):
    with pytest.raises(MergeError):
        merge_kml_files(tmp_path, tmp_path / "MERGED.kml", dry_run=True)
