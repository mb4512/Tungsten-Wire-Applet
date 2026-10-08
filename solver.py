import numpy as np
from physics import (get_Omega_tilde_zz, calc_irradiation_rates, calc_annealing_transfers)

class TungstenWire:
    # ---------------------------------------------------------
    # Wire Geometry (Evaluated within the class)
    # ---------------------------------------------------------
    L = 15.0             # Wire length (mm)
    r = 8.0              # Equivalent wire radius (µm)
    A = np.pi * r**2     # Cross-sectional area (µm^2)
    s = np.sqrt(A)       # Square side length (µm)

    def __init__(self, material, Nx, Nz, profile_f_x, profile_g_z):
        # Store the bundled constants object
        self.mat = material
        
        self.Nx = Nx
        self.Nz = Nz
        
        # Use the class-level geometric constants for the grid
        self.x_arr = np.linspace(0, self.s, self.Nx)
        self.z_arr = np.linspace(-self.L/2, self.L/2, self.Nz)
        self.X, self.Z = np.meshgrid(self.x_arr, self.z_arr, indexing='ij')

        # Evaluate the generic user-provided functions over the grid
        f_X = profile_f_x(self.X)
        g_Z = profile_g_z(self.Z)
        
        self.dose_rate_2D = f_X * g_Z
        max_dose = np.max(self.dose_rate_2D)
        if max_dose > 0:
            self.dose_rate_2D /= max_dose

        # Initialize state arrays
        self.cv = np.zeros_like(self.X)
        self.cil = np.zeros_like(self.X)
        self.cvl = np.zeros_like(self.X)
        self.cvoid = np.zeros_like(self.X)
        
        self.eps_v_zz = np.zeros_like(self.X)
        self.eps_il_zz = np.zeros_like(self.X)
        self.eps_vl_zz = np.zeros_like(self.X)
        self.eps_tot_zz = np.zeros_like(self.X)
        
        self.phi_current = 0.0
        self.phi_plot = []
        self.sig_plot = []
        self.annealing_markers = []

    def run_irradiation(self, dpa, sigma_ext_initial, N_steps):
        phi_start = self.phi_current
        phi_end = phi_start + dpa
        
        eps_tot_fixed = sigma_ext_initial / self.mat.E + np.mean(self.eps_tot_zz)
        dphi_nom = (phi_end - phi_start) / N_steps
        
        # Record the initial state of this irradiation phase 
        # (This captures the zero-dose point and instantaneous grip resets)
        self.phi_plot.append(self.phi_current)
        self.sig_plot.append(sigma_ext_initial)
        
        for _ in range(N_steps):
            dphi_local = dphi_nom * self.dose_rate_2D
            sigma_local = self.mat.E * (eps_tot_fixed - self.eps_tot_zz)
            
            # Pass the bundled MaterialConstants class directly
            rate_cv, rate_cvoid, rate_cil = calc_irradiation_rates(
                self.cv, self.cvoid, self.mat
            )
            
            self.cv += rate_cv * dphi_local
            self.cvoid += rate_cvoid * dphi_local
            self.cil += rate_cil * dphi_local
            
            self.eps_v_zz = (1.0 / 3.0) * self.mat.Omega_v * self.cv
            Om_tilde_zz = get_Omega_tilde_zz(sigma_local)
            self.eps_il_zz += self.mat.Omega_il * Om_tilde_zz * (rate_cil * dphi_local)
            
            self.eps_tot_zz = self.eps_v_zz + self.eps_il_zz + self.eps_vl_zz
            
            sigma_ext_current = self.mat.E * (eps_tot_fixed - np.mean(self.eps_tot_zz))
            
            self.phi_current += dphi_nom
            self.phi_plot.append(self.phi_current)
            self.sig_plot.append(sigma_ext_current)

    def run_annealing(self, fraction, r_void, r_il, r_vl):
        reacting_cv, cv_to_void, cv_to_il, cv_to_vl = calc_annealing_transfers(
            self.cv, self.cil, fraction, r_void, r_il, r_vl
        )

        scale_il = np.where(self.cil > 0, (self.cil - cv_to_il) / self.cil, 0.0)
        self.eps_il_zz *= scale_il

        Om_tilde_vl_zero_zz = get_Omega_tilde_zz(np.zeros_like(self.cv))
        self.eps_vl_zz += self.mat.Omega_vl * cv_to_vl * Om_tilde_vl_zero_zz

        self.cv -= reacting_cv
        self.cvoid += cv_to_void
        self.cil -= cv_to_il
        self.cvl += cv_to_vl

        self.eps_v_zz = (1.0 / 3.0) * self.mat.Omega_v * self.cv
        self.eps_tot_zz = self.eps_v_zz + self.eps_il_zz + self.eps_vl_zz
        
        self.annealing_markers.append(self.phi_current)