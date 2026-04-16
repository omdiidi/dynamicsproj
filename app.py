"""
ME 2030 Loop-the-Loop Prediction Tool
=====================================
Predicts minimum release heights for spheres completing a vertical circular
loop on a two-rail track. Built for the ME 2030 Spring 2026 term project.

Dynamics principles used:
  - Work-energy theorem (energy conservation)
  - Rotational dynamics (rolling without slipping)
  - Two-rail contact geometry (Bachman 1985)
  - Newton's second law (centripetal condition at loop top)

Run locally:  streamlit run app.py
Deploy:       see render.yaml
"""
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

from physics.constants import BALLS, G, RAIL_RADIUS, INCHES_TO_METERS, METERS_TO_INCHES
from physics.geometry import compute_contact_geometry, compute_effective_loop_radius
from physics.energy import (frictionless_block_height, flat_rolling_height,
                            two_rail_height, compute_all_predictions, compute_waterfall)
from physics.ode_model import simulate

# ============================================================
# Page Config
# ============================================================
st.set_page_config(page_title="Loop Predictor", layout="wide")

# ============================================================
# Apple Liquid Glass CSS
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="st-"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .stApp {
        background: linear-gradient(135deg, #F5F5F7 0%, #E8E8ED 50%, #F5F5F7 100%);
    }

    section[data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.72) !important;
        backdrop-filter: blur(20px) saturate(180%);
        -webkit-backdrop-filter: blur(20px) saturate(180%);
        border-right: 1px solid rgba(255, 255, 255, 0.3);
    }

    .stButton > button {
        background: linear-gradient(135deg, #0071E3 0%, #0077ED 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.6rem 1.4rem;
        font-weight: 500;
        transition: all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1);
        box-shadow: 0 2px 8px rgba(0, 113, 227, 0.3);
    }

    .stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 16px rgba(0, 113, 227, 0.4);
    }

    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.65);
        backdrop-filter: blur(12px);
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.4);
        padding: 1rem 1.2rem;
        box-shadow: 0 2px 16px rgba(0, 0, 0, 0.04);
    }

    h1, h2, h3 {
        color: #1D1D1F;
        font-weight: 600;
        letter-spacing: -0.02em;
    }

    h1 { font-size: 2.2rem; }

    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.15); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# Title
# ============================================================
st.title("Loop-the-Loop Predictor")
st.caption("ME 2030 Spring 2026 — Minimum release height prediction tool")

# ============================================================
# Sidebar: Inputs
# ============================================================
st.sidebar.header("Competition Inputs")
R_loop_in = st.sidebar.number_input("Loop Radius (inches)", min_value=1.0, max_value=20.0,
                                      value=5.0, step=0.1)
theta_deg = st.sidebar.slider("Ramp Angle (degrees)", min_value=5, max_value=80, value=30)

R_loop_interp = st.sidebar.selectbox("Loop Radius Measured To:",
    ["Inside surface of rails", "Rail centerline"],
    help="Based on project diagram, R appears measured to inside track surface")

# Apply interpretation correction
R_loop_effective_in = R_loop_in
if R_loop_interp == "Inside surface of rails":
    R_loop_effective_in = R_loop_in + RAIL_RADIUS * METERS_TO_INCHES

st.sidebar.header("Safety & Losses")
safety_margin_in = st.sidebar.slider("Safety Margin (inches)", 0.0, 3.0, 0.5, 0.1)
f_transition = st.sidebar.slider("Transition Loss Fraction", 0.0, 0.25, 0.05, 0.01,
    help="Fraction of KE lost at ramp-to-loop junction (Wang et al. 2021)")

st.sidebar.header("Rolling Resistance (C_rr)")
C_rr_overrides = {}
for bname, ball in BALLS.items():
    C_rr_overrides[bname] = st.sidebar.slider(
        f"C_rr - {bname}", min_value=0.0, max_value=0.20,
        value=ball.C_rr, step=0.001, format="%.3f")

