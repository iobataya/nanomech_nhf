import numpy as np
import scipy.optimize as opt

class NanomechModel:
    """Base class for nanomechanical models."""

    def __init__(self, name: str, parameters: dict=None, constants: dict=None):
        self.name = name
        self.parameters = parameters
        self.constants = constants if constants is not None else {}
        # Default scaling coefficient. (1.0 = no normalizing). Overwrite in subclasses if needed.
        self.param_scales = np.ones(len(parameters["name"])) if parameters else np.array([1.0])

    def evaluate(self, params, x):
        pass
    def jacobian(self, params, x, _):
        pass
    def residuals(self, params, x, y):
        pass
    def _default_initial_params(self, x, y):
        """Estimate default initial parameters based on data. This method should be implemented in subclasses."""
        pass
    def estimate_initial_params(self, x, y):
        """
        Base method to estimate initial parameters for fitting. This method should be overridden in subclasses.
        It provides a common framework for determining initial guesses based on the data.
        If the user has provided manual initial values in the parameters dictionary (self.parameters["init"]), those values will take precedence, and only None entries will be filled in with subclass-specific default estimates.
        """
        # Get estimated values from the subclass-specific method
        default_params = self._default_initial_params(x, y)
        
        # Final initial parameters list to be returned, combining user-specified and default values
        final_initial_params = []
        
        # Check each parameter for manual specification
        if self.parameters.get("init") is None:
            # If no manual initial values are provided, use the default estimates
            return default_params
        for i, manual_val in enumerate(self.parameters.get("init", [])):
            if manual_val is not None:                
                # If the user has provided a manual value, use it directly (in physical units)
                final_initial_params.append(manual_val)
            else:
                # If not specified, use the subclass's automatically estimated value
                final_initial_params.append(default_params[i])
                
        return final_initial_params

    def fit(self, x, y, bounds=None, ftol=1e-8, xtol=1e-8, gtol=1e-8, method='trf'):
        """
        Method to fit the model to data (x, y) using least squares optimization.
        This method handles normalization, fitting, and unit restoration internally.
        """
        # 1. Obtaining initial parameter estimates in physical units
        initial_params_physical = np.array(self.estimate_initial_params(x, y))
        
        # 2. Normalizing parameters for internal optimization (physical units / scale factors)
        initial_guess_scaled = initial_params_physical / self.param_scales
        
        # 3. If bounds are specified, normalize them for internal use
        scaled_bounds = (-np.inf, np.inf)
        if bounds is not None:
            lower, upper = bounds
            scaled_lower = np.array(lower) / self.param_scales
            scaled_upper = np.array(upper) / self.param_scales
            scaled_bounds = (scaled_lower, scaled_upper)
            
        # 4. Perform optimization (calls internal residuals and jacobian)
        result = opt.least_squares(
            fun=self._scaled_residuals,
            x0=initial_guess_scaled,
            jac=self._scaled_jacobian,
            bounds=scaled_bounds,
            args=(x, y),
            ftol=ftol,
            xtol=xtol,
            gtol=gtol,
            method=method,
        )
        
        # 5. Restoring the obtained internal parameters to physical units
        fitted_params_physical = result.x * self.param_scales
        
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
        """Convert physical parameters to scaled parameters for internal optimization."""
        return physical_params * self.param_scales

    def _scaled_params_to_physical(self, scaled_params):
        """Convert scaled parameters back to physical parameters after optimization."""
        return scaled_params / self.param_scales

    def _scaled_residuals(self, scaled_params, x, y):
        # Multiply internal parameters by scale factors to convert to physical units before computing residuals
        physical_params = scaled_params * self.param_scales
        return self.residuals(physical_params, x, y)

    def _scaled_jacobian(self, scaled_params, x, y_):
        # Apply the chain rule: automatically multiply each column of the Jacobian by the corresponding scale factor
        physical_params = scaled_params * self.param_scales
        jac_physical = self.jacobian(physical_params, x, y_)
        # Multiply each column by the corresponding scale factor
        return jac_physical * self.param_scales

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
    
    def _default_initial_params(self, x, y):
        """Estimate initial parameters for the linear model using linear regression."""
        width = x.max() - x.min()
        height = y.max() - y.min()
        slope = height / width
        intercept = y.min() - slope * x.min()
        return [slope, intercept]
    

