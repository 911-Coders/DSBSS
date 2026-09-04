import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Explainable AI Dispatcher", layout="wide")
st.title("🧠 Explainable AI: Financial Rerouting Engine")
st.markdown("Transparent Constrained Shortest Path First (CSPF) decision logic.")

# ==========================================
# 1. SETUP: MOCK DATASETS
# ==========================================
@st.cache_data
def load_mock_data():
    trains_data = {
        'train_id': ['T-Express-01', 'T-Freight-99'],
        'weight_tons': [450, 2500],
        'needs_electricity': [True, False],
        'priority': [1, 3],
        'revenue_usd': [25000, 15000],
        'penalty_per_min_usd': [500, 50]
    }
    lines_data = {
        'line_id': ['Line_A', 'Line_B', 'Line_C'],
        'status': ['CLEAR', 'CLEAR', 'CLEAR'],
        'max_weight_tons': [3000, 2000, 4000],
        'is_electrified': [True, True, False],
        'base_ops_cost_usd': [1000, 1500, 1200],
        'current_traffic_count': [2, 4, 1],
        'max_capacity': [5, 5, 5],
        'estimated_delay_min': [0, 15, 5]
    }
    return pd.DataFrame(trains_data), pd.DataFrame(lines_data)

trains_df, lines_df = load_mock_data()

# ==========================================
# 2. UI CONTROLS
# ==========================================
st.sidebar.header("🚨 Crisis Injection")
blocked_line = st.sidebar.selectbox("Block a Line", ["None", "Line_A", "Line_B", "Line_C"])
target_train = st.sidebar.selectbox("Select Train to Reroute", trains_df['train_id'].tolist())

if blocked_line != "None":
    lines_df.loc[lines_df['line_id'] == blocked_line, 'status'] = 'BLOCKED'

# ==========================================
# 3. CORE ALGORITHM (VISUALIZED)
# ==========================================
if st.sidebar.button("Run AI Optimizer"):
    train = trains_df[trains_df['train_id'] == target_train].iloc[0]
    st.subheader(f"🚂 Optimizing Route for {train['train_id']}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 1. Constraint Pruning")
        available_lines = lines_df[lines_df['status'] == 'CLEAR'].copy()
        valid_routes = []
        
        for index, line in available_lines.iterrows():
            rejected = False
            if train['weight_tons'] > line['max_weight_tons']:
                st.error(f"❌ **{line['line_id']} Rejected:** Train weight ({train['weight_tons']}t) > Capacity ({line['max_weight_tons']}t)")
                rejected = True
            elif train['needs_electricity'] and not line['is_electrified']:
                st.error(f"❌ **{line['line_id']} Rejected:** Train needs electricity. Line lacks overhead wires.")
                rejected = True
            elif line['current_traffic_count'] >= line['max_capacity']:
                st.error(f"❌ **{line['line_id']} Rejected:** Traffic at maximum capacity.")
                rejected = True
                
            if not rejected:
                st.success(f"✅ **{line['line_id']} Validated:** Passes all physical constraints.")
                valid_routes.append(line)

    with col2:
        st.markdown("### 2. Financial Maximization")
        if not valid_routes:
            st.error("🛑 CRITICAL: No valid routes available. Emergency halt required.")
        else:
            best_route = None
            max_net_profit = -float('inf')
            
            for line in valid_routes:
                delay_penalty = line['estimated_delay_min'] * train['penalty_per_min_usd']
                opportunity_cost = line['current_traffic_count'] * 200 
                total_costs = line['base_ops_cost_usd'] + delay_penalty + opportunity_cost
                net_profit = train['revenue_usd'] - total_costs
                
                with st.expander(f"Calculate Profit: {line['line_id']}"):
                    st.write(f"**Revenue:** +${train['revenue_usd']}")
                    st.write(f"**Base Operations Cost:** -${line['base_ops_cost_usd']}")
                    st.write(f"**Delay Penalty ({line['estimated_delay_min']}m):** -${delay_penalty}")
                    st.write(f"**Opportunity Cost:** -${opportunity_cost}")
                    st.markdown(f"#### Net Profit: ${net_profit}")
                
                if net_profit > max_net_profit:
                    max_net_profit = net_profit
                    best_route = line['line_id']

            st.success(f"🏆 **AI DECISION:** Reroute to **{best_route}** to maximize profit at **${max_net_profit}**")

st.markdown("---")
st.markdown("### Live Database View")
st.dataframe(lines_df, use_container_width=True)


#For runnung the code we need the folling commands
#source .venv/bin/activate
#pip install streamlit pandas

#streamlit run xai_financial_router.py
