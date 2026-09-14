from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from PIL import Image

from nanomech.cli import main
from nanomech.static import StaticConfig
from nanomech.sample_plot import plot_static_sample
from nanomech.nm_models import HertzSphere


def test_overlay_and_result_text(tmp_path,monkeypatch):
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure
    curves,texts = [],[]
    original_plot,original_label = Axes.plot,Figure.supxlabel
    def plot(self,x,y,*args,**kwargs):
        curves.append((np.asarray(x),np.asarray(y)))
        return original_plot(self,x,y,*args,**kwargs)
    def label(self,text,*args,**kwargs):
        texts.append(text)
        return original_label(self,text,*args,**kwargs)
    monkeypatch.setattr(Axes,"plot",plot)
    monkeypatch.setattr(Figure,"supxlabel",label)
    x = np.linspace(-100e-9,100e-9,50)
    config = StaticConfig(fit_direction="Retract")
    result = dict(young_modulus_pa=2e6,contact_point_m=10e-9,residual_norm_n=1e-10)
    model = HertzSphere(config.tip_radius,config.poisson_ratio)
    y = model.evaluate([2e6,10e-9],x)
    path = plot_static_sample(tmp_path,23,x,y,result,config)
    assert path.name == "sample_point00023_Hertz_retract.png"
    np.testing.assert_allclose(curves[0][0],x*1e9)
    np.testing.assert_allclose(curves[0][1],y*1e9)
    np.testing.assert_allclose(curves[1][1],model.evaluate([2e6,10e-9],curves[1][0]*1e-9)*1e9,atol=1e-12)
    assert "Young's modulus = 2 MPa" in texts[0]
    assert "Contact point = 10 nm" in texts[0]
    with Image.open(path) as image:
        assert image.format == "PNG"
        image.verify()


@pytest.mark.parametrize("options,count", [([],0),(["--plot-sample"],2),
    (["--plot-sample","--max-plot-sample","1"],1),
    (["--plot-sample","--max-plot-sample","0"],0),
    (["--max-plot-sample","1"],0)])
def test_cli_plot_limit_does_not_limit_analysis(tmp_path,monkeypatch,options,count):
    from nanomech import calibration
    root = Path(__file__).resolve().parents[1]/"test-data-large"
    sample,cal = root/"VEA-500-5k-sample.nhf",root/"VEA-500-5k-calibration.nhf"
    if not sample.exists() or not cal.exists():
        pytest.skip("Local VEA data unavailable")
    monkeypatch.setattr(calibration,"SCRIPT_DIRECTORY",tmp_path)
    assert main(["vea","--sample",str(sample),"--calibration",str(cal),"--max_count","2",
                 "--output",str(tmp_path/"results")]+options) == 0
    assert len(list((tmp_path/"results").glob("*/sample/*_Hertz_advance.png"))) == count
    dynamic = list((tmp_path/"results").glob("*/sample/*_sine_VEA.png"))
    assert len(dynamic) == count
    for path in dynamic:
        with Image.open(path) as image:
            assert image.size == (1600,3200)
    csv, = (tmp_path/"results").glob("*/static_results.csv")
    assert (pd.read_csv(csv).static_status == "success").sum() == 2


def test_bad_plot_limit():
    assert main(["vea","--sample","unused.nhf","--max-plot-sample","-1"]) == 1


def test_filename_width_and_segments():
    from nanomech.sample_plot import sample_plot_filename
    assert sample_plot_filename(3,"Hertz","advance") == "sample_point00003_Hertz_advance.png"
    assert sample_plot_filename(3,"sine","VEA",2) == "sample_point03_sine_VEA.png"
    assert sample_plot_filename(3,"Hertz","retract",1) == "sample_point3_Hertz_retract.png"
