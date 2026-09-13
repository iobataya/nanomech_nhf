"""Excitation response fit, using the legacy numerical conventions."""
from dataclasses import dataclass

import numpy as np
from scipy import optimize


@dataclass(frozen=True)
class ExcitationFitResult:
    coefficients: tuple[float, ...]
    normalization: float
    residual_norm: float
    frequencies_hz: tuple[float, ...]
    normalized_amplitudes: tuple[float, ...]
    solver: str


def polynomial(frequencies, *coefficients):
    x = np.log10(frequencies)
    return sum(c * x**i for i, c in enumerate(coefficients))


def fit_excitation(frequencies, amplitudes) -> ExcitationFitResult:
    """Fit six ascending coefficients to A/max(A) versus log10(f/Hz)."""
    f, a = np.asarray(frequencies, dtype=float), np.asarray(amplitudes, dtype=float)
    if f.ndim != 1 or a.shape != f.shape or len(f) < 6:
        raise ValueError("At least six paired frequency/amplitude values are required")
    if not np.all(np.isfinite(f)) or np.any(f <= 0):
        raise ValueError("Frequencies must be finite and positive")
    if not np.all(np.isfinite(a)) or np.any(a < 0) or a.max() <= 0:
        raise ValueError("Amplitudes must be finite, nonnegative and not all zero")
    design = np.vander(np.log10(f), 6, increasing=True)
    if np.linalg.matrix_rank(design) != 6:
        raise ValueError("Frequency design matrix does not have rank six")
    normalized = a / a.max()
    initial = [1., 0., 0., 0., 0., 0.]
    result = optimize.least_squares(
        lambda c: normalized - polynomial(f, *c), initial,
        xtol=1e-15, ftol=1e-15, gtol=1e-15, max_nfev=10000, method="trf",
    )
    coefficients, solver = result.x, "least_squares"
    if not result.success:
        coefficients, _ = optimize.curve_fit(polynomial, f, normalized, p0=initial, maxfev=5000)
        solver = "curve_fit"
    residual = normalized - polynomial(f, *coefficients)
    if not np.all(np.isfinite(coefficients)) or not np.all(np.isfinite(residual)):
        raise ValueError("Fit produced nonfinite coefficients or residuals")
    return ExcitationFitResult(tuple(map(float, coefficients)), float(a.max()),
                               float(np.linalg.norm(residual)), tuple(f), tuple(normalized), solver)


def demodulate_amplitudes(time, signal, frequencies, boundaries):
    """Legacy sine fit on the central 40%, with phase convention phi-1."""
    time, signal = np.asarray(time), np.asarray(signal)
    bounds = np.asarray(boundaries)
    if time.ndim != 1 or signal.shape != time.shape or not np.all(np.isfinite(time)) or not np.all(np.isfinite(signal)):
        raise ValueError("Time and signal must be paired finite vectors")
    if len(bounds) != len(frequencies) + 1 or np.any(bounds != bounds.astype(int)) or np.any(np.diff(bounds) <= 0) or bounds[0] < 0 or bounds[-1] > len(time):
        raise ValueError("Invalid frequency boundaries")
    amplitudes = []
    for f, start, end in zip(frequencies, bounds[:-1], bounds[1:]):
        if not np.isfinite(f) or f <= 0:
            raise ValueError("Frequency must be finite and positive")
        start, end = int(start), int(end)
        t, y = time[start:end] - time[start], signal[start:end]
        margin = int(len(t) * .5 * (1 - .4))
        fit_time = t[margin:len(t)-margin]
        # NHF timestamps may repeat because of clock quantization.
        if np.unique(fit_time).size < 5 or np.any(np.diff(fit_time) < 0):
            raise ValueError("Sine fit requires at least five distinct, nondecreasing timestamps")
        initial = [(y.max() - y.min()) / 2, f, .9*np.pi, (y.max() + y.min()) / 2]
        tf, yf = t[margin:len(t)-margin], y[margin:len(y)-margin]
        result = optimize.least_squares(
            lambda p: yf - (p[0]*np.sin(2*np.pi*tf*p[1]+p[2]-1)+p[3]), initial,
            bounds=([0, .999*f, 0, -np.inf], [np.inf, 1.001*f, 2*np.pi, np.inf]),
            gtol=2.23e-16, xtol=2.23e-16,
        )
        if not result.success or not np.all(np.isfinite(result.x)):
            raise ValueError(f"Sine fit failed at {f} Hz: {result.message}")
        amplitudes.append(result.x[0])
    return np.asarray(amplitudes)
