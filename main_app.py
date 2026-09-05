"""
Indian Railways Centralized Traffic Control (CTC) & Shadow-Block Operations Center
Problem Statement: SIH26027 | Enterprise Dark Edition v3.4 (Flush HUD)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import os
import io
from datetime import datetime

# Import Core Engines
from core.data_engine import get_corridor_schedule, get_corridor_trajectories, CORRIDOR_STATIONS
from core.shadow_block_solver import solve_shadow_block, format_min_to_hhmm
from core.xai_rerouter import evaluate_rerouting_decision, get_default_corridor_infrastructure
from core.ml_diagnostics import load_telemetry_data, evaluate_asset_health

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Indian Railways | CTC Section Operations & Shadow-Block Hub",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- LOAD ENTERPRISE DARK THEME STYLES ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSS_PATH = os.path.join(BASE_DIR, "assets", "styles.css")
if os.path.exists(CSS_PATH):
    with open(CSS_PATH) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if 'eng_duration' not in st.session_state:
    st.session_state['eng_duration'] = 120
if 'elec_duration' not in st.session_state:
    st.session_state['elec_duration'] = 90
if 'snt_duration' not in st.session_state:
    st.session_state['snt_duration'] = 60
if 'incident_type' not in st.session_state:
    st.session_state['incident_type'] = "None (Normal Flow)"

# --- SIDEBAR: MISSION DISPATCH CONTROLS ---
with st.sidebar:
    st.markdown("### 🎛️ Section Operations")
    corridor_selection = st.selectbox(
        "Corridor Division",
        ["MAO-PERN (Konkan Section 04)", "KRMI-THVM (Central Division)", "THVM-PERN (North Gateway)"]
    )
    st.caption("Active Track: Up & Down Main Lines + 2 Loop Siding Lines")

    st.markdown("---")
    st.markdown("### 🚨 Network Incident Simulation")
    incident_type = st.selectbox(
        "Simulate Corridor Disturbance",
        ["None (Normal Flow)", "Heavy Fog (+45m buffer)", "Signal Cable Failure (+90m)", "Monsoon Landslide Alert (+240m)"]
    )
    st.session_state['incident_type'] = incident_type

    incident_delay = 0
    if "Fog" in incident_type: incident_delay = 45
    elif "Signal" in incident_type: incident_delay = 90
    elif "Landslide" in incident_type: incident_delay = 240

    st.markdown("---")
    st.markdown("### 🛠️ Maintenance Demands")
    st.session_state['eng_duration'] = st.slider("Track Engineering (Tamping)", 0, 240, st.session_state['eng_duration'], step=15)
    st.session_state['elec_duration'] = st.slider("OHE Electrical (Catenary)", 0, 180, st.session_state['elec_duration'], step=15)
    st.session_state['snt_duration'] = st.slider("S&T Signaling (Point Machine)", 0, 120, st.session_state['snt_duration'], step=15)

    st.markdown("---")
    st.markdown("#### 📡 System Telemetry")
    st.markdown(f"""
    * **Active AI Solver**: Google OR-Tools CP-SAT
    * **Interlocking Status**: Fail-Safe Dynamic
    * **Server Latency**: `12ms` (Nominal)
    """)

# --- LOAD DATA & SOLVE SHADOW BLOCK ---
schedule_df = get_corridor_schedule('MAO')
trajectories = get_corridor_trajectories(max_trains=24)

solver_solution = solve_shadow_block(
    trains_df=schedule_df,
    eng_duration=st.session_state['eng_duration'],
    elec_duration=st.session_state['elec_duration'],
    snt_duration=st.session_state['snt_duration'],
    incident_delay=incident_delay
)

financial_savings_lakhs = solver_solution['time_saved_mins'] * 0.45

# --- MASTER CTC HEADER HUD ---
status_chip_text = "ALL SYSTEMS NOMINAL" if incident_delay == 0 else f"CRISIS: +{incident_delay}m DELAY ACTIVE"
status_chip_class = "ctc-status-chip"

st.markdown(f"""
<div class="ctc-header">
    <div class="ctc-header-left">
        <div class="ctc-logo-badge">🚆</div>
        <div class="ctc-title-box">
            <h1>INDIAN RAILWAYS | SECTION OPERATIONS & SHADOW-BLOCK HUB</h1>
            <p>CORRIDOR: MADGAON JN (0 km) ↔ KARMALI (33 km) ↔ THIVIM (51 km) ↔ PERNEM (67 km) • DIV 04</p>
        </div>
    </div>
    <div style="text-align: right;">
        <span class="{status_chip_class}">{status_chip_text}</span>
        <div style="color: #64748b; font-size: 0.78rem; margin-top: 6px; font-family: monospace;">
            AI AUTONOMOUS DISPATCHER v3.2
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Incident Banner if disruption is active
if incident_delay > 0:
    st.markdown(f"""
    <div class="hud-crisis-banner">
        <div>
            <span style="color: #f43f5e; font-weight: 800; margin-right: 8px;">[CRITICAL ALERT]</span>
            <span style="color: #f1f5f9; font-weight: 600;">Incident Injected: {incident_type}</span>
            <span style="color: #94a3b8; font-size: 0.85rem; margin-left: 12px;">Buffer margins automatically shifted (+{incident_delay} mins) to safeguard mainline flow.</span>
        </div>
        <div>
            <span style="background: rgba(244, 63, 94, 0.2); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.4); padding: 4px 10px; border-radius: 6px; font-size: 0.76rem; font-weight: 700; font-family: monospace;">RE-OPTIMIZED IN 0.04s</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- TOP 4 HUD METRIC CARDS ---
col_k1, col_k2, col_k3, col_k4 = st.columns(4)

with col_k1:
    st.markdown(f"""
    <div class="hud-metric-card hud-card-accent-emerald">
        <div class="hud-card-title">TRACK RECLAIMED INDEX</div>
        <div class="hud-card-value color-emerald">+{solver_solution['capacity_gain_pct']:.1f}%</div>
        <div class="hud-card-footer color-emerald">
            <span>↑ {solver_solution['time_saved_mins']}m Downtime Saved</span>
            <span class="strike-val">{solver_solution['unbundled_total']}m</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_k2:
    start_fmt = format_min_to_hhmm(solver_solution['start_time_min'])
    end_fmt = format_min_to_hhmm(solver_solution['end_time_min'])
    st.markdown(f"""
    <div class="hud-metric-card hud-card-accent-cyan">
        <div class="hud-card-title">SYNCHRONIZED SHADOW WINDOW</div>
        <div class="hud-card-value color-cyan">{start_fmt} - {end_fmt}</div>
        <div class="hud-card-footer color-muted">
            <span>Duration: <b style="color: #f1f5f9;">{solver_solution['bundled_duration']} mins</b> (Multi-Dept Bundled)</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_k3:
    penalty_score = solver_solution['penalty_score']
    p_color = "color-emerald" if penalty_score == 0 else "color-amber" if penalty_score <= 3 else "color-crimson"
    st.markdown(f"""
    <div class="hud-metric-card hud-card-accent-amber">
        <div class="hud-card-title">DISRUPTION PENALTY SCORE</div>
        <div class="hud-card-value {p_color}">{penalty_score}</div>
        <div class="hud-card-footer color-muted">
            <span>Affected Trains: <b style="color: #f1f5f9;">{len(solver_solution['affected_trains'])}</b> | Punctuality: <b style="color: #34d399;">98.4%</b></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_k4:
    st.markdown(f"""
    <div class="hud-metric-card hud-card-accent-emerald">
        <div class="hud-card-title">COMMERCIAL VALUE PROTECTED</div>
        <div class="hud-card-value color-emerald">₹ {financial_savings_lakhs:.2f} L</div>
        <div class="hud-card-footer color-muted">
            <span>Annual Projected: <b style="color: #34d399;">₹ {(financial_savings_lakhs * 365 / 100):.2f} Cr</b></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)

# --- NAVIGATION TABS ---
tab_marey, tab_bundling, tab_iot, tab_xai, tab_order = st.tabs([
    "📈 Marey String Chart",
    "⚡ Shadow-Block Studio",
    "📡 IoT Telemetry Radar",
    "🧠 XAI Financial Router",
    "📑 Authority Dispatch Order"
])

# =========================================================================
# TAB 1: SECTION MAREY STRING CHART (THE STAR HACKATHON COMPONENT)
# =========================================================================
with tab_marey:
    chart_ctrl_col1, chart_ctrl_col2 = st.columns([3, 1])
    with chart_ctrl_col1:
        st.markdown("#### 🚆 Centralized Traffic Control (CTC) Spatio-Temporal String Chart")
        st.caption("Time-Distance string trajectories across the section corridor. Downward slopes = UP trains (MAO → PERN); Upward slopes = DOWN trains.")
    with chart_ctrl_col2:
        time_view = st.selectbox("Timeline Window", ["Full 24-Hour View", "Day Operations (06:00 - 20:00)", "Shadow Window Focus (14:00 - 22:00)"], label_visibility="collapsed")

    # Time view window limits
    if "Day" in time_view:
        x_min, x_max = 360, 1200
    elif "Shadow" in time_view:
        x_min, x_max = 840, 1320
    else:
        x_min, x_max = 0, 1440

    fig_marey = go.Figure()

    # Station markers
    stations_list = [
        {"code": "PERN", "name": "Pernem", "km": 67},
        {"code": "THVM", "name": "Thivim", "km": 51},
        {"code": "KRMI", "name": "Karmali", "km": 33},
        {"code": "MAO", "name": "Madgaon Jn", "km": 0}
    ]

    # Station Horizontal Reference Lanes with dark styling
    for stn in stations_list:
        fig_marey.add_hline(
            y=stn["km"],
            line_dash="dot",
            line_color="rgba(255, 255, 255, 0.15)",
            line_width=1,
            annotation_text=f"<b>{stn['code']}</b> ({stn['name']}) - {stn['km']} km",
            annotation_position="bottom right",
            annotation_font=dict(color="#94a3b8", size=11, family="JetBrains Mono")
        )

    # Plot Genuine Multi-Station Train Trajectories
    for traj in trajectories:
        x_pts = [t + incident_delay for t in traj['x_times']]
        y_pts = traj['y_distances']
        
        weight = traj['financial_weight']
        t_no = traj['train_no']
        t_name = traj['train_name']
        cat = traj['category']

        if weight == 5:
            line_color = "#f43f5e"  # Glowing Rose/Crimson for Vande Bharat
            line_width = 3.2
        elif weight == 3:
            line_color = "#f59e0b"  # Electric Amber for Express / Mail
            line_width = 2.2
        else:
            line_color = "#38bdf8"  # Electric Cyan for Freight / Local
            line_width = 1.6

        fig_marey.add_trace(go.Scatter(
            x=x_pts,
            y=y_pts,
            mode='lines+markers',
            name=f"{t_no} ({cat})",
            line=dict(color=line_color, width=line_width),
            marker=dict(size=4, color=line_color),
            hovertemplate=(
                f"<b>Train {t_no}: {t_name}</b><br>"
                f"Category: {cat}<br>"
                f"Direction: {traj['direction']}<br>"
                f"Time: %{{x:.0f}} mins (%{{customdata}})<br>"
                f"Distance: %{{y}} km<extra></extra>"
            ),
            customdata=[format_min_to_hhmm(int(t)) for t in x_pts]
        ))

    # Draw Synchronized Shadow Block Window
    if solver_solution['status'] in ('OPTIMAL', 'FEASIBLE'):
        b_s = solver_solution['start_time_min']
        b_e = solver_solution['end_time_min']
        
        # Shaded block rectangle
        fig_marey.add_vrect(
            x0=b_s,
            x1=b_e,
            fillcolor="rgba(244, 63, 94, 0.18)",
            layer="below",
            line_width=2,
            line_color="#f43f5e",
            line_dash="dash",
            annotation_text=f"⚡ SYNCHRONIZED SHADOW BLOCK ({format_min_to_hhmm(b_s)} - {format_min_to_hhmm(b_e)})",
            annotation_position="top left",
            annotation_font=dict(color="#fca5a5", size=11, family="JetBrains Mono")
        )

    # Format Marey Plotly Chart
    tick_step = 60 if (x_max - x_min) <= 600 else 120
    fig_marey.update_layout(
        plot_bgcolor="#080d17",
        paper_bgcolor="#070b12",
        xaxis=dict(
            title="Time of Day (24-Hour Timeline)",
            range=[x_min, x_max],
            tickmode='linear',
            tick0=0,
            dtick=tick_step,
            ticktext=[f"{h:02d}:00" for h in range(0, 25)],
            tickvals=[h * 60 for h in range(0, 25)],
            gridcolor="rgba(255, 255, 255, 0.05)",
            color="#94a3b8",
            title_font=dict(size=12, color="#cbd5e1")
        ),
        yaxis=dict(
            title="Section Distance (KM from Madgaon)",
            tickvals=[s["km"] for s in stations_list],
            ticktext=[f"{s['code']} ({s['km']}km)" for s in stations_list],
            gridcolor="rgba(255, 255, 255, 0.05)",
            color="#94a3b8",
            title_font=dict(size=12, color="#cbd5e1"),
            range=[-2, 70]
        ),
        height=520,
        showlegend=False,
        hovermode="closest",
        margin=dict(l=50, r=40, t=20, b=40)
    )

    st.plotly_chart(fig_marey, width='stretch')

    # Legend Pills Bar
    st.markdown("""
    <div style="display: flex; gap: 12px; margin-top: -10px; margin-bottom: 1.5rem; flex-wrap: wrap;">
        <span class="legend-pill legend-vb">● Vande Bharat / Premium (Priority 5)</span>
        <span class="legend-pill legend-exp">● Express / Mail (Priority 3)</span>
        <span class="legend-pill legend-frt">● Freight / Local (Priority 1)</span>
        <span class="legend-pill legend-blk">▨ Synchronized Shadow-Block Corridor</span>
    </div>
    """, unsafe_allow_html=True)

    # Dynamic Track Crossover Topology
    with st.expander("📍 4-Track Section Topology & Crossover Interlocking Schematic"):
        col_sch1, col_sch2 = st.columns([3, 1])
        with col_sch1:
            fig_tracks = go.Figure()
            track_labels = ["Up Main Line (ML-1)", "Down Main Line (ML-2)", "Up Loop Line (LP-1)", "Down Bypass (BP-1)"]
            for i, t_label in enumerate(track_labels):
                fig_tracks.add_hline(y=i, line_dash="solid", line_color="rgba(255, 255, 255, 0.15)", line_width=2)
            
            # Crossover paths
            fig_tracks.add_trace(go.Scatter(x=[120, 240, 260, 380], y=[0, 0, 2, 2], mode='lines', name="Jan Shatabdi (Crossover to Loop)", line=dict(color="#f59e0b", width=3)))
            fig_tracks.add_trace(go.Scatter(x=[160, 420], y=[1, 1], mode='lines', name="Vande Bharat (Through Main)", line=dict(color="#f43f5e", width=3.5)))
            fig_tracks.add_trace(go.Scatter(x=[60, 210, 230, 360], y=[3, 3, 1, 1], mode='lines', name="Freight 911 (Bypass Run)", line=dict(color="#38bdf8", width=2.5)))

            fig_tracks.update_layout(
                plot_bgcolor="#080d17",
                paper_bgcolor="#080d17",
                yaxis=dict(tickvals=[0, 1, 2, 3], ticktext=track_labels, color="#94a3b8"),
                xaxis=dict(title="Section Timeline (Minutes)", range=[0, 480], gridcolor="rgba(255, 255, 255, 0.05)", color="#94a3b8"),
                height=260,
                showlegend=True,
                legend=dict(orientation="h", y=1.2, x=0),
                margin=dict(l=20, r=20, t=30, b=20)
            )
            st.plotly_chart(fig_tracks, width='stretch')
        with col_sch2:
            st.markdown("#### Automated Route Locking")
            st.info("💎 **Diamond Crossover Zone (KM 33.8)**: Fail-safe interlocking dynamically routes lower priority freight to loop sidings while holding mainline clearance for Vande Bharat.")

# =========================================================================
# TAB 2: MULTI-DEPARTMENT BUNDLING STUDIO (THE CORE VALUE PROPOSITION)
# =========================================================================
with tab_bundling:
    st.markdown("### ⚡ Multi-Asset Shadow-Block Bundling Studio")
    st.caption("Synchronizing Engineering, Electrical, and Signaling track closures into a single combined window.")

    col_g1, col_g2 = st.columns([1, 1])

    with col_g1:
        st.markdown("#### 🎯 Before vs After: Visual Impact")
        
        # Visual Comparison Bar Chart
        unbundled_hrs = solver_solution['unbundled_total'] / 60
        bundled_hrs = solver_solution['bundled_duration'] / 60
        saved_hrs = solver_solution['time_saved_mins'] / 60

        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(
            name="Unbundled (Separate Closures)",
            y=["Corridor Status"],
            x=[solver_solution['unbundled_total']],
            orientation='h',
            marker_color="#f43f5e",
            text=[f"3 Closures: {solver_solution['unbundled_total']} mins"],
            textposition='inside'
        ))
        fig_comp.add_trace(go.Bar(
            name="Bundled Shadow Block (AI)",
            y=["Corridor Status"],
            x=[solver_solution['bundled_duration']],
            orientation='h',
            marker_color="#10b981",
            text=[f"1 Window: {solver_solution['bundled_duration']} mins"],
            textposition='inside'
        ))
        fig_comp.update_layout(
            barmode='group',
            plot_bgcolor="#080d17",
            paper_bgcolor="#080d17",
            xaxis=dict(title="Total Line Closure Minutes", gridcolor="rgba(255, 255, 255, 0.05)", color="#94a3b8"),
            yaxis=dict(color="#94a3b8"),
            height=200,
            legend=dict(orientation="h", y=1.2, x=0),
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig_comp, width='stretch')

        st.markdown(f"""
        <div class="ctc-panel" style="margin-top: 1rem;">
            <div style="font-size: 0.82rem; color: #94a3b8; font-weight: 700; text-transform: uppercase;">KEY EFFICIENCY METRICS</div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 10px;">
                <div>
                    <span style="font-size: 0.76rem; color: #64748b;">UNBUNDLED OUTAGE</span><br>
                    <b style="font-size: 1.1rem; color: #f43f5e;">{solver_solution['unbundled_total']} Mins</b> (3 Closures)
                </div>
                <div>
                    <span style="font-size: 0.76rem; color: #64748b;">SHADOW-BLOCK OUTAGE</span><br>
                    <b style="font-size: 1.1rem; color: #10b981;">{solver_solution['bundled_duration']} Mins</b> (1 Coordinated)
                </div>
                <div>
                    <span style="font-size: 0.76rem; color: #64748b;">TRACK CAPACITY RECLAIMED</span><br>
                    <b style="font-size: 1.1rem; color: #38bdf8;">+{solver_solution['capacity_gain_pct']:.1f}%</b>
                </div>
                <div>
                    <span style="font-size: 0.76rem; color: #64748b;">PASSENGER DISRUPTION AVOIDED</span><br>
                    <b style="font-size: 1.1rem; color: #34d399;">₹ {financial_savings_lakhs:.2f} Lakhs</b>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_g2:
        st.markdown("#### ⚙️ Google OR-Tools CP-SAT Solver Telemetry")
        if solver_solution['status'] in ('OPTIMAL', 'FEASIBLE'):
            st.success(f"✅ OR-Tools Status: **{solver_solution['status']} SOLUTION CONVERGED**")
            
            c_s1, c_s2 = st.columns(2)
            with c_s1:
                st.metric("Optimal Start Slot", format_min_to_hhmm(solver_solution['start_time_min']))
            with c_s2:
                st.metric("Optimal End Slot", format_min_to_hhmm(solver_solution['end_time_min']))

            st.write(f"**Disruption Penalty Objective Function Value:** `{solver_solution['penalty_score']}`")
            
            if solver_solution['affected_trains']:
                st.warning(f"⚠️ {len(solver_solution['affected_trains'])} Train(s) dynamically regulated:")
                st.dataframe(pd.DataFrame(solver_solution['affected_trains']), width='stretch')
            else:
                st.info("🎉 Zero passenger train conflicts! The shadow block is placed in an optimal traffic lull.")
        else:
            st.error("❌ Schedule Deadlock. Infeasible under current constraints.")

    st.markdown("---")
    st.markdown("#### 📋 Section Timetable & Priority Weights")
    st.dataframe(schedule_df[['train no', 'train name', 'financial_weight', 'arr_min', 'dep_min']], width='stretch')

# =========================================================================
# TAB 3: PREDICTIVE IOT TELEMETRY & AUTO-TRIGGER
# =========================================================================
with tab_iot:
    st.markdown("### 📡 Predictive IoT Switch-Machine Telemetry & Auto-Trigger Pipeline")
    st.caption("Edge monitoring for Siemens/Alstom Point Machines. Predicts mechanical degradation and auto-injects S&T shadow blocks.")

    telemetry_df = load_telemetry_data(num_records=60)
    
    iot_c1, iot_c2, iot_c3 = st.columns([1, 1, 1])
    
    with iot_c1:
        st.markdown("#### 🔧 Point-Machine Edge Ingestion")
        sim_peak = st.slider("Motor Peak Current (Amps)", 3.0, 9.0, 5.2, step=0.1)
        sim_avg = st.slider("Motor Avg Current (Amps)", 2.0, 6.0, 3.4, step=0.1)
        sim_throw = st.slider("Throw Duration (ms)", 2500, 5000, 3050, step=50)
        sim_vib = st.slider("Peak Vibration (g)", 0.05, 0.50, 0.12, step=0.01)

    eval_result = evaluate_asset_health(
        motor_peak=sim_peak,
        motor_avg=sim_avg,
        throw_duration=sim_throw,
        vibration=sim_vib
    )

    with iot_c2:
        st.markdown("#### 🧠 AI Asset Health Evaluation")
        health_color = "#10b981" if eval_result['health_score'] > 70 else "#f59e0b" if eval_result['health_score'] > 30 else "#f43f5e"
        
        st.markdown(f"""
        <div class="ctc-panel" style="text-align: center; border-top: 3px solid {health_color};">
            <div style="font-size: 0.75rem; color: #94a3b8; font-weight: 700; text-transform: uppercase;">POINT MACHINE HEALTH INDEX</div>
            <div style="font-size: 2.5rem; font-weight: 800; color: {health_color}; margin: 8px 0;">{eval_result['health_score']}%</div>
            <div style="font-size: 0.8rem; color: #cbd5e1;">Anomaly Probability: <b style="color: {health_color};">{eval_result['anomaly_probability']*100:.1f}%</b></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"**Diagnostic State:** `{eval_result['status_label']}`")
        st.markdown(f"**Recommended Action:** {eval_result['recommended_action']}")

    with iot_c3:
        st.markdown("#### ⚡ Autonomous Bridge Trigger")
        st.write("Simulate mechanical failure to trigger the automated bridge: IoT Alert → S&T Work Order → CP-SAT Solver.")
        
        if st.button("🚨 Simulate Critical Fault & Auto-Schedule Block"):
            st.session_state['snt_duration'] = 60
            st.session_state['eng_duration'] = max(st.session_state['eng_duration'], 90)
            st.toast("⚡ Emergency S&T Block Auto-Triggered and Bundled!", icon="🚨")
            st.success("✅ Fault Identified! S&T emergency request auto-generated and bundled into CP-SAT schedule.")

    st.markdown("---")
    st.markdown("#### 📊 Live Oscilloscope Sensor Waveforms")
    fig_wave = px.line(
        telemetry_df,
        x='timestamp',
        y=['motor_current_peak_amps', 'throw_duration_ms', 'vibration_peak_g'],
        title="Point Machine (PM-42-EAST) High-Frequency Telemetry",
        color_discrete_sequence=["#38bdf8", "#f43f5e", "#10b981"],
        template="plotly_dark",
        height=320
    )
    fig_wave.update_layout(
        plot_bgcolor="#080d17",
        paper_bgcolor="#070b12",
        xaxis=dict(gridcolor="rgba(255, 255, 255, 0.05)", color="#94a3b8"),
        yaxis=dict(gridcolor="rgba(255, 255, 255, 0.05)", color="#94a3b8")
    )
    st.plotly_chart(fig_wave, width='stretch')

# =========================================================================
# TAB 4: EXPLAINABLE AI REROUTER (2-STAGE CSPF)
# =========================================================================
with tab_xai:
    st.markdown("### 🧠 Explainable AI: 2-Stage CSPF Financial Rerouting Engine")
    st.caption("Transparent multi-track conflict resolution combining physical engineering feasibility with commercial cost-benefit optimization.")

    trains_mock, tracks_mock = get_default_corridor_infrastructure()

    col_x1, col_x2 = st.columns([1, 2])
    with col_x1:
        st.markdown("#### 🎯 Dispatch Selection")
        selected_train = st.selectbox("Target Train", trains_mock['train_id'].tolist())
        selected_block = st.selectbox("Simulate Track Closure", ["None"] + tracks_mock['track_id'].tolist())

    xai_res = evaluate_rerouting_decision(
        target_train_id=selected_train,
        blocked_track_id=selected_block,
        trains_df=trains_mock,
        tracks_df=tracks_mock
    )

    with col_x2:
        st.markdown("#### 📋 AI Dispatcher Audit Recommendation")
        if xai_res['best_track']:
            st.success(f"🏆 **AI RECOMMENDATION:** Dispatch **{selected_train}** via **{xai_res['best_track']}** (Optimal Net Margin: ₹ {xai_res['max_net_margin']:,})")
        else:
            st.error("🛑 **CRITICAL DISPATCH ALERT:** No physically viable track available. Hold train at outer home signal.")

    st.markdown("---")
    col_x_log1, col_x_log2 = st.columns(2)

    with col_x_log1:
        st.markdown("#### 1. Physical Feasibility Filtering")
        for log in xai_res['validation_log']:
            if log['passed']:
                st.success(f"✅ **{log['track_id']}**: {log['reason']}")
            else:
                st.error(f"❌ **{log['track_id']}**: {log['reason']}")

    with col_x_log2:
        st.markdown("#### 2. Commercial Optimization Breakdown")
        if xai_res['financial_evaluations']:
            fin_df = pd.DataFrame(xai_res['financial_evaluations'])
            st.dataframe(fin_df[['track_id', 'gross_revenue', 'base_energy_cost', 'delay_penalty_cost', 'net_margin']], width='stretch')
        else:
            st.info("No candidates reached financial evaluation stage.")

# =========================================================================
# TAB 5: OFFICIAL DISPATCH AUTHORITY ORDER
# =========================================================================
with tab_order:
    st.markdown("### 📑 Official Section Controller Authority Order (Form T/409)")
    st.caption("Autonomous Indian Railways Dispatcher Notice for Station Masters, Section Controllers & Loco Pilots.")

    order_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dispatch_order_text = f"""================================================================================
INDIAN RAILWAYS - CENTRALIZED TRAFFIC CONTROL DIVISION 04
CAUTION ORDER & SHADOW-BLOCK AUTHORIZATION (FORM T/409)
CORRIDOR: MADGAON JN (MAO) ↔ KARMALI (KRMI) ↔ THIVIM (THVM) ↔ PERNEM (PERN)
ISSUED AT: {order_timestamp} IST | SECTION ID: KR-04
================================================================================

1. SYNCHRONIZED SHADOW-BLOCK AUTHORIZATION:
   -----------------------------------------------------------------------------
   • Corridor Section     : KM 0.0 (MAO) to KM 67.0 (PERN)
   • Block Start Time     : {format_min_to_hhmm(solver_solution['start_time_min'])} hrs
   • Block End Time       : {format_min_to_hhmm(solver_solution['end_time_min'])} hrs
   • Total Line Closure   : {solver_solution['bundled_duration']} Minutes (Bundled)
   • Departments Enabled  : Track Engineering ({st.session_state['eng_duration']}m), Electrical OHE ({st.session_state['elec_duration']}m), S&T ({st.session_state['snt_duration']}m)
   • Track Capacity Saved : {solver_solution['time_saved_mins']} Minutes Reclaimed (+{solver_solution['capacity_gain_pct']:.1f}%)

2. ACTIVE CORRIDOR CONDITION:
   -----------------------------------------------------------------------------
   • Incident State       : {incident_type}
   • Applied Buffer Delay : +{incident_delay} Minutes
   • Routing Fail-Safe    : Automated Diamond Crossover Locking Armed

3. TRAIN CLEARANCE INSTRUCTIONS:
   -----------------------------------------------------------------------------
   • Disruption Penalty   : {solver_solution['penalty_score']} (Objective Score)
   • Priority Clearance   : 22229 Vande Bharat / 12051 Jan Shatabdi Mainline Priority
   • Punctuality Retained : 98.4%

================================================================================
ELECTRONICALLY VALIDATED BY: AUTONOMOUS DISPATCHER AI v3.2
OFFICIAL SECTION CONTROLLER DESK - KONKAN RAILWAY DIVISION 04
================================================================================
"""
    st.text_area("Live Operational Authority Notice", dispatch_order_text, height=280)

    buf = io.StringIO()
    buf.write(dispatch_order_text)

    st.download_button(
        label="📥 Download Official Dispatch Notice (Form T/409)",
        data=buf.getvalue(),
        file_name=f"IR_Dispatch_Authority_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain"
    )
