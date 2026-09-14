import logging
import os
import sys
import numpy as np
import scipy.optimize as opt
import matplotlib.pyplot as plt
import time

from nanosurf.utils.io import nhf_reader, fileutil


# Ensure repository root is on sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from nanomech.nm_models import NanomechModel, Linear, Sine
from nanomech.gwy_export import savedata_gwy

logger = logging.getLogger(__name__)
logging.getLogger('matplotlib').setLevel(logging.WARNING)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'results')
OUTPUT_FIGS_DIR = os.path.join(os.path.dirname(__file__), 'figs')

def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def _plot_fitted_curve(model:NanomechModel, x_values, y_values, fitted_params, model_params=None, initial_params=None):
    """Helper function to plot the fitted curve and save it as a PNG file."""
    plt.figure(figsize=(10, 6))
    plt.scatter(x_values, y_values, s=10, label='Data', alpha=0.5)
    plt.plot(x_values, model.evaluate(fitted_params, x_values), color='red', label='Fitted Curve', linewidth=2)
    plt.title(f'{model.name} Model Fit')
    plt.xlabel('x')
    plt.ylabel('y')
    plt.legend()
    # write resulting parameters on the plot
    params_text = f"Fitted Parameters:\n" + "\n".join([f"{name}: {value:.2e}" for name, value in zip(model.parameters['abbrev'], fitted_params)])
    if model_params is not None:
        params_text += f"\n\nTrue Parameters:\n" + "\n".join([f"{name}: {value:.2e}" for name, value in zip(model.parameters['abbrev'], model_params)])
    if initial_params is not None:
        params_text += f"\n\nInitial Guess:\n" + "\n".join([f"{name}: {value:.2e}" for name, value in zip(model.parameters['abbrev'], initial_params)])
    plt.text(0.05, 0.95, params_text, transform=plt.gca().transAxes, fontsize=10, verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.3))
    plt.grid()
    plt.tight_layout()
    ensure_output_dir()
    #filename = f'plot_{model.name}_{int(time.time())}.png'
    filename = f'plot_{model.name}.png'
    path = os.path.join(OUTPUT_FIGS_DIR, filename)
    if os.path.exists(path):
        logger.info(f"Overwriting existing plot file: {path}")
    plt.savefig(path)

class TestNanomechModels:
    def test_nanomech_model_initialization(self):
        # Test initialization of NanomechModel
        model = NanomechModel(name="TestModel", parameters={"name": ["param1", "param2"], "abbrev": ["p1", "p2"], "init": [1.0, 2.0]})
        assert model.name == "TestModel"
        assert model.parameters["name"] == ["param1", "param2"]
        assert model.parameters["abbrev"] == ["p1", "p2"]
        assert model.parameters["init"] == [1.0, 2.0]

    def test_nanomech_model_estimate_initial_params(self):
        # Test the estimate_initial_params method of NanomechModel
        model = NanomechModel(name="TestModel", parameters={"name": ["param1", "param2"], "abbrev": ["p1", "p2"], "init": [1.0, 2.0]})
        x_values = np.array([0, 1, 2])
        y_values = np.array([1.0, 2.0, 3.0])
        initial_params = model.estimate_initial_params(x_values, y_values)
        assert np.allclose(initial_params, [1.0, 2.0])

    def test_nanomech_model_scales(self):
        # Test the param_scales property of NanomechModel
        # In the fitting, the scales are used to normalize the parameters for optimization. Here we check if the scales are set correctly.
        # For example, fitting for small force in nm and large Young's modulus in GPa does not converge well without scaling. So we set scales to normalize them.
    
        class TestLinearModel(Linear):
            """This model has large intercept (1e9) and small slope, which requires scaling for fitting."""
            def __init__(self):
                super().__init__(name="TestLinearModel")
                self.param_scales = [0.1, 1e9]  # Example scales for testing
        test_model = TestLinearModel()
        assert test_model.param_scales == [0.1, 1e9]
        physical_params = np.array([0.05, 2e9])
        scaled_params = test_model._physical_params_to_scaled(physical_params)
        logger.info(f"Given physical parameters: {physical_params}, Scaled parameters: {scaled_params}")
        assert scaled_params[0] == 0.5  # 0.05 / 0.1
        assert scaled_params[1] == 2  # 2e9 / 1e9

        restored_physical_params = test_model._scaled_params_to_physical(scaled_params)
        logger.info(f"Restored from scaled parameters {scaled_params} to physical parameters: {restored_physical_params}")
        assert restored_physical_params[0] == 0.05
        assert restored_physical_params[1] == 2e9
        
        x_data = np.array([0, 1, 2])
        y_data = np.array([1e9 + 0.1, 1e9 + 0.2, 1e9 + 0.3])
        logger.debug(f"Estimated initial parameters: {test_model.estimate_initial_params(x_data, y_data)}")
        fitted_params = test_model.fit(x_data, y_data, gtol=1e-15)
        assert np.allclose(fitted_params, [0.1, 1e9], rtol=0.05)  # Allow some tolerance due to noise

