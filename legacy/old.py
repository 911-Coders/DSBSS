import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from ortools.sat.python import cp_model

st.set_page_config(page_title="AI Rail Planner - 2D Routing", layout="wide")
st.title("🚆 Space-Time Block Auto-Generator")
st.markdown("Simulating both Maintenance Blocks (Time) and Signaling Blocks (Space/Tracks).")

# --- 1. SIMULATED DATASET (Main Line & Loop Line) ---
# We treat a specific station segment (like Madgoan) as having 2 physical signaling blocks
st.sidebar.header("🚨 Crisis Simulator")
incident = st.sidebar.selectbox("Inject Incident on Main Line", ["None", "Track Fracture (2hr Maintenance)", "Landslide (4hr Block)"])

# 0 = Main Line, 1 = Loop Line (Bypass)
trains = [
    {"name": "Rajdhani (Premium)", "arr": 100, "dep": 130, "weight": 5},
    {"name": "Freight A (Heavy)", "arr": 115, "dep": 160, "weight": 3},
    {"name": "Local Passenger 1", "arr": 140, "dep": 180, "weight": 1},
    {"name": "Express B", "arr": 200, "dep": 250, "weight": 3}
]

maintenance_start = 100
maintenance_duration = 0
if incident == "Track Fracture (2hr Maintenance)": maintenance_duration = 120
elif incident == "Landslide (4hr Block)": maintenance_duration = 240
maintenance_end = maintenance_start + maintenance_duration

# --- 2. THE 2D AI SOLVER (Space + Time) ---
model = cp_model.CpModel()

# Variables: Which physical track (Signaling Block) does each train take?
# 0 = Main Line, 1 = Loop Line
track_assignments = {}
for i, t in enumerate(trains):
    track_assignments[i] = model.NewIntVar(0, 1, f'track_train_{i}')

# CONSTRAINT 1: Temporal Maintenance Block
# If the Main Line (Track 0) is under maintenance, no train can use it during that time.
if maintenance_duration > 0:
    for i, t in enumerate(trains):
        # Does the train overlap with the maintenance time?
        if t["arr"] < maintenance_end and t["dep"] > maintenance_start:
            # Force the train onto the Loop Line (Track 1)
            model.Add(track_assignments[i] == 1)

# CONSTRAINT 2: Physical Signaling Blocks (Mutual Exclusion)
# Two trains CANNOT occupy the same track at the same time.
for i in range(len(trains)):
    for j in range(i + 1, len(trains)):
        t1, t2 = trains[i], trains[j]
        
        # Check if they overlap in time
        if t1["arr"] < t2["dep"] and t2["arr"] < t1["dep"]:
            # If they overlap in time, they MUST be on different tracks
            same_track = model.NewBoolVar(f'same_track_{i}_{j}')
            model.Add(track_assignments[i] == track_assignments[j]).OnlyEnforceIf(same_track)
            model.Add(track_assignments[i] != track_assignments[j]).OnlyEnforceIf(same_track.Not())
            
            # Prevent deadlock: Force them to not share the same track
            model.Add(same_track == 0)

# Solve the constraints
solver = cp_model.CpSolver()
status = solver.Solve(model)

# --- 3. 2D SIMULATION DASHBOARD ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Signaling & Routing Status")
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        st.success("✅ System Optimal: All Signaling & Maintenance constraints met.")
        for i, t in enumerate(trains):
            assigned_track = solver.Value(track_assignments[i])
            track_name = "Main Line" if assigned_track == 0 else "Loop Line (Bypass)"
            st.write(f"**{t['name']}**: Routed to {track_name}")
    else:
        st.error("❌ CRITICAL DEADLOCK: Both tracks are blocked or over capacity. Trains must be halted outside the station limits.")

with col2:
    st.subheader("Live Block Simulation")
    fig = go.Figure()
    
    # Plot the Maintenance Block on the Main Line (Y = 0)
    if maintenance_duration > 0:
        fig.add_shape(type="rect", x0=maintenance_start, y0=-0.2, x1=maintenance_end, y1=0.2,
                      fillcolor="red", opacity=0.5, line_width=0)
        fig.add_annotation(x=(maintenance_start+maintenance_end)/2, y=0.3, text="Dynamic Maintenance Block", showarrow=False, font=dict(color="red"))

    # Plot the Trains
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        for i, t in enumerate(trains):
            assigned_track = solver.Value(track_assignments[i])
            color = 'red' if t['weight'] == 5 else 'orange' if t['weight'] == 3 else 'cyan'
            
            # Y-axis represents the physical track (0 = Main, 1 = Loop)
            fig.add_trace(go.Scatter(x=[t["arr"], t["dep"]], y=[assigned_track, assigned_track], 
                                     mode='lines+markers', name=t["name"], line=dict(color=color, width=6)))

    fig.update_layout(
        xaxis_title="Time of Day (Minutes)",
        yaxis=dict(tickvals=[0, 1], ticktext=["Main Line (Block 0)", "Loop Line (Block 1)"], title="Physical Signaling Blocks"),
        template="plotly_dark", height=400, showlegend=True
    )
    st.plotly_chart(fig, use_container_width=True)