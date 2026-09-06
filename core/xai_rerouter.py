"""
Explainable AI (XAI) Financial Rerouting Engine (Indian Railways Edition)
Implements 2-Stage Constrained Shortest Path First (CSPF) with GTKM costing metrics
and plain-language audit trails.
"""

import pandas as pd
from typing import Dict, Any, List, Tuple

def get_default_corridor_infrastructure() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Provides standard Indian Railways corridor infrastructure and priority rolling stock.
    Features realistic axle weights, traction requirements, and commercial GTKM parameters.
    """
    trains_data = {
        'train_id': [
            '12951 Rajdhani Exp',
            'BOXN Coal Rake 42',
            '22229 Vande Bharat Exp',
            '12051 Jan Shatabdi Exp',
            '12617 Mangala Lakshadweep',
            'BCN Freight Rake 19'
        ],
        'train_type': [
            'Premium Superfast Passenger',
            'Heavy Bulk Freight (Coal)',
            'Semi-High Speed Express',
            'Intercity Express',
            'Long-Distance Mail/Express',
            'Standard Freight (Foodgrain)'
        ],
        'train_name': [
            'Rajdhani Express',
            'BOXN Heavy Coal Rake',
            'Goa Vande Bharat Express',
            'Jan Shatabdi Express',
            'Mangala Lakshadweep Express',
            'BCN Foodgrain Rake'
        ],
        'loco_type': [
            'WAP-7 (Electric 6000 HP)',
            'Twin WDG-4 (Diesel 9000 HP)',
            'Trainset 25kV OHE',
            'WAP-7 (Electric 6000 HP)',
            'WAP-7 (Electric 6000 HP)',
            'WDG-4 (Diesel 4500 HP)'
        ],
        'weight_tons': [1100, 4200, 480, 450, 750, 2800],
        'needs_electricity': [True, False, True, True, True, False],
        'priority_tier': [5, 2, 5, 4, 3, 1],
        'revenue_inr': [3500000, 5000000, 2800000, 1850000, 1420000, 2900000],
        'gross_revenue_inr': [3500000, 5000000, 2800000, 1850000, 1420000, 2900000],
        'penalty_per_min_inr': [5000, 500, 5000, 2500, 1800, 800]
    }

    lines_data = {
        'track_id': [
            'Line_A (Main Route)',
            'Line_B (Bypass Loop)',
            'Line_C (Branch Line)',
            'Line_D (Chord Bypass)'
        ],
        'line_id': [
            'Line_A (Main Route)',
            'Line_B (Bypass Loop)',
            'Line_C (Branch Line)',
            'Line_D (Chord Bypass)'
        ],
        'track_description': [
            'Direct Double High-Speed Main Line (Section KM 0-500)',
            'Outer Suburban Quad-Track Bypass Loop (Section KM 0-650)',
            'Single Non-Electrified Freight Branch Line (Section KM 0-550)',
            'Dedicated Heavy-Haul Chord Bypass (Section KM 0-580)'
        ],
        'status': ['CLEAR', 'CLEAR', 'CLEAR', 'CLEAR'],
        'distance_km': [500, 650, 550, 580],
        'max_weight_tons': [5000, 2000, 5000, 5500],
        'max_axle_tons': [5000, 2000, 5000, 5500],
        'is_electrified': [True, True, False, True],
        'current_traffic_count': [2, 4, 1, 2],
        'current_traffic': [2, 4, 1, 2],
        'max_capacity': [5, 5, 5, 6],
        'estimated_delay_min': [0, 45, 15, 20]
    }

    return pd.DataFrame(trains_data), pd.DataFrame(lines_data)

def evaluate_rerouting_decision(
    target_train_id: str,
    blocked_track_id: str = "None",
    trains_df: pd.DataFrame = None,
    tracks_df: pd.DataFrame = None,
    gtkm_rate: float = 0.90,
    opp_cost_rate: float = 15000.0
) -> Dict[str, Any]:
    """
    Evaluates 2-Stage Constrained Shortest Path First (CSPF) decision logic:
    - Stage 1: Constraint Pruning (axle load, traction OHE, headway capacity, blockage)
    - Stage 2: Indian Railways GTKM Financial Maximization:
        P_net = Revenue - (GTKM_cost + Delay_penalty + Opportunity_cost)
    """
    if trains_df is None or tracks_df is None:
        trains_df, tracks_df = get_default_corridor_infrastructure()

    working_tracks = tracks_df.copy()
    track_key = 'track_id' if 'track_id' in working_tracks.columns else 'line_id'

    if blocked_track_id and blocked_track_id != "None":
        working_tracks.loc[working_tracks[track_key] == blocked_track_id, 'status'] = 'BLOCKED'

    # Match train
    train_matches = trains_df[trains_df['train_id'] == target_train_id]
    if train_matches.empty:
        train_row = trains_df.iloc[0]
    else:
        train_row = train_matches.iloc[0]

    train_weight = float(train_row['weight_tons'])
    needs_elec = bool(train_row['needs_electricity'])
    revenue = float(train_row.get('revenue_inr', train_row.get('gross_revenue_inr', 0)))
    penalty_rate = float(train_row['penalty_per_min_inr'])

    # Stage 1: Physical Feasibility & Constraint Pruning
    validation_log = []
    valid_tracks = []

    for _, track in working_tracks.iterrows():
        t_id = track[track_key]
        max_wt = float(track.get('max_weight_tons', track.get('max_axle_tons', 5000)))
        curr_traf = int(track.get('current_traffic_count', track.get('current_traffic', 0)))
        max_cap = int(track['max_capacity'])
        is_elec = bool(track['is_electrified'])
        status = str(track['status']).upper()

        if status == 'BLOCKED':
            validation_log.append({
                "track_id": t_id,
                "passed": False,
                "criterion": "Block Status",
                "reason": f"Track is marked BLOCKED due to active incident / track maintenance."
            })
            continue

        if train_weight > max_wt:
            validation_log.append({
                "track_id": t_id,
                "passed": False,
                "criterion": "Axle Load Limit",
                "reason": f"Axle load limit exceeded. Train ({train_weight:,.0f}t) > Track Limit ({max_wt:,.0f}t)."
            })
            continue

        if needs_elec and not is_elec:
            validation_log.append({
                "track_id": t_id,
                "passed": False,
                "criterion": "Traction / Catenary",
                "reason": f"Locomotive requires 25kV AC OHE electrification. Track is non-electrified (Diesel only)."
            })
            continue

        if curr_traf >= max_cap:
            validation_log.append({
                "track_id": t_id,
                "passed": False,
                "criterion": "Block Capacity",
                "reason": f"Section traffic at saturation capacity ({curr_traf}/{max_cap} blocks occupied)."
            })
            continue

        validation_log.append({
            "track_id": t_id,
            "passed": True,
            "criterion": "Feasibility Verified",
            "reason": f"Passes all IR physical axle load ({max_wt:,.0f}t), traction, and headway safety constraints."
        })
        valid_tracks.append(track)

    # Stage 2: Indian Railways GTKM Financial Maximization
    financial_evaluations = []
    best_track = None
    max_net_profit = -float('inf')

    for track in valid_tracks:
        t_id = track[track_key]
        dist_km = float(track['distance_km'])
        delay_min = float(track['estimated_delay_min'])
        curr_traf = int(track.get('current_traffic_count', track.get('current_traffic', 0)))

        # 1. Gross Tonne Kilometre (GTKM) Operating Cost
        # Standard IR benchmark: Train Weight (Tons) x Distance (km) x Unit Cost
        gtkm_cost = train_weight * dist_km * gtkm_rate

        # 2. Punctuality Delay Penalty
        delay_penalty = delay_min * penalty_rate

        # 3. Network Bottleneck / Opportunity Cost
        opp_cost = curr_traf * opp_cost_rate

        # Aggregated Cost and Net Margin
        total_costs = gtkm_cost + delay_penalty + opp_cost
        net_profit = revenue - total_costs
        margin_pct = (net_profit / revenue * 100.0) if revenue > 0 else 0.0

        eval_item = {
            "track_id": t_id,
            "distance_km": dist_km,
            "weight_tons": train_weight,
            "gtkm_rate": gtkm_rate,
            "gross_revenue": revenue,
            "gtkm_cost": gtkm_cost,
            "delay_mins": delay_min,
            "penalty_per_min": penalty_rate,
            "delay_penalty_cost": delay_penalty,
            "current_traffic": curr_traf,
            "opp_cost_rate": opp_cost_rate,
            "opportunity_cost": opp_cost,
            "total_expense": total_costs,
            "net_margin": net_profit,
            "margin_pct": margin_pct
        }
        financial_evaluations.append(eval_item)

        if net_profit > max_net_profit:
            max_net_profit = net_profit
            best_track = t_id

    # Format into dataframe for convenience
    fin_df = pd.DataFrame(financial_evaluations) if financial_evaluations else pd.DataFrame()

    return {
        "train": train_row.to_dict(),
        "blocked_track": blocked_track_id,
        "validation_log": validation_log,
        "financial_evaluations": financial_evaluations,
        "financial_df": fin_df,
        "best_track": best_track,
        "max_net_margin": max_net_profit if best_track else 0.0,
        "has_valid_route": len(valid_tracks) > 0,
        "tracks_table": working_tracks,
        "gtkm_rate": gtkm_rate,
        "opp_cost_rate": opp_cost_rate
    }
