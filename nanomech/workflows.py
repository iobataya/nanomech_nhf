"""File-to-result services shared by CLI and future GUI."""
from pathlib import Path
import json
import numpy as np
import nanomech.nm_io as nhf
from .excitation import fit_excitation, demodulate_amplitudes


# These workflows accept plain Python requests and never import CLI or Qt code.
from dataclasses import asdict
from datetime import datetime, timezone
from functools import partial
import logging
from uuid import uuid4

from .requests import VeaRequest, ExcitationFitRequest
from .results import VeaResult, ExcitationFitResult
from .selection import select_sample_points
from .calibration import load_calibration
from .preparation import prepare_calibration
from .progress import AnalysisProgress, ProgressCallback

logger = logging.getLogger(__name__)

def excitation_fit(source: Path):
    measurement = nhf.load_nhf_file(source)
    segment = measurement.segment[nhf.Segment.VEA]
    channel = segment.read_channel(nhf.Channel.DEFLECTION)
    offsets, counts = nhf.get_offset_datapoints(segment, channel)
    start, count = int(offsets[0]), int(counts[0])
    signal = np.asarray(channel.dataset[start:start+count], dtype=float).copy()
    if channel.unit == "V":
        scale = float(measurement.attribute[nhf.Attribute.SENSITIVITY])
    elif channel.unit == "N":
        scale = 1 / float(measurement.attribute[nhf.Attribute.SPRING_CONST])
    elif channel.unit == "m":
        scale = 1.
    else:
        raise ValueError(f"Unsupported deflection unit: {channel.unit}")
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("Invalid deflection calibration")
    signal *= scale
    time = segment.read_channel(nhf.Channel.TIME).dataset[start:start+count]
    meta = segment.read_channel(nhf.Channel.SAMPLER_META).dataset[start:start+count]
    if count < 3 or len(signal) != count or len(time) != count or len(meta) != count:
        raise ValueError("Incomplete point-zero waveform")
    # Preserve the legacy point-zero boundary convention, including its terminal exclusion.
    boundaries = np.append(np.where(np.diff(meta[:-2]) != 0)[0], count-2) + 1
    sweep = nhf.SweepConfig(measurement)
    properties = json.loads(segment.attribute[nhf.Attribute.SEG_CONF])["property"]
    lo = float(properties["start_frequency"]["value"])
    hi = float(properties["end_frequency"]["value"])
    if lo <= 0 or hi <= 0:
        raise ValueError("Sweep frequencies must be positive")
    frequencies = (np.linspace(lo, hi, sweep.datapoints) if sweep.sweep_type == 0
                   else np.logspace(np.log10(lo), np.log10(hi), sweep.datapoints))
    if sweep.sweep_direction == 1:
        frequencies = frequencies[::-1]
    amplitudes = demodulate_amplitudes(time, signal, frequencies, boundaries)
    result = fit_excitation(frequencies, amplitudes)
    return result, {"input_amplitude_unit": channel.unit, "calibration_scale": scale}


