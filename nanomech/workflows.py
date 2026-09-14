"""File-to-result services shared by CLI and future GUI."""
from pathlib import Path
import json
import numpy as np
import nanomech.nm_io as nhf
from .excitation import fit_excitation, demodulate_amplitudes


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