class Sine(NanomechModel):
    """A simple sine model"""
    def __init__(self, name="Sine"):
        super().__init__(name, 
                         parameters={"name":["amplitude","frequency","phase", "slope", "offset"], "abbrev":["A","f","phi","a","b"], "units":["N","Hz","rad","N/sec","N"]},
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
    
    def _default_initial_params(self, x, y):
        """Estimate initial parameters for the sine model using FFT."""
        n = len(x)
        dt = (x[-1] - x[0]) / (n - 1)  # Sampling interval
        
        # まず線形ドリフトを除去して、低周波側への誤検出を抑える
        slope_estimate, offset_estimate = np.polyfit(x, y, 1)
        y_detrend = y - (slope_estimate * x + offset_estimate)

        # 窓関数でスペクトル漏れを軽減
        window = np.hanning(n)
        fft_y = np.fft.fft(y_detrend * window)
        freqs = np.fft.fftfreq(n, d=dt)
        
        positive_freqs = freqs[freqs > 0]
        positive_fft_y = fft_y[freqs > 0]
        
        dominant_freq_index = np.argmax(np.abs(positive_fft_y))
        dominant_freq = positive_freqs[dominant_freq_index]

        # 振幅はドリフト除去後の波形から推定
        amplitude_estimate = (np.max(y_detrend) - np.min(y_detrend)) / 2

        # 【修正】FFTの複素成分から sin 基準の位相へ変換
        # np.angle は cos 基準なので、sin に合わせるために -np.pi/2 の補正
        # また、x[0] の値を考慮して位相を補正
        fft_phase = np.angle(positive_fft_y[dominant_freq_index])
        phase_estimate = fft_phase + np.pi / 2 - 2 * np.pi * dominant_freq * x[0]
        
        # 位相を -pi 〜 pi の範囲に丸める
        phase_estimate = self.wrap_phase(phase_estimate)

        return [amplitude_estimate, dominant_freq, phase_estimate, slope_estimate, offset_estimate]
    
    def wrap_phase(self, phase):
        """Wrap phase to the range [-pi, pi]."""
        return (phase + np.pi) % (2 * np.pi) - np.pi

class HertzSphere(NanomechModel):
    """A simple Hertzian contact model for a spherical indenter"""
    def __init__(self, tip_radius, poisson_ratio, ignore_adhesion=True):
        super().__init__("HertzSphere", 
                         parameters={"name":["E_eff","x0"], "abbrev":["E","x0"], "units":["Pa","m"]},
                         constants={"R":tip_radius, "nu":poisson_ratio, "ignore_adhesion":ignore_adhesion},
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
        jacobian[:, 0] = -a_sphere * (indentation ** 1.5)                           # w.r.t E_eff
        jacobian[:, 1] = 1.5 * a_sphere * E_eff * (indentation ** 0.5)               # w.r.t x0 (符号はプラスで正解)
        return jacobian

    def residuals(self, params, x, y):
        """Compute the residuals for the Hertzian model."""
        return y - self.evaluate(params, x)
    
    def estimate_initial_params(self, x, y):
        """Estimate initial parameters for the Hertzian model."""
        # 1. initial x0 (contact point) is set to the midpoint of the x range, assuming contact occurs near the center of the data
        x0_estimate = x[len(x) // 2]
        
        # 2. Typical E_eff is assumed to be around 10 MPa
        #    If initial parameters are provided in self.parameters["init"], use them; otherwise, use the default estimates
        E_eff_typical = 10e6

        return [E_eff_typical, x0_estimate]
    
    def get_bounds(self):
        """Return bounds for the Hertzian model parameters."""
        return ([0.0, -np.inf], [np.inf, np.inf])
