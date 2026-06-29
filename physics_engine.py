# physics_engine.py
import numpy as np
from materials import MATERIAL_DB

def get_bethe_loss(E_keV, Z, A, rho, I_eV):
    """Calculates energy loss dE/dx (keV/cm) using the Bethe formula."""
    if E_keV <= 0.1:
        return 0.0
    
    C = 78500.0  # Empirical scaling constant
    I_keV = I_eV / 1000.0
    
    inner_log = (1.166 * E_keV) / I_keV
    if inner_log <= 1.0:
        return 0.0
        
    dedx = (C * rho * Z) / (A * E_keV) * np.log(inner_log)
    return dedx

def simulate_electrons(E_initial_keV, stack_layers, num_electrons=200):
    """Simulates a batch of electron trajectories and depth energy profiles."""
    all_trajectories = []
    
    # Calculate boundaries
    z_boundaries = []
    current_z = 0.0
    for layer in stack_layers:
        current_z += layer["thickness_um"]
        z_boundaries.append(current_z)
    max_depth_um = current_z if current_z > 0 else 1.0

    # Bins for depth-absorption tracking (e.g., 100 slices through the stack thickness)
    num_bins = 100
    depth_bins = np.linspace(0, max_depth_um, num_bins)
    energy_deposition = np.zeros(num_bins)
    
    # Track vectors
    x = np.zeros(num_electrons)
    z = np.zeros(num_electrons)
    E = np.ones(num_electrons) * E_initial_keV
    theta = np.zeros(num_electrons)
    active = np.ones(num_electrons, dtype=bool)
    
    history_x = [[0.0] for _ in range(num_electrons)]
    history_z = [[0.0] for _ in range(num_electrons)]
    
    step_cm = 1e-7  # 1 nm steps
    step_um = step_cm * 1e4
    
    max_cycles = 3000
    cycle = 0
    
    while np.any(active) and cycle < max_cycles:
        cycle += 1
        
        for i in range(num_electrons):
            if not active[i]:
                continue
                
            # Find layer index
            current_layer_idx = -1
            for idx, bound in enumerate(z_boundaries):
                if z[i] <= bound:
                    current_layer_idx = idx
                    break
            
            if current_layer_idx == -1 or z[i] > max_depth_um:
                active[i] = False # Transmitted out back
                continue
                
            layer_info = MATERIAL_DB[stack_layers[current_layer_idx]["name"]]
            
            dedx = get_bethe_loss(E[i], layer_info["Z"], layer_info["A"], layer_info["rho"], layer_info["I"])
            energy_lost = dedx * step_cm
            
            if energy_lost >= E[i] or E[i] < 0.1:
                # Energy completely spent and absorbed inside this bin
                bin_idx = np.searchsorted(depth_bins, z[i]) - 1
                if 0 <= bin_idx < num_bins:
                    energy_deposition[bin_idx] += E[i]
                E[i] = 0.0
                active[i] = False
                continue
            
            # Log intermediate continuous absorption along the path
            bin_idx = np.searchsorted(depth_bins, z[i]) - 1
            if 0 <= bin_idx < num_bins:
                energy_deposition[bin_idx] += energy_lost
                
            E[i] -= energy_lost
            
            # Scattering math
            alpha = 3.4e-3 * (layer_info["Z"]**0.67) / E[i]
            r1, r2 = np.random.random(), np.random.random()
            cos_alpha_deflect = 1.0 - (2.0 * alpha * r1) / (1.0 + alpha - r1)
            phi_deflect = 2.0 * np.pi * r2
            
            theta[i] += np.arccos(np.clip(cos_alpha_deflect, -1.0, 1.0)) * np.cos(phi_deflect)
            
            x[i] += step_um * np.sin(theta[i])
            z[i] += step_um * np.cos(theta[i])
            
            history_x[i].append(x[i])
            history_z[i].append(z[i])
            
            if z[i] < 0:
                active[i] = False # Backscattered out front
                
    return history_x, history_z, z_boundaries, depth_bins, energy_deposition