"""Pointwise static Hertz fitting in SI units and one-row-per-point output."""
from copy import copy
from dataclasses import dataclass
import logging

import numpy as np
import pandas as pd
from nanomech.nm_models import HertzSphere, create_contact_model, canonical_contact_model

from nanomech.nm_io import load_nhf_file, Segment, Channel, get_offset_datapoints
from .preparation import recalibrate_deflection, positive
from .progress import iter_progress

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StaticConfig:
    model: str = "Hertz"
    cone_half_angle: float = 15.
    fit_direction: str = "Advance"
    tip_radius: float = 5e-9
    poisson_ratio: float = .5
    baseline_start: float = .05
    baseline_end: float = .5

    def validate(self):
        canonical_contact_model(self.model)
        if not np.isfinite(self.cone_half_angle) or not 0 < self.cone_half_angle < 90:
            raise ValueError("cone_half_angle must be between 0 and 90 degrees")
        if self.fit_direction not in ("Advance", "Retract"):
            raise ValueError("fit_direction must be Advance or Retract")
        positive(self.tip_radius, "tip_radius")
        if not np.isfinite(self.poisson_ratio) or not -1 < self.poisson_ratio <= .5:
            raise ValueError("poisson_ratio must be in (-1, 0.5]")
        if not 0 <= self.baseline_start < self.baseline_end <= 1:
            raise ValueError("baseline range must satisfy 0 <= start < end <= 1")


def read_point_channel(segment, name, index, *, allow_nonfinite=False):
    """Slice raw storage first; use Nanosurf's calibration on the copied channel.

    Keeps the source NHFDataset and its cache unchanged. Only point-sized raw
    arrays reach read_data; offsets/count metadata are small per-point arrays.
    """
    original = segment.channel[name]
    offsets, counts = get_offset_datapoints(segment, original)
    start, count = int(offsets[index]), int(counts[index])
    if start < 0 or count < 3 or start + count > original.h5_dataset.size:
        raise ValueError(f"Invalid point data bounds for {name}")
    channel = copy(original)
    channel.attribute = original.attribute.copy()
    channel.h5_dataset = original.h5_dataset[start:start+count]
    channel.dataset = channel.h5_dataset
    channel.cached_signal_id = object()
    channel.read_data()
    values = np.asarray(channel.get_masked_dataset().filled(np.nan), dtype=float)
    if values.ndim != 1 or (not allow_nonfinite and not np.all(np.isfinite(values))):
        raise ValueError(f"Nonfinite or invalid {name} waveform")
    return values, channel.unit


def fit_hertz(indentation, force, radius, poisson_ratio):
    """Fit E and contact position with scaled residuals/parameters; ignore adhesion."""
    x, y = np.asarray(indentation), np.asarray(force)
    if x.shape != y.shape or x.ndim != 1 or not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError("Invalid indentation/force arrays")
    keep = y > 0
    if keep.sum() < 5 or np.ptp(x[keep]) <= 0 or np.max(y) <= 0:
        raise ValueError("Insufficient positive-force contact data")
    lo, span, scale = float(x.min()), float(np.ptp(x)), float(y.max())
    coefficient = 4*np.sqrt(radius)/(3*(1-poisson_ratio**2))
    e_scale = scale/(coefficient*span**1.5)
    model = HertzSphere(radius, poisson_ratio, residual_scale=scale)
    model.param_scales = np.array([e_scale, span])
    # Shift contact coordinates by lo; bounds and initialization match the
    # previous dimensionless implementation, while the model receives SI units.
    model.parameters["init"] = [np.clip(e_scale, 1., 1e12), .25*span]
    params = model.fit(x[keep]-lo, y[keep], bounds=([1.,0.],[1e12,span]),
                       xtol=1e-12, ftol=1e-12, gtol=1e-12, max_nfev=2000)
    result = model.last_results["raw_result"]
    if not result.success or np.linalg.matrix_rank(result.jac) < 2 or not np.all(np.isfinite(result.x)):
        raise ValueError(f"Hertz fit failed: {result.message}")
    return {"young_modulus_pa":float(params[0]),
            "contact_point_m":float(lo+params[1]),
            "residual_norm_n":float(np.linalg.norm(result.fun)*scale)}


def fit_contact(indentation,force,config):
    name = canonical_contact_model(config.model)
    if name == "Hertz":
        return dict(fit_hertz(indentation,force,config.tip_radius,config.poisson_ratio),adhesion_parameter_n_per_m=0.)
    x,y = np.asarray(indentation),np.asarray(force)
    if x.ndim != 1 or x.shape != y.shape or len(x)<6 or not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError("Invalid contact curve")
    lo,span,scale = float(x.min()),float(np.ptp(x)),float(np.max(np.abs(y)))
    if span <= 0 or scale <= 0 or np.count_nonzero(y>0)<5:
        raise ValueError("Insufficient contact data")
    model = create_contact_model(name,config.tip_radius,config.poisson_ratio,config.cone_half_angle,scale)
    adhesive = model.param_count == 3
    keep = np.ones(len(x),dtype=bool) if adhesive else y>0
    e_scale = scale/(model.coefficient*span**model.power)
    scales = [e_scale,span]
    lower,upper = [1.,0.],[1e12,span]
    if adhesive:
        gamma_scale = scale/(model.adhesion_coefficient*span**model.adhesion_power)
        scales.append(gamma_scale)
        lower.append(0.);upper.append(100.)
    model.param_scales = np.asarray(scales)
    candidates = []
    # DMT contact introduces a kink/discontinuity. Multiple starts reduce
    # sensitivity to the unknown contact location; full residuals keep the
    # optimizer from reducing error by excluding data as contact moves.
    for fraction in ((.1,.25,.5,.7,.85,.95) if adhesive else (.25,)):
        initial = [np.clip(e_scale,1,1e12),fraction*span]
        if adhesive:
            initial.append(min(gamma_scale,50.))
        model.parameters["init"] = initial
        params = model.fit(x[keep]-lo,y[keep],bounds=(lower,upper),
                           ftol=1e-12,xtol=1e-12,gtol=1e-12,max_nfev=2000)
        result = model.last_results["raw_result"]
        if result.success and np.all(np.isfinite(params)) and np.linalg.matrix_rank(result.jac)==model.param_count:
            candidates.append((float(np.linalg.norm(result.fun)),params.copy()))
    if not candidates:
        raise ValueError(f"{name} fit failed or is unidentifiable")
    residual,params = min(candidates,key=lambda item:item[0])
    return dict(young_modulus_pa=float(params[0]),contact_point_m=float(lo+params[1]),
                adhesion_parameter_n_per_m=float(params[2]) if adhesive else 0.,residual_norm_n=residual*scale)


