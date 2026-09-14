from pathlib import Path
import json

import numpy as np
import pandas as pd
import pytest

from nanomech.static import StaticConfig, fit_static_point, read_point_channel, analyze_static, RESULT_COLUMNS
from nanomech.preparation import resolve_probe
from nanomech.selection import select_sample_points
from nanomech.cli import main
from nanomech.nm_io import load_nhf_file, Segment, Channel


@pytest.mark.parametrize("direction",["Advance","Retract"])
@pytest.mark.parametrize("modulus",[2e3,2e6,2e9])
def test_known_young_modulus_si(direction,modulus):
    x = np.linspace(-300e-9,100e-9,1000)
    radius,k = 5e-9,.08
    force = 4/3*modulus*np.sqrt(radius)/(1-.5**2)*np.maximum(x,0)**1.5
    d = force/k
    z = -(x+d)
    result = fit_static_point(z,d,z[::-1],d[::-1],k,StaticConfig(fit_direction=direction))
    assert result["young_modulus_pa"] == pytest.approx(modulus,rel=1e-5)
    assert result["contact_point_m"] == pytest.approx(0,abs=1e-12)


def inputs():
    root = Path(__file__).resolve().parents[1]/"test-data-large"
    s,c = root/"VEA-500-5k-sample.nhf",root/"VEA-500-5k-calibration.nhf"
    if not s.exists() or not c.exists():
        pytest.skip("Local VEA files unavailable")
    return s,c


def test_slice_conversion_matches_official_reader():
    _,c = inputs()
    measurement = load_nhf_file(c)
    segment = measurement.segment[Segment.VEA]
    for name in (Channel.DEFLECTION,Channel.Z_POSITION):
        values,unit = read_point_channel(segment,name,0)
        full = segment.read_channel(name)
        np.testing.assert_array_equal(values,full.dataset[:len(values)])
        assert unit == full.unit


def test_cli_static_csv(tmp_path,monkeypatch):
    from nanomech import calibration
    from nanosurf.utils.io import nhf_reader
    s,c = inputs()
    monkeypatch.setattr(calibration,"SCRIPT_DIRECTORY",tmp_path)
    original = nhf_reader.NHFDataset.read_data
    def guard(channel,*a,**kw):
        if isinstance(channel.h5_dataset,np.ndarray):
            assert channel.h5_dataset.size < 10000
        elif Path(channel.h5_dataset.file.filename).resolve() == s.resolve():
            raise AssertionError("Full sample channel read")
        return original(channel,*a,**kw)
    monkeypatch.setattr(nhf_reader.NHFDataset,"read_data",guard)
    assert main(["vea","--sample",str(s),"--calibration",str(c),"--max_count","2",
                 "--crop_area","0,0:1,1","--output",str(tmp_path/"output")]) == 0
    csv, = (tmp_path/"output").glob("*/static_results.csv")
    table = pd.read_csv(csv)
    assert len(table) == 16384
    assert list(table.loc[:1,"static_status"]) == ["success","success"]
    assert (table.loc[2:,"static_status"] == "unprocessed").all()
    assert (table.loc[2:,list(RESULT_COLUMNS)] == 0).all().all()
    assert table.young_modulus_pa.iloc[0] > 0
    assert "Unnamed: 0" not in table.columns
    metadata = json.loads(csv.with_name("run.json").read_text())
    assert metadata["stage"] == "static_and_dynamic_moduli"
    assert metadata["status"] == "success"
    moduli = pd.read_csv(csv.with_name("vea_results.csv"))
    assert len(moduli) == 16384*5
    assert (moduli.loc[:9,"modulus_status"] == "success").all()
    assert np.isfinite(moduli.loc[:9,["storage_modulus_pa","loss_modulus_pa","loss_tangent"]]).all().all()
    assert (moduli.loc[10:,"storage_modulus_pa"] == 0).all()
    assert moduli.young_modulus_pa.iloc[0] == pytest.approx(table.young_modulus_pa.iloc[0])


def test_failed_points_nan_and_status(monkeypatch):
    s,_ = inputs()
    m = load_nhf_file(s)
    def fail(*a,**k):
        raise ValueError("No contact")
    monkeypatch.setattr("nanomech.static.fit_static_point",fail)
    table,status = analyze_static(s,select_sample_points(s,max_count=1),resolve_probe(m,m),StaticConfig())
    assert status == "failed"
    assert table.loc[0,"static_status"] == "failed"
    assert table.loc[0,list(RESULT_COLUMNS)].isna().all()
    assert table.loc[0,"failure_reason"] == "No contact"


def test_invalid_config():
    with pytest.raises(ValueError):
        StaticConfig(tip_radius=0).validate()


def test_hertz_scaled_jacobian():
    from nanomech.nm_models import HertzSphere
    model = HertzSphere(5e-9,.5,residual_scale=1e-9)
    model.param_scales = np.array([1e6,1e-7])
    p = np.array([2.,.1])
    x = np.array([-1e-7,3e-8,8e-8,2e-7])
    y = np.zeros_like(x)
    h = 1e-5
    finite = np.column_stack([(model._residuals_scaled(p+np.eye(2)[i]*h,x,y)
                             -model._residuals_scaled(p-np.eye(2)[i]*h,x,y))/(2*h) for i in range(2)])
    np.testing.assert_allclose(model._jacobian_scaled(p,x,y),finite,rtol=1e-7,atol=1e-8)


@pytest.mark.parametrize("direction,reference",[
    ("Advance",[2312984.9270881447,2544550.338122309]),
    ("Retract",[10439364.64092876,7114202.253799901])])
def test_real_moduli_preserved(direction,reference):
    s,_ = inputs()
    m = load_nhf_file(s)
    table,status = analyze_static(s,select_sample_points(s,max_count=2),resolve_probe(m,m),
                                  StaticConfig(fit_direction=direction))
    assert status == "success"
    np.testing.assert_allclose(table.young_modulus_pa[:2],reference,rtol=1e-6,atol=0)
