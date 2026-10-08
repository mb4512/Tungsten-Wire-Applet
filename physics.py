import numpy as np

# ---------------------------------------------------------
# Structural & Material Parameters
# ---------------------------------------------------------
E = 410000.0         # Young's modulus for Tungsten (MPa)
L = 15.0             # Wire length (mm)
r = 8.0              # Equivalent wire radius (µm)
A = np.pi * r**2     # Cross-sectional area (µm^2)
s = np.sqrt(A)       # Square side length (µm)

# ---------------------------------------------------------
# Defect Properties
# ---------------------------------------------------------
g_rate = 0.1         # Defect creation rate (/dpa)
c_sat = 0.003        # Saturation concentration (atomic fraction)
Omega_v = -0.3       # Vacancy relaxation volume
Omega_il = 1.0       # Interstitial loop relaxation volume
Omega_vl = -1.0      # Vacancy loop relaxation volume
m_rate = 100.0       # Void melting rate (/dpa)

def get_Omega_tilde_zz(sigma_local):
    """Vectorized calculation of zz-component of the normalized relaxation volume."""
    alpha = (np.pi / 3) * np.tanh(-0.8 * sigma_local / 1000.0)
    alpha_clip = np.clip(alpha + np.arccos(1 / np.sqrt(3)), 0, np.pi / 2)
    nz = np.cos(alpha_clip)
    nxy = np.sin(alpha_clip) / np.sqrt(2)
    trace = nz + 2 * nxy
    return np.where(trace != 0, nz / trace, 0.0)