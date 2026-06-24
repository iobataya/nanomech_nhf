import os
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Ensure repository root is on sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nm_plot import plot_data

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'figs')

def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)


def save_current_fig(name: str):
    path = os.path.join(OUTPUT_DIR, name)
    plt.savefig(path)
    plt.close()
    return path


def test_plot_force_spec():
    ensure_output_dir()
    x = np.linspace(0, 1, 10)
    y1 = x * 2.0
    y2 = x * 1.5
    y3 = x * 0.5

    name = 'plottest_force_spec.png'
    path = os.path.join(OUTPUT_DIR, name)
    if os.path.exists(path):
        os.remove(path)
    plot_data(x, x, x, y1, y2, y3, 'ForceSpec', None, show_plot=False)
    path = save_current_fig(name)
    assert os.path.exists(path)


def test_plot_transient():
    ensure_output_dir()
    t = np.linspace(0, 0.1, 50)
    force = np.sin(2 * np.pi * 5 * t)
    indent = 0.1 * np.cos(2 * np.pi * 5 * t)

    name = 'plottest_transient.png'
    path = os.path.join(OUTPUT_DIR, name)
    if os.path.exists(path):
        os.remove(path)  # Remove the file to ensure the test checks for creation
    path = save_current_fig(name)
    plot_data(t, t, t, force, indent, force, 'Transient', 5, show_plot=False)
    assert os.path.exists(path)


def test_plot_moduli():
    ensure_output_dir()
    freqs = np.logspace(0, 2, 10)
    storage = freqs ** 0.5
    loss = freqs ** 0.3

    name = 'plottest_moduli.png'
    path = os.path.join(OUTPUT_DIR, name)
    if os.path.exists(path):
        os.remove(path)  # Remove the file to ensure the test checks for creation
    path = save_current_fig(name)
    plot_data(freqs, freqs, freqs, storage, loss, loss, 'Moduli', None, show_plot=False)
    assert os.path.exists(path)


def test_plot_moduli_tangent():
    ensure_output_dir()
    freqs = np.logspace(0, 2, 10)
    storage = freqs ** 0.5
    loss_tan = 0.1 * np.ones_like(freqs)
    loss = freqs ** 0.3

    name = 'plottest_moduli_tangent.png'
    path = os.path.join(OUTPUT_DIR, name)
    if os.path.exists(path):
        os.remove(path)
    plot_data(freqs, freqs, freqs, storage, loss_tan, loss, 'Moduli_Tangent', None, show_plot=False)
    save_current_fig(name)
    assert os.path.exists(path)
