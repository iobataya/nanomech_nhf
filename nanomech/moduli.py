"""Hertz dynamic moduli from fitted complex responses (legacy VEA equations)."""
import json
import logging
import numpy as np

from nm_io import load_nhf_file, Segment, Attribute
from nm_models import canonical_contact_model

logger = logging.getLogger(__name__)
MODULUS_COLUMNS = ("storage_modulus_pa", "loss_modulus_pa", "loss_tangent")


def excitation_method(sample_path, requested="auto"):
    if requested in ("Piezo", "CleanDrive"):
        return requested
    if requested != "auto":
        raise ValueError("excitation must be auto, Piezo or CleanDrive")
    measurement = load_nhf_file(sample_path)
    properties = json.loads(measurement.segment[Segment.VEA].attribute[Attribute.SEG_CONF])["property"]
    output = properties.get("output_id", {}).get("value")
    # Match the legacy convention, including missing output_id -> Piezo.
    return "CleanDrive" if str(output) == "1" else "Piezo"


def hertz_moduli(ds, ins, dr, ir, indentation_dc, spring_constant, radius, nu,
                  *, excitation="Piezo", correct_drag=True, model="Hertz", cone_half_angle=15.):
    if not all(np.isfinite(v) for v in (ds,ins,dr,ir,indentation_dc,spring_constant,radius,nu)):
        raise ValueError("Nonfinite modulus input")
    if indentation_dc <= 0 or spring_constant <= 0 or radius <= 0 or not -1 < nu <= .5:
        raise ValueError("Invalid indentation DC or contact constants")
    def divide(numerator, denominator, scale):
        if abs(denominator) <= 1e-12 * max(scale, np.finfo(float).tiny):
            raise ValueError("Zero or numerically negligible complex denominator")
        return numerator/denominator
    if excitation == "Piezo":
        response = divide(ds,ins,max(abs(ds),abs(ins)))
        if correct_drag:
            response -= divide(dr,ir,max(abs(dr),abs(ir)))
    elif excitation == "CleanDrive":
        response = divide(dr,ds,max(abs(dr),abs(ds))) - 1
    else:
        raise ValueError("Unsupported excitation method")
    name = canonical_contact_model(model)
    if name in ("Hertz","DMT_Sphere"):
        shear_factor = (1-nu)*spring_constant/(4*np.sqrt(radius)*np.sqrt(indentation_dc))
    else:
        if not np.isfinite(cone_half_angle) or not 0 < cone_half_angle < 90:
            raise ValueError("Invalid cone half angle")
        tangent = np.tan(np.deg2rad(cone_half_angle))
        if name in ("Sneddon","DMT_Cone"):
            shear_factor = (1-nu)*spring_constant*np.pi/(8*tangent*indentation_dc)
        else:
            shear_factor = (1-nu)*spring_constant/(2*np.sqrt(2)*tangent*indentation_dc)
    elastic = 2*(1+nu)*shear_factor*response
    if not np.isfinite(elastic):
        raise ValueError("Nonfinite complex modulus")
    storage,loss = float(elastic.real),float(elastic.imag)
    if abs(storage) <= 1e-12*max(abs(elastic),np.finfo(float).tiny):
        return storage,loss,np.nan,"Loss tangent undefined: zero or negligible storage modulus"
    return storage,loss,loss/storage,""


def calculate_moduli(dynamic_table, static_table, preparation, config, *, excitation="Piezo", correct_drag=True):
    """Keep all point/frequency rows and diagnostics; never refit input data."""
    if type(correct_drag) is not bool:
        raise ValueError("correct_drag must be boolean")
    if excitation not in ("Piezo","CleanDrive"):
        raise ValueError("Unsupported excitation method")
    config.validate()
    table = dynamic_table.copy()
    table["model"] = canonical_contact_model(config.model)
    if "adhesion_parameter_n_per_m" in static_table:
        table["adhesion_parameter_n_per_m"] = table.point_index.map(static_table.set_index("point_index").adhesion_parameter_n_per_m)
    for name in ("young_modulus_pa","contact_point_m","snap_in_force_n","adhesion_force_n"):
        table[name] = table.point_index.map(static_table.set_index("point_index")[name])
    for name in MODULUS_COLUMNS:
        table[name] = 0.
    table["modulus_status"] = "unprocessed"
    table["modulus_failure_reason"] = ""
    table["excitation_method"] = excitation
    table["drag_correction_applied"] = excitation == "Piezo" and correct_drag
    def complex_fit(fit):
        return fit.amplitude*np.exp(1j*fit.phase_rad)
    reference_d = [complex_fit(fit) for fit in preparation.fits["deflection"]]
    reference_i = [complex_fit(fit) for fit in preparation.fits["indentation"]]
    for row in table.itertuples():
        if row.vea_status == "unprocessed":
            continue
        if row.vea_status != "success":
            table.loc[row.Index,list(MODULUS_COLUMNS)] = np.nan
            table.at[row.Index,"modulus_status"] = "skipped_fit_failed"
            table.at[row.Index,"modulus_failure_reason"] = row.failure_reason
            continue
        try:
            j = int(row.frequency_index)
            if row.frequency_hz != preparation.frequencies_hz[j]:
                raise ValueError("Calibration frequency mismatch")
            ds = row.deflection_amplitude_m*np.exp(1j*row.deflection_phase_rad)
            ins = row.indentation_amplitude_m*np.exp(1j*row.indentation_phase_rad)
            storage,loss,tangent,reason = hertz_moduli(ds,ins,reference_d[j],reference_i[j],
                row.indentation_dc_m,preparation.probe["spring_constant"].value,
                config.tip_radius,config.poisson_ratio,excitation=excitation,correct_drag=correct_drag,
                model=config.model,cone_half_angle=config.cone_half_angle)
            table.loc[row.Index,list(MODULUS_COLUMNS)] = [storage,loss,tangent]
            table.at[row.Index,"modulus_status"] = "partial_failure" if reason else "success"
            table.at[row.Index,"modulus_failure_reason"] = reason
            logger.info("Moduli point=%d frequency=%.12g Hz: storage=%.12g Pa loss=%.12g Pa tan_delta=%.12g",
                        row.point_index,row.frequency_hz,storage,loss,tangent)
        except (ValueError,IndexError,ZeroDivisionError,FloatingPointError) as error:
            table.loc[row.Index,list(MODULUS_COLUMNS)] = np.nan
            table.at[row.Index,"modulus_status"] = "failed"
            table.at[row.Index,"modulus_failure_reason"] = str(error)
            logger.warning("Moduli point=%d frequency=%.12g Hz failed: %s",row.point_index,row.frequency_hz,error)
    active = table[table.modulus_status != "unprocessed"].modulus_status
    valid = active.isin(("success","partial_failure"))
    status = "failed" if not valid.any() else "success" if (active == "success").all() else "partial_failure"
    return table,status
