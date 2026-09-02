import streamlit as st
import pandas as pd
import joblib
import os
import plotly.graph_objects as go
from ortools.sat.python import cp_model

st.set_page_config(page_title="AI Rail Planner", layout="wide")
st.title("🚆 Dynamic Shadow-Block Scheduling System")

# --- LOAD ASSETS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
@st.cache_data 
def load_data():
    # Added low_memory=False to silence the terminal warning
    return pd.read_csv(os.path.join(BASE_DIR, "FINAL_ML_READY_DATA.csv"), low_memory=False)

df = load_data()

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Disruption Simulator")
weather = st.sidebar.selectbox("Current Weather Condition", ["Clear", "Rain", "Fog"])
st.sidebar.markdown("---")
st.sidebar.subheader("Maintenance Request")
block_duration = st.sidebar.slider("Required Block Duration (Mins)", 60, 240, 180, step=30)

# --- 1. NEW DATA SEARCH FEATURE ---
st.subheader("🔍 Live Database Search")
search_query = st.text_input("Enter Train Number to search (e.g., 107):")
if search_query:
    filtered_df = df[df['train no'].astype(str).str.contains(search_query, na=False)]
    st.dataframe(filtered_df)
else:
    st.info("Enter a train number above to search the 186,000+ records.")

st.markdown("---")

# --- 2. OR-TOOLS SOLVER LOGIC ---
st.subheader("AI Maintenance Optimizer")
delay_penalty = 0
if weather == "Rain": delay_penalty = 45
elif weather == "Fog": delay_penalty = 120

trains_today = [
    {"name": "Train 107", "entry": 100 + delay_penalty, "exit": 150 + delay_penalty},
    {"name": "Express A", "entry": 300 + delay_penalty, "exit": 360 + delay_penalty},
    {"name": "Freight B", "entry": 450 + delay_penalty, "exit": 520 + delay_penalty},
    {"name": "Rajdhani C", "entry": 700, "exit": 750}, 
    {"name": "Train 108", "entry": 900 + delay_penalty, "exit": 960 + delay_penalty},
    {"name": "Local D", "entry": 1100 + delay_penalty, "exit": 1150 + delay_penalty}
]

model = cp_model.CpModel()
block_start = model.NewIntVar(0, 1440 - block_duration, 'block_start')
block_end = model.NewIntVar(block_duration, 1440, 'block_end')
model.Add(block_end == block_start + block_duration)

for t in trains_today:
    if t["exit"] <= 1440:
        b_before = model.NewBoolVar(f'before_{t["name"]}')
        b_after = model.NewBoolVar(f'after_{t["name"]}')
        model.Add(block_end <= t["entry"]).OnlyEnforceIf(b_before)
        model.Add(block_start >= t["exit"]).OnlyEnforceIf(b_after)
        model.AddBoolOr([b_before, b_after])

solver = cp_model.CpSolver()
status = solver.Solve(model)

# --- 3. DASHBOARD VISUALIZATION ---
col1, col2 = st.columns([1, 2])

with col1:
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        start_t = solver.Value(block_start)
        end_t = solver.Value(block_end)
        st.success(f"✅ Safe Shadow-Block Found!")
        st.metric(label="Block Start Time", value=f"{start_t // 60:02d}:{start_t % 60:02d}")
        st.metric(label="Block End Time", value=f"{end_t // 60:02d}:{end_t % 60:02d}")
    else:
        st.error("❌ Critical Alert: No safe window available.")
        start_t = None

with col2:
    fig = go.Figure()
    for t in trains_today:
        if t["exit"] <= 1440:
            fig.add_trace(go.Scatter(x=[t["entry"], t["exit"]], y=[0, 100], mode='lines+markers', name=t["name"], line=dict(color='cyan', width=2)))
    if start_t is not None:
        fig.add_vrect(x0=start_t, x1=end_t, fillcolor="red", opacity=0.3, layer="below", line_width=0, annotation_text=f"Maintenance ({block_duration}m)")
    fig.update_layout(xaxis_title="Time of Day (Minutes)", yaxis_title="Distance", template="plotly_dark", height=400)
    st.plotly_chart(fig, use_container_width=True)