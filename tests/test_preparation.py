from pathlib import Path
from types import SimpleNamespace
import logging

import numpy as np
import pytest

from nanomech.nm_io import Attribute, load_nhf_file
from nanomech.calibration import CalibrationInput
from nanomech.preparation import resolve_probe, recalibrate_deflection, prepare_calibration
from nanomech.excitation import demodulate_signal


def measurement(s=None, k=None):
    return SimpleNamespace(attribute={Attribute.SENSITIVITY:s, Attribute.SPRING_CONST:k})


def test_independent_precedence_and_provenance():
    result = resolve_probe(measurement(3,4), measurement(5,6),
                           cli={"sensitivity":1}, config={"sensitivity":9,"spring_constant":2}, config_path="settings.json")
    assert result["sensitivity"].value == 1
    assert result["sensitivity"].source == "CLI"
    assert result["spring_constant"].value == 2
    assert result["spring_constant"].source == "config:settings.json:spring_constant"
    result = resolve_probe(measurement(3,None), measurement(5,6))
    assert result["sensitivity"].value == 3
    assert result["spring_constant"].value == 6
    assert result["spring_constant"].source.startswith("calibration:")


@pytest.mark.parametrize("bad", [0,-1,np.inf,np.nan,True,"1"])
def test_invalid_override_never_falls_back(bad):
    with pytest.raises(ValueError):
        resolve_probe(measurement(3,4), measurement(5,6), cli={"sensitivity":bad})


def test_missing_logs_other_resolved_value(caplog):
    with caplog.at_level(logging.INFO), pytest.raises(ValueError, match="spring_constant"):
        resolve_probe(measurement(3,None), measurement())
    assert "sensitivity=3.0 m/V" in caplog.text
    assert "Missing probe constant: spring_constant" in caplog.text


@pytest.mark.parametrize("unit,raw", [("V",[1.,2.]),("m",[2.,4.]),("N",[6.,12.])])
def test_recalibration_and_force_without_mutation(unit, raw):
    probe = resolve_probe(measurement(5,7), measurement())
    values = np.array(raw)
    d, force = recalibrate_deflection(values, unit,
        {Attribute.SENSITIVITY:2.,Attribute.SPRING_CONST:3.}, probe)
    np.testing.assert_array_equal(d,[5.,10.])
    np.testing.assert_array_equal(force,[35.,70.])
    np.testing.assert_array_equal(values,raw)


def test_stored_constants_required():
    probe = resolve_probe(measurement(5,7), measurement())
    with pytest.raises(KeyError):
        recalibrate_deflection([1],"m",{},probe)
    with pytest.raises(ValueError):
        recalibrate_deflection([1],"unknown",{},probe)


def test_sine_result_contract():
    time = np.linspace(0,.1,1000)
    signal = .7*np.sin(2*np.pi*100*time+.6)+.2
    fit, = demodulate_signal(time,signal,[100],[0,len(time)])
    np.testing.assert_allclose([fit.amplitude,fit.frequency_hz,fit.phase_rad,fit.dc],[.7,100,1.6,.2],rtol=1e-6)
    assert fit.residual_norm < 1e-6


@pytest.mark.parametrize("amplitude", [1e-12, 1e-9, 1.])
def test_normalized_sine_recovers_small_signals(amplitude):
    t = np.linspace(0,.02,1000)
    signal = amplitude*np.sin(2*np.pi*500*t+.6)+.2*amplitude
    fit, = demodulate_signal(t,signal,[500],[0,len(t)])
    np.testing.assert_allclose([fit.amplitude/amplitude,fit.frequency_hz,fit.phase_rad,fit.dc/amplitude],
                               [1.,500,1.6,.2],rtol=1e-6)
    assert fit.residual_norm/amplitude < 1e-6


def test_fixed_drift_analytic_jacobian():
    from nanomech.nm_models import FixedDriftSine
    model = FixedDriftSine(1e-9)
    model.param_scales = np.array([1e-9,500,1,1e-9])
    p = np.array([2.,1.,.6,.2])
    t = np.linspace(0,.02,100)
    y = np.zeros_like(t)
    h = 1e-6
    finite = np.column_stack([(model._residuals_scaled(p+np.eye(4)[i]*h,t,y)
                              -model._residuals_scaled(p-np.eye(4)[i]*h,t,y))/(2*h) for i in range(4)])
    np.testing.assert_allclose(model._jacobian_scaled(p,t,y),finite,rtol=1e-6,atol=1e-7)
    assert model.param_count == 4


def test_real_preparation_logs_all_fits_without_sample_waveforms(monkeypatch, caplog):
    from nanosurf.utils.io import nhf_reader
    directory = Path(__file__).resolve().parents[1]/"test-data-large"
    sample, calibration = directory/"VEA-500-5k-sample.nhf", directory/"VEA-500-5k-calibration.nhf"
    if not sample.exists() or not calibration.exists():
        pytest.skip("Local VEA data unavailable")
    original = nhf_reader.NHFDataset.read_data
    def guarded(channel, *args, **kwargs):
        assert Path(channel.h5_dataset.file.filename).resolve() != sample.resolve(), "Sample waveform loaded"
        return original(channel,*args,**kwargs)
    monkeypatch.setattr(nhf_reader.NHFDataset,"read_data",guarded)
    loaded = CalibrationInput(calibration,"CLI",load_nhf_file(calibration))
    with caplog.at_level(logging.INFO):
        result = prepare_calibration(sample,loaded)
    assert len(result.frequencies_hz) == 5
    assert set(result.fits) == {"deflection","indentation","position_z"}
    records = [r for r in caplog.records if "Calibration fit:" in r.getMessage()]
    assert len(records) == 15
    assert all(r.levelno == logging.INFO for r in records)
    assert result.probe["sensitivity"].source.startswith("sample:")
    for fits in result.fits.values():
        assert all(f.amplitude >= 0 and np.isfinite(f.residual_norm) for f in fits)


def test_failed_calibration_fit_propagates(monkeypatch):
    # Shared demodulation must fail rather than returning successful-looking values.
    monkeypatch.setattr("nanomech.excitation.optimize.least_squares", lambda *a, **k:
                        SimpleNamespace(success=False, x=np.ones(4), message="no convergence"))
    with pytest.raises(ValueError, match="no convergence"):
        demodulate_signal(np.linspace(0,1,100),np.sin(np.linspace(0,10,100)),[5],[0,100])