def fit_static_point(advance_z, advance_d, retract_z, retract_d, spring_constant, config, *, plot_data=None):
    config.validate()
    start, end = int(len(advance_z)*config.baseline_start), int(len(advance_z)*config.baseline_end)
    if end-start < 3 or np.ptp(advance_z[start:end]) <= 0:
        raise ValueError("Insufficient baseline data")
    # Center the baseline coordinates for a well-conditioned linear regression.
    origin = advance_z[start:end].mean()
    span = np.ptp(advance_z[start:end])
    design = np.column_stack(((advance_z[start:end]-origin)/span,np.ones(end-start)))
    slope_scaled, intercept = np.linalg.lstsq(design,advance_d[start:end],rcond=None)[0]
    slope = slope_scaled/span
    ad = advance_d - (slope*(advance_z-origin)+intercept)
    rd = retract_d - (slope*(retract_z-origin)+intercept)
    z,d = (advance_z,ad) if config.fit_direction == "Advance" else (retract_z,rd)
    result = fit_contact(-(z+d),d*spring_constant,config)
    result.update(snap_in_force_n=float(np.min(ad)*spring_constant),
                  adhesion_force_n=float(np.min(rd)*spring_constant),
                  baseline_slope=float(slope), baseline_offset_m=float(intercept-slope*origin))
    if plot_data is not None:
        plot_data.update(indentation=-(z+d), force=d*spring_constant)
    return result


RESULT_COLUMNS = ("young_modulus_pa","contact_point_m","adhesion_parameter_n_per_m","residual_norm_n","snap_in_force_n",
                  "adhesion_force_n","baseline_slope","baseline_offset_m")


def analyze_static(sample_path, selection, probe, config, *, plot_callback=None, max_plot_sample=None,
                   progress_callback=None):
    config.validate()
    if max_plot_sample is not None and (isinstance(max_plot_sample, bool) or
            not isinstance(max_plot_sample, (int, np.integer)) or max_plot_sample < 0):
        raise ValueError("max_plot_sample must be a nonnegative integer")
    measurement = load_nhf_file(sample_path)
    # Missing required segments/channels abort the run, not individual points.
    for name in (Segment.ADVANCE, Segment.RETRACT):
        for channel in (Channel.DEFLECTION,Channel.Z_POSITION):
            measurement.segment[name].channel[channel]
    records = []
    for index in range(selection.total_count):
        x,y = selection.xy(index)
        records.append(dict(point_index=index,x_index=x,y_index=y,model=canonical_contact_model(config.model),
                            fit_direction=config.fit_direction,static_status="unprocessed",failure_reason="",
                            **dict.fromkeys(RESULT_COLUMNS,0.)))
    plotted = 0
    for index in iter_progress(selection.point_indices, progress_callback):
        plot_data = {} if plot_callback is not None and (max_plot_sample is None or plotted < max_plot_sample) else None
        try:
            waves = []
            for name in (Segment.ADVANCE,Segment.RETRACT):
                segment = measurement.segment[name]
                z,unit = read_point_channel(segment,Channel.Z_POSITION,index)
                if unit != "m":
                    raise ValueError("Position Z must be in metres")
                raw,unit = read_point_channel(segment,Channel.DEFLECTION,index)
                d,_ = recalibrate_deflection(raw,unit,measurement.attribute,probe)
                if len(z) != len(d):
                    raise ValueError("Z/deflection length mismatch")
                waves.extend((z,d))
            result = fit_static_point(*waves,probe["spring_constant"].value,config,plot_data=plot_data)
            records[index].update(result,static_status="success")
            logger.info("Static point=%d: Young modulus=%.12g Pa, contact=%.12g m",index,result["young_modulus_pa"],result["contact_point_m"])
        except (ValueError, RuntimeError, np.linalg.LinAlgError) as error:
            records[index].update(dict.fromkeys(RESULT_COLUMNS,np.nan),static_status="failed",failure_reason=str(error))
            logger.warning("Static point=%d failed: %s",index,error)
            continue
        # Plot I/O errors must not relabel successful fits as failed fits.
        if plot_data is not None:
            plot_callback(index, plot_data["indentation"], plot_data["force"], result, config)
            plotted += 1
    table = pd.DataFrame.from_records(records)
    successes = int((table.static_status == "success").sum())
    status = "failed" if successes == 0 else "success" if successes == len(selection.point_indices) else "partial_failure"
    return table,status
