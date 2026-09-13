import numpy as np
import scipy.optimize as opt
import logging
logger = logging.getLogger(__name__)

class NanomechModel:
    """Base class for nanomechanical models."""

    def __init__(self, name: str, parameters: dict=None, constants: dict=None, scale_factors: dict=None):
        self.name = name
        self.parameters = parameters
        self.param_count = len(parameters["name"]) if parameters else 0
        self.constants = constants if constants is not None else {}
        self.param_scales = np.ones(self.param_count) if self.param_count > 0 else np.array([1.0])

        # Default scaling coefficient. (1.0 = no normalizing). Overwrite in subclasses if needed.
        if scale_factors is not None:
            for i, scale in enumerate(scale_factors.get("name", [])):
                self.param_scales[i] = scale

    def evaluate(self, params, x):
        pass
    def jacobian(self, params, x, _):
        pass
    def residuals(self, params, x, y):
        pass

    def estimate_initial_params(self, x, y):
        """
        Estimate initial parameters p0 for fitting. This method should be overridden in subclasses.
        If the user has provided manual initial values in self.parameters["init"], those values will be used directly.
        """
        return self._map_manual_initial_params()

    def _map_manual_initial_params(self, initial_params=None):
        """
        Map manual initial parameters provided in self.parameters["init"] to the initial parameter list.
        """
        if initial_params is None:
            initial_params = np.array([1.0] * self.param_count, dtype=np.float64)
        if self.param_count != len(initial_params):
            raise ValueError(f"Length of manual initial parameters {len(self.parameters.get('init', []))} does not match the number of model parameters {self.param_count}.")
        if self.parameters.get("init") is None:
            return initial_params
        # Overwrite initial parameters with user-provided values
        for i, manual_val in enumerate(self.parameters.get("init", [])):
            if manual_val is not None:
                initial_params[i] = manual_val  # overwrite with user-provided value
        return initial_params

    def fit(self, x, y, bounds=None, ftol=1e-8, xtol=1e-8, gtol=1e-8, method='trf', max_nfev=None):
        """
        Method to fit the model to data (x, y) using least squares optimization.
        This method handles normalization, fitting, and unit restoration internally.
        """
        # 1. Obtaining initial parameter estimates in physical units
        initial_params_physical = self.estimate_initial_params(x, y)
        logger.debug(f"Initial parameters in physical units: {initial_params_physical}")

        # 2. Normalizing parameters for internal optimization (physical units / scale factors)
        initial_guess_scaled = self._physical_params_to_scaled(initial_params_physical)
        logger.debug(f"Initial parameters scaled for optimization: {initial_guess_scaled}")
        
        # 3. If bounds are specified, normalize them for internal use
        scaled_bounds = (-np.inf, np.inf)
        if bounds is not None:
            lower, upper = bounds
            if len(lower) != self.param_count or len(upper) != self.param_count:
                raise ValueError("Bounds must have the same length as the number of model parameters.")
            scaled_lower = np.array(lower) / self.param_scales
            scaled_upper = np.array(upper) / self.param_scales
            scaled_bounds = (scaled_lower, scaled_upper)
            
        # 4. Perform optimization (calls internal residuals and jacobian)
        result = opt.least_squares(
            fun=self._residuals_scaled,
            x0=initial_guess_scaled,
            jac=self._jacobian_scaled,
            bounds=scaled_bounds,
            args=(x, y),
            ftol=ftol,
            xtol=xtol,
            gtol=gtol,
            method=method,
            max_nfev=max_nfev,
        )
        
        # 5. Restoring the obtained internal parameters to physical units
        logger.debug(f"Optimization result: {result.x}")
        fitted_params_physical = self._scaled_params_to_physical(result.x)
        logger.debug(f"Rescaled fitted parameters to physical units: {fitted_params_physical}")
        
        # 6. Save and return the results in a dictionary format
        self.last_results = {
            "success": result.success,
            "params": fitted_params_physical,
            "message": result.message,
            "raw_result": result
        }
        return fitted_params_physical

    # --- Internal wrapper methods (not visible or accessible from outside) ---
    def _physical_params_to_scaled(self, physical_params):
        """Scale raw physical parameters to scaled parameters for internal optimization."""
        return physical_params / self.param_scales

    def _scaled_params_to_physical(self, scaled_params):
        """Unscale scaled parameters back to physical parameters after optimization."""
        return scaled_params * self.param_scales

    def _residuals_scaled(self, scaled_params, x, y):
        # Convert internal scaled parameters back to physical units before computing residuals.
        physical_params = self._scaled_params_to_physical(scaled_params)
        return self.residuals(physical_params, x, y)

    def _jacobian_scaled(self, scaled_params, x, y_):
        # Chain rule for p_phys = p_scaled * scale: J_scaled = J_phys * diag(scale).
        physical_params = self._scaled_params_to_physical(scaled_params)
        jac_phys = self.jacobian(physical_params, x, y_)
        return jac_phys * self.param_scales

