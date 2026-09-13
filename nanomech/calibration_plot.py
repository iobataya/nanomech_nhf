"""Headless PNG diagnostics from already fitted calibration data."""
import logging
from pathlib import Path

import numpy as np
from matplotlib import get_data_path
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.text import Text

logger = logging.getLogger(__name__)


def plot_calibration(preparation, output_directory):
    """Save one deflection/time overlay per nominal sweep frequency; never refit."""
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    paths = []
    font_path = Path(get_data_path()) / "fonts" / "ttf" / "DejaVuSans.ttf"
    for index, (frequency, fit, start, end) in enumerate(zip(
            preparation.frequencies_hz, preparation.fits["deflection"],
            preparation.boundaries[:-1], preparation.boundaries[1:])):
        start, end = int(start), int(end)
        time = preparation.time_s[start:end] - preparation.time_s[start]
        data = preparation.deflection_m[start:end]
        margin = int(len(time) * .5 * (1 - .4))
        # Use the same local time origin and phi-1 convention as the solver.
        curve_time = np.linspace(time.min(), time.max(), max(1000, len(time)))
        curve = fit.amplitude * np.sin(2*np.pi*curve_time*fit.frequency_hz + fit.phase_rad - 1) + fit.dc
        figure = Figure(figsize=(10, 5), layout="constrained")
        FigureCanvasAgg(figure)
        ax = figure.subplots()
        ax.plot(time * 1e3, data * 1e9, color="#2463a5", linewidth=.8, label="Measured deflection")
        ax.plot(curve_time * 1e3, curve * 1e9, color="#d14936", linewidth=1.2, label="Sine fit")
        ax.axvspan(time[margin] * 1e3, time[len(time)-margin-1] * 1e3,
                   color="#e4ae35", alpha=.15, label="Fit interval (central 40%)")
        ax.set(title=f"Calibration point 0 | {frequency:.9g} Hz",
               xlabel="Time from frequency segment start (ms)", ylabel="Deflection (nm)")
        ax.grid(alpha=.2)
        ax.legend(loc="upper right")
        # Resolve the bundled font by file, preserving each label's size/style.
        # Materialize tick labels before applying the font; later ticks inherit it.
        ax.get_xticklabels()
        ax.get_yticklabels()
        for label in figure.findobj(match=Text):
            properties = label.get_fontproperties().copy()
            properties.set_file(str(font_path))
            label.set_fontproperties(properties)
        path = output_directory / f"calibration_deflection_{index:03d}_{frequency:.12g}Hz.png"
        try:
            figure.savefig(path, dpi=160)
        finally:
            figure.clear()
        paths.append(path)
        logger.info("Calibration plot saved: %s", path.resolve())
    return tuple(paths)