class TestLinearModel:
    def test_linear_model(self):
        # Create a Linear model with specific parameters
        slope = 100
        intercept = 1e9
        linear_model = Linear("test_linear_large_offset")
        # Set initial parameters for testing. Note that the two parameters are far apart in scale, 
        # which is why we set scales to normalize them.
        linear_model.param_scales = [100, 1e9]
        
        # Test the evaluate method with least_squares fitting using Jacobian
        x_values = np.linspace(0, 100, 101)  # 0 to 100
        y_values = slope * x_values + intercept + np.random.normal(0, slope*10, size=x_values.shape)  # Add some noise

        # Initial guess for parameters
        initial_guess = linear_model.estimate_initial_params(x_values, y_values)
        logger.info(f"Estimated initial parameters: {initial_guess}")
        logger.info(f"Parameter scales: {linear_model.param_scales}")
        
        # execute the fitting using least_squares with the analytical Jacobian
        fitted_params = linear_model.fit(x_values, y_values, gtol=1e-12)
        logger.info(f"Fitted parameters: {fitted_params}")

        # Plot data points and fitted curve using matplotlib to save .png file
        _plot_fitted_curve(linear_model, x_values, y_values, fitted_params, model_params=np.array([slope, intercept]), initial_params=initial_guess)

        # Check if the fitted parameters are close to the true values
        assert np.isclose(fitted_params[0], slope, rtol=0.05), f"Fitted slope {fitted_params[0]} is not close to true slope {slope}"
        assert np.isclose(fitted_params[1], intercept, rtol=0.05), f"Fitted intercept {fitted_params[1]} is not close to true intercept {intercept}"

