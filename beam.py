import numpy as np

class BeamProfiles:
    """
    Registry for beam profiles. Each profile defines its required parameters 
    for the UI to generate, and a factory function that returns the mathematical profile.
    """
    
    LATERAL = {
        "Gaussian": {
            "params": [
                {"id": "width", "label": "Beam Gaussian FWHM (mm)", "min": 0.1, "max": 15.0, "default": 2.0}
            ],
            "func": lambda kwargs: (
                lambda z: np.exp(-(2.0 * np.sqrt(np.log(2)) / kwargs["width"])**2 * z**2)
            )
        },
        "Flat/Rastered": {
            "params": [
                {"id": "width", "label": "Rastered Width (mm)", "min": 0.1, "max": 15.0, "default": 2.0}
            ],
            "func": lambda kwargs: (
                lambda z: np.where(np.abs(z) <= kwargs["width"] / 2.0, 1.0, 0.0)
            )
        }
    }

    DEPTH = {
        "Heaviside": {
            "params": [
                # max is set to None so the UI can dynamically inject the wire thickness
                {"id": "depth", "label": "Heaviside Depth (x-direction) (µm)", "min": 0.0, "max": None, "default": 2.0}
            ],
            "func": lambda kwargs: (
                lambda x: np.where(x <= kwargs["depth"], 1.0, 0.0)
            )
        }
    }