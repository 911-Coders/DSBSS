"""
Explainable AI (XAI) Financial Rerouting Engine
Implements 2-Stage Constrained Shortest Path First (CSPF) with plain-language audit trails.
"""

import pandas as pd
from typing import Dict, Any, List, Tuple

def get_default_corridor_infrastructure() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Provides standard corridor infrastructure and priority trains data."""
    trains_data = {
        'train_id': ['12051-JAN-SHATABDI', '22229-VANDE-BHARAT', '12617-MANGALA-EXP', 'BOXN-FREIGHT-911'],
        'train_name': ['Jan Shatabdi Express', 'Goa Vande Bharat Express', 'Mangala Lakshadweep Express', 'BOXN Heavy Freight'],
        'weight_tons': [450, 480, 750, 3200],
        'needs_electricity': [True, True, True, False],
        'priority_tier': [4, 5, 3, 1],
        'gross_revenue_inr': [350000, 750000, 420000, 950000],
        'penalty_per_min_inr': [2500, 5000, 1800, 800]
    }
    
    tracks_data = {
        'track_id': ['Up Main Line (ML-1)', 'Down Main Line (ML-2)', 'Up Loop / Platform 1 (LP-1)', 'Down Loop / Bypass (BP-1)'],
        'status': ['CLEAR', 'CLEAR', 'CLEAR', 'CLEAR'],
        'max_axle_tons': [2500, 2500, 1200, 4000],
        'is_electrified': [True, True, True, False],
        'base_energy_cost_inr': [12000, 12000, 18000, 28000],
        'current_traffic': [1, 2, 0, 1],
        'max_capacity': [4, 4, 3, 5],
        'estimated_delay_min': [0, 5, 12, 20]
    }
    
    return pd.DataFrame(trains_data), pd.DataFrame(tracks_data)

def evaluate_rerouting_decision(
    target_train_id: str,
    blocked_track_id: str = "None",
    trains_df: pd.DataFrame = None,
    tracks_df: pd.DataFrame = None
) -> Dict[str, Any]:
    """Evaluates 2-Stage CSPF for a given train under active track blockage conditions."""
    if trains_df is None or tracks_df is None:
        trains_df, tracks_df = get_default_corridor_infrastructure()
        
    working_tracks = tracks_df.copy()
    if blocked_track_id and blocked_track_id != "None":
        working_tracks.loc[working_tracks['track_id'] == blocked_track_id, 'status'] = 'BLOCKED'

    train_row = trains_df[trains_df['train_id'] == target_train_id]
    if train_row.empty:
        train_row = trains_df.iloc[0]
    else:
        train_row = train_row.iloc[0]

    # Stage 1: Physical Constraint Pruning
    validation_log = []
    valid_tracks = []

    for _, track in working_tracks.iterrows():
        t_id = track['track_id']
        if track['status'] == 'BLOCKED':
            validation_log.append({
                "track_id": t_id,
                "passed": False,
                "reason": f"Track is marked BLOCKED due to active maintenance / obstruction."
            })
            continue

        if train_row['weight_tons'] > track['max_axle_tons']:
            validation_log.append({
                "track_id": t_id,
                "passed": False,
                "reason": f"Train weight ({train_row['weight_tons']}t) exceeds track axle limit ({track['max_axle_tons']}t)."
            })
            continue

        if train_row['needs_electricity'] and not track['is_electrified']:
            validation_log.append({
                "track_id": t_id,
                "passed": False,
                "reason": f"Electric traction required, but line lacks OHE electrification."
            })
            continue

        if track['current_traffic'] >= track['max_capacity']:
            validation_log.append({
                "track_id": t_id,
                "passed": False,
                "reason": f"Track is at full section block capacity ({track['current_traffic']}/{track['max_capacity']})."
            })
            continue

        validation_log.append({
            "track_id": t_id,
            "passed": True,
            "reason": "Passed all physical gauge, traction, axle weight, and block capacity constraints."
        })
        valid_tracks.append(track)

    # Stage 2: Financial Maximization & Cost Optimization
    financial_evaluations = []
    best_track = None
    max_net_margin = -float('inf')

    for track in valid_tracks:
        delay_cost = track['estimated_delay_min'] * train_row['penalty_per_min_inr']
        opp_cost = track['current_traffic'] * 3500
        total_expense = track['base_energy_cost_inr'] + delay_cost + opp_cost
        net_margin = train_row['gross_revenue_inr'] - total_expense

        eval_item = {
            "track_id": track['track_id'],
            "gross_revenue": train_row['gross_revenue_inr'],
            "base_energy_cost": track['base_energy_cost_inr'],
            "delay_mins": track['estimated_delay_min'],
            "delay_penalty_cost": delay_cost,
            "opportunity_cost": opp_cost,
            "total_expense": total_expense,
            "net_margin": net_margin
        }
        financial_evaluations.append(eval_item)

        if net_margin > max_net_margin:
            max_net_margin = net_margin
            best_track = track['track_id']

    return {
        "train": train_row.to_dict(),
        "blocked_track": blocked_track_id,
        "validation_log": validation_log,
        "financial_evaluations": financial_evaluations,
        "best_track": best_track,
        "max_net_margin": max_net_margin if best_track else 0,
        "has_valid_route": len(valid_tracks) > 0,
        "tracks_table": working_tracks
    }
