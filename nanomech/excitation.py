"""Excitation response fit, using the legacy numerical conventions."""
from dataclasses import dataclass
import logging

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


@dataclass(frozen=True)
class SineFitResult:
    amplitude: float
    frequency_hz: float
    phase_rad: float
    dc: float
    residual_norm: float


def demodulate_signal(time, signal, frequencies, boundaries, *, normalize=True, frequency_mode="free"):
    """Central 40% sine fit; returned phase retains the legacy phi-1 convention.

    ``validate`` estimates frequency in 0.5..1.5 times the NHF frequency and
    rejects relative errors above 5%, then refits at the exact NHF frequency.
    ``fixed`` solves normalized sine/cosine/DC least squares at that frequency.
    Both use FixedDriftSine's zero-drift equation and residual convention.
    The default and unnormalized branch retain the earlier excitation fit.
    """
    if frequency_mode not in ("free", "fixed", "validate"):
        raise ValueError("Unknown frequency mode")
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
        if normalize:
            from nm_models import FixedDriftSine
            scale = initial[0]
            if scale <= 0:
                raise ValueError(f"No oscillation amplitude at {f} Hz")
            if frequency_mode in ("fixed", "validate"):
                def seed(frequency):
                    angle = 2*np.pi*frequency*tf
                    design = np.column_stack((np.sin(angle), np.cos(angle), np.ones_like(tf)))
                    coefficients, _, rank, _ = np.linalg.lstsq(design, yf/scale, rcond=None)
                    if rank < 3:
                        raise ValueError("Rank deficient fixed-frequency sine fit")
                    a, b, dc = coefficients*scale
                    phase = (np.arctan2(b, a)+1) % (2*np.pi)-1
                    return [np.hypot(a,b), frequency, phase, dc], np.linalg.norm(design@coefficients-yf/scale)
                if frequency_mode == "validate":
                    # Search beyond the acceptance interval so mismatches cannot be hidden by bounds.
                    candidates = [seed(candidate) for candidate in np.linspace(.5*f,1.5*f,101)]
                    initial_free, _ = min(candidates, key=lambda item:item[1])
                    model = FixedDriftSine(scale)
                    model.param_scales = np.array([scale,f,1.,max(abs(initial[3]),scale)])
                    model.parameters["init"] = initial_free
                    estimated = model.fit(tf,yf,
                        bounds=([0,.5*f,-np.inf,-np.inf],[np.inf,1.5*f,np.inf,np.inf]),
                        ftol=1e-12,xtol=1e-12,gtol=1e-12)
                    if not model.last_results["raw_result"].success or not np.all(np.isfinite(estimated)):
                        raise ValueError(f"Calibration frequency fit failed at {f} Hz")
                    error = abs(estimated[1]-f)/f
                    logging.getLogger(__name__).info(
                        "Calibration frequency check: NHF=%.12g Hz fitted=%.12g Hz error=%.6g%%",f,estimated[1],100*error)
                    if error > .05 + 1e-12:
                        raise ValueError(f"Calibration frequency error exceeds 5%: NHF={f:.12g} Hz fitted={estimated[1]:.12g} Hz error={100*error:.6g}%")
                # With f and drift fixed, sine/cosine/DC are a linear normalized least-squares problem.
                params, _ = seed(f)
                model = FixedDriftSine(scale)
                residual = model.residuals(params,tf,yf)
                if not np.all(np.isfinite(params)) or params[0] <= 0:
                    raise ValueError(f"Invalid fixed-frequency sine fit at {f} Hz")
                amplitudes.append(SineFitResult(float(params[0]),float(f),float(params[2]+1),
                    float(params[3]),float(np.linalg.norm(residual)*scale)))
                continue
            model = FixedDriftSine(scale)
            model.param_scales = np.array([scale, f, 1., max(abs(initial[3]), scale)])
            model.parameters["init"] = [initial[0], f, initial[2]-1, initial[3]]
            params = model.fit(tf, yf,
                bounds=([0, .999*f, -1, -np.inf], [np.inf, 1.001*f, 2*np.pi-1, np.inf]),
                ftol=1e-12, xtol=1e-12, gtol=1e-12)
            result = model.last_results["raw_result"]
            if not result.success or not np.all(np.isfinite(params)):
                raise ValueError(f"Sine fit failed at {f} Hz: {result.message}")
            amplitudes.append(SineFitResult(float(params[0]), float(params[1]), float(params[2]+1),
                float(params[3]), float(np.linalg.norm(result.fun)*scale)))
            continue
        result = optimize.least_squares(
            lambda p: yf - (p[0]*np.sin(2*np.pi*tf*p[1]+p[2]-1)+p[3]), initial,
            bounds=([0, .999*f, 0, -np.inf], [np.inf, 1.001*f, 2*np.pi, np.inf]),
            gtol=2.23e-16, xtol=2.23e-16,
        )
        if not result.success or not np.all(np.isfinite(result.x)):
            raise ValueError(f"Sine fit failed at {f} Hz: {result.message}")
        amplitudes.append(SineFitResult(*map(float, result.x), float(np.linalg.norm(result.fun))))
    phases = np.unwrap([fit.phase_rad for fit in amplitudes])
    return tuple(SineFitResult(fit.amplitude, fit.frequency_hz, float(phase), fit.dc, fit.residual_norm)
                 for fit, phase in zip(amplitudes, phases))


def demodulate_amplitudes(time, signal, frequencies, boundaries):
    return np.asarray([fit.amplitude for fit in demodulate_signal(time, signal, frequencies, boundaries, normalize=False)])
