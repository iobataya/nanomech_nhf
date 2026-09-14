import numpy as np
import pytest
from nanomech.excitation import demodulate_signal

@pytest.mark.parametrize("ratio",[.94,1.06,.8,1.2])
def test_calibration_rejects_frequency_error(ratio):
    t=np.linspace(0,.1,10000)
    y=2e-9*np.sin(2*np.pi*100*ratio*t+.3)+5e-9
    with pytest.raises(ValueError,match="exceeds 5%"):
        demodulate_signal(t,y,[100],[0,len(t)],frequency_mode="validate")

@pytest.mark.parametrize("ratio",[.95,.98,1.,1.02,1.05])
def test_calibration_refits_at_nhf_frequency(ratio):
    t=np.linspace(0,.1,10000)
    y=2e-9*np.sin(2*np.pi*100*ratio*t+.3)+5e-9
    fit,=demodulate_signal(t,y,[100],[0,len(t)],frequency_mode="validate")
    fixed,=demodulate_signal(t,y,[100],[0,len(t)],frequency_mode="fixed")
    assert fit==fixed
    assert fit.frequency_hz==100

def test_fixed_frequency_recovers_phase_and_amplitude():
    t=np.linspace(0,.1,10000)
    y=2e-9*np.sin(2*np.pi*100*t+.3)+5e-9
    fit,=demodulate_signal(t,y,[100],[0,len(t)],frequency_mode="fixed")
    assert fit.amplitude==pytest.approx(2e-9,rel=1e-10,abs=1e-20)
    assert fit.phase_rad==pytest.approx(1.3)
    assert fit.dc==pytest.approx(5e-9,rel=1e-10,abs=1e-20)
