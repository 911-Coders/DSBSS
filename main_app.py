"""
Indian Railways - Section Operations & Maintenance Hub
Clean, professional dashboard for section controllers and maintenance planning.
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
    page_title="Railway Section Operations & Shadow-Block Hub",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- LOAD CLEAN THEME STYLES ---
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
    st.session_state['incident_type'] = "None (Normal)"

# --- SIDEBAR: SETTINGS & CONTROLS ---
with st.sidebar:
    st.markdown("### Settings")
    corridor_selection = st.selectbox(
        "Section",
        ["Madgaon – Pernem (Konkan Section 04)", "Karmali – Thivim (Central)", "Thivim – Pernem (North)"]
    )
    st.caption("Double track main line with loop sidings")

    st.markdown("---")
    st.markdown("### Simulate Disruption")
    incident_type = st.selectbox(
        "Incident Type",
        ["None (Normal)", "Heavy Fog (+45 min delay)", "Signal Failure (+90 min delay)", "Landslide Alert (+240 min delay)"]
    )
    st.session_state['incident_type'] = incident_type

    incident_delay = 0
    if "Fog" in incident_type:
        incident_delay = 45
    elif "Signal" in incident_type:
        incident_delay = 90
    elif "Landslide" in incident_type:
        incident_delay = 240

    st.markdown("---")
    st.markdown("### Maintenance Duration")
    st.session_state['eng_duration'] = st.slider("Track Work (mins)", 0, 240, st.session_state['eng_duration'], step=15)
    st.session_state['elec_duration'] = st.slider("Overhead Electrical (mins)", 0, 180, st.session_state['elec_duration'], step=15)
    st.session_state['snt_duration'] = st.slider("Signaling & Telecom (mins)", 0, 120, st.session_state['snt_duration'], step=15)

    total_requested_work = st.session_state['eng_duration'] + st.session_state['elec_duration'] + st.session_state['snt_duration']
    st.caption(f"Total separate work time: {total_requested_work} mins")

# --- LOAD DATA & SOLVE SCHEDULE ---
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

# --- HEADER PANEL ---
status_text = "Normal Operations" if incident_delay == 0 else f"Disruption Active (+{incident_delay} min delay)"
status_class = "" if incident_delay == 0 else "warning"

st.markdown(f"""
<div class="dash-header">
    <div class="dash-header-left">
        <div class="dash-logo-icon">🚆</div>
        <div class="dash-title-box">
            <h1>Section Operations & Shadow-Block Hub</h1>
            <p>Madgaon Jn (0 km) — Karmali (33 km) — Thivim (51 km) — Pernem (67 km) · Section 04</p>
        </div>
    </div>
    <div>
        <div class="dash-status-pill {status_class}">
            <span class="dash-status-dot"></span>
            <span>{status_text}</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Disruption notice banner
if incident_delay > 0:
    st.markdown(f"""
    <div class="dash-notice-bar">
        <div>
            <strong style="color: #fb7185; margin-right: 8px;">Active Delay:</strong>
            <span>{incident_type}</span>
            <span style="color: #94a3b8; margin-left: 12px;">Train schedules adjusted by +{incident_delay} minutes to maintain safety buffers.</span>
        </div>
        <span style="color: #94a3b8; font-size: 0.8rem;">Schedule re-calculated</span>
    </div>
    """, unsafe_allow_html=True)

# --- KEY METRIC CARDS ---
col_k1, col_k2, col_k3, col_k4 = st.columns(4)

