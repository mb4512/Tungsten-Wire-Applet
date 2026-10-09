import json
import uuid
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

from physics import MaterialConstants, get_Omega_tilde_zz
from solver import TungstenWire
from beam import BeamProfiles

st.set_page_config(page_title="Irradiation Creep Simulation", layout="wide")

MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024  # 1 MB

# ---------------------------------------------------------
# Synchronized Slider & Input Helper
# ---------------------------------------------------------
def synced_slider(label, min_val, max_val, current_val, step, key_base, container=st):
    col1, col2 = container.columns(2)
    
    def sync(source, target):
        st.session_state[target] = st.session_state[source]
        
    slider_key = f"{key_base}_slider"
    num_key = f"{key_base}_num"
    
    if slider_key not in st.session_state:
        st.session_state[slider_key] = current_val
    if num_key not in st.session_state:
        st.session_state[num_key] = current_val
        
    with col1:
        st.slider(
            label, min_value=min_val, max_value=max_val, 
            value=st.session_state[slider_key], step=step, 
            key=slider_key, on_change=sync, args=(slider_key, num_key)
        )
    with col2:
        st.number_input(
            label, min_value=min_val, max_value=max_val, 
            value=st.session_state[num_key], step=step, 
            key=num_key, label_visibility="hidden", 
            on_change=sync, args=(num_key, slider_key)
        )
        
    return st.session_state[slider_key]

# ---------------------------------------------------------
# Unified Configuration Loader
# ---------------------------------------------------------
def apply_config(data):
    """Parses a configuration dictionary and sets session_state variables."""
    if "stages" in data and isinstance(data["stages"], list):
        st.session_state.stages = [
            {**s, "id": uuid.uuid4().hex} for s in data["stages"]
        ]

    beam_data = data.get("beam_settings", {})
    if "lateral_shape" in beam_data:
        st.session_state["lat_profile_shape"] = beam_data["lateral_shape"]
    if "depth_shape" in beam_data:
        st.session_state["dep_profile_shape"] = beam_data["depth_shape"]

    if "beam_params" not in st.session_state:
        st.session_state.beam_params = {"lat": {}, "dep": {}}

    lat_params = beam_data.get("lateral_params", {})
    st.session_state.beam_params["lat"].update(lat_params)
    for name, pdict in lat_params.items():
        for pid, val in pdict.items():
            st.session_state[f"lat_param_{name}_{pid}_slider"] = float(val)
            st.session_state[f"lat_param_{name}_{pid}_num"] = float(val)

    dep_params = beam_data.get("depth_params", {})
    st.session_state.beam_params["dep"].update(dep_params)
    for name, pdict in dep_params.items():
        for pid, val in pdict.items():
            st.session_state[f"dep_param_{name}_{pid}_slider"] = float(val)
            st.session_state[f"dep_param_{name}_{pid}_num"] = float(val)

    mat_data = data.get("material_settings", {})
    for key in ["E_GPa", "g_rate", "c_sat", "Omega_v", "Omega_il", "Omega_vl", "m_rate"]:
        if key in mat_data:
            st.session_state[f"mat_{key}"] = float(mat_data[key])
    if "vl_mode" in mat_data:
        st.session_state["mat_vl_mode"] = str(mat_data["vl_mode"])

    rt_data = data.get("runtime_settings", {})
    for key in ["Nx", "Nz", "N_steps"]:
        if key in rt_data:
            st.session_state[f"grid_{key}"] = int(rt_data[key])

# Load initial state from default_config.json on first launch
if "initialized" not in st.session_state:
    with open("default_config.json", "r") as f:
        apply_config(json.load(f))
    st.session_state.initialized = True

# ---------------------------------------------------------
# State Callbacks
# ---------------------------------------------------------
def add_irradiation():
    last_irr = next((s for s in reversed(st.session_state.stages) if s["type"] == "irradiation"), None)
    if last_irr:
        st.session_state.stages.append({"id": uuid.uuid4().hex, "type": "irradiation", "dpa": last_irr["dpa"], "stress": last_irr["stress"]})
    else:
        st.session_state.stages.append({"id": uuid.uuid4().hex, "type": "irradiation", "dpa": 1.0, "stress": 1000.0})

def add_annealing():
    last_ann = next((s for s in reversed(st.session_state.stages) if s["type"] == "annealing"), None)
    if last_ann:
        st.session_state.stages.append({
            "id": uuid.uuid4().hex,
            "type": "annealing", 
            "fraction": last_ann["fraction"], 
            "r_void": last_ann["r_void"], 
            "r_il": last_ann["r_il"], 
            "r_vl": last_ann["r_vl"]
        })
    else:
        st.session_state.stages.append({
            "id": uuid.uuid4().hex,
            "type": "annealing", 
            "fraction": 0.9, 
            "r_void": 0.2, 
            "r_il": 0.8, 
            "r_vl": 0.0
        })