class Linear(NanomechModel):
    """A simple linear model"""
    def __init__(self, name="Linear"):
        super().__init__(
            name, 
            parameters={
                "name":["slope","intercept"], 
                "abbrev":["a","b"],
             })
        
    def evaluate(self, params, x):
        """Fit the linear model to the data."""
        a, b = params
        return a * x + b

    def residuals(self, params, x, y):
        """Compute the residuals for the linear model."""
        return y - self.evaluate(params, x)

    def jacobian(self, params, x, _):
        """Compute the Jacobian matrix for the linear model."""
        jacobian = np.zeros((len(x), len(params)))
        jacobian[:, 0] = -x  # derivative with respect to slope
        jacobian[:, 1] = -1  # derivative with respect to intercept
        return jacobian
    
    def estimate_initial_params(self, x, y):
        """Estimate initial parameters for the linear model using linear regression."""
        (width, height) = (x.max() - x.min(), y.max() - y.min())
        slope = height / width
        intercept = y.min() - slope * x.min()
        init_param = np.array([slope, intercept], dtype=np.float64)
        return self._map_manual_initial_params(initial_params=init_param)

class Sine(NanomechModel):
    """A simple sine model"""
    def __init__(self, name="Sine"):
        super().__init__(name, 
                         parameters={
                             "name":["amplitude","frequency","phase", "slope", "offset"], 
                             "abbrev":["A","f","phi","a","b"], 
                             "units":["N","Hz","rad","N/sec","N"]},
                         )
        
    def evaluate(self, params, x):
        """Fit the sine model to the data."""
        A, f, phi, a, b = params
        return A * np.sin(2 * np.pi * f * x + phi) + a * x + b

    def jacobian(self, params, x, _):
        """Compute the Jacobian matrix for the sine model."""
        A, f, phi, a, b = params
        jacobian = np.zeros((len(x), len(params)))
        arg = 2 * np.pi * f * x + phi
        jacobian[:, 0] = -np.sin(arg)                           # w.r.t amplitude
        jacobian[:, 1] = -A * 2 * np.pi * x * np.cos(arg)       # w.r.t frequency
        jacobian[:, 2] = -A * np.cos(arg)                       # w.r.t phase
        jacobian[:, 3] = -x                                     # w.r.t slope
        jacobian[:, 4] = -1                                     # w.r.t offset

        return jacobian

    def residuals(self, params, x, y):
        """Compute the residuals for the sine model."""
        return y - self.evaluate(params, x)
    
    def estimate_initial_params(self, x, y):
        """Estimate initial parameters for the sine model using FFT."""
        n = len(x)
        dt = (x[-1] - x[0]) / (n - 1)  # Sampling interval
        
        # 1. Remove linear drift to reduce false detection on the low-frequency side
        slope_estimate, offset_estimate = np.polyfit(x, y, 1)
        y_detrend = y - (slope_estimate * x + offset_estimate)

        # 2. Use FFT to estimate the dominant frequency and phase
        #    Apply a window function to reduce spectral leakage
        window = np.hanning(n)
        fft_y = np.fft.fft(y_detrend * window)
        freqs = np.fft.fftfreq(n, d=dt)
        
        positive_freqs = freqs[freqs > 0]
        positive_fft_y = fft_y[freqs > 0]
        
        dominant_freq_index = np.argmax(np.abs(positive_fft_y))
        dominant_freq = positive_freqs[dominant_freq_index]

        # 3. Estimate amplitude from the detrended waveform
        amplitude_estimate = (np.max(y_detrend) - np.min(y_detrend)) / 2

        # 4. Convert FFT complex component to sine-based phase
        #    np.angle is cosine-based, so adjust by -np.pi/2 for sine
        #    Also, adjust phase considering the value at x[0]
        fft_phase = np.angle(positive_fft_y[dominant_freq_index])
        phase_estimate = fft_phase + np.pi / 2 - 2 * np.pi * dominant_freq * x[0]
        
        # Wrap phase to the range [-pi, pi]
        phase_estimate = self.wrap_phase(phase_estimate)
        p0 = np.array([amplitude_estimate, dominant_freq, phase_estimate, slope_estimate, offset_estimate], dtype=np.float64)

        # 5. Map manual initial parameters if provided in self.parameters["init"]
        return self._map_manual_initial_params(initial_params=p0)
    
    def wrap_phase(self, phase):
        """Wrap phase to the range [-pi, pi]."""
        return (phase + np.pi) % (2 * np.pi) - np.pi

