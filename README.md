# Tungsten Wire Irradiation Creep Simulation Applet

An interactive, browser-based simulation applet for modeling irradiation-induced stress relaxation and microstructural defect evolution in tungsten wires under ion irradiation and subsequent thermal annealing cycles.

The application runs entirely client-side using [Stlite](https://github.com/whitphx/stlite) (WebAssembly / Pyodide). It requires no server backend, containerisation, or local Python installation.

---

## Overview

During ion irradiation under external tensile loading, materials undergo irradiation creep and anisotropic deformation driven by stress-induced polarisation of interstitial dislocation loops. When irradiation ceases and the material is thermally annealed, interstitial-vacancy recombination and defect agglomeration alter the residual defect microstructure and stored eigenstrains.

This applet provides an interactive simulation tool to:

* Model multi-stage experimental sequences combining irradiation stages and thermal annealing steps.
* Simulate custom spatial damage profiles across the wire depth ($x$) and along the wire axis ($z$).
* Compute local defect concentrations, eigenstrain generation, and macroscopic stress relaxation under fixed-grips boundary conditions.
* Export and import experimental scenarios via JSON configuration files.
* Export simulated relaxation datasets directly to CSV.

---

## Key Features

### 1. Multi-Stage Workflow Management

* **Sequential Stages**: Build sequences of alternating irradiation and annealing stages.
* **Stage-Specific Conditions**:
* **Irradiation Stage**: Specify total nominal dose (dpa) and initial externally applied stress (MPa).
* **Annealing Stage**: Specify reacting fraction of defects ($0.0 \le f \le 1.0$) and partition ratios into voids ($r_{\text{void}}$), interstitial loops ($r_{\text{il}}$), and vacancy loops ($r_{\text{vl}}$).


* **Dynamic Validation**: Ensures defect partition ratios strictly sum to $1.0$ and prevents adding annealing stages without prior defect populations.

### 2. Spatial Beam Profiles

* **Lateral Profiles ($z$-axis, wire length)**:
* **Gaussian**: Characterised by Full Width at Half Maximum (FWHM).
* **Flat / Rastered**: Uniform dose rate over a user-defined central width.


* **Depth Profiles ($x$-axis, wire cross-section)**:
* **Heaviside**: Step profile with a uniform damage region up to a cut-off penetration depth.
* **Parametric Bragg Peak**: Closed-form analytical approximation of an ion implantation Bragg peak.


* **Interactive Profile Visualisation**: Real-time comparison plots display active and inactive profiles dynamically as parameters are tuned.

### 3. Material and Defect Settings

* **Elasticity**: Young's modulus $E$ (GPa).
* **Point Defect Production**: Defect creation rate $g_{\text{rate}}$ (atomic fraction per dpa) and vacancy saturation concentration $c_{\text{sat}}$.
* **Defect Relaxation Volumes**:
* Vacancy relaxation volume $\Omega_v$ (atomic volumes, typically negative).
* Interstitial loop relaxation volume $\Omega_{\text{il}}$ (atomic volumes, positive).
* Vacancy loop relaxation volume $\Omega_{\text{vl}}$ (atomic volumes, negative).


* **Cascade Melting**: Void melting/dissolution rate $m_{\text{rate}}$.
* **Vacancy Loop Polarisation Modes**:
* `fixed`: Vacancy loops retain isotropic orientation generated during annealing.
* `adaptive`: Vacancy loops dynamically re-polarise along the tensile axis under subsequent applied stresses.


* **Illustrative Eigenstrain Plot**: Closed-form analytical reference plot showing pristine eigenstrain evolution $\varepsilon_{zz}^{*,\text{tot}}$ from $0$ to $0.7\text{ dpa}$ across applied stresses from $-1.0\text{ GPa}$ to $+2.0\text{ GPa}$.

### 4. Simulation and Data Export

* **Real-Time Macroscopic Stress Evolution**: Displays macroscopic stress relaxation curves across sequential irradiation stages, annotated with annealing events.
* **Display Modes**: Toggle between absolute stress (MPa) and stress relative to stage initial stress ($\sigma / \sigma_0$).
* **JSON State Management**: Export and load entire simulation configurations (stages, beam profiles, material parameters, and mesh resolutions) via human-readable JSON files (limited to 1 MB).
* **CSV Data Export**: Export the simulated macroscopic stress curve containing:
* `dose (dpa)`
* `externally applied stress (MPa)`
* `relative externally applied stress (unitless)`



---

## Physical and Mathematical Framework

### Wire Geometry

* Nominal length: $L = 15.0\text{ mm}$.
* Equivalent radius: $r = 8.0\ \mu\text{m}$.
* The wire cross-section is modeled as an equivalent square of side length $s = \sqrt{\pi r^2} \approx 14.18\ \mu\text{m}$, discretised onto a uniform 2D grid spanning $(x, z) \in [0, s] \times [-L/2, L/2]$.

### 2D Dose Field

The local damage rate is factorised into independent depth and lateral components:


$$\Phi(x, z) = f(x) \cdot g(z)$$


normalised such that $\max(\Phi(x, z)) = 1.0$.

### Defect Kinetics & Eigenstrain Generation

During irradiation, the local vacancy concentration $c_v$, interstitial loop concentration $c_{\text{il}}$, and void concentration $c_{\text{void}}$ evolve according to coupled rate equations.

1. **Vacancy Eigenstrain**:

$$\varepsilon_{v, zz}^*(x, z) = \frac{1}{3} \Omega_v c_v(x, z)$$


2. **Interstitial Loop Eigenstrain**:
Interstitial loops nucleate preferentially on habit planes inclined relative to the local tensile stress axis. The orientation factor $\tilde{\Omega}_{zz}(\sigma)$ weights the axial strain component:

$$d\varepsilon_{\text{il}, zz}^*(x, z) = \Omega_{\text{il}} \tilde{\Omega}_{zz}(\sigma_{\text{local}}(x, z)) \cdot dc_{\text{il}}(x, z)$$


3. **Total Eigenstrain**:

$$\varepsilon_{zz}^{*,\text{tot}}(x, z) = \varepsilon_{v, zz}^*(x, z) + \varepsilon_{\text{il}, zz}^*(x, z) + \varepsilon_{\text{vl}, zz}^*(x, z)$$



### Fixed-Grips Elastic Stress Relaxation

Assuming rigid clamped ends (isostrain boundary condition along $z$ across the cross-section), the fixed total axial strain is determined by the applied external stress at the start of each stage:


$$\varepsilon_{\text{tot}} = \frac{\sigma_{\text{ext}}(t_0)}{E} + \langle \varepsilon_{zz}^{*,\text{tot}}(x, z, t_0) \rangle_{V}$$

As eigenstrain accumulates heterogeneously across the irradiated volume, the local stress is:


$$\sigma_{\text{local}}(x, z) = E \left[ \varepsilon_{\text{tot}} - \varepsilon_{zz}^{*,\text{tot}}(x, z) \right]$$

The macroscopic externally measured load corresponds to the area-averaged axial stress:


$$\sigma_{\text{ext}} = E \left[ \varepsilon_{\text{tot}} - \langle \varepsilon_{zz}^{*,\text{tot}}(x, z) \rangle_{V} \right]$$

---

## Approximations Taken in This Simulation

To provide interactive execution in a WebAssembly environment, several physical and mechanical approximations are applied:

### 1. Irradiation Model

* **Separable Damage Field**: The ion damage distribution is assumed to factorise into independent lateral and depth functions: $\Phi(x, z) = f(x) \cdot g(z)$. Cross-coupling terms (such as beam divergence or depth-dependent beam broadening) are neglected.
* **Athermal Rate Equations**: Defect generation and clustering rates depend strictly on accumulated local dose (dpa) rather than instantaneous dose rate ($\text{dpa}/\text{s}$) or absolute temperature. Thermal vacancy emission, long-range thermally activated point defect diffusion, and recombination kinetics outside of immediate cascade interaction volumes are neglected during irradiation.
* **Instantaneous Cascades**: Damage cascade effects (such as direct cascade defect clustering and cascade-induced void melting) are parameterised through lumped kinetic rates ($g_{\text{rate}}$, $c_{\text{sat}}$, $m_{\text{rate}}$) rather than explicit stochastic cascade simulations.
* **Coarse-Grained Defect Classes**: Defects are categorised into four representative populations (point vacancies, interstitial loops, vacancy loops, and voids). Detailed defect size distributions, loop radius coarsening, Burgers vector distributions, and complex loop interactions are omitted.

### 2. Eigenstrain Model

* **Uniaxial Loop Polarisation **: Loop alignment under stress is modeled through an analytical orientation function $\tilde{\Omega}_{zz}(\sigma)$ based on stress-induced polarisation of dislocation lops. Stress-induced preferential absorption (SIPA) of point defects onto existing dislocation loops is not explicitly included.
* **Linear Superposition of Eigenstrains**: Interactions between adjacent strain fields of neighboring defect clusters are neglected. The total macroscopic eigenstrain tensor component $\varepsilon_{zz}^{*,\text{tot}}$ is assumed to be a linear superposition of individual defect concentrations multiplied by their relaxation volumes.
* **Isotropic Vacancy and Void Strain**: Point vacancies and three-dimensional voids are treated as mechanically isotropic dilatation centers with spherical relaxation volumes.
* **Instantaneous Polarisation Transitions**: When `adaptive` vacancy loop polarisation mode is selected, existing vacancy loops instantly rotate their habit plane polarisation to align with new stress states, neglecting the kinetic energy barrier of loop unfaulting, rotation, or glide.

### 3. 1D / Structural Mechanics Model

* **Parallel Fiber (1D Isostrain) Approximation**: The wire is treated as an ensemble of uncoupled parallel axial fibers. Compatibility of transverse displacements ($\varepsilon_{xx}$, $\varepsilon_{yy}$) and shear stresses ($\sigma_{xz}$, $\sigma_{yz}$) across adjacent fibers are neglected.
* **Uniaxial Constitutive Law**: Transverse stresses are neglected ($\sigma_{xx} = \sigma_{yy} = 0$). Elastic Poisson contraction coupling between transverse eigenstrains and the axial stress response is not solved.
* **Absence of Bending and Buckling**: The boundary condition enforces purely axial displacement compatibility. Asymmetric damage profiles across the depth ($x$) naturally produce bending moments; however, the model assumes rigid constraints or rotational symmetry that suppress beam deflection, curvature, and lateral buckling.
* **Square Wire Approximation**: To discretise the wire efficiently on a Cartesian finite difference grid, the circular wire cross-section ($\pi r^2$) is mapped to an area-equivalent square cross-section ($s = \sqrt{\pi r^2}$), neglecting circular edge curvature effects on ion incident angles.

---

## Architecture and File Structure

```
├── index.html              # Stlite HTML mounting point pinning dependencies (@stlite/browser)
├── app.py                  # Streamlit interface, stage manager, plotting, and file I/O
├── solver.py               # TungstenWire class: 2D spatial discretisation and ODE integration
├── physics.py              # Defect rate equations, eigenstrain tensors, and annealing transfer models
├── beam.py                 # Registry and mathematical functions for lateral and depth beam profiles
└── default_config.json     # Baseline configuration automatically loaded at application startup

```

---

## Local Development and Offline Deployment

While the applet is designed to run via GitHub Pages without installation, it can also be run locally using either standard Python or a local HTTP server:

### Option A: Standard Python / Streamlit

1. Clone the repository:
```bash
git clone https://github.com/mb4512/Tungsten-Wire-Applet.git
cd Tungsten-Wire-Applet

```


2. Install dependencies:
```bash
pip install streamlit numpy matplotlib

```


3. Run the Streamlit application:
```bash
streamlit run app.py

```



### Option B: Local Web Server (Emulating GitHub Pages / WebAssembly)

Run any local static file server from the root repository directory:

```bash
python -m http.server 8000

```

Navigate to `http://localhost:8000/` in a web browser.