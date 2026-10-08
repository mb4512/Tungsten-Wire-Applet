import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

from physics import MaterialConstants
from solver import TungstenWire
from beam import BeamProfiles

st.set_page_config(page_title="Irradiation Creep Simulation", layout="wide")

if "stages" not in st.session_state:
    st.session_state.stages = [
        {"type": "irradiation", "dpa": 1.0, "stress": 1000.0}
    ]

# ---------------------------------------------------------
# State Callbacks (Fixes the widget desync bug)
# ---------------------------------------------------------
def add_irradiation():
    last_irr = next((s for s in reversed(st.session_state.stages) if s["type"] == "irradiation"), None)
    if last_irr:
        st.session_state.stages.append({"type": "irradiation", "dpa": last_irr["dpa"], "stress": last_irr["stress"]})
    else:
        st.session_state.stages.append({"type": "irradiation", "dpa": 1.0, "stress": 1000.0})

def add_annealing():
    last_ann = next((s for s in reversed(st.session_state.stages) if s["type"] == "annealing"), None)
    if last_ann:
        st.session_state.stages.append({
            "type": "annealing", 
            "fraction": last_ann["fraction"], 
            "r_void": last_ann["r_void"], 
            "r_il": last_ann["r_il"], 
            "r_vl": last_ann["r_vl"]
        })
    else:
        st.session_state.stages.append({
            "type": "annealing", 
            "fraction": 0.9, 
            "r_void": 0.2, 
            "r_il": 0.8, 
            "r_vl": 0.0
        })

def remove_last_stage():
    if len(st.session_state.stages) > 0:
        st.session_state.stages.pop()

# ---------------------------------------------------------
# Sidebar Layout: Stage Management
# ---------------------------------------------------------
st.sidebar.header("Stage Management")

col1, col2 = st.sidebar.columns(2)
with col1:
    st.button("Add Irradiation", on_click=add_irradiation)
with col2:
    st.button("Add Annealing", on_click=add_annealing)