# ============================================================
# Compute predictions
# ============================================================
R_loop_m = R_loop_effective_in * INCHES_TO_METERS
results = compute_all_predictions(R_loop_effective_in, theta_deg, BALLS,
                                   C_rr_overrides, f_transition, safety_margin_in)

# ============================================================
# Section 1: Competition Mode
# ============================================================
st.header("Predictions")

col1, col2, col3 = st.columns(3)
for col, bname in zip([col1, col2, col3], ["Steel", "Plastic", "Rubber"]):
    pred = results["balls"][bname]
    col.metric(label=f"{bname}", value=f'{pred["h_predicted_in"]:.1f} in',
               delta=f'{pred["h_min_in"] - results["ref_rolling_in"]:+.2f} vs rolling')

total = sum(results["balls"][n]["h_predicted_in"] for n in ["Steel", "Plastic", "Rubber"])
st.info(f"Competition Score (if all succeed): **{total:.1f}**  |  "
        f"Ref Block: {results['ref_block_in']:.1f} in  |  Ref Rolling: {results['ref_rolling_in']:.1f} in")

# ============================================================
# Section 2: Waterfall Breakdown (CENTERPIECE)
# ============================================================
st.header("How We Got These Numbers")
st.caption("Each step applies one physics correction. This chain IS the equation development for the appendix.")

waterfall_ball = st.selectbox("Show waterfall for:", list(BALLS.keys()), key="wf_ball")
ball_obj = BALLS[waterfall_ball]
steps = compute_waterfall(ball_obj, R_loop_m, theta_deg,
                          C_rr=C_rr_overrides[waterfall_ball],
                          f_transition=f_transition,
                          safety_margin_in=safety_margin_in)

# Waterfall table
wf_rows = []
for s in steps:
    wf_rows.append({
        "Step": s["step"],
        "Correction": s["name"],
        "h (in)": f'{s["h_in"]:.2f}',
        "Delta": f'{s["delta_in"]:+.2f}' if s["step"] > 1 else "base",
        "Principle": s["principle"][:90] + ("..." if len(s["principle"]) > 90 else ""),
        "Source": s["source"],
    })
st.dataframe(pd.DataFrame(wf_rows), use_container_width=True, hide_index=True)

# Waterfall cascade chart
fig_wf, ax_wf = plt.subplots(figsize=(10, 4))
fig_wf.patch.set_facecolor('#F5F5F7')
ax_wf.set_facecolor('#F5F5F7')

labels = [s["name"] for s in steps]
values = [s["h_in"] for s in steps]
deltas = [s["delta_in"] for s in steps]

colors = ["#0071E3", "#34C759", "#FF9500", "#FF3B30", "#AF52DE", "#8E8E93"]
bottoms = [0] + values[:-1]
for i, (label, val, delta, bottom) in enumerate(zip(labels, values, deltas, bottoms)):
    if i == 0:
        ax_wf.bar(i, val, color=colors[i % len(colors)], alpha=0.85, width=0.6)
    else:
        ax_wf.plot([i - 0.7, i - 0.3], [bottom, bottom], color='#6E6E73', lw=0.8, ls='--')
        ax_wf.bar(i, delta, bottom=bottom, color=colors[i % len(colors)], alpha=0.85, width=0.6)
    ax_wf.text(i, val + 0.1, f'{val:.2f}"', ha='center', fontsize=8, fontweight=500, color='#1D1D1F')

ax_wf.set_xticks(range(len(labels)))
ax_wf.set_xticklabels([l.replace(" ", "\n") for l in labels], fontsize=7)
ax_wf.set_ylabel("Height (inches)")
ax_wf.set_title(f"Prediction Waterfall — {waterfall_ball} Ball", fontweight=600)
ax_wf.grid(axis='y', alpha=0.2)
ax_wf.spines['top'].set_visible(False)
ax_wf.spines['right'].set_visible(False)
st.pyplot(fig_wf)
plt.close(fig_wf)

# Expandable derivation details
with st.expander("Full derivation details (for appendix)"):
    for s in steps:
        st.markdown(f"**Step {s['step']}: {s['name']}**")
        st.markdown(f"- Formula: `{s['formula']}`")
        st.markdown(f"- Principle: {s['principle']}")
        st.markdown(f"- Source: {s['source']}")
        st.markdown(f"- Result: **{s['h_in']:.3f} in** (delta: {s['delta_in']:+.3f} in)")
        st.markdown("---")