with col_k1:
    st.markdown(f"""
    <div class="dash-card dash-card-accent-emerald">
        <div class="dash-card-label">Track Time Saved</div>
        <div class="dash-card-value val-emerald">+{solver_solution['time_saved_mins']} mins</div>
        <div class="dash-card-sub">
            <span>{solver_solution['capacity_gain_pct']:.1f}% less track closure</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_k2:
    start_fmt = format_min_to_hhmm(solver_solution['start_time_min'])
    end_fmt = format_min_to_hhmm(solver_solution['end_time_min'])
    st.markdown(f"""
    <div class="dash-card dash-card-accent-blue">
        <div class="dash-card-label">Shadow-Block Window</div>
        <div class="dash-card-value val-blue">{start_fmt} – {end_fmt}</div>
        <div class="dash-card-sub">
            <span>{solver_solution['bundled_duration']} mins (3 departments synchronized)</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_k3:
    penalty_score = solver_solution['penalty_score']
    p_color = "val-emerald" if penalty_score == 0 else "val-amber" if penalty_score <= 3 else "val-rose"
    affected_count = len(solver_solution['affected_trains'])
    affected_text = f"{affected_count} train shifted" if affected_count == 1 else f"{affected_count} trains shifted" if affected_count > 0 else "Zero trains delayed"
    st.markdown(f"""
    <div class="dash-card dash-card-accent-amber">
        <div class="dash-card-label">Trains Affected</div>
        <div class="dash-card-value {p_color}">{affected_count}</div>
        <div class="dash-card-sub">
            <span>{affected_text} · Penalty score: {penalty_score}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_k4:
    annual_cr = financial_savings_lakhs * 365 / 100
    st.markdown(f"""
    <div class="dash-card dash-card-accent-emerald">
        <div class="dash-card-label">Estimated Cost Savings</div>
        <div class="dash-card-value val-emerald">₹ {financial_savings_lakhs:.2f} L</div>
        <div class="dash-card-sub">
            <span>~₹ {annual_cr:.2f} Cr projected per year</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)

# --- NAVIGATION TABS ---
tab_trains, tab_sim, tab_schedule, tab_equipment, tab_reroute, tab_order = st.tabs([
    "🚆 Train Movement Chart",
    "🚂 Track Simulation",
    "📋 Shadow-Block Scheduling",
    "🔧 Equipment Health",
    "📊 Route Cost Analysis",
    "📄 Dispatch Order"
])

# =========================================================================
# TAB 1: TRAIN MOVEMENT CHART
# =========================================================================
with tab_trains:
    chart_col_title, chart_col_filter = st.columns([3, 1])
    with chart_col_title:
        st.markdown("#### Train Movement Chart (Time-Distance)")
        st.caption("Visualizes scheduled train paths across the 67 km section. Slopes going down are UP trains (Madgaon → Pernem); slopes going up are DOWN trains.")
    with chart_col_filter:
        time_view = st.selectbox(
            "Time Range",
            ["Full 24 Hours", "Daytime (06:00 – 20:00)", "Shadow Block Focus (14:00 – 22:00)"],
            label_visibility="collapsed"
        )

    if "Daytime" in time_view:
        x_min, x_max = 360, 1200
    elif "Maintenance" in time_view:
        x_min, x_max = 840, 1320
    else:
        x_min, x_max = 0, 1440

    fig_marey = go.Figure()

    stations_list = [
        {"code": "PERN", "name": "Pernem", "km": 67},
        {"code": "THVM", "name": "Thivim", "km": 51},
        {"code": "KRMI", "name": "Karmali", "km": 33},
        {"code": "MAO", "name": "Madgaon Jn", "km": 0}
    ]

    # Station reference lines
    for stn in stations_list:
        fig_marey.add_hline(
            y=stn["km"],
            line_dash="dot",
            line_color="rgba(255, 255, 255, 0.12)",
            line_width=1,
            annotation_text=f"{stn['name']} ({stn['km']} km)",
            annotation_position="bottom right",
            annotation_font=dict(color="#94a3b8", size=11)
        )

    # Train trajectory lines
    for traj in trajectories:
        x_pts = [t + incident_delay for t in traj['x_times']]
        y_pts = traj['y_distances']
        
        weight = traj['financial_weight']
        t_no = traj['train_no']
        t_name = traj['train_name']
        cat = traj['category']

        if weight == 5:
            line_color = "#f43f5e"  # Rose for Premium (Vande Bharat)
            line_width = 2.8
        elif weight == 3:
            line_color = "#f59e0b"  # Amber for Express / Mail
            line_width = 2.0
        else:
            line_color = "#60a5fa"  # Soft blue for Freight / Local
            line_width = 1.6

        fig_marey.add_trace(go.Scatter(
            x=x_pts,
            y=y_pts,
            mode='lines+markers',
            name=f"{t_no} {t_name}",
            line=dict(color=line_color, width=line_width),
            marker=dict(size=4, color=line_color),
            hovertemplate=(
                f"<b>{t_name} (#{t_no})</b><br>"
                f"Category: {cat}<br>"
                f"Direction: {traj['direction']}<br>"
                f"Time: %{{customdata}}<br>"
                f"Position: %{{y}} km<extra></extra>"
            ),
            customdata=[format_min_to_hhmm(int(t)) for t in x_pts]
        ))

    # Scheduled shadow block
    if solver_solution['status'] in ('OPTIMAL', 'FEASIBLE'):
        b_s = solver_solution['start_time_min']
        b_e = solver_solution['end_time_min']
        
        fig_marey.add_vrect(
            x0=b_s,
            x1=b_e,
            fillcolor="rgba(16, 185, 129, 0.12)",
            layer="below",
            line_width=1.5,
            line_color="#10b981",
            line_dash="dash",
            annotation_text=f"Shadow Block ({format_min_to_hhmm(b_s)} – {format_min_to_hhmm(b_e)})",
            annotation_position="top left",
            annotation_font=dict(color="#6ee7b7", size=11)
        )

    tick_step = 60 if (x_max - x_min) <= 600 else 120
    fig_marey.update_layout(
        plot_bgcolor="#121824",
        paper_bgcolor="#121824",
        xaxis=dict(
            title="Time of Day",
            range=[x_min, x_max],
            tickmode='linear',
            tick0=0,
            dtick=tick_step,
            ticktext=[f"{h:02d}:00" for h in range(0, 25)],
            tickvals=[h * 60 for h in range(0, 25)],
            gridcolor="rgba(255, 255, 255, 0.06)",
            color="#94a3b8",
            title_font=dict(size=12, color="#cbd5e1")
        ),
        yaxis=dict(
            title="Distance (km from Madgaon)",
            tickvals=[s["km"] for s in stations_list],
            ticktext=[f"{s['name']} ({s['km']} km)" for s in stations_list],
            gridcolor="rgba(255, 255, 255, 0.06)",
            color="#94a3b8",
            title_font=dict(size=12, color="#cbd5e1"),
            range=[-2, 70]
        ),
        height=500,
        showlegend=False,
        hovermode="closest",
        margin=dict(l=40, r=30, t=20, b=40)
    )

    st.plotly_chart(fig_marey, width='stretch')

    # Legend Badges
    st.markdown("""
    <div style="display: flex; gap: 10px; margin-top: -10px; margin-bottom: 1.25rem; flex-wrap: wrap;">
        <span class="badge-pill badge-vb">● Premium (Vande Bharat)</span>
        <span class="badge-pill badge-exp">● Express & Mail</span>
        <span class="badge-pill badge-frt">● Freight & Local</span>
        <span class="badge-pill badge-window">▨ Scheduled Shadow Block</span>
    </div>
    """, unsafe_allow_html=True)

    # Track layout & crossover details
    with st.expander("Track Layout & Crossover Routing"):
        col_sch1, col_sch2 = st.columns([3, 1])
        with col_sch1:
            fig_tracks = go.Figure()
            track_labels = ["Up Main Line", "Down Main Line", "Up Loop Siding", "Down Bypass"]
            for i, t_label in enumerate(track_labels):
                fig_tracks.add_hline(y=i, line_dash="solid", line_color="rgba(255, 255, 255, 0.12)", line_width=2)
            
            fig_tracks.add_trace(go.Scatter(x=[120, 240, 260, 380], y=[0, 0, 2, 2], mode='lines', name="Passenger (Crossover to Loop)", line=dict(color="#f59e0b", width=2.5)))
            fig_tracks.add_trace(go.Scatter(x=[160, 420], y=[1, 1], mode='lines', name="Vande Bharat (Through Main Line)", line=dict(color="#f43f5e", width=3)))
            fig_tracks.add_trace(go.Scatter(x=[60, 210, 230, 360], y=[3, 3, 1, 1], mode='lines', name="Freight (Bypass Run)", line=dict(color="#60a5fa", width=2)))

            fig_tracks.update_layout(
                plot_bgcolor="#121824",
                paper_bgcolor="#121824",
                yaxis=dict(tickvals=[0, 1, 2, 3], ticktext=track_labels, color="#94a3b8"),
                xaxis=dict(title="Time (Minutes)", range=[0, 480], gridcolor="rgba(255, 255, 255, 0.06)", color="#94a3b8"),
                height=240,
                showlegend=True,
                legend=dict(orientation="h", y=1.2, x=0),
                margin=dict(l=20, r=20, t=30, b=20)
            )
            st.plotly_chart(fig_tracks, width='stretch')
        with col_sch2:
            st.markdown("#### Dynamic Crossover")
            st.write("Slower freight and regional trains are routed to loop sidings at crossover junctions, leaving the main line clear for higher-priority express trains.")

# =========================================================================
# TAB 1.5: TRACK SIMULATION (FACTORIO-STYLE)
# =========================================================================
with tab_sim:
    st.markdown("### Interactive Track Simulation")
    st.caption("Real-time block section simulation with disruption injection and layout editing.")
    
    sim_html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "simulation.html")
    if os.path.exists(sim_html_path):
        with open(sim_html_path, "r", encoding="utf-8") as f:
            sim_html_content = f.read()
        import streamlit.components.v1 as components
        components.html(sim_html_content, height=700)
    else:
        st.error("Simulation engine (simulation.html) not found in assets folder.")

