# app.py
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import io
from materials import MATERIAL_DB
from physics_engine import simulate_electrons

st.set_page_config(page_title="AttenuE - Electron Track Simulator", layout="wide")

# --- 4. Streamlit UI Layout Configuration ---
st.set_page_config(page_title="AttenuE - Electron Track Simulator", layout="wide")

# Route directly to the hard-coded static image path to maintain instant sync
target_banner = "AttenuE_Banner.svg"

try:
    st.logo(target_banner)
    st.image(target_banner, use_container_width=True)
except Exception:
    # Minimal fallback structure if tracking files are absent
    st.title("⚡ AttenuE")
    st.caption("MONTE CARLO ELECTRON INTERACTION VOLUME SIMULATOR")

st.markdown("<br>", unsafe_allow_html=True)

# Setup clean working tabs
designer_tab, tracks_tab, absorption_tab = st.tabs([
    "📐 1. Layer Stack Designer", 
    "🎯 2. Monte Carlo Electron Trajectories",
    "📈 3. Depth-Absorption Profiles"
])

# Initialize session states
if "e_layers" not in st.session_state:
    st.session_state.e_layers = [
        {"name": "Silicon (Si)", "thickness_um": 0.5},
        {"name": "Gold (Au)", "thickness_um": 0.2}
    ]
if "sim_results" not in st.session_state:
    st.session_state.sim_results = None

# ==========================================
#         SIMULATION PARAMETERS PANEL (Sidebar)
# ==========================================
st.sidebar.header("🔬 Beam Parameters")
beam_energy = st.sidebar.slider("Beam Gun Power (keV)", min_value=5, max_value=50, value=20, step=5)
num_tracks = st.sidebar.slider("Simulated Sample Electron Count", min_value=50, max_value=500, value=150, step=50)

if st.sidebar.button("🚀 EXECUTE MONTE CARLO TRAJECTORY", use_container_width=True):
    if not st.session_state.e_layers:
        st.sidebar.error("Error: Build a layer stack first!")
    else:
        with st.spinner("Processing continuous slowing down approximations..."):
            hx, hz, boundaries, depth_bins, energy_dep = simulate_electrons(
                beam_energy, st.session_state.e_layers, num_electrons=num_tracks
            )
            st.session_state.sim_results = {
                "hx": hx, "hz": hz, "boundaries": boundaries,
                "depth_bins": depth_bins, "energy_dep": energy_dep,
                "beam_energy": beam_energy, "num_tracks": num_tracks
            }
        st.sidebar.success("Trajectory Compute Finished!")

# ==========================================
#       DATA EXPORT SYSTEM (Sidebar Card)
# ==========================================
if st.session_state.sim_results is not None:
    st.sidebar.markdown("---")
    st.sidebar.header("💾 Export Telemetry Data")
    res = st.session_state.sim_results
    
    # Formulate CSV 1: Continuous Absorption Profile Data
    absorption_df = pd.DataFrame({
        "Depth_Position_um": res["depth_bins"],
        "Deposited_Energy_keV": res["energy_dep"]
    })
    abs_csv = absorption_df.to_csv(index=False).encode('utf-8')
    
    st.sidebar.download_button(
        label="📥 Export Depth-Dose Profile (.CSV)",
        data=abs_csv,
        file_name=f"attenue_dose_profile_{beam_energy}keV.csv",
        mime="text/csv",
        use_container_width=True
    )
    
    # Formulate CSV 2: Granular Vector Electron Tracks (Flattened for spreadsheet parsing)
    track_records = []
    for track_idx, (x_coords, z_coords) in enumerate(zip(res["hx"], res["hz"])):
        for step_idx, (x, z) in enumerate(zip(x_coords, z_coords)):
            track_records.append({"Track_ID": track_idx, "Step_Index": step_idx, "Position_X_um": x, "Depth_Z_um": z})
    
    tracks_df = pd.DataFrame(track_records)
    tracks_csv = tracks_df.to_csv(index=False).encode('utf-8')
    
    st.sidebar.download_button(
        label="📥 Export Spatial Trajectories (.CSV)",
        data=tracks_csv,
        file_name=f"attenue_spatial_tracks_{num_tracks}e.csv",
        mime="text/csv",
        use_container_width=True
    )

# ==========================================
#         TAB 1: STACK DESIGNER
# ==========================================
with designer_tab:
    st.header("Configure Material Layer Targets")
    col_input, col_stack = st.columns([1, 1])
    
    with col_input:
        st.subheader("Add Heterojunction Components")
        new_layer_mat = st.selectbox("Select Target Material", list(MATERIAL_DB.keys()))
        new_layer_thick = st.number_input("Thickness Dimension (μm)", min_value=0.05, max_value=5.0, value=0.5, step=0.1)
        
        if st.button("➕ Inject Layer to Stack", use_container_width=True):
            st.session_state.e_layers.append({"name": new_layer_mat, "thickness_um": new_layer_thick})
            st.rerun()
            
        if st.button("🗑️ Reset Entire Stack", use_container_width=True, type="secondary"):
            st.session_state.e_layers = []
            st.rerun()
            
    with col_stack:
        st.subheader("Current Stack Composition Layout")
        if not st.session_state.e_layers:
            st.warning("No layers present. Build a device stack to begin calculations.")
        else:
            for i, layer in enumerate(st.session_state.e_layers):
                card_col, btn_col = st.columns([4, 1])
                with card_col:
                    st.info(f"**Layer {i+1}: {layer['name']}** ({layer['thickness_um']} μm)")
                with btn_col:
                    if st.button("❌", key=f"remove_{i}"):
                        st.session_state.e_layers.pop(i)
                        st.rerun()

