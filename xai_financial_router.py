import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Explainable AI Dispatcher (IR Edition)", layout="wide")
st.title("🧠 Explainable AI: Financial Rerouting Engine (Indian Railways)")
st.markdown("Transparent Constrained Shortest Path First (CSPF) decision logic tailored to Indian Railways Gross Tonne Kilometre (GTKM) metrics.")

# ==========================================
# 1. SETUP: INDIAN RAILWAYS DATASETS
# ==========================================
@st.cache_data
def load_mock_data():
    trains_data = {
        'train_id': ['12951 Rajdhani Exp', 'BOXN Coal Rake 42'],
        'train_type': ['Premium Passenger', 'Heavy Freight'],
        'weight_tons': [1100, 4200],  # Rajdhani ~1100t, Loaded BOXN rake ~4200t
        'needs_electricity': [True, False], # Electric (WAP-7) vs Diesel (WDG-4)
        'revenue_inr': [3500000, 5000000], 
        'penalty_per_min_inr': [5000, 500] # High punctuality penalty for premium passenger
    }
    lines_data = {
        'line_id': ['Line_A (Main Route)', 'Line_B (Bypass)', 'Line_C (Branch)'],
        'status': ['CLEAR', 'CLEAR', 'CLEAR'],
        'distance_km': [500, 650, 550], 
        'max_weight_tons': [5000, 2000, 5000], # Branch line has lower axle load limits
        'is_electrified': [True, True, False],
        'current_traffic_count': [2, 4, 1],
        'max_capacity': [5, 5, 5],
        'estimated_delay_min': [0, 45, 15] 
    }
    return pd.DataFrame(trains_data), pd.DataFrame(lines_data)

trains_df, lines_df = load_mock_data()

# ==========================================
# 2. UI CONTROLS
# ==========================================
st.sidebar.header("🚨 Crisis Injection")
blocked_line = st.sidebar.selectbox("Block a Line", ["None"] + lines_df['line_id'].tolist())
target_train = st.sidebar.selectbox("Select Train to Reroute", trains_df['train_id'].tolist())

if blocked_line != "None":
    lines_df.loc[lines_df['line_id'] == blocked_line, 'status'] = 'BLOCKED'

# ==========================================
# 3. CORE ALGORITHM (VISUALIZED)
# ==========================================
if st.sidebar.button("Run AI Optimizer"):
    train = trains_df[trains_df['train_id'] == target_train].iloc[0]
    st.subheader(f"🚂 Optimizing Route for {train['train_id']} ({train['train_type']})")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 1. Constraint Pruning")
        available_lines = lines_df[lines_df['status'] == 'CLEAR'].copy()
        valid_routes = []
        
        for index, line in available_lines.iterrows():
            rejected = False
            if train['weight_tons'] > line['max_weight_tons']:
                st.error(f"❌ **{line['line_id']} Rejected:** Axle load limit exceeded. Train ({train['weight_tons']}t) > Track Capacity ({line['max_weight_tons']}t)")
                rejected = True
            elif train['needs_electricity'] and not line['is_electrified']:
                st.error(f"❌ **{line['line_id']} Rejected:** Locomotive requires OHE. Line is non-electrified.")
                rejected = True
            elif line['current_traffic_count'] >= line['max_capacity']:
                st.error(f"❌ **{line['line_id']} Rejected:** Section traffic at maximum capacity.")
                rejected = True
                
            if not rejected:
                st.success(f"✅ **{line['line_id']} Validated:** Passes IR physical and traction constraints.")
                valid_routes.append(line)

    with col2:
        st.markdown("### 2. IR Financial Maximization")
        if not valid_routes:
            st.error("🛑 CRITICAL: No valid routes available. Trigger emergency halt.")
        else:
            best_route = None
            max_net_profit = -float('inf')
            
            for line in valid_routes:
                # Indian Railways Cost Formulation
                gtkm_cost = train['weight_tons'] * line['distance_km'] * 0.90
                delay_penalty = line['estimated_delay_min'] * train['penalty_per_min_inr']
                opportunity_cost = line['current_traffic_count'] * 15000 
                
                total_costs = gtkm_cost + delay_penalty + opportunity_cost
                net_profit = train['revenue_inr'] - total_costs
                
                with st.expander(f"Calculate Profit: {line['line_id']}"):
                    st.write(f"**Revenue:** +₹{train['revenue_inr']:,.2f}")
                    st.write(f"**GTKM Operating Cost (₹0.90/ton-km):** -₹{gtkm_cost:,.2f}")
                    st.write(f"**Delay Penalty ({line['estimated_delay_min']}m):** -₹{delay_penalty:,.2f}")
                    st.write(f"**Opportunity Cost:** -₹{opportunity_cost:,.2f}")
                    st.markdown(f"#### Net Profit: ₹{net_profit:,.2f}")
                
                if net_profit > max_net_profit:
                    max_net_profit = net_profit
                    best_route = line['line_id']

            st.success(f"🏆 **AI DECISION:** Reroute to **{best_route}** to maximize net profit at **₹{max_net_profit:,.2f}**")
            
st.markdown("---")
st.markdown("### Live Indian Railways CTC Database View")
st.dataframe(lines_df, use_container_width=True)