class FixedDriftSine(Sine):
    """Four-parameter sine with exactly zero drift and normalized residuals.

    Physical parameters are amplitude, frequency, phase and DC. The phase uses
    Sine's sin(2*pi*f*t + phase) convention. residual_scale has signal units.
    """
    def __init__(self, residual_scale):
        super().__init__(name="FixedDriftSine")
        if not np.isfinite(residual_scale) or residual_scale <= 0:
            raise ValueError("residual_scale must be finite and positive")
        self.residual_scale = float(residual_scale)
        self.param_count = 4
        self.parameters = {key: [values[i] for i in (0, 1, 2, 4)]
                           for key, values in self.parameters.items()}
        self.parameters["units"] = ["signal", "Hz", "rad", "signal"]
        self.param_scales = np.ones(4)

    @staticmethod
    def _with_zero_drift(params):
        return np.array([params[0], params[1], params[2], 0., params[3]])

    def evaluate(self, params, x):
        return Sine.evaluate(self, self._with_zero_drift(params), x)

    def residuals(self, params, x, y):
        return (y - self.evaluate(params, x)) / self.residual_scale

    def jacobian(self, params, x, y):
        return Sine.jacobian(self, self._with_zero_drift(params), x, y)[:, [0, 1, 2, 4]] / self.residual_scale

    def estimate_initial_params(self, x, y):
        if self.parameters.get("init") is None:
            raise ValueError("FixedDriftSine requires explicit initial parameters")
        return np.asarray(self.parameters["init"], dtype=float)


class HertzSphere(NanomechModel):
    """A simple Hertzian contact model for a spherical indenter"""
    def __init__(self, tip_radius, poisson_ratio, ignore_adhesion=True, residual_scale=1.0):
        if not np.isfinite(residual_scale) or residual_scale <= 0:
            raise ValueError("residual_scale must be finite and positive")
        self.residual_scale = float(residual_scale)
        super().__init__("HertzSphere", 
                         parameters={
                            "name":["E_eff","x0"], 
                            "abbrev":["E","x0"], 
                            "units":["Pa","m"]},
                         constants={
                             "R":tip_radius,
                             "nu":poisson_ratio,
                             "ignore_adhesion":ignore_adhesion},
                         )
        
    def evaluate(self, params, x):
        """Fit the Hertzian model to the data."""
        tip_radius = self.constants["R"]
        poisson_ratio = self.constants["nu"]
        e_eff, x0 = params
        
        # 幾何学的係数の計算
        a_sphere = (4/3) / (1 - poisson_ratio**2) * np.sqrt(tip_radius)
        
        # 0未満のストロークに対しては力を0にするため、np.maximumを使用
        indentation = np.maximum(x - x0, 0)  # should be non-negative
        return a_sphere * e_eff * (indentation ** 1.5)

    def jacobian(self, params, x, _):
        """Compute the Jacobian matrix for the Hertzian model."""
        E_eff, x0 = params
        jacobian = np.zeros((len(x), len(params)))
        tip_radius = self.constants["R"]
        poisson_ratio = self.constants["nu"]
        
        a_sphere = (4/3) / (1 - poisson_ratio**2) * np.sqrt(tip_radius)
        indentation = np.maximum(x - x0, 0)  # should be non-negative
        
        # 残差 y - evaluate に対する偏微分
        jacobian[:, 0] = -a_sphere * (indentation ** 1.5)
        jacobian[:, 1] = 1.5 * a_sphere * E_eff * (indentation ** 0.5)
        return jacobian / self.residual_scale

    def residuals(self, params, x, y):
        """Compute the residuals for the Hertzian model."""
        return (y - self.evaluate(params, x)) / self.residual_scale
    
    def estimate_initial_params(self, x, y):
        """Estimate initial parameters for the Hertzian model."""
        # 1. initial x0 (contact point) is set to the midpoint of the x range, assuming contact occurs near the center of the data
        x0_estimate = x[len(x) // 2]
        
        # 2. Typical E_eff is assumed to be around 10 MPa
        #    If initial parameters are provided in self.parameters["init"], use them; otherwise, use the default estimates
        E_eff_typical = 10e6

        return self._map_manual_initial_params(initial_params=np.array([E_eff_typical, x0_estimate], dtype=np.float64))
