# nanomech.nm_models.Sine calibration verification

Date: 2026-09-14. Production fitting code was not changed.

Input: `test-data-large/VEA-500-5k-calibration.nhf`, first measurement, point 0.
Probe constants are resolved using `VEA-500-5k-sample.nhf` as in the current
preparation workflow. Five frequencies and three channels (deflection,
indentation, position_z) were tested. Full numerical results are in
`sine-calibration-comparison.csv`.

All comparisons use the same frequency boundaries, local time origin and central
40% samples as current preparation. The old phase is translated to the Sine
convention with `phase_new = phase_old - 1`; phase differences are wrapped to
[-pi, pi]. Frequency bounds remain 0.999 to 1.001 times nominal; amplitude is
nonnegative. Initial values use half the full segment peak-to-peak amplitude,
nominal frequency, phase `0.9*pi-1`, zero drift and midrange offset. Tests do not
use Sine's default FFT initializer.

The prototype subclasses Sine and calls its inherited `fit`, scaled-parameter
machinery and analytic Jacobian. Parameter scales are signal amplitude, nominal
frequency, 1 rad, amplitude/fit duration, and max(abs(offset), amplitude).
Normalized variants divide both residuals and Jacobian by signal amplitude.
Solver tolerances ftol/xtol/gtol are 1e-12. The no-drift variant removes the drift
parameter from optimization, expands it as zero for Sine evaluation, and selects
the corresponding four Jacobian columns; it does not approximate fixed drift
with narrow bounds.

| Variant | Results |
| --- | --- |
| Parameter scaling only | Reports success in 15/15, but deflection fits stop at one function evaluation and have 2.03–6.87 times the current residual norm. Success flag alone is insufficient. |
| Residual normalization, free drift | Converges in 15/15. Deflection amplitude differences stay below 0.137%, but position_z differs by as much as 27.32% (500 Hz). Drift changes the model. |
| Residual normalization, drift fixed at zero | Converges in 15/15. Maximum amplitude difference from current preparation is 0.00008328%; maximum absolute wrapped phase difference is 0.0009767 rad. |

The scaled analytic Jacobian was checked against central differences of scaled
parameters with step 1e-6 at all fitted solutions. Maximum absolute matrix error
divided by maximum absolute analytic element was below 5.1e-10 across all variants.
This validates the derivatives on these inputs; it is not a performance benchmark
or proof of physical accuracy. Comparison reference is the current preparation
fitter, not archived legacy CSV results (which do not contain these calibration fits).

Conclusion: Sine is reusable with signal residual normalization, explicit initial
values/bounds and phase conversion. A fixed-drift option is required to preserve
the existing four-parameter model. Integrating free drift is a separate modeling
decision, especially for the small Z response. Neither variant has been adopted
in production by this verification.
