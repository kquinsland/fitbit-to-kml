#!/usr/bin/env python3
"""Tests for the TCX to KML converter."""

import sys
from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

import pytest

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import after path modification
# Importing like this avoids the hyphenated module name issue
import importlib.util

spec = importlib.util.spec_from_file_location(
    "tcx_to_kml",
    Path(__file__).parent.parent / "tcx-to-kml.py",
)
tcx_to_kml = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tcx_to_kml)


@pytest.fixture
def sample_tcx_content() -> str:
    """Return sample TCX content with GPS data."""
    return dedent(
        """\
        <?xml version="1.0" encoding="UTF-8"?>
        <TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">
          <Activities>
            <Activity Sport="Running">
              <Id>2024-01-01T10:00:00Z</Id>
              <Lap StartTime="2024-01-01T10:00:00Z">
                <TotalTimeSeconds>600</TotalTimeSeconds>
                <DistanceMeters>1000</DistanceMeters>
                <Track>
                  <Trackpoint>
                    <Time>2024-01-01T10:00:00Z</Time>
                    <Position>
                      <LatitudeDegrees>38.700255</LatitudeDegrees>
                      <LongitudeDegrees>-121.10608833333333</LongitudeDegrees>
                    </Position>
                  </Trackpoint>
                  <Trackpoint>
                    <Time>2024-01-01T10:01:00Z</Time>
                    <Position>
                      <LatitudeDegrees>38.701255</LatitudeDegrees>
                      <LongitudeDegrees>-121.10708833333333</LongitudeDegrees>
                    </Position>
                  </Trackpoint>
                  <Trackpoint>
                    <Time>2024-01-01T10:02:00Z</Time>
                    <Position>
                      <LatitudeDegrees>38.702255</LatitudeDegrees>
                      <LongitudeDegrees>-121.10808833333333</LongitudeDegrees>
                    </Position>
                  </Trackpoint>
                </Track>
              </Lap>
            </Activity>
          </Activities>
        </TrainingCenterDatabase>
        """
    )


@pytest.fixture
def empty_tcx_content() -> str:
    """Return TCX content without GPS data."""
    return dedent(
        """\
        <?xml version="1.0" encoding="UTF-8"?>
        <TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">
          <Activities>
            <Activity Sport="Running">
              <Id>2024-01-03T10:00:00Z</Id>
              <Lap StartTime="2024-01-03T10:00:00Z">
                <TotalTimeSeconds>100</TotalTimeSeconds>
                <Track>
                  <!-- No position data -->
                </Track>
              </Lap>
            </Activity>
          </Activities>
        </TrainingCenterDatabase>
        """
    )


def test_convert_tcx_to_kml_success(tmp_path: Path, sample_tcx_content: str) -> None:
    """Test successful conversion of TCX to KML."""
    tcx_file = tmp_path / "workout.tcx"
    kml_file = tmp_path / "workout.kml"

    tcx_file.write_text(sample_tcx_content)

    result = tcx_to_kml.convert_tcx_to_kml(tcx_file, kml_file, overwrite=False)

    assert result.success
    assert result.points == 3
    assert result.laps == 0
    assert result.error is None
    assert kml_file.exists()

    # Verify KML content has expected structure
    kml_content = kml_file.read_text()
    assert '<?xml version="1.0" encoding="UTF-8"?>' in kml_content
    assert "<kml" in kml_content
    assert "<LineString" in kml_content
    assert "<coordinates>" in kml_content


def test_convert_tcx_to_kml_no_gps_data(tmp_path: Path, empty_tcx_content: str) -> None:
    """Test conversion fails gracefully when TCX has no GPS data."""
    tcx_file = tmp_path / "empty-workout.tcx"
    kml_file = tmp_path / "empty-workout.kml"

    tcx_file.write_text(empty_tcx_content)

    result = tcx_to_kml.convert_tcx_to_kml(tcx_file, kml_file, overwrite=False)

    assert not result.success
    assert result.points == 0
    assert result.error == "No GPS points found in TCX file"
    assert not kml_file.exists()


def test_convert_tcx_to_kml_file_not_found(tmp_path: Path) -> None:
    """Test conversion fails when input file doesn't exist."""
    tcx_file = tmp_path / "nonexistent.tcx"
    kml_file = tmp_path / "output.kml"

    result = tcx_to_kml.convert_tcx_to_kml(tcx_file, kml_file, overwrite=False)

    assert not result.success
    assert result.error is not None
    assert (
        "No such file or directory" in result.error
        or "TCX file not found" in result.error
    )
    assert not kml_file.exists()


def test_convert_tcx_to_kml_overwrite_protection(
    tmp_path: Path, sample_tcx_content: str
) -> None:
    """Test that existing files are not overwritten without flag."""
    tcx_file = tmp_path / "workout.tcx"
    kml_file = tmp_path / "workout.kml"

    tcx_file.write_text(sample_tcx_content)
    kml_file.write_text("existing content")

    result = tcx_to_kml.convert_tcx_to_kml(tcx_file, kml_file, overwrite=False)

    assert not result.success
    assert "already exists" in result.error
    assert kml_file.read_text() == "existing content"


