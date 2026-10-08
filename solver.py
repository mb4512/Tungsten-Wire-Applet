import numpy as np
from physics import (E, g_rate, c_sat, m_rate, Omega_v, Omega_il, Omega_vl, get_Omega_tilde_zz)

def setup_grid(Nx, Nz, L, s, fwhm, w_irr):
    """Initializes the 2D spatial grid, dose profile, and state dictionary."""
    x_arr = np.linspace(0, s, Nx)
    z_arr = np.linspace(-L/2, L/2, Nz)
    X, Z = np.meshgrid(x_arr, z_arr, indexing='ij')

    f_X = np.where(X <= w_irr, 1.0, 0.0)
    a_param = 2.0 * np.sqrt(np.log(2)) / fwhm
    g_Z = np.exp(-a_param**2 * Z**2)
    
    dose_rate_2D = f_X * g_Z
    max_dose = np.max(dose_rate_2D)
    if max_dose > 0:
        dose_rate_2D /= max_dose

    state = {
        'cv': np.zeros_like(X),
        'cil': np.zeros_like(X),
        'cvl': np.zeros_like(X),
        'cvoid': np.zeros_like(X),
        'eps_v_zz': np.zeros_like(X),
        'eps_il_zz': np.zeros_like(X),
        'eps_vl_zz': np.zeros_like(X),
        'eps_tot_zz': np.zeros_like(X)
    }
    return state, dose_rate_2D

def run_irradiation(state, dose_rate_2D, phi_start, dpa, sigma_ext_initial, N_steps):
    """Advances the state over a continuous irradiation phase."""
    phi_end = phi_start + dpa
    eps_tot_fixed = sigma_ext_initial / E + np.mean(state['eps_tot_zz'])
    dphi_nom = (phi_end - phi_start) / N_steps
    
    phi_current = phi_start
    phi_plot = []
    sig_plot = []
    
    for _ in range(N_steps):
        dphi_local = dphi_nom * dose_rate_2D
        sigma_local = E * (eps_tot_fixed - state['eps_tot_zz'])
        
        rate_cv = g_rate * (1.0 - state['cv'] / c_sat) + m_rate * state['cvoid']
        rate_cvoid = -m_rate * state['cvoid']
        rate_cil = g_rate * (1.0 - state['cv'] / c_sat)
        
        state['cv'] += rate_cv * dphi_local
        state['cvoid'] += rate_cvoid * dphi_local
        state['cil'] += rate_cil * dphi_local
        
        state['eps_v_zz'] = (1.0 / 3.0) * Omega_v * state['cv']
        Om_tilde_zz = get_Omega_tilde_zz(sigma_local)
        state['eps_il_zz'] += Omega_il * Om_tilde_zz * (rate_cil * dphi_local)
        
        state['eps_tot_zz'] = state['eps_v_zz'] + state['eps_il_zz'] + state['eps_vl_zz']
        sigma_ext_current = E * (eps_tot_fixed - np.mean(state['eps_tot_zz']))
        
        phi_current += dphi_nom
        phi_plot.append(phi_current)
        sig_plot.append(sigma_ext_current)
        
    return phi_current, phi_plot, sig_plot

def run_annealing(state, fraction, r_void, r_il, r_vl):
    """Applies an instantaneous zero-stress annealing step to the current state."""
    reacting_cv = state['cv'] * fraction
    cv_to_void = reacting_cv * r_void
    cv_to_il = reacting_cv * r_il
    cv_to_vl = reacting_cv * r_vl

    if np.any(cv_to_il > state['cil']):
        raise ValueError("Insufficient interstitial loops for recombination.")

    scale_il = np.where(state['cil'] > 0, (state['cil'] - cv_to_il) / state['cil'], 0.0)
    state['eps_il_zz'] *= scale_il

    Om_tilde_vl_zero_zz = get_Omega_tilde_zz(np.zeros_like(state['cv']))
    state['eps_vl_zz'] += Omega_vl * cv_to_vl * Om_tilde_vl_zero_zz

    state['cv'] -= reacting_cv
    state['cvoid'] += cv_to_void
    state['cil'] -= cv_to_il
    state['cvl'] += cv_to_vl

    state['eps_v_zz'] = (1.0 / 3.0) * Omega_v * state['cv']
    state['eps_tot_zz'] = state['eps_v_zz'] + state['eps_il_zz'] + state['eps_vl_zz']