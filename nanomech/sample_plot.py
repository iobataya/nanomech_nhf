"""Per-point static force/indentation PNGs, using existing fit results."""
import logging
from pathlib import Path

import numpy as np
from matplotlib import get_data_path
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.text import Text
from nm_models import HertzSphere

logger = logging.getLogger(__name__)


def sample_plot_filename(point_index, model, segment, index_digits=5):
    return f"sample_point{point_index:0{index_digits}d}_{model}_{segment}.png"


def plot_dynamic_sample(output_directory, point_index, preparation, *, index_digits=5):
    from .calibration_plot import plot_calibration
    return plot_calibration(preparation,output_directory,
        filename=sample_plot_filename(point_index,"sine","VEA",index_digits),
        title=f"Sample point {point_index} | sine | VEA")


def plot_static_sample(output_directory, point_index, indentation, force, result, config, *, index_digits=5):
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    model_name = "Hertz"
    path = directory / sample_plot_filename(point_index,model_name,config.fit_direction.lower(),index_digits)
    x = np.linspace(np.min(indentation), np.max(indentation), 1000)
    model = HertzSphere(config.tip_radius, config.poisson_ratio)
    y = model.evaluate([result["young_modulus_pa"], result["contact_point_m"]], x)
    figure = Figure(figsize=(10,6), layout="constrained")
    FigureCanvasAgg(figure)
    ax = figure.subplots()
    ax.plot(np.asarray(indentation)*1e9, np.asarray(force)*1e9,
            color="#2463a5", linewidth=.9, label="Measured force")
    ax.plot(x*1e9, y*1e9, color="#d14936", linewidth=1.5, label="Hertz fit")
    ax.set(xlabel="Indentation (nm)", ylabel="Force (nN)",
           title=f"Sample point {point_index} | {model_name} | {config.fit_direction}")
    ax.grid(alpha=.2)
    ax.legend(loc="upper left")
    # Put results below the axes to keep the data unobscured.
    figure.supxlabel(
        f"Young's modulus = {result['young_modulus_pa']/1e6:.6g} MPa    "
        f"Contact point = {result['contact_point_m']*1e9:.6g} nm\n"
        f"Residual norm = {result['residual_norm_n']*1e9:.6g} nN    "
        f"R = {config.tip_radius*1e9:.6g} nm    Poisson ratio = {config.poisson_ratio:.4g}\n"
        "Fit uses positive-force samples; indentation retains the fitted contact offset.",
        fontsize=10)
    ax.get_xticklabels()
    ax.get_yticklabels()
    font = str(Path(get_data_path()) / "fonts/ttf/DejaVuSans.ttf")
    for text in figure.findobj(match=Text):
        properties = text.get_fontproperties().copy()
        properties.set_file(font)
        text.set_fontproperties(properties)
    try:
        figure.savefig(path,dpi=160)
    finally:
        figure.clear()
    logger.info("Sample plot saved: %s",path.resolve())
    return path
