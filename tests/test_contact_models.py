import numpy as np
import pytest

from nanomech.nm_models import CONTACT_MODELS, create_contact_model
from nanomech.static import StaticConfig,fit_contact


def curve(name,x,e=2e6,gamma=1e-4):
    d=np.maximum(x,0);r=5e-9;nu=.5;t=np.tan(np.deg2rad(15))
    if name in ("Hertz","DMT_Sphere"):
        force=4*e*np.sqrt(r)*d**1.5/(3*(1-nu**2))
        if name=="DMT_Sphere":force-=2*np.pi*r*gamma
    else:
        coefficient={"Sneddon":2/np.pi,"Pyramid":1/np.sqrt(2),"DMT_Cone":1}[name]
        force=coefficient*e*t*d**2/(1-nu**2)
        if name=="DMT_Cone":force-=2*np.pi*gamma*d/t
    return np.where(x>0,force,0)


@pytest.mark.parametrize("name",CONTACT_MODELS)
@pytest.mark.parametrize("reverse",[False,True])
def test_equation_jacobian_and_recovery(name,reverse):
    x=np.linspace(-100e-9,200e-9,800)
    if reverse: x=x[::-1]
    model=create_contact_model(name,5e-9,.5,residual_scale=1e-9)
    p=np.array([2e6,0]+([1e-4] if model.param_count==3 else []))
    np.testing.assert_allclose(model.evaluate(p,x),curve(name,x),rtol=1e-12,atol=1e-24)
    model.param_scales=np.array([1e6,1e-7]+([1e-4] if model.param_count==3 else []))
    scaled=p/model.param_scales;h=1e-6
    finite=np.column_stack([(model._residuals_scaled(scaled+np.eye(len(p))[i]*h,x,np.zeros_like(x))-
                            model._residuals_scaled(scaled-np.eye(len(p))[i]*h,x,np.zeros_like(x)))/(2*h) for i in range(len(p))])
    np.testing.assert_allclose(model._jacobian_scaled(scaled,x,x*0),finite,rtol=1e-6,atol=1e-7)
    result=fit_contact(x,curve(name,x),StaticConfig(model=name))
    assert result["young_modulus_pa"]==pytest.approx(2e6,rel=.01)
    assert result["contact_point_m"]==pytest.approx(0,abs=1e-10)
    if model.param_count==3:
        assert result["adhesion_parameter_n_per_m"]==pytest.approx(1e-4,rel=.01)


def test_case_alias_and_invalid_model():
    assert create_contact_model("DMT_sphere",5e-9,.5).name=="DMT_Sphere"
    with pytest.raises(ValueError): StaticConfig(model="unknown").validate()


def test_cli_model_output(tmp_path,monkeypatch):
    from pathlib import Path
    import pandas as pd
    from nanomech import calibration
    from nanomech.cli import main
    root=Path(__file__).resolve().parents[1]/"test-data-large"
    sample,cal=root/"VEA-500-5k-sample.nhf",root/"VEA-500-5k-calibration.nhf"
    if not sample.exists() or not cal.exists(): pytest.skip("Local VEA data unavailable")
    monkeypatch.setattr(calibration,"SCRIPT_DIRECTORY",tmp_path)
    assert main(["vea","--sample",str(sample),"--calibration",str(cal),"--model","DMT_sphere",
                 "--max_count","1","--output",str(tmp_path/"out"),"--plot-sample"])==0
    csv,=(tmp_path/"out").glob("*/static_results.csv")
    table=pd.read_csv(csv)
    assert table.model.iloc[0]=="DMT_Sphere"
    assert table.adhesion_parameter_n_per_m.iloc[0]>0
    assert list((csv.parent/"sample").glob("*_DMT_Sphere_advance.png"))


@pytest.mark.parametrize("name",CONTACT_MODELS)
def test_dynamic_geometry(name):
    from nanomech.moduli import hertz_moduli
    dc,k,r,nu=1e-7,.08,5e-9,.5
    t=np.tan(np.deg2rad(15))
    if name in ("Hertz","DMT_Sphere"):
        expected=(1-nu**2)*k/(2*np.sqrt(r*dc))
    elif name in ("Sneddon","DMT_Cone"):
        expected=(1-nu**2)*k*np.pi/(4*t*dc)
    else:
        expected=(1-nu**2)*k/(np.sqrt(2)*t*dc)
    storage,loss,_,_=hertz_moduli(1e-9,1e-9,0.,1e-9,dc,k,r,nu,model=name,correct_drag=False)
    assert storage==pytest.approx(expected)
    assert loss==0