# ==========================================
#         TAB 2: ELECTRON TRAJECTORIES
# ==========================================
with tracks_tab:
    st.header("Visualized Scattering Volumes")
    if st.session_state.sim_results is None:
        st.info("Click 'EXECUTE MONTE CARLO TRAJECTORY' in the sidebar panel to generate the spatial interaction maps.")
    else:
        res = st.session_state.sim_results
        col_metrics, col_plot = st.columns([1, 2])
        
        with col_metrics:
            st.subheader("📍 Target Scattering Outcomes")
            bs_count = sum(1 for z_c in res["hz"] if z_c[-1] < 0)
            trans_count = sum(1 for z_c in res["hz"] if z_c[-1] >= res["boundaries"][-1])
            abs_count = res["num_tracks"] - (bs_count + trans_count)
            
            st.metric("Backscattering Coefficient (𝜂)", f"{(bs_count/res['num_tracks'])*100:.1f}%")
            st.metric("Absorbed / Anchored Fraction", f"{(abs_count/res['num_tracks'])*100:.1f}%")
            st.metric("Transmitted Yield Pass-through", f"{(trans_count/res['num_tracks'])*100:.1f}%")
            
            st.markdown("---")
            st.caption("**𝜂 (Backscatter)** captures electrons reflecting entirely out the front facing incident window.")

        with col_plot:
            fig, ax = plt.subplots(figsize=(10, 6.5))
            for x_coords, z_coords in zip(res["hx"], res["hz"]):
                track_color = "#ff4b4b" if z_coords[-1] < 0 else "#00f3ff"
                ax.plot(x_coords, z_coords, color=track_color, alpha=0.3, linewidth=0.8)
                
            prev_b = 0.0
            for idx, b in enumerate(res["boundaries"]):
                ax.axhline(b, color="#ffffff", linestyle="--", alpha=0.4)
                ax.text(ax.get_xlim()[0] + 0.05, (prev_b + b)/2, f"{st.session_state.e_layers[idx]['name']}", 
                        color="#ffffff", fontsize=9, fontweight="bold")
                prev_b = b
                
            ax.set_ylabel("Depth Penetration Dimension Z (μm)", color="#ffffff")
            ax.set_xlabel("Lateral Scattering Profile X (μm)", color="#ffffff")
            ax.invert_yaxis()
            
            fig.patch.set_facecolor('#0b0f19')
            ax.set_facecolor('#111827')
            ax.tick_params(colors='#ffffff')
            st.pyplot(fig)
            plt.close(fig)

# ==========================================
#         TAB 3: DEPTH-ABSORPTION CURVE
# ==========================================
with absorption_tab:
    st.header("Kinetic Energy Dissipation and Dose Mapping")
    if st.session_state.sim_results is None:
        st.info("Click 'EXECUTE MONTE CARLO TRAJECTORY' in the sidebar panel to generate the depth dose analytics.")
    else:
        res = st.session_state.sim_results
        col_metrics3, col_plot3 = st.columns([1, 2])
        
        with col_metrics3:
            st.subheader("⚡ Radiation Dose Profiles")
            total_deposited_energy_keV = np.sum(res["energy_dep"])
            peak_idx = np.argmax(res["energy_dep"])
            peak_depth = res["depth_bins"][peak_idx]
            
            peak_layer = "Surface"
            for idx, b in enumerate(res["boundaries"]):
                if peak_depth <= b:
                    peak_layer = f"Layer {idx+1} ({st.session_state.e_layers[idx]['name']})"
                    break
            
            deepest_points = [max(z_track) for z_track in res["hz"]]
            max_range_um = max(deepest_points)

            st.metric(label="Maximum Energy Peak Depth", value=f"{peak_depth:.3f} μm")
            st.write(f"📍 Resides inside: **{peak_layer}**")
            st.markdown("<br>", unsafe_allow_html=True)
            
            st.metric(label="Maximum Beam Penetration Range", value=f"{max_range_um:.3f} μm")
            st.markdown("<br>", unsafe_allow_html=True)
            
            st.metric(label="Total Absorbed Beam Energy Load", value=f"{total_deposited_energy_keV:,.1f} keV")

        with col_plot3:
            fig2, ax2 = plt.subplots(figsize=(10, 6.5))
            ax2.plot(res["depth_bins"], res["energy_dep"], color="#2af598", linewidth=2.5, label="Energy Deposited (keV)")
            ax2.fill_between(res["depth_bins"], res["energy_dep"], color="#2af598", alpha=0.15)
            ax2.axvline(peak_depth, color="#ff4b4b", linestyle="-.", alpha=0.7, label=f"Peak Dose ({peak_depth:.3f} μm)")
            
            prev_b = 0.0
            for idx, b in enumerate(res["boundaries"]):
                ax2.axvline(b, color="#ffffff", linestyle=":", alpha=0.5)
                prev_b = b
                
            ax2.set_xlabel("Depth Position inside Stack (μm)", color="#ffffff")
            ax2.set_ylabel("Total Dissipated Kinetic Energy (keV)", color="#ffffff")
            ax2.set_title("Energy Deposition Profile (Dose Spectrum)", fontsize=12, fontweight="bold", color="#00f3ff")
            ax2.set_xlim(0, max(res["boundaries"][-1], max_range_um * 1.05))
            ax2.grid(True, linestyle=":", alpha=0.2)
            ax2.legend(facecolor='#111827', edgecolor='none', labelcolor='#ffffff')
            
            fig2.patch.set_facecolor('#0b0f19')
            ax2.set_facecolor('#111827')
            ax2.tick_params(colors='#ffffff')
            st.pyplot(fig2)
            plt.close(fig2)