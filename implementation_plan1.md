# Implementation Plan: AI-Powered Enterprise Shadow-Block Planning System (SIH26027)

Upgrade the current prototype into a unified, production-grade **Indian Railways Section Controller & Automatic Shadow-Block Planning Platform** for Smart India Hackathon problem statement **SIH26027**.

## User Review Required

> [!IMPORTANT]
> **Key Architecture Decisions:**
> 1. **Unified Enterprise UI**: Consolidate all independent scripts (`app.py`, `block.py`, `xai_financial_router.py`, `data.py`) into a single, polished multi-view Indian Railways Dispatcher Dashboard.
> 2. **Multi-Asset Shadow Blocking**: Expand OR-Tools solver from single-block placement to **multi-department synchronized bundling** (Track Engineering + OHE Electrical + S&T Signaling) to maximize track availability.
> 3. **Corridor-Level Time-Distance String Chart (Marey Chart)**: Implement standard Indian Railways time-distance string charts for section controllers with visual conflict resolution.
> 4. **Live Anomaly-to-Block Pipeline**: Direct automated bridge between IoT ML anomaly detection and the mathematical solver.

---

## Proposed System Architecture

```
d:\DSBSS\
├── core/
│   ├── data_engine.py          # Real corridor extractor (MAO-KRMI-THVM-PERN section from CSV)
│   ├── shadow_block_solver.py  # Advanced OR-Tools CP-SAT multi-asset shadow-block optimizer
│   ├── xai_rerouter.py         # 2-Stage CSPF dynamic financial rerouting engine
│   └── ml_diagnostics.py       # Point-machine telemetry inference & auto-trigger pipeline
├── assets/
│   └── styles.css              # Dark-mode enterprise control room styling
├── main_app.py                 # Unified Enterprise Indian Railways Control Center
├── FINAL_ML_READY_DATA.csv     # 186k+ real train timetable records
├── sensor_simulator.py         # IoT stream simulator for switch machines
└── train_model.py              # ML classifier trainer
```

---

## Proposed Changes

### 1. Data Processing & Corridor Engine
#### [NEW] [`core/data_engine.py`](file:///d:/DSBSS/core/data_engine.py)
- Load [FINAL_ML_READY_DATA.csv](file:///d:/DSBSS/FINAL_ML_READY_DATA.csv) and extract realistic multi-station section corridors (e.g. Madgaon `MAO` $\to$ Karmali `KRMI` $\to$ Thivim `THVM` $\to$ Pernem `PERN`).
- Calculate cumulative kilometer distances, arrival/departure timestamps in minutes, and speed gradients.
- Categorize train priorities and commercial penalty weights (*Vande Bharat/Rajdhani* = 5, *Superfast/Mail* = 3, *Freight/Local* = 1).

---

### 2. Multi-Asset Shadow-Block Optimizer (OR-Tools CP-SAT)
#### [NEW] [`core/shadow_block_solver.py`](file:///d:/DSBSS/core/shadow_block_solver.py)
- Upgrade the single-block model in [block.py](file:///d:/DSBSS/block.py) to a **Multi-Department Shadow-Block Optimizer**:
  - **Track Maintenance (Engineering)**: e.g., Track Tamping (120 mins)
  - **OHE Maintenance (Electrical)**: e.g., Wire Inspection (90 mins)
  - **S&T Maintenance (Signaling & Telecom)**: e.g., Point Machine Overhaul (60 mins)
- **Shadow-Block Bundling Constraint**: Mathematical bonus/enforcement to align disparate maintenance requests into an overlapping single "Shadow Block" window on the corridor, reducing total line closures from $120+90+60 = 270\text{ mins}$ down to a single coordinated $\approx 120\text{ min}$ window.
- **Objective**:
  $$\min \sum (\text{Train Delay Penalty} \times \text{Financial Weight}) + \text{Unclustered Maintenance Overhead}$$

---

### 3. Explainable AI & Financial Rerouting Engine
#### [NEW] [`core/xai_rerouter.py`](file:///d:/DSBSS/core/xai_rerouter.py)
- Replace mock data from [xai_financial_router.py](file:///d:/DSBSS/xai_financial_router.py) with real corridor tracks (Up Main Line, Down Main Line, Loop/Bypass Lines).
- Implements two-phase CSPF:
  1. **Physical Constraint Filtering**: Gauge, electrification, axle load, line length, block interlocking status.
  2. **Financial Optimization**: Evaluates gross revenue against operational power cost, delay penalties per minute, and platform dwell opportunity cost.
- Produces plain-language explanation logs for Section Controllers.

---

### 4. Predictive Telemetry & Live Auto-Triggering
#### [NEW] [`core/ml_diagnostics.py`](file:///d:/DSBSS/core/ml_diagnostics.py)
- Ingests real-time telemetry from [point_machine_telemetry_trend.csv](file:///d:/DSBSS/point_machine_telemetry_trend.csv) / simulator.
- Evaluates asset health with `RandomForestClassifier` (`rf_model.pkl`).
- When degradation threshold ($>80\%$) is reached, **automatically packages an emergency/scheduled S&T maintenance request** and triggers the CP-SAT solver to schedule a shadow-block without manual human entry.

---

### 5. Unified Enterprise Control Center (Streamlit + Plotly)
#### [NEW] [`main_app.py`](file:///d:/DSBSS/main_app.py)
Create a centralized dashboard with 4 integrated views:
1. 🎛️ **Section Overview & Live Marey String Chart**: Time-distance trajectory graph of all section trains, with dynamic red shadow-block windows and alternative loop line routing.
2. ⚡ **Shadow-Block Auto-Planner (Multi-Department)**: Sliders for departmental requests (Engineering, Electrical, S&T), crisis injector (fog, signal failure), and one-click OR-Tools solve.
3. 📡 **Predictive Health & Telemetry Stream**: Live sensor charts (Motor Peak Amps, Throw Time, Vibration) + instant "Trigger Degraded Machine" button that automatically updates the schedule.
4. 💰 **Executive ROI & Capacity Analytics**: Metrics showing:
   - **Track Availability Gain**: $+22.4\%$
   - **Disruption Penalties Saved**: In ₹ Lakhs/Crores
   - **Punctuality Impact**: Trains delayed vs saved.
   - **Exportable Schedule**: Downloadable CSV/PDF operational order for loco pilots & station masters.

---

## Verification Plan

### Automated Tests
- Test CP-SAT solver feasibility under tight traffic schedules:
  ```bash
  python -c "from core.shadow_block_solver import run_solver_test; run_solver_test()"
  ```
- Test data extraction from [FINAL_ML_READY_DATA.csv](file:///d:/DSBSS/FINAL_ML_READY_DATA.csv):
  ```bash
  python -c "from core.data_engine import get_corridor_schedule; print(get_corridor_schedule('MAO').head())"
  ```
- Test ML model inference & auto-triggering:
  ```bash
  python -c "from core.ml_diagnostics import evaluate_sensor_telemetry; print(evaluate_sensor_telemetry())"
  ```

### Manual Verification
- Run `streamlit run main_app.py` in browser.
- Verify that selecting different crisis scenarios (e.g. Fog / Signal Failure) dynamically recalculates the optimal shadow block and updates the Marey String Chart.
- Verify that triggering an asset degradation alert in the Telemetry tab creates an automated maintenance block request and recalculates the train schedule.
