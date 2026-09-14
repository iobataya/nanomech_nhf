"""Selection tests use an asymmetric map to detect XY flips."""
from pathlib import Path
import json
import logging

import pytest

from nanomech.selection import select_points, select_sample_points
from nanomech.cli import main


def test_crop_then_limit_in_acquisition_order():
    result = select_points(5, 3, crop_area="1,0:3,2", max_count=5)
    assert result.point_indices == (1, 2, 3, 6, 7)
    assert [result.xy(i) for i in result.point_indices] == [(1,0), (2,0), (3,0), (3,1), (2,1)]
    assert result.total_count == 15


def test_defaults_single_point_and_large_limit():
    assert select_points(5,3).point_indices == tuple(range(15))
    assert select_points(5,3,max_count=2).point_indices == (0,1)
    assert select_points(1,1).point_indices == (0,)
    assert select_points(5,3,crop_area="4,2:4,2",max_count=100).point_indices == (14,)


@pytest.mark.parametrize("limit", [0, -1, 1.5, True, "2"])
def test_bad_limit(limit):
    with pytest.raises(ValueError):
        select_points(5,3,max_count=limit)


@pytest.mark.parametrize("crop", ["", "1,2,3,4", "-1,0:2,2", "3,0:1,2", "0,0:5,2", "0,0:4,3", 1])
def test_bad_crop(crop):
    with pytest.raises(ValueError):
        select_points(5,3,crop_area=crop)


def test_single_point_still_validates_options():
    with pytest.raises(ValueError):
        select_points(1,1,crop_area="0,0:1,1")
    with pytest.raises(ValueError):
        select_points(5,3,scan_pattern="unknown")


def representative():
    source = Path(__file__).resolve().parents[1]/"test-data-large/VEA-500-5k-sample.nhf"
    if not source.exists():
        pytest.skip("Local VEA sample is unavailable")
    return source


def test_large_sample_does_not_load_waveforms(monkeypatch):
    from nanosurf.utils.io import nhf_reader
    def forbidden(*args, **kwargs):
        raise AssertionError("Selection must not load channel data")
    monkeypatch.setattr(nhf_reader.NHFDataset, "read_data", forbidden)
    result = select_sample_points(representative(), max_count=4, crop_area="0,0:1,1")
    assert result.point_indices == (0,1,254,255)
    assert result.total_count == 16384


@pytest.mark.parametrize("option", ["--max_count", "--max-count", "--max_points", "--max-points"])
def test_cli_config_override(option, tmp_path, caplog, monkeypatch):
    monkeypatch.setattr("nanomech.workflows.load_calibration", lambda path: None)
    monkeypatch.setattr("nanomech.workflows.prepare_calibration", lambda *a, **k: None)
    config = tmp_path/"vea.json"
    config.write_text(json.dumps({"schema_version":1,"command":"vea","sample":str(representative()),
                                  "max_count":8,"crop_area":"0,0:1,1"}))
    with caplog.at_level(logging.INFO):
        assert main(["vea","--config",str(config),option,"2","--dry-run"]) == 0
    assert "2 / 16384 points" in caplog.text
