"""Resolve probe constants and fit calibration point zero before sample analysis."""
from dataclasses import dataclass
import logging
from pathlib import Path

import numpy as np

from nm_io import load_nhf_file, Attribute, Segment, Channel, SweepConfig, get_offset_datapoints
from .excitation import demodulate_signal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProbeValue:
    value: float
    unit: str
    source: str


def positive(value, name):
    if isinstance(value, (bool, str)):
        raise ValueError(f"{name} must be a positive finite number")
    value = float(value)
    if not np.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive finite number")
    return value


def resolve_probe(sample, calibration, *, cli=None, config=None, sample_path=None,
                  calibration_path=None, config_path=None):
    cli, config = cli or {}, config or {}
    resolved, missing = {}, []
    for name, attribute, unit in (("sensitivity", Attribute.SENSITIVITY, "m/V"),
                                   ("spring_constant", Attribute.SPRING_CONST, "N/m")):
        choices = ((cli, name, "CLI"), (config, name, f"config:{config_path}:{name}"),
                   (sample.attribute, attribute, f"sample:{sample_path}:{attribute}"),
                   (calibration.attribute, attribute, f"calibration:{calibration_path}:{attribute}"))
        for values, key, origin in choices:
            if key in values and values[key] is not None:
                value = positive(values[key], name)
                resolved[name] = ProbeValue(value, unit, origin)
                logger.info("Probe %s=%s %s, source=%s", name, value, unit, origin)
                break
        else:
            missing.append(name)
            logger.error("Missing probe constant: %s", name)
    if missing:
        raise ValueError("Missing probe constants: " + ", ".join(missing))
    return resolved


def recalibrate_deflection(values, unit, attributes, probe):
    """Recover detector volts using stored constants, then apply new sensitivity.

    Saved N = volts * stored sensitivity * stored spring constant.
    The returned displacement is in metres; force uses the resolved spring constant.
    """
    values = np.asarray(values, dtype=float)
    sensitivity = probe["sensitivity"].value
    if unit == "V":
        factor = sensitivity
    elif unit in ("m", "N"):
        factor = sensitivity / positive(attributes[Attribute.SENSITIVITY], "stored sensitivity")
        if unit == "N":
            factor /= positive(attributes[Attribute.SPRING_CONST], "stored spring_constant")
    else:
        raise ValueError(f"Unsupported deflection unit: {unit}")
    displacement = values * factor
    if not np.all(np.isfinite(displacement)):
        raise ValueError("Nonfinite calibrated deflection")
    return displacement, displacement * probe["spring_constant"].value


@dataclass(frozen=True)
class CalibrationPreparation:
    probe: dict
    frequencies_hz: tuple
    fits: dict
    time_s: np.ndarray
    deflection_m: np.ndarray
    boundaries: np.ndarray


def prepare_calibration(sample_path, calibration, *, cli=None, config=None, config_path=None):
    # Metadata only: do not read any sample waveform, regardless of map size.
    sample = load_nhf_file(Path(sample_path))
    measurement = calibration.measurement
    probe = resolve_probe(sample, measurement, cli=cli, config=config,
                          sample_path=Path(sample_path).resolve(), calibration_path=calibration.path,
                          config_path=config_path)
    sweep, sample_sweep = SweepConfig(measurement), SweepConfig(sample)
    for name in ("start_frequency", "end_frequency", "datapoints", "sines_pnts", "sines_number", "sweep_type", "sweep_direction"):
        if getattr(sweep, name) != getattr(sample_sweep, name):
            raise ValueError(f"Calibration/sample sweep mismatch: {name}")
    segment = measurement.segment[Segment.VEA]
    deflection = segment.read_channel(Channel.DEFLECTION)
    offsets, counts = get_offset_datapoints(segment, deflection)
    start, count = int(offsets[0]), int(counts[0])
    if start < 0 or count < 3:
        raise ValueError("Invalid calibration point-zero offsets")
    def point(channel):
        values = np.asarray(channel.dataset[start:start+count], dtype=float)
        if len(values) != count or not np.all(np.isfinite(values)):
            raise ValueError("Incomplete or nonfinite calibration waveform")
        return values
    d, force = recalibrate_deflection(point(deflection), deflection.unit, measurement.attribute, probe)
    time_channel, z_channel = segment.read_channel(Channel.TIME), segment.read_channel(Channel.Z_POSITION)
    if time_channel.unit != "s" or z_channel.unit != "m":
        raise ValueError("Calibration time/Z units must be s/m")
    time, z = point(time_channel), point(z_channel)
    meta = point(segment.read_channel(Channel.SAMPLER_META))
    boundaries = np.append(np.flatnonzero(np.diff(meta[:-2]) != 0), count-2) + 1
    frequencies = tuple(sweep.freq_list)
    fits = {}
    for name, values in (("deflection", d), ("indentation", -(z+d)), ("position_z", z)):
        fits[name] = demodulate_signal(time, values, frequencies, boundaries)
        for frequency, fit in zip(frequencies, fits[name]):
            logger.info("Calibration fit: channel=%s, frequency_hz=%.12g, amplitude_m=%.12g, fitted_frequency_hz=%.12g, phase_rad=%.12g, dc_m=%.12g, residual_norm_m=%.12g",
                        name, frequency, fit.amplitude, fit.frequency_hz, fit.phase_rad, fit.dc, fit.residual_norm)
    return CalibrationPreparation(probe, frequencies, fits, time, d, boundaries)