def remove_last_stage():
    if len(st.session_state.stages) > 0:
        removed = st.session_state.stages.pop()
        s_id = removed["id"]
        keys_to_delete = [k for k in st.session_state.keys() if s_id in k]
        for k in keys_to_delete:
            del st.session_state[k]

def load_config_callback():
    file = st.session_state.get("config_file_uploader")
    if file is not None:
        if file.size > MAX_FILE_SIZE_BYTES:
            st.session_state["config_load_status"] = (
                "error",
                f"File size exceeds 1 MB limit ({file.size / 1024:.1f} KB provided)."
            )
            return

        try:
            apply_config(json.load(file))
            st.session_state["config_load_status"] = ("success", "Configuration loaded successfully.")
        except Exception as e:
            st.session_state["config_load_status"] = ("error", f"Failed to parse file: {str(e)}")

# ---------------------------------------------------------
# Sidebar Layout: Stage Management & I/O
# ---------------------------------------------------------
st.sidebar.header("Stage Management")

col1, col2 = st.sidebar.columns(2)
with col1:
    st.button("Add Irradiation", on_click=add_irradiation)
with col2:
    st.button("Add Annealing", on_click=add_annealing)

st.sidebar.button("Remove Last Stage", on_click=remove_last_stage, use_container_width=True)

with st.sidebar.expander("Save / Load Configuration", expanded=False):
    export_payload = {
        "version": "1.0",
        "stages": [
            {k: v for k, v in stage.items() if k != "id"}
            for stage in st.session_state.stages
        ],
        "beam_settings": {
            "lateral_shape": st.session_state["lat_profile_shape"],
            "depth_shape": st.session_state["dep_profile_shape"],
            "lateral_params": st.session_state.beam_params["lat"],
            "depth_params": st.session_state.beam_params["dep"]
        },
        "material_settings": {
            "E_GPa": st.session_state["mat_E_GPa"],
            "g_rate": st.session_state["mat_g_rate"],
            "c_sat": st.session_state["mat_c_sat"],
            "Omega_v": st.session_state["mat_Omega_v"],
            "Omega_il": st.session_state["mat_Omega_il"],
            "Omega_vl": st.session_state["mat_Omega_vl"],
            "m_rate": st.session_state["mat_m_rate"],
            "vl_mode": st.session_state["mat_vl_mode"]
        },
        "runtime_settings": {
            "Nx": st.session_state["grid_Nx"],
            "Nz": st.session_state["grid_Nz"],
            "N_steps": st.session_state["grid_N_steps"]
        }
    }
    
    st.download_button(
        label="Export Settings to JSON",
        data=json.dumps(export_payload, indent=2),
        file_name="simulation_config.json",
        mime="application/json",
        use_container_width=True
    )
    
    st.file_uploader(
        label="Import Configuration (.json)",
        type=["json"],
        key="config_file_uploader",
        on_change=load_config_callback
    )
    
    if "config_load_status" in st.session_state:
        status_type, status_msg = st.session_state["config_load_status"]
        if status_type == "success":
            st.success(status_msg)
        else:
            st.error(status_msg)

st.sidebar.markdown("---")
st.sidebar.subheader("Sequence Configuration")

for idx, stage in enumerate(st.session_state.stages):
    st.sidebar.markdown(f"**Stage {idx + 1}: {stage['type'].capitalize()}**")
    if stage["type"] == "irradiation":
        stage["dpa"] = st.sidebar.number_input(f"Duration (dpa)", min_value=0.01, value=stage["dpa"], key=f"dpa_{stage['id']}")
        stage["stress"] = st.sidebar.number_input(f"Initial Stress (MPa)", value=stage["stress"], key=f"str_{stage['id']}")
    else:
        stage["fraction"] = synced_slider(
            "Reacting Fraction", 0.0, 1.0, stage["fraction"], 0.01, f"f_{stage['id']}", container=st.sidebar
        )
        stage["r_void"] = st.sidebar.number_input("Ratio to Voids", 0.0, 1.0, stage["r_void"], key=f"rv_{stage['id']}")
        stage["r_il"] = st.sidebar.number_input("Ratio to Int. Loops", 0.0, 1.0, stage["r_il"], key=f"ri_{stage['id']}")
        stage["r_vl"] = st.sidebar.number_input("Ratio to Vac. Loops", 0.0, 1.0, stage["r_vl"], key=f"rvl_{stage['id']}")
        
        total_ratio = stage["r_void"] + stage["r_il"] + stage["r_vl"]
        if not np.isclose(total_ratio, 1.0) and stage["fraction"] > 0:
            st.sidebar.error("Ratios must sum to 1.0")
            st.stop()
    st.sidebar.markdown("---")

