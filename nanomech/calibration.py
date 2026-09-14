"""Resolve and retain the last successfully opened VEA calibration file."""
from dataclasses import dataclass
import logging
from pathlib import Path
import shutil
import tempfile

from nanomech.nm_io import load_nhf_file, Segment, Channel

logger = logging.getLogger(__name__)
# main.py lives beside the nanomech package; this is independent of cwd.
SCRIPT_DIRECTORY = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class CalibrationInput:
    path: Path
    source: str
    measurement: object


def load_calibration(explicit_path=None):
    """Explicit input never falls back; cache only after successful validation.

    Opening NHF metadata does not load waveform arrays. The returned first
    measurement is retained for subsequent point-zero numerical analysis.
    """
    cache = SCRIPT_DIRECTORY / ".last_calibration.nhf"
    source = "CLI" if explicit_path is not None else "cache"
    path = Path(explicit_path).resolve() if explicit_path is not None else cache.resolve()
    logger.debug("Calibration selected: source=%s, path=%s", source, path)
    if not path.is_file():
        raise FileNotFoundError(f"Calibration file not found ({source}): {path}")
    measurement = load_nhf_file(path)
    size = measurement.attribute.get("rect_axis_size")
    if size is None or len(size) != 2 or any(value <= 0 for value in size):
        raise ValueError(f"Calibration first measurement has no valid points: {path}")
    segment = measurement.segment[Segment.VEA]
    for name in (Channel.DEFLECTION, Channel.TIME, Channel.Z_POSITION, Channel.SAMPLER_META):
        if segment.channel[name].h5_dataset.size == 0:
            raise ValueError(f"Calibration channel is empty: {name}")
    if explicit_path is not None and path != cache.resolve():
        # Write next to the destination and replace atomically, preserving the
        # previous cache if reading or copying the new file fails.
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=SCRIPT_DIRECTORY, prefix=".last_calibration.", suffix=".tmp", delete=False) as handle:
                temporary = Path(handle.name)
                with path.open("rb") as original:
                    shutil.copyfileobj(original, handle)
            temporary.replace(cache)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        logger.debug("Calibration cache updated: %s", cache)
    logger.debug("Calibration loaded: source=%s, path=%s, measurement_index=0, point_index=0", source, path)
    return CalibrationInput(path, source, measurement)
