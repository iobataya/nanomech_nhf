import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

from nanomech import calibration
from nanomech.cli import main
from nanomech.selection import select_points


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    directory = tmp_path / "script"
    directory.mkdir()
    monkeypatch.setattr(calibration, "SCRIPT_DIRECTORY", directory)
    return directory


@pytest.fixture
def reader(monkeypatch):
    calls = []
    def read(path):
        calls.append(path)
        if path.read_bytes() == b"invalid":
            raise ValueError("Invalid NHF")
        channel = SimpleNamespace(h5_dataset=SimpleNamespace(size=10))
        return SimpleNamespace(attribute={"rect_axis_size": [1,1]}, segment={
            calibration.Segment.VEA: SimpleNamespace(channel={name:channel for name in (
                calibration.Channel.DEFLECTION, calibration.Channel.TIME,
                calibration.Channel.Z_POSITION, calibration.Channel.SAMPLER_META)})})
    monkeypatch.setattr(calibration, "load_nhf_file", read)
    return calls


def test_explicit_priority_and_refresh(cache_dir, tmp_path, reader, caplog):
    cache = cache_dir / ".last_calibration.nhf"
    cache.write_bytes(b"old")
    explicit = tmp_path / "calibration.nhf"
    explicit.write_bytes(b"new")
    with caplog.at_level(logging.DEBUG):
        result = calibration.load_calibration(explicit)
    assert result.path == explicit.resolve()
    assert result.source == "CLI"
    assert reader == [explicit.resolve()]
    assert cache.read_bytes() == b"new"
    assert "source=CLI" in caplog.text
    explicit.write_bytes(b"newer")
    calibration.load_calibration(explicit)
    assert cache.read_bytes() == b"newer"
    assert len(reader) == 2


def test_cache_is_script_relative(cache_dir, tmp_path, reader, monkeypatch, caplog):
    cache = cache_dir / ".last_calibration.nhf"
    cache.write_bytes(b"cached")
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".last_calibration.nhf").write_bytes(b"wrong-directory")
    with caplog.at_level(logging.DEBUG):
        result = calibration.load_calibration()
    assert result.path == cache.resolve()
    assert reader == [cache.resolve()]
    assert "source=cache" in caplog.text


def test_missing_cache_raises(cache_dir, reader):
    with pytest.raises(FileNotFoundError):
        calibration.load_calibration()
    assert reader == []


@pytest.mark.parametrize("exists", [False, True])
def test_bad_explicit_never_falls_back(cache_dir, tmp_path, reader, exists):
    cache = cache_dir / ".last_calibration.nhf"
    cache.write_bytes(b"good")
    explicit = tmp_path / "bad.nhf"
    if exists:
        explicit.write_bytes(b"invalid")
    with pytest.raises((ValueError, FileNotFoundError)):
        calibration.load_calibration(explicit)
    assert cache.read_bytes() == b"good"
    assert cache.resolve() not in reader


def test_copy_failure_preserves_cache(cache_dir, tmp_path, reader, monkeypatch):
    cache = cache_dir / ".last_calibration.nhf"
    cache.write_bytes(b"old")
    explicit = tmp_path / "new.nhf"
    explicit.write_bytes(b"new")
    def fail(*args):
        raise OSError("Copy failed")
    monkeypatch.setattr(calibration.shutil, "copyfileobj", fail)
    with pytest.raises(OSError):
        calibration.load_calibration(explicit)
    assert cache.read_bytes() == b"old"
    assert not list(cache_dir.glob("*.tmp"))


def test_explicit_cache_itself(cache_dir, reader):
    cache = cache_dir / ".last_calibration.nhf"
    cache.write_bytes(b"same")
    assert calibration.load_calibration(cache).source == "CLI"
    assert cache.read_bytes() == b"same"


def test_real_calibration_preview(cache_dir, monkeypatch):
    path = Path(__file__).resolve().parents[1] / "test-data-large/VEA-500-5k-calibration.nhf"
    if not path.exists():
        pytest.skip("Local calibration NHF unavailable")
    monkeypatch.setattr("nanomech.vea_command.select_sample_points", lambda *a, **k: select_points(1,1))
    sample = path.with_name("VEA-500-5k-sample.nhf")
    if not sample.exists():
        pytest.skip("Local sample NHF unavailable")
    assert main(["vea", "--sample", str(sample), "--calibration", str(path), "--dry-run"]) == 0
    assert (cache_dir / ".last_calibration.nhf").read_bytes() == path.read_bytes()
    assert main(["vea", "--sample", str(sample), "--dry-run"]) == 0


def test_cli_missing_calibration_fails(cache_dir, monkeypatch):
    monkeypatch.setattr("nanomech.vea_command.select_sample_points", lambda *a, **k: select_points(1,1))
    assert main(["vea", "--sample", "unused.nhf", "--dry-run"]) == 1
