from types import SimpleNamespace
from pathlib import Path
import numpy as np
import pytest

from nanomech.dynamic import fit_dynamic_point, analyze_dynamic, FIT_COLUMNS
from nanomech.preparation import ProbeValue, resolve_probe
from nanomech.selection import select_sample_points
from nanomech.static import analyze_static, StaticConfig
from nanomech.nm_io import load_nhf_file


def synthetic():
    frequencies = [500.,1000.]
    local = np.arange(1000)*1e-5
    time = np.r_[0,local+1e-5,local+.01001,.02001]
    meta = np.r_[-1,np.zeros(1000),np.ones(1000),1]
    z = np.r_[0,1e-9*np.sin(2*np.pi*500*local+.3),1e-9*np.sin(2*np.pi*1000*local+.3),0]
    clean = np.r_[0,2e-9*np.sin(2*np.pi*500*local+.6)+.2e-9,
                    2e-9*np.sin(2*np.pi*1000*local+.6)+.2e-9,0]
    raw = clean + .1*z + 1e-9
    probe = {"sensitivity":ProbeValue(1.,"m/V","test"),"spring_constant":ProbeValue(.1,"N/m","test")}
    static = dict(baseline_slope=.1,baseline_offset_m=1e-9,contact_point_m=-10e-9)
    return time,raw,z,meta,"V",{},probe,static,frequencies


def test_known_dynamic_fit_and_static_correction():
    results = fit_dynamic_point(*synthetic())
    for r in results:
        assert r["vea_status"] == "success"
        assert r["deflection_amplitude_m"] == pytest.approx(2e-9,rel=1e-6)
        assert r["deflection_dc_m"] == pytest.approx(.2e-9,abs=1e-15)
        assert r["deflection_phase_rad"] == pytest.approx(1.6,abs=1e-6)
        assert r["indentation_dc_m"] == pytest.approx(9.8e-9,abs=1e-15)


def test_bad_frequency_continues():
    args = list(synthetic())
    args[1][200] = np.nan
    rows = fit_dynamic_point(*args)
    assert rows[0]["vea_status"] == "failed"
    assert np.isnan(rows[0]["deflection_amplitude_m"])
    assert rows[0]["failure_reason"]
    assert rows[1]["vea_status"] == "success"


def test_failed_channel_preserves_others(monkeypatch):
    import nanomech.dynamic as module
    original = module.demodulate_signal
    calls = 0
    def fail_once(*a,**kw):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ValueError("forced fit failure")
        return original(*a,**kw)
    monkeypatch.setattr(module,"demodulate_signal",fail_once)
    rows = fit_dynamic_point(*synthetic())
    assert rows[0]["vea_status"] == "failed"
    assert rows[0]["deflection_status"] == "success"
    assert rows[0]["position_z_status"] == "success"
    assert rows[1]["vea_status"] == "success"


def test_real_map_index_and_static_failure(monkeypatch):
    from nanosurf.utils.io import nhf_reader
    path = Path(__file__).resolve().parents[1]/"test-data-large/VEA-500-5k-sample.nhf"
    if not path.exists():
        pytest.skip("Local VEA sample unavailable")
    m = load_nhf_file(path)
    probe = resolve_probe(m,m)
    selection = select_sample_points(path,max_count=2,crop_area="0,1:1,1")
    table,_ = analyze_static(path,selection,probe,StaticConfig())
    table.loc[254,"static_status"] = "failed"
    table.loc[254,"failure_reason"] = "static failure"
    original = nhf_reader.NHFDataset.read_data
    def guard(channel,*a,**kw):
        assert isinstance(channel.h5_dataset,np.ndarray), "Full waveform loaded"
        return original(channel,*a,**kw)
    monkeypatch.setattr(nhf_reader.NHFDataset,"read_data",guard)
    from nanomech.nm_io import SweepConfig
    result,status = analyze_dynamic(path,selection,probe,table,tuple(SweepConfig(m).freq_list))
    assert len(result) == 16384*5
    assert status == "partial_failure"
    skipped = result[result.point_index == 254]
    assert (skipped.vea_status == "skipped_static_failed").all()
    assert skipped[list(FIT_COLUMNS)].isna().all().all()
    fitted = result[result.point_index == 255]
    assert (fitted.vea_status == "success").all()
    assert list(fitted.frequency_index) == list(range(5))
    assert (fitted.x_index == 0).all() and (fitted.y_index == 1).all()
    untouched = result[result.point_index == 0]
    assert (untouched[list(FIT_COLUMNS)] == 0).all().all()
