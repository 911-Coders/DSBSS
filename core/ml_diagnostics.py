"""
Predictive IoT Telemetry & ML Asset Diagnostics Engine
Analyzes point-machine sensor telemetry and auto-triggers maintenance block requests.
"""

import os
import pandas as pd
import numpy as np
import joblib
from typing import Dict, Any, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "rf_model.pkl")
TELEMETRY_CSV = os.path.join(BASE_DIR, "point_machine_telemetry_trend.csv")

def load_telemetry_data(num_records: int = 100) -> pd.DataFrame:
    """Loads recent switch machine sensor telemetry."""
    if os.path.exists(TELEMETRY_CSV):
        df = pd.read_csv(TELEMETRY_CSV)
        return df.tail(num_records).copy()
    else:
        # Fallback dummy telemetry generator
        records = []
        for i in range(num_records):
            records.append({
                'message_id': f"MSG-{i:04d}",
                'timestamp': f"2026-09-05T12:{i % 60:02d}:00Z",
                'asset_id': 'PM-42-EAST',
                'motor_current_peak_amps': round(4.8 + (0.03 * (i % 20)), 2),
                'motor_current_avg_amps': round(3.2 + (0.02 * (i % 20)), 2),
                'throw_duration_ms': 3000 + (10 * (i % 30)),
                'vibration_peak_g': round(0.1 + (0.005 * (i % 15)), 3),
                'ambient_temp_c': 30.5,
                'label_anomaly': 1 if i > 85 else 0
            })
        return pd.DataFrame(records)

def evaluate_asset_health(
    motor_peak: float = 5.2,
    motor_avg: float = 3.5,
    throw_duration: int = 3100,
    vibration: float = 0.12,
    ambient_temp: float = 31.0
) -> Dict[str, Any]:
    """
    Evaluates point-machine telemetry reading and computes anomaly probability.
    """
    features = pd.DataFrame([{
        'motor_current_peak_amps': motor_peak,
        'motor_current_avg_amps': motor_avg,
        'throw_duration_ms': throw_duration,
        'vibration_peak_g': vibration,
        'ambient_temp_c': ambient_temp
    }])

    anomaly_prob = 0.0
    model_loaded = False

    if os.path.exists(MODEL_PATH):
        try:
            model = joblib.load(MODEL_PATH)
            probs = model.predict_proba(features)
            anomaly_prob = float(probs[0][1])
            model_loaded = True
        except Exception as e:
            model_loaded = False

    if not model_loaded:
        # Heuristic fallback if model pkl isn't loaded
        severity = 0.0
        if motor_peak > 6.0: severity += 0.35
        if throw_duration > 3800: severity += 0.35
        if vibration > 0.25: severity += 0.30
        anomaly_prob = min(1.0, severity)

    is_critical = anomaly_prob >= 0.75
    health_score = max(0, int((1.0 - anomaly_prob) * 100))

    if is_critical:
        status_label = "CRITICAL DEGRADATION"
        recommended_action = "Auto-trigger S&T Emergency Shadow Block (60m window)"
        urgency = "HIGH"
    elif anomaly_prob >= 0.40:
        status_label = "MODERATE WEAR"
        recommended_action = "Schedule routine inspection during next bundled window"
        urgency = "MEDIUM"
    else:
        status_label = "OPTIMAL HEALTH"
        recommended_action = "Normal operations - No block required"
        urgency = "LOW"

    return {
        "model_loaded": model_loaded,
        "anomaly_probability": anomaly_prob,
        "health_score": health_score,
        "status_label": status_label,
        "recommended_action": recommended_action,
        "urgency": urgency,
        "auto_block_suggested": is_critical,
        "suggested_block_duration_mins": 60 if is_critical else 0,
        "input_telemetry": {
            "motor_peak_amps": motor_peak,
            "motor_avg_amps": motor_avg,
            "throw_duration_ms": throw_duration,
            "vibration_g": vibration,
            "ambient_temp_c": ambient_temp
        }
    }
