"""Plotting helpers extracted from demo_VEA_analysis_v10.

This module centralizes plotting used by the demo script. The public
function `plot_data` keeps the original API but is now annotated and
implemented using smaller helper functions to make testing and reuse
easier.
"""
from __future__ import annotations
from typing import Sequence, Optional
import numpy as np
import matplotlib.pyplot as plt
import logging
logger = logging.getLogger(__name__)

ArrayLike = Sequence[float] | np.ndarray

def _plot_force_spec(x1: ArrayLike, x2: ArrayLike, x3: ArrayLike,
                     y1: ArrayLike, y2: ArrayLike, y3: ArrayLike) -> None:
    """Plot indentation vs. force (force-spectroscopy).

    The function creates a single axis and plots the three provided series.
    """
    logger.info("Force-Spectroscopy plotted.")
    fig, ax = plt.subplots()
    ax.plot(x1, y1)
    ax.plot(x2, y2)
    ax.plot(x3, y3, linestyle='--')
    ax.set_xlabel('Indentation (m)')
    ax.set_ylabel('Force (N)')


def _plot_transient(x1: ArrayLike, x2: ArrayLike, x3: ArrayLike,
                    y1: ArrayLike, y2: ArrayLike, y3: ArrayLike,
                    info: Optional[float]) -> None:
    """Plot time transient: force (left y) and indentation (right y).

    `info` is shown in the printed header and expected to be a frequency
    (but is optional to keep compatibility with callers).
    """
    fig, ax1 = plt.subplots()
    ax1.plot(x1, y1, 'b-', label='Force')
    ax1.plot(x3, y3, 'g-', label='Force')
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Force (N)', color='b')
    ax1.tick_params(axis='y', labelcolor='b')
    ax2 = ax1.twinx()
    ax2.plot(x1, y2, 'r-', label='Indentation')
    ax2.set_ylabel('Indentation (m)', color='r')
    ax2.tick_params(axis='y', labelcolor='r')


def _plot_moduli(x: ArrayLike, storage: ArrayLike, loss: ArrayLike) -> None:
    """Plot storage and loss moduli on log-log frequency axis.
    """
    fig, ax = plt.subplots()
    ax.plot(x, storage, 'b-', label='Storage')
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('Storage Modulus (Pa)', color='b')
    ax.tick_params(axis='y', labelcolor='b')
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.plot(x, loss, 'r-', label='Loss')


def _plot_moduli_tangent(x: ArrayLike, storage: ArrayLike, loss_tan: ArrayLike,
                         loss: ArrayLike) -> None:
    """Plot storage modulus (left y) and loss tangent (right y).
    """
    fig, ax1 = plt.subplots()
    ax1.plot(x, storage, 'b-', label='Storage')
    ax1.plot(x, loss, 'g--', label='Loss')
    ax1.set_xlabel('Frequency (Hz)')
    ax1.set_ylabel('Storage Modulus (Pa)', color='b')
    ax1.tick_params(axis='y', labelcolor='b')
    ax1.set_xscale('log')
    ax2 = ax1.twinx()
    ax2.plot(x, loss_tan, 'r-', label='Loss')
    ax2.set_ylabel('Loss Tangent', color='r')
    ax2.tick_params(axis='y', labelcolor='r')


def plot_data(x1data: ArrayLike, x2data: ArrayLike, x3data: ArrayLike,
              y1data: ArrayLike, y2data: ArrayLike, y3data: ArrayLike,
              plot_type: str, info: Optional[float] = None, show_plot=True) -> None:
    """Create common VEA plots.

    Parameters
    - x1data, x2data, x3data: x-axis data used by the original demo script
      (time, frequency or indentation depending on plot type).
    - y1data, y2data, y3data: y-axis series used by the original demo script.
    - plot_type: one of "ForceSpec", "Transient", "Moduli", "Moduli_Tangent".
    - info: optional, printed for transient plots (frequency).

    The function preserves the original behaviour and calls matplotlib's
    `plt.show()` at the end.
    """
    # Convert simple python lists to numpy arrays for consistent plotting
    # (matplotlib accepts either, but numpy makes some ops predictable).
    x1 = np.asarray(x1data)
    x2 = np.asarray(x2data)
    x3 = np.asarray(x3data)
    y1 = np.asarray(y1data)
    y2 = np.asarray(y2data)
    y3 = np.asarray(y3data)

    if plot_type == "ForceSpec":
        _plot_force_spec(x1, x2, x3, y1, y2, y3)
    elif plot_type == "Transient":
        _plot_transient(x1, x2, x3, y1, y2, y3, info)
    elif plot_type == "Moduli":
        _plot_moduli(x1, y1, y2)
    elif plot_type == "Moduli_Tangent":
        _plot_moduli_tangent(x1, y1, y2, y3)
    else:
        raise ValueError(f"Unknown plot_type: {plot_type!r}")
    logger.info(f"  {plot_type} plotted.")
    if show_plot:
        plt.show()