def run_vea(request: VeaRequest, *, progress_callback: ProgressCallback | None = None) -> VeaResult:
    """Validate, calibrate, analyze and save a VEA run (or preview a dry run).

    A dry run may update the calibration cache. It creates an output directory
    only when calibration plotting is requested. Exceptions propagate to callers.
    Progress callbacks run synchronously in the caller's thread. Point totals
    are per stage and include handled failures/skips, not just successful fits.
    """
    request.validate()
    last_progress = None

    def emit(stage, completed=0, total=None):
        nonlocal last_progress
        if progress_callback is not None:
            event = AnalysisProgress(stage, completed, total)
            if event != last_progress:
                progress_callback(event)
                last_progress = event

    def point_callback(stage):
        return partial(emit, stage) if progress_callback is not None else None

    from .static import analyze_static
    source = request.sample
    static_config = request.static
    limit, crop = request.max_count, request.crop_area
    run = None
    limit_label = "ALL" if limit is None else limit
    crop_label = "ALL" if crop is None else crop
    logger.debug("VEA selection options: crop_area=%s, max_count=%s", crop_label, limit_label)
    emit("selection")
    selection = select_sample_points(Path(source), max_count=limit, crop_area=crop)
    selected_count = len(selection.point_indices)
    emit("calibration", 0, 1)
    calibration = load_calibration(request.calibration)
    preparation = prepare_calibration(Path(source), calibration,
        cli={"sensitivity": request.probe.sensitivity, "spring_constant": request.probe.spring_constant},
        config=asdict(request.probe_config), config_path=request.config_path,
        override_source=request.probe_source)
    emit("calibration", 1, 1)
    if request.plot_calibration or not request.dry_run:
        emit("output_preparation")
        output = Path(request.output)
        run = output / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex)
        run.mkdir(parents=True, exist_ok=False)
        from .config import copy_run_config
        copy_run_config(request.config_path, run)
    if request.plot_calibration:
        emit("calibration_plot")
        from .calibration_plot import plot_calibration
        plot_calibration(preparation, run / "calibration")
    logger.info("VEA selection preview: %d / %d points, map=%dx%d, max_count=%s, crop_area=%s",
                len(selection.point_indices), selection.total_count, selection.width, selection.height, limit_label, crop_label)
    preview = selection.point_indices[:20]
    logger.info("Selected acquisition indices (first 20): %s", list(preview))
    logger.info("Selected XY (first 20): %s", [selection.xy(i) for i in preview])
    if not request.dry_run:
        plot_callback = None
        dynamic_plot_callback = None
        index_digits = len(str(selection.total_count))
        if request.plot_sample:
            from .sample_plot import plot_static_sample, plot_dynamic_sample
            plot_callback = partial(plot_static_sample, run / "sample",index_digits=index_digits)
            dynamic_plot_callback = partial(plot_dynamic_sample, run / "sample",index_digits=index_digits)
        emit("static", 0, selected_count)
        table,status = analyze_static(Path(source),selection,preparation.probe,static_config,
                                     plot_callback=plot_callback, max_plot_sample=request.max_plot_sample,
                                     progress_callback=point_callback("static"))
        emit("save_static")
        table.to_csv(run / "static_results.csv",index=False,na_rep="NaN")
        from .dynamic import analyze_dynamic
        emit("dynamic", 0, selected_count)
        dynamic_table,dynamic_status = analyze_dynamic(Path(source),selection,preparation.probe,
                                                       table,preparation.frequencies_hz,
                                                       plot_callback=dynamic_plot_callback,max_plot_sample=request.max_plot_sample,
                                                       progress_callback=point_callback("dynamic"))
        emit("save_dynamic")
        dynamic_table.to_csv(run / "vea_fit_results.csv",index=False,na_rep="NaN")
        static_status = status
        from .moduli import excitation_method, calculate_moduli
        emit("moduli", 0, selected_count)
        method = excitation_method(Path(source), request.excitation)
        correct_drag = request.correct_drag
        moduli_table,status = calculate_moduli(dynamic_table,table,preparation,static_config,
                                             excitation=method,correct_drag=correct_drag,
                                             progress_callback=point_callback("moduli"))
        emit("save_results")
        moduli_table.to_csv(run / "vea_results.csv",index=False,na_rep="NaN")
        metadata = dict(schema_version=1,command="vea",stage="static_and_dynamic_moduli",status=status,
                        excitation=method,correct_drag=correct_drag,use_reference=False,
                        static_status=static_status,dynamic_status=dynamic_status,
                        sample=str(Path(source).resolve()),calibration=str(calibration.path),
                        calibration_source=calibration.source,static_config=asdict(static_config),
                        probe={key:asdict(value) for key,value in preparation.probe.items()},
                        max_count=limit,crop_area=crop,selected_count=len(selection.point_indices),
                        total_count=selection.total_count,plot_sample=request.plot_sample,
                        max_plot_sample=request.max_plot_sample)
        from .gwyddion import export_gwyddion
        gwy_path = run / (Path(source).stem + "_VEAnalysis.gwy")
        metadata["gwyddion_file"] = gwy_path.name
        export_gwyddion(gwy_path,Path(source),selection,table,moduli_table,preparation.frequencies_hz,metadata)
        (run / "run.json").write_text(json.dumps(metadata,indent=2,allow_nan=False),encoding="utf-8")
        logger.info("Static results saved: %s (status=%s)",run / "static_results.csv",static_status)
        logger.info("VEA fit results saved: %s (status=%s)",run / "vea_fit_results.csv",dynamic_status)
        logger.info("VEA moduli saved: %s (status=%s)",run / "vea_results.csv",status)
        emit("complete", selected_count, selected_count)
        return VeaResult(status, run, selection, preparation, metadata)
    emit("dry_run_complete", 1, 1)
    return VeaResult("success", run, selection, preparation)


def run_excitation_fit(request: ExcitationFitRequest) -> ExcitationFitResult:
    """Fit excitation coefficients and save the result with input provenance."""
    request.validate()
    source, output = Path(request.source), Path(request.output)
    result, provenance = excitation_fit(source)
    run = output / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex)
    run.mkdir(parents=True, exist_ok=False)
    from .config import copy_run_config
    copy_run_config(request.config_path, run)
    metadata = {"schema_version": 1, "command": "excitation-fit", "input": str(source.resolve()),
                "measurement_index": 0, "point_index": 0, "amplitude_unit": "m",
                **provenance,
                "frequency_unit": "Hz", "log_base": 10, "status": "success", **asdict(result)}
    (run / "run.json").write_text(json.dumps(metadata, indent=2, allow_nan=False), encoding="utf-8")
    (run / "excitation_coefficients.json").write_text(
        json.dumps(dict(zip((f"c{i}" for i in range(6)), result.coefficients)), indent=2, allow_nan=False), encoding="utf-8")
    logger.info("%s", run)
    return ExcitationFitResult("success", run, result, metadata)