st.sidebar.button("Remove Last Stage", on_click=remove_last_stage, use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.subheader("Sequence Configuration")

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
# Main Layout
# ---------------------------------------------------------
tab_sim, tab_beam, tab_materials, tab_settings = st.tabs([
    "Simulation", "Beam Settings", "Material Constants", "Runtime Settings"
])

with tab_settings:
    st.subheader("Grid Resolution")
    Nx = st.number_input("Nx (Depth resolution)", min_value=10, max_value=500, value=50)
    Nz = st.number_input("Nz (Axial resolution)", min_value=50, max_value=1000, value=150)
    N_steps = st.number_input("Integration steps per irradiation stage", min_value=100, max_value=5000, value=500)

with tab_materials:
    st.subheader("Material & Defect Properties")
    mat_E_GPa = st.number_input("Young's modulus E (GPa)", value=410.0, step=1.0)
    mat_E = mat_E_GPa * 1000.0  
    
    mat_g_rate = st.number_input("Defect creation rate (atomic fraction/dpa)", value=0.1, format="%.3f")
    mat_c_sat = st.number_input("Saturation concentration c_sat (atomic fraction)", value=0.003, format="%.4f")
    mat_Omega_v = st.number_input("Vacancy relaxation volume (atomic volumes)", value=-0.3, format="%.2f")
    mat_Omega_il = st.number_input("Interstitial loop relaxation volume (atomic volumes)", value=1.0, format="%.2f")
    mat_Omega_vl = st.number_input("Vacancy loop relaxation volume (atomic volumes)", value=-1.0, format="%.2f")
    mat_m_rate = st.number_input("Void melting rate (atomic fraction/dpa)", value=100.0, format="%.1f")
    
    mat_vl_mode = st.selectbox(
        "Vacancy loop polarization mode (post-annealing)",
        options=["fixed", "adaptive"],
        index=0,
        help="'fixed': retains the zero-stress [111] orientation generated during annealing. 'adaptive': instantly adjusts to the new applied stress upon further irradiation."
    )

with tab_beam:
    st.subheader("Lateral Profile (z-direction)")
    
    lat_opts = list(BeamProfiles.LATERAL.keys())
    lat_type = st.selectbox("Lateral Profile Shape", options=lat_opts, key="lat_profile_shape")
    
    lat_kwargs = {}
    for p in BeamProfiles.LATERAL[lat_type]["params"]:
        lat_kwargs[p["id"]] = st.slider(
            p["label"], 
            min_value=p["min"], 
            max_value=p["max"], 
            value=p["default"], 
            key=f"lat_param_{lat_type}_{p['id']}"
        )

    st.markdown("---")
    st.subheader("Depth Profile (x-direction)")
    
    dep_opts = list(BeamProfiles.DEPTH.keys())
    dep_type = st.selectbox("Depth Profile Shape", options=dep_opts, key="dep_profile_shape")
    
    dep_kwargs = {}
    for p in BeamProfiles.DEPTH[dep_type]["params"]:
        max_v = p["max"] if p["max"] is not None else float(np.round(TungstenWire.s, 2))
        dep_kwargs[p["id"]] = st.slider(
            p["label"], 
            min_value=p["min"], 
            max_value=max_v, 
            value=p["default"],
            key=f"dep_param_{dep_type}_{p['id']}"
        )

    # Visualization
    z_plot = np.linspace(-TungstenWire.L/2, TungstenWire.L/2, 500)
    fig_prof, ax_prof = plt.subplots(figsize=(8, 3))
    
    for name, config in BeamProfiles.LATERAL.items():
        func_kwargs = {}
        for p in config["params"]:
            func_kwargs[p["id"]] = lat_kwargs.get(p["id"], p["default"])
        
        func = config["func"](func_kwargs)
        profile_vals = func(z_plot)
        
        if name == lat_type:
            ax_prof.plot(z_plot, profile_vals, color='red', lw=3.0, label=f'{name} (Active)')
        else:
            ax_prof.plot(z_plot, profile_vals, color='blue', lw=1.5, alpha=0.5, label=f'{name} (Inactive)')
            
    ax_prof.set_xlabel("z position along wire (mm)")
    ax_prof.set_ylabel("Normalized Dose Rate")
    ax_prof.set_title("Lateral Beam Profile $g(z)$")
    ax_prof.grid(True, linestyle='--', alpha=0.6)
    ax_prof.legend(loc="upper right")
    
    st.pyplot(fig_prof)

with tab_sim:
    current_profile_g_z = BeamProfiles.LATERAL[lat_type]["func"](lat_kwargs)
    current_profile_f_x = BeamProfiles.DEPTH[dep_type]["func"](dep_kwargs)

    mat_constants = MaterialConstants(
        E=mat_E,
        g_rate=mat_g_rate,
        c_sat=mat_c_sat,
        Omega_v=mat_Omega_v,
        Omega_il=mat_Omega_il,
        Omega_vl=mat_Omega_vl,
        m_rate=mat_m_rate,
        vl_mode=mat_vl_mode
    )

    wire = TungstenWire(
        material=mat_constants,
        Nx=Nx, 
        Nz=Nz, 
        profile_f_x=current_profile_f_x, 
        profile_g_z=current_profile_g_z
    )

    for idx, stage in enumerate(st.session_state.stages):
        if stage["type"] == "irradiation":
            wire.run_irradiation(dpa=stage["dpa"], sigma_ext_initial=stage["stress"], N_steps=N_steps)
            
        elif stage["type"] == "annealing":
            try:
                wire.run_annealing(
                    fraction=stage["fraction"], 
                    r_void=stage["r_void"], 
                    r_il=stage["r_il"], 
                    r_vl=stage["r_vl"]
                )
            except ValueError as e:
                st.error(f"Stage {idx+1}: {str(e)}")
                st.stop()

    if len(wire.phi_plot) > 0:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(wire.phi_plot, wire.sig_plot, color='navy', lw=2)
        
        for marker in wire.annealing_markers:
            ax.axvline(marker, color='red', linestyle='--', alpha=0.6)
            
        ax.set_title('Macroscopic Stress Relaxation')
        ax.set_xlabel('Nominal Beam Dose (dpa)')
        ax.set_ylabel('Externally Applied Stress (MPa)')
        ax.grid(True, linestyle='--', alpha=0.6)
        
        st.pyplot(fig)
    else:
        st.info("Add an irradiation stage to view the simulation plot.")