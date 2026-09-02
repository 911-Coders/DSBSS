import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
from ortools.sat.python import cp_model

st.set_page_config(page_title="AI Rail Planner - Enterprise", layout="wide")
st.title("🚆 Enterprise Shadow-Block Auto-Generator")
st.markdown("Dynamic revenue-protecting schedule optimizer for Indian Railways.")

# --- 1. LOAD & PREP REAL DATA ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
@st.cache_data 
def load_data():
    df = pd.read_csv(os.path.join(BASE_DIR, "FINAL_ML_READY_DATA.csv"), low_memory=False)
    # Grab a workable chunk of trains passing through MAO (Madgoan)
    df = df[df['station code'].str.contains('MAO', na=False)].head(15).copy()
    
    # Assign financial priority/penalty weights (1 = standard, 5 = premium)
    def assign_weight(name):
        name = str(name).lower()
        if 'rajdhani' in name or 'shatabdi' in name: return 5
        elif 'exp' in name or 'express' in name: return 3
        return 1
    
    df['financial_weight'] = df['train name'].apply(assign_weight)
    return df

df = load_data()

# --- 2. THE CRISIS MATRIX (UI) ---
st.sidebar.header("🚨 Crisis Simulator")
incident = st.sidebar.selectbox("Inject Network Incident", ["None", "Heavy Fog", "Signal Failure", "Landslide"])
block_duration = st.sidebar.slider("Required Maintenance Block (Mins)", 60, 300, 120, step=30)

delay_added = 0
if incident == "Heavy Fog": delay_added = 45
elif incident == "Signal Failure": delay_added = 90
elif incident == "Landslide": delay_added = 240

# --- 3. THE PROFIT-MAXIMIZING AI SOLVER ---
model = cp_model.CpModel()

# Variables: Block can start anywhere in the 24h period (1440 mins)
block_start = model.NewIntVar(0, 1440 - block_duration, 'block_start')
block_end = model.NewIntVar(block_duration, 1440, 'block_end')
model.Add(block_end == block_start + block_duration)

train_overlap_penalties = []

# Loop through the actual dataset
for index, row in df.iterrows():
    # Adjust times based on the crisis simulator
    entry_time = int(row['arr_min']) + delay_added
    exit_time = int(row['dep_min']) + delay_added
    weight = int(row['financial_weight'])
    
    # If the train crosses midnight or has bad data, skip for simulation stability
    if entry_time >= exit_time or exit_time > 1440: continue
    
    # Create a boolean variable: Does the block overlap with this train?
    overlap = model.NewBoolVar(f'overlap_{index}')
    
    # Mathematical logic for intersection
    b_before = model.NewBoolVar(f'before_{index}')
    b_after = model.NewBoolVar(f'after_{index}')
    model.Add(block_end <= entry_time).OnlyEnforceIf(b_before)
    model.Add(block_start >= exit_time).OnlyEnforceIf(b_after)
    
    # If not before and not after, it MUST overlap
    model.AddBoolOr([b_before, b_after, overlap])
    model.AddImplication(b_before, overlap.Not())
    model.AddImplication(b_after, overlap.Not())
    
    # Store the penalty if this train is disrupted
    train_overlap_penalties.append(overlap * weight)

# OBJECTIVE: Minimize total financial penalty (Maximize Profit)
model.Minimize(sum(train_overlap_penalties))

solver = cp_model.CpSolver()
status = solver.Solve(model)

# --- 4. COMMAND CENTER VISUALIZATION ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Auto-Generator Status")
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        start_t = solver.Value(block_start)
        end_t = solver.Value(block_end)
        penalty_score = solver.ObjectiveValue()
        
        st.success(f"✅ AI Block Generated Successfully!")
        st.metric(label="Optimal Start Time", value=f"{start_t // 60:02d}:{start_t % 60:02d}")
        st.metric(label="Optimal End Time", value=f"{end_t // 60:02d}:{end_t % 60:02d}")
        st.warning(f"Total Disruption Penalty Score: {penalty_score}")
        st.info("The AI placed the block here to avoid delaying premium revenue trains.")
    else:
        st.error("❌ Critical Alert: Schedule deadlock.")
        start_t = None

with col2:
    fig = go.Figure()
    for index, row in df.iterrows():
        entry = int(row['arr_min']) + delay_added
        exit = int(row['dep_min']) + delay_added
        if entry < exit and exit <= 1440:
            color = 'red' if row['financial_weight'] == 5 else 'orange' if row['financial_weight'] == 3 else 'cyan'
            fig.add_trace(go.Scatter(x=[entry, exit], y=[0, 100], mode='lines+markers', name=row['train no'], line=dict(color=color, width=2)))
            
    if start_t is not None:
        fig.add_vrect(x0=start_t, x1=end_t, fillcolor="red", opacity=0.3, layer="below", line_width=0, annotation_text=f"Auto-Block")
    fig.update_layout(xaxis_title="Time of Day (Minutes)", yaxis_title="Track Distance", template="plotly_dark", height=450)
    st.plotly_chart(fig, use_container_width=True)
    
st.dataframe(df[['train no', 'train name', 'arr_min', 'dep_min', 'financial_weight']])