# =========================================================================
# TAB 2: SHADOW-BLOCK SCHEDULING
# =========================================================================
with tab_schedule:
    st.markdown("### Synchronized Shadow-Block Scheduling")
    st.caption("Combines separate track, electrical, and signaling maintenance into a single coordinated shadow block to minimize total line closure time.")

    col_g1, col_g2 = st.columns([1, 1])

    with col_g1:
        st.markdown("#### Before vs After Closure Time")
        
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(
            name="Separate Closures",
            y=["Corridor Status"],
            x=[solver_solution['unbundled_total']],
            orientation='h',
            marker_color="#f43f5e",
            text=[f"Separate: {solver_solution['unbundled_total']} mins"],
            textposition='inside'
        ))
        fig_comp.add_trace(go.Bar(
            name="Shadow Block (Bundled)",
            y=["Corridor Status"],
            x=[solver_solution['bundled_duration']],
            orientation='h',
            marker_color="#10b981",
            text=[f"Shadow Block: {solver_solution['bundled_duration']} mins"],
            textposition='inside'
        ))
        fig_comp.update_layout(
            barmode='group',
            plot_bgcolor="#121824",
            paper_bgcolor="#121824",
            xaxis=dict(title="Total Track Closure (Minutes)", gridcolor="rgba(255, 255, 255, 0.06)", color="#94a3b8"),
            yaxis=dict(color="#94a3b8"),
            height=180,
            legend=dict(orientation="h", y=1.25, x=0),
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig_comp, width='stretch')

        st.markdown(f"""
        <div class="dash-panel" style="margin-top: 1rem;">
            <div style="font-size: 0.82rem; color: #94a3b8; font-weight: 600;">EFFICIENCY BREAKDOWN</div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 12px;">
                <div>
                    <span style="font-size: 0.78rem; color: #64748b;">SEPARATE WORK TIME</span><br>
                    <b style="font-size: 1.15rem; color: #f43f5e;">{solver_solution['unbundled_total']} mins</b>
                    <div style="font-size: 0.75rem; color: #94a3b8;">3 separate track closures</div>
                </div>
                <div>
                    <span style="font-size: 0.78rem; color: #64748b;">SHADOW-BLOCK DURATION</span><br>
                    <b style="font-size: 1.15rem; color: #10b981;">{solver_solution['bundled_duration']} mins</b>
                    <div style="font-size: 0.75rem; color: #94a3b8;">1 coordinated shadow block</div>
                </div>
                <div>
                    <span style="font-size: 0.78rem; color: #64748b;">TIME SAVED</span><br>
                    <b style="font-size: 1.15rem; color: #60a5fa;">{solver_solution['time_saved_mins']} mins</b>
                    <div style="font-size: 0.75rem; color: #94a3b8;">+{solver_solution['capacity_gain_pct']:.1f}% track availability</div>
                </div>
                <div>
                    <span style="font-size: 0.78rem; color: #64748b;">COMMERCIAL VALUE SAVED</span><br>
                    <b style="font-size: 1.15rem; color: #34d399;">₹ {financial_savings_lakhs:.2f} Lakhs</b>
                    <div style="font-size: 0.75rem; color: #94a3b8;">Avoided passenger and freight delays</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_g2:
        st.markdown("#### Optimization Results")
        if solver_solution['status'] in ('OPTIMAL', 'FEASIBLE'):
            st.success("Optimal shadow block scheduled successfully.")
            
            c_s1, c_s2 = st.columns(2)
            with c_s1:
                st.metric("Scheduled Start", format_min_to_hhmm(solver_solution['start_time_min']))
            with c_s2:
                st.metric("Scheduled End", format_min_to_hhmm(solver_solution['end_time_min']))

            st.write(f"**Disruption penalty score:** `{solver_solution['penalty_score']}`")
            
            if solver_solution['affected_trains']:
                st.warning(f"{len(solver_solution['affected_trains'])} train schedule(s) adjusted:")
                st.dataframe(pd.DataFrame(solver_solution['affected_trains']), width='stretch')
            else:
                st.info("No train schedule conflicts. The shadow block fits cleanly in a natural traffic lull.")
        else:
            st.error("Could not find a feasible schedule within current constraints.")

    st.markdown("---")
    st.markdown("#### Section Train Timetable")
    display_sched = schedule_df[['train no', 'train name', 'financial_weight', 'arr_min', 'dep_min']].copy()
    display_sched.columns = ['Train Number', 'Train Name', 'Priority Weight', 'Arrival (mins)', 'Departure (mins)']
    st.dataframe(display_sched, width='stretch', hide_index=True)

# =========================================================================
# TAB 3: EQUIPMENT HEALTH
# =========================================================================
with tab_equipment:
    st.markdown("### Switch & Point Machine Health")
    st.caption("Monitors motor current, throw duration, and vibration on track point machines to detect mechanical wear before failures occur.")

    telemetry_df = load_telemetry_data(num_records=60)
    
    iot_c1, iot_c2, iot_c3 = st.columns([1, 1, 1])
    
    with iot_c1:
        st.markdown("#### Sensor Inputs")
        sim_peak = st.slider("Peak Motor Current (Amps)", 3.0, 9.0, 5.2, step=0.1)
        sim_avg = st.slider("Average Motor Current (Amps)", 2.0, 6.0, 3.4, step=0.1)
        sim_throw = st.slider("Throw Duration (ms)", 2500, 5000, 3050, step=50)
        sim_vib = st.slider("Peak Vibration (g)", 0.05, 0.50, 0.12, step=0.01)

    eval_result = evaluate_asset_health(
        motor_peak=sim_peak,
        motor_avg=sim_avg,
        throw_duration=sim_throw,
        vibration=sim_vib
    )

    with iot_c2:
        st.markdown("#### Health Evaluation")
        health_color = "#10b981" if eval_result['health_score'] > 70 else "#f59e0b" if eval_result['health_score'] > 30 else "#f43f5e"
        condition_label = "Good Condition" if eval_result['health_score'] > 70 else "Minor Wear Detected" if eval_result['health_score'] > 30 else "Maintenance Required"

        st.markdown(f"""
        <div class="dash-panel" style="text-align: center; border-top: 3px solid {health_color};">
            <div style="font-size: 0.78rem; color: #94a3b8; font-weight: 600;">POINT MACHINE HEALTH</div>
            <div style="font-size: 2.4rem; font-weight: 700; color: {health_color}; margin: 6px 0;">{eval_result['health_score']}%</div>
            <div style="font-size: 0.85rem; color: #f1f5f9; font-weight: 500;">{condition_label}</div>
            <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 4px;">Anomaly likelihood: {eval_result['anomaly_probability']*100:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"**Diagnostic State:** `{eval_result['status_label']}`")
        st.markdown(f"**Recommended Action:** {eval_result['recommended_action']}")

    with iot_c3:
        st.markdown("#### Automated Action")
        st.write("If equipment shows abnormal wear, you can automatically schedule an emergency S&T shadow block.")
        
        if st.button("Simulate Fault & Schedule Shadow Block"):
            st.session_state['snt_duration'] = 60
            st.session_state['eng_duration'] = max(st.session_state['eng_duration'], 90)
            st.toast("Emergency S&T shadow block added to schedule.", icon="🔧")
            st.success("Fault logged. An emergency 60-minute signaling shadow block has been scheduled.")

    st.markdown("---")
    st.markdown("#### Sensor Waveforms (Point Machine PM-42)")
    fig_wave = px.line(
        telemetry_df,
        x='timestamp',
        y=['motor_current_peak_amps', 'throw_duration_ms', 'vibration_peak_g'],
        color_discrete_sequence=["#60a5fa", "#f43f5e", "#10b981"],
        labels={
            "motor_current_peak_amps": "Peak Current (A)",
            "throw_duration_ms": "Throw Time (ms)",
            "vibration_peak_g": "Vibration (g)"
        },
        height=300
    )
    fig_wave.update_layout(
        plot_bgcolor="#121824",
        paper_bgcolor="#121824",
        xaxis=dict(title="Timestamp", gridcolor="rgba(255, 255, 255, 0.06)", color="#94a3b8"),
        yaxis=dict(title="Value", gridcolor="rgba(255, 255, 255, 0.06)", color="#94a3b8"),
        legend=dict(orientation="h", y=1.15, x=0),
        margin=dict(l=20, r=20, t=30, b=20)
    )
    st.plotly_chart(fig_wave, width='stretch')

# =========================================================================
# TAB 4: ROUTE COST ANALYSIS
# =========================================================================
with tab_reroute:
    st.markdown("### Route Cost & Feasibility Analysis")
    st.caption("Evaluates alternate routing options when a track is blocked or under maintenance, balancing operating costs, punctuality penalties, and track capacity.")

    # Cost Model Explanation
    st.markdown("""
    <div class="dash-panel" style="margin-bottom: 1.25rem; border-left: 3px solid #3b82f6;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span style="font-size: 0.85rem; font-weight: 600; color: #60a5fa;">
                Cost Model: Net Margin Calculation
            </span>
            <span style="font-size: 0.78rem; color: #94a3b8;">Indian Railways GTKM Standards</span>
        </div>
        <div style="font-size: 1.1rem; font-weight: 600; color: #f8fafc; margin-bottom: 8px;">
            Net Margin = Revenue − (Operating Cost + Delay Penalty + Congestion Surcharge)
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; font-size: 0.82rem; color: #94a3b8;">
            <div><b style="color: #34d399;">Revenue:</b> Passenger ticket sales & freight freight tariff.</div>
            <div><b style="color: #60a5fa;">Operating Cost:</b> Weight (tonnes) × Distance (km) × ₹0.90 per ton-km.</div>
            <div><b style="color: #fbbf24;">Delay Penalty:</b> Delay (mins) × Scheduled penalty rate (₹/min).</div>
            <div><b style="color: #fb7185;">Congestion Surcharge:</b> Active trains on route × ₹15,000 bottleneck surcharge.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    trains_mock, tracks_mock = get_default_corridor_infrastructure()

    col_x1, col_x2, col_x3 = st.columns([1.2, 1.2, 1.0])
    with col_x1:
        selected_train = st.selectbox(
            "Select Train",
            trains_mock['train_id'].tolist(),
            index=0
        )
    with col_x2:
        selected_block = st.selectbox(
            "Simulate Track Blockage",
            ["None"] + tracks_mock['track_id'].tolist(),
            index=1  # Default to Line_A blocked to demonstrate alternate routing
        )
    with col_x3:
        with st.popover("Cost Parameters"):
            st.markdown("##### Rate Settings")
            gtkm_param = st.slider("Cost per Ton-Km (₹)", 0.50, 2.00, 0.90, step=0.05)
            opp_param = st.slider("Congestion Penalty per Train (₹)", 5000, 30000, 15000, step=2500)

    # Train specs lookup
    target_train_row = trains_mock[trains_mock['train_id'] == selected_train].iloc[0]
    train_wt = float(target_train_row.get('weight_tons', 1000))
    train_elec = bool(target_train_row.get('needs_electricity', True))
    train_rev = float(target_train_row.get('revenue_inr', target_train_row.get('gross_revenue_inr', 1000000)))
    train_pen = float(target_train_row.get('penalty_per_min_inr', 1000))
    train_type = str(target_train_row.get('train_type', target_train_row.get('train_name', 'Passenger / Freight')))
    train_loco = str(target_train_row.get('loco_type', '25kV AC Electric' if train_elec else 'Diesel Traction'))

    st.markdown(f"""
    <div style="background: rgba(18, 24, 36, 0.7); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 10px 16px; margin-bottom: 1rem; display: flex; flex-wrap: wrap; gap: 16px; align-items: center; font-size: 0.84rem;">
        <span style="color: #94a3b8;">Train: <b style="color: #f1f5f9;">{selected_train}</b> ({train_type})</span>
        <span style="color: #94a3b8;">Gross Weight: <b style="color: #60a5fa;">{train_wt:,.0f} Tonnes</b></span>
        <span style="color: #94a3b8;">Traction: <b style="color: {'#34d399' if train_elec else '#fbbf24'};">{'25kV AC Electric' if train_elec else 'Diesel Traction'}</b> ({train_loco})</span>
        <span style="color: #94a3b8;">Revenue: <b style="color: #34d399;">₹{train_rev:,.0f}</b></span>
        <span style="color: #94a3b8;">Delay Penalty: <b style="color: #fb7185;">₹{train_pen:,.0f}/min</b></span>
    </div>
    """, unsafe_allow_html=True)

    # Evaluate decision
    xai_res = evaluate_rerouting_decision(
        target_train_id=selected_train,
        blocked_track_id=selected_block,
        trains_df=trains_mock,
        tracks_df=tracks_mock,
        gtkm_rate=gtkm_param,
        opp_cost_rate=opp_param
    )

    # Recommendation banner
    if xai_res['best_track']:
        best_eval = [e for e in xai_res['financial_evaluations'] if e['track_id'] == xai_res['best_track']][0]
        st.markdown(f"""
        <div class="dash-panel" style="border: 1px solid #10b981; background: rgba(16, 185, 129, 0.08); margin-bottom: 1.25rem;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="background: rgba(16, 185, 129, 0.2); color: #34d399; font-weight: 600; font-size: 0.74rem; padding: 3px 8px; border-radius: 4px;">
                        RECOMMENDED ROUTE
                    </span>
                    <h3 style="margin: 8px 0 4px 0; color: #f8fafc; font-size: 1.2rem;">
                        Route <span style="color: #60a5fa;">{selected_train}</span> via <span style="color: #34d399;">{xai_res['best_track']}</span>
                    </h3>
                    <p style="margin: 0; color: #94a3b8; font-size: 0.84rem;">
                        Satisfies axle load limits, overhead electrification, and safety headway margins while maximizing net operating margin.
                    </p>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 0.75rem; color: #94a3b8;">Net Operating Margin</div>
                    <div style="font-size: 1.55rem; font-weight: 700; color: #34d399;">
                        ₹{xai_res['max_net_margin']:,.2f}
                    </div>
                    <div style="font-size: 0.78rem; color: #94a3b8;">
                        Margin: {best_eval['margin_pct']:.1f}% · Total Expenses: ₹{best_eval['total_expense']:,.2f}
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="dash-panel" style="border: 1px solid #f43f5e; background: rgba(244, 63, 94, 0.08); margin-bottom: 1.25rem;">
            <span style="background: rgba(244, 63, 94, 0.2); color: #fb7185; font-weight: 600; font-size: 0.74rem; padding: 3px 8px; border-radius: 4px;">
                NO FEASIBLE ALTERNATE ROUTE
            </span>
            <h3 style="margin: 8px 0 4px 0; color: #f8fafc; font-size: 1.2rem;">
                Train Must Hold at Outer Signal
            </h3>
            <p style="margin: 0; color: #fda4af; font-size: 0.84rem;">
                All alternate routes failed physical constraints (exceeded axle load limits or lacked overhead electric catenary).
            </p>
        </div>
        """, unsafe_allow_html=True)

    col_x_log1, col_x_log2 = st.columns([1, 1])

    with col_x_log1:
        st.markdown("#### 1. Route Feasibility Checks")
        st.caption("Checks axle load limits, overhead electric power, line closures, and block headway capacity.")

        for log in xai_res['validation_log']:
            if log['passed']:
                st.markdown(f"""
                <div style="background: rgba(16, 185, 129, 0.06); border-left: 3px solid #10b981; padding: 10px 14px; border-radius: 6px; margin-bottom: 8px;">
                    <div style="color: #34d399; font-weight: 600; font-size: 0.88rem;">✓ {log['track_id']} Available</div>
                    <div style="color: #94a3b8; font-size: 0.82rem; margin-top: 2px;">{log['reason']}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background: rgba(244, 63, 94, 0.06); border-left: 3px solid #f43f5e; padding: 10px 14px; border-radius: 6px; margin-bottom: 8px;">
                    <div style="color: #fb7185; font-weight: 600; font-size: 0.88rem;">✗ {log['track_id']} Unavailable</div>
                    <div style="color: #fda4af; font-size: 0.82rem; margin-top: 2px;">{log['reason']}</div>
                </div>
                """, unsafe_allow_html=True)

    with col_x_log2:
        st.markdown("#### 2. Financial Breakdown")
        st.caption("Detailed arithmetic for each feasible route option.")

        if not xai_res['financial_evaluations']:
            st.warning("No candidate routes passed physical feasibility checks.")
        else:
            for eval_data in xai_res['financial_evaluations']:
                is_winner = (eval_data['track_id'] == xai_res['best_track'])
                expander_label = f"{'★ Recommended: ' if is_winner else ''}{eval_data['track_id']} — Net Margin: ₹{eval_data['net_margin']:,.2f}"
                
                with st.expander(expander_label, expanded=is_winner):
                    st.markdown(f"""
                    <div style="font-size: 0.85rem; line-height: 1.6; background: rgba(18, 24, 36, 0.6); padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.06);">
                        <div style="display: flex; justify-content: space-between; color: #34d399;">
                            <span><b>[+] Gross Revenue:</b></span>
                            <span><b>+₹{eval_data['gross_revenue']:,.2f}</b></span>
                        </div>
                        <div style="display: flex; justify-content: space-between; color: #60a5fa; margin-top: 4px;">
                            <span><b>[-] Ton-Km Operating Cost ({eval_data['weight_tons']:,.0f}t × {eval_data['distance_km']}km × ₹{eval_data['gtkm_rate']:.2f}):</b></span>
                            <span>-₹{eval_data['gtkm_cost']:,.2f}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; color: #fbbf24; margin-top: 4px;">
                            <span><b>[-] Delay Penalty ({eval_data['delay_mins']:.0f}m × ₹{eval_data['penalty_per_min']:,.0f}/m):</b></span>
                            <span>-₹{eval_data['delay_penalty_cost']:,.2f}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; color: #fb7185; margin-top: 4px;">
                            <span><b>[-] Congestion Surcharge ({eval_data['current_traffic']} trains × ₹{eval_data['opp_cost_rate']:,.0f}):</b></span>
                            <span>-₹{eval_data['opportunity_cost']:,.2f}</span>
                        </div>
                        <hr style="border: 0; border-top: 1px dashed rgba(255,255,255,0.12); margin: 8px 0;">
                        <div style="display: flex; justify-content: space-between; color: #94a3b8;">
                            <span><b>Total Operating Expenses:</b></span>
                            <span>-₹{eval_data['total_expense']:,.2f}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 1.02rem; font-weight: 700; color: {'#34d399' if eval_data['net_margin'] > 0 else '#fb7185'}; margin-top: 6px;">
                            <span><b>Net Retained Margin:</b></span>
                            <span>₹{eval_data['net_margin']:,.2f}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.caption(f"Margin: {eval_data['margin_pct']:.1f}% · Route distance: {eval_data['distance_km']} km · Active trains: {eval_data['current_traffic']}")

    # Comparative Cost Chart
    if xai_res['financial_evaluations']:
        st.markdown("---")
        st.markdown("#### Comparative Route Financials")
        fin_df = pd.DataFrame(xai_res['financial_evaluations'])
        
        fig_xai = go.Figure()
        fig_xai.add_trace(go.Bar(
            name="Net Margin",
            x=fin_df['track_id'],
            y=fin_df['net_margin'],
            marker_color="#10b981",
            text=[f"₹{v/1e5:.2f}L" for v in fin_df['net_margin']],
            textposition='auto'
        ))
        fig_xai.add_trace(go.Bar(
            name="Ton-Km Operating Cost",
            x=fin_df['track_id'],
            y=fin_df['gtkm_cost'],
            marker_color="#60a5fa",
            text=[f"₹{v/1e5:.2f}L" for v in fin_df['gtkm_cost']],
            textposition='auto'
        ))
        fig_xai.add_trace(go.Bar(
            name="Delay Penalty",
            x=fin_df['track_id'],
            y=fin_df['delay_penalty_cost'],
            marker_color="#fbbf24",
            text=[f"₹{v/1e5:.2f}L" for v in fin_df['delay_penalty_cost']],
            textposition='auto'
        ))
        fig_xai.add_trace(go.Bar(
            name="Congestion Surcharge",
            x=fin_df['track_id'],
            y=fin_df['opportunity_cost'],
            marker_color="#fb7185",
            text=[f"₹{v/1e5:.2f}L" for v in fin_df['opportunity_cost']],
            textposition='auto'
        ))

        fig_xai.update_layout(
            barmode='group',
            plot_bgcolor="#121824",
            paper_bgcolor="#121824",
            xaxis=dict(gridcolor="rgba(255, 255, 255, 0.06)", color="#94a3b8"),
            yaxis=dict(title="Amount (₹)", gridcolor="rgba(255, 255, 255, 0.06)", color="#94a3b8"),
            height=300,
            legend=dict(orientation="h", y=1.18, x=0),
            margin=dict(l=20, r=20, t=30, b=20)
        )
        st.plotly_chart(fig_xai, width='stretch')

    # Corridor Infrastructure Table
    st.markdown("---")
    st.markdown("#### Corridor Track Information")
    
    display_tracks = xai_res['tracks_table'].copy()
    col_mapping = {
        'track_id': 'Route ID',
        'status': 'Status',
        'distance_km': 'Distance (km)',
        'max_weight_tons': 'Max Axle Load (Tonnes)',
        'is_electrified': 'Overhead Electric (25kV)',
        'current_traffic_count': 'Active Trains',
        'max_capacity': 'Capacity Limit',
        'estimated_delay_min': 'Section Delay (mins)'
    }
    cols_to_show = [c for c in col_mapping.keys() if c in display_tracks.columns]
    display_df = display_tracks[cols_to_show].rename(columns=col_mapping)
    display_df['Overhead Electric (25kV)'] = display_df['Overhead Electric (25kV)'].apply(lambda x: "Yes (25kV AC)" if x else "No (Diesel Only)")
    
    st.dataframe(display_df, width='stretch', hide_index=True)

# =========================================================================
# TAB 5: DISPATCH ORDER
# =========================================================================
with tab_order:
    st.markdown("### Section Dispatch Order (Form T/409)")
    st.caption("Official caution order and shadow-block authorization for Station Masters, Section Controllers, and Loco Pilots.")

    order_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dispatch_order_text = f"""================================================================================
INDIAN RAILWAYS - CENTRALIZED TRAFFIC CONTROL DIVISION 04
CAUTION ORDER & SHADOW-BLOCK AUTHORIZATION (FORM T/409)
SECTION: MADGAON JN (MAO) - KARMALI (KRMI) - THIVIM (THVM) - PERNEM (PERN)
ISSUED: {order_timestamp} IST | SECTION ID: KR-04
================================================================================

1. SHADOW-BLOCK AUTHORIZATION DETAILS:
   -----------------------------------------------------------------------------
   • Section              : KM 0.0 (MAO) to KM 67.0 (PERN)
   • Block Start Time     : {format_min_to_hhmm(solver_solution['start_time_min'])} hrs
   • Block End Time       : {format_min_to_hhmm(solver_solution['end_time_min'])} hrs
   • Total Line Closure   : {solver_solution['bundled_duration']} Minutes (Coordinated)
   • Departments Involved : Track Engineering ({st.session_state['eng_duration']}m), Electrical OHE ({st.session_state['elec_duration']}m), S&T ({st.session_state['snt_duration']}m)
   • Total Downtime Saved : {solver_solution['time_saved_mins']} Minutes (+{solver_solution['capacity_gain_pct']:.1f}% availability)

2. CORRIDOR OPERATING CONDITIONS:
   -----------------------------------------------------------------------------
   • Active Incident      : {incident_type}
   • Safety Buffer Added  : +{incident_delay} Minutes
   • Crossover Route      : Dynamic interlocking armed at crossover points

3. TRAIN CLEARANCE:
   -----------------------------------------------------------------------------
   • Disruption Penalty   : {solver_solution['penalty_score']}
   • Priority Clearance   : 22229 Vande Bharat / 12051 Jan Shatabdi Main Line Priority
   • Punctuality Target   : On schedule

================================================================================
ISSUED BY: SECTION CONTROLLER DESK - KONKAN RAILWAY DIVISION 04
================================================================================
"""
    st.text_area("Operational Authority Notice", dispatch_order_text, height=260)

    buf = io.StringIO()
    buf.write(dispatch_order_text)

    st.download_button(
        label="Download Shadow-Block Order (Form T/409)",
        data=buf.getvalue(),
        file_name=f"IR_Shadow_Block_Order_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain"
    )
