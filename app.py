import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# UI Configuration & State Initialization
# ---------------------------------------------------------
st.set_page_config(page_title="Irradiation Creep Simulation", layout="wide")

if "stages" not in st.session_state:
    st.session_state.stages = [
        {"type": "irradiation", "dpa": 0.5, "stress": 1000.0}
    ]

# ---------------------------------------------------------
# Global Parameters
# ---------------------------------------------------------
E = 410000.0         # Young's modulus for Tungsten (MPa)
L = 15.0             # Wire length (mm)
r = 8.0              # Equivalent wire radius (µm)
A = np.pi * r**2     # Cross-sectional area (µm^2)
s = np.sqrt(A)       # Square side length (µm)

g_rate = 0.1         # Defect creation rate (/dpa)
c_sat = 0.003        # Saturation concentration (atomic fraction)
Omega_v = -0.3       # Vacancy relaxation volume
Omega_il = 1.0       # Interstitial loop relaxation volume
Omega_vl = -1.0      # Vacancy loop relaxation volume
m_rate = 100.0       # Void melting rate (/dpa)

# ---------------------------------------------------------
# Math Helpers
# ---------------------------------------------------------
def get_Omega_tilde_zz(sigma_local):
    alpha = (np.pi / 3) * np.tanh(-0.8 * sigma_local / 1000.0)
    alpha_clip = np.clip(alpha + np.arccos(1 / np.sqrt(3)), 0, np.pi / 2)
    nz = np.cos(alpha_clip)
    nxy = np.sin(alpha_clip) / np.sqrt(2)
    trace = nz + 2 * nxy
    return np.where(trace != 0, nz / trace, 0.0)

# ---------------------------------------------------------
# Sidebar Layout: Stage Management
# ---------------------------------------------------------
st.sidebar.header("Stage Management")

col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("Add Irradiation"):
        st.session_state.stages.append({"type": "irradiation", "dpa": 0.5, "stress": 800.0})
        st.rerun()
with col2:
    if st.button("Add Annealing"):
        st.session_state.stages.append({"type": "annealing", "fraction": 0.9, "r_void": 0.5, "r_il": 0.5, "r_vl": 0.0})
        st.rerun()

if st.sidebar.button("Remove Last Stage", use_container_width=True):
    if len(st.session_state.stages) > 0:
        st.session_state.stages.pop()
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("Sequence Configuration")

# Dynamic UI for editing stages
for idx, stage in enumerate(st.session_state.stages):
    st.sidebar.markdown(f"**Stage {idx + 1}: {stage['type'].capitalize()}**")
    if stage["type"] == "irradiation":
        stage["dpa"] = st.sidebar.number_input(f"Duration (dpa)", min_value=0.01, value=stage["dpa"], key=f"dpa_{idx}")
        stage["stress"] = st.sidebar.number_input(f"Initial Stress (MPa)", value=stage["stress"], key=f"str_{idx}")
    else:
        stage["fraction"] = st.sidebar.slider("Reacting Fraction", 0.0, 1.0, stage["fraction"], key=f"f_{idx}")
        stage["r_void"] = st.sidebar.number_input("Ratio to Voids", 0.0, 1.0, stage["r_void"], key=f"rv_{idx}")
        stage["r_il"] = st.sidebar.number_input("Ratio to Int. Loops", 0.0, 1.0, stage["r_il"], key=f"ri_{idx}")
        stage["r_vl"] = st.sidebar.number_input("Ratio to Vac. Loops", 0.0, 1.0, stage["r_vl"], key=f"rvl_{idx}")
        
        total_ratio = stage["r_void"] + stage["r_il"] + stage["r_vl"]
        if not np.isclose(total_ratio, 1.0) and stage["fraction"] > 0:
            st.sidebar.error("Ratios must sum to 1.0")
            st.stop()
    st.sidebar.markdown("---")

# ---------------------------------------------------------
# Main Layout: Tabs
# ---------------------------------------------------------
tab_sim, tab_settings = st.tabs(["Simulation", "Runtime Settings"])

with tab_settings:
    st.subheader("Grid Resolution")
    Nx = st.number_input("Nx (Depth resolution)", min_value=10, max_value=500, value=50)
    Nz = st.number_input("Nz (Axial resolution)", min_value=50, max_value=1000, value=150)
    N_steps = st.number_input("Integration steps per irradiation stage", min_value=100, max_value=5000, value=500)

with tab_sim:
    col_prof1, col_prof2 = st.columns(2)
    with col_prof1:
        fwhm = st.slider("Beam Gaussian FWHM (mm)", min_value=0.1, max_value=15.0, value=2.0)
    with col_prof2:
        max_depth = float(np.round(s, 2))
        w_irr = st.slider("Heaviside Depth (µm)", min_value=0.0, max_value=max_depth, value=2.0)

    # Setup Grid
    x_arr = np.linspace(0, s, Nx)
    z_arr = np.linspace(-L/2, L/2, Nz)
    X, Z = np.meshgrid(x_arr, z_arr, indexing='ij')

    # Calculate Profile
    f_X = np.where(X <= w_irr, 1.0, 0.0)
    a_param = 2.0 * np.sqrt(np.log(2)) / fwhm
    g_Z = np.exp(-a_param**2 * Z**2)
    
    dose_rate_2D = f_X * g_Z
    max_dose = np.max(dose_rate_2D)
    if max_dose > 0:
        dose_rate_2D /= max_dose

    # Initialize State
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

    # Simulation Execution
    phi_current = 0.0
    phi_plot = []
    sig_plot = []
    annealing_markers = []

    for idx, stage in enumerate(st.session_state.stages):
        if stage["type"] == "irradiation":
            phi_start = phi_current
            phi_end = phi_start + stage["dpa"]
            sigma_ext_initial = stage["stress"]
            
            eps_tot_fixed = sigma_ext_initial / E + np.mean(state['eps_tot_zz'])
            dphi_nom = (phi_end - phi_start) / N_steps
            
            for step in range(N_steps):
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
                
        elif stage["type"] == "annealing":
            reacting_cv = state['cv'] * stage["fraction"]
            cv_to_void = reacting_cv * stage["r_void"]
            cv_to_il = reacting_cv * stage["r_il"]
            cv_to_vl = reacting_cv * stage["r_vl"]

            if np.any(cv_to_il > state['cil']):
                st.error(f"Stage {idx+1}: Insufficient interstitial loops for recombination.")
                st.stop()

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
            
            annealing_markers.append(phi_current)

    # Plotting
    if len(phi_plot) > 0:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(phi_plot, sig_plot, color='navy', lw=2)
        
        for marker in annealing_markers:
            ax.axvline(marker, color='red', linestyle='--', alpha=0.6)
            
        ax.set_title('Macroscopic Stress Relaxation')
        ax.set_xlabel('Nominal Beam Dose (dpa)')
        ax.set_ylabel('Externally Applied Stress (MPa)')
        ax.grid(True, linestyle='--', alpha=0.6)
        
        st.pyplot(fig)
    else:
        st.info("Add an irradiation stage to view the simulation plot.")