# ============================================================
# Section 3: Two-Rail Geometry
# ============================================================
st.header("Two-Rail Geometry")
geom_rows = []
for bname, ball in BALLS.items():
    geom = compute_contact_geometry(ball.radius_m)
    geom_rows.append({
        "Ball": bname,
        "R (mm)": f"{ball.radius_m*1000:.2f}",
        "r_eff (mm)": f"{geom['r_eff']*1000:.2f}",
        "h_offset (mm)": f"{geom['h_offset']*1000:.2f}",
        "R/r_eff": f"{ball.radius_m/geom['r_eff']:.3f}",
        "KE_factor": f"{geom['KE_factor']:.3f}",
        "KE vs flat": f"+{(geom['KE_factor']/1.4 - 1)*100:.0f}%",
    })
st.dataframe(pd.DataFrame(geom_rows), use_container_width=True, hide_index=True)

# ============================================================
# Section 4: Track Diagram
# ============================================================
st.header("Track Geometry")
fig_track, ax_track = plt.subplots(figsize=(10, 6))
fig_track.patch.set_facecolor('#F5F5F7')
ax_track.set_facecolor('#F5F5F7')

sample_geom = compute_contact_geometry(list(BALLS.values())[0].radius_m)
R_c_sample = R_loop_m - sample_geom["h_offset"]
theta_rad = np.radians(theta_deg)
h_pred_m = results["balls"]["Steel"]["h_min_m"]
L_ramp = h_pred_m / np.sin(theta_rad)

# Draw ramp
ramp_x = np.array([-L_ramp * np.cos(theta_rad), 0]) * 1000
ramp_y = np.array([h_pred_m + sample_geom["h_offset"] * np.cos(theta_rad),
                    sample_geom["h_offset"]]) * 1000
ax_track.plot(ramp_x, ramp_y, color='#1D1D1F', lw=2.5)

# Draw loop
phi_arr = np.linspace(0, 2 * np.pi, 200)
loop_cx = 0.0
loop_cy = (sample_geom["h_offset"] + R_c_sample) * 1000
loop_x = loop_cx + R_c_sample * 1000 * np.sin(phi_arr)
loop_y = loop_cy - R_c_sample * 1000 * np.cos(phi_arr)
ax_track.plot(loop_x, loop_y, color='#1D1D1F', lw=2.5)

# Ball at start
ax_track.plot(ramp_x[0], ramp_y[0], 'o', color='#0071E3', markersize=12, zorder=5)

# Annotations
ax_track.annotate(f'R = {R_loop_effective_in:.1f} in', xy=(loop_cx, loop_cy),
                  fontsize=10, ha='center', color='#0071E3', fontweight=500)
ax_track.annotate(f'h = {results["balls"]["Steel"]["h_predicted_in"]:.1f} in',
                  xy=(ramp_x[0], ramp_y[0] + 8), fontsize=9, color='#FF3B30',
                  ha='center', fontweight=500)
ax_track.set_aspect('equal')
ax_track.set_xlabel('x (mm)')
ax_track.set_ylabel('y (mm)')
ax_track.grid(True, alpha=0.15)
ax_track.spines['top'].set_visible(False)
ax_track.spines['right'].set_visible(False)
st.pyplot(fig_track)
plt.close(fig_track)

# ============================================================
# Section 5: Energy Breakdown
# ============================================================
st.header("Energy Breakdown")
fig_energy, ax_energy = plt.subplots(figsize=(10, 5))
fig_energy.patch.set_facecolor('#F5F5F7')
ax_energy.set_facecolor('#F5F5F7')
ball_names_list = ["Steel", "Plastic", "Rubber"]