def test_convert_tcx_to_kml_with_overwrite(
    tmp_path: Path, sample_tcx_content: str
) -> None:
    """Test that existing files can be overwritten with flag."""
    tcx_file = tmp_path / "workout.tcx"
    kml_file = tmp_path / "workout.kml"

    tcx_file.write_text(sample_tcx_content)
    kml_file.write_text("existing content")

    result = tcx_to_kml.convert_tcx_to_kml(tcx_file, kml_file, overwrite=True)

    assert result.success
    assert result.points == 3
    assert kml_file.read_text() != "existing content"
    assert "<kml" in kml_file.read_text()


def test_convert_single_file_auto_output(
    tmp_path: Path, sample_tcx_content: str
) -> None:
    """Test single file conversion with auto-generated output path."""
    tcx_file = tmp_path / "workout.tcx"
    tcx_file.write_text(sample_tcx_content)

    exit_code = tcx_to_kml.convert_single_file(tcx_file, None, overwrite=False)

    assert exit_code == 0
    kml_file = tmp_path / "workout.kml"
    assert kml_file.exists()


def test_convert_single_file_explicit_output(
    tmp_path: Path, sample_tcx_content: str
) -> None:
    """Test single file conversion with explicit output path."""
    tcx_file = tmp_path / "workout.tcx"
    output_file = tmp_path / "custom.kml"
    tcx_file.write_text(sample_tcx_content)

    exit_code = tcx_to_kml.convert_single_file(tcx_file, output_file, overwrite=False)

    assert exit_code == 0
    assert output_file.exists()


def test_convert_directory_success(tmp_path: Path, sample_tcx_content: str) -> None:
    """Test directory conversion with multiple files."""
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()

    # Create multiple TCX files
    (input_dir / "workout1.tcx").write_text(sample_tcx_content)
    (input_dir / "workout2.tcx").write_text(sample_tcx_content)

    exit_code = tcx_to_kml.convert_directory(
        input_dir, output_dir, overwrite=False, show_stats=True
    )

    assert exit_code == 0
    assert (output_dir / "workout1.kml").exists()
    assert (output_dir / "workout2.kml").exists()


def test_convert_directory_mixed_results(
    tmp_path: Path, sample_tcx_content: str, empty_tcx_content: str
) -> None:
    """Test directory conversion with both valid and invalid files."""
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()

    # Create one valid and one invalid TCX file
    (input_dir / "valid.tcx").write_text(sample_tcx_content)
    (input_dir / "invalid.tcx").write_text(empty_tcx_content)

    exit_code = tcx_to_kml.convert_directory(
        input_dir, output_dir, overwrite=False, show_stats=True
    )

    assert exit_code == 0  # Should succeed if at least one file converts
    assert (output_dir / "valid.kml").exists()
    assert not (output_dir / "invalid.kml").exists()


def test_convert_directory_no_files(tmp_path: Path) -> None:
    """Test directory conversion fails when no TCX files are found."""
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()

    exit_code = tcx_to_kml.convert_directory(
        input_dir, output_dir, overwrite=False, show_stats=True
    )

    assert exit_code == 1


def test_convert_directory_no_stats(tmp_path: Path, sample_tcx_content: str) -> None:
    """Test directory conversion with statistics disabled."""
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()

    (input_dir / "workout.tcx").write_text(sample_tcx_content)

    exit_code = tcx_to_kml.convert_directory(
        input_dir, output_dir, overwrite=False, show_stats=False
    )

    assert exit_code == 0
    assert (output_dir / "workout.kml").exists()


def test_main_missing_input_args() -> None:
    """Test main function fails when no input is specified."""
    with patch("sys.argv", ["tcx-to-kml.py"]):
        with pytest.raises(SystemExit) as exc_info:
            tcx_to_kml.main()
        assert exc_info.value.code != 0


def test_main_conflicting_args() -> None:
    """Test main function fails when both --in and --in-dir are specified."""
    with patch("sys.argv", ["tcx-to-kml.py", "--in", "file.tcx", "--in-dir", "dir"]):
        with pytest.raises(SystemExit) as exc_info:
            tcx_to_kml.main()
        assert exc_info.value.code != 0


def test_main_missing_output_dir() -> None:
    """Test main function fails when --in-dir is used without --out-dir."""
    with patch("sys.argv", ["tcx-to-kml.py", "--in-dir", "dir"]):
        with pytest.raises(SystemExit) as exc_info:
            tcx_to_kml.main()
        assert exc_info.value.code != 0


def test_conversion_stats_named_tuple() -> None:
    """Test ConversionStats NamedTuple structure."""
    stats = tcx_to_kml.ConversionStats(
        total_files=10,
        successful=8,
        failed=2,
        total_points=1000,
        total_laps=20,
    )

    assert stats.total_files == 10
    assert stats.successful == 8
    assert stats.failed == 2
    assert stats.total_points == 1000
    assert stats.total_laps == 20


def test_conversion_result_named_tuple() -> None:
    """Test ConversionResult NamedTuple structure."""
    result = tcx_to_kml.ConversionResult(
        success=True,
        points=100,
        laps=5,
        error=None,
    )

    assert result.success is True
    assert result.points == 100
    assert result.laps == 5
    assert result.error is None
