import numpy as np
from dataclasses import dataclass

# ---------------------------------------------------------
# Material & Defect Properties
# ---------------------------------------------------------
@dataclass
class MaterialConstants:
    E: float = 410000.0         # Young's modulus for Tungsten (MPa)
    g_rate: float = 0.1         # Defect creation rate (/dpa)
    c_sat: float = 0.003        # Saturation concentration (atomic fraction)
    Omega_v: float = -0.3       # Vacancy relaxation volume
    Omega_il: float = 1.0       # Interstitial loop relaxation volume
    Omega_vl: float = -1.0      # Vacancy loop relaxation volume
    m_rate: float = 100.0       # Void melting rate (/dpa)

# ---------------------------------------------------------
# Mathematical & Kinetic Models
# ---------------------------------------------------------
def get_Omega_tilde_zz(sigma_local):
    """Vectorized calculation of zz-component of the normalized relaxation volume."""
    alpha = (np.pi / 3) * np.tanh(-0.8 * sigma_local / 1000.0)
    alpha_clip = np.clip(alpha + np.arccos(1 / np.sqrt(3)), 0, np.pi / 2)
    nz = np.cos(alpha_clip)
    nxy = np.sin(alpha_clip) / np.sqrt(2)
    trace = nz + 2 * nxy
    return np.where(trace != 0, nz / trace, 0.0)

def calc_irradiation_rates(cv, cvoid, mat: MaterialConstants):
    """Calculates defect accumulation rates reading from the constants class."""
    rate_cv = mat.g_rate * (1.0 - cv / mat.c_sat) + mat.m_rate * cvoid
    rate_cvoid = -mat.m_rate * cvoid
    rate_cil = mat.g_rate * (1.0 - cv / mat.c_sat)
    return rate_cv, rate_cvoid, rate_cil

def calc_annealing_transfers(cv, cil, fraction, r_void, r_il, r_vl):
    """Calculates reacting fractions and checks physical bounds for annealing."""
    reacting_cv = cv * fraction
    cv_to_void = reacting_cv * r_void
    cv_to_il = reacting_cv * r_il
    cv_to_vl = reacting_cv * r_vl

    if np.any(cv_to_il > cil):
        raise ValueError("Insufficient interstitial loops for recombination.")

    return reacting_cv, cv_to_void, cv_to_il, cv_to_vl