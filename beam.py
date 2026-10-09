import numpy as np

def _calc_parametric_bragg(kwargs):
    x_peak = float(kwargs["x_peak"])
    phi_0 = float(kwargs["phi_0"])
    c_3 = 10.0 ** float(kwargs["a"])
    c_5 = max(float(kwargs["c_5"]), 1e-9)
    phi0_root = phi_0 ** (1.0 / c_3)

    def profile(x):
        exp_peak = np.exp(x_peak / c_5)
        exp_x = np.exp(x / c_5)
        
        num = -c_5 * phi0_root + exp_peak * ((c_5 + x - x_peak) * phi0_root - x)
        den = -exp_peak * x_peak + c_5 * (exp_peak - phi0_root + exp_x * (-1.0 + phi0_root))
        
        base = np.where(den != 0, num / den, 0.0)
        base = np.maximum(base, 0.0)
        return base ** c_3

    return profile


class BeamProfiles:
    """
    Registry for beam profiles. Each profile defines its parameters
    for the UI to generate, and a factory function returning the mathematical profile.
    """

    LATERAL = {
        "Gaussian": {
            "params": [
                {"id": "width", "label": "Beam Gaussian FWHM (mm)", "min": 0.1, "max": 15.0, "default": 2.0, "step": 0.05}
            ],
            "func": lambda kwargs: (
                lambda z: np.exp(-(2.0 * np.sqrt(np.log(2)) / kwargs["width"])**2 * z**2)
            )
        },
        "Flat/Rastered": {
            "params": [
                {"id": "width", "label": "Rastered Width (mm)", "min": 0.1, "max": 15.0, "default": 4.0, "step": 0.05}
            ],
            "func": lambda kwargs: (
                lambda z: np.where(np.abs(z) <= kwargs["width"] / 2.0, 1.0, 0.0)
            )
        }
    }

    DEPTH = {
        "Heaviside": {
            "params": [
                {"id": "depth", "label": "Heaviside Depth (x-direction) (µm)", "min": 0.0, "max": None, "default": 2.0, "step": 0.05}
            ],
            "func": lambda kwargs: (
                lambda x: np.where(x <= kwargs["depth"], 1.0, 0.0)
            )
        },
        "Parametric Bragg Peak": {
            "params": [
                {"id": "x_peak", "label": "Bragg peak position (µm)", "min": 0.01, "max": 20.0, "default": 1.3, "step": 0.05},
                {"id": "phi_0", "label": "dose at surface (rel. to Bragg peak)", "min": 0.01, "max": 1.0, "default": 0.5, "step": 0.01},
                {"id": "a", "label": "Curvature at surface", "min": 0.0, "max": 2.0, "default": 0.7, "step": 0.01},
                {"id": "c_5", "label": "Curvature at Bragg peak", "min": 0.001, "max": 2.0, "default": 0.2, "step": 0.01}
            ],
            "func": _calc_parametric_bragg
        }
    }