for i, bname in enumerate(ball_names_list):
    pred = results["balls"][bname]
    ball_geom = compute_contact_geometry(BALLS[bname].radius_m)
    m = BALLS[bname].mass_kg
    v_top_sq = pred["v_top_sq"]
    KE_factor_val = pred["KE_factor"]

    total_E = m * G * pred["h_min_m"]
    PE_top = m * G * (2 * R_loop_m - 2 * ball_geom["h_offset"])
    KE_trans = 0.5 * m * v_top_sq
    KE_rot = 0.5 * m * v_top_sq * (KE_factor_val - 1)

    bottom_val = 0
    for label, val, color in [
        ("PE at top", PE_top, "#0071E3"),
        ("KE translational", KE_trans, "#34C759"),
        ("KE rotational", KE_rot, "#FF3B30"),
        ("Losses", max(total_E - PE_top - KE_trans - KE_rot, 0), "#8E8E93"),
    ]:
        pct = val / total_E * 100 if total_E > 0 else 0
        ax_energy.bar(i, pct, bottom=bottom_val, width=0.6,
                      label=label if i == 0 else "", color=color, alpha=0.85)
        bottom_val += pct

ax_energy.set_xticks(range(3))
ax_energy.set_xticklabels(ball_names_list)
ax_energy.set_ylabel("% of Release PE")
ax_energy.legend(loc='upper right')
ax_energy.spines['top'].set_visible(False)
ax_energy.spines['right'].set_visible(False)
st.pyplot(fig_energy)
plt.close(fig_energy)

# ============================================================
# Section 6: Simulator
# ============================================================
st.header("Simulation")
sim_col1, sim_col2 = st.columns([1, 1])
with sim_col1:
    sim_ball = st.selectbox("Ball", list(BALLS.keys()), key="sim_ball")
with sim_col2:
    sim_h_in = st.number_input("Release height (in)", min_value=1.0, max_value=50.0,
                                value=float(results["balls"][sim_ball]["h_predicted_in"]),
                                step=0.1)