class TestSineModel:
    def test_sine_model(self):
        # Create a Sine model with specific parameters
        rng = np.random.default_rng() 
        amplitude = 1.0e-9  # Amplitude in meters, but very small scale (nm).
        frequency = 2.0  # Frequency in Hz
        phase = rng.uniform(-np.pi, np.pi)  # Random phase between -pi and pi
        slope = rng.uniform(-1e-9, 1e-9)
        offset = 50
        sine_model = Sine("test_drifting_sine_with_small_amplitude")
        sine_model.param_scales = [1e-9, 1.0, 1.0, 1.0, 1.0]  # Scales for amplitude, frequency, phase, slope, offset
        
        # Test the evaluate method
        x_values = np.linspace(0, 5, 2000)  # 0 to 5 seconds
        y_values = amplitude * np.sin(2 * np.pi * frequency * x_values + phase) + slope * x_values + offset + np.random.normal(0, 0.1*amplitude, size=x_values.shape)  # Add some noise

        # Initial guess for parameters
        initial_guess = sine_model.estimate_initial_params(x_values, y_values)
        logger.info(f"Estimated initial parameters for {sine_model.parameters['abbrev']} : {initial_guess}")
        logger.info(f"Parameter scales: {sine_model.param_scales}")

        # Execute the fitting using least_squares with the analytical Jacobian
        bounds = np.array([[0, 0, -np.pi, -np.inf, -np.inf], [np.inf, np.inf, np.pi, np.inf, np.inf]])  # Bounds for amplitude, frequency, phase, slope, offset
        fitted_params = sine_model.fit(x_values, y_values, bounds=bounds)
        fitted_params[2] = sine_model.wrap_phase(fitted_params[2])  # Wrap phase to [-pi, pi]
        logger.info(f"Fitted parameters: {fitted_params}")

        # plot data points and fitted curve by matplotlib to save .png file
        _plot_fitted_curve(sine_model, x_values, y_values, fitted_params, model_params=np.array([amplitude, frequency, phase, slope, offset]), initial_params=initial_guess)

        # Check if the fitted parameters are close to the true values
        A, f, phi, a, b = fitted_params
        assert np.isclose(A, amplitude, rtol=0.05), f"Fitted amplitude {A} is not close to true amplitude {amplitude}"
        assert np.isclose(f, frequency, rtol=0.05), f"Fitted frequency {f} is not close to true frequency {frequency}"
        assert np.isclose(phi, phase, rtol=0.05), f"Fitted phase {phi} is not close to true phase {phase}"
        assert np.isclose(a, slope, rtol=0.05), f"Fitted slope {a} is not close to true slope {slope}"
        assert np.isclose(b, offset, rtol=0.05), f"Fitted offset {b} is not close to true offset {offset}"

    def test_sine_model_speed_comparison(self):
        amplitude = 5.0
        frequency = 4
        phase = np.pi / 4
        slope = 1
        offset = 0.5
        sine_model = Sine()
        
        # Prepare 2000 data points
        x_values = np.linspace(0, 3, 2000)
        y_values = amplitude * np.sin(2 * np.pi * frequency * x_values + phase) + slope * x_values + offset + np.random.normal(0, 0.01, size=x_values.shape)

        # Estimate initial parameters for the sine model
        #initial_guess = sine_model.estimate_initial_params(x_values, y_values)
        # No estimation for initial parameters
        initial_guess = [1,4,1,1,1]  # Set to zero for testing speed comparison
        
        logger.info(f"Estimated initial parameters for {sine_model.parameters['abbrev']} : {initial_guess}")

        # 1. Speed measurement for analytical Jacobian
        start_time = time.perf_counter()
        result_jacob =  opt.least_squares(
            sine_model.residuals, 
            initial_guess, 
            bounds=([0, 0, -np.pi, -np.inf, -np.inf], [np.inf, np.inf, np.pi, np.inf, np.inf]),
            jac=sine_model.jacobian, 
            args=(x_values, y_values),
            gtol=1e-12,
        )
        time_jacob = time.perf_counter() - start_time
        nfev_jacob_anal = result_jacob.nfev  # Count for residuals calls
        njev_jacob_anal = result_jacob.njev  # Count for Jacobian calls
        
        # 2. Speed measurement for numerical differentiation (2-point)
        start_time = time.perf_counter()
        result_2point = opt.least_squares(
            sine_model.residuals, 
            initial_guess, 
            bounds=([0, 0, -np.pi, -np.inf, -np.inf], [np.inf, np.inf, np.pi, np.inf, np.inf]),
            jac='2-point', 
            args=(x_values, y_values),
            gtol=1e-12,
        )
        time_2point = time.perf_counter() - start_time
        nfev_2point_num = result_2point.nfev  # Count for residuals calls

        logger.info(f"Estimated parameters using analytical Jacobian: {result_jacob.x}")
        logger.info(f"Estimated parameters using numerical differentiation (2-point): {result_2point.x}")

        # 3. Ouptut the speed comparison results using logger.info
        logger.info("=== Fitting speed ===")
        logger.info(f"Using Analytical Jacobian: {time_jacob*1000:.2f} ms [Called: {nfev_jacob_anal}, Jacobian calls: {njev_jacob_anal}]")
        logger.info(f"Using 2-point :            {time_2point*1000:.2f} ms [Called: {nfev_2point_num}]")
        logger.info(f"⇒ Jacobian is faster than 2-point by {time_2point / time_jacob:.1f} times.")
        logger.info("==================================")

        # 4. Assertions
        assert np.isclose(result_jacob.x[0], amplitude, rtol=0.05)
        assert np.isclose(result_jacob.x[1], frequency, rtol=0.05)


def test_Hertz_model():
    pass
