"""
Corridor Schedule & Spatio-Temporal Trajectory Engine
Extracts realistic multi-station train movements for the Konkan Railway section:
Madgaon Jn (MAO - 0km) <-> Karmali (KRMI - 33km) <-> Thivim (THVM - 51km) <-> Pernem (PERN - 67km)
"""

import pandas as pd
import numpy as np
import os
from typing import Dict, Any, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, "FINAL_ML_READY_DATA.csv")

CORRIDOR_STATIONS = {
    'MAO': {'name': 'Madgaon Jn', 'km': 0, 'code': 'MAO'},
    'KRMI': {'name': 'Karmali', 'km': 33, 'code': 'KRMI'},
    'THVM': {'name': 'Thivim', 'km': 51, 'code': 'THVM'},
    'PERN': {'name': 'Pernem', 'km': 67, 'code': 'PERN'}
}

def assign_financial_weight(train_name: str) -> int:
    """Assigns railway priority / financial disruption penalty weight."""
    name = str(train_name).lower()
    if any(k in name for k in ['vande', 'rajdhani', 'shatabdi', 'duronto', 'tejas']):
        return 5  # Premium High-Speed
    elif any(k in name for k in ['exp', 'express', 'mail', 'superfast', 'spl']):
        return 3  # Standard Passenger / Mail
    return 1      # Freight / Local Suburban

def get_corridor_schedule(station_code='MAO') -> pd.DataFrame:
    """
    Backward-compatible extractor for CP-SAT solver.
    Returns cleaned schedule records with financial weights.
    """
    if not os.path.exists(CSV_PATH):
        return pd.DataFrame()

    df = pd.read_csv(CSV_PATH, low_memory=False)
    corridor_df = df[df['station code'].str.contains(station_code, na=False, case=False)].copy()
    corridor_df = corridor_df.head(25).copy()

    corridor_df['financial_weight'] = corridor_df['train name'].apply(assign_financial_weight)
    corridor_df['arr_min'] = pd.to_numeric(corridor_df['arr_min'], errors='coerce').fillna(0).astype(int)
    corridor_df['dep_min'] = pd.to_numeric(corridor_df['dep_min'], errors='coerce').fillna(0).astype(int)

    # Clean zero-duration stops
    for idx in corridor_df.index:
        if corridor_df.loc[idx, 'arr_min'] > corridor_df.loc[idx, 'dep_min']:
            if corridor_df.loc[idx, 'dep_min'] == 0:
                corridor_df.loc[idx, 'dep_min'] = min(1440, corridor_df.loc[idx, 'arr_min'] + 10)
            elif corridor_df.loc[idx, 'arr_min'] == 0:
                corridor_df.loc[idx, 'arr_min'] = max(0, corridor_df.loc[idx, 'dep_min'] - 10)

    return corridor_df

def get_corridor_trajectories(max_trains: int = 20) -> List[Dict[str, Any]]:
    """
    Extracts multi-station trajectory paths for genuine Marey (Time-Distance) charts.
    """
    if not os.path.exists(CSV_PATH):
        return []

    df = pd.read_csv(CSV_PATH, low_memory=False)
    stn_keys = list(CORRIDOR_STATIONS.keys())
    sub = df[df['station code'].isin(stn_keys)].copy()
    sub['km'] = sub['station code'].map(lambda c: CORRIDOR_STATIONS[c]['km'])
    sub['arr_min'] = pd.to_numeric(sub['arr_min'], errors='coerce').fillna(0).astype(int)
    sub['dep_min'] = pd.to_numeric(sub['dep_min'], errors='coerce').fillna(0).astype(int)

    train_groups = sub.groupby('train no')
    trajectories = []

    for train_no, grp in train_groups:
        grp = grp.sort_values(by=['seq', 'km'])
        t_name = str(grp['train name'].iloc[0]).title()
        weight = assign_financial_weight(t_name)

        # Build trajectory coordinates
        coords = []
        for _, row in grp.iterrows():
            stn = row['station code']
            km = CORRIDOR_STATIONS[stn]['km']
            t_arr = int(row['arr_min'])
            t_dep = int(row['dep_min'])
            t_eff = t_arr if t_arr > 0 else t_dep
            if t_eff > 0:
                coords.append((t_eff, km, stn))

        if len(coords) < 1:
            continue

        # If only 1 station is in dataset, project section traverse based on typical corridor speed (75 km/h ~ 55 mins)
        if len(coords) == 1:
            mid_t, mid_km, mid_stn = coords[0]
            if mid_km < 35: # Starts at MAO, heading to PERN
                x_pts = [max(0, mid_t - 5), min(1440, mid_t + 55)]
                y_pts = [0, 67]
                direction = "UP (MAO -> PERN)"
            else: # Starts at PERN, heading to MAO
                x_pts = [max(0, mid_t - 5), min(1440, mid_t + 55)]
                y_pts = [67, 0]
                direction = "DOWN (PERN -> MAO)"
        else:
            coords = sorted(coords, key=lambda c: c[0])
            x_pts = [c[0] for c in coords]
            y_pts = [c[1] for c in coords]
            direction = "UP (MAO -> PERN)" if y_pts[-1] >= y_pts[0] else "DOWN (PERN -> MAO)"

        trajectories.append({
            'train_no': str(train_no),
            'train_name': t_name,
            'financial_weight': weight,
            'category': 'Vande Bharat / Premium' if weight == 5 else 'Express / Mail' if weight == 3 else 'Freight / Suburban',
            'x_times': x_pts,
            'y_distances': y_pts,
            'entry_min': min(x_pts),
            'exit_min': max(x_pts),
            'direction': direction
        })

        if len(trajectories) >= max_trains:
            break

    return sorted(trajectories, key=lambda t: t['entry_min'])