# ---------------------------------------------------------
# Main Layout: Tabs
# ---------------------------------------------------------
tab_sim, tab_beam, tab_materials, tab_settings = st.tabs([
    "Simulation", "Beam Settings", "Material settings", "Runtime Settings"
])

with tab_settings:
    st.subheader("Grid Resolution")
    Nx = st.number_input("Nx (Depth resolution)", min_value=10, max_value=500, value=st.session_state["grid_Nx"], key="grid_Nx")
    Nz = st.number_input("Nz (Axial resolution)", min_value=50, max_value=1000, value=st.session_state["grid_Nz"], key="grid_Nz")
    N_steps = st.number_input("Integration steps per irradiation stage", min_value=100, max_value=5000, value=st.session_state["grid_N_steps"], key="grid_N_steps")

with tab_materials:
    st.subheader("Material & Defect Properties")
    mat_E_GPa = st.number_input("Young's modulus E (GPa)", step=1.0, value=st.session_state["mat_E_GPa"], key="mat_E_GPa")
    mat_E = mat_E_GPa * 1000.0  
    
    mat_g_rate = st.number_input("Defect creation rate (atomic fraction/dpa)", format="%.3f", value=st.session_state["mat_g_rate"], key="mat_g_rate")
    mat_c_sat = st.number_input("Vacancy saturation concentration (atomic fraction)", format="%.4f", value=st.session_state["mat_c_sat"], key="mat_c_sat")
    mat_Omega_v = st.number_input("Vacancy relaxation volume (atomic volumes)", format="%.2f", value=st.session_state["mat_Omega_v"], key="mat_Omega_v")
    mat_Omega_il = st.number_input("Interstitial loop relaxation volume (atomic volumes)", format="%.2f", value=st.session_state["mat_Omega_il"], key="mat_Omega_il")
    mat_Omega_vl = st.number_input("Vacancy loop relaxation volume (atomic volumes)", format="%.2f", value=st.session_state["mat_Omega_vl"], key="mat_Omega_vl")
    mat_m_rate = st.number_input("Void melting rate (atomic fraction/dpa)", format="%.1f", value=st.session_state["mat_m_rate"], key="mat_m_rate")
    
    vl_options = ["fixed", "adaptive"]
    cur_vl_mode = st.session_state.get("mat_vl_mode", "fixed")
    vl_idx = vl_options.index(cur_vl_mode) if cur_vl_mode in vl_options else 0
    mat_vl_mode = st.selectbox(
        "Vacancy loop polarization mode (post-annealing)",
        options=vl_options,
        index=vl_idx,
        key="mat_vl_mode",
        help="'fixed': retains the zero-stress [111] orientation generated during annealing. 'adaptive': instantly adjusts to the new applied stress upon further irradiation."
    )

    st.markdown("---")
    st.subheader("Illustrative Eigenstrain Evolution")
    st.markdown("Analytical evolution of $\\varepsilon_{zz}^{*,tot}$ for an initially pristine microstructure under constant uniaxial stress.")

    phi_plot_0d = np.linspace(0, 0.7, 200)
    
    if mat_c_sat > 0:
        cv_plot_0d = mat_c_sat * (1 - np.exp(-mat_g_rate * phi_plot_0d / mat_c_sat))
    else:
        cv_plot_0d = mat_g_rate * phi_plot_0d
        
    eps_v_zz_0d = (1.0 / 3.0) * mat_Omega_v * cv_plot_0d
    
    fig_mat, ax_mat = plt.subplots(figsize=(8, 4))
    stresses_MPa = np.arange(-1000.0, 2001.0, 500.0)
    for sig in stresses_MPa:
        Om_zz_0d = get_Omega_tilde_zz(sig)
        eps_il_zz_0d = mat_Omega_il * Om_zz_0d * cv_plot_0d
        eps_tot_zz_0d = eps_v_zz_0d + eps_il_zz_0d
        ax_mat.plot(phi_plot_0d, eps_tot_zz_0d, label=f"{sig/1000.0:g} GPa")
        
    ax_mat.set_xlabel("Dose (dpa)")
    ax_mat.set_ylabel(r"Total Eigenstrain $\varepsilon_{zz}^{*,tot}$")
    ax_mat.grid(True, linestyle='--', alpha=0.6)
    ax_mat.legend(title="Applied Stress", bbox_to_anchor=(1.05, 1), loc='upper left')
    fig_mat.tight_layout()
    st.pyplot(fig_mat)

