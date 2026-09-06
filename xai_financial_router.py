import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

from core.xai_rerouter import get_default_corridor_infrastructure, evaluate_rerouting_decision

st.set_page_config(
    page_title="Explainable AI Dispatcher (IR GTKM Edition)",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 Explainable AI: Financial Rerouting Engine (Indian Railways)")
st.markdown("Transparent Constrained Shortest Path First (CSPF) decision logic tailored to Indian Railways Gross Tonne Kilometre (GTKM) metrics.")

# 1. Mathematical Objective HUD
st.markdown("""
<div style="background: rgba(14, 21, 37, 0.9); border-left: 4px solid #38bdf8; border-radius: 8px; padding: 14px 18px; margin-bottom: 1.2rem; border: 1px solid rgba(255,255,255,0.08);">
    <div style="font-size: 0.85rem; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;">
        📐 Mathematical Objective Function: Dynamic Net Profit Maximization
    </div>
    <div style="font-size: 1.2rem; font-weight: 700; color: #f8fafc; margin-bottom: 8px; font-family: monospace;">
        P<sub>net</sub> = R - [ C<sub>GTKM</sub> + P<sub>delay</sub> + C<sub>opp</sub> ]
    </div>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; font-size: 0.82rem; color: #94a3b8;">
        <div><b style="color: #34d399;">R (Commercial Revenue):</b> Freight tariffs & passenger ticket collection.</div>
        <div><b style="color: #38bdf8;">C<sub>GTKM</sub> (Operating Cost):</b> Weight (T) × Distance (km) × ₹0.90/T-km.</div>
        <div><b style="color: #f59e0b;">P<sub>delay</sub> (Punctuality Penalty):</b> Delay (min) × Section SLA Penalty Rate (₹/min).</div>
        <div><b style="color: #f43f5e;">C<sub>opp</sub> (Opportunity Cost):</b> Active Section Rakes × ₹15,000 Bottleneck Surcharge.</div>
    </div>
</div>
""", unsafe_allow_html=True)

# 2. Data Ingestion
trains_df, lines_df = get_default_corridor_infrastructure()

# 3. Sidebar Controls
st.sidebar.header("🚨 Crisis Injection & Selection")
blocked_line = st.sidebar.selectbox("Block a Line / Track", ["None"] + lines_df['line_id'].tolist(), index=1)
target_train = st.sidebar.selectbox("Select Train to Reroute", trains_df['train_id'].tolist(), index=0)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ IR Unit Cost Calibration")
gtkm_rate = st.sidebar.slider("GTKM Unit Cost (₹/ton-km)", 0.50, 2.00, 0.90, step=0.05)
opp_cost_rate = st.sidebar.slider("Opportunity Cost per Train (₹)", 5000, 30000, 15000, step=2500)

# Evaluate Decision
xai_res = evaluate_rerouting_decision(
    target_train_id=target_train,
    blocked_track_id=blocked_line,
    trains_df=trains_df,
    tracks_df=lines_df,
    gtkm_rate=gtkm_rate,
    opp_cost_rate=opp_cost_rate
)

train = xai_res['train']
st.subheader(f"🚂 Optimizing Route for {train['train_id']} ({train.get('train_type', '')})")

# Metadata row
m1, m2, m3, m4 = st.columns(4)
m1.metric("Gross Weight", f"{train['weight_tons']:,} Tonnes")
m2.metric("Traction", "25kV AC Electric" if train['needs_electricity'] else "Diesel Locomotive")
m3.metric("Commercial Revenue", f"₹{train.get('revenue_inr', train.get('gross_revenue_inr', 0)):,.0f}")
m4.metric("Delay Penalty", f"₹{train['penalty_per_min_inr']:,}/min")

st.markdown("---")

# Decision Announcement
if xai_res['best_track']:
    st.success(f"🏆 **AI DECISION:** Reroute **{train['train_id']}** via **{xai_res['best_track']}** to maximize net profit at **₹{xai_res['max_net_margin']:,.2f}**")
else:
    st.error("🛑 **CRITICAL DISPATCH ALERT:** No valid routes available. Hold train at outer home signal.")

# Two columns for 2-Stage CSPF
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 1. Constraint Pruning (Physical & Traction Audits)")
    for log in xai_res['validation_log']:
        if log['passed']:
            st.success(f"✅ **{log['track_id']} Validated:** {log['reason']}")
        else:
            st.error(f"❌ **{log['track_id']} Rejected:** {log['reason']}")

with col2:
    st.markdown("### 2. IR Financial Maximization & Cost Breakdown")
    if not xai_res['financial_evaluations']:
        st.warning("No candidate tracks passed physical feasibility checks.")
    else:
        for eval_data in xai_res['financial_evaluations']:
            is_winner = (eval_data['track_id'] == xai_res['best_track'])
            with st.expander(f"{'🏆 [AI CHOICE] ' if is_winner else ''}Calculate Profit: {eval_data['track_id']} → Net Profit: ₹{eval_data['net_margin']:,.2f}", expanded=is_winner):
                st.write(f"**Gross Revenue:** +₹{eval_data['gross_revenue']:,.2f}")
                st.write(f"**GTKM Operating Cost ({eval_data['weight_tons']:,}t × {eval_data['distance_km']}km × ₹{eval_data['gtkm_rate']:.2f}):** -₹{eval_data['gtkm_cost']:,.2f}")
                st.write(f"**Delay Penalty ({eval_data['delay_mins']}m × ₹{eval_data['penalty_per_min']:,}/m):** -₹{eval_data['delay_penalty_cost']:,.2f}")
                st.write(f"**Opportunity Bottleneck Cost ({eval_data['current_traffic']} rakes × ₹{eval_data['opp_cost_rate']:,}):** -₹{eval_data['opportunity_cost']:,.2f}")
                st.markdown(f"#### Net Profit: ₹{eval_data['net_margin']:,.2f} (Margin: {eval_data['margin_pct']:.1f}%)")

if xai_res['financial_evaluations']:
    st.markdown("---")
    st.markdown("### 📊 Comparative Route Financial Performance")
    fin_df = pd.DataFrame(xai_res['financial_evaluations'])
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Net Margin", x=fin_df['track_id'], y=fin_df['net_margin'], marker_color="#10b981"))
    fig.add_trace(go.Bar(name="GTKM Operating Cost", x=fin_df['track_id'], y=fin_df['gtkm_cost'], marker_color="#38bdf8"))
    fig.add_trace(go.Bar(name="Delay Penalty", x=fin_df['track_id'], y=fin_df['delay_penalty_cost'], marker_color="#f59e0b"))
    fig.add_trace(go.Bar(name="Opportunity Cost", x=fin_df['track_id'], y=fin_df['opportunity_cost'], marker_color="#f43f5e"))
    fig.update_layout(barmode='group', height=300, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, width='stretch')

st.markdown("---")
st.markdown("### Live Indian Railways CTC Database View")
st.dataframe(xai_res['tracks_table'], width='stretch')