"""Frequency-by-frequency sample VEA sine fits; moduli are a later stage."""
import logging
import numpy as np
import pandas as pd
from types import SimpleNamespace

from nanomech.nm_io import load_nhf_file, Segment, Channel, SweepConfig
from .static import read_point_channel
from .preparation import recalibrate_deflection
from .excitation import demodulate_signal, SineFitResult

logger = logging.getLogger(__name__)
FIT_CHANNELS = ("deflection", "indentation", "position_z")
FIT_FIELDS = ("amplitude_m", "fitted_frequency_hz", "phase_rad", "dc_m", "residual_norm_m")
FIT_COLUMNS = tuple(f"{channel}_{field}" for channel in FIT_CHANNELS for field in FIT_FIELDS)


def fit_dynamic_point(time, raw_deflection, z, meta, deflection_unit, attributes, probe, static_result, frequencies, *, plot_data=None):
    """Fit independent frequency intervals; retain successful channels on failure."""
    n = len(time)
    if n < 3 or any(len(a) != n for a in (raw_deflection,z,meta)):
        raise ValueError("VEA channel lengths do not match")
    if not np.all(np.isfinite(meta)):
        raise ValueError("Nonfinite sampler metadata")
    # Point-local boundaries preserve the calibration/legacy convention.
    boundaries = np.append(np.flatnonzero(np.diff(meta[:-2]) != 0), n-2) + 1
    if len(boundaries) != len(frequencies)+1 or np.any(np.diff(boundaries) <= 0):
        raise ValueError("VEA frequency boundary count does not match sweep")
    rows = []
    if plot_data is not None:
        plot_data.update(time_s=time,deflection_m=np.full(n,np.nan),boundaries=boundaries,
                         frequencies_hz=tuple(frequencies))
    previous_phase = {}
    for f,start,end in zip(frequencies,boundaries[:-1],boundaries[1:]):
        row = dict.fromkeys(FIT_COLUMNS,np.nan)
        errors = []
        try:
            t,zz = time[start:end],z[start:end]
            d,_ = recalibrate_deflection(raw_deflection[start:end],deflection_unit,attributes,probe)
            d = d - (static_result["baseline_slope"]*zz + static_result["baseline_offset_m"])
            if plot_data is not None:
                plot_data["deflection_m"][start:end] = d
            indentation = -(zz+d) - static_result["contact_point_m"]
            signals = dict(deflection=d,indentation=indentation,position_z=zz)
        except (ValueError,RuntimeError) as error:
            errors.append(str(error))
            signals = {}
        for channel in FIT_CHANNELS:
            if channel not in signals:
                row[f"{channel}_status"] = "failed"
                previous_phase.pop(channel,None)
                continue
            try:
                fit, = demodulate_signal(t,signals[channel],[f],[0,len(t)], frequency_mode="fixed")
                phase = fit.phase_rad
                if channel in previous_phase:
                    phase = np.unwrap([previous_phase[channel],phase])[1]
                previous_phase[channel] = phase
                values = (fit.amplitude,fit.frequency_hz,float(phase),fit.dc,fit.residual_norm)
                row.update(zip((f"{channel}_{field}" for field in FIT_FIELDS),values))
                row[f"{channel}_status"] = "success"
                logger.info("Sample VEA fit: frequency_hz=%.12g, channel=%s, amplitude_m=%.12g, fitted_frequency_hz=%.12g, phase_rad=%.12g, dc_m=%.12g, residual_norm_m=%.12g",f,channel,*values)
            except (ValueError,RuntimeError,np.linalg.LinAlgError) as error:
                row[f"{channel}_status"] = "failed"
                previous_phase.pop(channel,None)
                errors.append(f"{channel}: {error}")
        row.update(vea_status="failed" if errors else "success",failure_reason="; ".join(errors))
        rows.append(row)
    if plot_data is not None:
        plot_data["fits"] = {"deflection":tuple(SineFitResult(*(row[f"deflection_{key}"] for key in FIT_FIELDS)) for row in rows)}
    return rows


def analyze_dynamic(sample_path, selection, probe, static_table, frequencies, *, plot_callback=None, max_plot_sample=None):
    measurement = load_nhf_file(sample_path)
    segment = measurement.segment[Segment.VEA]
    required = (Channel.TIME,Channel.DEFLECTION,Channel.Z_POSITION,Channel.SAMPLER_META)
    for name in required:
        segment.channel[name]  # Missing channels abort before processing points.
    if not np.array_equal(SweepConfig(measurement).freq_list,frequencies):
        raise ValueError("Sample sweep differs from prepared calibration frequencies")
    count = len(frequencies)
    table = pd.DataFrame({"point_index":np.repeat(np.arange(selection.total_count),count),
                          "frequency_index":np.tile(np.arange(count),selection.total_count),
                          "frequency_hz":np.tile(frequencies,selection.total_count)})
    for key in ("x_index","y_index","static_status"):
        table[key] = np.repeat(static_table[key].to_numpy(),count)
    for key in FIT_COLUMNS:
        table[key] = 0.
    for key in ("vea_status",*(f"{c}_status" for c in FIT_CHANNELS)):
        table[key] = "unprocessed"
    table["failure_reason"] = ""
    plotted = 0
    for index in selection.point_indices:
        rows = slice(index*count,(index+1)*count-1)
        static_result = static_table.iloc[index]
        if static_result.static_status != "success":
            table.loc[rows,list(FIT_COLUMNS)] = np.nan
            for key in ("vea_status",*(f"{c}_status" for c in FIT_CHANNELS)):
                table.loc[rows,key] = "skipped_static_failed"
            table.loc[rows,"failure_reason"] = str(static_result.failure_reason)
            continue
        logger.info("Sample VEA point=%d",index)
        plot_data = {} if plot_callback is not None and (max_plot_sample is None or plotted < max_plot_sample) else None
        try:
            channels = [read_point_channel(segment,name,index,allow_nonfinite=True) for name in required]
            (time,tu),(raw,du),(z,zu),(meta,_) = channels
            if tu != "s" or zu != "m":
                raise ValueError("VEA Time/Z units must be s/m")
            results = fit_dynamic_point(time,raw,z,meta,du,measurement.attribute,probe,static_result,frequencies,plot_data=plot_data)
            for j,result in enumerate(results):
                for key,value in result.items():
                    table.at[index*count+j,key] = value
        except (ValueError,RuntimeError,np.linalg.LinAlgError) as error:
            table.loc[rows,list(FIT_COLUMNS)] = np.nan
            for key in ("vea_status",*(f"{c}_status" for c in FIT_CHANNELS)):
                table.loc[rows,key] = "failed"
            table.loc[rows,"failure_reason"] = str(error)
            logger.warning("Sample VEA point=%d failed: %s",index,error)
            continue
        if plot_data is not None:
            plot_callback(index,SimpleNamespace(**plot_data))
            plotted += 1
    success = int((table.vea_status == "success").sum())
    status = "failed" if success == 0 else "success" if success == len(selection.point_indices)*count else "partial_failure"
    return table,status
