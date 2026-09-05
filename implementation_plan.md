# AI-Powered Enterprise Shadow-Block Planning System (SIH26027)

## Master Implementation Plan & System Status

This document compiles the current architecture, implementation status, and complete technical specifications for the Indian Railways Section Controller & Automatic Shadow-Block Planning Platform.

---

## 1. System Architecture & Module Map

```
d:\DSBSS\
├── core/
│   ├── __init__.py
│   ├── data_engine.py          # [DONE] Corridor schedule extractor with financial weights
│   ├── shadow_block_solver.py  # [DONE] OR-Tools CP-SAT multi-department bundling optimizer
│   ├── xai_rerouter.py         # [DONE] 2-Stage CSPF explainable financial rerouting engine
│   └── ml_diagnostics.py       # [DONE] Point-machine IoT telemetry inference & auto-trigger pipeline
├── assets/
│   └── styles.css              # [DONE] Dark-mode enterprise control room styling
├── main_app.py                 # [DONE] Unified Streamlit Section Controller Dashboard
├── FINAL_ML_READY_DATA.csv     # [EXISTS] 186k+ real train timetable records
├── point_machine_telemetry_trend.csv # [EXISTS] Switch machine sensor telemetry
├── sensor_simulator.py         # [EXISTS] Prototype IoT simulator
├── train_model.py              # [EXISTS] ML model training script
├── xai_financial_router.py     # [EXISTS] Standalone routing prototype
├── block.py                    # [EXISTS] Standalone single-block solver prototype
└── app.py                      # [EXISTS] Legacy Streamlit app
```

---

## 2. Implementation Status Summary

| Component | Target File | Status | Description |
| :--- | :--- | :---: | :--- |
| **1. Corridor Data Engine** | [`core/data_engine.py`](file:///d:/DSBSS/core/data_engine.py) | 🟢 **Implemented** | Extracts real train timetable data for section corridors (e.g., `MAO`), cleans time values, and tags train priorities/financial weights (5 for Vande Bharat/Rajdhani, 3 for Mail/Express, 1 for Freight/Local). |
| **2. Multi-Asset Shadow-Block Solver** | [`core/shadow_block_solver.py`](file:///d:/DSBSS/core/shadow_block_solver.py) | 🟢 **Implemented** | OR-Tools CP-SAT multi-department solver bundling Track Engineering (120m), Electrical OHE (90m), and S&T Signaling (60m) into single overlapping windows to minimize disruption penalties. |
| **3. XAI & Financial Rerouting** | [`core/xai_rerouter.py`](file:///d:/DSBSS/core/xai_rerouter.py) | 🟢 **Implemented** | 2-Stage CSPF engine evaluating physical track constraints (gauge, axle load, electrification) and commercial cost-benefit trade-offs with plain-language audit logs. |
| **4. Predictive ML Diagnostics** | [`core/ml_diagnostics.py`](file:///d:/DSBSS/core/ml_diagnostics.py) | 🟢 **Implemented** | Evaluates live IoT sensor telemetry (amps, throw time, vibration) with Random Forest classifier and auto-injects emergency maintenance block requests when degradation exceeds threshold. |
| **5. Unified Control Center** | [`main_app.py`](file:///d:/DSBSS/main_app.py) & [`assets/styles.css`](file:///d:/DSBSS/assets/styles.css) | 🟢 **Implemented** | Centralized dashboard featuring Marey Time-Distance string charts, interactive scenario injection (fog, track failure), telemetry monitors, and ROI analytics. |

---

## 3. How to Run the System

To launch the complete Indian Railways Section Controller Dashboard:
```bash
streamlit run main_app.py
```
