from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest

from nanomech.moduli import hertz_moduli, calculate_moduli
from nanomech.static import StaticConfig
from nanomech.preparation import ProbeValue
from nanomech.excitation import SineFitResult


@pytest.mark.parametrize("method",["Piezo","CleanDrive"])
def test_known_complex_modulus(method):
    target = 2e6 + 3e5j
    k,r,dc,nu = .08,5e-9,100e-9,.5
    # Linearized Hertz contact stiffness is 2 E sqrt(R*dc)/(1-nu^2).
    q = target*2*np.sqrt(r*dc)/(k*(1-nu**2))
    ins,ds,dr,ir = 1e-9,1e-9,1e-9,2e-9
    if method == "Piezo":
        ds = (q+dr/ir)*ins
    else:
        dr = (1+q)*ds
    storage,loss,tangent,reason = hertz_moduli(ds,ins,dr,ir,dc,k,r,nu,excitation=method)
    np.testing.assert_allclose([storage,loss,tangent],[target.real,target.imag,.15],rtol=1e-12)
    assert not reason


def test_no_drag_and_invalid_inputs():
    args = [2e-9+1e-9j,1e-9,1e-9,2e-9,1e-7,.08,5e-9,.5]
    corrected = hertz_moduli(*args)
    uncorrected = hertz_moduli(*args,correct_drag=False)
    assert uncorrected[0] > corrected[0]
    assert uncorrected[1] == corrected[1]
    for index,value in [(1,0),(4,0),(4,-1e-9),(0,np.nan)]:
        invalid = args.copy();invalid[index]=value
        with pytest.raises(ValueError):
            hertz_moduli(*invalid)


def test_zero_storage_preserves_moduli():
    storage,loss,tangent,reason = hertz_moduli(1e-9j,1e-9,0,1e-9,1e-7,.08,5e-9,.5,correct_drag=False)
    assert storage == 0 and loss > 0
    assert np.isnan(tangent) and reason


def test_table_preserves_unprocessed_and_failed():
    frame = pd.DataFrame(dict(point_index=[0,1,2],frequency_index=[0]*3,frequency_hz=[500.]*3,
        vea_status=["success","unprocessed","failed"],failure_reason=["","","bad fit"],
        deflection_amplitude_m=[2e-9,0,np.nan],deflection_phase_rad=[.3,0,np.nan],
        indentation_amplitude_m=[1e-9,0,np.nan],indentation_phase_rad=[0.,0,np.nan],indentation_dc_m=[1e-7,0,np.nan]))
    static = pd.DataFrame(dict(point_index=[0,1,2],young_modulus_pa=[1e6,0,np.nan],contact_point_m=[0.]*3,
                              snap_in_force_n=[0.]*3,adhesion_force_n=[0.]*3))
    fit = SineFitResult(1e-10,500,0,0,0)
    prep = SimpleNamespace(frequencies_hz=(500.,),fits={"deflection":[fit],"indentation":[fit]},
                            probe={"spring_constant":ProbeValue(.08,"N/m","test")})
    result,status = calculate_moduli(frame,static,prep,StaticConfig())
    assert status == "partial_failure"
    assert result.modulus_status.tolist() == ["success","unprocessed","skipped_fit_failed"]
    assert result.storage_modulus_pa.iloc[1] == 0
    assert np.isnan(result.storage_modulus_pa.iloc[2])
    assert result.young_modulus_pa.iloc[0] == 1e6
    assert "storage_modulus_pa" not in frame
