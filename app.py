import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="AI Rail Planner - 4 Track", layout="wide")
st.title("🚆 4-Track Junction & Crossover Simulation")
st.markdown("Visualizing multi-track routing, diamond crossings, and dynamic track switching.")

# --- THE TRACK NETWORK ---
# Y=0: Up Main Line (High Speed)
# Y=1: Down Main Line (High Speed)
# Y=2: Up Branch/Loop Line (Diverging)
# Y=3: Down Branch/Loop Line (Diverging)

# --- SIMULATED AI ROUTING DATA ---
# In your final app, the OR-Tools solver outputs these exact coordinate paths.
# We define paths as lists of (time_minute, track_number)
routes = [
    {
        "name": "Rajdhani (Premium Up)", 
        "color": "red", 
        "path": [(10, 0), (120, 0)] # Straight run on Track 0
    }, 
    {
        "name": "Freight (Heavy Down)", 
        "color": "orange", 
        "path": [(20, 1), (130, 1)] # Straight run on Track 1
    }, 
    {
        "name": "Local Passenger (Switching)", 
        "color": "cyan", 
        "path": [(30, 0), (50, 0), (55, 2), (140, 2)] # Diamond Crossover: Track 0 -> Track 2
    }, 
    {
        "name": "Emergency Relief Train", 
        "color": "yellow",
        "path": [(60, 3), (70, 3), (75, 1), (150, 1)] # Junction Crossover: Track 3 -> Track 1
    } 
]

# --- DASHBOARD VISUALIZATION ---
st.subheader("Live Spatio-Temporal Network Map")
st.write("Watch how the AI handles the physical routing. Diagonal lines represent trains actively traversing a track switch or diamond intersection.")

fig = go.Figure()

# 1. Draw the physical track infrastructure (Background Lines)
track_names = ["Up Main Line (0)", "Down Main Line (1)", "Up Branch Line (2)", "Down Branch Line (3)"]
for i, name in enumerate(track_names):
    fig.add_hline(y=i, line_dash="dot", line_color="gray", opacity=0.4)

# 2. Plot the Trains and their paths
for route in routes:
    x_vals = [pt[0] for pt in route["path"]]
    y_vals = [pt[1] for pt in route["path"]]
    
    fig.add_trace(go.Scatter(
        x=x_vals, 
        y=y_vals, 
        mode='lines+markers', 
        name=route["name"], 
        line=dict(color=route["color"], width=4, shape='linear'),
        marker=dict(size=8, symbol='square')
    ))

# 3. Highlight the Physical Interlocking / Junction Zone
fig.add_vrect(
    x0=45, x1=80,
    fillcolor="white", opacity=0.05,
    layer="below", line_width=1, line_dash="dash",
    annotation_text="Diamond Crossover / Interlocking Zone", 
    annotation_position="top left"
)

# 4. Format the UI
fig.update_layout(
    xaxis_title="Time of Day (Minutes)",
    yaxis=dict(
        tickvals=[0, 1, 2, 3], 
        ticktext=track_names, 
        title="Physical Track Topology"
    ),
    template="plotly_dark", 
    height=550, 
    showlegend=True,
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True)

# --- TELEMETRY READOUT ---
st.markdown("---")
st.subheader("📡 Junction Telemetry Logs")
st.info("Minute 50: Local Passenger engages switch, diverging from Up Main to Up Branch.")
st.warning("Minute 70: Emergency Relief Train crosses diamond intersection from Down Branch to Down Main.")