with tab_beam:
    st.subheader("Lateral Profile (z-direction)")
    
    lat_opts = list(BeamProfiles.LATERAL.keys())
    cur_lat_shape = st.session_state.get("lat_profile_shape", "Flat/Rastered")
    lat_default_idx = lat_opts.index(cur_lat_shape) if cur_lat_shape in lat_opts else 0
    lat_type = st.selectbox("Lateral Profile Shape", options=lat_opts, index=lat_default_idx, key="lat_profile_shape")
    
    lat_kwargs = {}
    for p in BeamProfiles.LATERAL[lat_type]["params"]:
        cur_val = st.session_state.beam_params["lat"][lat_type].get(p["id"], p["default"])
        val = synced_slider(
            label=p["label"], 
            min_val=float(p["min"]), 
            max_val=float(p["max"]), 
            current_val=float(cur_val), 
            step=float(p.get("step", 0.05)),
            key_base=f"lat_param_{lat_type}_{p['id']}",
            container=st
        )
        st.session_state.beam_params["lat"][lat_type][p["id"]] = val
        lat_kwargs[p["id"]] = val

    z_plot = np.linspace(-TungstenWire.L/2, TungstenWire.L/2, 500)
    fig_lat, ax_lat = plt.subplots(figsize=(8, 3))
    
    for name, config in BeamProfiles.LATERAL.items():
        func_kwargs = st.session_state.beam_params["lat"][name]
        func = config["func"](func_kwargs)
        profile_vals = func(z_plot)
        
        if name == lat_type:
            ax_lat.plot(z_plot, profile_vals, color='red', lw=3.0, label=f'{name} (Active)')
        else:
            ax_lat.plot(z_plot, profile_vals, color='blue', lw=1.5, alpha=0.5, label=f'{name} (Inactive)')
            
    ax_lat.set_xlabel("z position along wire (mm)")
    ax_lat.set_ylabel("Normalized Dose Rate")
    ax_lat.set_title("Lateral Beam Profile $g(z)$")
    ax_lat.grid(True, linestyle='--', alpha=0.6)
    ax_lat.legend(loc="upper right")
    st.pyplot(fig_lat)

    st.markdown("---")
    st.subheader("Depth Profile (x-direction)")
    
    dep_opts = list(BeamProfiles.DEPTH.keys())
    cur_dep_shape = st.session_state.get("dep_profile_shape", "Parametric Bragg Peak")
    dep_default_idx = dep_opts.index(cur_dep_shape) if cur_dep_shape in dep_opts else 0
    dep_type = st.selectbox("Depth Profile Shape", options=dep_opts, index=dep_default_idx, key="dep_profile_shape")
    
    dep_kwargs = {}
    for p in BeamProfiles.DEPTH[dep_type]["params"]:
        max_v = float(p["max"]) if p["max"] is not None else float(np.round(TungstenWire.s, 2))
        cur_val = st.session_state.beam_params["dep"][dep_type].get(p["id"], p["default"])
        val = synced_slider(
            label=p["label"], 
            min_val=float(p["min"]), 
            max_val=max_v, 
            current_val=float(cur_val), 
            step=float(p.get("step", 0.01)),
            key_base=f"dep_param_{dep_type}_{p['id']}",
            container=st
        )
        st.session_state.beam_params["dep"][dep_type][p["id"]] = val
        dep_kwargs[p["id"]] = val

    if dep_type == "Parametric Bragg Peak":
        needed_x = dep_kwargs.get("x_peak", 1.3) + 1.0
    else:
        needed_x = dep_kwargs.get("depth", 2.0) + 0.5
    x_plot_max = min(float(TungstenWire.s), max(3.0, float(needed_x)))
    x_plot = np.linspace(0, x_plot_max, 500)

    fig_dep, ax_dep = plt.subplots(figsize=(8, 3))
    
    for name, config in BeamProfiles.DEPTH.items():
        func_kwargs = st.session_state.beam_params["dep"][name]
        func = config["func"](func_kwargs)
        profile_vals = func(x_plot)
        
        if name == dep_type:
            ax_dep.plot(x_plot, profile_vals, color='red', lw=3.0, label=f'{name} (Active)')
        else:
            ax_dep.plot(x_plot, profile_vals, color='blue', lw=1.5, alpha=0.5, label=f'{name} (Inactive)')
            
    ax_dep.set_xlabel("depth into the wire (µm)")
    ax_dep.set_ylabel("Normalized Dose Rate")
    ax_dep.set_title("Depth Beam Profile $f(x)$")
    ax_dep.grid(True, linestyle='--', alpha=0.6)
    ax_dep.legend(loc="upper right")
    st.pyplot(fig_dep)

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