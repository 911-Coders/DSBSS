"""
Multi-Department Shadow-Block Optimization Engine (OR-Tools CP-SAT)
Synchronizes multi-department maintenance requests into bundled shadow-block windows.
"""

from ortools.sat.python import cp_model
import pandas as pd
from typing import Dict, Any, List

def solve_shadow_block(
    trains_df: pd.DataFrame,
    eng_duration: int = 120,
    elec_duration: int = 90,
    snt_duration: int = 60,
    incident_delay: int = 0
) -> Dict[str, Any]:
    """
    Optimizes the multi-department shadow block placement across a 24-hour window (1440 mins).
    """
    # 1. Calculate Bundled vs Unbundled Durations
    bundled_duration = max(eng_duration, elec_duration, snt_duration)
    unbundled_total = eng_duration + elec_duration + snt_duration
    time_saved_mins = unbundled_total - bundled_duration
    capacity_gain_pct = (time_saved_mins / unbundled_total) * 100 if unbundled_total > 0 else 0.0

    if trains_df.empty or bundled_duration <= 0:
        return {
            "status": "NO_DATA",
            "start_time_min": 0,
            "end_time_min": 0,
            "bundled_duration": bundled_duration,
            "unbundled_total": unbundled_total,
            "time_saved_mins": time_saved_mins,
            "capacity_gain_pct": capacity_gain_pct,
            "penalty_score": 0,
            "affected_trains": []
        }

    # 2. Build OR-Tools CP-SAT Model
    model = cp_model.CpModel()
    
    # Block start and end variables (0 to 1440 minutes in a day)
    block_start = model.NewIntVar(0, 1440 - bundled_duration, 'block_start')
    block_end = model.NewIntVar(bundled_duration, 1440, 'block_end')
    model.Add(block_end == block_start + bundled_duration)

    train_overlap_penalties = []
    train_overlap_vars = []

    # 3. Formulate train overlap constraints with incident delays
    for index, row in trains_df.iterrows():
        entry_time = int(row.get('arr_min', 0)) + incident_delay
        exit_time = int(row.get('dep_min', 0)) + incident_delay
        weight = int(row.get('financial_weight', 1))

        # Handle crossing midnight / anomalies
        if entry_time >= exit_time or exit_time > 1440:
            continue

        overlap = model.NewBoolVar(f'overlap_{index}')
        b_before = model.NewBoolVar(f'before_{index}')
        b_after = model.NewBoolVar(f'after_{index}')

        model.Add(block_end <= entry_time).OnlyEnforceIf(b_before)
        model.Add(block_start >= exit_time).OnlyEnforceIf(b_after)

        model.AddBoolOr([b_before, b_after, overlap])
        model.AddImplication(b_before, overlap.Not())
        model.AddImplication(b_after, overlap.Not())

        train_overlap_penalties.append(overlap * weight)
        train_overlap_vars.append((index, row, overlap, entry_time, exit_time))

    # Objective: Minimize total financial penalty for delayed/disrupted trains
    model.Minimize(sum(train_overlap_penalties))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5.0
    status = solver.Solve(model)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        start_val = int(solver.Value(block_start))
        end_val = int(solver.Value(block_end))
        penalty_val = int(solver.ObjectiveValue())

        affected = []
        for idx, row, var, ent, ext in train_overlap_vars:
            if solver.Value(var) == 1:
                affected.append({
                    "train_no": row.get('train no', f"TR-{idx}"),
                    "train_name": row.get('train name', "Unknown"),
                    "financial_weight": row.get('financial_weight', 1),
                    "entry_min": ent,
                    "exit_min": ext
                })

        return {
            "status": "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE",
            "start_time_min": start_val,
            "end_time_min": end_val,
            "bundled_duration": bundled_duration,
            "unbundled_total": unbundled_total,
            "time_saved_mins": time_saved_mins,
            "capacity_gain_pct": capacity_gain_pct,
            "penalty_score": penalty_val,
            "affected_trains": affected
        }
    else:
        return {
            "status": "INFEASIBLE",
            "start_time_min": 0,
            "end_time_min": bundled_duration,
            "bundled_duration": bundled_duration,
            "unbundled_total": unbundled_total,
            "time_saved_mins": time_saved_mins,
            "capacity_gain_pct": capacity_gain_pct,
            "penalty_score": 9999,
            "affected_trains": []
        }

def format_min_to_hhmm(minutes: int) -> str:
    """Helper to convert minute of day (0-1440) to HH:MM format."""
    hours = (minutes // 60) % 24
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"
