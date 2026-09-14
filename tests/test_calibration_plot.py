from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from nanomech.preparation import CalibrationPreparation
from nanomech.excitation import SineFitResult
from nanomech.calibration_plot import plot_calibration
from nanomech.cli import main


def test_plot_uses_existing_fit(tmp_path, monkeypatch):
    from matplotlib.axes import Axes
    lines = []
    original = Axes.plot
    def record(self, x, y, *args, **kwargs):
        lines.append((np.asarray(x), np.asarray(y)))
        return original(self, x, y, *args, **kwargs)
    monkeypatch.setattr(Axes, "plot", record)
    t = np.linspace(3, 3.01, 100)
    fit = SineFitResult(2e-9, 501., 1.3, 3e-9, 0.)
    d = fit.amplitude*np.sin(2*np.pi*(t-t[0])*fit.frequency_hz+.3)+fit.dc
    result = CalibrationPreparation({}, (500.,), {"deflection":(fit,)}, t, d, np.array([0,100]))
    files = plot_calibration(result, tmp_path)
    assert len(files) == 1 and files[0].name == "calibration_deflection.png"
    np.testing.assert_allclose(lines[0][0], (t-t[0])*1e3)
    np.testing.assert_allclose(lines[0][1], d*1e9)
    tx = lines[1][0]/1e3
    np.testing.assert_allclose(lines[1][1], (fit.amplitude*np.sin(2*np.pi*501*tx+.3)+fit.dc)*1e9)
    with Image.open(files[0]) as image:
        assert image.format == "PNG"
        assert image.size == (1600,640)


def test_real_cli_plots_and_opt_in(tmp_path, monkeypatch):
    from nanomech import calibration
    from nanosurf.utils.io import nhf_reader
    root = Path(__file__).resolve().parents[1]
    sample = root/"test-data-large/VEA-500-5k-sample.nhf"
    source = root/"test-data-large/VEA-500-5k-calibration.nhf"
    if not sample.exists() or not source.exists():
        pytest.skip("Local VEA inputs unavailable")
    monkeypatch.setattr(calibration,"SCRIPT_DIRECTORY",tmp_path)
    original = nhf_reader.NHFDataset.read_data
    def guarded(channel,*args,**kwargs):
        assert Path(channel.h5_dataset.file.filename).resolve() != sample.resolve()
        return original(channel,*args,**kwargs)
    monkeypatch.setattr(nhf_reader.NHFDataset,"read_data",guarded)
    args = ["vea","--sample",str(sample),"--calibration",str(source),"--max_count","1",
            "--dry-run","--output",str(tmp_path/"plots")]
    assert main(args) == 0
    assert not (tmp_path/"plots").exists()
    assert main(args+["--plot-calibration"]) == 0
    files = list((tmp_path/"plots").glob("*/calibration/*.png"))
    assert len(files) == 1
    for path in files:
        with Image.open(path) as image:
            assert image.size == (1600,3200)
            image.verify()