if st.button("Run Simulation", type="primary"):
    ball = BALLS[sim_ball]
    geom = compute_contact_geometry(ball.radius_m)
    h_release_m = sim_h_in * INCHES_TO_METERS

    with st.spinner("Solving ODE..."):
        sim_result = simulate(ball.radius_m, ball.mass_kg, R_loop_m, theta_deg,
                              h_release_m, C_rr_overrides[sim_ball],
                              geom["KE_factor"], geom["h_offset"])

    if len(sim_result["v"]) == 0:
        st.error("Simulation returned no data. Check inputs.")
    elif sim_result["completed"]:
        st.success(f"Loop completed. Final speed: {sim_result['v'][-1]:.2f} m/s")
    else:
        st.error(f"Loop NOT completed. Reason: {sim_result.get('failure_reason', 'unknown')}")

    if len(sim_result["v"]) > 0:
        # Velocity + Normal Force plot
        fig_sim, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 5), sharex=True)
        fig_sim.patch.set_facecolor('#F5F5F7')
        ax1.set_facecolor('#F5F5F7')
        ax2.set_facecolor('#F5F5F7')

        s_mm = sim_result["s"] * 1000
        ax1.plot(s_mm, sim_result["v"], color=ball.color, lw=1.5)
        ax1.axvline(x=sim_result["L_ramp"] * 1000, color='#8E8E93', ls='--', lw=0.8,
                     label='Loop entry')
        ax1.set_ylabel("Speed (m/s)")
        ax1.legend(fontsize=8)

        ax2.plot(s_mm, sim_result["N"] * 1000, color=ball.color, lw=1.5)
        ax2.axhline(y=0, color='#FF3B30', ls='--', lw=0.8, alpha=0.6)
        ax2.axvline(x=sim_result["L_ramp"] * 1000, color='#8E8E93', ls='--', lw=0.8)
        ax2.set_ylabel("Normal Force (mN)")
        ax2.set_xlabel("Arc length (mm)")

        for ax in [ax1, ax2]:
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

        st.pyplot(fig_sim)
        plt.close(fig_sim)

        # Animation
        st.subheader("Animation")
        placeholder = st.empty()
        track_fn = sim_result["track_func"]
        s_track = np.linspace(0, sim_result["L_total"], 500)
        track_pts = np.array([track_fn(si)[:2] for si in s_track])

        skip = max(1, len(sim_result["t"]) // 40)  # ~40 frames for Render compat
        for idx in range(0, len(sim_result["t"]), skip):
            fig_a, ax_a = plt.subplots(figsize=(8, 6))
            fig_a.patch.set_facecolor('#F5F5F7')
            ax_a.set_facecolor('#F5F5F7')
            ax_a.plot(track_pts[:, 0] * 1000, track_pts[:, 1] * 1000,
                      color='#1D1D1F', lw=2)
            ax_a.plot(sim_result["x"][idx] * 1000, sim_result["y"][idx] * 1000, 'o',
                      color=ball.color, markersize=14, zorder=5)
            ax_a.set_aspect('equal')
            ax_a.set_xlabel('x (mm)')
            ax_a.set_ylabel('y (mm)')
            ax_a.set_title(
                f't={sim_result["t"][idx]:.3f}s   v={sim_result["v"][idx]:.2f} m/s   '
                f'N={sim_result["N"][idx]*1000:.1f} mN', fontsize=10)
            ax_a.grid(True, alpha=0.15)
            ax_a.spines['top'].set_visible(False)
            ax_a.spines['right'].set_visible(False)
            placeholder.pyplot(fig_a)
            plt.close(fig_a)
            time.sleep(0.03)

# ============================================================
# Section 7: Memo Comparison Table (R=5in, theta=20 and 50)
# ============================================================
st.header("Memo Reference Tables")
st.caption("Required for memo section II: R_loop=5 in, theta = 20 and 50 degrees")

memo_R = 5.0
memo_rows = []
for theta_val in [20, 50]:
    mr = compute_all_predictions(memo_R, theta_val, BALLS, C_rr_overrides, f_transition, 0)
    bh = mr["ref_block_in"]
    rh = mr["ref_rolling_in"]
    row = {"Angle": f"{theta_val} deg", "Block": f"{bh:.2f}", "Rolling": f"{rh:.2f}"}
    for bname in ["Steel", "Plastic", "Rubber"]:
        h = mr["balls"][bname]["h_min_in"]
        row[bname] = f"{h:.2f}"
        row[f"{bname} vs Roll"] = f"{h - rh:+.2f}"
    memo_rows.append(row)

st.dataframe(pd.DataFrame(memo_rows), use_container_width=True, hide_index=True)

# ============================================================
# Section 8: Sensitivity Analysis
# ============================================================
st.header("Sensitivity Analysis")
st.caption("Parameter uncertainty impact on predictions")

sens_rows = []
for bname in ["Steel", "Plastic", "Rubber"]:
    base = results["balls"][bname]["h_min_in"]
    crr_base = C_rr_overrides[bname]

    p_lo = two_rail_height(BALLS[bname], R_loop_m, theta_deg,
                            C_rr=crr_base * 0.5, f_transition=f_transition)
    p_hi = two_rail_height(BALLS[bname], R_loop_m, theta_deg,
                            C_rr=crr_base * 1.5, f_transition=f_transition)

    # Alternative R_loop interpretation
    if R_loop_interp == "Rail centerline":
        R_alt = (R_loop_in + RAIL_RADIUS * METERS_TO_INCHES) * INCHES_TO_METERS
    else:
        R_alt = R_loop_in * INCHES_TO_METERS
    p_alt = two_rail_height(BALLS[bname], R_alt, theta_deg,
                             C_rr=crr_base, f_transition=f_transition)

    sens_rows.append({
        "Ball": bname,
        "Base (in)": f"{base:.2f}",
        "C_rr -50%": f"{p_lo['h_min_in']:.2f} ({p_lo['h_min_in']-base:+.2f})",
        "C_rr +50%": f"{p_hi['h_min_in']:.2f} ({p_hi['h_min_in']-base:+.2f})",
        "Alt R interp": f"{p_alt['h_min_in']:.2f} ({p_alt['h_min_in']-base:+.2f})",
    })

st.dataframe(pd.DataFrame(sens_rows), use_container_width=True, hide_index=True)
